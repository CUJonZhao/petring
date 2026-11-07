"""Render a local model QA preview; keep photos out of generated assets."""
from pathlib import Path
import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root / "Resources" / "Delta.blend"))

def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.camera_add(location=(3.0, -5.6, 2.7))
camera = bpy.context.object
aim(camera, (0, -0.25, 1.05))
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 3.5
bpy.context.scene.camera = camera
bpy.ops.object.light_add(type='AREA', location=(-3.0, -4.0, 5.0))
bpy.context.object.data.energy = 600
bpy.context.object.data.shape = 'DISK'
bpy.context.object.data.size = 5
bpy.ops.object.light_add(type='AREA', location=(3.0, 2.0, 3.0))
bpy.context.object.data.energy = 400
bpy.context.object.data.size = 4
world = bpy.context.scene.world
world.color = (0.32, 0.32, 0.32)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.render.resolution_x = 1000
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = True
scene.render.filepath = str(root / "Resources" / "Delta-preview.png")
bpy.ops.render.render(write_still=True)
