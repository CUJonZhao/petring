#!/usr/bin/env python3
"""Build base, slip-over lid, and review geometry from explicit design inputs.

Use --draft while required measurements are null. Draft files are not approved
for printing. Dependencies: manifold3d, trimesh, numpy, networkx, Pillow.
"""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path

import manifold3d as md
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SEGMENTS = 64


def box(l,w,h,xyz=(0,0,0)):
    return md.Manifold.cube([l,w,h]).translate(xyz)


def rounded(l,w,h,r,xyz=(0,0,0)):
    pts = []
    for cx,cy in [(r,r),(l-r,r),(l-r,w-r),(r,w-r)]:
        for n in range(SEGMENTS):
            a=2*math.pi*n/SEGMENTS
            for z in [0,h]:
                pts.append([cx+r*math.cos(a),cy+r*math.sin(a),z])
    return md.Manifold.hull_points(pts).translate(xyz)


def u_slot(x,depth,y,width,bottom,top,r=1.0):
    # Local X -> global Y, Y -> Z, Z -> X. Top corners stay above the part.
    return rounded(width,top-bottom+8,depth,r).rotate([90,0,90]).translate([x,y-width/2,bottom])


def to_mesh(solid):
    assert solid.status() == md.Error.NoError, str(solid.status())
    m=solid.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(m.vert_properties)[:,:3],faces=np.asarray(m.tri_verts),process=True)


def export(solid,path):
    mesh=to_mesh(solid)
    mesh.export(path)
    actual=trimesh.load_mesh(path,process=True)
    assert actual.is_volume and actual.is_watertight and actual.is_winding_consistent, path.name
    assert len(actual.split()) == 1, path.name
    assert actual.area_faces.min()>1e-9, path.name
    assert np.allclose(actual.bounds[0],0,atol=1e-5), actual.bounds
    return actual, {'dimensions_mm':actual.extents.tolist(),'faces':len(actual.faces),
                    'single_connected_solid':True,'watertight':True,'consistent_winding':True,
                    'volume_mm3':float(actual.volume),'euler_number':int(actual.euler_number)}


def mesh_picture(im,meshes,rectangle,label,font,camera_dir):
    draw=ImageDraw.Draw(im)
    x0,y0,x1,y1=rectangle
    draw.rounded_rectangle(rectangle,radius=18,fill='white')
    draw.text((x0+20,y0+15),label,font=font(23),fill='#15283f')
    camera=np.array(camera_dir,dtype=float); camera/=np.linalg.norm(camera)
    right=np.array([-camera[1],camera[0],0]);right/=np.linalg.norm(right)
    up=np.cross(camera,right)
    all_v=np.concatenate([m.vertices for m,c in meshes])
    projected=np.column_stack((all_v@right,-all_v@up))
    center=(projected.min(axis=0)+projected.max(axis=0))/2
    scale=min((x1-x0-70)/np.ptp(projected[:,0]),(y1-y0-110)/np.ptp(projected[:,1]))
    origin=np.array([(x0+x1)/2,(y0+y1)/2+25])
    light=np.array([-.8,-1.3,2.0]);light/=np.linalg.norm(light)
    pixels=np.full((y1-y0,x1-x0,3),255,dtype=np.uint8)
    zbuffer=np.full(pixels.shape[:2],-np.inf)
    for mesh,color in meshes:
        vertices=mesh.vertices
        pp=(np.column_stack((vertices@right,-vertices@up))-center)*scale+origin-[x0,y0]
        depth=vertices@camera
        for idx,face in enumerate(mesh.faces):
            normal=mesh.face_normals[idx]
            if normal@camera<=0:continue
            factor=.65+.35*max(0,float(normal@light))
            tri=pp[face]
            xmin,ymin=np.maximum(np.floor(tri.min(axis=0)).astype(int),[0,65])
            xmax,ymax=np.minimum(np.ceil(tri.max(axis=0)).astype(int),[x1-x0-1,y1-y0-1])
            if xmax<xmin or ymax<ymin:continue
            xx,yy=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5)
            a,b,c=tri
            denom=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denom)<1e-10:continue
            aa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/denom
            bb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/denom
            cc=1-aa-bb
            zz=aa*depth[face[0]]+bb*depth[face[1]]+cc*depth[face[2]]
            local_z=zbuffer[ymin:ymax+1,xmin:xmax+1]
            mask=(aa>=-1e-8)&(bb>=-1e-8)&(cc>=-1e-8)&(zz>local_z)
            local_z[mask]=zz[mask]
            pixels[ymin:ymax+1,xmin:xmax+1][mask]=[int(v*factor) for v in color]
    rendered=Image.fromarray(pixels)
    im.paste(rendered.crop((0,65,x1-x0,y1-y0-20)),(x0,y0+65))


