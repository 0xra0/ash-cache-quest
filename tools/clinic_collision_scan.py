#!/usr/bin/env python3
"""Collision of the deleted clinic dressing -> reference/clinic_collision.json (D138).

Deleting a mesh node (D137) does not delete its collision: the physics lives in
separate worldCollisionNode actors in the level-1/2 sectors that Phantom Liberty
overrides (interior_-15_-20_0_2, exterior_-15_-20_0_1, exterior_-30_-39_0_0), mixed
with the room's own walls and floor. An actor carries no link to its mesh, so each
one is matched by position to the nearest setup, or instanced copy, of the clinic
sectors. Only an actor whose nearest owner is a setup we delete goes; one nearest to
a kept setup (architecture, lights, vents) or to nothing close stays.

    clinic_collision_scan.py <dir: clinic sectors as .json> <dir: collision sectors as .json>
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HIDE = os.path.join(HERE, "..", "reference", "clinic_hide.json")
OUT = os.path.join(HERE, "..", "reference", "clinic_collision.json")
DEPOT = "base\\worlds\\03_night_city\\_compiled\\default\\"
COLLISION = ["interior_-15_-20_0_2", "exterior_-15_-20_0_1", "exterior_-30_-39_0_0"]
# An actor sits on its mesh's pivot; 0.3 m still catches small props whose collision
# shape is offset, and is well under the 1-2 m spacing of the wall and floor pieces.
MATCH = 0.3
FIXED = 131072.0            # WorldPosition FixedPoint: 17 fractional bits


def handles(o, H):
    if isinstance(o, dict):
        if "HandleId" in o:
            H[o["HandleId"]] = o["Data"]
        for v in o.values():
            handles(v, H)
    elif isinstance(o, list):
        for v in o:
            handles(v, H)


def buffer(n, key, H):
    b = n[key]
    ref = b["sharedDataBuffer"].get("HandleRefId") or b["sharedDataBuffer"]["HandleId"]
    return H[ref]["buffer"]["Data"]["Transforms"][b["startIndex"]:b["startIndex"] + b["numElements"]]


def rotate(q, x, y, z):
    i, j, k, r = q["i"], q["j"], q["k"], q["r"]
    tx, ty, tz = 2 * (j * z - k * y), 2 * (k * x - i * z), 2 * (i * y - j * x)
    return (x + r * tx + (j * tz - k * ty), y + r * ty + (k * tx - i * tz), z + r * tz + (i * ty - j * tx))


def owners(src, hide):
    """Every setup of the clinic sectors, and every instanced copy, with its fate."""
    pts = []
    for sec in hide["sectors"]:
        name = sec["path"].split("\\")[-1].replace(".streamingsector", "")
        full = json.load(open(f"{src}/{name}.streamingsector.json"))
        H = {}
        handles(full, H)
        root = full["Data"]["RootChunk"]
        nd, nodes = root["nodeData"]["Data"], root["nodes"]
        gone = {e["i"] for e in sec["delete"]}
        for i, e in enumerate(nd):
            n, p = nodes[e["NodeIndex"]]["Data"], e["Position"]
            fate = "delete" if i in gone else "keep"
            if n["$type"] == "worldInstancedMeshNode":
                for t in buffer(n, "worldTransformsBuffer", H):
                    q = t["translation"]
                    pts.append(((q["X"], q["Y"], q["Z"]), fate))
            elif n["$type"] == "worldInstancedDestructibleMeshNode":
                for t in buffer(n, "cookedInstanceTransforms", H):
                    v = t["position"]
                    dx, dy, dz = rotate(e["Orientation"], v["X"], v["Y"], v["Z"])
                    pts.append(((p["X"] + dx, p["Y"] + dy, p["Z"] + dz), fate))
            else:
                pts.append(((p["X"], p["Y"], p["Z"]), fate))
    return pts


def main(src, colsrc):
    hide = json.load(open(HIDE))
    box = hide["box"]
    pts = owners(src, hide)
    out = {"_about": __doc__.strip().splitlines()[0], "sectors": []}
    for name in COLLISION:
        root = json.load(open(f"{colsrc}/{name}.streamingsector.json"))["Data"]["RootChunk"]
        nd, nodes = root["nodeData"]["Data"], root["nodes"]
        dels, kept = [], 0
        for i, e in enumerate(nd):
            n = nodes[e["NodeIndex"]]["Data"]
            if n["$type"] != "worldCollisionNode":
                continue
            actors = n["compiledData"]["Data"]["Actors"]
            gone = []
            for k, a in enumerate(actors):
                x, y, z = (a["Position"][c]["Bits"] / FIXED for c in "xyz")
                if not (box[0] <= x <= box[1] and box[2] <= y <= box[3] and box[4] - 1 <= z <= box[5]):
                    continue
                (px, py, pz), fate = min(pts, key=lambda t: (t[0][0] - x) ** 2 + (t[0][1] - y) ** 2 + (t[0][2] - z) ** 2)
                if fate == "delete" and ((px - x) ** 2 + (py - y) ** 2 + (pz - z) ** 2) ** 0.5 < MATCH:
                    gone.append(k)
                else:
                    kept += 1
            if gone:
                dels.append({"i": i, "actors": len(actors), "delete": gone})
        out["sectors"].append({"path": DEPOT + name + ".streamingsector", "setups": len(nd), "nodes": dels})
        print(f"{name}: {len(nd)} setups, {sum(len(d['delete']) for d in dels)} actor(s) deleted "
              f"in {len(dels)} collision node(s), {kept} kept in the room")
    json.dump(out, open(OUT, "w"), indent=1)
    print("->", os.path.normpath(OUT))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
