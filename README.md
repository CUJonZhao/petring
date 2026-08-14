# Delta Rest & Activity Smart Collar Prototype

This repository contains the working files for a Delta-first smart collar prototype.

The current engineering goal is Stage 1: build a comfortable wearable prototype for Delta, a 4-month-old Sheltie, that streams IMU-based rest/activity data wirelessly from an ESP32 Feather/HUZZAH32 V2 to a browser dashboard on a computer.

## Current Stage

Stage 1 focuses on:

- ESP32 Feather/HUZZAH32 V2 as the controller.
- Adafruit LSM6DSOX IMU as the primary motion sensor.
- 3.7 V 500 mAh Adafruit LiPo battery for untethered testing.
- Wi-Fi streaming to a local browser dashboard.
- CSV logging for short experiments of a few hours.
- Comfort-first collar mounting using a small project box, foam padding, and removable hook-and-loop straps.

Stage 1 intentionally does not include medical diagnosis, production waterproofing, phone app deployment, GPS/LTE, or validated heart/respiration measurement.

## Repository Layout

- `docs/` - proposals, purchase/build notes, and PDF generation script.
- `firmware/` - ESP32 firmware will live here.
- `hardware/` - wiring notes, enclosure sketches, and hardware photos/diagrams will live here.
- `experiments/` - experiment plans and observation logs.
- `data/raw/` - raw CSV/log captures, ignored by Git except `.gitkeep`.
- `data/processed/` - processed analysis outputs, ignored by Git except `.gitkeep`.

## Key Documents

- `docs/canine_resting_vitals_smart_collar_proposal_v3_delta_first.md`
- `docs/canine_resting_vitals_smart_collar_proposal_v3_delta_first.pdf`
- `docs/stage1_purchase_and_build_notes.md`
- `docs/2026-08-12_stage1_handoff.md`
- `docs/2026-08-14_stage1_enclosure_bench_and_calibration.md`

## Safety Note

This is an engineering prototype, not a veterinary diagnostic device. During early tests, Delta should be supervised, the battery should not be compressed or exposed, and charging should not be left unattended.
