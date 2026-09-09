#!/usr/bin/env python3
"""Build a removable two-post cable guide for the already printed v0.3 tray.

Dependencies: manifold3d, trimesh, numpy, networkx, Pillow. No slicer/printer control.
"""
import importlib.metadata
import json
import math
from pathlib import Path

import manifold3d as md
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
# Revised from 32 mm to 27 mm after the user's physical space measurement.
NAME = 'delta_collar_v0_3_cable_guide_27mm'
L, W, BASE_H, BASE_R = 20.0, 27.0, 1.2, 2.0
CORE_R, CORE_H, LIP_R = 5.0, 6.0, 6.0
FLARE_H, RIM_H, BEVEL_H = 1.0, 0.4, 0.4
CENTERS = [(L/2, 6.5), (L/2, W-6.5)]
SEGMENTS = 64
TOTAL_H = BASE_H + CORE_H + FLARE_H + RIM_H + BEVEL_H
PLACEMENT = (42.0, 28.0)  # from v0.3 tray's outside corner, design proposal only


def preview(mesh):
    im = Image.new('RGB', (1280, 760), '#f7f8fb')
    draw = ImageDraw.Draw(im)
    path = '/System/Library/Fonts/Supplemental/Arial.ttf'
    font = lambda size: ImageFont.truetype(path, size)
    draw.text((45, 30), 'Cable guide add-on for the printed v0.3 tray', font=font(30), fill='#18283e')
    draw.text((45, 79), 'Two flanged posts; prototype routing check, not the finished enclosure.', font=font(20), fill='#54637b')
    draw.rounded_rectangle((28,130,614,690), radius=18, fill='white')
    draw.rounded_rectangle((636,130,1252,690), radius=18, fill='white')
    draw.text((55,153), 'Actual STL geometry', font=font(23), fill='#18283e')
    draw.text((55,186), f'{L:g} x {W:g} x {TOTAL_H:g} mm  |  core diameter {2*CORE_R:g} mm', font=font(18), fill='#54637b')
    camera = np.array([1., -1.35, 1.15]); camera /= np.linalg.norm(camera)
    right = np.array([-camera[1], camera[0], 0.]); right /= np.linalg.norm(right)
    up = np.cross(camera,right)
    verts = mesh.vertices - mesh.bounds.mean(axis=0)
    projected = np.column_stack((verts @ right, -(verts @ up))) * 10.2 + [320,430]
    depth = verts @ camera
    light = np.array([-.5,-1,2]); light /= np.linalg.norm(light)
    for index in np.argsort(depth[mesh.faces].mean(axis=1)):
        normal = mesh.face_normals[index]
        if normal @ camera <= 0:
            continue
        factor = 0.68 + 0.32*max(0,float(normal @ light))
        color = tuple(int(c*factor) for c in (69,155,199))
        draw.polygon([tuple(p) for p in projected[mesh.faces[index]]], fill=color)
    draw.text((55,632), 'Flat underside for existing double-sided tape.', font=font(18), fill='#54637b')
    draw.text((662,153), 'Suggested placement (top view)', font=font(23), fill='#18283e')
    ox,oy,scale = 722,209,6.5
    def rect(x,y,w,h):
        return (ox+x*scale,oy+y*scale,ox+(x+w)*scale,oy+(y+h)*scale)
    draw.rounded_rectangle(rect(0,0,65.25,65.25), radius=4*scale, fill='#d4dae2', outline='#8998a9', width=2)
    draw.rounded_rectangle(rect(1.6,1.6,62.05,62.05), radius=2.4*scale, fill='#ffffff')
    draw.rounded_rectangle(rect(3.6,3.6,52.05,22.8), radius=7, fill='#d3e8f9', outline='#4487b3', width=2)
    draw.text((ox+9*scale,oy+11*scale), 'Feather + IMU', font=font(21), fill='#235576')
    draw.text((ox+8*scale,oy+17*scale), 'USB end on the left', font=font(15), fill='#235576')
    draw.rounded_rectangle(rect(3.6,29.4,35.9,32.25), radius=7, fill='#fff0c6', outline='#c89635', width=2)
    draw.text((ox+12*scale,oy+41*scale), 'Battery', font=font(22), fill='#88621d')
    draw.text((ox+7*scale,oy+47*scale), 'Side wire included', font=font(14), fill='#88621d')
    gx,gy = PLACEMENT
    draw.rounded_rectangle(rect(gx,gy,L,W), radius=BASE_R*scale, fill='#fce0d6', outline='#cf7858', width=2)
    for cx,cy in CENTERS:
        draw.ellipse(rect(gx+cx-LIP_R,gy+cy-LIP_R,2*LIP_R,2*LIP_R),fill='#6db3d5',outline='#276e92',width=2)
        draw.ellipse(rect(gx+cx-CORE_R,gy+cy-CORE_R,2*CORE_R,2*CORE_R),outline='#276e92',width=2)
    draw.text((662,652), 'Position is a proposal; check real wires before sticking.', font=font(17), fill='#54637b')
    draw.text((45,716), 'No adhesive thickness or actual wire bundle is included in these dimensions.',font=font(18),fill='#54637b')
    im.save(HERE/(NAME+'_preview.png'))


