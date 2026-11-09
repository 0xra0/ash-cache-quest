#!/usr/bin/env python3
"""Serialise the BUILT sectors and block back, and print every world marker.

Same principle as dump_graph.py and dump_scene.py: read the packed engine
resources, never the generator's intermediates.

This one cross-checks the three things that must agree but live in different
files, and that nothing else in the build compares:

    block descriptor  ->  the sector depot path it points at
    sector nodes[]    <-> sector nodeRefs[]      (same order, same count)
    sector nodeData   ->  the NodeRef each instance actually carries
    marker NodeRefs   ->  the '#name' the journal and quest graph reference

A marker whose NodeRef does not match what a map pin asks for is invisible: the
pin points at nothing and the objective has no location, with no error anywhere.

    python3 tools/dump_sectors.py
"""
import base64
import json
import struct
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TREE = ROOT / "build" / "tree"
VERIFY = ROOT / "build" / "verify"
WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"


def serialize(path):
    out = VERIFY / (path.name + ".json")
    if not out.exists() or out.stat().st_mtime < path.stat().st_mtime:
        VERIFY.mkdir(parents=True, exist_ok=True)
        subprocess.run(["dotnet", WK, "convert", "serialize", str(path), "-o", str(VERIFY)],
                       check=True, capture_output=True,
                       env={**__import__("os").environ, "DOTNET_ROLL_FORWARD": "LatestMajor"})
    return json.loads(out.read_text(encoding="utf-8"))


def wanted_refs():
    """Every '#ac_*' NodeRef the rest of the source actually asks for."""
    import re
    src = ROOT / "source"
    found = {}
    for f in sorted(src.glob("*.json")):
        for m in re.findall(r"#(ac_[a-z0-9_]+)", f.read_text(encoding="utf-8")):
            found.setdefault(m, set()).add(f.name)
    return found


def check_node(name, i, nd, inst, problems, is_probe=False):
    """The parts of a placed node that only exist AFTER the round trip.

    Each of these is a field the generator writes and nothing else reads back, and
    each fails in game the same silent way: the object is not there. Reading them
    off the packed resource is the only place a typo shows up before the game.
    """
    t = nd["$type"]
    if t == "worldTriggerAreaNode":
        notif = [n["Data"]["$type"] for n in nd.get("notifiers", [])]
        if notif != ["questTriggerNotifier_Quest"]:
            problems.append(f"{name}[{i}]: trigger notifiers are {notif} - without a "
                            f"questTriggerNotifier_Quest the volume tells the quest nothing")
        out = (nd.get("outline") or {}).get("Data")
        if not out:
            problems.append(f"{name}[{i}]: trigger has no outline, so it has no shape")
            return
        pts = [(v["X"], v["Y"], v["Z"]) for v in out["points"]]
        raw = base64.b64decode(out["buffer"])
        n_buf = struct.unpack_from("<I", raw, 0)[0]
        buf_pts = [struct.unpack_from("<4f", raw, 4 + 16 * k)[:3] for k in range(n_buf)]
        height = struct.unpack_from("<f", raw, 4 + 16 * n_buf)[0]
        # points and buffer are two copies of one shape. If they disagree the
        # engine believes the buffer and the file lies about where the edges are.
        if buf_pts != pts:
            problems.append(f"{name}[{i}]: outline buffer {buf_pts} != points {pts}")
        if abs(height - out["height"]) > 1e-6:
            problems.append(f"{name}[{i}]: outline buffer height {height} != {out['height']}")
        sc = inst["Scale"]
        print(f"           trigger {2*sc['X']:.0f}x{2*sc['Y']:.0f} m, "
              f"{out['height'] * sc['Z']:.0f} m tall, {len(pts)}-point outline, buffer OK")
    elif t == "worldPopulationSpawnerNode":
        rec = nd["objectRecordId"].get("$value")
        live = bool(nd.get("spawnOnStart"))
        if live and not is_probe:
            problems.append(f"{name}[{i}]: spawnOnStart is set - the object would appear "
                            f"the moment the sector streams in, before the quest starts")
        if nd.get("instanceData") is not None:
            problems.append(f"{name}[{i}]: spawner carries instanceData; no sample does")
        print(f"           spawns {rec}, "
              + ("appears as soon as the sector streams in (probe)" if live
                 else "inert until the graph activates it"))
    elif t == "worldEntityNode":
        tmpl = nd["entityTemplate"]["DepotPath"].get("$value")
        app = nd["appearanceName"].get("$value")
        buf = "null" if nd.get("instanceData") is None else "a RedPackage buffer"
        if not isinstance(tmpl, str):
            problems.append(f"{name}[{i}]: entityTemplate did not survive as a path "
                            f"({tmpl!r}) - it would stream in as nothing")
        print(f"           {tmpl}")
        print(f"           appearance {app!r}, instanceData {buf}")


