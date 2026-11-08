"""Build Delta's stylized desk-pet model (v2).

Run with: Blender --background --factory-startup --python scripts/build_delta_model.py

v2 replaces the primitive-stack model:
  * each body part is ONE continuous mesh (primitive union -> voxel remesh -> smooth);
  * the coat is painted per pixel from a 3D marking function (world-position bake),
    following the local reference photos (deskpet/reference_photos, not in Git);
  * fluffy coat from alpha-cut hair cards, one mesh per colour class;
  * node names and pivots used by PetSceneView.swift are unchanged.

Coordinates: Blender Z-up, metres-ish, Delta faces -Y, -X is Delta's RIGHT side
(blue eye, black cheek), +X her LEFT side (brown eye, merle cheek).
"""

import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Resources"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(14)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
view_layer = bpy.context.view_layer


# --------------------------------------------------------------------------
# Colour helpers and procedural noise (numpy, vectorised)
# --------------------------------------------------------------------------

def srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def smooth(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = np.asarray(t, dtype=np.float64)[..., None]
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


WHITE = np.array([0.80, 0.80, 0.78])
SILVER = np.array([0.50, 0.54, 0.57])
GREY = np.array([0.29, 0.32, 0.35])
BLACK = np.array([0.018, 0.020, 0.024])
MOUTH = np.array([0.22, 0.05, 0.06])


def _hash(x, y, z, seed):
    h = (x * 374761393 + y * 668265263 + z * 1440662683 + seed * 1013904223) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFF) / 65535.0


def vnoise(P, scale, seed):
    p = np.asarray(P, dtype=np.float64) * scale
    i = np.floor(p).astype(np.int64)
    f = p - i
    u = f * f * (3 - 2 * f)
    x, y, z = i[:, 0], i[:, 1], i[:, 2]
    res = 0.0
    for dx in (0, 1):
        wx = u[:, 0] if dx else 1 - u[:, 0]
        for dy in (0, 1):
            wy = u[:, 1] if dy else 1 - u[:, 1]
            for dz in (0, 1):
                wz = u[:, 2] if dz else 1 - u[:, 2]
                res = res + wx * wy * wz * _hash(x + dx, y + dy, z + dz, seed)
    return res


def fbm(P, scale, seed, octaves=4):
    total, amp, norm = 0.0, 1.0, 0.0
    for k in range(octaves):
        total = total + amp * vnoise(P, scale * (2 ** k), seed + 17 * k)
        norm += amp
        amp *= 0.5
    return total / norm


def merle(P, thr=0.58, light=0.0):
    """Blue merle: silver/grey mottling, black patches, black speckles."""
    patch = fbm(P, 2.4, 11, 4)
    mottle = fbm(P, 6.0, 23, 3)
    speck = vnoise(P, 24.0, 37)
    base = mix(SILVER, GREY, smooth(0.30, 0.70, mottle))
    base = mix(base, WHITE, light)
    c = mix(base, BLACK, smooth(thr - 0.025, thr + 0.025, patch))
    c = mix(c, BLACK, 0.85 * smooth(0.74, 0.78, speck))
    streak = vnoise(np.asarray(P) * np.array([1.0, 0.35, 1.0]), 40.0, 41)
    return c * (0.88 + 0.24 * streak)[:, None]


# --------------------------------------------------------------------------
# Rig layout (pivots kept compatible with PetSceneView.swift)
# --------------------------------------------------------------------------

HEAD = np.array([0.0, -1.06, 1.42])
TAIL = np.array([0.0, 0.98, 1.04])
EYES = {"right": np.array([-0.113, -0.186, 0.152]),   # head-local, Delta's right = -X
        "left": np.array([0.113, -0.186, 0.152])}
LEGS = {  # tag: (front?, side, pivot, knee offset)
    "fl": (True, -1, (-0.25, -0.60, 0.83), (0, 0.0, -0.43)),
    "fr": (True, 1, (0.25, -0.60, 0.83), (0, 0.0, -0.43)),
    "hl": (False, -1, (-0.25, 0.60, 0.86), (0, 0.12, -0.44)),
    "hr": (False, 1, (0.25, 0.60, 0.86), (0, 0.12, -0.44)),
}
TAIL_CHAIN = [(0, -0.10, 0.03, 0.09), (0, 0.00, 0.00, 0.085), (0, 0.12, -0.06, 0.085), (0, 0.22, -0.18, 0.08),
              (0, 0.28, -0.34, 0.075), (0, 0.30, -0.50, 0.07), (0, 0.32, -0.64, 0.06),
              (0, 0.38, -0.74, 0.05)]


