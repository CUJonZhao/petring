#!/usr/bin/env python3
"""Ask the board to time a few requests to the site (serial "T"), and print them.

Read-only: the probe uses a session id that cannot exist, so nothing is stored
or changed. Use it to see where upload time goes without a full walk test:

  python3 experiments/cloud_self_test.py --config data/raw/cloud_sync_20260911/secrets.config.json
"""
import argparse
import json
import time
from pathlib import Path

import serial


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=60)
    a = p.parse_args()
    c = json.loads(a.config.read_text())
    s = serial.Serial(port=None, baudrate=115200, timeout=0.2)
    s.dtr = False  # do not reset the board
    s.rts = False
    s.port = c["port"]
    s.open()
    try:
        s.write(b"NQT")
        end = time.monotonic() + a.seconds
        seen = 0
        while time.monotonic() < end:
            line = s.readline().decode(errors="replace").strip()
            if line.startswith(("STATUS", "ERROR", "{")):
                print(line, flush=True)
                seen += line.startswith("STATUS,cloud_timing")
                if seen >= 3:
                    break
    finally:
        s.close()


if __name__ == "__main__":
    main()
