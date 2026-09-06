// delta_collar_enclosure_v1.scad
// Parametric starting point for the Stage 1B smaller 3D-printed enclosure.
// Delta collar project.
// See docs/2026-09-06_stage1b_printer_arrival_and_enclosure_kickoff.md
//
// v0.2 - 2026-09-06: split into a two-part BASE + LID (slip-over skirt lid,
// like a shoebox lid), confirmed after v0.1 rendered correctly in OpenSCAD
// but turned out to be a fully sealed shell with no way to insert parts.
// No fasteners or glue -- matches the "close the lid gently, don't force it"
// approach already used for the larger off-the-shelf enclosure.
//
// Layout (unchanged from v0.1):
//   - LSM6DSOX is mounted to the UNDERSIDE of the Feather (taped back-to-back,
//     matching docs/2026-08-14_stage1_enclosure_bench_and_calibration.md),
//     so it adds to the STACK HEIGHT under the Feather, not to the footprint.
//   - Feather sits at the "top" of the base footprint, LiPo sits beside/below
//     it in the same length-wise lane, both flat on the base floor.
//
// IMPORTANT: all dimensions below are still NOMINAL values pulled from
// public Adafruit product pages, NOT measurements of the actual parts.
// High-precision calipers are arriving 2026-09-07 -- update every variable
// below marked "verify" with the real measurement before finalizing v0.3.
// This v0.2 is still for a physical dry-fit / lid-fit test print, not a
// final assembly: no switch cutout or cable strain relief yet.

// ---------- Component nominal dimensions (mm) ----------
feather_l = 52.3; feather_w = 22.8; feather_h = 7.2; // bare PCB only -- verify
feather_header_clearance = 3.0; // extra height for soldered headers -- verify
feather_usb_overhang = 3.0;     // USB-C connector overhang beyond board edge -- verify

lsm6dsox_l = 25.6; lsm6dsox_w = 17.8; lsm6dsox_h = 4.6; // verify
imu_mount_gap = 1.0; // double-sided tape / standoff gap between Feather underside and IMU -- verify

lipo_l = 36; lipo_w = 29; lipo_h = 4.75; // add roughly 10-15 percent thickness margin -- verify

// JST switch and STEMMA QT cable clearances are not published by Adafruit.
// These are placeholders -- measure the real parts before relying on them.
jst_switch_l = 25; jst_switch_w = 10; jst_switch_h = 6; // verify
cable_bend_clearance = 8; // minimum radius to keep STEMMA QT cable from a sharp bend -- verify

// ---------- Base layout ----------
wall_t = 2.0;              // wall thickness -- tune for your printer/material
board_gap = 4.0;           // gap between the Feather lane and the LiPo lane
headroom = 1.5;            // clear space above the tallest internal stack, below the open top
foam_pad_thickness = 3;    // neoprene foam pad thickness on the dog-facing side (added after printing, not printed)

feather_stack_h = feather_h + feather_header_clearance + imu_mount_gap + lsm6dsox_h;

internal_l = max(feather_l + feather_usb_overhang, lipo_l) + 4; // + margin for cable routing
internal_w = feather_w + board_gap + lipo_w;
internal_h = max(feather_stack_h, lipo_h) + headroom;

base_external_l = internal_l + 2 * wall_t;
base_external_w = internal_w + 2 * wall_t;
base_external_h = internal_h + wall_t; // floor only -- top stays open, lid covers it

echo(str("Base external (approx, mm): ", base_external_l, " x ", base_external_w, " x ", base_external_h));

// ---------- Lid: slips down over the OUTSIDE of the base, like a shoebox lid ----------
lid_fit_clearance = 0.3; // per-side gap so the lid slides over the base -- tune after test fit
lid_skirt_h = 6;         // how far the lid overlaps down over the base wall for grip -- verify feels secure
lid_top_t = wall_t;      // lid top thickness

lid_cavity_l = base_external_l + 2 * lid_fit_clearance;
lid_cavity_w = base_external_w + 2 * lid_fit_clearance;
lid_outer_l = lid_cavity_l + 2 * wall_t;
lid_outer_w = lid_cavity_w + 2 * wall_t;
lid_outer_h = lid_skirt_h + lid_top_t;

echo(str("Lid external (approx, mm): ", lid_outer_l, " x ", lid_outer_w, " x ", lid_outer_h));

// ---------- Shared shape helper ----------
module rounded_box(l, w, h, r) {
    hull() {
        for (x = [r, l - r])
            for (y = [r, w - r])
                translate([x, y, 0])
                    cylinder(r = r, h = h, $fn = 32);
    }
}

// ---------- Base: open-top tray ----------
module base_shell() {
    difference() {
        rounded_box(base_external_l, base_external_w, base_external_h, 3);
        // cavity extends above the top face so the top is fully open
        translate([wall_t, wall_t, wall_t])
            rounded_box(internal_l, internal_w, internal_h + 1, 2);
    }
}

// ---------- Lid: cap with a skirt that slips over the base ----------
module lid_shell() {
    difference() {
        rounded_box(lid_outer_l, lid_outer_w, lid_outer_h, 3);
        // cavity from the bottom up through the skirt height, leaving a solid top cap
        translate([wall_t, wall_t, 0])
            rounded_box(lid_cavity_l, lid_cavity_w, lid_skirt_h + 1, 2);
    }
}

// ---------- Render: base on the left, lid on the right, both flat on the bed ----------
base_shell();

translate([base_external_l + 10, 0, 0])
    lid_shell();

// ---------- Component placement guides on the base (visual dry-fit reference only) ----------
// Feather lane (top of footprint)
%translate([wall_t + 2, wall_t + 2, wall_t + imu_mount_gap + lsm6dsox_h])
    cube([feather_l, feather_w, feather_h]);

// LSM6DSOX taped to the Feather underside -- shown touching the base floor,
// with the Feather sitting on top of it (component-side up). Flip this if
// the real assembly is mounted the other way up.
%translate([wall_t + 2 + (feather_l - lsm6dsox_l) / 2, wall_t + 2 + (feather_w - lsm6dsox_w) / 2, wall_t])
    cube([lsm6dsox_l, lsm6dsox_w, lsm6dsox_h]);

// LiPo lane (below the Feather lane in Y), resting flat on the base floor
%translate([wall_t + 2, wall_t + feather_w + board_gap, wall_t])
    cube([lipo_l, lipo_w, lipo_h]);
