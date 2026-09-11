#!/usr/bin/env python3
"""Decode Delta DLOG v1 files without the device; validate CRCs before export."""
import argparse
import binascii
import csv
import json
import math
import os
from pathlib import Path
import struct
import tempfile

HEADER_BYTES, RECORD_BYTES = 32, 24
COLUMNS = "elapsed_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,temp_c,motion_g,activity_score,battery_v,state".split(",")


def convert(source, destination, recover_prefix=False):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output must be different files")
    stats = {"records": 0, "last_elapsed_ms": 0, "trailing_bytes": 0,
             "recovered_prefix": False, "warnings": []}
    temporary = None
    try:
        with source.open("rb") as incoming:
            header = incoming.read(HEADER_BYTES)
            if len(header) != HEADER_BYTES:
                raise ValueError("Incomplete header; original file was not changed")
            magic, version, record_size, period, uptime, unix_ms = struct.unpack("<4sHHIIQ", header[:24])
            if (magic, version, record_size, period) != (b"DLOG", 1, RECORD_BYTES, 50):
                raise ValueError("Unsupported log format")
            if binascii.crc_hqx(header[:30], 0xffff) != struct.unpack_from("<H", header, 30)[0]:
                raise ValueError("Header CRC mismatch")
            stats.update(start_unix_ms=unix_ms, start_uptime_ms=uptime, sample_period_ms=period)
            with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8",
                                             dir=destination.parent, delete=False) as output:
                temporary = Path(output.name)
                writer = csv.writer(output, lineterminator="\n")
                writer.writerow(COLUMNS)
                previous = None
                while True:
                    record = incoming.read(RECORD_BYTES)
                    if not record:
                        break
                    if len(record) < RECORD_BYTES:
                        stats["trailing_bytes"] = len(record)
                        stats["warnings"].append("Incomplete final record ignored; earlier records validated")
                        break
                    ms, *values = struct.unpack("<I7hHBBH", record)
                    accel, gyro = values[:3], values[3:6]
                    temp, battery, activity, flags, crc = values[6:]
                    invalid = (crc != binascii.crc_hqx(record[:22], 0xffff) or flags & ~1 or
                               (previous is not None and ms <= previous))
                    if invalid:
                        if not recover_prefix:
                            raise ValueError(f"Invalid record {stats['records']}; use --recover-prefix to export only the intact prefix")
                        stats["recovered_prefix"] = True
                        stats["warnings"].append(f"Stopped before damaged record {stats['records']}; later bytes not exported")
                        break
                    a = [x * 0.000122 for x in accel]
                    g = [x * 0.0175 for x in gyro]
                    writer.writerow([ms, *[f"{x:.6f}" for x in a], *[f"{x:.4f}" for x in g],
                                     f"{25 + temp / 256:.4f}", f"{math.sqrt(sum(x*x for x in a)):.6f}",
                                     f"{activity / 255:.6f}", f"{battery / 1000:.3f}",
                                     "Active" if flags & 1 else "Resting"])
                    stats["records"] += 1
                    stats["last_elapsed_ms"] = ms
                    previous = ms
        os.replace(temporary, destination)
        temporary = None
        return stats
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--recover-prefix", action="store_true",
                        help="Explicitly export only intact records before the first damaged record")
    args = parser.parse_args()
    try:
        result = convert(args.input, args.output, args.recover_prefix)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