def color(part, P):
    """Linear RGB albedo for world positions P (N,3) on a given part, at rest pose."""
    P = np.asarray(P, dtype=np.float64)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    if part == "body":
        c = merle(P, 0.60 - 0.035 * smooth(1.08, 1.32, z))
        collar = 1 - smooth(-0.74, -0.54, y + 0.10 * (fbm(P, 3.0, 5, 2) - 0.5))
        belly = 1 - smooth(0.66, 0.80, z)
        return mix(c, WHITE, np.maximum(collar, belly))
    if part == "ruff":
        return WHITE[None, :] * (0.90 + 0.10 * fbm(P, 5.0, 7, 2))[:, None]
    if part in ("head", "jaw", "eyelid"):
        L = P - HEAD
        lx, ly, lz = L[:, 0], L[:, 1], L[:, 2]
        if part == "jaw":
            c = np.tile(WHITE, (len(P), 1))
            c = mix(c, BLACK, smooth(-0.112, -0.102, lz))
            return mix(c, MOUTH, smooth(-0.085, -0.075, lz))
        # Black & white head after the reference sculpt: wide white blaze up to the crown,
        # black eye patches that break into speckles on the cheeks, speckled muzzle sides,
        # black crown tufts, white lower frill and chin.
        def speck(t, P2):
            m = smooth(0.28, 0.72, 0.62 * vnoise(P2, 40.0, 61) + 0.38 * vnoise(P2, 85.0, 62))
            return smooth(t - 0.04, t + 0.04, 1 - m)        # 1 = black
        ax = np.abs(lx)
        d_eye = np.minimum(np.linalg.norm(L - EYES["left"], axis=1), np.linalg.norm(L - EYES["right"], axis=1))
        patch = 1 - smooth(0.085, 0.12, d_eye)
        side = smooth(0.05, 0.075, ax) * smooth(-0.31, -0.23, ly)
        t_side = 0.28 + 0.72 * smooth(-0.03, 0.11, lz)          # black above, breaking into speckles below
        crown = smooth(0.14, 0.19, lz) * smooth(0.05, 0.075, ax)
        back = smooth(0.06, 0.12, ly) * smooth(0.06, 0.12, lz)
        black_field = np.clip(np.maximum.reduce([patch, side * t_side, crown, back]), 0, 1)
        bw = 0.044 + 0.016 * smooth(0.10, 0.28, lz) + 0.04 * smooth(-0.20, -0.30, ly)
        blaze = (1 - smooth(bw, bw + 0.012, ax)) * (1 - smooth(0.04, 0.12, ly))
        black_field = black_field * (1 - blaze)
        whisker = smooth(0.03, 0.055, ax) * smooth(-0.17, -0.22, ly) * (1 - smooth(-0.34, -0.39, ly)) \
            * smooth(-0.09, -0.05, lz) * (1 - smooth(0.04, 0.08, lz))
        t = np.maximum(black_field, 0.42 * whisker)
        under = 1 - smooth(-0.10, -0.06, lz)
        t = t * (1 - under * (1 - patch))
        b = speck(1 - t, P)                             # dense black where t~1, sparse dots where t small
        b = np.where(t > 0.92, 1.0, np.where(t < 0.04, 0.0, b))
        c = mix(np.tile(WHITE, (len(P), 1)), BLACK, b)
        lip = smooth(-0.112, -0.102, lz) * (1 - smooth(-0.090, -0.080, lz)) * smooth(-0.15, -0.20, ly)
        return mix(c, BLACK, lip)
    if part == "head_fur":
        # Fur roots: the outer frill ring is white below eye level and black above it.
        L = P - HEAD
        c = color("head", P)
        ring = smooth(-0.12, -0.06, L[:, 1])
        ring_col = mix(np.tile(WHITE, (len(P), 1)), BLACK, smooth(0.06, 0.11, L[:, 2]))
        return mix(c, ring_col, ring)
    if part == "ear":
        return np.tile(BLACK, (len(P), 1))
    if part == "leg_f":
        c = np.tile(WHITE, (len(P), 1))
        spot = 1 - smooth(0.035, 0.055, np.linalg.norm(P - np.array([0.27, -0.76, 0.86]), axis=1))
        return mix(c, BLACK, spot)
    if part == "leg_h":
        c = merle(P, 0.60)
        inner = 1 - smooth(0.16, 0.22, np.abs(x))
        c = mix(c, WHITE, 0.55 * inner)
        return mix(c, WHITE, 1 - smooth(0.12, 0.20, z))
    if part == "tail":
        L = P - TAIL
        c = merle(P, 0.68, light=0.30)
        return mix(c, WHITE, smooth(-0.46, -0.62, L[:, 2]))
    return np.tile(GREY, (len(P), 1))


# --------------------------------------------------------------------------
# Scene objects
# --------------------------------------------------------------------------

def link(obj):
    scene.collection.objects.link(obj)
    return obj


def empty(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    obj = link(bpy.data.objects.new(name, None))
    obj.empty_display_size = 0.1
    obj.parent = parent
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def set_smooth(me):
    try:
        me.shade_smooth()
    except AttributeError:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))


def material(name, rgb, roughness=0.85, specular=0.25):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    mat.diffuse_color = (*rgb, 1)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = specular
            break
    return mat


def textured_material(name, image, roughness=0.9, alpha=False):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.2
            break
    if alpha:
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        for attr, value in (("surface_render_method", "DITHERED"), ("blend_method", "HASHED")):
            try:
                setattr(mat, attr, value)
                break
            except (AttributeError, TypeError):
                pass
        try:
            mat.use_backface_culling = False
        except AttributeError:
            pass
    return mat


def mesh_object(name, me):
    return link(bpy.data.objects.new(name, me))


def prim_union(name, prims, voxel, smooth_iter=6, smooth_factor=0.6, M=Matrix.Identity(4)):
    """Union of ellipsoids/tapered capsules -> one remeshed, smoothed mesh (world coords)."""
    bm = bmesh.new()
    for p in prims:
        if p[0] == "ell":
            c, r = p[1], p[2]
            rot = p[3] if len(p) > 3 else (0, 0, 0)
            m = M @ Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*r, 1))
            bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0, matrix=m)
        elif p[0] == "loft":
            # sections: (y, centre z, half width, half height above, half height below)
            secs, expo, sides = p[1], (p[2] if len(p) > 2 else 2.2), 40
            rings = []
            for (yy, cz, w, ht, hb) in secs:
                ring = []
                for j in range(sides):
                    a = 2 * math.pi * j / sides
                    ca, sa = math.cos(a), math.sin(a)
                    px = w * math.copysign(abs(ca) ** (2 / expo), ca)
                    pz = (ht if sa >= 0 else hb) * math.copysign(abs(sa) ** (2 / expo), sa)
                    ring.append(bm.verts.new(M @ Vector((px, yy, cz + pz))))
                rings.append(ring)
            new_faces = []
            for i in range(len(rings) - 1):
                for j in range(sides):
                    k = (j + 1) % sides
                    new_faces.append(bm.faces.new((rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j])))
            new_faces.append(bm.faces.new(rings[0]))
            new_faces.append(bm.faces.new(rings[-1]))
            bmesh.ops.recalc_face_normals(bm, faces=new_faces)
        elif p[0] == "cap":
            p0, p1, r0, r1 = Vector(p[1]), Vector(p[2]), p[3], p[4]
            d = p1 - p0
            m = M @ Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24,
                                  radius1=r0, radius2=r1, depth=d.length, matrix=m)
            for pt, r in ((p0, r0), (p1, r1)):
                bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r,
                                          matrix=M @ Matrix.Translation(pt))
    me = bpy.data.meshes.new(name + "_src")
    bm.to_mesh(me)
    bm.free()
    obj = mesh_object(name, me)
    rm = obj.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    sm = obj.modifiers.new("smooth", "SMOOTH")
    sm.factor = smooth_factor
    sm.iterations = smooth_iter
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    obj.modifiers.clear()
    obj.data = new
    bpy.data.meshes.remove(me)
    new.name = name
    set_smooth(new)
    return obj


