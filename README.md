# Spy Bot — Citrus Hack 2026

> A spy-themed autonomous robot that drives to a wall outlet, identifies the plug with on-device YOLO, and raises an arm to exactly the right height to plug itself in — streamed live to a remote operator over Tailscale + Foxglove.

**Theme:** Spy · **Event:** [Citrus Hack 2026](https://citrus-hack-2026.devpost.com/) · **Team size:** 4

## Demo in 30 seconds

1. Operator opens Foxglove on a laptop anywhere in the world.
2. Over Tailscale, they see live RGB + depth from the bot.
3. They drive the bot with a joystick toward a wall outlet.
4. A YOLO detector (RTX 4060) locks onto the outlet; depth tells us how far and how high it is.
5. E-STOP (or the RC transmitter) cuts motors at any moment.

**Next (wired, not yet auto):** operator presses **Engage** and the lead-screw arm raises to the detected outlet height.

## Architecture

```
    ┌──────────── Operator Laptop (RTX 4060) ─────────────┐
    │  librealsense · ONNX/Roboflow YOLO · outlet_planner │
    │  Foxglove Studio + spybot-panels extension          │
    │  drive_bridge ROS 2 node ─── pyserial ──► Arduino   │
    └─────────────────────┬───────────────────────────────┘
                          │ Tailscale (encrypted)
                          ▼
    ┌──────────────────── Spy Bot ────────────────────────┐
    │  Intel RealSense D435i ── USB3 ── laptop            │
    │  Arduino Uno + L298N ─── motors L/R + screw (arm)   │
    │  FS-iA6B RC receiver ─── hardware override          │
    └─────────────────────────────────────────────────────┘
```

## Repo layout

```
src/
  drive/                   Arduino sketch — 5-command serial protocol + 500 ms watchdog
  spybot_control/          ROS 2 package — drive_bridge node (Twist + Int8 → serial)
  spybot_perception/       ROS 2 package — RealSense capture + YOLO detection + overlay
  realsense-ros/           Vendor package (upstream Intel)
spybot-foxglove-extension/ Foxglove extension — Manual Engage panel (joystick + screw + E-STOP)
Speedrun-Firmware/         (Future) ESP32-S3 Zephyr arm controller — not shipped for hackathon
```

## Quick start

### 1. Flash the Arduino

```bash
# Open src/drive/drive.ino in the Arduino IDE, flash to an Uno R3.
# Confirm it enumerates as /dev/ttyACM0 (Linux) or COM* (Windows).
```

### 2. Bring up the operator laptop (Ubuntu + ROS 2 Humble)

```bash
cd src/spybot_control && pip install -e .
cd ../spybot_perception && pip install -e .

# In one terminal: drive bridge
ros2 launch spybot_control drive_bridge.launch.py serial_port:=/dev/ttyACM0

# In another: camera + detector
ros2 launch spybot_perception perception.launch.py
```

### 3. Foxglove extension

```bash
cd spybot-foxglove-extension
npm install
npm run local-install   # installs into Foxglove Desktop
```

Open Foxglove, load the operator layout JSON, point it at `ws://<bot-tailscale-hostname>:8765`.

### 4. Bench verification

Walk the bench checklist top-to-bottom before demo.

## Safety

- **RC transmitter** always wins over serial — hardware-level override.
- **500 ms firmware watchdog** — any serial silence cuts motors (`drive.ino`).
- **Foxglove E-STOP** — single click zeroes drive + screw; keyboard: Space / Esc.
- **Panel hygiene** — zeros both topics on unmount and window blur.

## Hardware

| Component | Notes |
| --- | --- |
| Intel RealSense D435i | RGB + depth + IMU |
| Arduino Uno R3 | Drive + screw MCU, serial protocol |
| L298N H-bridge | With heatsink — mandatory |
| REV HD Hex motor ×2 | Drive wheels |
| Lead-screw arm | Straight-line plug insertion |
| FlySky FS-i6X + FS-iA6B | RC override |
| RTX 4060 laptop | Brain: YOLO + planner + Foxglove |

## The pivot (2026-04-18)

Our Jetson Orin Nano bricked at T-18 hours. We moved the entire perception + planning stack to the operator laptop, kept the Arduino drive + RealSense camera, and shipped. Isaac ROS is out; librealsense + ONNX is in. Clean interfaces made this possible.

## License

{{TBD — MIT recommended for hackathon submission.}}

## Submitted to

[Citrus Hack 2026](https://citrus-hack-2026.devpost.com/) — tracks: Hardware Build, AI/ML & Data, Overall.
