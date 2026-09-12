#!/usr/bin/env python3
"""Summarize one physical home-sync run: sampling coverage and upload blocking.

Usage: python3 experiments/analyze_cloud_sync_run.py data/raw/cloud_sync_20260911/<run dir>

Sampling numbers come from the session binary the run downloaded from the board.
Blocking numbers come from the serial log: the firmware prints one CSV row per
sample, so a jump between consecutive row timestamps is time the main loop spent
inside something else (flash writes, HTTPS requests).
"""
import argparse
import importlib.util
import json
import re
import statistics
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def decoder():
    spec = importlib.util.spec_from_file_location("decoder", ROOT / "experiments/decode_motion_log.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sampling(binary: Path):
    out = Path(tempfile.mkdtemp()) / "session.csv"
    info = decoder().convert(binary, out)
    times = [int(line.split(",")[0]) for line in out.read_text().splitlines()[1:]]
    if len(times) < 2:
        return None
    gaps = [b - a for a, b in zip(times, times[1:])]
    late = [g for g in gaps if g > 100]
    span = times[-1] / 1000
    return {
        "file": binary.name,
        "samples": len(times),
        "span_s": round(span, 1),
        "mean_hz": round(len(times) / span, 2),
        "interval_median_ms": statistics.median(gaps),
        "interval_max_ms": max(gaps),
        "gaps_over_100ms": len(late),
        "gap_seconds": round(sum(late) / 1000, 1),
        "uncovered_percent": round(100 * sum(late) / times[-1], 1),
        "start_unix_ms": info.get("start_unix_ms"),
    }


def blocking(log: Path):
    stalls, previous = [], None
    for line in log.read_text(errors="replace").splitlines():
        row = re.match(r"^(\d+),-?\d", line)
        if not row:
            continue
        now = int(row.group(1))
        if previous is not None and now > previous and now - previous > 400:
            stalls.append(now - previous)
        previous = now
    if not stalls:
        return {"file": log.name, "stalls_over_400ms": 0}
    ordered = sorted(stalls)
    return {
        "file": log.name,
        "stalls_over_400ms": len(stalls),
        "median_ms": statistics.median(stalls),
        "p90_ms": ordered[int(len(ordered) * 0.9)],
        "max_ms": max(stalls),
        "total_s": round(sum(stalls) / 1000, 1),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", type=Path, help="validation output directory")
    a = p.parse_args()
    report = {"run": str(a.run)}
    result = a.run / "result.json"
    if result.is_file():
        data = json.loads(result.read_text())
        report["passed"] = data.get("passed")
        report["events"] = [event["name"] for event in data.get("events", [])]
        report["receipt"] = data.get("receipt")
    report["sampling"] = [s for s in (sampling(b) for b in sorted(a.run.glob("*.bin"))) if s]
    report["blocking"] = [blocking(f) for f in sorted(a.run.glob("*.log"))]
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