def plain_prims(name, prims, mat, M=Matrix.Identity(4), segments=24):
    """Small closed shapes (eyes, nose) without remeshing."""
    bm = bmesh.new()
    for c, r, rot in prims:
        m = M @ Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*r, 1))
        bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=segments // 2, radius=1.0, matrix=m)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    set_smooth(me)
    me.materials.append(mat)
    return mesh_object(name, me)


def ring(name, R, r, sx, sz, mat, M, seg=40, rseg=8):
    """Almond eyelid rim in the local XZ plane (eye looks along local -Y)."""
    verts, faces = [], []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        cx, cz = R * sx * math.cos(t), R * sz * math.sin(t)
        radial = Vector((math.cos(t), 0, math.sin(t)))
        for j in range(rseg):
            f = 2 * math.pi * j / rseg
            off = radial * (r * math.cos(f)) + Vector((0, 1, 0)) * (r * 0.8 * math.sin(f))
            verts.append(M @ (Vector((cx, 0, cz)) + off))
    for i in range(seg):
        for j in range(rseg):
            a = i * rseg + j
            b = ((i + 1) % seg) * rseg + j
            c = ((i + 1) % seg) * rseg + (j + 1) % rseg
            d = i * rseg + (j + 1) % rseg
            faces.append((a, b, c, d))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    set_smooth(me)
    me.materials.append(mat)
    return mesh_object(name, me)


def iris_texture(name, inner, outer, size=256, seed=3):
    """Dog iris: lighter centre, darker outer band, radial fibres, dark limbal ring,
    large soft pupil and a little shade under the upper lid."""
    u = (np.arange(size) + 0.5) / size * 2 - 1
    X, Z = np.meshgrid(u, u)                 # row 0 = bottom (Blender image order)
    r = np.sqrt(X * X + Z * Z)
    th = np.arctan2(Z, X)
    P = np.stack([np.cos(th) * 3, np.sin(th) * 3, r * 4], axis=-1).reshape(-1, 3)
    fib = vnoise(P * np.array([6.0, 6.0, 1.0]), 1.0, seed).reshape(size, size)
    base = mix(np.asarray(inner), np.asarray(outer), smooth(0.40, 0.95, r))
    base = base * (0.80 + 0.35 * fib)[..., None]
    base = mix(base, np.asarray(inner) * 1.08, 0.30 * (1 - smooth(0.42, 0.62, r)))   # bright collarette
    base = mix(base, np.array([0.03, 0.03, 0.035]), smooth(0.86, 0.98, r))          # limbal ring
    base = mix(base, np.array([0.006, 0.006, 0.008]), 1 - smooth(0.38, 0.44, r))    # pupil
    base = base * (0.72 + 0.28 * (1 - smooth(0.2, 1.0, Z)))[..., None]              # upper-lid shade
    rgba = np.concatenate([srgb(base), np.ones((size, size, 1))], axis=-1).astype(np.float32)
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def iris_disc(name, rx, rz, dome, y0, mat, M, rings=8, seg=40):
    """Slightly domed disc facing local -Y with planar UVs (top of texture = +Z)."""
    verts = [(0.0, y0 - dome, 0.0)]
    for i in range(1, rings + 1):
        t = i / rings
        for j in range(seg):
            a = 2 * math.pi * j / seg
            verts.append((rx * t * math.cos(a), y0 - dome * (1 - t * t), rz * t * math.sin(a)))
    faces = []
    for j in range(seg):
        faces.append((0, 1 + (j + 1) % seg, 1 + j))
    for i in range(rings - 1):
        a0, a1 = 1 + i * seg, 1 + (i + 1) * seg
        for j in range(seg):
            k = (j + 1) % seg
            faces.append((a0 + j, a0 + k, a1 + k, a1 + j))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(M @ Vector(v)) for v in verts], [], faces)
    uv = me.uv_layers.new(name="UVMap")
    loop_uv = []
    for f in faces:
        for vi in f:
            x, _, z = verts[vi]
            loop_uv += [0.5 + x / (2 * rx), 0.5 + z / (2 * rz)]
    uv.data.foreach_set("uv", loop_uv)
    set_smooth(me)
    me.materials.append(mat)
    return mesh_object(name, me)


# --------------------------------------------------------------------------
# Hair cards
# --------------------------------------------------------------------------

FUR_CLASSES = [  # name, linear colour, luminance lower bound
    ("white", WHITE, 0.62),
    ("light", np.array([0.50, 0.54, 0.57]), 0.40),
    ("grey", np.array([0.29, 0.32, 0.35]), 0.17),
    ("dark", np.array([0.095, 0.105, 0.115]), 0.05),
    ("black", np.array([0.020, 0.022, 0.026]), -1.0),
]


