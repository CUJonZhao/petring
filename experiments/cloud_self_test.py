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
    p.add_argument("--seconds", type=int, default=90)
    p.add_argument("--boot", type=int, default=25, help="seconds to wait for boot and Wi-Fi")
    a = p.parse_args()
    c = json.loads(a.config.read_text())
    s = serial.Serial(port=None, baudrate=115200, timeout=0.2)
    s.dtr = False  # do not reset the board
    s.rts = False
    s.port = c["port"]
    s.open()
    def drain(seconds, count=0):
        """Read for a while; return how many timing lines appeared."""
        seen = 0
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            line = s.readline().decode(errors="replace").strip()
            if line.startswith(("STATUS", "ERROR", "{")):
                print(line, flush=True)
                if line.startswith("STATUS,cloud_timing"):
                    seen += 1
                    if count and seen >= count:
                        return seen
        return seen

    try:
        # Opening the port resets the board on this adapter, and bytes sent
        # during boot are lost, so wait for it to come up and join Wi-Fi first.
        drain(a.boot)
        s.write(b"NQT")
        if not drain(a.seconds // 2, count=3):
            s.write(b"T")  # the board may have still been connecting
            drain(a.seconds // 2, count=3)
    finally:
        s.close()


if __name__ == "__main__":
    main()
