"""
Headless Blender script to render the 3D BrandCourt shield on a transparent background.
Run with:
  blender -b -P tools/blender/shield_poster.py
"""
import sys
import os

try:
    import bpy
    import math
except ImportError:
    print("Blender (bpy) is not available in the current environment.")
    sys.exit(0)

# Clear existing objects
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES' if 'CYCLES' in dir(bpy.types) else 'BLENDER_EEVEE'
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'WEBP'
scene.render.image_settings.quality = 90
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000

# Create camera
cam_data = bpy.data.cameras.new("Camera")
cam_obj = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
cam_obj.location = (0, -4.2, 0)
cam_obj.rotation_euler = (math.radians(90), 0, 0)

# Create key light & teal rim light
light_data1 = bpy.data.lights.new(name="KeyLight", type='AREA')
light_data1.energy = 300
light_obj1 = bpy.data.objects.new("KeyLight", light_data1)
scene.collection.objects.link(light_obj1)
light_obj1.location = (2, -3, 2.5)

light_data2 = bpy.data.lights.new(name="TealRim", type='POINT')
light_data2.color = (0.176, 0.831, 0.749)  # #2dd4bf
light_data2.energy = 450
light_obj2 = bpy.data.objects.new("TealRim", light_data2)
scene.collection.objects.link(light_obj2)
light_obj2.location = (-2.5, 1.5, 0.5)

# Render output path
output_path = os.path.abspath("frontend/public/landing/shield-poster.webp")
scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)
print(f"Rendered shield poster to {output_path}")

