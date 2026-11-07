"""Build Delta's locally authored, stylized 3D desktop-pet asset.

Run with: Blender --background --factory-startup --python scripts/build_delta_model.py
Reference photos stay outside the repository; this script contains only hand-authored
proportions and markings observed from them.
"""

import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Resources"
OUT.mkdir(exist_ok=True)
random.seed(14)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, roughness=0.88):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


snow = material("warm white coat", (0.84, 0.85, 0.82))
ivory = material("bright white blaze", (0.96, 0.95, 0.90))
silver = material("blue merle silver", (0.43, 0.48, 0.51))
slate = material("blue merle slate", (0.27, 0.32, 0.36))
charcoal = material("black merle patches", (0.065, 0.075, 0.085))
black = material("nose and eyelids", (0.025, 0.029, 0.032), 0.44)
pink = material("tongue pink", (0.84, 0.27, 0.34), 0.58)
mouth = material("mouth interior", (0.14, 0.055, 0.07), 0.65)
blue_eye = material("Delta blue eye", (0.39, 0.66, 0.77), 0.3)
brown_eye = material("Delta dark eye", (0.13, 0.10, 0.09), 0.3)
eye_glint = material("eye highlight", (0.94, 0.98, 0.99), 0.12)


def mix(a, b, t):
    return tuple(a[k]*(1-t) + b[k]*t for k in range(3))


def smooth(a, b, x):
    t = max(0, min(1, (x-a)/(b-a)))
    return t*t*(3-2*t)


def coat_texture(name, kind):
    """A local hand-authored blue-merle coat map, including fine hair tone variation."""
    width, height = 768, 384
    image = bpy.data.images.new(name + " map", width=width, height=height, alpha=True)
    pixels = [0.0] * (width*height*4)
    white = (0.82, 0.84, 0.82)
    bright = (0.94, 0.94, 0.90)
    grey = (0.42, 0.48, 0.51)
    dark = (0.045, 0.055, 0.063)
    for py in range(height):
        v = py/(height-1)
        angle = 2*math.pi*v
        around = math.sin(angle)
        across = math.cos(angle)
        for px in range(width):
            u = px/(width-1)
            n = (0.50*math.sin(u*22.3 + math.sin(v*19.1)*1.9)*math.cos(v*17.7)
                 + 0.24*math.sin(u*47.1 + v*15.7)*math.cos(v*39.2-u*9.1)
                 + 0.12*math.sin(u*91.5-v*28.3)*math.sin(v*73.6)
                 + 0.07*math.sin(u*160.7+v*120.9))
            grain = 0.022*math.sin(u*387+v*57)*math.cos(v*341-u*37)
            if kind == "body":
                # White belly and sides, with a dark asymmetric saddle and silver mottling.
                underside = 1-smooth(-0.62, -0.20, around)
                shoulder = 1-smooth(0.68, 0.88, u)
                base = mix(grey, white, underside*0.96)
                saddle = smooth(-0.10, 0.30, around) * shoulder
                patch = smooth(-0.22, 0.02, n + 0.25*math.sin(u*8.6-v*9.5))
                base = mix(base, dark, saddle*patch*0.92)
                base = mix(base, (0.25, 0.30, 0.33), saddle*(1-patch)*0.45)
            else:
                # The narrow blaze remains clear down the muzzle; the left mask is darker.
                blaze = 1-smooth(0.13, 0.37, abs(across))
                mask = (1-smooth(-0.08, 0.18, across)) * (1-smooth(-0.70, -0.35, around))
                base = mix(grey, dark, mask*0.93)
                base = mix(base, bright, blaze*0.96)
                base = mix(base, dark, smooth(0.18, 0.45, n)*0.30*(1-blaze))
            c = tuple(max(0.01, min(1, q+grain)) for q in base)
            index = (py*width+px)*4
            pixels[index:index+4] = (*c, 1.0)
    image.pixels.foreach_set(pixels)
    image.pack()
    mat = material(name, (1, 1, 1))
    tree = mat.node_tree
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tree.links.new(tex.outputs["Color"], tree.nodes.get("Principled BSDF").inputs["Base Color"])
    return mat


body_map = coat_texture("delta blue merle body", "body")
face_map = coat_texture("delta blue merle face", "face")


