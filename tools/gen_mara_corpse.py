#!/usr/bin/env python3
"""Mara's body at the landfill: her own outfit and face, dead, with the wound D122 gave her (D175).

The game draws a corpse as an entCorpseComponent plus a generated .app: the character's skinned
meshes, bound to that component, posed by entCorpseParameter.bakedPose (one model-space
transform per bone name). Nothing is re-skinned or exported - this builds such an .app out of
Mara's own appearance, corpo__nusa_wa.app/_q306__fia_undercover_01, and one vanilla corpse pose:

    mara_shot  wa_generic_valentinos_01's pose, sprawled on her back. Three gunshot wounds grouped
               on the torso (D122: gave her the Liberty).
    mara_cut   wa_generic_citizen_01's pose, on her back with the arms up. Incised wounds on the
               neck and both forearms, the forearm ones defensive (D122: told her to get lost).

Bones outside woman_base.rig (hair, garment, face joints) are re-derived from Mara's own bind
poses: the vanilla pose placed them for ITS meshes, and a face baked for another head is a
different face. Wound decals are placed on the posed skin (tools/posed_skin.py), because a
corpse decal is a 3 cm box and a guessed body thickness misses it.

    gen_mara_corpse.py <outdir>      writes <outdir>/ash_mara_corpse.app and .ent
"""
import copy, json, os, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from posed_skin import Body, baked_pose, mat_to_q, trs

EX = "/mnt/sata/Cyberpunk2077/game_extract"
DEV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dev", "mara_dead")
WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
MARA_APP = f"{EX}/ep1/characters/appearances/corpo/corpo__nusa_wa.app.json"
MARA_APPEARANCE = "_q306__fia_undercover_01"
TEMPLATE_ENT = f"{EX}/base/quest/main_quests/part1/q105/entities/q105_fluff_dead_body_01.ent.json"
TEMPLATE_APP = f"{EX}/base/characters/appearances/corpse/generated/wa_q105_fluff_01.app.json"
BODY_GLB = f"{DEV}/glb/base/characters/common/base_bodies/woman_average/t0_000_wa_base__full.glb"
DEPOT = "mod\\ash_cache\\characters\\mara_corpse\\ash_mara_corpse"
DECALS = "base\\characters\\common\\corpse\\common\\decals\\materials\\"

# Components a corpse has no use for: animation (the pose is baked), the face rig and the
# earring dangle rig (their bones are in the baked pose), the jaw slot, light blocking.
DROP_TYPES = {"entAnimationSetupExtensionComponent", "entAnimatedComponent", "entSlotComponent",
              "entLightBlockingComponent"}

# Wounds, in the body's BIND space (Z up, she faces +Y, her left is -X). "at" is (x, z) - the
# skin nearest it in x/z - or an (x, y, z) inside a limb - the skin nearest it in 3D - among
# vertices whose normal faces "facing". "along" is the
# decal's long axis in bind space; "size" is (long, short, depth) in metres.
VARIANTS = {
    "mara_shot": {
        "pose": "wa_generic_valentinos_01",
        "wounds": [
            ("corpse_dec_006_gunshot_blood_mixed.mi", (-0.070, 1.235), (0, 1, 0), (1, 0, 0), (0.035, 0.035, 0.10)),
            ("corpse_dec_006_gunshot_blood_mixed.mi", (-0.015, 1.180), (0, 1, 0), (0, 0, 1), (0.035, 0.035, 0.10)),
            ("corpse_dec_006_gunshot_blood_mixed.mi", (-0.095, 1.150), (0, 1, 0), (1, 0, 1), (0.035, 0.035, 0.10)),
            # the three bled together down the side she lies towards
            ("corpse_dec_002_splatter_blood_mixed.mi", (-0.050, 1.170), (0, 1, 0), (0, 0, 1), (0.22, 0.22, 0.12)),
        ],
    },
    "mara_cut": {
        "pose": "wa_generic_citizen_01",
        "wounds": [
            # across the left side of the neck
            ("corpse_dec_007_incised_blood_mixed.mi", (-0.045, 1.455), (-0.7, 0.7, 0), (0.7, 0.7, -0.15), (0.075, 0.03, 0.08)),
            # defensive: the outer edge of both forearms, across the arm. The points are on the
            # bone axis (elbow -0.33,-0.02,1.29 -> wrist -0.43,0.17,1.14), so the nearest
            # outward-facing vertex is forearm skin and never thigh
            ("corpse_dec_007_incised_blood_mixed.mi", (-0.372, 0.058, 1.225), (-1, -0.3, 0), (0, 0.55, 0.75), (0.07, 0.025, 0.08)),
            ("corpse_dec_007_incised_blood_mixed.mi", (-0.400, 0.110, 1.185), (-1, -0.3, 0), (0.2, 0.55, 0.75), (0.06, 0.025, 0.08)),
            ("corpse_dec_007_incised_blood_mixed.mi", (0.372, 0.058, 1.225), (1, -0.3, 0), (0, 0.55, 0.75), (0.07, 0.025, 0.08)),
            # the neck bled onto the chest
            ("corpse_dec_001_splatter_blood_mixed.mi", (-0.030, 1.380), (0, 1, 0), (0, 0, 1), (0.20, 0.20, 0.12)),
        ],
    },
}


