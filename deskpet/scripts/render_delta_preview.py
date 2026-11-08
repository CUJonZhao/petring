"""Render QA previews of Resources/Delta.blend into .work/ (and Resources/Delta-preview.png).

Views: app (same framing as the DeskPet window camera), side (Delta's right),
front, face (3/4 from her right, like reference photo 1) and face_left.
"""
import math
import shutil
from pathlib import Path

import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root / "Resources" / "Delta.blend"))
scene = bpy.context.scene
out = root / ".work"
out.mkdir(exist_ok=True)

engine = None
for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = name
        engine = name
        break
    except TypeError:
        pass
if engine is None:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
else:
    try:
        scene.eevee.taa_render_samples = 48
    except AttributeError:
        pass
print(f"[preview] engine {scene.render.engine}")

try:
    scene.view_settings.view_transform = "Standard"
except TypeError:
    pass
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.40, 0.41, 0.43, 1)
bg.inputs[1].default_value = 1.0
scene.render.film_transparent = False


def sun(name, direction_from, energy):
    light = bpy.data.lights.new(name, "SUN")
    light.energy = energy
    obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.rotation_euler = (-Vector(direction_from)).to_track_quat("-Z", "Y").to_euler()


sun("key", (-3.6, -6.0, 6.0), 3.0)
sun("rim", (3.0, 5.0, 3.0), 1.2)

# The app hides closed eyelids and the tongue until an animation needs them.
for obj in list(scene.objects):
    if obj.name.startswith(("delta_closed_eye", "delta_tongue")):
        for child in [obj] + list(obj.children_recursive):
            child.hide_render = True

cam_data = bpy.data.cameras.new("qa")
cam = bpy.data.objects.new("qa", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

views = {
    "app": dict(loc=(2.59, -5.0, 1.99), target=(0, 0, 0.63), fov=38, res=(560, 600)),
    "side": dict(loc=(-7.0, -0.30, 1.05), target=(0, -0.30, 1.05), ortho=3.7, res=(900, 680)),
    "front": dict(loc=(0, -7.0, 1.15), target=(0, 0, 1.15), ortho=2.6, res=(640, 800)),
    "face": dict(loc=(-1.25, -3.05, 1.85), target=(0, -1.32, 1.52), fov=24, res=(700, 700)),
    "face_left": dict(loc=(1.25, -3.05, 1.85), target=(0, -1.32, 1.52), fov=24, res=(700, 700)),
    "face_front": dict(loc=(0.0, -3.3, 1.62), target=(0, -1.30, 1.52), fov=22, res=(700, 700)),
    "top": dict(loc=(0, 0.0, 7.0), target=(0, 0.0, 0.0), ortho=3.4, res=(700, 900)),
}
for name, v in views.items():
    cam.location = v["loc"]
    up = "Y" if name != "top" else "X"
    cam.rotation_euler = (Vector(v["target"]) - Vector(v["loc"])).to_track_quat("-Z", "Y").to_euler()
    if "ortho" in v:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = v["ortho"]
    else:
        cam_data.type = "PERSP"
        cam_data.sensor_fit = "VERTICAL"
        cam_data.angle = math.radians(v["fov"])
    scene.render.resolution_x, scene.render.resolution_y = v["res"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out / f"preview_{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[preview] wrote preview_{name}.png")

shutil.copy(out / "preview_app.png", root / "Resources" / "Delta-preview.png")
