#!/usr/bin/env bash
# Smoke-test the Roboflow inference server against the socket-and-switch model.
# Usage:
#   export ROBOFLOW_API_KEY=xxxx
#   ./smoke_test.sh [path/to/image.jpg]
#
# If no image is given, downloads a free Creative Commons outlet photo.

set -euo pipefail

: "${ROBOFLOW_API_KEY:?Set ROBOFLOW_API_KEY first}"

MODEL_ID="${MODEL_ID:-socket-and-switch/1}"
SERVER="${SERVER:-http://localhost:9001}"
IMG="${1:-/tmp/outlet_test.jpg}"

if [[ ! -f "$IMG" ]]; then
  echo "Downloading test outlet image -> $IMG"
  # Public-domain US wall outlet from Wikimedia
  curl -fsSL -o "$IMG" \
    "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/US_receptacle_rotated.jpg/640px-US_receptacle_rotated.jpg"
fi

echo "Posting $(stat -c%s "$IMG") bytes to $SERVER/$MODEL_ID"
BASE64_IMG=$(base64 -w 0 "$IMG")

RESPONSE=$(curl -sS -X POST \
  "$SERVER/$MODEL_ID?api_key=$ROBOFLOW_API_KEY&confidence=0.4" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "$BASE64_IMG")

echo "--- response ---"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