def cname(s):
    return {"$type": "CName", "$storage": "string", "$value": s}


def rpath(s, flags="Default"):
    return {"DepotPath": {"$type": "ResourcePath", "$storage": "string", "$value": s}, "Flags": flags}


def fixed(v):
    return {"$type": "FixedPoint", "Bits": int(round(v * 131072))}


def wtransform(pos, q):
    return {"$type": "WorldTransform",
            "Orientation": {"$type": "Quaternion", "i": q[0], "j": q[1], "k": q[2], "r": q[3]},
            "Position": {"$type": "WorldPosition", "x": fixed(pos[0]), "y": fixed(pos[1]), "z": fixed(pos[2])}}


# --- handles ------------------------------------------------------------------------------
# WolvenKit JSON writes a shared handle once ("HandleId" + "Data") and refers back to it
# ("HandleRefId"). Components get dropped and copied here, so every handle is expanded to its
# own copy first and renumbered at the end.

def collect(n, table):
    if isinstance(n, dict):
        if "HandleId" in n and "Data" in n:
            table[n["HandleId"]] = n["Data"]
        for v in n.values():
            collect(v, table)
    elif isinstance(n, list):
        for x in n:
            collect(x, table)


def expand(n, table):
    if isinstance(n, dict):
        if "HandleRefId" in n and len(n) == 1:
            return {"HandleId": "?", "Data": expand(copy.deepcopy(table[n["HandleRefId"]]), table)}
        return {k: expand(v, table) for k, v in n.items()}
    if isinstance(n, list):
        return [expand(x, table) for x in n]
    return n


def renumber(n, counter, buffers):
    """Handle ids and buffer ids are both per file; the two appearances are copies of one."""
    if isinstance(n, dict):
        if "HandleId" in n and "Data" in n:
            n["HandleId"] = str(counter[0])
            counter[0] += 1
        if "BufferId" in n:
            n["BufferId"] = str(buffers[0])
            buffers[0] += 1
        for v in n.values():
            renumber(v, counter, buffers)
    elif isinstance(n, list):
        for x in n:
            renumber(x, counter, buffers)


# --- pose -----------------------------------------------------------------------------------

ARCHIVES = ["/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc/content",
            "/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc/ep1"]
ENV = {**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}


def depot_json(depot):
    """game_extract/<depot>.json, unbundled and serialized on first use."""
    p = f"{EX}/{depot.replace(chr(92), '/')}"
    if not os.path.exists(p):
        for arc in ARCHIVES:
            subprocess.run(["dotnet", WK, "unbundle", arc, "-o", EX, "-w", depot], env=ENV, capture_output=True)
            if os.path.exists(p):
                break
    if not os.path.exists(p + ".json"):
        subprocess.run(["dotnet", WK, "convert", "serialize", p, "-o", os.path.dirname(p)], env=ENV, capture_output=True)
    return json.load(open(p + ".json"))


