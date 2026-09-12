#!/usr/bin/env python3
"""Time budget (rest / walk / run) and a relative activity index for one session.

Input is a session recorded by the collar: the raw .bin (downloaded from the
board or the site) or an exported .csv. Nothing here measures energy: the
activity index is MAD (mean amplitude deviation of the acceleration magnitude)
in milli-g, comparable between sessions of the same device and mounting
position, and not calories. ENMO is reported too, for comparison with the human
accelerometry literature, but at 20 Hz MAD separates movement far better: on a
desk bench, handling the board showed MAD about 100 mg against 0.7 mg at rest,
while mean ENMO stayed under 30 mg for both.

  python3 experiments/gait_analysis.py data/raw/.../session.bin --plot out.png

Thresholds are placeholders until they are calibrated against labelled data:

  python3 experiments/gait_analysis.py session.bin --labels labels.csv --suggest

where labels.csv holds "start,end,label" rows, times either in seconds from the
start of the session or as HH:MM:SS wall clock (needs a session start time),
and label is one of rest/walk/run.
"""
import argparse
import csv
import importlib.util
import json
import math
import statistics
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW_S = 4.0
HOP_S = 2.0
MIN_COVERAGE = 0.6          # a window with more gap than this is not classified
MAX_INTERPOLATION_MS = 250  # never interpolate across a longer sampling gap
BAND_HZ = (0.5, 5.0)        # canine/human stride fundamentals live here
CLASSES = ("rest", "walk", "run")
# Placeholders. Replace from --suggest output once labelled data exists.
DEFAULT_THRESHOLDS = {"rest_max_mad_mg": 40.0, "run_min_mad_mg": 450.0,
                      "run_stride_hz": 2.6, "run_stride_min_mad_mg": 250.0}


def load_samples(path: Path):
    """Return (times_s, accel_g, gyro_dps, battery_v) from a .bin or .csv."""
    if path.suffix == ".bin":
        spec = importlib.util.spec_from_file_location("decoder", ROOT / "experiments/decode_motion_log.py")
        decoder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(decoder)
        out = Path(tempfile.mkdtemp()) / "session.csv"
        info = decoder.convert(path, out)
        rows, started = list(csv.DictReader(out.open())), info.get("start_unix_ms")
    else:
        rows, started = list(csv.DictReader(path.open())), None
    if not rows:
        raise SystemExit("no samples in " + str(path))
    # Session exports use elapsed_ms; the serial capture scripts use device_ms.
    time_key = next((k for k in ("elapsed_ms", "ms", "device_ms", "host_elapsed_s") if k in rows[0]), None)
    if not time_key:
        raise SystemExit("no time column in " + str(path))
    scale = 1.0 if time_key == "host_elapsed_s" else 1000.0
    times, accel, gyro, battery = [], [], [], []
    for row in rows:
        times.append(float(row[time_key]) / scale)
        accel.append(tuple(float(row[k]) for k in ("ax_g", "ay_g", "az_g")))
        gyro.append(tuple(float(row[k]) for k in ("gx_dps", "gy_dps", "gz_dps")))
        if row.get("battery_v"):
            battery.append(float(row["battery_v"]))
    return times, accel, gyro, battery, started


def dominant_frequency(magnitudes, rate):
    """Strongest frequency in the stride band, plus how much power it holds."""
    n = len(magnitudes)
    mean = sum(magnitudes) / n
    # Hann window keeps a single stride peak from smearing across bins.
    signal = [(v - mean) * (0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1))) for i, v in enumerate(magnitudes)]
    best, band_power = (0.0, 0.0), 0.0
    steps = max(1, int(n * (BAND_HZ[1] - BAND_HZ[0]) / rate * 4))  # 4x zero-padding resolution
    for step in range(steps + 1):
        freq = BAND_HZ[0] + (BAND_HZ[1] - BAND_HZ[0]) * step / steps
        angle = 2 * math.pi * freq / rate
        real = sum(v * math.cos(angle * i) for i, v in enumerate(signal))
        imag = sum(v * math.sin(angle * i) for i, v in enumerate(signal))
        power = real * real + imag * imag
        band_power += power
        if power > best[1]:
            best = (freq, power)
    return best[0], (best[1] / band_power if band_power else 0.0)