def empty(name, position=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    if parent:
        obj.parent = parent
    return obj


def ellipsoid(name, at, size, mat, parent, segments=24, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=at)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent = parent
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def loft(name, sections, parent, mats, coat=None, sides=48):
    """Sections are (longitudinal y, center z, width x, radius z)."""
    vertices = []
    faces = []
    indices = []
    for i, (y, cz, wx, hz) in enumerate(sections):
        for j in range(sides):
            a = 2 * math.pi * j / sides
            vertices.append((wx * math.cos(a), y, cz + hz * math.sin(a)))
            if i:
                faces.append(((i-1)*sides+j, (i-1)*sides+(j+1)%sides,
                              i*sides+(j+1)%sides, i*sides+j))
                indices.append(coat(i, j, a, y, cz) if coat else 0)
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((len(sections)-1)*sides+j for j in range(sides)))
    indices += [0, 0]
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    for mat in mats:
        mesh.materials.append(mat)
    for poly, idx in zip(mesh.polygons, indices):
        poly.material_index = idx
        poly.use_smooth = True
    uv = mesh.uv_layers.new(name="UVMap")
    count = len(sections)
    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            vertex_idx = mesh.loops[loop_idx].vertex_index
            ring = vertex_idx // sides
            side = vertex_idx % sides
            uv.data[loop_idx].uv = (ring/(count-1), side/sides)
    return obj


def dense(sections, steps=5):
    result = []
    for i in range(len(sections)-1):
        a = sections[i]
        b = sections[i+1]
        for k in range(steps):
            t = k/steps
            t = t*t*(3-2*t)
            result.append(tuple(a[c]*(1-t)+b[c]*t for c in range(4)))
    result.append(sections[-1])
    return result


def tapered(name, start, end, r1, r2, mat, parent, vertices=12):
    direction = Vector(end) - Vector(start)
    midpoint = (Vector(start) + Vector(end)) / 2
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2,
                                    depth=direction.length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    obj.parent = parent
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


pet = empty("delta_root")


body = loft("delta_body", dense([
    (1.03, 0.91, 0.10, 0.14), (0.88, 0.92, 0.34, 0.36),
    (0.60, 0.94, 0.43, 0.43), (0.24, 0.94, 0.43, 0.43),
    (-0.24, 0.93, 0.40, 0.40), (-0.62, 0.90, 0.36, 0.36),
    (-0.88, 0.88, 0.29, 0.28), (-1.04, 0.89, 0.08, 0.10)
]), pet, [body_map])

# Delta's large fluffy white chest ruff, with a less spherical front silhouette.
loft("delta_chest_mane", dense([
    (-0.38, 1.00, 0.08, 0.12), (-0.53, 1.06, 0.34, 0.43),
    (-0.70, 1.13, 0.48, 0.52), (-0.90, 1.18, 0.45, 0.55),
    (-1.08, 1.20, 0.38, 0.49), (-1.21, 1.23, 0.20, 0.33),
    (-1.28, 1.28, 0.04, 0.10)
]), pet, [snow])

# Tufts soften the contour. They are deliberately varied rather than identical spikes.
for side in (-1, 1):
    for k in range(14):
        theta = -0.58 + k * 0.11
        y = -0.68 - 0.45*math.cos(theta)
        z = 0.75 + k*0.065
        x = side*(0.34 + 0.09*math.sin(k*0.75))
        length = 0.12 + 0.08*(k % 3)/2
        ellipsoid(f"ruff feather {side} {k}",
                  (x+side*0.025, y-length*0.36, z+0.01),
                  (0.055, length*0.65, 0.12),
                  ivory if k % 4 else snow, pet, 12, 8)

# A relatively long, narrow collie-like head rather than a round puppy face.
head = empty("delta_head", (0, -1.06, 1.42), pet)


loft("delta_face", dense([
    (0.34, 0.06, 0.23, 0.23), (0.18, 0.05, 0.36, 0.31),
    (-0.05, 0.01, 0.40, 0.33), (-0.25, -0.035, 0.34, 0.28),
    (-0.40, -0.08, 0.27, 0.22), (-0.54, -0.12, 0.21, 0.16),
    (-0.67, -0.14, 0.17, 0.11), (-0.72, -0.15, 0.10, 0.075)
]), head, [face_map])

