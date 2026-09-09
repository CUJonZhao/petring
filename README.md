# Delta Rest & Activity Smart Collar Prototype

This repository contains the working files for a Delta-first smart collar prototype.

The current engineering goal is Stage 1: build a comfortable wearable prototype for Delta, a Sheltie, that streams IMU-based rest/activity data wirelessly from an ESP32 Feather/HUZZAH32 V2 to a browser dashboard on a computer.

**Resume here (2026-09-09):** [Stage 1B handoff / 当前工作交接](docs/2026-09-09_stage1b_handoff.md).
The v0.4 base and lid are ready for slicing and dry-fit printing. The user plans
to print; completion and physical fit have not yet been reported.

- [Current print package](hardware/enclosure/print_packages/delta_collar_v0_4_fit_print_20260909.zip)
- [Base/lid instructions](hardware/enclosure/v0_4/README.md)
- [Placement and cable-routing image](hardware/enclosure/v0_4/placement_routing.png)

## Current Stage

Current status: Stage 1B enclosure printing and dry-fit preparation.

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

As of 2026-09-06, a 3D printer has arrived and enclosure CAD work has
started. See
`docs/2026-09-06_stage1b_printer_arrival_and_enclosure_kickoff.md` and the
starting model in `hardware/enclosure/delta_collar_enclosure_v1.scad`.

As of 2026-09-08, the calipers have arrived and GitHub changes through
`7b54d0d` have been synced locally. Measured dimensions now feed a v0.3 low-wall
tray for powerless fit checks; see `hardware/enclosure/README.md`.
The first Feather, detached IMU, battery, and mounting-hole measurements are
recorded in `docs/2026-09-08_stage1b_caliper_measurements.md`. Hole-edge references
and the USB-inclusive length are confirmed, and mounting coordinates are derived.
Switch dimensions are recorded; the current preference is to mount it externally,
reserving cable exits and strain relief rather than internal switch space.
Underside and IMU slide-fit photos are archived. The user clarified that
19.59 mm measures the metal-pin gap, excluding the inward-projecting plastic
header bodies; the earlier usable-width estimate is withdrawn. The IMU can be
slid in from the side. The user confirms firm mechanical retention with no glue
or insulating layer, and an unchanged assembled height of 16.36 mm. Electrical
isolation and retention under motion remain to be verified; right-hand mounting
access was subsequently confirmed by the user on September 9.
A two-minute USB serial observation of this assembly then captured 2,370 samples
at 19.98 Hz with no firmware errors or post-startup resets. IMU temperature ranged
from 29.08 to 31.45 C. The user confirmed the battery was disconnected and reported
no physical anomalies during capture. See
`experiments/usb_slide_fit_2min_2026-09-08.md`; this is a short functional check,
not completion of enclosure, insulation, or wearability validation.

As of 2026-09-09, the user has printed the v0.3 tray and confirmed that the
board assembly and battery fit side by side with spare space. A removable
two-post cable guide (20 x 27 x 9 mm, shortened after the user's space check)
is being printed for the long leads; see
`docs/2026-09-09_stage1b_tray_fit_and_cable_routing.md`. A v0.4 base and separate
lid now include four support posts, USB access, and a lay-in switch-wire exit.
The actual plug housing is 8.95 x 3.30 mm; the combined wire envelope is
3.32 x 1.59 mm, and the user confirms the IMU leaves the right holes accessible.
The battery plug's hard plastic projects 1.06 mm beyond the PCB edge, leaving
about 0.94 mm of nominal wall clearance; its raised wire bend needs a lid fit check.
See `hardware/enclosure/v0_4/README.md` for both STLs and fit instructions.
Mesh and nominal collision checks pass. Slicing, screw fit, cable routing and
lid fit remain to be validated physically; M2 fasteners are not yet confirmed.

Stage 1 intentionally does not include medical diagnosis, production waterproofing, phone app deployment, GPS/LTE, or validated heart/respiration measurement.

## Next Work

Recommended next steps:

1. Complete the current 20 x 27 x 9 mm cable-guide print and try it in the spare
   area beside the battery with power disconnected.
   Route internal slack loosely around the two posts; leave external switch
   leads for external fastening. Confirm routing before attaching the guide
   to the existing tray using the available foam tape, and record top/side photos.
2. Import both v0.4 base and lid STLs, verify dimensions/orientation, slice and
   print. Check all four post positions, the USB insertion path, the complete
   wire bundle in its slot, and the lid fit without compressing components.
3. Fit appropriate M2 fasteners and complete battery retention, external switch
   mounting, cable strain relief and collar attachment. Resolve board-to-board
   electrical isolation and retention before completing powered enclosure tests.
4. Repeat the dry fit / enclosed USB / enclosed battery / motion calibration
   sequence before any dog-worn test. The one-hour battery run, full capture
   of that run, and summary plotting remain pending.

## Repository Layout

- `docs/` - proposals, purchase/build notes, and PDF generation script.
- `firmware/` - ESP32 firmware will live here.
- `hardware/` - wiring notes, enclosure sketches, hardware photos/diagrams, and enclosure CAD (OpenSCAD) starting point in `hardware/enclosure/`.
- `experiments/` - experiment plans and observation logs.
- `data/raw/` - raw CSV/log captures, ignored by Git except `.gitkeep`.
- `data/processed/` - processed analysis outputs, ignored by Git except `.gitkeep`.

## Key Documents

- `docs/canine_resting_vitals_smart_collar_proposal_v3_delta_first.md`
- `docs/canine_resting_vitals_smart_collar_proposal_v3_delta_first.pdf`
- `docs/stage1_purchase_and_build_notes.md`
- `docs/2026-08-12_stage1_handoff.md`
- `docs/2026-08-14_stage1_enclosure_bench_and_calibration.md`
- `docs/2026-09-06_stage1b_printer_arrival_and_enclosure_kickoff.md`
- `docs/2026-09-08_stage1b_caliper_measurements.md`
- `docs/2026-09-09_stage1b_tray_fit_and_cable_routing.md`
- `docs/2026-09-09_stage1b_handoff.md`
- `experiments/usb_slide_fit_2min_2026-09-08.md`
- `hardware/enclosure/README.md`

## Safety Note

This is an engineering prototype, not a veterinary diagnostic device. During early tests, Delta should be supervised, the battery should not be compressed or exposed, and charging should not be left unattended.
