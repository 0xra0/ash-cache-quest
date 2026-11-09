"""High-poly Trellis2 case -> game-ready body + lid (Blender, headless).

    blender -b -P bl_game.py -- <high.glb> <outdir> [bake]

Out: body.glb / lid.glb (Z-up, metres, lid origin on the hinge so the .ent can
open it with one rotation), ash_case_{d01,n01,r01,m01}.png, preview_*.png.
"""
import bpy, bmesh, sys, math, os
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
BAKE = "bake" in argv[2:]
WIDTH = 0.45          # m, across the front
LOW_FACES = 20000     # whole case, before the cut
SEAM_FRAC = 0.61      # seam height / body height (latch centre in the side photo)
WALL = 0.022          # m, tray wall thickness
TEX = 2048
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.context.view_layer.objects.active = meshes[0]
for o in meshes:
    o.select_set(True)
if len(meshes) > 1:
    bpy.ops.object.join()
high = bpy.context.view_layer.objects.active
high.name = "high"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Trellis frame -> game frame: after the glTF import the case lies on its back
# (front face up, handle along +Y). Stand it up: handle +Z, front -Y.
high.data.transform(Matrix.Rotation(math.radians(90), 4, "X"))
high.data.update()
bb = [v.co for v in high.data.vertices]
mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
s = WIDTH / (mx.x - mn.x)
high.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation(-Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))))
high.data.update()
dims = (mx - mn) * s
print(f"[case] dims {dims.x:.3f} x {dims.y:.3f} x {dims.z:.3f} m, {len(high.data.polygons)} faces")


def body_height(obj):
    """Top of the box, not of the handle: the height below which most of the
    footprint area still exists. The handle is a thin bar, so a horizontal
    slice through it covers a small fraction of the full footprint."""
    zs = sorted(v.co.z for v in obj.data.vertices)
    top = zs[-1]
    xs_full = dims.x * dims.y
    for k in range(100, 40, -1):
        z = top * k / 100
        band = [v.co for v in obj.data.vertices if abs(v.co.z - z) < top * 0.01]
        if band:
            w = max(p.x for p in band) - min(p.x for p in band)
            d = max(p.y for p in band) - min(p.y for p in band)
            if w * d > 0.6 * xs_full:
                return z
    return top


H = body_height(high)
SEAM = H * SEAM_FRAC
print(f"[case] body top {H:.3f} m, seam at {SEAM:.3f} m")

# ---- low poly -----------------------------------------------------------
low = high.copy()
low.data = high.data.copy()
low.name = "low"
bpy.context.collection.objects.link(low)
for o in bpy.context.selected_objects:
    o.select_set(False)
bpy.context.view_layer.objects.active = low
low.select_set(True)
# The input is already watertight (close.py: morphological closing of the
# Trellis output, which is layered double sheets no decimator can collapse).
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.object.mode_set(mode="OBJECT")
m = low.modifiers.new("dec", "DECIMATE")
m.ratio = LOW_FACES / len(low.data.polygons)
bpy.ops.object.modifier_apply(modifier="dec")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.0005)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
low.data.materials.clear()
for uv in list(low.data.uv_layers):
    low.data.uv_layers.remove(uv)
low.data.uv_layers.new(name="UV")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
bpy.ops.uv.pack_islands(margin=0.003)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
print(f"[case] low {len(low.data.polygons)} faces")

shell = bpy.data.materials.new("ash_case")
shell.use_nodes = True
low.data.materials.append(shell)
inner = bpy.data.materials.new("ash_case_interior")
inner.use_nodes = True
inner.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.022, 1)
inner.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
inner.diffuse_color = (0.03, 0.03, 0.035, 1)  # what the workbench preview shows
low.data.materials.append(inner)