# Nose is a soft black triangular shape made from three tapered lobes.
ellipsoid("delta_nose", (0, -0.73, -0.14), (0.145, 0.075, 0.075), black, head)
the_jaw = empty("delta_jaw", (0, -0.40, -0.21), head)
ellipsoid("lower_jaw", (0, -0.18, -0.04), (0.18, 0.24, 0.055), mouth, the_jaw)
ellipsoid("chin_fur", (0, -0.07, -0.085), (0.17, 0.19, 0.045), ivory, the_jaw)
the_tongue = empty("delta_tongue", (0, -0.57, -0.28), head)
ellipsoid("tongue_shape", (0, -0.12, -0.012), (0.105, 0.17, 0.025), pink, the_tongue)
for side in (-1, 1):
    x = side*0.20
    ellipsoid(f"eyelid {side}", (x, -0.208, 0.115), (0.085, 0.035, 0.075), black, head)
    eye = empty(f"delta_eye_{'left' if side < 0 else 'right'}", (x, -0.256, 0.12), head)
    ellipsoid(f"iris {side}", (0, -0.004, 0), (0.061, 0.025, 0.061),
              blue_eye if side < 0 else brown_eye, eye, 16, 8)
    ellipsoid(f"pupil {side}", (0, -0.025, 0), (0.025, 0.013, 0.034), black, eye, 12, 8)
    ellipsoid(f"glint {side}", (-0.018, -0.037, 0.018), (0.011, 0.008, 0.011),
              eye_glint, eye, 10, 6)
    closed = empty(f"delta_closed_eye_{'left' if side < 0 else 'right'}",
                   (x, -0.295, 0.12), head)
    ellipsoid(f"sleep eyelid {side}", (0, 0, 0), (0.083, 0.012, 0.011), black,
              closed, 12, 8)
    # Upright, slightly flared ears with darker outer edge and silver inner fur.
    ear = empty(f"delta_ear_{'left' if side < 0 else 'right'}",
                (side*0.25, 0.13, 0.245), head)
    tapered(f"ear outer {side}", (0, 0, -0.02), (side*0.09, 0.045, 0.33),
            0.17, 0.012, charcoal, ear, 20)
    tapered(f"ear inner {side}", (0, -0.075, 0.04), (side*0.07, -0.065, 0.27),
            0.10, 0.008, silver, ear, 16)
    for k in range(4):
        z = 0.065 + k*0.055
        ellipsoid(f"ear wisps {side} {k}", (side*0.16, 0.02, z),
                  (0.065, 0.035, 0.028), charcoal, ear, 10, 6)

# Two-segment legs with separate pivots: gait and folding can use actual joints.
for front, y in ((True, -0.66), (False, 0.67)):
    for side in (-1, 1):
        tag = ('f' if front else 'h') + ('l' if side < 0 else 'r')
        upper = empty(f"delta_leg_{tag}", (side*0.31, y, 0.78), pet)
        if front:
            ellipsoid(f"shoulder {tag}", (0, 0.005, -0.13),
                      (0.19, 0.20, 0.27), snow, upper)
            tapered(f"upper foreleg {tag}", (0, -0.015, -0.12),
                    (0, -0.012, -0.39), 0.13, 0.105, snow, upper)
        else:
            ellipsoid(f"haunch {tag}", (0, 0.05, -0.14),
                      (0.22, 0.27, 0.30), slate if side < 0 else silver, upper)
            tapered(f"upper hindleg {tag}", (0, 0.06, -0.22),
                    (0, 0.12, -0.41), 0.16, 0.11, silver, upper)
        lower = empty(f"delta_knee_{tag}", (0, 0.0 if front else 0.12, -0.37), upper)
        tapered(f"lower leg {tag}", (0, 0, 0.03), (0, -0.025, -0.33),
                0.105, 0.072, snow if front or side > 0 else slate, lower)
        ellipsoid(f"paw {tag}", (0, -0.085, -0.34),
                  (0.14, 0.19, 0.085), ivory, lower)
        for toe in (-1, 0, 1):
            ellipsoid(f"toe {tag} {toe}", (toe*0.073, -0.19, -0.37),
                      (0.038, 0.069, 0.035), ivory, lower, 12, 8)

tail = empty("delta_tail", (0, 0.98, 1.04), pet)
ellipsoid("tail root", (0, 0.15, 0.00), (0.14, 0.35, 0.14), slate, tail)
ellipsoid("tail plume", (0, 0.44, -0.07), (0.20, 0.36, 0.19), silver, tail)
ellipsoid("tail white tip", (0, 0.69, -0.18), (0.20, 0.20, 0.16), ivory, tail)
for k in range(10):
    a = 2*math.pi*k/10
    tapered(f"tail feather {k}", (0.14*math.cos(a), 0.36, -0.06+0.12*math.sin(a)),
            (0.21*math.cos(a), 0.74+0.06*random.random(), -0.15+0.18*math.sin(a)),
            0.055, 0.001, silver if k % 3 else ivory, tail, 8)

# Save the editable source and export only geometry/materials for the app.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Delta.blend"))
bpy.ops.wm.usd_export(filepath=str(OUT / "Delta.usdz"),
                      selected_objects_only=False, export_animation=False,
                      export_lights=False, export_cameras=False,
                      export_materials=True, generate_preview_surface=True,
                      convert_orientation=False)
print(f"Wrote {OUT / 'Delta.usdz'}")
