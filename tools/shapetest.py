#!/usr/bin/env python3
"""Round-trip the graph node types that no shipped node uses yet.

`negtest.py` proves the validator catches bad SOURCE. This proves the emitter
writes shapes the ENGINE accepts, which is a different failure and a worse one:
a node whose payload is subtly wrong deserialises fine, packs fine, ships, and
then does nothing at runtime with no log line.

The check is a real round trip - build a throwaway .questphase holding one of
every new node and condition, deserialise it to CR2W with WolvenKit, serialise
it back, and read the fields out of what came back. WolvenKit refuses unknown
field names and bad enum values on the way in, and anything that survives to the
way out is what the engine would actually load. Nothing here is shipped; the
whole thing lives in build/shapetest/ and build.sh never looks there.

Run it after touching build_node_data or build_condition. It takes ~10 s.
"""
import json
import pathlib
import zlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import envelope
from gen_questphase import build_phase

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "shapetest"
WK = ["dotnet", "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"]

# One node per new emitter branch, wired into a line so the reachability check
# in build_phase passes. Every payload here mirrors a measured vanilla instance;
# reference/sectors.md says which file each came off.
GRAPH = {
    "nodes": [
        {"id": "in", "type": "input"},
        {"id": "spawn_both", "type": "spawn", "actions": [
            {"spawner": "#shape_spawner"},
            {"community": "#shape_community", "entry": "wave_1", "action": "Deactivate"}]},
        {"id": "wait_spawn", "type": "pause",
         "condition": {"spawned": "#shape_community", "entry": "av"}},
        {"id": "wait_dead", "type": "pause",
         "condition": {"killed": "#shape_community", "count": 3}},
        {"id": "wait_use", "type": "pause",
         "condition": {"interaction": "#shape_prop"}},
        {"id": "wait_open", "type": "pause",
         "condition": {"device": "#shape_door", "function": "IsOpen",
                       "controller": "DoorControllerPS"}},
        # Nested inside a logical condition too - the new terms have to survive
        # being operands, not just top-level conditions.
        {"id": "branch", "type": "condition", "condition": {"any": [
            {"interaction": "#shape_prop", "event": "Entered"},
            {"fact": "shape_fact", "value": 1}]}},
        # Two operations, a non-default operationType and quantity, and an
        # 'entry' - so names[] being populated and operations[] staying empty
        # are both observed rather than assumed.
        {"id": "loot_box", "type": "inject_loot", "target": "#shape_container",
         "entry": "stash_01",
         "items": [{"item": "shape_shard_01"},
                   {"item": "shape_shard_02", "quantity": 4,
                    "operation": "RemoveAll"}]},
        {"id": "out", "type": "output"},
    ],
    "links": [["in", "spawn_both"], ["spawn_both", "wait_spawn"],
              ["wait_spawn", "wait_dead"], ["wait_dead", "wait_use"],
              ["wait_use", "wait_open"], ["wait_open", "branch"],
              ["branch:True", "loot_box"], ["branch:False", "loot_box"],
              ["loot_box", "out"]],
}


def D(o):
    """Unwrap {HandleId, Data} until a typed object appears."""
    while isinstance(o, dict) and "$type" not in o and "Data" in o:
        o = o["Data"]
    return o


def collect(o, out):
    o = D(o)
    if isinstance(o, dict):
        if isinstance(o.get("$type"), str):
            out.setdefault(o["$type"], []).append(o)
        for v in o.values():
            collect(v, out)
    elif isinstance(o, list):
        for v in o:
            collect(v, out)


def tdbid(s):
    """What a TweakDBID string weighs once cooked.

    WolvenKit prints a TweakDBID back as its string only when the hash is in its
    own string table. Every id this project invents - and every id in this test -
    is absent from it, so what comes back is the number. That is not a downgrade:
    the number IS what the engine looks up, and reproducing it here from the
    documented formula proves the emitter hashed the right bytes.

    (len(str) << 32) | crc32(str), confirmed against the round-tripped values.
    """
    return (len(s) << 32) | zlib.crc32(s.encode())


