"""hull.json -> <name>.glb (game low poly) + textured preview renders.

    blender -b -P bl_hull.py -- <dir> [flat] [bevel_m]

Visual hull: the front outline extruded along Y, intersected with the left
profile extruded along X and, when the sheet has one, the top outline along Z.
UVs are a planar projection onto the view each face points at. `flat` lays the
result on its back afterwards (front up), for chips and shards.
"""
import bpy, bmesh, json, math, sys
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index("--") + 1:]
d, FLAT = a[0], "flat" in a[1:]
BEVEL = float(next((x for x in a[1:] if x[0].isdigit()), "0.004"))
o = json.load(open(f"{d}/hull.json"))
E = max(o["height"], o["width"]) * 2  # prism half-length, beyond the part
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
PRISM = {  # view -> (2D -> 3D at the far side, extrusion direction)
    "front": (lambda p, q: (p, -E, q), (0, 1, 0)),
    "left": (lambda p, q: (-E, p, q), (1, 0, 0)),
    "top": (lambda p, q: (p, q, -E), (0, 0, 1)),
}


def prism(view, loops):
    to3, axis = PRISM[view]
    bm = bmesh.new()
    edges = []
    for loop in loops:
        vs = [bm.verts.new(to3(p, q)) for p, q in loop]
        edges += [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
    faces = [g for g in bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)["geom"]
             if isinstance(g, bmesh.types.BMFace)]
    ext = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(bm, vec=Vector(axis) * 2 * E, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(view)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(view, me)
    sc.collection.objects.link(ob)
    return ob


body = prism("front", o["loops"]["front"])
bpy.context.view_layer.objects.active = body
for v in ("left", "top"):
    if v in o["loops"]:
        cut = prism(v, o["loops"][v])
        m = body.modifiers.new(v, "BOOLEAN")
        m.operation, m.solver, m.object = "INTERSECT", "EXACT", cut
        bpy.ops.object.modifier_apply(modifier=v)
        bpy.data.objects.remove(cut)
bv = body.modifiers.new("bevel", "BEVEL")
bv.width, bv.segments, bv.limit_method, bv.angle_limit = BEVEL, 1, "ANGLE", math.radians(35)
bv.harden_normals = True
bpy.ops.object.modifier_apply(modifier="bevel")
bpy.ops.object.modifier_add(type="TRIANGULATE")
bpy.ops.object.modifier_apply(modifier="Triangulate")

# planar UVs from the view each face points at
me = body.data
uvl = me.uv_layers.new(name="UVMap")
views = o["uv"]
for p in me.polygons:
    n = p.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    if ax == 1:
        view = "front" if n.y < 0 else "back"
    elif ax == 0:
        view = "left" if n.x < 0 else "right"
    else:  # tops/bottoms: the top view if drawn, else the front slid back by depth
        view = "top" if "top" in views else "ztop"
    hax, _, vax = o["axes"].get(view, ("x", 1, "z"))
    au, bu, av, bv_ = views.get(view, views["front"])
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        vert = co.z + co.y if view == "ztop" else getattr(co, vax)  # no row gets stretched
        uvl.data[li].uv = (au * getattr(co, hax) + bu, av * vert + bv_)

if FLAT:  # front up, the sheet's up along +Y
    me.transform(Matrix.Rotation(math.radians(-90), 4, "X"))
zs = [v.co.z for v in me.vertices]
me.transform(Matrix.Translation((0, 0, -min(zs))))
me.update()

name = o["name"]
mat = bpy.data.materials.new(name)
me.materials.append(mat)
body.name = me.name = "submesh_00_LOD_1"
xs = [v.co for v in me.vertices]
print("HULL", name, len(me.polygons), "tris, bbox m",
      [round(min(c[i] for c in xs), 3) for i in range(3)], [round(max(c[i] for c in xs), 3) for i in range(3)])
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.ops.export_scene.gltf(filepath=f"{d}/{name}.glb", use_selection=True, export_format="GLB",
                          export_materials="PLACEHOLDER", export_tangents=True, export_normals=True)

# textured preview (the exporter leaves the slot empty)
me.materials.clear()
me.materials.append(mat)
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
for key, sock, cs in (("d01", "Base Color", "sRGB"), ("r01", "Roughness", "Non-Color"), ("m01", "Metallic", "Non-Color")):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(f"{d}/{name}_{key}.png")
    t.image.colorspace_settings.name = cs
    nt.links.new(t.outputs["Color"], bsdf.inputs[sock])
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 600, 600
sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.5, 0.5, 0.52)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4
sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
sc.collection.objects.link(cam)
sc.camera = cam
lo, hi = Vector([min(c[i] for c in xs) for i in range(3)]), Vector([max(c[i] for c in xs) for i in range(3)])
mid, R = (lo + hi) / 2, (hi - lo).length
for shot, dirn in (("a", (0.6, -1, 0.45)), ("b", (-0.8, 1, 0.35))):
    if FLAT:
        dirn = (dirn[0], dirn[1] * 0.6, 1.2) if shot == "a" else (dirn[0], dirn[1] * 0.6, -1.2)
    cam.location = mid + Vector(dirn).normalized() * R * 1.9
    cam.rotation_euler = (mid - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{d}/prev_{shot}.png"
    bpy.ops.render.render(write_still=True)
