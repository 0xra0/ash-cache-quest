#!/usr/bin/env python3
"""Two .ent for the ash case: closed, and opened with the splinter in the tray.

Template: vanilla q005_broken_suitcase.ent - the plain gameObject (no device,
no instanceData) the quest already draws as its opened case. Its parts are
edited in BOTH copies, `components` (editor) and `compiledData` (what the game
spawns), matched by component name:

    ld_kit_suitcase_opened_a -> ash_case_body   (our body mesh, at the origin)
    + ash_case_lid                               (new: lid mesh on the hinge)
    full (the splinter)      -> lies on the tray floor; opened only
    light                    -> over the tray; opened only
    both colliders           -> resized to the case

    gen_case_ent.py <case_dims.json> <outdir> [insert.json]

With insert.json (from bl_insert.py) the opened case also gets the foam insert
(ash_case_insert.mesh) and the splinter rests in the insert's pocket instead of on
the tray floor (D150).
"""
import copy, json, math, os, subprocess, sys

WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
TEMPLATE = "/mnt/sata/Cyberpunk2077/ash-cache-quest/research/case_ex/json/q005_broken_suitcase.ent.json"
DEPOT = "mod\\ash_cache\\props\\ash_case"
OPEN_DEG = -100.0      # lid about the hinge's local X; negative swings it back
LID_ID = "7310046598145880064"  # new component id, unused by the template
SPLINTER = "mod\\ash_cache\\props\\splinter\\o1140_splinter.mesh"
CHIP_SCALE = 3.0       # 42 mm reads as ~13 cm in the tray; 1.0 = true size
INSERT_ID = "7310046598145880100"  # new component id, unused by the template
# D150d: the template's light (55 lm, pure red, 8 cm over the tray) saturated the whole
# interior and drowned the steel cradle and its cyan edge. Softer, warmer, higher.
LIGHT_LM, LIGHT_RGB, LIGHT_LIFT = 18, (255, 60, 45), 0.15


def fp(x):
    return {"$type": "FixedPoint", "Bits": int(round(x * 131072))}


def pos(x, y, z):
    return {"$type": "WorldPosition", "x": fp(x), "y": fp(y), "z": fp(z)}


def quat_x(deg):
    h = math.radians(deg) / 2
    return {"$type": "Quaternion", "i": math.sin(h), "j": 0, "k": 0, "r": math.cos(h)}


def path(p):
    return {"DepotPath": {"$type": "ResourcePath", "$storage": "string", "$value": p}, "Flags": "Default"}


def edit(comps, dims, opened, insert=None):
    """Apply the edits to one component list; returns it."""
    by = {c["name"]["$value"]: c for c in comps}
    t = dims["tray"]["body"]
    sx, sy, sz = dims["size"]
    hx, hy, hz = dims["hinge"]

    body = by["ld_kit_suitcase_opened_a"]
    body["name"]["$value"] = "ash_case_body"
    body["mesh"] = path(f"{DEPOT}\\ash_case_body.mesh")
    body["meshAppearance"]["$value"] = "default"
    body["localTransform"] = {"$type": "WorldTransform", "Orientation": quat_x(0), "Position": pos(0, 0, 0)}
    body["visualScale"] = {"$type": "Vector3", "X": 1, "Y": 1, "Z": 1}

    lid = copy.deepcopy(body)
    lid["name"]["$value"] = "ash_case_lid"
    lid["id"] = LID_ID
    lid["mesh"] = path(f"{DEPOT}\\ash_case_lid.mesh")
    lid["localTransform"] = {"$type": "WorldTransform",
                             "Orientation": quat_x(OPEN_DEG if opened else 0), "Position": pos(hx, hy, hz)}
    comps.insert(comps.index(body) + 1, lid)

    # our O-1140 splinter, real size (42 mm), drawn at CHIP_SCALE; lies flat in its own XY.
    chip = by["full"]
    chip["mesh"] = path(SPLINTER)
    chip["meshAppearance"]["$value"] = "default"
    chip["visualScale"] = {"$type": "Vector3", "X": CHIP_SCALE, "Y": CHIP_SCALE, "Z": CHIP_SCALE}
    chip_z = insert["pocket_floor"] + 0.0005 if insert else t["z_floor"] + 0.004
    chip["localTransform"] = {"$type": "WorldTransform", "Orientation": quat_x(0),
                              "Position": pos((t["x0"] + t["x1"]) / 2, (t["y0"] + t["y1"]) / 2, chip_z)}
    if insert and opened:
        bed = copy.deepcopy(body)
        bed["name"]["$value"] = "ash_case_insert"
        bed["id"] = INSERT_ID
        bed["mesh"] = path(f"{DEPOT}\\ash_case_insert.mesh")
        comps.insert(comps.index(body) + 1, bed)
    light = by["light"]
    light["localTransform"]["Position"] = pos((t["x0"] + t["x1"]) / 2, (t["y0"] + t["y1"]) / 2, dims["seam"] + LIGHT_LIFT)
    light["intensity"] = LIGHT_LM
    light["color"].update({"Red": LIGHT_RGB[0], "Green": LIGHT_RGB[1], "Blue": LIGHT_RGB[2]})
    if not opened:
        comps.remove(chip)
        comps.remove(light)

    for c in comps:
        if c["$type"] == "entColliderComponent":
            c["localTransform"]["Position"] = pos(0, 0, sz / 2)
            for col in (x for x in c["colliders"] if "Data" in x):  # editor copy holds handle refs
                col["Data"]["halfExtents"] = {"$type": "Vector3", "X": sx / 2, "Y": sy / 2, "Z": sz / 2}
    return comps


def main(dims_path, out, insert_path=None):
    dims = json.load(open(dims_path))
    insert = json.load(open(insert_path)) if insert_path else None
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    for state, opened in (("closed", False), ("open", True)):
        doc = json.load(open(TEMPLATE))
        root = doc["Data"]["RootChunk"]
        root["components"] = edit(root["components"], dims, opened, insert)
        pkg = root["compiledData"]["Data"]
        pkg["Chunks"] = [pkg["Chunks"][0]] + edit(pkg["Chunks"][1:], dims, opened, insert)
        # CruidDict: chunk index -> component id, 0 being the entity itself.
        pkg["CruidDict"] = {"0": "0", **{str(i + 1): c["id"] for i, c in enumerate(pkg["Chunks"][1:])}}
        name = f"ash_case_{state}.ent"
        doc["Header"]["ArchiveFileName"] = f"{DEPOT}\\{name}"
        jp = f"{out}/{name}.json"
        json.dump(doc, open(jp, "w"), indent=1)
        r = subprocess.run(["dotnet", WK, "convert", "deserialize", jp, "-o", out],
                           env={**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}, capture_output=True, text=True)
        bad = [l for l in r.stdout.splitlines() if "Error" in l or "Exception" in l]
        if bad or not os.path.exists(f"{out}/{name}"):
            sys.exit(f"{name}: " + "\n".join(bad or r.stdout.splitlines()[-4:]))
        names = [c["name"]["$value"] for c in pkg["Chunks"][1:]]
        print(f"{name}: {len(names)} components: {', '.join(names)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
