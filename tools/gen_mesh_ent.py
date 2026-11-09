#!/usr/bin/env python3
"""Wrap one vanilla .mesh in a spawnable .ent with a box collider (D146).

The glue spawns props with Codeware from an .ent template, and most vanilla
furniture exists only as a .mesh placed straight into sectors - with its
collision in separate sector collision nodes, so the mesh itself carries none.
This builds the .ent from the same template the case uses (vanilla
q005_broken_suitcase.ent, a plain gameObject), keeping only its mesh and its
two colliders; the colliders become one box the size of the mesh's bounds.

    gen_mesh_ent.py <mesh depot path> <mesh .json (WolvenKit serialize)> <appearance> <out .ent depot path> <outdir> [extra mesh depot path ...]

Extra meshes are added at the same origin (a vanilla furniture piece is often several meshes
sharing one pivot - morgue_table_a's slab is morgue_table_a_top_*). The collider stays the
first mesh's bounds.
"""
import copy, json, os, subprocess, sys

WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
TEMPLATE = "/mnt/sata/Cyberpunk2077/ash-cache-quest/research/case_ex/json/q005_broken_suitcase.ent.json"
KEEP = {"ld_kit_suitcase_opened_a", "Collider0252", "defaultColider"}
# The template's colliders are "Interaction Object": they answer interaction rays and nothing
# walks into them, so a table built on them is walk-through. Vanilla solid devices use this
# preset (copied from ma_wbr_hil_05_fluff_dead_body_01.ent): blocks the player, visible to traces.
SOLID = {"$type": "physicsFilterData", "customFilterData": None,
         "preset": {"$type": "CName", "$storage": "string", "$value": "Device solid visible"},
         "queryFilter": {"$type": "physicsQueryFilter", "mask1": "0", "mask2": "70107400"},
         "simulationFilter": {"$type": "physicsSimulationFilter", "mask1": "114696", "mask2": "23627"}}


def fp(x):
    return {"$type": "FixedPoint", "Bits": int(round(x * 131072))}


def edit(comps, mesh, app, lo, hi, extra=()):
    comps = [c for c in comps if c["name"]["$value"] in KEEP]
    for c in comps:
        if c["$type"] == "entMeshComponent":
            c["name"]["$value"] = "mesh"
            c["mesh"] = {"DepotPath": {"$type": "ResourcePath", "$storage": "string", "$value": mesh}, "Flags": "Default"}
            c["meshAppearance"]["$value"] = app
            c["localTransform"] = {"$type": "WorldTransform",
                                   "Orientation": {"$type": "Quaternion", "i": 0, "j": 0, "k": 0, "r": 1},
                                   "Position": {"$type": "WorldPosition", "x": fp(0), "y": fp(0), "z": fp(0)}}
            c["visualScale"] = {"$type": "Vector3", "X": 1, "Y": 1, "Z": 1}
        elif c["$type"] == "entColliderComponent":
            if "Data" in c.get("filterData", {}):  # editor copy holds a handle ref
                c["filterData"]["Data"] = copy.deepcopy(SOLID)
            p = c["localTransform"]["Position"]
            p["x"], p["y"], p["z"] = (fp((lo[k] + hi[k]) / 2) for k in "XYZ")
            for col in (x for x in c["colliders"] if "Data" in x):  # editor copy holds handle refs
                col["Data"]["halfExtents"] = {"$type": "Vector3", **{k: (hi[k] - lo[k]) / 2 for k in "XYZ"}}
    base = next(c for c in comps if c["$type"] == "entMeshComponent")
    for n, path in enumerate(extra, 1):
        part = copy.deepcopy(base)
        part["name"]["$value"] = f"mesh{n}"
        part["id"] = str(7310046598145880064 + n)  # unused by the template
        part["mesh"]["DepotPath"]["$value"] = path
        comps.insert(comps.index(base) + n, part)
    return comps


def main(mesh, mesh_json, app, ent, outdir, *extra):
    bb = json.load(open(mesh_json))["Data"]["RootChunk"]["boundingBox"]
    lo, hi = bb["Min"], bb["Max"]
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    doc = json.load(open(TEMPLATE))
    root = doc["Data"]["RootChunk"]
    root["components"] = edit(root["components"], mesh, app, lo, hi, extra)
    pkg = root["compiledData"]["Data"]
    pkg["Chunks"] = [pkg["Chunks"][0]] + edit(pkg["Chunks"][1:], mesh, app, lo, hi, extra)
    # CruidDict: chunk index -> component id, 0 being the entity itself.
    pkg["CruidDict"] = {"0": "0", **{str(i + 1): c["id"] for i, c in enumerate(pkg["Chunks"][1:])}}
    name = ent.split("\\")[-1]
    doc["Header"]["ArchiveFileName"] = ent
    jp = f"{outdir}/{name}.json"
    json.dump(doc, open(jp, "w"), indent=1)
    r = subprocess.run(["dotnet", WK, "convert", "deserialize", jp, "-o", outdir],
                       env={**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}, capture_output=True, text=True)
    bad = [l for l in r.stdout.splitlines() if "Error" in l or "Exception" in l]
    if bad or not os.path.exists(f"{outdir}/{name}"):
        sys.exit(f"{name}: " + "\n".join(bad or r.stdout.splitlines()[-4:]))
    names = [c["name"]["$value"] for c in pkg["Chunks"][1:]]
    print(f"{name}: {', '.join(names)}; box {[round(hi[k] - lo[k], 3) for k in 'XYZ']}")


if __name__ == "__main__":
    main(*sys.argv[1:])