def windows(times, accel, gyro, rate=20.0):
    """Feature rows for overlapping windows, skipping poorly covered ones."""
    rows, start, end = [], times[0], times[-1]
    index = 0
    while start + WINDOW_S <= end + HOP_S:
        stop = start + WINDOW_S
        while index and times[index - 1] >= start:
            index -= 1
        while index < len(times) and times[index] < start:
            index += 1
        take = index
        chunk_t, chunk_a, chunk_g = [], [], []
        while take < len(times) and times[take] < stop:
            chunk_t.append(times[take])
            chunk_a.append(accel[take])
            chunk_g.append(gyro[take])
            take += 1
        expected = WINDOW_S * rate
        coverage = len(chunk_t) / expected
        row = {"start_s": round(start, 2), "coverage": round(coverage, 3)}
        if coverage >= MIN_COVERAGE:
            magnitude = [math.sqrt(x * x + y * y + z * z) for x, y, z in chunk_a]
            mean_magnitude = sum(magnitude) / len(magnitude)
            row["mad_mg"] = round(1000 * sum(abs(m - mean_magnitude) for m in magnitude) / len(magnitude), 1)
            row["enmo_mg"] = round(1000 * sum(max(0.0, m - 1.0) for m in magnitude) / len(magnitude), 1)
            row["gyro_dps"] = round(sum(math.sqrt(a * a + b * b + c * c) for a, b, c in chunk_g) / len(chunk_g), 1)
            # Resample onto an even grid so the transform sees constant spacing.
            grid, values, cursor = [], [], 0
            steps = int(WINDOW_S * rate)
            for step in range(steps):
                moment = start + step / rate
                while cursor + 1 < len(chunk_t) and chunk_t[cursor + 1] < moment:
                    cursor += 1
                if cursor + 1 >= len(chunk_t):
                    break
                span = chunk_t[cursor + 1] - chunk_t[cursor]
                if span * 1000 > MAX_INTERPOLATION_MS:
                    continue
                weight = (moment - chunk_t[cursor]) / span if span else 0.0
                values.append(magnitude[cursor] + weight * (magnitude[cursor + 1] - magnitude[cursor]))
                grid.append(moment)
            if len(values) >= steps * MIN_COVERAGE:
                stride, periodicity = dominant_frequency(values, rate)
                row["stride_hz"] = round(stride, 2)
                row["periodicity"] = round(periodicity, 3)
        rows.append(row)
        start += HOP_S
    return rows


def classify(rows, thresholds):
    for row in rows:
        if "mad_mg" not in row:
            row["class"] = "uncovered"
            continue
        mad, stride = row["mad_mg"], row.get("stride_hz", 0.0)
        if mad < thresholds["rest_max_mad_mg"]:
            row["class"] = "rest"
        elif mad >= thresholds["run_min_mad_mg"] or (
                stride >= thresholds["run_stride_hz"] and mad >= thresholds["run_stride_min_mad_mg"]):
            row["class"] = "run"
        else:
            row["class"] = "walk"
    # Median of three neighbours: a single window never flips the time budget.
    smoothed = [row["class"] for row in rows]
    for i in range(1, len(rows) - 1):
        window = [smoothed[i - 1], rows[i]["class"], smoothed[i + 1]]
        if window[0] == window[2] != window[1] and "uncovered" not in window:
            rows[i]["class"] = window[0]
    return rows


def summarize(rows, times, battery):
    covered = [row for row in rows if row["class"] != "uncovered"]
    budget = {name: round(HOP_S * sum(1 for row in covered if row["class"] == name), 1) for name in CLASSES}
    active = [row["mad_mg"] for row in covered]
    summary = {
        "duration_s": round(times[-1] - times[0], 1),
        "samples": len(times),
        "mean_rate_hz": round(len(times) / max(times[-1] - times[0], 1e-9), 2),
        "seconds_by_class": budget,
        "uncovered_s": round(HOP_S * sum(1 for row in rows if row["class"] == "uncovered"), 1),
        "activity_index_mad_mg": round(statistics.mean(active), 1) if active else None,
        "activity_index_enmo_mg": round(statistics.mean([r["enmo_mg"] for r in covered]), 1) if covered else None,
        "activity_index_note": "mean MAD in milli-g over classified time; relative, not calories",
        "moving_fraction": round((budget["walk"] + budget["run"]) / max(sum(budget.values()), 1e-9), 3),
    }
    if battery:
        summary["battery_v"] = {"start": round(battery[0], 3), "end": round(battery[-1], 3),
                                "drop_mv": round(1000 * (battery[0] - battery[-1]))}
    return summary


def read_labels(path: Path, started_ms):
    labels = []
    for row in csv.reader(path.open()):
        if not row or row[0].lstrip().startswith("#"):
            continue
        start, end, name = row[0].strip(), row[1].strip(), row[2].strip()

        def moment(value):
            if ":" not in value:
                return float(value)
            if not started_ms:
                raise SystemExit("clock times need a session with a start time; use seconds instead")
            base = datetime.fromtimestamp(started_ms / 1000)
            stamp = datetime.strptime(value, "%H:%M:%S").replace(year=base.year, month=base.month, day=base.day)
            return (stamp - base).total_seconds()

        labels.append((moment(start), moment(end), name))
    return labels


