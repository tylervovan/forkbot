"""
usb_camera_capture — build a GStreamer pipeline that asks a UVC USB webcam for an
already-compressed stream (MJPEG or UVC-H.264), decodes it in-process, and
exposes a cv2.VideoCapture that yields BGR frames at full native resolution.

Why compressed-over-USB: raw 1280x720x3 @ 30 fps is ~663 Mbps, which exceeds
USB 2's 480 Mbps ceiling and causes dropped frames on shared hubs. Asking the
camera for MJPEG drops the wire load to ~10-20 Mbps with 20x-60x headroom.

Usage:
    cap = open_usb_camera("/dev/video0", 1280, 720, 30, codec="mjpeg")
    if not cap.isOpened():
        raise RuntimeError("pipeline negotiation failed")
    ok, bgr = cap.read()
"""

from dataclasses import dataclass
from typing import Literal

import cv2

Codec = Literal["mjpeg", "h264"]


@dataclass(frozen=True)
class CaptureConfig:
    device: str = "/dev/video4"
    width: int = 1280
    height: int = 720
    fps: int = 30
    codec: Codec = "mjpeg"


def build_pipeline(cfg: CaptureConfig) -> str:
    caps = f"width={cfg.width},height={cfg.height},framerate={cfg.fps}/1"
    tail = (
        "videoconvert ! video/x-raw,format=BGR "
        "! appsink drop=true max-buffers=1 sync=false"
    )
    if cfg.codec == "mjpeg":
        source = (
            f"v4l2src device={cfg.device} io-mode=2 "
            f"! image/jpeg,{caps} ! jpegdec"
        )
    elif cfg.codec == "h264":
        source = (
            f"v4l2src device={cfg.device} "
            f"! video/x-h264,{caps} ! h264parse ! avdec_h264"
        )
    else:
        raise ValueError(f"unsupported codec: {cfg.codec!r}")
    return f"{source} ! {tail}"


def open_usb_camera(
    device: str = "/dev/video0",
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    codec: Codec = "mjpeg",
) -> cv2.VideoCapture:
    cfg = CaptureConfig(device=device, width=width, height=height, fps=fps, codec=codec)
    pipeline = build_pipeline(cfg)
    return cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)


def assert_gstreamer_available() -> None:
    info = cv2.getBuildInformation()
    for line in info.splitlines():
        if "GStreamer" in line:
            if "YES" in line:
                return
            raise RuntimeError(
                f"cv2 was built without GStreamer support: {line.strip()!r}. "
                "Install distro OpenCV (`sudo apt install python3-opencv`) or "
                "rebuild from source with -D WITH_GSTREAMER=ON."
            )
    raise RuntimeError("could not find GStreamer line in cv2.getBuildInformation()")
