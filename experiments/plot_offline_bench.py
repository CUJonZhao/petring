#!/usr/bin/env python3
"""Plot the published, aggregated USB-bench evidence. Raw logs stay local.

Default: regenerate figures from the committed summary JSON.
--csv PATH --result PATH: regenerate that summary from local bench evidence.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / 'experiments/results/offline_usb_bench_2026-09-09_summary.json'


def aggregate(csv_path, result_path):
    result = json.loads(result_path.read_text())
    with csv_path.open() as incoming:
        rows = list(csv.DictReader(incoming))
    times = [int(r['elapsed_ms']) for r in rows]
    assert len(rows) == result['records']
    assert times[-1] == result['duration_ms']
    assert all(b > a for a, b in zip(times, times[1:]))
    intervals = [b - a for a, b in zip(times, times[1:])]
    events = {e['event']: e for e in result['events']}
    started = events['recording_started']['host_unix']
    binned = []
    cursor = 0
    for end in range(1000, times[-1] + 1000, 1000):
        end = min(end, times[-1])
        first = cursor
        while cursor < len(times) and times[cursor] <= end:
            cursor += 1
        diffs = [times[i] - times[i-1] for i in range(max(1, first), cursor)]
        binned.append({'end_ms': end, 'cumulative_samples': cursor,
                       'samples_in_bin': cursor-first,
                       'max_interval_ms': max(diffs, default=0),
                       'intervals_over_100ms': sum(d > 100 for d in diffs)})
    assert binned[-1]['cumulative_samples'] == result['records']
    return {
        'schema_version': 1, 'date': '2026-09-09', 'timezone': 'America/New_York',
        'source': 'Real ESP32 USB bench; synthetic data is excluded',
        'session_id': result['session_id'], 'duration_ms': times[-1],
        'records': result['records'], 'effective_hz': result['effective_hz'],
        'interval_ms': result['interval_ms'],
        'intervals_over_100ms_total_ms': sum(d for d in intervals if d > 100),
        'initial_uncovered_ms': times[0],
        'uncovered_ms_for_dashboard': times[0] + sum(d for d in intervals if d > 100),
        'temperature_c': result['temperature_c'], 'binary_bytes': result['binary_bytes'],
        'raw_binary_sha256': result['sha256'],
        'source_csv_sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        'csv_binary_agree': result['csv_binary_agree'],
        'wifi_off_recording': result['wifi_off_recording'],
        'restart_identical_completed_file': result['reset_identical_completed_file'],
        'interrupted_recovered_records': result['interrupted_recovered_records'],
        'old_battery_rows_preserved': result['old_battery_rows'],
        'wifi_off_command_s': round(events['wifi_disabled']['host_unix'] - started, 3),
        'wifi_reconnected_confirmation_s': round(events['wifi_reconnected']['host_unix'] - started, 3),
        'radio_band_note': 'Command off to confirmed reconnection; includes reconnection delay. Event times are host-relative, within request latency of device-relative sample times.',
        'serial_errors': result['serial_errors'], 'limitations': result['limitations'],
        'bins': binned,
    }


def plot(data):
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10,
                         'axes.spines.top':False, 'axes.spines.right':False,
                         'svg.hashsalt':'delta-offline-bench-20260909'})
    fig, axes = plt.subplots(2, 1, figsize=(11.2, 7.3), sharex=True)
    fig.patch.set_facecolor('#f5f8f6')
    fig.subplots_adjust(top=.78, bottom=.19, left=.10, right=.96, hspace=.42)
    fig.text(.10, .945, 'DELTA  /  REAL DEVICE USB BENCH', color='#47645b', size=11, weight='bold')
    fig.text(.10, .895, 'Offline recording works; sampling timing needs refinement',
             color='#1e3d32', size=17, weight='bold')
    fig.text(.10, .841, f"{data['records']:,} samples  |  {data['duration_ms']/1000:.3f} s  |  "
             f"{data['effective_hz']:.2f} Hz average  |  CSV / binary / restart checks passed", color='#365547', size=11)
    x = [b['end_ms']/1000 for b in data['bins']]
    for ax in axes:
        ax.set_facecolor('white')
        ax.axvspan(data['wifi_off_command_s'], data['wifi_reconnected_confirmation_s'],
                   color='#dcece2', zorder=0)
        ax.grid(axis='y', color='#e5eae7', lw=.7)
        ax.set_xlim(0,121)
        ax.spines['left'].set_color('#a2b7ac')
        ax.spines['bottom'].set_color('#a2b7ac')
    axes[0].plot([0]+x, [0]+[b['cumulative_samples'] for b in data['bins']], color='#27634d', lw=2.3)
    axes[0].set_ylabel('Cumulative samples in saved file')
    axes[0].set_ylim(0,2600)
    axes[0].text(.02,.89,'A   Data continues while Wi-Fi is unavailable', transform=axes[0].transAxes, color='#284f3e', weight='bold')
    axes[0].text(62,185,'Wi-Fi off / reconnecting', ha='center', size=10, color='#365c46')
    axes[0].annotate(f"{data['records']:,}", xy=(x[-1],data['records']), xytext=(-4,10),
                     textcoords='offset points', ha='right', color='#27634d', weight='bold')
    peaks = [b['max_interval_ms'] for b in data['bins']]
    colors = ['#b35732' if n>100 else '#819d8d' for n in peaks]
    axes[1].bar(x, peaks, width=.72, color=colors, zorder=3)
    axes[1].axhline(50,color='#27634d',lw=1.2,ls='--',label='50 ms target',zorder=4)
    axes[1].axhline(100,color='#ae623d',lw=1,ls=':',label='100 ms gap threshold',zorder=4)
    axes[1].set_ylim(0,450)
    axes[1].set_ylabel('Longest interval per 1 s bin (ms)')
    axes[1].set_xlabel('Elapsed time (s)')
    axes[1].text(.02,.89,'B   Flash writes introduce timing gaps', transform=axes[1].transAxes, color='#704430', weight='bold')
    axes[1].legend(loc='lower right',bbox_to_anchor=(1,1.03),ncol=2,frameon=False,fontsize=9)
    fig.text(.10,.035,'54 intervals >100 ms; longest 387 ms. The dashboard excludes 7.23 s from activity totals.\n'
             'USB power + EN reset only. One-hour battery runtime and physical power-cut recovery are not yet verified.',
             color='#52685c',size=9,linespacing=1.5)
    prefix=ROOT/'docs/figures/offline_usb_bench_2026-09-09'
    prefix.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(prefix.with_suffix('.png'),dpi=160,facecolor=fig.get_facecolor())
    svg_path = prefix.with_suffix('.svg')
    fig.savefig(svg_path,metadata={'Date':None},facecolor=fig.get_facecolor())
    # Matplotlib adds trailing spaces inside path data; keep generated diffs clean.
    svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines()) + '\n')
    plt.close(fig)
    print(prefix.with_suffix('.png'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path)
    parser.add_argument('--result',type=Path)
    args=parser.parse_args()
    if bool(args.csv) != bool(args.result): parser.error('Supply both --csv and --result')
    if args.csv:
        data=aggregate(args.csv,args.result)
        SUMMARY.parent.mkdir(parents=True,exist_ok=True)
        SUMMARY.write_text(json.dumps(data,indent=2)+'\n')
    else:
        data=json.loads(SUMMARY.read_text())
    plot(data)


if __name__=='__main__': main()
