#!/usr/bin/env python3
"""Mara's arms-crossed idle workspot: the vanilla stand_around__02 cut down to standing still (D171).

The vanilla workspot is a street-idle, not a pose. Played as-is on Mara it:
  - entered from hands-at-sides / walking (workEntryAnim), so the arms crossed only seconds in;
  - turned her 120 degrees each way after the look-at target (workLookAtDrivenTurn);
  - shuffled her feet (the *__shuffle__* clips in the random list) and walked out on random exits,
    which read as her trying to leave on the spot.
This keeps the tree and its animsets and drops those nodes, leaving the arms-crossed idle, the
look_around fidget and the fast exit.

    gen_idle_workspot.py <vanilla .workspot.json> <out depot path> <outdir>
"""
import json, os, subprocess, sys

WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
DROP_TYPES = {"workEntryAnim", "workExitAnim", "workLookAtDrivenTurn", "workReactionSequence"}
DROP_CLIPS = ("__shuffle__",)
IDLE = "stand__arms_crossed_front__01"


def keep(n):
    if not isinstance(n, dict):
        return True
    n = n.get("Data", n) if "HandleId" in n else n   # tree children are CHandle wrappers
    if not isinstance(n, dict):
        return True
    if n.get("$type") in DROP_TYPES:
        return False
    name = n.get("animName", {})
    name = name.get("$value", "") if isinstance(name, dict) else ""
    return not (n.get("$type") == "workAnimClip" and any(s in name for s in DROP_CLIPS))


def prune(n):
    if isinstance(n, dict):
        for k, v in n.items():
            if isinstance(v, list):
                n[k] = [prune(x) for x in v if keep(x)]
            else:
                prune(v)
    elif isinstance(n, list):
        for x in n:
            prune(x)
    return n


def settle(n):
    """One clip left: a 5-7 clip list that won't repeat the last 3 could never fill, and the
    sequence must not end and fall back to the (now empty) entry path."""
    if isinstance(n, dict):
        if n.get("$type") == "workRandomList":
            n.update(minClips=1, maxClips=1, dontRepeatLastAnims=0)
        if n.get("$type") == "workSequence" and n.get("idleAnim", {}).get("$value") == IDLE:
            n["loopInfinitely"] = 1
        for v in n.values():
            settle(v)
    elif isinstance(n, list):
        for x in n:
            settle(x)


def clips(n, out):
    if isinstance(n, dict):
        if n.get("$type") in ("workAnimClip", "workEntryAnim", "workExitAnim"):
            out.append(n["animName"]["$value"])
        for v in n.values():
            clips(v, out)
    elif isinstance(n, list):
        for x in n:
            clips(x, out)
    return out


def main(src, depot, outdir):
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    doc = json.load(open(src))
    prune(doc["Data"]["RootChunk"]["workspotTree"])
    settle(doc["Data"]["RootChunk"]["workspotTree"])
    doc["Header"]["ArchiveFileName"] = depot
    fname = depot.split("\\")[-1]
    jp = f"{outdir}/{fname}.json"
    json.dump(doc, open(jp, "w"), indent=1)
    r = subprocess.run(["dotnet", WK, "convert", "deserialize", jp, "-o", outdir],
                       env={**os.environ, "DOTNET_ROLL_FORWARD": "LatestMajor"}, capture_output=True, text=True)
    bad = [l for l in r.stdout.splitlines() if "Error" in l or "Exception" in l]
    if bad or not os.path.exists(f"{outdir}/{fname}"):
        sys.exit(f"{fname}: " + "\n".join(bad or r.stdout.splitlines()[-4:]))
    os.remove(jp)
    print(f"{fname}: clips {clips(doc['Data']['RootChunk']['workspotTree'], [])}")


if __name__ == "__main__":
    main(*sys.argv[1:])