def strand_texture(name, rgb, seed, mixin=None, mix_frac=0.0, W=128, H=256):
    """Alpha-cut strand sheet: roots at v=0 (bottom row), wispy tips at the top."""
    r = np.random.default_rng(seed)
    X = np.arange(W)[None, :] + 0.5
    Y = (np.arange(H)[:, None] + 0.5) / H
    one_minus = np.ones((H, W))
    acc_c = np.zeros((H, W, 3))
    acc_a = np.zeros((H, W))
    for _ in range(34):
        x0 = r.uniform(0.10, 0.90) * W
        length = r.uniform(0.55, 1.0)
        bend = r.uniform(-0.14, 0.14) * W
        w0 = r.uniform(2.6, 5.2)
        tint = rgb * r.uniform(0.80, 1.15)
        if mixin is not None and r.random() < mix_frac:
            tint = mixin * r.uniform(0.85, 1.1)
        t = np.clip(Y / length, 0, 1)
        xc = x0 + bend * t * t
        sigma = np.maximum(w0 * (1 - 0.85 * t), 0.5)
        a = np.exp(-0.5 * ((X - xc) / sigma) ** 2) * (Y < length)
        acc_c += a[..., None] * tint
        acc_a += a
        one_minus *= 1 - a
    alpha = 1 - one_minus
    root = (1 - smooth(0.18, 0.32, Y)) * (1 - smooth(0.40, 0.48, np.abs(X / W - 0.5)))
    alpha = np.maximum(alpha, 0.95 * root)
    col = np.where(acc_a[..., None] > 1e-4, acc_c / np.maximum(acc_a, 1e-4)[..., None], rgb)
    col = col * (0.82 + 0.18 * smooth(0.0, 0.5, Y))[..., None]  # darker roots read as depth
    alpha = smooth(0.35, 0.55, alpha)                 # near-binary, matches SceneKit cutout
    rgba = np.concatenate([srgb(col), alpha[..., None]], axis=-1).astype(np.float32)
    img = bpy.data.images.new(name, W, H, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def clump_texture(name, rgb, seed, W=128, H=256):
    """Sculpted fur clump (feather/petal): pointed tip, grooves converging to the tip,
    lit ridge and darker edges, as in the stylised reference sculpt."""
    r = np.random.default_rng(seed)
    u = (np.arange(W)[None, :] + 0.5) / W
    v = (np.arange(H)[:, None] + 0.5) / H
    hw = 0.47 * np.sin(np.pi * (0.10 + 0.40 * v)) ** 0.5 * np.clip(1 - v ** 2.4, 0, 1) ** 0.55
    d = np.abs(u - 0.5) / np.maximum(hw, 1e-4)
    alpha = (1 - smooth(0.88, 1.0, d)) * (v < 0.995)
    shade = 1 - 0.22 * d ** 2
    for k in range(-3, 4):
        xk = 0.5 + k / 3.4 * hw * 0.95 + r.normal(0, 0.004)
        shade = shade - 0.09 * np.exp(-0.5 * ((u - xk) / 0.010) ** 2) * (v < 0.93)
    ridge = np.exp(-0.5 * ((u - 0.5) / (0.10 * np.maximum(hw, 0.02) + 0.01)) ** 2)
    shade = shade * (0.88 + 0.12 * smooth(0.0, 0.35, v))
    lum = float(np.dot(rgb, [0.2126, 0.7152, 0.0722]))
    sheen = (0.035 if lum < 0.1 else 0.03) * ridge * smooth(0.1, 0.5, v)
    base_rgb = np.asarray(rgb) * (1.15 if lum > 0.6 else 1.0)
    col = np.clip(base_rgb * shade[..., None] + sheen[..., None], 0, 1)
    alpha = smooth(0.35, 0.55, alpha)
    rgba = np.concatenate([srgb(col), alpha[..., None]], axis=-1).astype(np.float32)
    img = bpy.data.images.new(name, W, H, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


FUR_MATS = {}
for k, (cls, rgb, _) in enumerate(FUR_CLASSES):
    neighbour = {"white": GREY * 1.6, "light": BLACK, "grey": BLACK, "dark": GREY, "black": GREY}[cls]
    frac = {"white": 0.08, "light": 0.22, "grey": 0.25, "dark": 0.15, "black": 0.10}[cls]
    img = strand_texture(f"fur strands {cls}", rgb, 100 + k, neighbour, frac)
    FUR_MATS[("strand", cls)] = textured_material(f"fur_{cls}", img, roughness=0.8, alpha=True)
    img = clump_texture(f"fur clump {cls}", rgb, 200 + k)
    m = textured_material(f"fur_clump_{cls}", img, roughness=0.85, alpha=True)
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.12
            break
    FUR_MATS[("clump", cls)] = m


def sample_surface(me, n):
    me.calc_loop_triangles()
    tri = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tri)
    tri = tri.reshape(-1, 3)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    nor = np.empty(len(me.vertices) * 3, np.float32)
    try:
        me.vertex_normals.foreach_get("vector", nor)
    except AttributeError:
        me.vertices.foreach_get("normal", nor)
    nor = nor.reshape(-1, 3).astype(np.float64)
    a, b, c = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    idx = rng.choice(len(tri), n, p=area / area.sum())
    r1 = np.sqrt(rng.random(n))
    r2 = rng.random(n)
    w = np.stack([1 - r1, r1 * (1 - r2), r1 * r2], axis=1)
    P = sum(co[tri[idx, k]] * w[:, k:k + 1] for k in range(3))
    N = sum(nor[tri[idx, k]] * w[:, k:k + 1] for k in range(3))
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    return P, N


def unit(v):
    return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)


def classify(part, P):
    """Pick a hair colour class from the marking colour at each root (with jitter)."""
    c = color(part, P)
    lum = c @ np.array([0.2126, 0.7152, 0.0722]) + rng.normal(0, 0.035, len(P))
    bounds = np.array([b for _, _, b in FUR_CLASSES])
    cls = np.argmax(lum[:, None] > bounds[None, :], axis=1)
    if part in ("head_fur", "ear", "ruff"):          # the sculpted head is pure black & white
        cls = np.where(lum > 0.32, 0, len(FUR_CLASSES) - 1)
    return cls


