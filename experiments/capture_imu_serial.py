#!/usr/bin/env python3
"""Capture CSV samples emitted by firmware/imu_raw_stream."""

import argparse
import csv
import json
import time
from pathlib import Path

import serial


CSV_HEADER = [
    "host_elapsed_s",
    "device_ms",
    "ax_g",
    "ay_g",
    "az_g",
    "gx_dps",
    "gy_dps",
    "gz_dps",
    "temp_c",
    "motion_g",
    "battery_v",
]


def parse_sample(line: str) -> list[float] | None:
    fields = line.strip().split(",")
    if len(fields) != 10:
        return None

    try:
        return [float(value) for value in fields]
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)

    sample_count = 0
    invalid_line_count = 0
    first_device_ms = None
    last_device_ms = None
    motion_min = float("inf")
    motion_max = float("-inf")
    battery_min = float("inf")
    battery_max = float("-inf")
    gyro_peak = 0.0
    accel_min = [float("inf")] * 3
    accel_max = [float("-inf")] * 3
    start = time.monotonic()

    with serial.Serial(args.port, 115200, timeout=0.25) as port:
        with args.output.open("w", newline="", encoding="ascii") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(CSV_HEADER)

            while time.monotonic() - start < args.duration:
                sample = parse_sample(port.readline().decode("utf-8", errors="replace"))
                if sample is None:
                    invalid_line_count += 1
                    continue

                elapsed = time.monotonic() - start
                writer.writerow([f"{elapsed:.3f}", *sample])
                output_file.flush()

                sample_count += 1
                first_device_ms = sample[0] if first_device_ms is None else first_device_ms
                last_device_ms = sample[0]
                for index in range(3):
                    accel_min[index] = min(accel_min[index], sample[index + 1])
                    accel_max[index] = max(accel_max[index], sample[index + 1])
                gyro_peak = max(gyro_peak, *(abs(value) for value in sample[4:7]))
                motion_min = min(motion_min, sample[8])
                motion_max = max(motion_max, sample[8])
                battery_min = min(battery_min, sample[9])
                battery_max = max(battery_max, sample[9])

    device_elapsed_s = 0.0
    if sample_count > 1:
        device_elapsed_s = (last_device_ms - first_device_ms) / 1000

    summary = {
        "port": args.port,
        "requested_duration_s": args.duration,
        "sample_count": sample_count,
        "invalid_line_count": invalid_line_count,
        "device_elapsed_s": device_elapsed_s,
        "sample_rate_hz": (sample_count - 1) / device_elapsed_s if device_elapsed_s else 0.0,
        "motion_g_min": motion_min if sample_count else None,
        "motion_g_max": motion_max if sample_count else None,
        "battery_v_min": battery_min if sample_count else None,
        "battery_v_max": battery_max if sample_count else None,
        "gyro_peak_dps": gyro_peak if sample_count else None,
        "accel_span_g": [
            accel_max[index] - accel_min[index] if sample_count else None
            for index in range(3)
        ],
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="ascii")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
