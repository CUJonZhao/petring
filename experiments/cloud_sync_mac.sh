#!/bin/bash
# Mac helper for the home Wi-Fi sync firmware. Each step logs to
# data/raw/cloud_sync_20260911/<step>_<time>.log (ignored by Git).
#   bash experiments/cloud_sync_mac.sh probe     # tools + serial port
#   bash experiments/cloud_sync_mac.sh build     # compile only
#   bash experiments/cloud_sync_mac.sh flash     # compile + normal upload (keeps data partitions)
#   bash experiments/cloud_sync_mac.sh validate  # provision + simulated walk + cloud receipt
#   bash experiments/cloud_sync_mac.sh all       # flash, then validate (stops on failure)
set -u -o pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/data/raw/cloud_sync_20260911"
CONFIG="$OUT/secrets.config.json"
STEP="${1:-probe}"
if [ "$STEP" = all ]; then
  bash "$0" flash && bash "$0" validate
  exit $?
fi
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
LOG="$OUT/${STEP}_${STAMP}.log"
PIO="$(command -v pio || command -v platformio || true)"
[ -z "$PIO" ] && [ -x "$HOME/.platformio/penv/bin/pio" ] && PIO="$HOME/.platformio/penv/bin/pio"
[ -z "$PIO" ] && [ -x /tmp/petring-firmware-env/bin/pio ] && PIO=/tmp/petring-firmware-env/bin/pio
pick_python() {
  for py in python3 /tmp/petring-firmware-env/bin/python "$HOME/.platformio/penv/bin/python"; do
    if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import serial, requests' >/dev/null 2>&1; then
      echo "$py"; return 0
    fi
  done
  return 1
}
{
  echo "step=$STEP start=$(date)"
  echo "pio=${PIO:-missing} python=$(pick_python || echo 'missing pyserial/requests')"
  ls /dev/cu.usbserial-* 2>&1
  case "$STEP" in
    probe)
      [ -n "$PIO" ] && "$PIO" --version
      lsof /dev/cu.usbserial-* 2>/dev/null | head -5 ;;
    build)
      cd "$ROOT/firmware/imu_raw_stream" && "$PIO" run ;;
    flash)
      cd "$ROOT/firmware/imu_raw_stream" && "$PIO" run -t upload ;;
    validate)
      PY="$(pick_python)" || { echo "need a python with pyserial and requests"; exit 2; }
      "$PY" "$ROOT/experiments/validate_cloud_sync.py" --config "$CONFIG" \
        --output "$OUT/validation_$STAMP" --provision ;;
    *) echo "unknown step $STEP"; exit 2 ;;
  esac
  code=$?
  echo "EXIT=$code end=$(date)"
  exit $code
} 2>&1 | tee "$LOG"