# ---- bake (before the cut, so the caps never sample the high poly) -------
if BAKE:
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 4
    img = {}
    for k in ("d01", "n01", "r01", "m01"):
        img[k] = bpy.data.images.new(f"ash_case_{k}", TEX, TEX, alpha=False)
        img[k].colorspace_settings.name = "sRGB" if k == "d01" else "Non-Color"
    nt = shell.node_tree
    tn = nt.nodes.new("ShaderNodeTexImage")
    nt.nodes.active = tn
    hm = high.active_material
    hn = hm.node_tree
    bsdf = next(n for n in hn.nodes if n.type == "BSDF_PRINCIPLED")
    out = next(n for n in hn.nodes if n.type == "OUTPUT_MATERIAL")
    emit = hn.nodes.new("ShaderNodeEmission")
    sep = hn.nodes.new("ShaderNodeSeparateColor")

    def src(inp):
        return inp.links[0].from_socket if inp.links else None

    base_src = src(bsdf.inputs["Base Color"])
    # glTF metallicRoughness: the importer splits it; follow either socket back
    # to its image node and read G (roughness) / B (metal) off that image.
    mr_img = None
    for name in ("Roughness", "Metallic"):
        s_ = src(bsdf.inputs[name])
        while s_ is not None and s_.node.type != "TEX_IMAGE":
            s_ = s_.node.inputs[0].links[0].from_socket if s_.node.inputs and s_.node.inputs[0].links else None
        if s_ is not None:
            mr_img = s_.node
    hn.links.new(mr_img.outputs["Color"], sep.inputs["Color"]) if mr_img else None
    hn.links.new(emit.outputs[0], out.inputs["Surface"])

    for o in bpy.context.selected_objects:
        o.select_set(False)
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bk = sc.render.bake
    bk.use_selected_to_active = True
    bk.cage_extrusion = 0.006
    bk.max_ray_distance = 0.02
    bk.margin = 8

    def emit_bake(key, sock, const=None):
        for l in list(emit.inputs["Color"].links):
            hn.links.remove(l)
        if sock is not None:
            hn.links.new(sock, emit.inputs["Color"])
        else:
            emit.inputs["Color"].default_value = const
        tn.image = img[key]
        bpy.ops.object.bake(type="EMIT")
        img[key].filepath_raw = f"{OUT}/ash_case_{key}.png"
        img[key].file_format = "PNG"
        img[key].save()
        print(f"[case] baked {key}")

    emit_bake("d01", base_src, (0.2, 0.2, 0.2, 1))
    emit_bake("r01", sep.outputs["Green"] if mr_img else None, (0.5, 0.5, 0.5, 1))
    emit_bake("m01", sep.outputs["Blue"] if mr_img else None, (0.0, 0.0, 0.0, 1))
    hn.links.new(bsdf.outputs[0], out.inputs["Surface"])
    tn.image = img["n01"]
    bk.normal_g = "NEG_Y"  # REDengine normal maps are DirectX-style (green down)
    bpy.ops.object.bake(type="NORMAL")
    img["n01"].filepath_raw = f"{OUT}/ash_case_n01.png"
    img["n01"].file_format = "PNG"
    img["n01"].save()
    print("[case] baked n01")

# ---- cut: body below the seam, lid above ---------------------------------
bpy.data.objects.remove(high)