def main():
    spacing = math.dist(*CENTERS)
    assert W == 27.0 and spacing-2*LIP_R >= 1.0
    assert all(LIP_R < x < L-LIP_R and LIP_R < y < W-LIP_R for x,y in CENTERS)
    pts = []
    for cx,cy in [(BASE_R,BASE_R),(L-BASE_R,BASE_R),(L-BASE_R,W-BASE_R),(BASE_R,W-BASE_R)]:
        for n in range(SEGMENTS):
            t = 2*math.pi*n/SEGMENTS
            for z in [0,BASE_H]:
                pts.append([cx+BASE_R*math.cos(t),cy+BASE_R*math.sin(t),z])
    solid = md.Manifold.hull_points(pts)
    profile = [[0,BASE_H-0.01],[CORE_R,BASE_H-0.01],
               [CORE_R,BASE_H+CORE_H],[LIP_R,BASE_H+CORE_H+FLARE_H],
               [LIP_R,BASE_H+CORE_H+FLARE_H+RIM_H],
               [LIP_R-BEVEL_H,TOTAL_H],[0,TOTAL_H]]
    # Revolve a single continuous outline to avoid coincident internal end caps.
    post = md.CrossSection([profile]).revolve(SEGMENTS)
    for x,y in CENTERS:
        solid += post.translate([x,y,0])
    assert solid.status() == md.Error.NoError
    mm = solid.to_mesh()
    mesh = trimesh.Trimesh(vertices=np.asarray(mm.vert_properties)[:,:3],faces=np.asarray(mm.tri_verts),process=True)
    stl = HERE/(NAME+'.stl')
    mesh.export(stl)
    actual = trimesh.load_mesh(stl,process=True)
    assert actual.is_watertight and actual.is_winding_consistent and actual.is_volume
    assert len(actual.split()) == 1 and actual.euler_number == 2
    assert np.allclose(actual.extents,[L,W,TOTAL_H],atol=1e-5)
    assert all(len(set(face)) == 3 for face in actual.faces)
    assert actual.area_faces.min() > 1e-9
    # Check the proposed add-on footprint against the nominal placement only.
    # User's real cable positions remain unmeasured.
    gx,gy = PLACEMENT
    assert gx > 3.6+35.90 and gy > 3.6+22.80
    assert gx+L < 1.6+62.05 and gy+W < 1.6+62.05
    summary = {
        'part':'removable cable guide, not a full base/lid',
        'dimensions_mm':[L,W,TOTAL_H],'base_thickness_mm':BASE_H,
        'post_core_diameter_mm':2*CORE_R,'post_flange_diameter_mm':2*LIP_R,
        'post_center_spacing_mm':spacing,'core_height_mm':CORE_H,
        'post_flange_gap_mm':spacing-2*LIP_R,
        'user_space_feedback':'About 30 mm available; requested long side 27 mm.',
        'proposed_position_in_v0_3_mm':list(PLACEMENT),
        'nominal_gap_from_battery_footprint_mm':round(gx-(3.6+35.90),2),
        'nominal_gap_from_board_footprint_mm':round(gy-(3.6+22.80),2),
        'is_watertight':bool(actual.is_watertight),'is_winding_consistent':bool(actual.is_winding_consistent),
        'connected_components':1,'euler_number':int(actual.euler_number),
        'faces':len(actual.faces),'material_volume_mm3':round(float(actual.volume),3),
        'limitations':'Wire bend radius/capacity not validated. Tape thickness not included. No slicing or printing performed.',
        'libraries':{key:importlib.metadata.version(key) for key in ['manifold3d','trimesh','numpy','networkx','Pillow']}}
    (HERE/(NAME+'_validation.json')).write_text(json.dumps(summary,indent=2)+'\n')
    (HERE/(NAME+'.scad')).write_text(f'''// v0.3 add-on, 2026-09-09: removable two-post cable guide. Units mm.
// Attach underneath to the tray with existing foam tape after powerless fit.
// Post radius is a design trial, not a verified wire bend-radius specification.
$fn={SEGMENTS};
plate_l={L}; plate_w={W}; plate_h={BASE_H}; plate_r={BASE_R};
core_r={CORE_R}; core_h={CORE_H}; lip_r={LIP_R};
flare_h={FLARE_H}; rim_h={RIM_H}; bevel_h={BEVEL_H};
module base() {{
    hull() for(x=[plate_r,plate_l-plate_r]) for(y=[plate_r,plate_w-plate_r])
        translate([x,y,0]) cylinder(r=plate_r,h=plate_h);
}}
module post() {{
    rotate_extrude() polygon([[0,plate_h-0.01],[core_r,plate_h-0.01],
        [core_r,plate_h+core_h],[lip_r,plate_h+core_h+flare_h],
        [lip_r,plate_h+core_h+flare_h+rim_h],
        [lip_r-bevel_h,plate_h+core_h+flare_h+rim_h+bevel_h],
        [0,plate_h+core_h+flare_h+rim_h+bevel_h]]);
}}
post_centers={json.dumps(CENTERS)};
union() {{ base(); for(p=post_centers) translate([p[0],p[1],0]) post(); }}
''')
    preview(actual)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