def add_fur(part_obj, color_part, count, rule, droop=0.25, width=0.5, style="strand"):
    """rule(P, N) -> (L lengths, F flow dirs, lift radians). Returns fur objects."""
    P, N = sample_surface(part_obj.data, count * 2)
    L, F, lift = rule(P, N)
    keep = np.where(L > 1e-4)[0][:count]
    P, N, L, F, lift = P[keep], N[keep], L[keep], F[keep], lift[keep]
    n = len(P)
    if n == 0:
        return []
    Ft = F - np.sum(F * N, axis=1, keepdims=True) * N
    bad = np.linalg.norm(Ft, axis=1) < 1e-3
    Ft[bad] = np.cross(N[bad], np.array([1.0, 0, 0]))
    Ft = unit(Ft)
    D = unit(Ft * np.cos(lift)[:, None] + N * np.sin(lift)[:, None])
    S0 = unit(np.cross(N, D))
    phi = rng.uniform(-0.8, 0.8, n) if style == "strand" else rng.uniform(-0.22, 0.22, n)
    S = unit(S0 * np.cos(phi)[:, None] + np.cross(D, S0) * np.sin(phi)[:, None])
    W = np.maximum(L * width, 0.018)
    root = P - N * np.minimum(0.012, 0.15 * L)[:, None]
    ts = np.array([0.0, 0.34, 0.67, 1.0])
    down = np.array([0, 0, -1.0])
    levels = []
    for t in ts:
        centre = root + D * (L * t)[:, None] + down * (droop * L * t * t)[:, None]
        half = (W * (1 - 0.55 * t) / 2)[:, None]
        levels.append(np.stack([centre - S * half, centre + S * half], axis=1))
    V = np.stack(levels, axis=1)                      # n, 4 levels, 2, 3
    Nrm = unit(N * 0.8 + D * 0.2)
    cls = classify(color_part, P)
    objs = []
    for k, (cname, _, _) in enumerate(FUR_CLASSES):
        sel = np.where(cls == k)[0]
        if len(sel) == 0:
            continue
        verts = V[sel].reshape(-1, 3)
        normals = np.repeat(Nrm[sel], 8, axis=0)
        faces, uvs = [], []
        for c in range(len(sel)):
            base = c * 8
            for lv in range(3):
                a = base + 2 * lv
                faces.append((a, a + 1, a + 3, a + 2))
                t0, t1 = ts[lv], ts[lv + 1]
                uvs += [(0, t0), (1, t0), (1, t1), (0, t1)]
        me = bpy.data.meshes.new(f"fur_{part_obj.name}_{style}_{cname}")
        me.from_pydata(verts.tolist(), [], faces)
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", np.array(uvs, np.float32).ravel())
        set_smooth(me)
        try:
            me.normals_split_custom_set_from_vertices(normals.tolist())
        except Exception:
            pass
        me.materials.append(FUR_MATS[(style, cname)])
        objs.append(mesh_object(me.name, me))
    return objs


# --------------------------------------------------------------------------
# Coat textures: bake world positions, paint markings per pixel
# --------------------------------------------------------------------------

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1


def select_only(obj):
    for o in scene.objects:
        o.select_set(False)
    view_layer.objects.active = obj
    obj.select_set(True)


def unwrap(obj):
    select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.012)
    bpy.ops.object.mode_set(mode="OBJECT")


