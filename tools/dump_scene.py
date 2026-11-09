#!/usr/bin/env python3
"""Serialise the BUILT .scene and its subtitle resource back, and print the script.

Same principle as dump_graph.py: read the packed engine resources, never the
generator's intermediates. This one goes further and JOINS them, following

    section event -> screenplayLineId -> screenplay line -> locstring ruid
                  -> subtitle entry -> the text a player actually reads

which is the one linkage nothing else can check. A broken join here means a scene
that plays the right number of silent, empty subtitle bars.

It also joins the second linkage the same way - a line's speaker id back to the
actor table - because a speaker id is a bare integer index. If it points past the
end of the cast the scene still plays; the line just comes from nobody, with no
nameplate and nothing to look at. Printed as a name, that is obvious on sight.

    python3 tools/dump_scene.py [locale]      (default ua-ua)
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TREE = ROOT / "build" / "tree"
VERIFY = ROOT / "build" / "verify"
WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
NO_ACTOR = 4294967295


def serialize(path):
    """Run the packed resource back through WolvenKit and load the JSON."""
    out = VERIFY / (path.name + ".json")
    if not out.exists() or out.stat().st_mtime < path.stat().st_mtime:
        VERIFY.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["dotnet", WK, "cr2w", "-p", str(path), "-o", str(VERIFY),
                            "--serialize"],
                           capture_output=True, text=True,
                           env={"DOTNET_ROLL_FORWARD": "LatestMajor", "PATH": "/usr/bin:/bin",
                                "HOME": str(pathlib.Path.home())})
        if not out.exists():
            sys.exit(f"could not serialise {path}:\n{r.stdout}{r.stderr}")
    return json.loads(out.read_text(encoding="utf-8"))


def main():
    locale = sys.argv[1] if len(sys.argv) > 1 else "ua-ua"
    scenes = sorted(TREE.glob("ash_cache_*.scene"))
    if not scenes:
        sys.exit("no built scene in build/tree - run tools/build.sh")

    subs = serialize(TREE / f"subtitlelines_{locale}.json")
    text = {e["stringId"]: e["femaleVariant"]
            for e in subs["Data"]["RootChunk"]["root"]["Data"]["entries"]}

    for path in scenes:
        root = serialize(path)["Data"]["RootChunk"]
        store = root["screenplayStore"]
        # itemId -> ruid, for both kinds; the two id spaces never collide because
        # the low byte of an itemId says which kind it is.
        ruid = {i["itemId"]["id"]: i["locstringId"]["ruid"]
                for i in store["lines"] + store["options"]}

        # An actor's lipsyncAnimSet is an index into this table, and a bad one is
        # the kind of dangle that shows up as a crash on spawn rather than an
        # error, so it gets resolved to a filename here like everything else.
        lipsync = [e["asyncRefLipsyncAnimSet"]["DepotPath"]["$value"]
                   for e in root["resouresReferences"]["lipsyncAnimSets"]]

        def lip(i):
            if i == NO_ACTOR:
                return "(unset)"
            if not 0 <= i < len(lipsync):
                return f"<<lipsync {i} of {len(lipsync)}>>"
            return str(lipsync[i]).rsplit("\\", 1)[-1]

        # A speaker id indexes this table by position; anything else is a dangle.
        cast = {a["actorId"]["id"]:
                (a["actorName"], a["specCharacterRecordId"]["$value"],
                 a["spawnDespawnParams"]["spawnMarkerNodeRef"]["$value"],
                 a["specAppearance"]["$value"], a["acquisitionPlan"],
                 lip(a["lipsyncAnimSet"]["id"]))
                for a in root["actors"]}
        for p in root["playerActors"]:
            cast[p["actorId"]["id"]] = (p["playerName"],
                                        p["specCharacterRecordId"]["$value"],
                                        "-", "-", p["acquisitionPlan"],
                                        lip(p["lipsyncAnimSet"]["id"]))
        speaker = {i["itemId"]["id"]: i["speaker"]["id"] for i in store["lines"]}

        def who(aid):
            if aid == NO_ACTOR:
                return "(nobody)"
            if aid not in cast:
                return f"<<actor {aid} is not in the cast>>"
            return cast[aid][0]

        entry = {e["nodeId"]["id"]: e["name"]["$value"] for e in root["entryPoints"]}
        exit_ = {e["nodeId"]["id"]: e["name"]["$value"] for e in root["exitPoints"]}
        nodes = {n["Data"]["nodeId"]["id"]: n["Data"]
                 for n in root["sceneGraph"]["Data"]["graph"]}

        def resolve(item_id, where):
            r = ruid.get(item_id)
            if r is None:
                return f"<<no screenplay entry for itemId {item_id} — {where}>>"
            if r not in text:
                return f"<<no {locale} subtitle for ruid {r} — {where}>>"
            return text[r]

        print(f"\n=== {path.name}  [{locale}]  "
              f"{len(store['lines'])} lines, {len(store['options'])} options ===")
        for aid in sorted(cast):
            name, rec, mark, app, plan, lipname = cast[aid]
            print(f"  actor {aid}  {name:<8} {plan:<14} {rec:<34} {mark:<12} {app}")
            print(f"           {'':<8} lipsync {lipname}")
        for nid in sorted(nodes):
            n = nodes[nid]
            t = n["$type"].replace("scn", "").replace("Node", "")
            tag = ""
            if nid in entry:
                tag = f"  <<entry {entry[nid]}>>"
            if nid in exit_:
                tag = f"  <<exit {exit_[nid]}>>"
            outs = " ".join(
                f"{s['stamp']['name']}->{','.join(str(d['nodeId']['id']) for d in s['destinations'])}"
                for s in n.get("outputSockets", []) if s["destinations"])
            print(f"[{nid}] {t:<10} {outs or '(end)':<24}{tag}")
            for ev in n.get("events", []):
                d = ev["Data"]
                if d["$type"] != "scnDialogLineEvent":
                    continue
                item = d["screenplayLineId"]["id"]
                print(f"        {d['startTime']:>6}ms +{d['duration']:<5} "
                      f"{who(speaker.get(item, NO_ACTOR)) + ':':<9}"
                      f"{resolve(item, f'node {nid}')}")
            if n["$type"] == "scnChoiceNode":
                print(f"        hub {n['mode']} -> {who(n['ataParams']['actorId']['id'])}"
                      f"  (style {n['ataParams']['visualizerStyle']})")
            for i, o in enumerate(n.get("options", [])):
                item = o["screenplayOptionId"]["id"]
                print(f"        [{i}] > {resolve(item, f'choice {nid} option {i}')}")


if __name__ == "__main__":
    main()
