"""Closed / opened preview renders of body.glb + lid.glb.

    blender -b -P bl_prev.py -- <dir> [tex]

With `tex`, the shell gets the baked ash_case_{d01,r01,m01}.png from <dir>.
"""
import bpy, sys, math, json
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
d, TEX = a[0], "tex" in a[1:]
hx, hy, hz = json.load(open(f"{d}/case_dims.json"))["hinge"]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE" if TEX else "BLENDER_WORKBENCH"
sc.render.resolution_x = sc.render.resolution_y = 640
if not TEX:
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.35, 0.35, 0.38)
if TEX:
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc.collection.objects.link(sun)


def load(fn):
    before = set(sc.objects)
    bpy.ops.import_scene.gltf(filepath=f"{d}/{fn}.glb")
    return [o for o in sc.objects if o not in before and o.type == "MESH"]


body = load("body")
lid_parts = load("lid")
hinge = bpy.data.objects.new("hinge", None)
sc.collection.objects.link(hinge)
hinge.location = (hx, hy, hz)
for o in lid_parts:
    o.parent = hinge

if TEX:
    shell = bpy.data.materials.new("shell")
    nt = shell.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    for key, sock, cs in (("d01", "Base Color", "sRGB"), ("r01", "Roughness", "Non-Color"), ("m01", "Metallic", "Non-Color")):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(f"{d}/ash_case_{key}.png")
        t.image.colorspace_settings.name = cs
        nt.links.new(t.outputs["Color"], bsdf.inputs[sock])
    inner = bpy.data.materials.new("inner")
    inner.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.022, 1)
    for o in body + lid_parts:
        o.data.materials.clear()
        o.data.materials.append(shell if o.name.startswith("submesh_00") else inner)
else:
    for o in body + lid_parts:
        for m in o.data.materials:
            m.diffuse_color = (0.7, 0.7, 0.7, 1) if o.name.startswith("submesh_00") else (0.05, 0.05, 0.06, 1)

cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
sc.collection.objects.link(cam)
sc.camera = cam


def shot(name, ang, loc):
    hinge.rotation_euler = (math.radians(ang), 0, 0)
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector((0, 0, 0.17)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{d}/prev_{name}.png"
    bpy.ops.render.render(write_still=True)


shot("closed_front", 0, (0.55, -0.85, 0.55))
shot("open_front", -100, (0.55, -0.85, 0.75))
shot("open_back", -100, (-0.6, 0.9, 0.6))
