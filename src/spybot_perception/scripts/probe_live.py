#!/usr/bin/env python3
"""
probe_live — subscribe to /image_raw/compressed, grab ONE frame, save it to
/tmp/probe_frame.jpg, and POST it to the Roboflow server with confidence=0.01.
Dump the FULL response (no filter) so we can see every class + score the model
produces, including "switch" detections we normally hide.

Usage:
    bash -lic 'python3 scripts/probe_live.py'
"""

import base64
import os
import sys
import time

import rclpy
import requests
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage


API_KEY = os.environ["ROBOFLOW_API_KEY"]
MODEL_ID = "socket-and-switch/1"
URL = f"http://localhost:9001/{MODEL_ID}"


class FrameGrabber(Node):
    def __init__(self) -> None:
        super().__init__("probe_live")
        self._got_frame = False
        self.create_subscription(
            CompressedImage, "/image_raw/compressed", self._on_frame, 10
        )

    def _on_frame(self, msg: CompressedImage) -> None:
        if self._got_frame:
            return
        self._got_frame = True
        jpeg = bytes(msg.data)
        with open("/tmp/probe_frame.jpg", "wb") as f:
            f.write(jpeg)
        print(f"grabbed frame ({len(jpeg)} bytes) from /image_raw/compressed")
        print(f"saved to /tmp/probe_frame.jpg")

        print("\n--- posting to inference server (confidence=0.01) ---")
        b64 = base64.b64encode(jpeg).decode("ascii")
        t = time.monotonic()
        r = requests.post(
            URL,
            params={"api_key": API_KEY, "confidence": 0.01},
            data=b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5.0,
        )
        dt = time.monotonic() - t
        print(f"HTTP {r.status_code} in {dt*1000:.0f}ms")
        if r.ok:
            import json
            data = r.json()
            print(f"image: {data.get('image')}")
            preds = data.get("predictions", [])
            print(f"predictions: {len(preds)} total")
            for p in preds:
                print(
                    f"  class={p.get('class')!r} "
                    f"conf={p.get('confidence', 0):.3f} "
                    f"bbox=({p.get('x'):.0f},{p.get('y'):.0f}) "
                    f"{p.get('width'):.0f}x{p.get('height'):.0f}"
                )
        else:
            print(r.text[:500])


def main() -> int:
    rclpy.init()
    node = FrameGrabber()
    deadline = time.monotonic() + 10.0
    while rclpy.ok() and not node._got_frame and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
    if not node._got_frame:
        print("ERROR: no frame received on /image_raw/compressed within 10s",
              file=sys.stderr)
        return 1
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
