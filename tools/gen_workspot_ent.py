#!/usr/bin/env python3
"""A spawnable 'workspot device' .ent: a plain gameObject whose only component points at one
vanilla .workspot (D171).

The glue spawns it on an NPC and calls WorkspotSystem.PlayInDeviceSimple(device, npc, ...), the
exact call AMM's Poses tab makes (and LocationStudio's npc_play_animation), proven in game on the
scene-spawned Mara while her meeting ran. A scene questUseWorkspot node crashed the game instead.

Built from two known-good files:
  - the q005_broken_suitcase.ent template gen_mesh_ent.py already ships (entity chunk: gameObject)
  - AMM's base\\amm_workspots\\entity\\workspot_anim.ent, for the workWorkspotResourceComponent and
    its compiledData chunk, re-pointed at our workspot. Its localTransform turns the workspot 180
    degrees, which is why AMM (and the glue) spawn the device at the NPC's yaw + 180.

    gen_workspot_ent.py <workspot depot path> <component name> <out .ent depot path> <outdir>
"""
import copy, json, os, subprocess, sys

WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
TEMPLATE_UNUSED = "/mnt/sata/Cyberpunk2077/ash-cache-quest/research/case_ex/json/q005_broken_suitcase.ent.json"
AMM = "/mnt/sata/Cyberpunk2077/wk_scratch/amm_ws/workspot_anim.ent.json"
AMM_COMPONENT = "amm_workspot_base"


def retarget(c, workspot, name):
    c = copy.deepcopy(c)
    c["name"]["$value"] = name
    c["workspotResource"] = {"DepotPath": {"$type": "ResourcePath", "$storage": "string", "$value": workspot},
                             "Flags": "Default"}
    return c


def main(workspot, name, ent, outdir):
    if not workspot.endswith(".workspot"):
        sys.exit(f"{workspot!r} is not a .workspot path")
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    # The whole AMM device, minus its other workspot components. A bare gameObject carrying only
    # the workspot component spawned fine, but PlayInDeviceSimple never put the NPC in it: the
    # device needs AMM's WorkspotMapperComponent / device controller around it (D171, in game).
    doc = json.load(open(AMM))
    root = doc["Data"]["RootChunk"]
    def keep(c):
        return c["$type"] != "workWorkspotResourceComponent" or c["name"]["$value"] == AMM_COMPONENT
    def fix(c):
        return retarget(c, workspot, name) if c["$type"] == "workWorkspotResourceComponent" else c
    root["components"] = [fix(c) for c in root["components"] if keep(c)]
    pkg = root["compiledData"]["Data"]
    pkg["Chunks"] = [fix(c) for c in pkg["Chunks"] if keep(c)]
    pkg["CruidDict"] = {str(i): c.get("id", "0") for i, c in enumerate(pkg["Chunks"])}
    doc["Header"]["ArchiveFileName"] = ent
    fname = ent.split("\\")[-1]
    jp = f"{outdir}/{fname}.json"
    json.dump(doc, open(jp, "w"), indent=1)
    r = subprocess.run(["dotnet", WK, "convert", "deserialize", jp, "-o", outdir],
                       env={**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}, capture_output=True, text=True)
    bad = [l for l in r.stdout.splitlines() if "Error" in l or "Exception" in l]
    if bad or not os.path.exists(f"{outdir}/{fname}"):
        sys.exit(f"{fname}: " + "\n".join(bad or r.stdout.splitlines()[-4:]))
    os.remove(jp)
    print(f"{fname}: component {name!r} -> {workspot}")


if __name__ == "__main__":
    main(*sys.argv[1:])
