#!/usr/bin/env python3
"""A spawnable point light .ent (D154) for the clinic dressing's accent lights.

Built from the case's template (vanilla q005_broken_suitcase.ent, a plain gameObject) keeping only
its entLightComponent "light" - the one gen_case_ent.py tunes for the opened case - with colour,
lumens and radius set here. The light sits at the entity origin.

    gen_light_ent.py <out .ent depot path> <outdir> <r,g,b> <lumens> <radius>
"""
import json, os, subprocess, sys

WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
TEMPLATE = "/mnt/sata/Cyberpunk2077/ash-cache-quest/research/case_ex/json/q005_broken_suitcase.ent.json"


def edit(comps, rgb, lm, radius):
    comps = [c for c in comps if c["name"]["$value"] == "light"]
    for c in comps:
        c["localTransform"]["Position"] = {"$type": "WorldPosition", **{k: {"$type": "FixedPoint", "Bits": 0} for k in "xyz"}}
        c["intensity"] = lm
        c["radius"] = radius
        c["color"].update({"Red": rgb[0], "Green": rgb[1], "Blue": rgb[2]})
    return comps


def main(ent, outdir, rgb, lm, radius):
    rgb = [int(v) for v in rgb.split(",")]
    lm, radius = float(lm), float(radius)
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    doc = json.load(open(TEMPLATE))
    root = doc["Data"]["RootChunk"]
    root["components"] = edit(root["components"], rgb, lm, radius)
    pkg = root["compiledData"]["Data"]
    pkg["Chunks"] = [pkg["Chunks"][0]] + edit(pkg["Chunks"][1:], rgb, lm, radius)
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
    print(f"{name}: light {rgb} {lm} lm r {radius}")


if __name__ == "__main__":
    main(*sys.argv[1:6])
