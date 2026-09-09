// v0.3 add-on, 2026-09-09: removable two-post cable guide. Units mm.
// Attach underneath to the tray with existing foam tape after powerless fit.
// Post radius is a design trial, not a verified wire bend-radius specification.
$fn=64;
plate_l=20.0; plate_w=32.0; plate_h=1.2; plate_r=2.0;
core_r=6.0; core_h=6.0; lip_r=7.0;
flare_h=1.0; rim_h=0.4; bevel_h=0.4;
module base() {
    hull() for(x=[plate_r,plate_l-plate_r]) for(y=[plate_r,plate_w-plate_r])
        translate([x,y,0]) cylinder(r=plate_r,h=plate_h);
}
module post() {
    rotate_extrude() polygon([[0,plate_h-0.01],[core_r,plate_h-0.01],
        [core_r,plate_h+core_h],[lip_r,plate_h+core_h+flare_h],
        [lip_r,plate_h+core_h+flare_h+rim_h],
        [lip_r-bevel_h,plate_h+core_h+flare_h+rim_h+bevel_h],
        [0,plate_h+core_h+flare_h+rim_h+bevel_h]]);
}
union() { base(); for(y=[8,24]) translate([10,y,0]) post(); }