def half(name, keep_below):
    o = low.copy()
    o.data = low.data.copy()
    o.name = name
    bpy.context.collection.objects.link(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, SEAM), plane_no=(0, 0, 1),
                               clear_outer=keep_below, clear_inner=not keep_below)
    cut_edges = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    # holes_fill leaves the big concave outline open; triangle_fill takes the
    # whole planar cut at once, outer outline plus any inner loops.
    bnd = [e for e in bm.edges if e.is_boundary and all(abs(v.co.z - SEAM) < 1e-5 for v in e.verts)]
    open_ends = sum(1 for v in {v for e in bnd for v in e.verts}
                    if sum(1 for e in v.link_edges if e in set(bnd)) != 2)
    print(f"[case] {name}: {len(bnd)} boundary edges on the cut, {open_ends} open ends")
    ring = [v.co.copy() for e in bnd for v in e.verts]

    # A tray, not a solid block. triangle_fill given the outline AND a
    # rectangle loop fills only the ring between them, which leaves the
    # opening; the rectangle is then extruded into walls and floored.
    def pct(vals, q):
        v = sorted(vals)
        return v[int(q * (len(v) - 1))]
    x0, x1 = pct([p.x for p in ring], 0.1) + WALL, pct([p.x for p in ring], 0.9) - WALL
    y0, y1 = pct([p.y for p in ring], 0.1) + WALL, pct([p.y for p in ring], 0.9) - WALL
    depth = SEAM * 0.7 if keep_below else -(H - SEAM) * 0.45
    z0 = SEAM - depth
    step = 0.01
    pts = []
    for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                               ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        n = max(1, round(max(abs(bx - ax), abs(by - ay)) / step))
        pts += [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n)]
    rv = [bm.verts.new((x, y, SEAM)) for x, y in pts]
    re = [bm.edges.new((rv[i], rv[(i + 1) % len(rv)])) for i in range(len(rv))]
    fill = bmesh.ops.triangle_fill(bm, edges=bnd + re, use_beauty=True,
                                   normal=(0, 0, 1 if keep_below else -1))["geom"]
    cap = [g for g in fill if isinstance(g, bmesh.types.BMFace)]
    # triangle_fill fills every closed region, the rectangle too: drop that.
    hole = [f for f in cap if x0 < f.calc_center_median().x < x1 and y0 < f.calc_center_median().y < y1]
    bmesh.ops.delete(bm, geom=hole, context="FACES_ONLY")
    cap = [f for f in cap if f.is_valid]
    for f in cap:
        f.material_index = 1
    ext = bmesh.ops.extrude_edge_only(bm, edges=re)["geom"]
    nv = [g for g in ext if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nv, vec=(0, 0, -depth))
    walls = [g for g in ext if isinstance(g, bmesh.types.BMFace)]
    fe = [g for g in ext if isinstance(g, bmesh.types.BMEdge) and all(v in set(nv) for v in g.verts)]
    fl = [g for g in bmesh.ops.triangle_fill(bm, edges=fe, use_beauty=True,
                                             normal=(0, 0, 1 if keep_below else -1))["geom"]
          if isinstance(g, bmesh.types.BMFace)]
    for f in walls + fl:
        f.material_index = 1
    TRAY[name] = dict(x0=x0, x1=x1, y0=y0, y1=y1, z_floor=z0, z_rim=SEAM)
    print(f"[case] {name}: rim {len(cap)} faces, opening {len(hole)} dropped, walls {len(walls)}, floor {len(fl)}")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(o.data)
    bm.free()
    return o


TRAY = {}
body = half("body", True)
lid = half("lid", False)
bpy.data.objects.remove(low)

# Hinge on the back edge of the seam; lid origin there, so "open" is one
# rotation about local X in the .ent.
ys = [v.co.y for v in lid.data.vertices if abs(v.co.z - SEAM) < 0.01]
hinge = Vector((0, max(ys), SEAM))
lid.data.transform(Matrix.Translation(-hinge))
lid.location = hinge
print(f"[case] body {len(body.data.polygons)} faces, lid {len(lid.data.polygons)} faces, hinge {tuple(round(c, 4) for c in hinge)}")

def export(o, fn):
    """WolvenKit maps each glTF MESH (not primitive) to one submesh, by name:
    submesh_00_LOD_1 is chunk 0 -> material 0 (shell), submesh_01 -> interior."""
    for x in bpy.context.selected_objects:
        x.select_set(False)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    tri = o.modifiers.new("tri", "TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier="tri")
    loc = o.location.copy()
    o.location = (0, 0, 0)
    bpy.ops.object.duplicate()
    d = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = sorted(bpy.context.selected_objects,
                   key=lambda x: x.data.materials[x.data.polygons[0].material_index].name != "ash_case")
    for i, x in enumerate(parts):
        mi = {p.material_index for p in x.data.polygons}
        x.name = x.data.name = f"submesh_{i:02d}_LOD_1"
        print(f"[case] {fn}: {x.name} {len(x.data.polygons)} tris, material {x.data.materials[min(mi)].name}")
    bpy.ops.export_scene.gltf(filepath=f"{OUT}/{fn}.glb", use_selection=True, export_format="GLB",
                              export_yup=True, export_materials="PLACEHOLDER",
                              export_tangents=True, export_normals=True)
    for x in parts:
        bpy.data.objects.remove(x)
    o.location = loc


export(body, "body")
export(lid, "lid")

# Preview: closed and opened (lid -100 deg about the hinge).
with open(f"{OUT}/hinge.txt", "w") as f:
    f.write(f"{hinge.x} {hinge.y} {hinge.z}\n")
import json
json.dump({"hinge": list(hinge), "seam": SEAM, "body_top": H, "size": list(dims), "tray": TRAY},
          open(f"{OUT}/case_dims.json", "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/case_game.blend")