def val(o):
    """CName / NodeRef / TweakDBID all serialise as {$type,$storage,$value}."""
    o = D(o)
    return o.get("$value") if isinstance(o, dict) else o


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    src = WORK / "shapes.questphase.json"
    src.write_text(json.dumps(envelope(build_phase(GRAPH), "CR2W"), indent=2) + "\n",
                   encoding="utf-8")

    cooked = WORK / "shapes.questphase"
    cooked.unlink(missing_ok=True)
    r = subprocess.run(WK + ["convert", "deserialize", str(src), "-o", str(WORK)],
                       capture_output=True, text=True,
                       env={"DOTNET_ROLL_FORWARD": "LatestMajor", "PATH": "/usr/bin:/bin",
                            "HOME": str(pathlib.Path.home())})
    if not cooked.exists():
        print("FAILED: WolvenKit would not deserialize the shapes")
        print(r.stdout.strip()[:800] or r.stderr.strip()[:800])
        return 1

    back = WORK / "back"
    back.mkdir(exist_ok=True)
    for stale in back.glob("*.json"):
        stale.unlink()
    subprocess.run(WK + ["convert", "serialize", "-p", str(cooked), "-o", str(back)],
                   capture_output=True, text=True,
                   env={"DOTNET_ROLL_FORWARD": "LatestMajor", "PATH": "/usr/bin:/bin",
                        "HOME": str(pathlib.Path.home())})
    got = list(back.glob("*.json"))
    if not got:
        print("FAILED: WolvenKit would not serialize the cooked file back")
        return 1

    found = {}
    collect(json.loads(got[0].read_text(encoding="utf-8")), found)

    def one(t):
        if t not in found:
            fails.append(f"{t}: not in the round-tripped file at all")
            return {}
        return found[t][0]

    fails = []
    # (type, field, reader, expected) - expected comes from the GRAPH above,
    # so a wrong emitter default shows up as a mismatch rather than silence.
    spawners = found.get("questSpawner_NodeType", [])
    if len(spawners) != 1:
        fails.append(f"questSpawner_NodeType: expected 1, got {len(spawners)}")
    else:
        s = spawners[0]
        if val(s.get("spawnerReference")) != "#shape_spawner":
            fails.append(f"questSpawner_NodeType.spawnerReference = "
                         f"{val(s.get('spawnerReference'))!r}")
        if s.get("action") != "Activate":
            fails.append(f"questSpawner_NodeType.action = {s.get('action')!r}")

    com = one("questCommunityTemplate_NodeType")
    for field, want in (("action", "Deactivate"), ("communityEntryName", "wave_1"),
                        ("communityEntryPhaseName", "None"),
                        ("spawnerReference", "#shape_community")):
        if com and val(com.get(field)) != want:
            fails.append(f"questCommunityTemplate_NodeType.{field} = "
                         f"{val(com.get(field))!r}, wanted {want!r}")

    sp = one("questCharacterSpawned_ConditionType")
    if sp:
        cp = D(sp.get("comparisonParams") or {})
        if (cp.get("comparisonType"), cp.get("count"), cp.get("entireCommunity")) \
                != ("Greater", 0, 1):
            fails.append(f"questCharacterSpawned comparisonParams = {cp}")
        names = [val(n) for n in D(sp.get("objectRef") or {}).get("names", [])]
        if names != ["av"]:
            fails.append(f"questCharacterSpawned objectRef.names = {names}")

    kd = one("questCharacterKilled_ConditionType")
    if kd:
        cp = D(kd.get("comparisonParams") or {})
        if (cp.get("comparisonType"), cp.get("count"), cp.get("entireCommunity")) \
                != ("GreaterOrEqual", 3, 0):
            fails.append(f"questCharacterKilled comparisonParams = {cp}")
        if (kd.get("killed"), kd.get("defeated"), kd.get("unconscious")) != (1, 1, 1):
            fails.append("questCharacterKilled: one of killed/defeated/unconscious "
                         "did not survive as 1")

    inter = found.get("questInteraction_ConditionType", [])
    if len(inter) != 2:
        fails.append(f"questInteraction_ConditionType: expected 2 "
                     f"(one plain, one nested in an OR), got {len(inter)}")
    else:
        events = sorted(i.get("eventType") for i in inter)
        if events != ["Entered", "Executed"]:
            fails.append(f"questInteraction eventType(s) = {events}")
        if any(val(i.get("objectRef")) != "#shape_prop" for i in inter):
            fails.append("questInteraction objectRef did not survive as #shape_prop")

    dv = one("questDevice_ConditionType")
    for field, want in (("deviceConditionFunction", "IsOpen"),
                        ("deviceControllerClass", "DoorControllerPS"),
                        ("objectRef", "#shape_door")):
        if dv and val(dv.get(field)) != want:
            fails.append(f"questDevice_ConditionType.{field} = {val(dv.get(field))!r}")

    # questInjectLoot. The wrapper matters as much as the payload: the engine
    # reaches the node type through questItemManagerNodeDefinition.type, so a
    # correct payload under the wrong definition class executes nothing.
    holders = [d for d in found.get("questItemManagerNodeDefinition", [])
               if D(d.get("type") or {}).get("$type") == "questInjectLoot_NodeType"]
    if len(holders) != 1:
        fails.append(f"questInjectLoot_NodeType: expected exactly 1 wrapped in a "
                     f"questItemManagerNodeDefinition, got {len(holders)}")
    lp = D((one("questInjectLoot_NodeType").get("params") or [{}])[0])
    if lp:
        ref = D(lp.get("objectRef") or {})
        er = ref.get("entityReference") or {}
        if val(er.get("reference")) != "#shape_container":
            fails.append(f"questInjectLoot objectRef.reference = "
                         f"{val(er.get('reference'))!r}")
        if [val(n) for n in er.get("names", [])] != ["stash_01"]:
            fails.append(f"questInjectLoot objectRef.names = "
                         f"{[val(n) for n in er.get('names', [])]}")
        # The whole point of the node: loot goes into a world object, so this is
        # 0 where questAddRemoveItem's equivalent is 1.
        if (ref.get("refLocalPlayer"), ref.get("mainPlayerObject")) != (0, 0):
            fails.append(f"questInjectLoot refLocalPlayer/mainPlayerObject = "
                         f"{(ref.get('refLocalPlayer'), ref.get('mainPlayerObject'))}"
                         f", wanted (0, 0)")
        if lp.get("operations") != []:
            fails.append(f"questInjectLoot legacy operations[] came back "
                         f"{lp.get('operations')!r}, wanted empty")
        got_ops = [(int(val(D(o).get("itemTDBID"))), D(o).get("operationType"),
                    D(o).get("quantity")) for o in lp.get("lootOperations", [])]
        want_ops = [(tdbid("Items.shape_shard_01"), "Inject", 1),
                    (tdbid("Items.shape_shard_02"), "RemoveAll", 4)]
        if got_ops != want_ops:
            fails.append(f"questInjectLoot lootOperations = {got_ops}, "
                         f"wanted {want_ops}")

    if fails:
        print(f"SHAPE TEST FAILED ({len(fails)}):")
        for f in fails:
            print(f"  {f}")
        return 1
    print(f"shapes OK ({len(found)} distinct type(s) round-tripped through CR2W: "
          f"2 spawn action(s), 4 new condition(s), 1 loot node)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
