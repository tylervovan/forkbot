# Spy Bot Manual Engage — Foxglove Extension

Single-panel Foxglove extension for T2 operator control of the Spy Bot over Tailscale.
Publishes to the `drive_bridge` ROS 2 node (`geometry_msgs/Twist` → `/cmd_drive`,
`std_msgs/Int8` → `/cmd_screw`).

## Panel

**Manual Engage** — joystick + momentary screw buttons + E-STOP.

Controls:
- **Joystick** — drag to steer. Forward on Y axis = `linear.x`, left/right on X axis = `angular.z`.
  Values are normalized to [-1, 1] and scaled by the settings sidebar `Max linear / Max angular`.
- **WASD** — keyboard alt to the joystick.
- **Screw Up / Screw Down** — hold to publish `+1` / `-1` on `/cmd_screw`; release publishes `0`.
  Keys `R` and `F`.
- **E-STOP** — single click sends zero Twist + Int8(0). Key: `Space` or `Esc`.

## Safety

- Panel zeroes both topics on unmount and on window blur.
- Drive publishes throttled to the `publishHz` setting (default 20 Hz) while the joystick has
  non-zero intent; ramps down to a final zero Twist immediately after release.
- Momentary screw buttons use `onPointerLeave` + `onPointerCancel` to release on drag-off.
- **Firmware** watchdog (500 ms serial silence → motors off) and the RC transmitter override
  are the primary safety backstops — see the T2 plan.

## Topic names

| Topic | Type | Default | Configurable |
|-------|------|---------|--------------|
| drive | `geometry_msgs/Twist` | `/cmd_drive` | ✓ |
| screw | `std_msgs/Int8` | `/cmd_screw` | ✓ |

## Build

```bash
npm install
npm run build         # webpack → dist/extension.js
npm run package       # produces spybot.spybot-panels-0.1.0.foxe
```

Install locally into Foxglove Desktop:

```bash
npm run local-install
```

Or upload the `.foxe` at `app.foxglove.dev` → Settings → Extensions.

## Testing without hardware

Point Foxglove at a running `foxglove_bridge` (or a `rosbridge`/mock) that advertises `/cmd_drive`
and `/cmd_screw`. Verify via:

```bash
ros2 topic echo /cmd_drive
ros2 topic echo /cmd_screw
```

Press the joystick / screw buttons / E-STOP and confirm the messages.