def mesh_binds(paths):
    """Bind pose, bone -> 4x4, from the meshes' own inverse bind matrices."""
    out = {}
    for p in paths:
        r = depot_json(p)["Data"]["RootChunk"]
        for b, m in zip(r.get("boneNames", []), r.get("boneRigMatrices", [])):
            M = np.array([[m[row][c] for c in "XYZW"] for row in "XYZW"])
            out.setdefault(b["$value"], np.linalg.inv(M).T)   # rows are X Y Z W, translation in W
    return out


def app_meshes(appearance):
    return [c["mesh"]["DepotPath"]["$value"] for c in appearance["components"]
            if "mesh" in c and "proxy" not in c["mesh"]["DepotPath"]["$value"]
            and c["mesh"]["DepotPath"]["$value"].endswith(".mesh") and "fx\\meshes" not in c["mesh"]["DepotPath"]["$value"]]


def corpse_param(app_json):
    a = app_json["Data"]["RootChunk"]["appearances"][0]["Data"]
    for pb in a["parametersBuffer"]["parameterBuffers"]:
        for f in pb["Data"]["Files"]:
            if f["RootChunk"]["$type"] == "entCorpseParameter":
                return pb, f
    raise SystemExit("no entCorpseParameter")


def rebake(orig, orig_binds, binds):
    """The vanilla pose is exact for the vanilla corpse's meshes. Each bone is re-seated on
    Mara's bind: pose * inv(their bind) * her bind - identity where the two agree (the body,
    the rig), a correction where they do not (another head's face joints, another hair's
    strands). Face joints the vanilla head never had ride rigidly on Head."""
    pose, moved = {}, 0
    for b, bind in binds.items():
        if b in orig and b in orig_binds:
            pose[b] = orig[b] @ np.linalg.inv(orig_binds[b]) @ bind
            moved += not np.allclose(orig_binds[b], bind, atol=1e-4)
        elif b in orig:
            pose[b] = orig[b]
        else:
            pose[b] = orig["Head"] @ np.linalg.inv(orig_binds["Head"]) @ bind
            moved += 1
    return pose, moved


def qs(m):
    q = mat_to_q(m[:3, :3])
    t = m[:3, 3]
    return {"$type": "QsTransform",
            "Rotation": {"$type": "Quaternion", "i": q[0], "j": q[1], "k": q[2], "r": q[3]},
            "Scale": {"$type": "Vector4", "W": 1, "X": 1, "Y": 1, "Z": 1},
            "Translation": {"$type": "Vector4", "W": 1, "X": float(t[0]), "Y": float(t[1]), "Z": float(t[2])}}


# --- wounds ---------------------------------------------------------------------------------

def place(body, posed_p, posed_n, pose, at, facing, along):
    facing = np.asarray(facing, float) / np.linalg.norm(facing)
    ok = body.N @ facing > 0.5
    if len(at) == 3:   # a point inside the limb: nearest facing skin
        d = np.linalg.norm(body.P - np.asarray(at), axis=1)
    else:              # (x, z) on the front of the torso
        d = np.hypot(body.P[:, 0] - at[0], body.P[:, 2] - at[1])
    v = int(np.argmin(np.where(ok, d, np.inf)))
    p, n = posed_p[v], posed_n[v]
    # carry the bind-space long axis through the same skinning as the vertex, then square it
    # up against the posed normal
    J, W = body.J[v], body.W[v]
    M = sum(w * (pose[body.bones[j]] @ np.linalg.inv(body.bind[j]))[:3, :3]
            for j, w in zip(J, W) if w > 0 and body.bones[j] in pose)
    x = M @ np.asarray(along, float)
    x = x - n * (x @ n)
    x /= np.linalg.norm(x)
    R = np.column_stack([x, np.cross(n, x), n])   # decal projects along its local Z
    return p, mat_to_q(R), body.P[v]


