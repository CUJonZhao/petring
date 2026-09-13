#!/usr/bin/env python3
"""Operate and preserve one battery-powered Delta recording session.

Use ``status`` while USB is attached. After unplugging USB and confirming the
board has rejoined home Wi-Fi, use ``start --confirm-battery-only``. At the
end, return to home Wi-Fi but keep USB disconnected; use ``stop`` to stop,
download and cross-check the completed session. Reconnect USB only after that
clean stop.

The explicit confirmation prevents accidentally starting the battery test
while the USB cable is still powering the board.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from decode_motion_log import convert


def request(base, path, method="GET", form=None):
    data = urlencode(form).encode() if form else None
    req = Request(base.rstrip("/") + path, data=data, method=method)
    try:
        with urlopen(req, timeout=12) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except URLError as exc:
        raise RuntimeError(f"device unreachable: {exc.reason}") from exc


def json_request(base, path, method="GET", form=None):
    status, _, body = request(base, path, method, form)
    try:
        value = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path} returned non-JSON HTTP {status}: {body[:200]!r}") from exc
    if status >= 300:
        raise RuntimeError(f"{path} returned HTTP {status}: {value}")
    return value


def snapshot(base):
    return {
        "recording": json_request(base, "/api/recording"),
        "latest": json_request(base, "/api/latest"),
        "cloud": json_request(base, "/api/cloud"),
    }


def cmd_status(args):
    print(json.dumps(snapshot(args.url), indent=2))


def cmd_start(args):
    if not args.confirm_battery_only:
        raise SystemExit("Refusing to start: pass --confirm-battery-only after USB is unplugged.")
    before = snapshot(args.url)
    if before["recording"]["recording"]:
        raise SystemExit(f"A recording is already active: {before['recording']['id']}")
    started = json_request(
        args.url, "/api/recording/start", "POST",
        {"unix_ms": str(int(time.time() * 1000))},
    )
    if not started["recording"] or not started["id"]:
        raise SystemExit(f"The board did not enter recording state: {started}")
    print(json.dumps({"before": before, "started": started}, indent=2))


def cmd_stop(args):
    before = json_request(args.url, "/api/recording")
    if not before["recording"] or not before["id"]:
        raise SystemExit(f"No active recording to stop: {before}")
    session_id = before["id"]
    stopped = json_request(args.url, "/api/recording/stop", "POST")
    if stopped["recording"] or stopped["error"]:
        raise SystemExit(f"The board did not cleanly stop: {stopped}")

    args.output.mkdir(parents=True, exist_ok=True)
    status, headers, csv_bytes = request(args.url, f"/api/session?id={session_id}&format=csv")
    if status != 200:
        raise SystemExit(f"CSV download failed with HTTP {status}")
    status, _, binary = request(args.url, f"/api/session?id={session_id}&format=bin")
    if status != 200:
        raise SystemExit(f"Binary download failed with HTTP {status}")
    csv_path = args.output / f"{session_id}.csv"
    bin_path = args.output / f"{session_id}.bin"
    decoded_path = args.output / f"{session_id}-decoded.csv"
    csv_path.write_bytes(csv_bytes)
    bin_path.write_bytes(binary)
    rows = list(csv.DictReader(io.StringIO(csv_bytes.decode())))
    decoded = convert(bin_path, decoded_path)
    expected = int(headers["X-Delta-Records"])
    if len(rows) != expected or decoded["records"] != expected or decoded["warnings"]:
        raise SystemExit(
            f"Downloaded files do not agree: CSV={len(rows)}, header={expected}, "
            f"decoded={decoded['records']}, warnings={decoded['warnings']}"
        )
    elapsed_ms = int(rows[-1]["elapsed_ms"]) if rows else 0
    report = {
        "id": session_id,
        "records": expected,
        "elapsed_ms": elapsed_ms,
        "effective_hz": round((len(rows) - 1) * 1000 / elapsed_ms, 3) if elapsed_ms and len(rows) > 1 else 0,
        "csv_binary_agree": True,
        "binary_sha256": hashlib.sha256(binary).hexdigest(),
        "stopped": stopped,
        "cloud_after_stop": json_request(args.url, "/api/cloud"),
        "files": {"csv": str(csv_path), "binary": str(bin_path), "decoded_csv": str(decoded_path)},
    }
    (args.output / f"{session_id}-result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://172.24.23.133")
    parser.add_argument("--output", type=Path, default=Path("data/raw/battery_recording"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    start = sub.add_parser("start")
    start.add_argument("--confirm-battery-only", action="store_true")
    sub.add_parser("stop")
    args = parser.parse_args()
    {"status": cmd_status, "start": cmd_start, "stop": cmd_stop}[args.command](args)


if __name__ == "__main__":
    main()
