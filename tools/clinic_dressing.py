#!/usr/bin/env python3
"""Clinic dressing (D151): source/clinic_dressing.json -> solid prop .ent + world.json poses + glue props.

Each item is a vanilla .mesh placed on a measured surface. For every item this
  1. extracts the mesh from the game into ../game_extract (once) and reads its bounds,
  2. wraps it with tools/gen_mesh_ent.py in mod\\ash_cache\\props\\clinic\\<id>.ent (solid collider),
  3. writes a disabled pose entry into the clinic sector's props in source/world.json and a glue
     prop that draws it while ashcache_progress is 2..6 (the window the quest owns the room, the
     same as the ac_clinic hide), so Farida's room comes back without it.
Entries it wrote carry "_dressing": true and are replaced wholesale on every run; nothing else in
world.json / glue.json is touched. "surface" is the z the item stands on; the origin is lifted by
the mesh's own bottom so the item sits on it whatever its pivot.

D155 room placement (instead of "pos"/"yaw"/"center"):
  "room": [u, v]      footprint centre in the room frame (ROOM below)
  "face": "+u"        where the item's front points: +u (terminal wall), -u, +v (far wall), -v (door);
                      "yaw_add" turns it further (degrees)
  "front": "+y"       which mesh-local axis is the item's front (+x, -x, +y, -y; default +y)
  "against": "left"   slide it along its facing so its back touches that wall (left, right, far, door)
  "on": "<item id>"   surface = the top of an item listed earlier (stacking)
  "wall_gap": 0.03    "against" items: space left between the back and the wall line (default 0.015); set from
                      the real wall by dev/roommap/fitcheck.py --wall (D164)
  "dz": -0.012        added to the surface; for "on" items whose support's bounds top is not its real
                      top under them (measured by dev/roommap/fitcheck.py, D163)

    clinic_dressing.py            # regenerate everything
"""
import json, math, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "source", "clinic_dressing.json")
WORLD = os.path.join(ROOT, "source", "world.json")
GLUE = os.path.join(ROOT, "source", "glue.json")
EXTRACT = os.path.normpath(os.path.join(ROOT, "..", "game_extract"))
JSONDIR = os.path.join(EXTRACT, "json_tbl")
OUTDIR = os.path.join(ROOT, "assets", "mod", "ash_cache", "props", "clinic")
DEPOT = "mod\\ash_cache\\props\\clinic"
WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
ARCHIVES = ["/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc/content",
            "/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc/ep1"]
ENV = {**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}

# D155: room frame (D153) and its walls, from horizontal live raycasts at 1.1 m and 1.9 m (2026-09-25
# 12:10, dev/roommap.py). The walls run 2.4 degrees off the frame axes, so "face" turns by ROT.
ROOM_O, ROOM_U, ROOM_V = (-1908.0, -2469.5), (0.70710678, 0.70710678), (-0.70710678, 0.70710678)
ROT = -2.4
WALLS = {  # wall -> (axis the wall is a constant of, function of the other coordinate, side sign)
    "left": ("u", lambda v: -3.94 + 0.0444 * (v + 5.5), +1),
    "right": ("u", lambda v: 3.17 + 0.0407 * (v + 5.5), -1),
    "far": ("v", lambda u: 8.79 - 0.0383 * (u + 3), -1),
    "door": ("v", lambda u: -5.81 - 0.0378 * (u + 3), +1),
    # D156 (dev/roommap/walls.py, 2026-09-25 16:30): Mara's side room left of the table (door gap
    # v 3.9..6.0 in its inner wall) and the entry hall between the street door and the glass door
    "mara_out": ("u", lambda v: -6.63 + 0.0433 * (v - 2), +1),
    "mara_in": ("u", lambda v: -3.56 + 0.05 * (v - 6), -1),
    "mara_far": ("v", lambda u: 8.88, -1),
    "mara_near": ("v", lambda u: 1.28, +1),
    "hall_left": ("u", lambda v: -2.40 + 0.04 * (v + 7), +1),
    "hall_right": ("u", lambda v: 2.11 + 0.0433 * (v + 7), -1),
}
FACE = {"+u": 45.0, "+v": 135.0, "-u": 225.0, "-v": -45.0}
AXIS = {"+x": 0.0, "+y": 90.0, "-x": 180.0, "-y": -90.0}


