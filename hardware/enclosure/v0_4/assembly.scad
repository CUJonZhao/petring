// v0.4 mesh assembly preview. Editable inputs: design_inputs.json.
// Fit-test geometry; physical validation required
show_lid=false;
import("delta_collar_v0_4_base.stl");
if(show_lid) color([0.2,0.7,0.6,0.4])
    translate([-1.9000000000000001,67.15,22.96]) rotate([180,0,0])
        import("delta_collar_v0_4_lid.stl");
%color([0.2,0.5,0.9,0.35]) translate([3.6,3.6,3.0])
    cube([52.05,22.8,16.36]);
%color([0.9,0.65,0.2,0.4]) translate([3.6,29.4,2.0])
    cube([35.9,32.25,4.8]);
%color([0.8,0.4,0.2,0.4]) translate([42.0,28.0,2.0])
    import("../delta_collar_v0_3_cable_guide_27mm.stl");