def calibrate(rows, labels):
    """Per-label feature spread, and thresholds that separate the labels."""
    groups = {}
    for row in rows:
        if "mad_mg" not in row:
            continue
        middle = row["start_s"] + WINDOW_S / 2
        for start, end, name in labels:
            if start <= middle < end:
                groups.setdefault(name, []).append(row)
                break
    report = {}
    for name, group in sorted(groups.items()):
        mad = sorted(r["mad_mg"] for r in group)
        stride = sorted(r.get("stride_hz", 0.0) for r in group)
        report[name] = {"windows": len(group),
                        "mad_mg": {"p10": mad[len(mad) // 10], "median": statistics.median(mad),
                                   "p90": mad[min(len(mad) - 1, 9 * len(mad) // 10)]},
                        "stride_hz_median": round(statistics.median(stride), 2)}
    suggestion = {}
    if "rest" in report and "walk" in report:
        suggestion["rest_max_mad_mg"] = round((report["rest"]["mad_mg"]["p90"] + report["walk"]["mad_mg"]["p10"]) / 2, 1)
    if "walk" in report and "run" in report:
        suggestion["run_min_mad_mg"] = round((report["walk"]["mad_mg"]["p90"] + report["run"]["mad_mg"]["p10"]) / 2, 1)
        suggestion["run_stride_hz"] = round((report["walk"]["stride_hz_median"] + report["run"]["stride_hz_median"]) / 2, 2)
    return {"per_label": report, "suggested_thresholds": suggestion,
            "accuracy": accuracy(rows, labels)}


def accuracy(rows, labels):
    matrix, correct, total = {}, 0, 0
    for row in rows:
        if row["class"] == "uncovered":
            continue
        middle = row["start_s"] + WINDOW_S / 2
        for start, end, name in labels:
            if start <= middle < end:
                matrix.setdefault(name, {}).setdefault(row["class"], 0)
                matrix[name][row["class"]] += 1
                correct += name == row["class"]
                total += 1
                break
    return {"labelled_windows": total, "agreement": round(correct / total, 3) if total else None,
            "confusion_label_to_class": matrix}


def plot(rows, times, battery, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"rest": "#8fa8b8", "walk": "#2d685a", "run": "#c4582b", "uncovered": "#f2a04a"}
    figure, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True,
                                gridspec_kw={"height_ratios": [3, 2, 1]})
    for row in rows:
        axes[0].axvspan(row["start_s"] / 60, (row["start_s"] + HOP_S) / 60,
                        color=colors[row["class"]], alpha=0.25 if row["class"] != "uncovered" else 0.5, linewidth=0)
    covered = [r for r in rows if "mad_mg" in r]
    axes[0].plot([r["start_s"] / 60 for r in covered], [r["mad_mg"] for r in covered], color="#1d2a2c", linewidth=1.2)
    axes[0].set_ylabel("MAD (mg)")
    axes[0].set_title("Activity, gait frequency and battery — shading is the classified state")
    # A dominant frequency is only meaningful where the signal is periodic and
    # the board is actually moving; at rest it is noise.
    striding = [r for r in covered if "stride_hz" in r and r["class"] in ("walk", "run")]
    axes[1].scatter([r["start_s"] / 60 for r in striding], [r["stride_hz"] for r in striding],
                    s=[6 + 40 * r["periodicity"] for r in striding], color="#2356d8", alpha=0.6, linewidths=0)
    axes[1].set_ylabel("stride (Hz)")
    axes[1].set_ylim(0, BAND_HZ[1])
    if battery:
        axes[2].plot([t / 60 for t in times[:len(battery)]], battery, color="#5a6a69", linewidth=1)
    axes[2].set_ylabel("battery (V)")
    axes[2].set_xlabel("minutes")
    for axis in axes:
        axis.grid(alpha=0.25)
    handles = [plt.Line2D([], [], color=c, linewidth=8, alpha=0.4, label=n) for n, c in colors.items()]
    axes[0].legend(handles=handles, loc="upper right", ncol=4, fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=130)
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("session", type=Path)
    p.add_argument("--labels", type=Path)
    p.add_argument("--config", type=Path, help="JSON with threshold overrides")
    p.add_argument("--suggest", action="store_true", help="print thresholds that separate the labels")
    p.add_argument("--plot", type=Path)
    p.add_argument("--windows-csv", type=Path)
    a = p.parse_args()
    thresholds = dict(DEFAULT_THRESHOLDS)
    if a.config:
        thresholds.update(json.loads(a.config.read_text()))
    times, accel, gyro, battery, started = load_samples(a.session)
    rows = classify(windows(times, accel, gyro), thresholds)
    report = {"session": a.session.name, "thresholds": thresholds,
              "calibrated": bool(a.config), "summary": summarize(rows, times, battery)}
    if not a.config:
        report["warning"] = "thresholds are placeholders; calibrate with --labels --suggest before trusting the split"
    if a.labels:
        report["calibration"] = calibrate(rows, read_labels(a.labels, started))
        if not a.suggest:
            report["calibration"].pop("suggested_thresholds", None)
    if a.windows_csv:
        fields = ["start_s", "coverage", "mad_mg", "enmo_mg", "gyro_dps", "stride_hz", "periodicity", "class"]
        with a.windows_csv.open("w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        report["windows_csv"] = str(a.windows_csv)
    if a.plot:
        report["plot"] = str(plot(rows, times, battery, a.plot))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
