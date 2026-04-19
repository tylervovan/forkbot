#!/usr/bin/env python3
"""
probe_camera — list what a UVC webcam actually supports, then print a ready-to-
paste GStreamer pipeline for the largest MJPG (and H.264, if offered) mode.

Why: GStreamer pipelines fail-closed when caps don't match the camera's v4l2
table, and the error message is unhelpful. Run this first, copy the caps it
emits into usb_camera_capture, move on.

Usage:
    python3 probe_camera.py [/dev/videoN]
"""

import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    fourcc: str
    width: int
    height: int
    fps: float


def list_formats(device: str) -> str:
    result = subprocess.run(
        ["v4l2-ctl", "--list-formats-ext", "-d", device],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"v4l2-ctl failed for {device}: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


_FOURCC_RE = re.compile(r"^\s*\[\d+\]:\s*'(\w+)'")
_SIZE_RE = re.compile(r"Size:\s*Discrete\s+(\d+)x(\d+)")
_FPS_RE = re.compile(r"\(([\d.]+)\s*fps\)")


def parse_modes(v4l2_output: str) -> list[Mode]:
    modes: list[Mode] = []
    current_fourcc: str | None = None
    current_size: tuple[int, int] | None = None
    for line in v4l2_output.splitlines():
        fourcc_match = _FOURCC_RE.match(line)
        if fourcc_match:
            current_fourcc = fourcc_match.group(1)
            continue
        size_match = _SIZE_RE.search(line)
        if size_match:
            current_size = (int(size_match.group(1)), int(size_match.group(2)))
            continue
        fps_match = _FPS_RE.search(line)
        if fps_match and current_fourcc and current_size:
            modes.append(
                Mode(
                    fourcc=current_fourcc,
                    width=current_size[0],
                    height=current_size[1],
                    fps=float(fps_match.group(1)),
                )
            )
    return modes


def largest_mode(modes: list[Mode], fourcc: str, min_fps: float = 15.0) -> Mode | None:
    candidates = [
        m for m in modes if m.fourcc == fourcc and m.fps >= min_fps
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda m: (m.width * m.height, m.fps))


def pipeline_for(mode: Mode, device: str) -> str:
    caps = f"width={mode.width},height={mode.height},framerate={int(mode.fps)}/1"
    tail = (
        "videoconvert ! video/x-raw,format=BGR "
        "! appsink drop=true max-buffers=1 sync=false"
    )
    if mode.fourcc == "MJPG":
        return (
            f"v4l2src device={device} io-mode=2 "
            f"! image/jpeg,{caps} ! jpegdec ! {tail}"
        )
    if mode.fourcc == "H264":
        return (
            f"v4l2src device={device} "
            f"! video/x-h264,{caps} ! h264parse ! avdec_h264 ! {tail}"
        )
    return (
        f"v4l2src device={device} "
        f"! video/x-raw,format={mode.fourcc},{caps} ! {tail}"
    )


def main(argv: list[str]) -> int:
    device = argv[1] if len(argv) > 1 else "/dev/video0"
    try:
        output = list_formats(device)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("hint: `sudo apt install v4l-utils` then plug in the camera", file=sys.stderr)
        return 1

    modes = parse_modes(output)
    if not modes:
        print(f"no modes parsed from v4l2-ctl output for {device}", file=sys.stderr)
        print(output, file=sys.stderr)
        return 1

    print(f"# Found {len(modes)} modes on {device}")
    for fourcc in ("MJPG", "H264", "YUYV"):
        mode = largest_mode(modes, fourcc)
        if mode is None:
            print(f"# {fourcc}: not supported")
            continue
        print(
            f"# {fourcc}: largest = {mode.width}x{mode.height} @ {mode.fps:.0f} fps"
        )
        print(pipeline_for(mode, device))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