def paint_coat(obj, part, size):
    unwrap(obj)
    pos_img = bpy.data.images.new(obj.name + " pos", size, size, alpha=False, float_buffer=True)
    bake = bpy.data.materials.new("bake position")
    try:
        bake.use_nodes = True
    except Exception:
        pass
    nt = bake.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    add = nt.nodes.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    add.inputs[1].default_value = (4.0, 4.0, 4.0)
    sc = nt.nodes.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    sc.inputs["Scale"].default_value = 0.125
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = pos_img
    nt.nodes.active = tex
    nt.links.new(geo.outputs["Position"], add.inputs[0])
    nt.links.new(add.outputs["Vector"], sc.inputs[0])
    nt.links.new(sc.outputs["Vector"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    obj.data.materials.clear()
    obj.data.materials.append(bake)
    select_only(obj)
    bpy.ops.object.bake(type="EMIT", margin=8, use_clear=True)
    arr = np.empty(size * size * 4, np.float32)
    pos_img.pixels.foreach_get(arr)
    arr = arr.reshape(size, size, 4)
    valid = arr[..., :3].max(axis=-1) > 1e-6
    print(f"[delta] coat {obj.name}: baked {valid.mean():.2f} of {size}px")
    col = np.tile(GREY, (size, size, 1))
    col[valid] = color(part, arr[..., :3][valid].astype(np.float64) * 8.0 - 4.0)
    rgba = np.concatenate([srgb(col), np.ones((size, size, 1))], axis=-1).astype(np.float32)
    img = bpy.data.images.new(obj.name + " coat", size, size, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    bpy.data.images.remove(pos_img)
    obj.data.materials.clear()
    bpy.data.materials.remove(bake)
    obj.data.materials.append(textured_material("coat_" + obj.name, img))


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

root = empty("delta_root")
head = empty("delta_head", root, tuple(HEAD))
jaw = empty("delta_jaw", head, (0, -0.20, -0.08))
tongue = empty("delta_tongue", head, (0, -0.35, -0.115))
tail = empty("delta_tail", root, tuple(TAIL))
legs, knees = {}, {}
for tag, (front, side, pivot, knee) in LEGS.items():
    legs[tag] = empty(f"delta_leg_{tag}", root, pivot)
    knees[tag] = empty(f"delta_knee_{tag}", legs[tag], knee)
eye_nodes = {}
for side_name, e in EYES.items():
    sgn = -1 if side_name == "right" else 1
    look = Vector((sgn * 0.40, -1.0, 0.08)).normalized()
    rot = look.to_track_quat("-Y", "Z").to_euler()
    centre = tuple(Vector(tuple(e)) + look * 0.003)
    eye_nodes[side_name] = (empty(f"delta_eye_{side_name}", head, centre, rot),
                            empty(f"delta_closed_eye_{side_name}", head, centre, rot))
ears = {}
for side_name, sgn in (("right", -1), ("left", 1)):
    ears[side_name] = empty(f"delta_ear_{side_name}", head, (sgn * 0.115, 0.05, 0.255),
                            (-0.25, sgn * 0.30, sgn * 0.25))
view_layer.update()
H = Matrix.Translation(Vector(HEAD))
parts = []   # (object, parent empty)

# Torso with neck base.
body = prim_union("delta_body", [
    ("ell", (0, -0.50, 1.00), (0.37, 0.38, 0.40)),
    ("ell", (0, -0.08, 0.99), (0.35, 0.42, 0.37)),
    ("ell", (0, 0.34, 1.00), (0.32, 0.33, 0.33)),
    ("ell", (0, 0.62, 0.98), (0.32, 0.26, 0.31)),
    ("cap", (0, -0.70, 1.12), (0, -0.98, 1.36), 0.21, 0.17),
], voxel=0.028, smooth_iter=8)
parts.append((body, root, "body", 1024))

ruff = prim_union("delta_chest_mane", [
    ("ell", (0, -0.84, 1.40), (0.30, 0.20, 0.22)),
    ("ell", (0, -0.74, 1.30), (0.38, 0.26, 0.28)),
    ("ell", (0, -0.86, 1.16), (0.36, 0.30, 0.36), (-0.3, 0, 0)),
    ("ell", (0, -0.92, 1.02), (0.26, 0.20, 0.20)),
    ("ell", (0, -0.80, 1.34), (0.33, 0.26, 0.24)),
    ("ell", (0, -0.70, 1.10), (0.37, 0.22, 0.34)),
], voxel=0.025, smooth_iter=8)
parts.append((ruff, root, "ruff", 512))

head_mesh = prim_union("delta_face", [
    # Sheltie head: a long blunt wedge, flat skull, muzzle about as long as the skull.
    ("loft", [(0.24, 0.10, 0.13, 0.12, 0.15),
              (0.14, 0.12, 0.175, 0.165, 0.19),
              (0.02, 0.12, 0.185, 0.165, 0.19),
              (-0.10, 0.11, 0.165, 0.15, 0.18),
              (-0.18, 0.085, 0.142, 0.125, 0.165),
              (-0.235, 0.062, 0.124, 0.10, 0.145),
              (-0.285, 0.044, 0.110, 0.088, 0.128),
              (-0.33, 0.026, 0.096, 0.077, 0.112),
              (-0.37, 0.01, 0.080, 0.065, 0.094),
              (-0.40, -0.004, 0.052, 0.046, 0.066)], 2.4),
    ("ell", (0.10, -0.06, 0.0), (0.085, 0.13, 0.10)),
    ("ell", (-0.10, -0.06, 0.0), (0.085, 0.13, 0.10)),
    ("ell", (0, 0.16, -0.04), (0.14, 0.13, 0.17)),
], voxel=0.011, smooth_iter=5, M=H)
parts.append((head_mesh, head, "head", 1024))

J = H @ Matrix.Translation((0, -0.20, -0.08))
jaw_mesh = prim_union("lower_jaw", [
    ("ell", (0, -0.05, -0.03), (0.07, 0.09, 0.038)),
    ("ell", (0, -0.12, -0.032), (0.052, 0.07, 0.03)),
    ("ell", (0, -0.165, -0.03), (0.036, 0.03, 0.02)),
], voxel=0.010, smooth_iter=4, M=J)
parts.append((jaw_mesh, jaw, "jaw", 256))

for side_name, ear in ears.items():
    Me = ear.matrix_world.copy()
    ear_mesh = prim_union(f"ear_{side_name}", [
        ("ell", (0, 0, 0.05), (0.085, 0.03, 0.08)),
        ("ell", (0, -0.01, 0.115), (0.062, 0.024, 0.05)),
        ("ell", (0, -0.04, 0.15), (0.048, 0.02, 0.034), (-1.15, 0, 0)),
        ("ell", (0, -0.07, 0.135), (0.036, 0.016, 0.026), (-1.6, 0, 0)),
    ], voxel=0.009, smooth_iter=5, M=Me)
    parts.append((ear_mesh, ear, "ear", 256))

for tag, (front, side, pivot, knee) in LEGS.items():
    Mu = legs[tag].matrix_world.copy()
    Mk = knees[tag].matrix_world.copy()
    if front:
        upper = prim_union(f"upper_leg_{tag}", [
            ("ell", (0, 0.02, 0.10), (0.13, 0.17, 0.22)),
            ("cap", (0, 0, 0.0), (0, 0, -0.43), 0.10, 0.08),
        ], voxel=0.016, M=Mu)
        lower = prim_union(f"lower_leg_{tag}", [
            ("cap", (0, 0, 0.02), (0, -0.015, -0.33), 0.075, 0.065),
            ("ell", (0, -0.05, -0.36), (0.085, 0.11, 0.05)),
        ], voxel=0.013, smooth_iter=4, M=Mk)
        cpart = "leg_f"
    else:
        upper = prim_union(f"upper_leg_{tag}", [
            ("ell", (0, 0.02, 0.0), (0.14, 0.22, 0.25)),
            ("cap", (0, 0.04, -0.10), (0, 0.12, -0.44), 0.10, 0.068),
        ], voxel=0.016, M=Mu)
        lower = prim_union(f"lower_leg_{tag}", [
            ("cap", (0, 0, 0.02), (0, -0.04, -0.33), 0.07, 0.062),
            ("ell", (0, -0.075, -0.37), (0.08, 0.11, 0.05)),
        ], voxel=0.013, smooth_iter=4, M=Mk)
        cpart = "leg_h"
    parts.append((upper, legs[tag], cpart, 512))
    parts.append((lower, knees[tag], cpart, 512))

Mt = Matrix.Translation(Vector(TAIL))
tail_prims = [("cap", TAIL_CHAIN[i][:3], TAIL_CHAIN[i + 1][:3], TAIL_CHAIN[i][3], TAIL_CHAIN[i + 1][3])
              for i in range(len(TAIL_CHAIN) - 1)]
tail_mesh = prim_union("tail_core", tail_prims, voxel=0.016, smooth_iter=5, M=Mt)
parts.append((tail_mesh, tail, "tail", 512))

# ---- fur rules (world-space P, N) -------------------------------------------


def rule_body(P, N):
    n = len(P)
    L = np.full(n, 0.10)
    L = np.where(P[:, 2] < 0.88, 0.13, L)
    L = np.where(N[:, 2] < -0.4, 0.16, L)
    L = np.where(N[:, 2] > 0.6, 0.085, L)
    L = np.where(P[:, 1] < -0.66, 0.0, L)
    L = L * rng.uniform(0.8, 1.2, n)
    F = np.tile([0.0, 1.0, -0.55], (n, 1))
    return L, F, np.full(n, math.radians(25))


def rule_ruff(P, N):
    """Sheltie mane: a full ring around the neck; front hangs down, top flows back."""
    n = len(P)
    z = P[:, 2]
    L = 0.15 + 0.06 * smooth(0.95, 1.35, z) - 0.05 * smooth(0.95, 0.80, z)
    L = L * rng.uniform(0.8, 1.15, n)
    top = smooth(0.2, 0.6, N[:, 2])
    F = mix(np.array([0.0, -0.4, -1.0]), np.array([0.0, 1.0, -0.35]), top)
    side = np.sign(P[:, 0])[:, None] * np.array([1.0, 0, 0]) * 0.35
    return L, F + side, np.full(n, math.radians(42))


def rule_head(P, N):
    """Sculpted clumps: black crown tufts sweep up and out above the eyes, a white frill
    frames the cheeks and chin; the muzzle and eye area stay smooth."""
    n = len(P)
    Lc = P - HEAD
    lx, ly, lz = Lc[:, 0], Lc[:, 1], Lc[:, 2]
    ax = np.abs(lx)
    out = np.sign(lx)[:, None] * np.array([1.0, 0, 0])
    crown = (lz > 0.13) & (ly > -0.16) & (ax > 0.05)
    blaze_top = (lz > 0.13) & (ly > -0.16) & (ax <= 0.05)
    frill = (ly > -0.12) & (lz <= 0.13)
    throat = (lz < -0.06) & (ly > -0.14)
    L = np.zeros(n)
    L = np.where(crown, 0.16 + 0.06 * smooth(-0.1, 0.15, ly), L)
    L = np.where(blaze_top, 0.0, L)
    L = np.where(frill, 0.12 + 0.08 * smooth(-0.12, 0.12, ly), L)
    L = np.where(throat, np.maximum(L, 0.14), L)
    cheek = (ly <= -0.12) & (ly > -0.26) & (lz > -0.08) & (lz < 0.10) & (ax > 0.06)
    L = np.where(cheek, 0.04 + 0.04 * smooth(-0.26, -0.12, ly), L)
    for e in EYES.values():
        L = np.where(np.linalg.norm(Lc - e, axis=1) < 0.05, 0.0, L)
    forehead = (ax < 0.085) & (lz > 0.04) & (ly < 0.06)          # keep the white blaze smooth
    L = np.where(forehead, 0.0, L)
    L = L * rng.uniform(0.85, 1.15, n)
    F = np.tile([0.0, 1.0, 0.25], (n, 1))
    F = np.where(crown[:, None], np.array([0.0, 0.55, 0.15]) + 1.4 * out, F)
    F = np.where(frill[:, None], np.array([0.0, 0.8, -0.25]) + 0.9 * out, F)
    F = np.where(throat[:, None], np.array([0.0, 0.2, -1.0]), F)
    F = np.where(cheek[:, None], np.array([0.0, 1.0, -0.1]) + 0.4 * out, F)
    lift = np.where(crown, math.radians(28), math.radians(30))
    lift = np.where(frill | throat, math.radians(42), lift)
    lift = np.where(cheek, math.radians(16), lift)
    return L, F, lift


def make_rule_ear(ear_empty):
    """Ear tufts sweep outward and down, so the ears read as part of the black 'wings'."""
    up = np.array(ear_empty.matrix_world.to_3x3() @ Vector((0, 0, 1)))
    side = np.sign(ear_empty.matrix_world.translation.x)
    flow = up * 0.45 + np.array([side * 1.0, 0.35, -0.25])

    def rule(P, N):
        n = len(P)
        L = rng.uniform(0.12, 0.18, n)
        return L, np.tile(flow, (n, 1)), np.full(n, math.radians(30))
    return rule


def rule_jaw(P, N):
    n = len(P)
    L = np.where(N[:, 2] < -0.3, 0.035, 0.0) * rng.uniform(0.8, 1.2, n)
    return L, np.tile([0.0, 0.3, -1.0], (n, 1)), np.full(n, math.radians(15))


def rule_leg_upper_f(P, N):
    n = len(P)
    L = np.where(N[:, 1] > 0.3, 0.14, 0.07) * rng.uniform(0.8, 1.2, n)
    L = np.where(P[:, 2] > 1.05, 0.0, L)
    return L, np.tile([0.0, 0.25, -1.0], (n, 1)), np.full(n, math.radians(20))


def rule_leg_lower(P, N):
    n = len(P)
    L = np.where(N[:, 1] > 0.4, 0.09, 0.05)
    L = np.where(P[:, 2] < 0.07, 0.03, L) * rng.uniform(0.8, 1.2, n)
    return L, np.tile([0.0, 0.25, -1.0], (n, 1)), np.full(n, math.radians(18))


def rule_leg_upper_h(P, N):
    n = len(P)
    L = np.where(N[:, 1] > 0.3, 0.17, 0.12) * rng.uniform(0.8, 1.2, n)
    return L, np.tile([0.0, 0.8, -1.0], (n, 1)), np.full(n, math.radians(20))


CHAIN_W = np.array([np.array(c[:3]) + TAIL for c in TAIL_CHAIN])


def rule_tail(P, N):
    n = len(P)
    best_d = np.full(n, 1e9)
    F = np.zeros((n, 3))
    for i in range(len(CHAIN_W) - 1):
        a, b = CHAIN_W[i], CHAIN_W[i + 1]
        ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        d = np.linalg.norm(P - (a + t[:, None] * ab), axis=1)
        better = d < best_d
        best_d = np.where(better, d, best_d)
        F[better] = ab / np.linalg.norm(ab)
    L = rng.uniform(0.15, 0.22, n)
    return L, F, np.full(n, math.radians(35))


FUR_PLAN = {  # object name -> (colour part, count, rule, droop)
    "delta_body": ("body", 2200, rule_body, 0.25),
    "delta_chest_mane": ("ruff", 1500, rule_ruff, 0.18, 0.62, "clump"),
    "delta_face": ("head_fur", 2600, rule_head, 0.32, 0.72, "clump"),
    "lower_jaw": ("jaw", 60, rule_jaw, 0.2),
    "ear_right": ("ear", 150, make_rule_ear(ears["right"]), 0.25, 0.7, "clump"),
    "ear_left": ("ear", 150, make_rule_ear(ears["left"]), 0.25, 0.7, "clump"),
    "tail_core": ("tail", 650, rule_tail, 0.15),
}
for tag, (front, *_rest) in LEGS.items():
    FUR_PLAN[f"upper_leg_{tag}"] = ("leg_f" if front else "leg_h", 320 if front else 360,
                                    rule_leg_upper_f if front else rule_leg_upper_h, 0.2)
    FUR_PLAN[f"lower_leg_{tag}"] = ("leg_f" if front else "leg_h", 220 if front else 180,
                                    rule_leg_lower, 0.15)

fur_objects = []   # (object, parent)
for obj, parent, cpart, _size in parts:
    plan = FUR_PLAN.get(obj.name)
    if plan:
        for f in add_fur(obj, plan[0], plan[1], plan[2], plan[3], plan[4] if len(plan) > 4 else 0.5,
                         plan[5] if len(plan) > 5 else "strand"):
            fur_objects.append((f, parent))

for obj, parent, cpart, size in parts:
    paint_coat(obj, cpart, size)

# ---- small parts: nose, tongue, eyes ------------------------------------------
small = []
nose = plain_prims("delta_nose", [((0, -0.402, 0.004), (0.047, 0.032, 0.033), (0, 0, 0)),
                                  ((0, -0.388, 0.022), (0.037, 0.026, 0.02), (0, 0, 0))],
                   material("nose black", (0.02, 0.022, 0.025), 0.35, 0.5), M=H)
small.append((nose, head))
T = H @ Matrix.Translation((0, -0.35, -0.115))
tongue_mesh = plain_prims("tongue_shape", [((0, -0.02, -0.012), (0.038, 0.075, 0.011), (-0.45, 0, 0))],
                          material("tongue pink", (0.80, 0.25, 0.32), 0.5, 0.4), M=T)
small.append((tongue_mesh, tongue))
iris_imgs = {"right": iris_texture("iris dark right", (0.085, 0.06, 0.045), (0.025, 0.02, 0.018), seed=3),
             "left": iris_texture("iris dark left", (0.085, 0.06, 0.045), (0.025, 0.02, 0.018), seed=5)}
iris_mats = {}
for side_name, img in iris_imgs.items():
    m = textured_material(f"Delta {side_name} iris", img, roughness=0.12)
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.7
            break
    iris_mats[side_name] = m
glint_mat = material("eye catchlight", (1.0, 1.0, 1.0), 0.1, 0.5)
try:
    gb = glint_mat.node_tree.nodes.get("Principled BSDF")
    gb.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    gb.inputs["Emission Strength"].default_value = 1.2
except KeyError:
    pass
for side_name, (open_e, closed_e) in eye_nodes.items():
    Mo = open_e.matrix_world.copy()
    small.append((plain_prims(f"eyeball_{side_name}", [((0, 0, 0), (0.033, 0.014, 0.029), (0, 0, 0))],
                              material("eye dark", (0.035, 0.025, 0.02), 0.25, 0.5), M=Mo), open_e))
    small.append((iris_disc(f"iris_{side_name}", 0.029, 0.028, 0.0045, -0.0135,
                            iris_mats[side_name], Mo), open_e))
    small.append((plain_prims(f"glint_{side_name}", [((-0.0085, -0.0188, 0.0095), (0.0052, 0.001, 0.0049), (0, 0, 0)),
                                                    ((0.0078, -0.0180, -0.0068), (0.0024, 0.0007, 0.0022), (0, 0, 0))],
                              glint_mat, M=Mo, segments=12), open_e))
    Mr = Mo @ Matrix.Translation((0, -0.0142, 0))
    small.append((ring(f"eye_rim_{side_name}", 0.0293, 0.0032, 1.0, 0.76,
                       material("eye rim", (0.015, 0.016, 0.02), 0.5), Mr), open_e))
    lid_rgb = tuple(color("head", np.array(Mo.translation)[None, :] + np.array([[0, -0.02, 0.03]]))[0])
    small.append((plain_prims(f"sleep_lid_{side_name}", [((0, -0.010, 0), (0.046, 0.021, 0.040), (0, 0, 0))],
                              material(f"eyelid {side_name}", lid_rgb, 0.9), M=Mo), closed_e))
    small.append((plain_prims(f"sleep_line_{side_name}", [((0, -0.029, -0.004), (0.040, 0.0045, 0.0055), (0, 0, 0))],
                              material("eye rim", (0.015, 0.016, 0.02), 0.5), M=Mo, segments=16), closed_e))

# ---- parent everything with identity local transforms ------------------------
view_layer.update()
for obj, parent in [(o, p) for o, p, *_ in parts] + fur_objects + small:
    obj.data.transform(parent.matrix_world.inverted())
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)

total = 0
for o in scene.objects:
    if o.type == "MESH":
        total += len(o.data.polygons)
print(f"[delta] mesh objects: {sum(o.type == 'MESH' for o in scene.objects)}, faces: {total}")
for obj, *_ in parts:
    print(f"[delta]   {obj.name}: {len(obj.data.polygons)} faces")

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Delta.blend"))
bpy.ops.wm.usd_export(filepath=str(OUT / "Delta.usdz"),
                      selected_objects_only=False, export_animation=False,
                      export_lights=False, export_cameras=False,
                      export_materials=True, generate_preview_surface=True,
                      convert_orientation=False)
print(f"[delta] wrote {OUT / 'Delta.usdz'}")
