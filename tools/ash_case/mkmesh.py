#!/usr/bin/env python3
"""body.glb / lid.glb -> ash_case_{body,lid}.mesh with two metal_base materials.

WolvenKit.CLI `import -k` rebuilds geometry onto an existing .mesh, so the
vanilla splinter mesh (one metal_base material) is the template. Its material
block is then rewritten to ours: submesh 0 = shell, submesh 1 = interior.

    mkmesh.py <dir with body.glb lid.glb> <outdir>          # the ash case
    mkmesh.py <dir> <outdir> <glb>:<mesh>:<mat,...> <depot>  # any other part,
        textures at <depot>\\textures\\<mat>_{d01,m01,r01,n01}.xbm
"""
import copy, json, os, shutil, subprocess, sys

WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
GP = "/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game"
TEMPLATE = "/mnt/sata/Cyberpunk2077/ash-cache-quest/research/case_ex/base/items/quest/q003__splinter_case/q003__splinter.mesh"
DEPOT = "mod\\ash_cache\\props\\ash_case"
ENV = {**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}
CASE = [("body", "ash_case_body"), ("lid", "ash_case_lid")]
CASE_MATS = ["ash_case", "ash_case_interior"]  # submesh 0 = shell, 1 = interior
SLOTS = {"BaseColor": "d01", "Metalness": "m01", "Roughness": "r01", "Normal": "n01"}
# Materials that glow (D150c). metal_base takes an Emissive mask + colour + EV; values copied
# from vanilla int_container_001__military_case_k.mesh (white mask, EV ~4).
EMISSIVE = {"ash_case_glow": {"color": (0, 200, 255), "ev": 5.0}}  # D150e: saturated cyan, reads as cyan not white


def wk(*a):
    r = subprocess.run(["dotnet", WK, *a], env=ENV, capture_output=True, text=True)
    bad = [l for l in r.stdout.splitlines() if "Error" in l or "Exception" in l]
    if bad:  # exit code is nonzero even on success (Oodle warning)
        sys.exit(f"WolvenKit {a[0]} failed:\n" + "\n".join(bad or r.stdout.splitlines()[-5:]))
    return r.stdout


def cname(v):
    return {"$type": "CName", "$storage": "string", "$value": v}


def build(src, out, part, name, mats, depot):
    work = os.path.join(out, "_work_" + part)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(f"{work}/raw")
    os.makedirs(f"{work}/cooked")
    os.makedirs(f"{work}/check")
    shutil.copy(f"{src}/{part}.glb", f"{work}/raw/{name}.glb")
    shutil.copy(TEMPLATE, f"{work}/cooked/{name}.mesh")
    wk("import", f"{work}/raw", "-o", f"{work}/cooked", "-k", "-gp", GP)
    wk("convert", "serialize", f"{work}/cooked/{name}.mesh", "-o", work)
    doc = json.load(open(f"{work}/{name}.mesh.json"))
    root = doc["Data"]["RootChunk"]
    chunks = len(root["renderResourceBlob"]["Data"]["header"]["renderChunkInfos"])
    assert chunks == len(mats), f"{name}: {chunks} chunks, expected {len(mats)} ({', '.join(mats)})"

    lmb = root["localMaterialBuffer"]
    proto = lmb["materials"][0]
    insts = []
    for mname in mats:
        m = copy.deepcopy(proto)
        m["values"] = [{"$type": "rRef:ITexture",
                        slot: {"DepotPath": {"$type": "ResourcePath", "$storage": "string",
                                             "$value": f"{depot}\\textures\\{mname}_{suf}.xbm"},
                               "Flags": "Default"}} for slot, suf in SLOTS.items()]
        glow = EMISSIVE.get(mname)
        if glow:
            r, g, b = glow["color"]
            m["values"] += [
                {"$type": "rRef:ITexture", "Emissive": {"DepotPath": {"$type": "ResourcePath", "$storage": "string",
                                                                      "$value": "engine\\textures\\editor\\white.xbm"}, "Flags": "Default"}},
                {"$type": "Float", "EmissiveEV": glow["ev"]},
                {"$type": "Color", "EmissiveColor": {"$type": "Color", "Alpha": 255, "Blue": b, "Green": g, "Red": r}}]
        insts.append(m)
    lmb["materials"] = insts
    # The cooked copy of the template's materials; WolvenKit rewrites it from
    # "materials" on deserialize only if it is not there to be kept.
    lmb.pop("rawData", None)
    lmb.pop("rawDataHeaders", None)
    ent0 = root["materialEntries"][0]
    root["materialEntries"] = []
    for i, mname in enumerate(mats):
        e = copy.deepcopy(ent0)
        e["index"], e["name"], e["isLocalInstance"] = i, cname(mname), 1
        root["materialEntries"].append(e)
    app = root["appearances"][0]
    app["Data"]["name"] = cname("default")
    app["Data"]["chunkMaterials"] = [cname(m) for m in mats]
    root["appearances"] = [app]
    json.dump(doc, open(f"{work}/{name}.mesh.json", "w"), indent=1)
    wk("convert", "deserialize", f"{work}/{name}.mesh.json", "-o", out)
    # Read it back: the only proof the material block survived the round trip.
    wk("convert", "serialize", f"{out}/{name}.mesh", "-o", work + "/check")
    chk = json.load(open(f"{work}/check/{name}.mesh.json"))["Data"]["RootChunk"]
    def show(v):
        k, x = list(v.items())[1]
        if isinstance(x, dict) and "DepotPath" in x:
            return k + "=" + x["DepotPath"]["$value"].split("\\")[-1]
        if isinstance(x, dict):  # Color
            return k + "=" + ",".join(str(x[c]) for c in ("Red", "Green", "Blue"))
        return f"{k}={x}"
    got = [[show(v) for v in m["values"]] for m in chk["localMaterialBuffer"]["materials"]]
    names = [e["name"]["$value"] for e in chk["materialEntries"]]
    b = chk["boundingBox"]
    print(f"{name}.mesh: {chunks} chunks, materials {names}, "
          f"bbox {[round(b['Min'][k], 3) for k in 'XYZ']}..{[round(b['Max'][k], 3) for k in 'XYZ']}")
    for n, g in zip(names, got):
        print(f"   {n}: {g}")
    shutil.rmtree(work)


if __name__ == "__main__":
    src, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])  # WolvenKit wants absolute
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 3:
        glb, name, mats = sys.argv[3].split(":")
        build(src, out, glb, name, mats.split(","), sys.argv[4])
    else:
        for part, name in CASE:
            build(src, out, part, name, CASE_MATS, DEPOT)
