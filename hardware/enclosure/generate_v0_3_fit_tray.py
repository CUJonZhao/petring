#!/usr/bin/env python3
"""Generate the measured, powerless-fit tray as SCAD and a checked binary STL.

Uses only the Python standard library. Edit the measurements/design allowances
here and rerun to regenerate both files consistently. No printer is controlled.
"""
import json
import math
import struct
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "delta_collar_enclosure_v0_3_fit_tray"

# User measurements, 2026-09-08. Header height already includes the nested IMU.
FEATHER_USB_L, FEATHER_W, ASSEMBLY_H = 52.05, 22.80, 16.36
BATTERY_L, BATTERY_W, BATTERY_H = 35.90, 32.25, 4.80
# Design allowances, NOT additional measured dimensions.
EDGE_GAP, LANE_GAP, CABLE_END_ALLOWANCE = 2.0, 3.0, 8.0
WALL, FLOOR, CAVITY_H, OUTER_RADIUS = 1.6, 1.6, 10.0, 4.0
CORNER_STEPS = 16
INNER_L = max(FEATHER_USB_L, BATTERY_L) + EDGE_GAP + CABLE_END_ALLOWANCE
INNER_W = FEATHER_W + LANE_GAP + BATTERY_W + 2 * EDGE_GAP
L, W, H = INNER_L + 2 * WALL, INNER_W + 2 * WALL, CAVITY_H + FLOOR


def outline(l, w, r, offset=0.0):
    points = []
    for cx, cy, start in [(l-r, r, 270), (l-r, w-r, 0),
                           (r, w-r, 90), (r, r, 180)]:
        for step in range(CORNER_STEPS + 1):
            angle = math.radians(start + 90 * step / CORNER_STEPS)
            points.append((offset+cx+r*math.cos(angle), offset+cy+r*math.sin(angle)))
    return points


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def polygon_area(points):
    return sum(p[0]*q[1]-q[0]*p[1] for p, q in zip(points, points[1:]+points[:1]))/2


