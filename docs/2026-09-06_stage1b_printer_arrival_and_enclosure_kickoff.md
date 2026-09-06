# Stage 1B Progress Update - 3D Printer Arrival And Enclosure Kickoff - 2026-09-06

This note picks up from `docs/2026-08-14_stage1_enclosure_bench_and_calibration.md`. Read this file at the start of the next working session.

## Status Since Last Update (2026-08-14)

- No firmware or bench-test changes were found since the last enclosure bench report. The larger Zulkit enclosure (90 x 70 x 28 mm) remains the only enclosure that has passed the full bench sequence (powerless dry fit, enclosed USB, enclosed battery, four-minute motion calibration).
- The local working copy currently shows line-ending-only differences (CRLF vs the LF stored in Git) across most tracked text files. No content actually changed; safe to leave alone or normalize later with a `.gitattributes` entry. Not addressed in this update.
- `git pull` could not be verified from the automated assistant session used to write this note (network access to github.com is blocked from that environment). The local `HEAD` (`457c923`, "Update Stage 1B progress in README") matches the last known `origin/main` from the previous session. Run `git pull` from a normal terminal to confirm nothing has changed upstream since 2026-08-14.

## New Milestone

The 3D printer has arrived. This unblocks the "smaller 3D-printed enclosure" step that the 2026-08-14 report identified as the gating item before any dog-worn test.

## Reference Component Dimensions (For Enclosure CAD)

Pulled from public Adafruit product pages. Treat these as a starting point only; verify every value with calipers on the actual parts before finalizing the design. Extra clearance is still needed for soldered headers, the USB-C connector overhang, and cable strain relief.

| Component | Nominal size (L x W x H) | Source |
|---|---|---|
| ESP32 Feather V2 (PID 5400) | 52.3 x 22.8 x 7.2 mm | Adafruit product page |
| LSM6DSOX STEMMA QT breakout (PID 4438) | 25.6 x 17.8 x 4.6 mm | Adafruit product page |
| 3.7 V 500 mAh LiPo (PID 1578) | 36 x 29 x 4.75 mm nominal | Adafruit product page |
| JST-PH 2-pin switch cable, STEMMA QT cables | Not published | Measure directly |

Board height figures above are bare-PCB thickness; add clearance for soldered headers, the USB-C receptacle, and the STEMMA QT connector shrouds on both boards.

## Recommended Next Steps

1. Printer bring-up: run the printer's own first-print / bed-leveling routine and one calibration cube before printing anything functional, since this is a brand-new machine.
2. Measure the real parts with calipers: the Feather (with headers and USB-C seated), the LSM6DSOX breakout, the LiPo, the JST switch body, and the minimum STEMMA QT cable bend radius. Record the actual numbers next to the nominal table above.
3. Decide the internal layout (Feather and LiPo side by side vs. stacked) and update `hardware/enclosure/delta_collar_enclosure_v1.scad` (added in this update) with the measured dimensions.
4. Print a shell-only test (no lid fasteners yet) to check dry fit against the real components before committing to a final version.
5. Re-run the same validation sequence used for the larger enclosure, in order, before any dog-worn test:
   - Powerless dry fit.
   - Enclosed USB bench test, 15 minutes.
   - Enclosed battery-only bench test, 15 minutes.
   - Four-minute motion calibration.
6. Only after all four checks pass, proceed to a short supervised collar-fit test per the existing Safety Limits in the README.

## Files Added In This Update

- `hardware/enclosure/delta_collar_enclosure_v1.scad`: a parametric OpenSCAD starting point for the smaller enclosure, using the nominal dimensions above. Open it in OpenSCAD, adjust the dimension variables at the top after measuring the real parts, and export an STL from there. The current geometry is a placeholder shell with component-outline guides only; it has no lid split line, switch cutout, cable strain relief, or strap slots yet.

## Safety Status

Unchanged from the 2026-08-14 report: this remains an engineering prototype, not a veterinary diagnostic device. No dog-worn testing until the smaller enclosure passes the same bench sequence as the current larger enclosure.

## Same-Day Update: OpenSCAD Verified, Base/Lid Split, Mounting Plan (later on 2026-09-06)

The v0.1 parametric model was rendered and exported in OpenSCAD on the real
machine (2021.01) and loaded correctly in Bambu Studio, confirming the
nominal math above: external shell 63.3 x 59.8 x 21.3 mm, matching the
computed values exactly.

That v0.1 shape turned out to be a fully sealed box (no way to insert
parts). It was replaced with a v0.2 two-part design:

- Base: an open-top tray, 63.3 x 59.8 x 19.3 mm nominal, holding the
  Feather (+ LSM6DSOX taped underneath) and the LiPo.
- Lid: a slip-over skirt cap (like a shoebox lid), 67.9 x 64.4 x 8.0 mm
  nominal, no fasteners or glue, matching the "close it gently, do not force
  it" approach already used for the larger off-the-shelf enclosure. Fit
  clearance between base and lid is a placeholder (0.3 mm per side) to be
  tuned after a real print.

Both parts render and export together from
hardware/enclosure/delta_collar_enclosure_v1.scad and loaded correctly in
Bambu Studio (combined bounding box 141.2 x 64.4 x 19.3 mm, matching base
width + 10 mm gap + lid width).

Mounting plan: the real ESP32 HUZZAH32 Feather V2 has four corner mounting
holes (photographed 2026-09-06), not the header pins. Plan is to add four
printed standoff pegs in the base at the real hole positions, each with an
optional pilot hole down the middle so an M2.5 screw can be added later
without reprinting if a plain press-fit peg does not hold securely enough
under motion. This avoids relying on the 2.54 mm header pins, which are a
poor fit for FDM-printed sockets: tight tolerance, no spring contact, wear
out with repeated insertion.

Open question carried to tomorrow: the header pins are soldered through the
board and may protrude significantly on one side (up to roughly 8-9 mm for
stacking-style long headers) or only a few mm (short solder tails).
feather_header_clearance = 3.0 in the model is an unverified placeholder
and may be too small. Needs a real measurement before the internal height
is trusted.

## Updated Caliper Measurement List For 2026-09-07

In addition to the list earlier in this document, measure and report:

- Header pin protrusion on both sides of the Feather board (solder-tail
  side and mating-pin side).
- The four corner mounting hole diameters and the two center-to-center
  spacings (along the long edge and along the short edge).
