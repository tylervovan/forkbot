"""
drive_bridge — ROS 2 node that forwards /cmd_drive (Twist) and /cmd_screw (Int8)
to the Arduino over USB serial using the Path B protocol (see drive.ino):

    DRIVE <left> <right>\\n    left,right in [-255, 255]  (pre-mixed wheel PWMs)
    SCREW <dir>\\n             dir in {-1, 0, +1}

The node holds the serial port open at 9600 baud, performs a 2 s sleep after
open (Arduino auto-resets on DTR), flushes the input buffer, then sends a
single DRIVE 0 0 handshake to prime the firmware watchdog before entering the
main heartbeat loop at 20 Hz.

Kinematics lives here (arcade mix). The Arduino is a dumb motor driver on the
serial path — DO NOT re-mix on the firmware side.
"""

import math
import threading
import time
from typing import List, Optional

import rclpy
import serial
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Int8


class DriveBridge(Node):
    def __init__(self) -> None:
        super().__init__("drive_bridge")

        self.declare_parameter("serial_port", "/dev/ttyACM0")
        self.declare_parameter("baud_rate", 9600)
        self.declare_parameter("watchdog_ms", 500)
        self.declare_parameter("heartbeat_hz", 20.0)
        self.declare_parameter("max_pwm", 255)
        self.declare_parameter("linear_scale", 255.0)
        self.declare_parameter("angular_scale", 255.0)
        self.declare_parameter("boot_sleep_sec", 2.0)

        self._port: str = self.get_parameter("serial_port").value
        self._baud: int = int(self.get_parameter("baud_rate").value)
        self._max_pwm: int = int(self.get_parameter("max_pwm").value)
        self._linear_scale: float = float(self.get_parameter("linear_scale").value)
        self._angular_scale: float = float(self.get_parameter("angular_scale").value)
        heartbeat_hz: float = float(self.get_parameter("heartbeat_hz").value)
        self._heartbeat_period = 1.0 / heartbeat_hz if heartbeat_hz > 0 else 0.05
        boot_sleep: float = float(self.get_parameter("boot_sleep_sec").value)

        self._last_drive_l = 0
        self._last_drive_r = 0
        self._last_screw = 0
        self._ser_lock = threading.Lock()

        self.get_logger().info(
            f"opening serial {self._port} @ {self._baud} baud "
            f"(heartbeat {heartbeat_hz:.1f} Hz)"
        )
        self._ser = serial.Serial(
            port=self._port,
            baudrate=self._baud,
            timeout=0.1,
            dsrdtr=False,
        )

        # Boot sequence (see plan Phase 3). Without this the Arduino bootloader
        # eats the first commands and prints "Dual Motor System Ready."
        # garbage into our RX that would later confuse any read-back.
        time.sleep(boot_sleep)
        self._ser.reset_input_buffer()
        self._write_raw(b"DRIVE 0 0\n")
        self._ser.flush()
        self.get_logger().info("serial ready; sent initial DRIVE 0 0")

        self._cmd_drive_sub = self.create_subscription(
            Twist, "/cmd_drive", self._on_cmd_drive, qos_profile=10
        )
        self._cmd_screw_sub = self.create_subscription(
            Int8, "/cmd_screw", self._on_cmd_screw, qos_profile=10
        )

        self._heartbeat = self.create_timer(
            self._heartbeat_period, self._send_heartbeat
        )

    # --- Callbacks ------------------------------------------------------------
    def _on_cmd_drive(self, msg: Twist) -> None:
        lin = msg.linear.x
        ang = msg.angular.z
        left = lin * self._linear_scale + ang * self._angular_scale
        right = lin * self._linear_scale - ang * self._angular_scale
        self._last_drive_l = self._clamp_pwm(left)
        self._last_drive_r = self._clamp_pwm(right)

    def _on_cmd_screw(self, msg: Int8) -> None:
        d = max(-1, min(1, int(msg.data)))
        self._last_screw = d
        # Send immediately so operators feel latch responsiveness.
        self._write_line(f"SCREW {d}")

    # --- Heartbeat ------------------------------------------------------------
    def _send_heartbeat(self) -> None:
        self._write_line(f"DRIVE {self._last_drive_l} {self._last_drive_r}")

    # --- Serial helpers -------------------------------------------------------
    def _clamp_pwm(self, value: float) -> int:
        if math.isnan(value):
            return 0
        return max(-self._max_pwm, min(self._max_pwm, int(round(value))))

    def _write_line(self, line: str) -> None:
        self._write_raw((line + "\n").encode("ascii"))

    def _write_raw(self, payload: bytes) -> None:
        with self._ser_lock:
            try:
                self._ser.write(payload)
            except serial.SerialException as exc:
                self.get_logger().warn(f"serial write failed: {exc}")

    # --- Shutdown -------------------------------------------------------------
    def safe_stop_and_close(self) -> None:
        try:
            self._write_line("DRIVE 0 0")
            self._write_line("SCREW 0")
            with self._ser_lock:
                self._ser.flush()
                self._ser.close()
            self.get_logger().info("serial closed after safe stop")
        except Exception as exc:  # noqa: BLE001 — best-effort on shutdown
            self.get_logger().warn(f"safe_stop_and_close error: {exc}")


def main(argv: Optional[List[str]] = None) -> None:
    rclpy.init(args=argv)
    node = DriveBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.safe_stop_and_close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