def room_xy(u, v):
    return ROOM_O[0] + u * ROOM_U[0] + v * ROOM_V[0], ROOM_O[1] + u * ROOM_U[1] + v * ROOM_V[1]


def room_pose(it, lo, hi):
    """(x, y, yaw) of the mesh origin for a D155 "room" item."""
    yaw = FACE[it["face"]] + ROT - AXIS[it.get("front", "+y")] + it.get("yaw_add", 0.0)
    yaw = (yaw + 180) % 360 - 180
    u, v = it["room"]
    if "against" in it:
        axis, line, sign = WALLS[it["against"]]
        # half the footprint measured along the wall's normal (the rotated bounds' extent)
        r = math.radians(yaw - FACE["+u" if axis == "u" else "+v"] - ROT)
        hx, hy = (hi["X"] - lo["X"]) / 2, (hi["Y"] - lo["Y"]) / 2
        half = abs(hx * math.cos(r)) + abs(hy * math.sin(r))
        gap = it.get("wall_gap", 0.015)
        if axis == "u":
            u = line(v) + sign * (half + gap)
        else:
            v = line(u) + sign * (half + gap)
    x, y = room_xy(u, v)
    cx, cy = (lo["X"] + hi["X"]) / 2, (lo["Y"] + hi["Y"]) / 2
    r = math.radians(yaw)
    return round(x - (cx * math.cos(r) - cy * math.sin(r)), 3), round(y - (cx * math.sin(r) + cy * math.cos(r)), 3), round(yaw, 1)


def mesh_json(depot):
    """Extract + serialize a vanilla mesh once; return the path of its JSON."""
    name = depot.split("\\")[-1]
    js = os.path.join(JSONDIR, name + ".json")
    if os.path.exists(js):
        return js
    raw = os.path.join(EXTRACT, *depot.split("\\"))
    if not os.path.exists(raw):
        for arc in ARCHIVES:
            subprocess.run(["dotnet", WK, "unbundle", arc, "-o", EXTRACT, "-w", depot],
                           env=ENV, capture_output=True, text=True)
            if os.path.exists(raw):
                break
    if not os.path.exists(raw):
        sys.exit(f"{depot}: not found in the game archives")
    os.makedirs(JSONDIR, exist_ok=True)
    subprocess.run(["dotnet", WK, "convert", "serialize", raw, "-o", JSONDIR], env=ENV, capture_output=True, text=True)
    if not os.path.exists(js):
        sys.exit(f"{depot}: serialize failed")
    return js


def prefetch(depots):
    """Extract every missing mesh in one regex pass per archive (a -w pass per mesh scans the
    whole archive each time: minutes per mesh)."""
    import re
    todo = [d for d in dict.fromkeys(depots)
            if not os.path.exists(os.path.join(JSONDIR, d.split("\\")[-1] + ".json"))
            and not os.path.exists(os.path.join(EXTRACT, *d.split("\\")))]
    for arc in ARCHIVES:
        if not todo:
            break
        rx = "^(" + "|".join(re.escape(d) for d in todo) + ")$"
        subprocess.run(["dotnet", WK, "unbundle", arc, "-o", EXTRACT, "-r", rx], env=ENV, capture_output=True, text=True)
        todo = [d for d in todo if not os.path.exists(os.path.join(EXTRACT, *d.split("\\")))]


def clinic_props(world):
    for sec in world["sectors"]:
        props = sec.get("props", [])
        if any(p.get("id") == "ac_splinter_box" for p in props):
            return props
    sys.exit("clinic sector (the one holding ac_splinter_box) not found in world.json")


def add(props, glue, mid, ent, x, y, z, yaw, it):
    """The disabled pose entry in world.json and the glue prop that draws it (ashcache_progress 2..6)."""
    props.append({"id": mid, "_dressing": True, "disabled": True, "verified": False,
                  "disabled_why": "D151 clinic dressing: drawn by the glue while ashcache_progress is 2..6; this entry is the pose.",
                  "scenery": "Nothing references this node by NodeRef: glue.json reads its pos and yaw.",
                  "pos": [x, y, z], "yaw": yaw, "template": ent,
                  "_source": f"source/clinic_dressing.json ({it.get('note', '')})"})
    glue["props"].append({"_dressing": True, "id": f"dress_{mid}", "prop": mid, "watch": ["ashcache_progress"],
                          "states": [{"tag": f"ashcache_{mid}", "template": ent,
                                      "when": [{"fact": "ashcache_progress", "min": 2},
                                               {"fact": "ashcache_progress", "max": 6}],
                                      "z_offset": 0.0, "yaw_offset": 0.0}]})


