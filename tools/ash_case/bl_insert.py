"""Foam insert for the opened ash case: a fitted bed with a raised cradle in the middle.

The Relic case (q005) reads as precious because the chip sits in a pocket cut for it;
ours had a bare tray with the splinter lying on its floor. This fills the tray with
dark foam (material ash_case_interior, already shipped) and raises a gunmetal cradle
(ash_case_cradle) in the centre, with a splinter-shaped pocket the chip rests in, so
the chip stands just proud of everything around it.

Built from boxes in the case's own frame (Z up, the frame case_dims.json is in).
    blender -b -P bl_insert.py -- <case_dims.json> <out dir>
D150c: a thin emissive strip (ash_case_glow) rims the pocket so the holder reads even under
the case's red light.
Writes <out>/insert.glb (submesh_00 foam, 01 cradle, 02 glow) and <out>/insert.json
with the pocket floor height the entity needs for the splinter.
"""
import json, sys
import bpy, bmesh

DIMS, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
t = json.load(open(DIMS))["tray"]["body"]
E = 0.002                              # clearance to the tray walls
FOAM_TOP = t["z_rim"] - 0.032          # the bed sits below the rim, like a real insert
CHIP = (0.0201, 0.0630, 0.0165)        # half X, half Y, height of the splinter drawn at 3x
POCKET = (CHIP[0] + 0.004, CHIP[1] + 0.004)
PAD = (POCKET[0] + 0.016, POCKET[1] + 0.016)
PAD_TOP = FOAM_TOP + 0.008
POCKET_FLOOR = PAD_TOP - 0.010
cx, cy = (t["x0"] + t["x1"]) / 2, (t["y0"] + t["y1"]) / 2
x0, x1, y0, y1, z0 = t["x0"] + E, t["x1"] - E, t["y0"] + E, t["y1"] - E, t["z_floor"]

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new("insert")
obj = bpy.data.objects.new("insert", mesh)
bpy.context.collection.objects.link(obj)
MATS = ("ash_case_interior", "ash_case_cradle", "ash_case_glow")
for name in MATS:
    mesh.materials.append(bpy.data.materials.new(name))
bm = bmesh.new()


def box(ax, bx, ay, by, az, bz, mat):
    if bx - ax < 1e-4 or by - ay < 1e-4 or bz - az < 1e-4:
        return
    v = [bm.verts.new((x, y, z)) for z in (az, bz) for y in (ay, by) for x in (ax, bx)]
    for q in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
        bm.faces.new([v[i] for i in q]).material_index = mat


def frame(ox, oy, ix, iy, az, bz, mat):
    """Rectangle (half sizes ox, oy) about the centre minus the inner one (ix, iy)."""
    box(cx - ox, cx + ox, cy - oy, cy - iy, az, bz, mat)
    box(cx - ox, cx + ox, cy + iy, cy + oy, az, bz, mat)
    box(cx - ox, cx - ix, cy - iy, cy + iy, az, bz, mat)
    box(cx + ix, cx + ox, cy - iy, cy + iy, az, bz, mat)


# foam bed: the whole tray minus the pad's footprint
box(x0, x1, y0, cy - PAD[1], z0, FOAM_TOP, 0)
box(x0, x1, cy + PAD[1], y1, z0, FOAM_TOP, 0)
box(x0, cx - PAD[0], cy - PAD[1], cy + PAD[1], z0, FOAM_TOP, 0)
box(cx + PAD[0], x1, cy - PAD[1], cy + PAD[1], z0, FOAM_TOP, 0)
# cradle: raised gunmetal ring around the pocket, foam lining at the pocket floor
frame(PAD[0], PAD[1], POCKET[0], POCKET[1], z0, PAD_TOP, 1)
box(cx - POCKET[0], cx + POCKET[0], cy - POCKET[1], cy + POCKET[1], z0, POCKET_FLOOR, 0)
# lit edge: 3 mm strip round the pocket mouth, 1.5 mm proud of the cradle
GLOW_W, GLOW_H = 0.003, 0.0015
frame(POCKET[0] + GLOW_W, POCKET[1] + GLOW_W, POCKET[0], POCKET[1], PAD_TOP - 0.001, PAD_TOP + GLOW_H, 2)

bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(mesh)
bm.free()

bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.cube_project(cube_size=0.25)
bpy.ops.mesh.separate(type="MATERIAL")
bpy.ops.object.mode_set(mode="OBJECT")
parts = sorted(bpy.context.selected_objects,
               key=lambda x: MATS.index(x.data.materials[x.data.polygons[0].material_index].name))
for i, x in enumerate(parts):
    tri = x.modifiers.new("tri", "TRIANGULATE")
    bpy.context.view_layer.objects.active = x
    bpy.ops.object.modifier_apply(modifier="tri")
    x.name = x.data.name = f"submesh_{i:02d}_LOD_1"
    print(f"[insert] {x.name} {len(x.data.polygons)} tris, {x.data.materials[x.data.polygons[0].material_index].name}")
for x in parts:
    x.select_set(True)
bpy.ops.export_scene.gltf(filepath=f"{OUT}/insert.glb", use_selection=True, export_format="GLB",
                          export_yup=True, export_materials="PLACEHOLDER",
                          export_tangents=True, export_normals=True)
json.dump({"pocket_floor": POCKET_FLOOR, "centre": [cx, cy], "foam_top": FOAM_TOP, "pad_top": PAD_TOP},
          open(f"{OUT}/insert.json", "w"), indent=1)
print(f"[insert] pocket floor z {POCKET_FLOOR:.4f}, pad top {PAD_TOP:.4f}, foam top {FOAM_TOP:.4f}")
