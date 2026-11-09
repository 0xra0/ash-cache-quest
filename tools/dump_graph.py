#!/usr/bin/env python3
"""Serialise the BUILT .questphase back to JSON and print the graph.

The point is that this reads the packed engine resource, not the generator's own
intermediate. Anything the generator got structurally wrong either fails the
deserialise in build.sh step 4 or shows up here as the wrong wiring.

    python3 tools/dump_graph.py
"""
import json
import pathlib
import subprocess
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "build" / "tree" / "ash_cache.questphase"
VERIFY = ROOT / "build" / "verify"
WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"


def item_names():
    """hash -> Items.<record>, for every item this mod defines.

    WolvenKit cooks a TweakDBID written as a string into its hash, so the packed
    graph holds a bare number where the source held a name. Reversing it needs the
    candidate names, and the only ones that can legitimately appear here are the
    mod's own - so a grant whose id resolves to nothing is either a typo or a
    reference to an item nobody defined, and both are silent in game.
    """
    src = ROOT / "source" / "items.json"
    if not src.exists():
        return {}
    out = {}
    for i in json.loads(src.read_text(encoding="utf-8"))["items"]:
        n = f"Items.{i['record']}".encode()
        out[str((len(n) << 32) | (zlib.crc32(n) & 0xFFFFFFFF))] = n.decode()
    return out


ITEMS = item_names()


def label(data, idx):
    """One readable line per node."""
    t = data["$type"].replace("questDefinition", "").replace("NodeDefinition", "")

    def deref(o):
        while isinstance(o, dict) and ("HandleRefId" in o or "Data" in o):
            o = idx[o["HandleRefId"]] if "HandleRefId" in o else o["Data"]
        return o

    def cond(c):
        c = deref(c)
        k = c["$type"]
        if k == "questLogicalCondition":
            op = f" {c['operation']} "
            return "(" + op.join(cond(x) for x in c["conditions"]) + ")"
        inner = deref(c["type"])
        if k == "questFactsDBCondition":
            return f"{inner['factName']} {inner['comparisonType']} {inner['value']}"
        if k == "questJournalCondition":
            return f"journal {deref(inner['path'])['realPath'].split('/')[-1]} is {inner['state']}"
        return k

    if t == "questInput":
        return f"Input({data['socketName']['$value']})"
    if t == "questOutput":
        return f"Output({data['socketName']['$value']}, {data['type']})"
    if t == "questCondition":
        return f"If({cond(data['condition'])})"
    if t == "questPauseCondition":
        return f"Await({cond(data['condition'])})"
    if t == "questFactsDBManager":
        n = deref(data["type"])
        return f"SetFact({n['factName']} = {n['value']})"
    if t == "questJournal":
        n = deref(data["type"])
        p = deref(n["path"])["realPath"].split("/")[-1]
        extra = " optional" if n.get("optional") else ""
        return f"Journal({p}{extra})"
    if t == "questLogicalAnd":
        return f"And({data['inputSocketCount']} in)"
    if t == "questItemManager":
        n = deref(data["type"])
        if n["$type"] != "questAddRemoveItem_NodeType":
            return f"Item({n['$type']})"
        out = []
        for prm in n["params"]:
            prm = deref(prm)
            # refLocalPlayer is what actually addresses the player - isPlayer is 0
            # in every vanilla instance - so a grant that reaches nobody looks
            # exactly like a working one unless this is printed.
            who = "player" if deref(prm["entityRef"])["refLocalPlayer"] else "<<nobody>>"
            qty = f" x{prm['quantity']}" if prm["quantity"] != 1 else ""
            bell = " (notify)" if prm["sendNotification"] else ""
            raw = str(prm["itemID"]["$value"])
            # A hash means a record this mod ships (ITEMS knows those); a plain
            # "Items.*" string is a vanilla record borrowed as-is, which is what
            # the Blue Eyes payout does with Items.money (D120) - not a miss.
            name = (raw if raw.startswith("Items.") and "ashcache_" not in raw
                    else ITEMS.get(raw, f"<<no item hashes to {raw}>>"))
            out.append(f"{prm['nodeType']}({name}{qty} -> {who}){bell}")
        return " ".join(out)
    return t


def main():
    if not SRC.exists():
        sys.exit(f"{SRC} not found - run tools/build.sh first")
    VERIFY.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(f'DOTNET_ROLL_FORWARD=LatestMajor dotnet {WK} convert serialize '
                       f'"{SRC}" -o "{VERIFY}"', shell=True, capture_output=True, text=True)
    out = VERIFY / "ash_cache.questphase.json"
    if not out.exists():
        sys.exit(f"serialize failed:\n{r.stdout}\n{r.stderr}")

    d = json.loads(out.read_text(encoding="utf-8"))
    idx = {}

    def index(o):
        if isinstance(o, dict):
            if "HandleId" in o and "Data" in o:
                idx[o["HandleId"]] = o["Data"]
            for v in o.values():
                index(v)
        elif isinstance(o, list):
            for v in o:
                index(v)
    index(d)

    nodes = [n["Data"] for n in d["Data"]["RootChunk"]["graph"]["Data"]["nodes"]]
    names = {n["id"]: label(n, idx) for n in nodes}

    # An output socket's connections name their destination socket, which is owned by
    # the target node - so walk the target list to recover the edges.
    owner = {}
    for n in nodes:
        for s in n["sockets"]:
            s = idx[s["HandleRefId"]] if "HandleRefId" in s else s["Data"]
            owner[id(s)] = (n["id"], s["name"]["$value"])

    print(f"{len(nodes)} nodes\n")
    for n in nodes:
        outs = []
        for s in n["sockets"]:
            s = idx[s["HandleRefId"]] if "HandleRefId" in s else s["Data"]
            if s["type"] != "Output":
                continue
            for c in s["connections"]:
                c = idx[c["HandleRefId"]] if "HandleRefId" in c else c["Data"]
                dst = c["destination"]
                dst = idx[dst["HandleRefId"]] if "HandleRefId" in dst else dst["Data"]
                nid, sname = owner[id(dst)]
                outs.append(f"{s['name']['$value']}->[{nid}]{sname}")
        print(f"[{n['id']:2d}] {names[n['id']]:<52s} {'  '.join(outs) or '(end)'}")


if __name__ == "__main__":
    main()