def main():
    items = json.load(open(SRC))["items"]
    world, glue = json.load(open(WORLD)), json.load(open(GLUE))
    props = clinic_props(world)
    props[:] = [p for p in props if not p.get("_dressing")]
    glue["props"] = [p for p in glue["props"] if not p.get("_dressing")]
    os.makedirs(OUTDIR, exist_ok=True)
    tops = {}
    prefetch([m for it in items if "mesh" in it for m in [it["mesh"], *it.get("extra", [])]])
    for it in items:
        mid = it["id"]
        if "light" in it:  # D154: accent light, no mesh - the entity origin is the light
            L = it["light"]
            ent = f"{DEPOT}\\{mid}.ent"
            r = subprocess.run([sys.executable, os.path.join(HERE, "gen_light_ent.py"), ent, OUTDIR,
                                ",".join(str(v) for v in L["rgb"]), str(L["lumens"]), str(L["radius"])],
                               capture_output=True, text=True)
            if r.returncode:
                sys.exit(f"{mid}: {r.stdout}{r.stderr}")
            for f in os.listdir(OUTDIR):
                if f.endswith(".json"):
                    os.remove(os.path.join(OUTDIR, f))
            x, y = room_xy(*it["room"]) if "room" in it else it["pos"]
            x, y = round(x, 3), round(y, 3)
            add(props, glue, mid, ent, x, y, it["z"], 0.0, it)
            print(f"{mid}: light {L['rgb']} {L['lumens']} lm at {x:.3f} {y:.3f} {it['z']:.3f}")
            continue
        mesh = it["mesh"]
        js = mesh_json(mesh)
        bb = json.load(open(js))["Data"]["RootChunk"]["boundingBox"]
        lo, hi = bb["Min"], bb["Max"]
        ent = f"{DEPOT}\\{mid}.ent"
        args = [mesh, js, it.get("appearance", "default"), ent, OUTDIR, *it.get("extra", [])]
        # D156: an .ent is rebuilt only when its generator arguments change (~20 s per WolvenKit call)
        stamp = os.path.join(EXTRACT, "dress_stamps", f"{mid}.args")  # outside assets/: not packed
        if not (os.path.exists(os.path.join(OUTDIR, f"{mid}.ent")) and os.path.exists(stamp)
                and open(stamp).read() == json.dumps(args)):
            r = subprocess.run([sys.executable, os.path.join(HERE, "gen_mesh_ent.py"), *args], capture_output=True, text=True)
            if r.returncode:
                sys.exit(f"{mid}: {r.stdout}{r.stderr}")
            os.makedirs(os.path.dirname(stamp), exist_ok=True)
            open(stamp, "w").write(json.dumps(args))
        for f in os.listdir(OUTDIR):
            if f.endswith(".json"):
                os.remove(os.path.join(OUTDIR, f))
        if "room" in it:
            x, y, yaw = room_pose(it, lo, hi)
            it["yaw"] = yaw
        else:
            x, y = it["pos"]
        if it.get("center") and "room" not in it:
            # pos is the middle of the footprint: move the origin back by the rotated bounds centre
            cx, cy = (lo["X"] + hi["X"]) / 2, (lo["Y"] + hi["Y"]) / 2
            r = math.radians(it["yaw"])
            x = round(x - (cx * math.cos(r) - cy * math.sin(r)), 3)
            y = round(y - (cx * math.sin(r) + cy * math.cos(r)), 3)
        surface = (tops[it["on"]] if "on" in it else it["surface"]) + it.get("dz", 0.0)
        z = round(surface - lo["Z"], 4)
        tops[mid] = round(z + hi["Z"], 4)
        add(props, glue, mid, ent, x, y, z, it["yaw"], it)
        print(f"{mid}: {mesh.split(chr(92))[-1]} at {x:.3f} {y:.3f} {z:.3f} yaw {it['yaw']}")
    json.dump(world, open(WORLD, "w"), indent=2, ensure_ascii=False)
    json.dump(glue, open(GLUE, "w"), indent=2, ensure_ascii=False)
    print(f"{len(items)} dressing item(s) -> {OUTDIR}")


if __name__ == "__main__":
    main()
