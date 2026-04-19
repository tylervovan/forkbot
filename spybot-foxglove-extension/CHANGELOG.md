# Changelog

## 0.1.0 — 2026-04-19

Initial release.

- Manual Engage panel
  - Virtual joystick → `geometry_msgs/Twist` on `/cmd_drive`
  - Momentary Screw Up / Screw Down buttons → `std_msgs/Int8` on `/cmd_screw`
  - E-STOP button (zero Twist + Int8(0))
  - WASD / R / F / Space keyboard shortcuts
  - Settings sidebar: topic names, max linear, max angular, publish rate
  - Auto-zero on unmount and window blur
