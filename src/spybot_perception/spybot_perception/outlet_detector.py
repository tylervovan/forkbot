"""
outlet_detector — ROS 2 node that runs Roboflow YOLO inference on USB camera JPEG
frames and republishes detections for Foxglove overlay.

Pipeline:
    /image_raw/compressed  (sensor_msgs/CompressedImage)
        -> base64 the JPEG bytes directly (no decode / re-encode)
        -> HTTP POST to local Roboflow inference server (port 9001)
        -> parse predictions
        -> filter (class == 'socket', confidence > threshold)
        -> /detections (vision_msgs/Detection2DArray)
"""

import base64
import time
from typing import List

import rclpy
import requests
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from vision_msgs.msg import (
    BoundingBox2D,
    Detection2D,
    Detection2DArray,
    ObjectHypothesisWithPose,
)

# --- Configuration ------------------------------------------------------------
INFERENCE_URL = "http://localhost:9001"
MODEL_ID = "socket-and-switch/1"            # Roboflow Universe model
API_KEY_ENV = "ROBOFLOW_API_KEY"             # env var name (read in main())
CONFIDENCE_THRESHOLD = 0.5                    # T1.2: "confidence above 0.5"
TARGET_CLASS = "0 Outlet"                     # dataset label; "Switch" is the other class
MAX_INFERENCE_HZ = 10.0                       # T1.2: rate-limit 10 Hz
LOG_PERIOD_SEC = 5.0                          # T1.2: log every 5 seconds
IMAGE_TOPIC = "/image_raw/compressed"


class OutletDetector(Node):
    def __init__(self, api_key: str):
        super().__init__("outlet_detector")
        self._api_key = api_key
        self._session = requests.Session()    # reuse TCP connection (keepalive)
        self._min_period = 1.0 / MAX_INFERENCE_HZ
        self._last_inference_time = 0.0

        # Stats for periodic logging
        self._det_count_total = 0
        self._conf_sum = 0.0
        self._conf_n = 0
        self._frames_processed = 0
        self._frames_skipped = 0
        self._last_log_time = time.monotonic()

        self._sub = self.create_subscription(
            CompressedImage,
            IMAGE_TOPIC,
            self._on_image,
            qos_profile=10,
        )
        self._pub = self.create_publisher(Detection2DArray, "/detections", 10)

        self.get_logger().info(
            f"outlet_detector up | model={MODEL_ID} | topic={IMAGE_TOPIC} | "
            f"conf>{CONFIDENCE_THRESHOLD} | class={TARGET_CLASS} | "
            f"max_hz={MAX_INFERENCE_HZ}"
        )

    # --- Image callback -------------------------------------------------------
    def _on_image(self, msg: CompressedImage) -> None:
        now = time.monotonic()
        if (now - self._last_inference_time) < self._min_period:
            self._frames_skipped += 1
            return
        self._last_inference_time = now

        predictions = self._infer(bytes(msg.data))
        if predictions is None:
            return  # network / server error, logged inside

        # Raw server output (pre-filter) — indispensable for debugging
        if predictions:
            raw_summary = [(p.get("class"), round(p.get("confidence", 0), 2))
                           for p in predictions]
            self.get_logger().info(f"raw preds: {raw_summary}")

        filtered = self._filter_predictions(predictions)
        self._publish_detections(filtered, msg.header)

        # Stats bookkeeping
        self._frames_processed += 1
        self._det_count_total += len(filtered)
        for p in filtered:
            self._conf_sum += p["confidence"]
            self._conf_n += 1

        # Periodic summary
        if (now - self._last_log_time) >= LOG_PERIOD_SEC:
            mean_conf = (self._conf_sum / self._conf_n) if self._conf_n else 0.0
            self.get_logger().info(
                f"[{LOG_PERIOD_SEC:.0f}s] frames={self._frames_processed} "
                f"skipped={self._frames_skipped} dets={self._det_count_total} "
                f"mean_conf={mean_conf:.2f}"
            )
            self._det_count_total = 0
            self._conf_sum = 0.0
            self._conf_n = 0
            self._frames_processed = 0
            self._frames_skipped = 0
            self._last_log_time = now

    # --- HTTP call to Roboflow inference server -------------------------------
    def _infer(self, jpeg_bytes: bytes) -> list | None:
        b64 = base64.b64encode(jpeg_bytes).decode("ascii")

        try:
            r = self._session.post(
                f"{INFERENCE_URL}/{MODEL_ID}",
                # Server filters at 0.01 so our raw logs show everything; the
                # client-side filter then enforces CONFIDENCE_THRESHOLD.
                params={"api_key": self._api_key, "confidence": 0.01},
                data=b64,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=2.0,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            self.get_logger().warn(f"inference request failed: {exc}")
            return None

        return r.json().get("predictions", [])

    def _filter_predictions(self, predictions: list) -> list:
        return [p for p in predictions
                if p["class"] == TARGET_CLASS and p["confidence"] >= CONFIDENCE_THRESHOLD]

    # --- Publish --------------------------------------------------------------
    def _publish_detections(self, predictions: list, header) -> None:
        out = Detection2DArray()
        out.header = header
        for p in predictions:
            det = Detection2D()
            det.header = header
            bb = BoundingBox2D()
            bb.center.position.x = float(p["x"])
            bb.center.position.y = float(p["y"])
            bb.size_x = float(p["width"])
            bb.size_y = float(p["height"])
            det.bbox = bb
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = str(p["class"])
            hyp.hypothesis.score = float(p["confidence"])
            det.results.append(hyp)
            out.detections.append(det)
        self._pub.publish(out)


def main(argv: List[str] | None = None) -> None:
    import os
    api_key = os.environ.get(API_KEY_ENV, "")
    if not api_key:
        raise RuntimeError(
            f"Set {API_KEY_ENV} to your Roboflow API key "
            "(get one free at https://app.roboflow.com/settings/api)"
        )
    rclpy.init(args=argv)
    node = OutletDetector(api_key=api_key)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