def main():
    block_path = TREE / "ash_cache.streamingblock"
    if not block_path.exists():
        sys.exit("no built streamingblock in build/tree - run tools/build.sh")

    block = serialize(block_path)["Data"]["RootChunk"]
    print(f"streamingblock  index oup={block['index']['oup']} "
          f"cell={block['index']['rldGridCell']}  "
          f"{len(block['descriptors'])} descriptor(s)")

    defined = {}
    problems = []
    world = json.loads((ROOT / "source" / "world.json").read_text(encoding="utf-8"))
    # A probe sector is allowed things quest content is not - see world.json's
    # "probe" key for what each one is asking and D15 for why.
    probe_sectors = {f"{s['id']}.streamingsector" for s in world["sectors"] if s.get("probe")}
    for d in block["descriptors"]:
        path = d["data"]["DepotPath"]["$value"]
        name = path.split("\\")[-1]
        box = d["streamingBox"]
        always = abs(box["Max"]["X"]) > 1e30 and abs(box["Min"]["X"]) > 1e30
        print(f"\n  {path}")
        print(f"    category={d['category']} level={d['level']} "
              f"ranges={d['numNodeRanges']} box={'+/-FLT_MAX' if always else 'BOUNDED'}")

        sec_path = TREE / name
        if not sec_path.exists():
            problems.append(f"block points at {name}, which was not built")
            continue
        sec = serialize(sec_path)["Data"]["RootChunk"]
        nodes = sec["nodes"]
        refs = [r["$value"] for r in sec["nodeRefs"]]
        data = sec["nodeData"]["Data"]
        print(f"    sector: category={sec['category']} level={sec['level']} "
              f"version={sec['version']}  {len(nodes)} node(s), "
              f"{len(refs)} nodeRef(s), {len(data)} instance(s)")
        # nodes and nodeData still have to agree one-for-one. nodeRefs no longer
        # does: since D132 a mesh or a collision box ships no NodeRef at all -
        # QuestPrefabRefHash 0, nothing in the pool - exactly as vanilla does
        # (one Dogtown sector lists 114 refs for 1648 nodes). So the count that
        # must match is the number of nodes that actually carry a name.
        named = sum(1 for inst in data
                    if isinstance(inst["QuestPrefabRefHash"].get("$value"), str)
                    and inst["QuestPrefabRefHash"]["$value"] not in ("0", ""))
        if len(nodes) != len(data):
            problems.append(f"{name}: nodes/nodeData disagree "
                            f"({len(nodes)}/{len(data)})")
        if named != len(refs):
            problems.append(f"{name}: {named} node(s) carry a NodeRef but the sector "
                            f"pools {len(refs)}")

        for inst in data:
            i = inst["NodeIndex"]
            nd = nodes[i]["Data"]
            ref = inst["QuestPrefabRefHash"].get("$value")
            # A uint64 0 is how "this node has no name" is stored, and it comes
            # back as the string "0" rather than as null.
            if ref in ("0", ""):
                ref = None
            p, o = inst["Position"], inst["Orientation"]
            short = ref.split("/")[-1] if isinstance(ref, str) else "<anonymous>"
            print(f"      [{i}] {nd['$type'][5:]:<16} {short:<22} "
                  f"({p['X']:9.2f},{p['Y']:9.2f},{p['Z']:8.2f})  k={o['k']:+.4f} r={o['r']:+.4f}")
            if isinstance(ref, str):
                # Membership, not position. gen_sector's own comment says the
                # pool is unordered - vanilla quest_9694582f55685f39 lists its
                # two refs in the opposite order to its two nodes - and with
                # geometry in the sector the indices cannot line up anyway.
                if ref not in refs:
                    problems.append(f"{name}[{i}]: nodeData ref {ref!r} is in no "
                                    f"nodeRefs entry, so nothing can resolve it")
                defined[short.lstrip("#")] = name
            inner = nd.get("data", {}).get("Data", {})
            if nd["$type"] == "worldStaticMarkerNode" and inner.get("$type") != "scnSceneMarker":
                problems.append(f"{name}[{i}]: marker payload is {inner.get('$type')!r}")
            check_node(name, i, nd, inst, problems, name in probe_sectors)

    print("\n-- NodeRefs the rest of source/ asks for --")
    deferred = {k for k in world.get("deferred", {}) if not k.startswith("_")}
    for ref, files in sorted(wanted_refs().items()):
        if ref in defined:
            state = f"OK   -> {defined[ref]}"
        elif ref in deferred:
            state = "deferred (declared in world.json)"
        else:
            state = "MISSING - no marker defines it"
            problems.append(f"{ref} referenced by {', '.join(sorted(files))} but no marker defines it")
        print(f"  #{ref:<22} {state:<34} used by {', '.join(sorted(files))}")

    # Probe nodes are SUPPOSED to be referenced by nothing - they exist to be
    # looked at in game, not to be pointed at by the journal (D15).
    probe_nodes = {m["id"]
                   for sec in world["sectors"] if sec.get("probe")
                   for key in ("markers", "triggers", "spawners", "props")
                   for m in sec.get(key, [])}
    unused = sorted(set(defined) - set(wanted_refs()))
    for u in unused:
        if u in probe_nodes:
            print(f"  (probe {u!r} - referenced by nothing on purpose, D15)")
        else:
            print(f"  (node {u!r} is defined but nothing references it)")

    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"sectors OK ({len(defined)} node(s) defined, "
          f"{len(deferred)} deferred, 0 problems)")


if __name__ == "__main__":
    main()
