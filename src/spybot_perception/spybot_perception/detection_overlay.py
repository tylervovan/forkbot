"""
detection_overlay — draw /detections bounding boxes on /image_raw/compressed
frames and publish the annotated result as /image_annotated/compressed.

Time-sync strategy: latest-wins. Cache the most recent Detection2DArray and
draw it on every incoming frame. At 30 Hz camera × 10 Hz detector, the
detections can be up to 100ms stale, which is imperceptible for teleop.
"""

from __future__ import annotations

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from vision_msgs.msg import Detection2DArray

INPUT_IMAGE_TOPIC = "/image_raw/compressed"
DETECTIONS_TOPIC = "/detections"
OUTPUT_IMAGE_TOPIC = "/image_annotated/compressed"
JPEG_QUALITY = 80

BOX_COLOR = (0, 255, 255)   # BGR yellow
BOX_THICKNESS = 3
TEXT_COLOR = (0, 0, 0)
TEXT_BG = (0, 255, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.6
FONT_THICK = 2


class DetectionOverlay(Node):
    def __init__(self) -> None:
        super().__init__("detection_overlay")
        self._latest_detections: Detection2DArray | None = None

        self.create_subscription(
            Detection2DArray, DETECTIONS_TOPIC, self._on_dets, 10
        )
        self.create_subscription(
            CompressedImage, INPUT_IMAGE_TOPIC, self._on_image, 10
        )
        self._pub = self.create_publisher(
            CompressedImage, OUTPUT_IMAGE_TOPIC, 10
        )
        self.get_logger().info(
            f"detection_overlay up | {INPUT_IMAGE_TOPIC} + {DETECTIONS_TOPIC} "
            f"-> {OUTPUT_IMAGE_TOPIC}"
        )

    def _on_dets(self, msg: Detection2DArray) -> None:
        self._latest_detections = msg

    def _on_image(self, msg: CompressedImage) -> None:
        arr = np.frombuffer(bytes(msg.data), dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return

        if self._latest_detections is not None:
            for det in self._latest_detections.detections:
                bb = det.bbox
                cx, cy = bb.center.position.x, bb.center.position.y
                w, h = bb.size_x, bb.size_y
                x1, y1 = int(cx - w / 2), int(cy - h / 2)
                x2, y2 = int(cx + w / 2), int(cy + h / 2)
                cv2.rectangle(bgr, (x1, y1), (x2, y2), BOX_COLOR, BOX_THICKNESS)
                if det.results:
                    cls = det.results[0].hypothesis.class_id
                    score = det.results[0].hypothesis.score
                    label = f"{cls} {score:.2f}"
                    (tw, th), _ = cv2.getTextSize(label, FONT, FONT_SCALE, FONT_THICK)
                    cv2.rectangle(
                        bgr, (x1, y1 - th - 6), (x1 + tw + 4, y1), TEXT_BG, -1
                    )
                    cv2.putText(
                        bgr, label, (x1 + 2, y1 - 4),
                        FONT, FONT_SCALE, TEXT_COLOR, FONT_THICK, cv2.LINE_AA,
                    )

        ok, jpeg = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if not ok:
            return
        out = CompressedImage()
        out.header = msg.header
        out.format = "jpeg"
        out.data = jpeg.tobytes()
        self._pub.publish(out)


def main(argv: list[str] | None = None) -> None:
    rclpy.init(args=argv)
    node = DetectionOverlay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