def main():
    outer = outline(L, W, OUTER_RADIUS)
    inner = outline(INNER_L, INNER_W, OUTER_RADIUS-WALL, WALL)
    n = len(outer)
    vertices = ([(x,y,0) for x,y in outer] + [(x,y,H) for x,y in outer]
                + [(x,y,FLOOR) for x,y in inner] + [(x,y,H) for x,y in inner]
                + [(L/2,W/2,0), (L/2,W/2,FLOOR)])
    faces = []
    def quad(a,b,c,d):
        faces.extend([(a,b,c),(a,c,d)])
    for i in range(n):
        j = (i+1)%n
        quad(i,j,n+j,n+i)                          # outer walls
        quad(2*n+i,3*n+i,3*n+j,2*n+j)              # cavity walls
        quad(n+i,n+j,3*n+j,3*n+i)                  # rim, open in the center
        faces.extend([(4*n,j,i),(4*n+1,2*n+i,2*n+j)])

    stl = HERE / (NAME + '.stl')
    with stl.open('wb') as f:
        f.write(b'Measured v0.3 tray; POWERLESS FIT ONLY'.ljust(80,b' '))
        f.write(struct.pack('<I',len(faces)))
        for face in faces:
            a,b,c = [vertices[k] for k in face]
            normal = cross(sub(b,a),sub(c,a))
            length = math.sqrt(sum(x*x for x in normal))
            assert length > 1e-9, 'Degenerate triangle'
            f.write(struct.pack('<12fH',*(x/length for x in normal),*a,*b,*c,0))

    # Validate the EXPORTED float32 mesh, rather than only source arrays.
    data = stl.read_bytes()
    count = struct.unpack_from('<I',data,80)[0]
    assert len(data) == 84 + 50*count
    triangles = []
    for i in range(count):
        values = struct.unpack_from('<12fH',data,84+50*i)
        triangles.append([tuple(values[3+3*j:6+3*j]) for j in range(3)])
    edges = Counter()
    directions = Counter()
    volume = 0.0
    adjacency = {}
    for a,b,c in triangles:
        volume += sum(x*y for x,y in zip(a,cross(b,c)))/6
        for p,q in [(a,b),(b,c),(c,a)]:
            edges[tuple(sorted((p,q)))] += 1
            directions[(p,q)] += 1
            adjacency.setdefault(p,set()).add(q)
            adjacency.setdefault(q,set()).add(p)
    assert all(v == 2 for v in edges.values()), 'Non-manifold edge'
    assert all(directions[(a,b)] == directions[(b,a)] for a,b in directions), 'Inconsistent winding'
    seen = set()
    pending = [next(iter(adjacency))]
    while pending:
        point = pending.pop()
        if point not in seen:
            seen.add(point)
            pending.extend(adjacency[point]-seen)
    assert len(seen) == len(adjacency), 'Disconnected mesh'
    assert len(seen)-len(edges)+count == 2, 'Unexpected surface topology'
    expected_volume = polygon_area(outer)*H-polygon_area(inner)*CAVITY_H
    assert volume > 0 and abs(volume-expected_volume) < 0.01
    bbox = [[min(v[k] for v in seen), max(v[k] for v in seen)] for k in range(3)]
    assert all(abs(bbox[k][1]-bbox[k][0]-size)<1e-4 for k,size in enumerate([L,W,H]))

    def scad_polygon(points):
        return '[' + ','.join(f'[{x:.9f},{y:.9f}]' for x,y in points) + ']'
    # Explicit matched profiles keep the SCAD geometry equivalent to the STL.
    scad = f'''// v0.3 measured low-wall tray, 2026-09-08. Units: mm.
// POWERLESS FIT ONLY. Open top, no lid, fasteners, or powered-use retention.
// Dimensions: external {L:.2f} x {W:.2f} x {H:.2f}; cavity {INNER_L:.2f} x {INNER_W:.2f} x {CAVITY_H:.2f}.
// Rebuild with generate_v0_3_fit_tray.py after changing measured/design inputs.
// IMU is nested: assembly height {ASSEMBLY_H:.2f}, not Feather height + IMU height.
// Cable-end allowance {CABLE_END_ALLOWANCE:.1f} is provisional, not a measured bend radius.
show_guides = true; // Preview-only component envelopes; excluded from STL exports.
outer_profile = {scad_polygon(outer)};
inner_profile = {scad_polygon(inner)};
difference() {{
    linear_extrude(height={H:.5f}) polygon(outer_profile);
    translate([0,0,{FLOOR:.5f}])
        linear_extrude(height={CAVITY_H+1:.5f}) polygon(inner_profile);
}}
if (show_guides) {{
    %color([0.2,0.5,0.9,0.4]) translate([{WALL+EDGE_GAP},{WALL+EDGE_GAP},{FLOOR}])
        cube([{FEATHER_USB_L},{FEATHER_W},{ASSEMBLY_H}]);
    %color([0.9,0.6,0.2,0.4]) translate([{WALL+EDGE_GAP},{WALL+EDGE_GAP+FEATHER_W+LANE_GAP},{FLOOR}])
        cube([{BATTERY_L},{BATTERY_W},{BATTERY_H}]);
}}
'''
    (HERE/(NAME+'.scad')).write_text(scad)
    summary = {'external_mm':[L,W,H], 'cavity_mm':[INNER_L,INNER_W,CAVITY_H],
               'wall_mm':WALL,'floor_mm':FLOOR,'assembly_height_mm':ASSEMBLY_H,
               'design_cable_end_allowance_mm':CABLE_END_ALLOWANCE,
               'triangles':count,'connected_components':1,'all_edges_used_twice':True,
               'consistent_winding':True,'euler_characteristic':2,
               'material_volume_mm3':round(volume,3),'bounding_box_mm':bbox,
               'purpose':'Powerless footprint/route fit; not final enclosure or mounting design.',
               'export_method':'Analytical standard-library mesh; SCAD generated from identical profiles. OpenSCAD renderer not run.'}
    (HERE/(NAME+'_validation.json')).write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
