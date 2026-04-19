#!/usr/bin/env bash
# Firmware-only bench test for drive.ino (Path B).
# No ROS — talks directly to /dev/ttyACM0 at 9600 baud using pyserial.
#
# Checks (from T2.1 in the Notion plan):
#   1. DRIVE 80 80   -> both motors spin forward
#   2. DRIVE 0 0     -> stop
#   3. SCREW 1 / -1 / 0
#   4. Watchdog     -> send DRIVE 80 80, then go silent 700 ms, motors stop
#
# Usage:
#   ./t2_drive_bench.sh [/dev/ttyACM0]

set -euo pipefail

PORT="${1:-/dev/ttyACM0}"
BAUD="${BAUD:-9600}"

if [[ ! -e "$PORT" ]]; then
  echo "Port $PORT not found. Pass the device path as arg 1." >&2
  exit 1
fi

echo "T2 drive bench using $PORT @ $BAUD baud"

python3 - "$PORT" "$BAUD" <<'PY'
import sys, time
import serial

port, baud = sys.argv[1], int(sys.argv[2])
ser = serial.Serial(port=port, baudrate=baud, timeout=0.2, dsrdtr=False)
time.sleep(2.0)          # let the bootloader hand off
ser.reset_input_buffer()

def send(cmd, hold=0.5):
    print(f"  -> {cmd}")
    ser.write((cmd + "\n").encode("ascii"))
    ser.flush()
    time.sleep(hold)

def drain_status(label):
    end = time.time() + 0.3
    while time.time() < end:
        line = ser.readline().decode("ascii", errors="replace").strip()
        if line:
            print(f"     [{label}] {line}")

print("[1] DRIVE 80 80 (both forward)")
send("DRIVE 80 80", hold=1.0); drain_status("drive80")

print("[2] DRIVE 0 0 (stop)")
send("DRIVE 0 0", hold=0.5); drain_status("drive0")

print("[3a] SCREW 1 (raise)")
send("SCREW 1", hold=1.0); drain_status("screw+1")

print("[3b] SCREW -1 (lower)")
send("SCREW -1", hold=1.0); drain_status("screw-1")

print("[3c] SCREW 0 (stop)")
send("SCREW 0", hold=0.5); drain_status("screw0")

print("[4] Watchdog: DRIVE 120 120 then silent for 700 ms -> motors should cut")
send("DRIVE 120 120", hold=0.1); drain_status("pre-watchdog")
time.sleep(0.7)
drain_status("post-watchdog")  # STATUS line should show drive=0,0

print("[clean] final STOP")
send("STOP", hold=0.2); drain_status("stop")

ser.close()
print("done.")
PY