def decal_pair(tpl_helper, tpl_decal, idx, mat, pos, q, size):
    h = copy.deepcopy(tpl_helper)
    d = copy.deepcopy(tpl_decal)
    hn = f"ash_wound_{idx:02d}"
    h["name"] = cname(hn)
    h["localTransform"] = wtransform(pos, q)
    h["id"] = str(0x5A5A000000000000 + idx * 2)
    h["parentTransform"]["Data"]["bindName"] = cname("root")
    d["name"] = cname(f"ash_wound_decal_{idx:02d}")
    d["id"] = str(0x5A5A000000000001 + idx * 2)
    d["material"] = rpath(DECALS + mat, "Obligatory")
    d["visualScale"] = {"$type": "Vector3", "X": size[0], "Y": size[1], "Z": size[2]}
    d["localTransform"] = wtransform((0, 0, 0), (0, 0, 0, 1))
    d["parentTransform"]["Data"]["bindName"] = cname(hn)
    return h, d


# --- build ----------------------------------------------------------------------------------

def main(outdir):
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    mara = json.load(open(MARA_APP))
    table = {}
    collect(mara, table)
    src = next(a["Data"] for a in mara["Data"]["RootChunk"]["appearances"]
               if a["Data"]["name"]["$value"] == MARA_APPEARANCE)
    src = expand(copy.deepcopy(src), table)

    tpl = json.load(open(TEMPLATE_APP))
    ttab = {}
    collect(tpl, ttab)
    tcomps = expand(tpl["Data"]["RootChunk"]["appearances"][0]["Data"]["components"], ttab)
    tpl_helper = next(c for c in tcomps if c["name"]["$value"].startswith("corpse_dec_"))
    tpl_decal = next(c for c in tcomps if c["$type"] == "entDecalComponent")

    comps, meshes = [], []
    for c in src["components"]:
        if c["$type"] in DROP_TYPES or c["name"]["$value"] == "AppearanceProxyMesh":
            continue
        for k in ("skinning", "parentTransform"):
            b = c.get(k)
            if b and b.get("Data") and "bindName" in b["Data"]:
                b["Data"]["bindName"] = cname("root")
                if "slotName" in b["Data"]:
                    b["Data"]["slotName"] = cname("None")
        if "mesh" in c:
            # D183: vanilla corpses use "Appearance". "AlwaysVisible" broke skinning once the
            # meshes went to LOD0 (camera within ~2 m): her whole body streaked at the camera.
            c["LODMode"] = "Appearance"
            meshes.append(c["mesh"]["DepotPath"]["$value"])
        comps.append(c)
    binds = mesh_binds(meshes)
    garment = src["parametersBuffer"]["parameterBuffers"]
    body = Body(BODY_GLB)

    apps = []
    for name, spec in VARIANTS.items():
        pj = json.load(open(f"{DEV}/corpse_json/{spec['pose']}.app.json"))
        pb, pf = corpse_param(pj)
        param = copy.deepcopy(pf["RootChunk"])
        theirs = mesh_binds(app_meshes(pj["Data"]["RootChunk"]["appearances"][0]["Data"]))
        pose, moved = rebake(baked_pose(param), theirs, binds)
        # D182: vanilla lists its bones in rig order (Hips, Spine, ...), extras after. An
        # alphabetical list left part of her mesh flung off to a far point in game.
        vorder = [n["$value"] for n in param["bakedBoneNames"]]
        names = [b for b in vorder if b in pose] + sorted(set(pose) - set(vorder))
        param["bakedBoneNames"] = [cname(b) for b in names]
        param["bakedPose"] = [qs(pose[b]) for b in names]
        param["forceLOD0Components"] = [c["id"] for c in comps if "mesh" in c]
        corpse_buf = copy.deepcopy(pb)
        corpse_buf["Data"]["Files"] = [dict(pf, RootChunk=param)]

        pp, pn = body.pose(pose)
        extra = []
        print(f"{name}: pose {spec['pose']}, {len(names)} bones ({moved} re-seated on Mara's bind)")
        for i, (mat, at, facing, along, size) in enumerate(spec["wounds"]):
            p, q, bp = place(body, pp, pn, pose, at, facing, along)
            extra += decal_pair(tpl_helper, tpl_decal, i, mat, p, q, size)
            print(f"  {mat.split('.')[0]:40} bind {np.round(bp, 3)} -> posed {np.round(p, 3)}")

        a = copy.deepcopy(src)
        a["name"] = cname(name)
        a["components"] = comps + extra
        # WolvenKit's writer refills the package from components; the CRUID dict is not read
        a["compiledData"]["Data"] = {"Version": 4, "Sections": 7, "CruidIndex": -1, "CruidDict": {}, "Chunks": []}
        a["parametersBuffer"]["parameterBuffers"] = copy.deepcopy(garment) + [corpse_buf]
        a["proxyMesh"] = {"DepotPath": {"$type": "ResourcePath", "$storage": "uint64", "$value": "0"}, "Flags": "Default"}
        deps = [d for d in a.get("resolvedDependencies", []) if "proxy" not in d["DepotPath"]["$value"]]
        deps += [rpath(DECALS + w[0], "Soft") for w in spec["wounds"]]
        a["resolvedDependencies"] = list({d["DepotPath"]["$value"]: d for d in deps}.values())
        apps.append({"HandleId": "?", "Data": a})

    root = copy.deepcopy(tpl["Data"]["RootChunk"])
    root["appearances"] = apps
    root["baseEntityType"] = cname("WomanAverage")
    doc = {"Header": dict(tpl["Header"], ArchiveFileName=DEPOT + ".app"), "Data": {"Version": tpl["Data"]["Version"],
           "BuildVersion": tpl["Data"]["BuildVersion"], "RootChunk": root,
           "EmbeddedFiles": tpl["Data"].get("EmbeddedFiles", [])}}
    renumber(doc, [0], [0])
    write(doc, outdir, "ash_mara_corpse.app")

    ent = json.load(open(TEMPLATE_ENT))
    er = ent["Data"]["RootChunk"]
    one = er["appearances"][0]
    er["appearances"] = [dict(copy.deepcopy(one), name=cname(n), appearanceName=cname(n),
                              appearanceResource=rpath(DEPOT + ".app")) for n in VARIANTS]
    er["defaultAppearance"] = cname(next(iter(VARIANTS)))
    # the q105 body is a braindance prop: its scanner reads "dead netrunner" out of three
    # scanning.q105_* clue records. Cleared in the components AND the compiled copy of them.
    def no_clues(n):
        if isinstance(n, dict):
            if n.get("$type") == "gameScanningComponent":
                n["clues"] = []
            for v in n.values():
                no_clues(v)
        elif isinstance(n, list):
            for x in n:
                no_clues(x)
    no_clues(er)
    assert "q105" not in json.dumps(er["components"]) + json.dumps(er["compiledData"])
    ent["Header"]["ArchiveFileName"] = DEPOT + ".ent"
    write(ent, outdir, "ash_mara_corpse.ent")


def write(doc, outdir, fname):
    jp = f"{outdir}/{fname}.json"
    json.dump(doc, open(jp, "w"), indent=1)
    r = subprocess.run(["dotnet", WK, "convert", "deserialize", jp, "-o", outdir],
                       env={**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}, capture_output=True, text=True)
    bad = [l for l in r.stdout.splitlines() if "Error" in l or "Exception" in l]
    if bad or not os.path.exists(f"{outdir}/{fname}"):
        sys.exit(f"{fname}: " + "\n".join(bad or r.stdout.splitlines()[-4:]))
    os.remove(jp)
    print(f"{fname}: {os.path.getsize(f'{outdir}/{fname}')} bytes")


if __name__ == "__main__":
    main(*sys.argv[1:])
