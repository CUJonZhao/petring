# Delta Rest & Activity Smart Collar Prototype

This repository contains the working files for a Delta-first smart collar prototype.

The current engineering goal is Stage 1: build a comfortable wearable prototype for Delta, a 4-month-old Sheltie, that streams IMU-based rest/activity data wirelessly from an ESP32 Feather/HUZZAH32 V2 to a browser dashboard on a computer.

## Current Stage

Current status: Stage 1B bench and miniaturization preparation.

Stage 1A hardware bring-up is complete. The ESP32 Feather/HUZZAH32 V2,
LSM6DSOX IMU, LiPo battery path, Wi-Fi dashboard, enclosed USB bench test,
enclosed battery-only bench test, and four-minute hand-motion calibration have
all passed. The first dog-worn test is intentionally deferred because the
current enclosure is larger than desired for Delta.

Stage 1B focuses on:

- Longer battery-only bench runtime testing.
- Full-resolution data capture and automatic summary plots.
- Activity/rest threshold review from repeatable bench and hand-motion tests.
- Smaller 3D-printable enclosure planning.
- Dog-worn testing only after the smaller enclosure passes dry fit, enclosed
  USB, enclosed battery, and motion calibration checks.

Stage 1 intentionally does not include medical diagnosis, production waterproofing, phone app deployment, GPS/LTE, or validated heart/respiration measurement.

## Next Work

Recommended next steps:

1. Run a 1-hour battery-only bench runtime test with full CSV capture.
2. Add or use tooling that saves complete test data and generates plots.
3. Measure the Feather, LiPo, IMU, JST switch, cable bends, and collar geometry
   for a smaller 3D-printed enclosure.
4. Draft the first smaller enclosure concept with flat LiPo placement, cable
   strain relief, accessible switch, and a soft dog-facing side.

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
