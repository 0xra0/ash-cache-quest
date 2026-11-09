"""outline.json -> splinter.glb (game low poly) + textured preview renders.

    blender -b -P bl_splinter.py -- <dir>

Visual hull of two views: the front outline (with the key-ring hole) extruded
through the thickness, intersected with the left profile extruded across the
width. UVs are a per-face planar projection onto the view the face points at,
using the mm -> uv maps prep.py wrote.
"""
import bpy, bmesh, json, math, sys
from mathutils import Vector

d = sys.argv[sys.argv.index("--") + 1]
o = json.load(open(f"{d}/outline.json"))
MM = 0.001
W = 20  # mm, half-width of the profile prism; wider than the part
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def prism(name, loops, to3, depth, axis):
    """Fill `loops` (2D, first outer, rest holes) and extrude by depth along axis."""
    bm = bmesh.new()
    edges = []
    for loop in loops:
        vs = [bm.verts.new(to3(a, b)) for a, b in loop]
        edges += [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
    faces = [g for g in bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)["geom"]
             if isinstance(g, bmesh.types.BMFace)]
    ext = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(bm, vec=Vector(axis) * depth, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


T = o["thickness"]
loops = [o["outer"]] + ([o["hole"]] if o["hole"] else [])
body = prism("body", loops, lambda x, y: (x * MM, y * MM, 0), T * MM, (0, 0, 1))
side = prism("side", [o["profile"]], lambda z, y: (-W * MM, y * MM, z * MM), 2 * W * MM, (1, 0, 0))
m = body.modifiers.new("hull", "BOOLEAN")
m.operation, m.solver, m.object = "INTERSECT", "EXACT", side
bpy.context.view_layer.objects.active = body
bpy.ops.object.modifier_apply(modifier="hull")
bpy.data.objects.remove(side)

# soft edges: one bevel segment catches light the way the sheet's edges do
bv = body.modifiers.new("bevel", "BEVEL")
bv.width, bv.segments, bv.limit_method, bv.angle_limit = 0.25 * MM, 1, "ANGLE", math.radians(35)
bv.harden_normals = True
bpy.ops.object.modifier_apply(modifier="bevel")
bpy.ops.object.modifier_add(type="TRIANGULATE")
bpy.ops.object.modifier_apply(modifier="Triangulate")

# planar UVs from the view each face points at
me = body.data
uvl = me.uv_layers.new(name="UVMap")
for p in me.polygons:
    n = p.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    if ax == 2:
        view, coord = ("front" if n.z > 0 else "back"), "x"
    else:  # ends (Y) borrow the left strip; they are a few mm of plain body
        view, coord = ("right" if (ax == 0 and n.x > 0) else "left"), "z"
    au, bu, av, bv_ = o["uv"][view]
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co / MM
        c = co.x if coord == "x" else co.z
        uvl.data[li].uv = (au * c + bu, av * co.y + bv_)

mat = bpy.data.materials.new("o1140_splinter")
me.materials.append(mat)
body.name = me.name = "submesh_00_LOD_1"
xs = [v.co for v in me.vertices]
print("SPLINTER", len(me.polygons), "tris, bbox mm",
      [round(min(c[i] for c in xs) / MM, 2) for i in range(3)], [round(max(c[i] for c in xs) / MM, 2) for i in range(3)])
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.ops.export_scene.gltf(filepath=f"{d}/splinter.glb", use_selection=True, export_format="GLB",
                          export_materials="PLACEHOLDER", export_tangents=True, export_normals=True,
                          export_yup=True)

# textured preview (the exporter leaves the slot empty)
me.materials.clear()
me.materials.append(mat)
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
for key, sock, cs in (("d01", "Base Color", "sRGB"), ("r01", "Roughness", "Non-Color"), ("m01", "Metallic", "Non-Color")):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(f"{d}/o1140_splinter_{key}.png")
    t.image.colorspace_settings.name = cs
    nt.links.new(t.outputs["Color"], bsdf.inputs[sock])
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 900, 600
sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.5, 0.5, 0.52)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4
sun.rotation_euler = (math.radians(40), 0, math.radians(25))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
cam.data.lens = 85
sc.collection.objects.link(cam)
sc.camera = cam
for name, loc in (("front", (0.05, -0.06, 0.12)), ("back", (-0.05, 0.06, -0.12)), ("edge", (0.14, -0.02, 0.03))):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector((0, 0, T * MM / 2)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{d}/prev_{name}.png"
    bpy.ops.render.render(write_still=True)
