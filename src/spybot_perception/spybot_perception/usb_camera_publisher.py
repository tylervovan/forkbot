"""
usb_camera_publisher — reads BGR frames from a UVC webcam via the GStreamer/MJPEG
pipeline in usb_camera_capture, re-encodes to JPEG, and publishes as
sensor_msgs/CompressedImage on /image_raw/compressed.

foxglove_bridge forwards the compressed topic directly to Foxglove Studio over
Tailscale; the browser-side decode is roughly free.
"""

import time

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

from spybot_perception.usb_camera_capture import (
    assert_gstreamer_available,
    open_usb_camera,
)

DEVICE = "/dev/video4"
WIDTH = 1280
HEIGHT = 720
FPS = 30
JPEG_QUALITY = 80
TOPIC = "/image_raw/compressed"
FRAME_ID = "usb_camera"


class UsbCameraPublisher(Node):
    def __init__(self) -> None:
        super().__init__("usb_camera_publisher")
        assert_gstreamer_available()
        self._cap = open_usb_camera(DEVICE, WIDTH, HEIGHT, FPS, codec="mjpeg")
        if not self._cap.isOpened():
            raise RuntimeError(
                f"GStreamer pipeline did not open for {DEVICE} at {WIDTH}x{HEIGHT}@{FPS}"
            )
        self._pub = self.create_publisher(CompressedImage, TOPIC, 10)
        self._timer = self.create_timer(1.0 / FPS, self._tick)
        self._frame_count = 0
        self._last_log = time.monotonic()
        self.get_logger().info(
            f"usb_camera_publisher up | {DEVICE} {WIDTH}x{HEIGHT}@{FPS} mjpeg | "
            f"publishing {TOPIC}"
        )

    def _tick(self) -> None:
        ok, bgr = self._cap.read()
        if not ok:
            self.get_logger().warn("capture read returned False")
            return
        success, jpeg = cv2.imencode(
            ".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
        )
        if not success:
            self.get_logger().warn("jpeg encode failed")
            return
        msg = CompressedImage()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = FRAME_ID
        msg.format = "jpeg"
        msg.data = jpeg.tobytes()
        self._pub.publish(msg)

        self._frame_count += 1
        now = time.monotonic()
        if now - self._last_log >= 5.0:
            hz = self._frame_count / (now - self._last_log)
            self.get_logger().info(f"publishing {hz:.1f} Hz")
            self._frame_count = 0
            self._last_log = now

    def destroy_node(self) -> bool:
        self._cap.release()
        return super().destroy_node()


def main(argv: list[str] | None = None) -> None:
    rclpy.init(args=argv)
    node = UsbCameraPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
