#!/usr/bin/env python3
"""Redraw the 2026-09-11 figures from the committed summaries.

    python3 experiments/plot_2026-09-11.py

Reads experiments/results/gait_calibration_2026-09-11.json and
tuning_2026-09-11.json, writes docs/figures/. Raw recordings stay local; the
summaries carry everything these figures need.
"""
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'experiments/results'
FIGURES = ROOT / 'docs/figures'
# Rest -> walk -> run is ordered by intensity, so one hue in three steps rather
# than three unrelated colours: no colour-vision pair to confuse. Gaps get the
# amber used elsewhere in this repository plus a label, never colour alone.
STATE = {'rest': '#d7e6df', 'walk': '#7fb3a0', 'run': '#2d685a', 'uncovered': '#f2a04a'}
# Figure labels stay English, like the existing figures in docs/figures.
STATE_EN = {'rest': 'rest', 'walk': 'walk', 'run': 'run', 'uncovered': 'sampling gap'}
INK, MUTED, GRID = '#1d2a2c', '#5c706b', '#e0e7e3'


def calibration(data):
    windows = data['windows']
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(11, 6.8), gridspec_kw={'height_ratios': [3, 2]})
    for w in windows:
        top.axvspan(w['t'] / 60, (w['t'] + 2) / 60, color=STATE[w['state']],
                    alpha=1 if w['state'] != 'uncovered' else .8, linewidth=0)
    covered = [w for w in windows if w['mad'] is not None]
    top.plot([w['t'] / 60 for w in covered], [w['mad'] for w in covered], color=INK, linewidth=1.6)
    for start, end, label in data['labels_s']:
        top.annotate('', xy=(start / 60, 640), xytext=(end / 60, 640),
                     arrowprops=dict(arrowstyle='|-|', color=MUTED, linewidth=1))
        top.text((start + end) / 120, 660, 'labelled ' + STATE_EN[label], color=MUTED,
                 fontsize=9, ha='center')
    top.set_ylim(0, 700)
    top.set_ylabel('MAD (mg)')
    top.set_xlabel('minutes')
    top.set_title('Indoor calibration session ce940dee: shading is the classified state, brackets are the labels', color=INK)
    # Below the panel: inside it the legend covered the label brackets.
    top.legend(handles=[Patch(facecolor=STATE[k], label=STATE_EN[k]) for k in STATE],
               loc='upper center', bbox_to_anchor=(.5, -.22), ncol=4, fontsize=9, frameon=False)

    labels = data['per_label']
    positions = []
    for i, (name, stats) in enumerate(labels.items()):
        mad = stats['mad_mg']
        bottom.barh(i, mad['p90'] - mad['p10'], left=mad['p10'], height=.42,
                    color=STATE[name], edgecolor='white', linewidth=2)
        bottom.plot([mad['median']], [i], marker='|', color=INK, markersize=18, markeredgewidth=2)
        bottom.text(mad['p90'] * 1.15, i, 'p10 %.1f · median %.1f · p90 %.1f  (%d windows)'
                    % (mad['p10'], mad['median'], mad['p90'], stats['windows']),
                    va='center', fontsize=9, color=MUTED)
        positions.append(STATE_EN[name])
    boundary = data['thresholds']['rest_max_mad_mg']
    bottom.axvline(boundary, color='#c4582b', linewidth=1.6, linestyle='--')
    bottom.text(boundary * 1.1, .5, 'threshold %.0f mg' % boundary, color='#c4582b', fontsize=9, va='center')
    bottom.set_xscale('log')
    bottom.set_yticks(range(len(positions)))
    bottom.set_yticklabels(positions)
    bottom.set_xlim(.5, 2600)
    bottom.set_xlabel('MAD (mg, log scale)')
    bottom.set_title('About 25x apart; all %d labelled windows agreed'
                     % data['agreement']['labelled_windows'], color=INK, fontsize=11)
    for axis in (top, bottom):
        axis.grid(axis='x', color=GRID)
        axis.set_axisbelow(True)
        for side in ('top', 'right'):
            axis.spines[side].set_visible(False)
    figure.tight_layout()
    out = FIGURES / 'gait_calibration_2026-09-11.png'
    figure.savefig(out, dpi=140)
    figure.savefig(out.with_suffix('.svg'))
    return out


def tuning(data):
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6))
    runs = data['sampling']
    # The uncovered share rides in the tick label: inside the bars it was clipped.
    names = ['%s\n%.1f%% uncovered' % (r['label'], r['uncovered_percent']) for r in runs]
    left.bar(range(len(runs)), [r['mean_hz'] for r in runs], color=['#b8c6c2'] + ['#2d685a'] * (len(runs) - 1),
             width=.62, edgecolor='white', linewidth=2)
    for i, run in enumerate(runs):
        left.text(i, run['mean_hz'] + .35, '%.2f Hz' % run['mean_hz'], ha='center', fontsize=9, color=INK)
    left.axhline(20, color=MUTED, linewidth=1, linestyle=':')
    left.text(-.45, 20.3, '20 Hz target', fontsize=8.5, color=MUTED, ha='left')
    left.set_xticks(range(len(runs)))
    left.set_xticklabels(names, fontsize=8, rotation=16, ha='right')
    left.set_ylim(0, 22)
    left.set_ylabel('measured mean rate (Hz)')
    left.set_title('Sampling: after the per-flush filesystem walk was removed', color=INK, fontsize=11)

    requests = data['request_ms']
    colors = ['#b8c6c2', '#b8c6c2', '#2d685a', '#8fa8b8']
    right.barh(range(len(requests)), [r['value'] for r in requests], color=colors,
               height=.6, edgecolor='white', linewidth=2)
    for i, item in enumerate(requests):
        right.text(item['value'] + 90, i, '%d ms' % item['value'], va='center', fontsize=9, color=INK)
    right.set_yticks(range(len(requests)))
    right.set_yticklabels([r['label'] for r in requests], fontsize=9)
    right.invert_yaxis()
    right.set_xlim(0, 5600)
    right.set_xlabel('main-loop stall per upload request (ms)')
    estimate = data['upload_estimate_min']
    right.set_title('Upload: an hour of recording, ~%.1f min to ~%.1f min'
                    % (estimate['before'], estimate['after']), color=INK, fontsize=11)
    for axis, direction in ((left, 'y'), (right, 'x')):
        axis.grid(axis=direction, color=GRID)
        axis.set_axisbelow(True)
        for side in ('top', 'right'):
            axis.spines[side].set_visible(False)
    figure.tight_layout()
    out = FIGURES / 'tuning_2026-09-11.png'
    figure.savefig(out, dpi=140)
    figure.savefig(out.with_suffix('.svg'))
    return out


def main():
    plt.rcParams['axes.unicode_minus'] = False
    FIGURES.mkdir(parents=True, exist_ok=True)
    print(calibration(json.loads((RESULTS / 'gait_calibration_2026-09-11.json').read_text())))
    print(tuning(json.loads((RESULTS / 'tuning_2026-09-11.json').read_text())))


if __name__ == '__main__':
    main()
