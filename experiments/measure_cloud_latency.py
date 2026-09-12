#!/usr/bin/env python3
"""Time the site's device endpoint from this computer.

The board spends about 4 s per upload request even on a reused TLS connection.
This tells us whether that is the site's own response time or something on the
board: run it from the Mac, which has none of the board's constraints.

  python3 experiments/measure_cloud_latency.py --config data/raw/cloud_sync_20260911/secrets.config.json

Only the status endpoint is used (a read), with a session id that does not exist,
so nothing is uploaded, changed or deleted.
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import requests


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--samples", type=int, default=8)
    a = p.parse_args()
    c = json.loads(a.config.read_text())
    headers = {"OAI-Sites-Authorization": "Bearer " + c["bypass"],
               "Authorization": "Bearer " + c["token"]}
    params = {"id": "00000000", "sha": "0" * 64, "size": 4096}
    fresh, reused = [], []
    for index in range(a.samples):
        session = requests.Session()  # first call per session includes the TLS handshake
        for attempt in range(2):
            start = time.monotonic()
            r = session.get(c["url"] + "/api/device/status", params=params, headers=headers, timeout=30)
            elapsed = round((time.monotonic() - start) * 1000)
            (fresh if attempt == 0 else reused).append(elapsed)
            if index == 0 and attempt == 0:
                print("http", r.status_code, r.text[:120])
        session.close()
    for name, values in (("new connection", fresh), ("reused connection", reused)):
        print("%-18s median %5d ms   min %5d   max %5d   (n=%d)"
              % (name, statistics.median(values), min(values), max(values), len(values)))


if __name__ == "__main__":
    main()