def preview(base,lid,path,draft,measurements):
    im=Image.new('RGB',(1400,930),'#f4f7fa');draw=ImageDraw.Draw(im)
    font=lambda size:ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',size)
    heading='v0.4 enclosure - measurement draft' if draft else 'v0.4 enclosure - fit-test revision'
    draw.text((35,25),heading,font=font(31),fill='#17283e')
    draw.text((35,74),'Base, USB access, four pilot-hole supports, removable cable-guide bay, and slip-over lid.',font=font(20),fill='#54637b')
    mesh_picture(im,[(base,(81,159,199))],(25,125,687,740),'Base / USB side',font,[-1,1.2,3.0])
    mesh_picture(im,[(lid,(116,168,167))],(712,125,1375,740),'Lid / underside, print orientation',font,[1,-1.2,1.6])
    draw.text((35,763),'USB: open-top cutout. Switch wires: lay into the side slot; lid tongue limits the opening.',font=font(21),fill='#273f57')
    draw.text((35,801),'Pilot holes are for M2 screw fit checks. Cable guide remains a separate reusable part.',font=font(20),fill='#54637b')
    note='DRAFT: required measurements are pending. Do not print.' if draft else 'Ready for slicing and dry fit. Screw fit, cable routing and lid fit still need physical checks.'
    draw.text((35,862),note,font=font(20),fill='#a04329')
    im.save(path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--draft',action='store_true')
    args=parser.parse_args()
    cfg=json.loads((HERE/'design_inputs.json').read_text())
    m=cfg['measured'].copy(); d=cfg['design']
    pending=[key for key,value in m.items() if value is None]
    if pending and not args.draft:
        raise SystemExit('Measurements pending: '+', '.join(pending)+'. Use --draft for review only.')
    for key in pending:m[key]=cfg['draft_placeholders'][key]
    if m['right_posts_clear'] is not True:
        raise SystemExit('Right support access not confirmed. Revise supports instead of exporting four interfering posts.')
    draft=bool(pending) or args.draft
    suffix='_draft' if draft else ''
    l,w,t,f,r=[d[key] for key in ['base_l','base_w','wall','floor','outer_r']]
    h=f+d['assembly_bottom_gap']+m['assembly_h']+d['headroom']
    support_h=m['lower_header_h']+d['assembly_bottom_gap']
    pcb_z=f+support_h
    pcb_xy=[d['board_usb_envelope_xy'][0]+m['usb_overhang'],d['board_usb_envelope_xy'][1]]
    hole_xy=[[pcb_xy[0]+x,pcb_xy[1]+y] for x,y in m['mount_holes_xy']]
    body=rounded(l,w,h,r)-rounded(l-2*t,w-2*t,h+2,r-t,(t,t,f))
    usb_y=pcb_xy[1]+m['board_w']/2
    usb_w=m['usb_plug_w']+2*d['slot_side_clearance']
    usb_bottom=f+d['usb_slot_bottom_above_floor']
    wire_w=m['switch_bundle_w']+2*d['slot_side_clearance']
    wire_bottom=f+d['wire_slot_bottom_above_floor']
    wire_y=d['wire_exit_y']; wire_r=1.0
    usb_cut=u_slot(-5,5+t+.02,usb_y,usb_w,usb_bottom,h)
    wire_cut=u_slot(l-t-.02,7,wire_y,wire_w,wire_bottom,h,wire_r)
    body=body-usb_cut-wire_cut
    assert usb_w < m['board_w']-2
    assert h-usb_bottom >= m['usb_plug_h']+1.0, 'USB window height needs measurement/layout revision'
    assert wire_w < 16

    # One revolved outline gives a flared foot and shaft without internal caps.
    profile=[[0,f-.02],[d['post_foot_r'],f-.02],[d['post_foot_r'],f+.3],
             [d['post_r'],f+1.6],[d['post_r'],pcb_z],[0,pcb_z]]
    support=md.CrossSection([profile]).revolve(SEGMENTS)
    bore=md.Manifold.cylinder(d['pilot_depth']+.2,d['pilot_d']/2,d['pilot_d']/2,48).translate([0,0,pcb_z-d['pilot_depth']])
    entry=md.Manifold.cylinder(.45,d['pilot_d']/2,1.05,48).translate([0,0,pcb_z-.4])
    support=support-bore-entry
    for x,y in hole_xy:body+=support.translate([x,y,0])

    gap,lw,roof,skirt=[d[key] for key in ['lid_fit_gap','lid_wall','lid_top','lid_skirt_h']]
    over=gap+lw
    lid=rounded(l+2*over,w+2*over,skirt+roof,r+over,(-over,-over,h-skirt))
    lid-=rounded(l+2*gap,w+2*gap,skirt+.02,r+gap,(-gap,-gap,h-skirt-.02))
    skirt_only=box(l+30,w+30,100,(-15,-15,h-100))
    lid=lid-(usb_cut^skirt_only)-(wire_cut^skirt_only)
    gate_gap=d['wire_gate_gap']
    gate_bottom=wire_bottom+wire_r+m['switch_bundle_h']+d['wire_top_clearance']
    # The tongue overlaps the slot and extends inward for strength. The 27 mm
    # guide footprint stays clear of this thicker tongue in the closed model.
    gate_x=l-gate_gap-d['wire_gate_thickness']
    gate=box(d['wire_gate_thickness'],wire_w-2*gate_gap,h-gate_bottom+.02,
             (gate_x,wire_y-wire_w/2+gate_gap,gate_bottom))
    lid+=gate
    assert abs((body^lid).volume())<1e-6, 'Base/lid collision in closed position'
    # A filled box models the supplied assembly's height envelope. Hole support
    # placement itself still requires user confirmation of the IMU underside.
    envelope=box(m['board_l']+m['usb_overhang'],m['board_w'],m['assembly_h'],
                 (*d['board_usb_envelope_xy'],f+d['assembly_bottom_gap']))
    assert abs((envelope^lid).volume())<1e-6, 'Lid collides with assembly envelope'
    battery=box(m['battery_l'],m['battery_w'],m['battery_h'],(*d['battery_xy'],f))
    guide=box(20,27,9,(*d['cable_guide_xy'],f))
    assert abs((battery^body).volume())<1e-6 and abs((guide^body).volume())<1e-6
    assert abs((battery^guide).volume())<1e-6
    assert abs((battery^lid).volume())<1e-6 and abs((guide^lid).volume())<1e-6
    # Probe the smallest guaranteed rectangular wire passage, above the rounded
    # slot corners. This confirms a route through BOTH walls in closed position.
    wire_probe=box(15,m['switch_bundle_w'],m['switch_bundle_h'],
                   (l-8,wire_y-m['switch_bundle_w']/2,wire_bottom+wire_r))
    assert abs((wire_probe^(body+lid)).volume())<1e-6, 'Closed wire route is blocked'
    # Full-width USB passage excluding its lower corner fillets. Exact connector
    # vertical alignment is deliberately checked on the physical fit-test print.
    usb_probe=box(5,usb_w-.02,h-usb_bottom-1.02,
                  (-over-.01,usb_y-usb_w/2+.01,usb_bottom+1.01))
    assert abs((usb_probe^(body+lid)).volume())<1e-6, 'USB through-window is blocked'
    # Export lid with its outer roof on the bed, cavity/tongue pointing upward.
    lid_print=lid.rotate([180,0,0]).translate([over,w+over,h+roof])
    bm,bs=export(body,HERE/('delta_collar_v0_4_base'+suffix+'.stl'))
    lm,ls=export(lid_print,HERE/('delta_collar_v0_4_lid'+suffix+'.stl'))
    assert np.allclose(bm.extents,[l,w,h],atol=1e-5)
    assert np.allclose(lm.extents[:2],[l+2*over,w+2*over],atol=1e-5)
    summary={'draft':draft,'pending_measurements':pending,'effective_measurements':m,
             'base':bs,'lid_print_orientation':ls,'assembled_outer_height_mm':h+roof,
             'pcb_underside_height_from_floor_mm':support_h,'pcb_underside_z_mm':pcb_z,
             'post_centers_global_mm':hole_xy,'usb_window_width_mm':usb_w,
             'usb_window_vertical_clearance_mm':h-usb_bottom,'wire_slot_width_mm':wire_w,
             'wire_gate_bottom_z_mm':gate_bottom,'assembled_base_lid_collision_mm3':(body^lid).volume(),
             'wire_passage_nominal_height_mm':gate_bottom-wire_bottom,
             'closed_wire_passage_probe_clear':True,'usb_through_window_probe_clear':True,
             'battery_and_guide_clear_of_base_and_lid':True,
             'limitations':['No slicer or physical print check performed.','USB vertical alignment and M2 pilot/screw fit still require physical checks.','M2 fasteners are not confirmed in the existing purchase list.','Lid is a slip-over bench prototype; retention for wearing is not validated.','Cable guide envelope excludes tape and wound-wire height.'],
             'libraries':{k:importlib.metadata.version(k) for k in ['manifold3d','trimesh','numpy','networkx','Pillow']}}
    (HERE/('validation'+suffix+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
    preview(bm,lm,HERE/('preview'+suffix+'.png'),draft,m)
    # A compact assembly viewer uses the generated meshes without flattening
    # the editable dimensions: change design_inputs.json and regenerate.
    (HERE/('assembly'+suffix+'.scad')).write_text(f'''// v0.4 mesh assembly preview. Editable inputs: design_inputs.json.
// {'MEASUREMENTS PENDING - NOT FOR PRINTING' if draft else 'Fit-test geometry; physical validation required'}
show_lid=false;
import("delta_collar_v0_4_base{suffix}.stl");
if(show_lid) color([0.2,0.7,0.6,0.4])
    translate([-{over},{w+over},{h+roof}]) rotate([180,0,0])
        import("delta_collar_v0_4_lid{suffix}.stl");
%color([0.2,0.5,0.9,0.35]) translate([{d['board_usb_envelope_xy'][0]},{d['board_usb_envelope_xy'][1]},{f+d['assembly_bottom_gap']}])
    cube([{m['board_l']+m['usb_overhang']},{m['board_w']},{m['assembly_h']}]);
%color([0.9,0.65,0.2,0.4]) translate([{d['battery_xy'][0]},{d['battery_xy'][1]},{f}])
    cube([{m['battery_l']},{m['battery_w']},{m['battery_h']}]);
%color([0.8,0.4,0.2,0.4]) translate([{d['cable_guide_xy'][0]},{d['cable_guide_xy'][1]},{f}])
    import("../delta_collar_v0_3_cable_guide_27mm.stl");
''')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
