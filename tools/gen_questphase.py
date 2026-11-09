#!/usr/bin/env python3
"""source/quest_graph.json  ->  build/ash_cache.questphase.json

The quest graph IS the quest. Every node type below was read off a working
reference (Hot Fuzz mod 7832, Deceptious Quest Core) rather than inferred,
because four things about this format are not guessable:

  1. A journal node has no 'state' field. It has one INPUT SOCKET PER STATE
     (Active / Inactive / Succeeded / Failed) and you wire flow into the socket
     for the transition you want.
  2. A condition node is the mirror image: no state field either, but two
     OUTPUT sockets, True and False. You branch by which output you leave from.
  3. Fan-out and OR-join are both just multiple connections on one socket.
     An output socket with N connections activates all N targets in parallel
     (Hot Fuzz has one with 4); an input socket with N connections fires when
     ANY of them arrives (Deceptious has several). No join node is needed
     unless you want AND semantics - that is questLogicalAndNodeDefinition.
  4. Sockets are shared objects. A connection inlines one endpoint in full; the
     other endpoint refers back by HandleRefId. Connection and socket reference
     each other, so the emitter must claim an id before descending. See cr2w.S.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import H, S, check_enum, cname, envelope, lockey, noderef
from enums import (EComparisonType, GameplayTier, gameGodModeType,
                   gameJournalEntryState,
                   populationSpawnerObjectCtrlAction, questExitType,
                   questInjectLootOperationType, questLogicalOperation,
                   questObjectInteractionEventType, questPhoneCallMode,
                   questPhoneCallPhase, questPhoneCallVisuals)

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Input sockets each node type exposes, in the order the reference files list them.
# 'CutDestination' is always present and always unconnected; it is prepended below.
INPUTS = {
    "input":         [],
    "journal_quest": ["Active", "Inactive", "Succeeded", "Failed"],
    "journal_entry": ["Active", "Inactive"],
    "phone_call":    ["In"],
    "set_fact":      ["In"],
    "pause_fact":    ["In"],
    "pause":         ["In"],
    "condition":     ["In"],
    "output":        ["In"],
    "add_item":      ["In"],
    "inject_loot":   ["In"],
    "spawn":         ["In"],
    "set_tier":      ["In"],
    "set_mortality": ["In"],
    "shoot_at":      ["In"],
    "device_action": ["In"],
    "remove_item":   ["In"],
    "play_fx":       ["In"],
    # Both HUD nodes are questUIManagerNodeDefinition, and every vanilla one of
    # those carries the plain In/Out pair (q005_07's six, checked individually).
    "progress_bar":  ["In"],
    "warning_message": ["In"],
    # In1/Out1, not In/Out: a phase node's own sockets are matched by name
    # against the socketName of the input/output nodes INSIDE its phaseGraph,
    # and vanilla writes those as In1/Out1 (q305_07 node 128). Same rule as the
    # top-level phase, one level down.
    "prefab_phase":  ["In1"],
    # All 24 vanilla questTeleportPuppetNodeDefinitions: In / Out (+ CutDestination).
    "teleport":      ["In"],
    # Hot Fuzz's two questWorldDataManagerNodeDefinitions: In / Out (+ CutDestination).
    "show_world_node": ["In"],
}

# DoorControllerPS.GetQuestActionByName's switch, vanilla_scripts.reds:135033.
DOOR_QUEST_ACTIONS = {"ForceOpen", "ForceClose", "ForceCloseImmediate", "ForceOpenScene",
                      "ForceCloseScene", "ForceLock", "ForceUnlock", "ForceSeal",
                      "ForceUnseal"}

# Output sockets. Anything not listed gets a single "Out".
OUTPUTS = {
    "condition":    ["True", "False"],
    "output":       [],
    "prefab_phase": ["Out1"],
    # All 21 vanilla questCombatNodeDefinitions in combat_json are ShootAt with
    # sockets In / Success (+ CutDestination).
    "shoot_at":     ["Success"],
}


def inputs_of(spec):
    if spec["type"] == "and":
        return [f"In{i + 1}" for i in range(spec.get("count", 2))]
    if spec["type"] == "scene":
        # One input per scene entry point, plus Prefetch. Both references list
        # every entry point the .scene declares, whether or not it is wired.
        return list(spec["entries"]) + ["Prefetch"]
    if spec["type"] not in INPUTS:
        sys.exit(f"unknown node type {spec['type']!r} for node {spec['id']!r}")
    return INPUTS[spec["type"]]


def outputs_of(spec):
    if spec["type"] == "and":
        return ["Out1"]
    if spec["type"] == "scene":
        # One output per scene exit point. "Default INT"/"Default RET" carry the
        # interruption and return paths and are present on every scene node in
        # both references, wired or not.
        return list(spec["exits"]) + ["Default INT", "Default RET"]
    return OUTPUTS.get(spec["type"], ["Out"])


_lockeys = None


def lockey_ref(sid, where):
    """A symbolic string id from source/strings.json as the LocKey the engine wants.

    Rule 6: LocKeys come from the reserved block in source/lockeys.json and are
    never invented, so an unallocated id stops the build instead of inheriting a
    fresh number that would drift the next time the allocator ran. Everything
    else in this project resolves ids at its own layer (gen_tweak, gen_chip,
    gen_journal); the HUD nodes are the first quest nodes to need text, which is
    why the phase builder only learns about strings here.
    """
    global _lockeys
    if _lockeys is None:
        _lockeys = {k: v for k, v in json.loads(
            (ROOT / "source" / "lockeys.json").read_text(encoding="utf-8")).items()
            if not k.startswith("_")}
    if sid not in _lockeys:
        sys.exit(f"{where}: no LocKey allocated for string id {sid!r} - put the text "
                 f"in source/strings.json and run tools/alloc_lockeys.py")
    return lockey(_lockeys[sid])


def sock(name, typ):
    return S({"$type": "questSocketDefinition", "connections": [], "name": cname(name), "type": typ})


def _entity_ref():
    """A null gameEntityReference. Every field is the explicit 'unset' form, which
    for a NodeRef is uint64 0 rather than an empty string."""
    return {"$type": "gameEntityReference",
            "dynamicEntityUniqueName": cname("None"), "names": [],
            "reference": {"$type": "NodeRef", "$storage": "uint64", "$value": "0"},
            "sceneActorContextName": cname("None"), "slotName": cname("None"),
            "type": "EntityRef"}


def _node_ref(name, where):
    """A bare NodeRef, as questInteraction/questDevice/questSpawner take it.

    Not interchangeable with the gameEntityReference below: those two conditions
    address the node directly, while the character conditions wrap the same name
    in an entity reference so they can also name a community entry inside it.
    """
    if not isinstance(name, str) or not name.startswith("#"):
        sys.exit(f"{where}: node reference {name!r} must start with '#'")
    return {"$type": "NodeRef", "$storage": "string", "$value": name}


def _entity_ref_to(name, where, entry=None):
    """A gameEntityReference aimed at a world node, optionally at one named
    member of the community it spawns - vanilla's '#sa_ep1_31_av_com' + 'av'."""
    ref = _entity_ref()
    ref["reference"] = _node_ref(name, where)
    if entry:
        ref["names"] = [cname(entry)]
    return ref


def add_remove_item(spec, node_type="AddItem"):
    """Give the player an item, or take one back.

    Read field-for-field off vanilla's own q003.questphase - The Pickup, which
    grants Items.RavenControlSplinter and two states of the Flathead chip through
    three of these. All three agree, and two of the fields are the opposite of what
    a reasonable guess would set:

      isPlayer = 0.  Not 1. The player is NOT addressed with the isPlayer flag.
      entityRef = a questUniversalRef with refLocalPlayer = 1. THAT is how the
                  node finds the player, and it is the field that must be right.

    sendNotification is 0 in all three vanilla instances, so it is 0 by default
    here too; set "notify": true on the node to get the item-received popup. The
    quest already announces each grant with a journal objective, which is why
    vanilla can afford to stay silent.
    """
    return H({
        "$type": "questAddRemoveItem_NodeTypeParams",
        "entityRef": H({"$type": "questUniversalRef",
                        "entityReference": _entity_ref(),
                        "mainPlayerObject": 0,
                        "refLocalPlayer": 1}),
        "flagItemAddedCallbackAsSilent": 0,
        "isPlayer": 0,
        "itemID": {"$type": "TweakDBID", "$storage": "string",
                   "$value": f"Items.{spec['item']}"},
        "itemIDsToIgnoreOnRemove": [],
        "nodeType": node_type,
        "objectRef": _entity_ref(),
        "quantity": spec.get("quantity", 1),
        "removeAllQuantity": 0,
        "sendNotification": 1 if spec.get("notify") else 0,
        "tagsToIgnoreOnRemove": [],
        "tagToRemove": cname("None"),
    })


def inject_loot(spec, where):
    """Put items INSIDE a world object rather than into the player's pockets.

    Read off ma_std_arr_10_phase.questphase; the deserialised node is kept whole
    at reference/examples/questInjectLoot_node.json. Three fields are the kind
    that look wrong until you check them:

      refLocalPlayer = 0.  The exact opposite of add_remove_item above, and for
                  the obvious reason once stated: loot goes into a world object,
                  so the ref must NOT resolve to the player. Same trap as
                  questAddRemoveItem's isPlayer (D12), pointing the other way.
      the target is addressed TWICE.  A NodeRef ('#ac_splinter_case') picks the
                  sector node; an optional names[] entry picks one entity inside
                  it, which is how vanilla addresses 'ganger_001' within a
                  community node. A prop node holds one entity, so 'entry' is
                  omitted there and names[] stays empty.
      'operations' is a second, empty array beside 'lootOperations'.  Not a
                  typo in the reference. The RTTI says lootOperations is
                  CArray<CHandle<OperationData>> and operations is a bare
                  CArray<OperationData> - the pre-handle form of the same
                  struct, left in place for old data. Vanilla ships it empty in
                  all 317 uses and so do we.

    The wrapper is questItemManagerNodeDefinition, the same one add_item uses.
    That is not an assumption: questInjectLoot_NodeType and
    questAddRemoveItem_NodeType both derive from questIItemManagerNodeType, and
    questItemManagerNodeDefinition.type is a CHandle<questIItemManagerNodeType>.
    """
    items = spec.get("items")
    if not isinstance(items, list) or not items:
        sys.exit(f"{where}: an inject_loot node needs a non-empty 'items' list")
    ops = []
    for i, it in enumerate(items):
        if not isinstance(it, dict) or not it.get("item"):
            sys.exit(f"{where}: items[{i}] needs an 'item' id")
        qty = it.get("quantity", 1)
        if not isinstance(qty, int) or qty < 1:
            sys.exit(f"{where}: items[{i}] quantity {qty!r} must be a positive int")
        ops.append(H({
            "$type": "questInjectLoot_NodeTypeParams_OperationData",
            "itemTDBID": {"$type": "TweakDBID", "$storage": "string",
                          "$value": f"Items.{it['item']}"},
            "operationType": check_enum(it.get("operation", "Inject"),
                                        questInjectLootOperationType,
                                        f"{where}: items[{i}] operation"),
            "quantity": qty,
        }))
    return H({
        "$type": "questInjectLoot_NodeTypeParams",
        "lootOperations": ops,
        "objectRef": H({"$type": "questUniversalRef",
                        "entityReference": _entity_ref_to(spec.get("target"), where,
                                                          spec.get("entry")),
                        "mainPlayerObject": 0,
                        "refLocalPlayer": 0}),
        "operations": [],
    })


def journal_path(cls, path):
    return H({
        "$type": "gameJournalPath",
        "className": cname(cls),
        "editorPath": "",
        # 3 for quest entries, 1 for phone/contact entries - matches both references.
        "fileEntryIndex": 1 if path.startswith("contacts/") else 3,
        "realPath": path,
    })


def build_condition(c, where):
    """The condition DSL, shared by 'pause' and 'condition' nodes.

        {"fact": "x", "value": 1, "compare": "Equal"}   -> questFactsDBCondition
        {"journal": "path/to/obj", "state": "Succeeded"} -> questJournalCondition
        {"all": [...]} / {"any": [...]}                  -> questLogicalCondition

    questLogicalCondition nests, so 'all' and 'any' may contain each other -
    Hot Fuzz ships a 5-term OR with an AND inside it.
    """
    if not isinstance(c, dict):
        sys.exit(f"{where}: condition must be an object, got {c!r}")
    if "all" in c or "any" in c:
        op = "AND" if "all" in c else "OR"
        terms = c.get("all") or c.get("any")
        if len(terms) < 2:
            sys.exit(f"{where}: {op.lower()} needs at least two terms")
        return H({"$type": "questLogicalCondition",
                  "conditions": [build_condition(t, where) for t in terms],
                  "operation": check_enum(op, questLogicalOperation, f"{where} operation")})
    if "fact" in c:
        return H({"$type": "questFactsDBCondition",
                  "type": H({"$type": "questVarComparison_ConditionType",
                             "comparisonType": check_enum(c.get("compare", "Equal"),
                                                          EComparisonType,
                                                          f"{where} comparison"),
                             "factName": c["fact"],
                             "value": c.get("value", 1)})})
    if "journal" in c:
        return H({"$type": "questJournalCondition",
                  "type": H({"$type": "questJournalEntryState_ConditionType",
                             "inverted": 1 if c.get("inverted") else 0,
                             "path": journal_path(c.get("class", "gameJournalQuestObjective"),
                                                  c["journal"]),
                             "state": check_enum(c.get("state", "Succeeded"),
                                                 gameJournalEntryState, f"{where} state")})})
    if "delay" in c:
        # A wall-clock wait, in milliseconds. The field really is spelled
        # 'miliseconds' with one L - that is the engine's name for it, not a typo
        # to be helpfully corrected. questTimeCondition also has a game-time
        # sibling; this is the realtime one, which is what every wired INT/RET
        # safety net in the game uses, always at 500 ms.
        ms = c["delay"]
        if not isinstance(ms, int) or ms < 0:
            sys.exit(f"{where}: 'delay' is a whole number of milliseconds, got {ms!r}")
        return H({"$type": "questTimeCondition",
                  "type": H({"$type": "questRealtimeDelay_ConditionType",
                             "hours": 0, "miliseconds": ms, "minutes": 0,
                             "seconds": 0})})
    if "interaction" in c:
        # The player used a placed prop. eventType "Executed" is the press; the
        # volume-style "Entered"/"Exited" exist but no EP1 quest uses them.
        return H({"$type": "questObjectCondition",
                  "type": H({"$type": "questInteraction_ConditionType",
                             "eventType": check_enum(c.get("event", "Executed"),
                                                     questObjectInteractionEventType,
                                                     f"{where} interaction event"),
                             "objectRef": _node_ref(c["interaction"], where)})})
    if "device" in c:
        # A device's own controller answers the question. Both names are CNames
        # resolved at runtime against redscript classes, so a typo in either is
        # silent - the condition simply never becomes true.
        return H({"$type": "questObjectCondition",
                  "type": H({"$type": "questDevice_ConditionType",
                             "deviceConditionFunction": cname(c.get("function", "IsOpen")),
                             "deviceControllerClass": cname(c["controller"]),
                             "functionParameters": [],
                             "objectRef": _node_ref(c["device"], where)})})
    if "spawned" in c:
        # 39 of the 55 vanilla instances are exactly this: Greater 0 over the
        # entire community, i.e. "anyone at all has appeared yet".
        return H({"$type": "questCharacterCondition",
                  "type": H({"$type": "questCharacterSpawned_ConditionType",
                             "comparisonParams": comparison_param(c, where, "Greater", 0, 1),
                             "objectRef": _entity_ref_to(c["spawned"], where,
                                                         c.get("entry"))})})
    if "killed" in c:
        # 'count' is required and deliberately has no default. Both vanilla uses
        # name an explicit number with entireCommunity 0; there is no measured
        # "the whole group is dead" form, and inventing one would give a
        # condition that goes true on the first kill. See reference/sectors.md.
        if "count" not in c:
            sys.exit(f"{where}: a 'killed' condition needs a 'count' - how many of "
                     f"them have to be down. Vanilla never asks this of a whole "
                     f"community, and a wrong default fires on the first body.")
        return H({"$type": "questCharacterCondition",
                  "type": H({"$type": "questCharacterKilled_ConditionType",
                             "comparisonParams": comparison_param(c, where,
                                                                  "GreaterOrEqual",
                                                                  c["count"], 0),
                             # All three are 1 in both vanilla instances: a body
                             # counts however it stopped moving. Splitting them
                             # would let a non-lethal run stall the quest.
                             "defeated": 1, "killed": 1, "unconscious": 1,
                             "objectRef": _entity_ref_to(c["killed"], where,
                                                         c.get("entry")),
                             "source": None})})
    sys.exit(f"{where}: condition has no 'fact', 'journal', 'interaction', 'device', "
             f"'spawned', 'killed', 'all' or 'any' key: {c!r}")


def comparison_param(c, where, op, count, entire):
    return H({"$type": "questComparisonParam",
              "comparisonType": check_enum(c.get("compare", op), EComparisonType,
                                           f"{where} comparison"),
              "count": c.get("count", count),
              "entireCommunity": 1 if c.get("entire_community", entire) else 0})


def hold_graph(spec, where):
    """The sub-graph a prefab_phase node holds open: In1 -> pause -> Out1.

    The graph is deliberately almost empty. All the work is done by the node
    ABOVE it: a questPhaseNodeDefinition owns its phaseInstancePrefabs for
    exactly as long as it is running, so "keep this prefab streamed" is spelled
    "enter this phase and do not leave it yet". The pause is the leaving
    condition - while it blocks, the phase is alive and the prefab is loaded.
    """
    rel = spec.get("release")
    if not isinstance(rel, dict):
        sys.exit(f"{where}: prefab_phase needs a 'release' condition object - "
                 f"without one the phase can never exit and the prefabs it owns "
                 f"stay streamed until the save is reloaded")
    i_out = sock("Out", "Output")
    p_in, p_out = sock("In", "Input"), sock("Out", "Output")
    o_in = sock("In", "Input")
    for a, b in ((i_out, p_in), (p_out, o_in)):
        c = S({"$type": "graphGraphConnectionDefinition", "destination": b, "source": a})
        a.obj["connections"].append(c)
        b.obj["connections"].append(c)
    cut = lambda: sock("CutDestination", "CutDestination")
    return {"$type": "questGraphDefinition", "nodes": [
        H({"$type": "questInputNodeDefinition", "id": 0, "socketName": cname("In1"),
           "sockets": [cut(), i_out]}),
        H({"$type": "questPauseConditionNodeDefinition", "id": 1,
           "condition": build_condition(rel, where),
           "sockets": [cut(), p_in, p_out]}),
        H({"$type": "questOutputNodeDefinition", "id": 2, "socketName": cname("Out1"),
           "type": check_enum("Terminating", questExitType, f"{where} exit type"),
           "sockets": [cut(), o_in]}),
    ]}


def build_node_data(spec, nid):
    t = spec["type"]
    where = f"node {spec['id']!r}"
    # In1/Out1, not In/Out. ArchiveXL synthesises the questPhaseNodeDefinition in
    # the parent quest and hardcodes its sockets to those names; the engine enters
    # this graph by matching the parent socket name against an input node here.
    # A mismatch merges cleanly and executes nothing. See D20.
    if t == "input":
        return {"$type": "questInputNodeDefinition", "id": nid,
                "socketName": cname(spec.get("socket", "In1"))}
    if t == "output":
        return {"$type": "questOutputNodeDefinition", "id": nid,
                "socketName": cname(spec.get("socket", "Out1")),
                "type": check_enum(spec.get("exit", "Terminating"), questExitType,
                                   f"{where} exit type")}
    if t == "journal_quest":
        optional = 1 if spec.get("optional") else 0
        return {"$type": "questJournalNodeDefinition", "id": nid,
                "type": H({"$type": "questJournalQuestEntry_NodeType",
                           "optional": optional,
                           "path": journal_path(spec["class"], spec["path"]),
                           "sendNotification": 1 if spec.get("notify", True) else 0,
                           "trackQuest": 1 if spec.get("track", True) else 0,
                           # Vanilla never once ships optional=1 with version
                           # Initial: 11 cases out of 11 across all 11,794
                           # quest-entry nodes in the game (OI-4). So this
                           # pairing is right. The reason it is right is NOT
                           # that the enum announces the property - 2,281
                           # vanilla nodes stamp OptionalProperty with
                           # optional=0. It is a format-version stamp, and the
                           # implication only runs one way. Do not read it back.
                           "version": "OptionalProperty" if optional else "Initial"})}
    if t == "journal_entry":
        return {"$type": "questJournalNodeDefinition", "id": nid,
                "type": H({"$type": "questJournalEntry_NodeType",
                           "path": journal_path(spec["class"], spec["path"]),
                           "sendNotification": 1 if spec.get("notify", True) else 0})}
    if t == "phone_call":
        # D124. The ONLY way to open the phone UI. The engine ships no scene-side
        # phone event whatsoever - `strings` on Cyberpunk2077.exe returns nothing
        # for ^scn.*(Phone|Call|Holo).*$ - so a call is not a property of the
        # conversation, it is a quest node that brackets one.
        #
        # Field for field with vanilla's NPC-calls-V shape, read out of
        # q112_03_infiltration (Takemura, twice) and q104_gas_station (Panam):
        #
        #   caller/addressee   gameJournalContact paths. 'contacts/player' is a
        #                      real vanilla journal entry; phoneSystem.script
        #                      resolves whichever end is NOT the player and looks
        #                      the contact up by id, so the id in journal.json is
        #                      what has to match.
        #   mode Audio         the avatar-and-subtitles call. Video needs a
        #                      holocall PREFAB to render the caller to a texture
        #                      (q104 names one: prefabNodeRef #holocalls_studio),
        #                      and we have no such prefab - see D124.
        #   showAvatar 0       what all six vanilla instances ship, including the
        #                      ones that visibly show a portrait in game. The
        #                      portrait comes from the contact's avatarID.
        #
        # applyPhoneRestriction reads backwards from its name: phoneSystem's
        # TriggerCall only touches the restriction when it is 1, and on the
        # EndCall branch it calls ApplyPhoneCallRestriction(FALSE). So 1 on
        # EndCall means "release the phone", and vanilla ships exactly that -
        # 0 on StartCall, 1 on EndCall. Defaulted from the phase for that reason;
        # override only with vanilla in hand.
        phase = check_enum(spec.get("phase", "StartCall"), questPhoneCallPhase,
                           f"{where} phone call phase")
        return {"$type": "questPhoneManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questCallContact_NodeType",
                           "caller": journal_path("gameJournalContact", spec["caller"]),
                           "addressee": journal_path("gameJournalContact",
                                                     spec["addressee"]),
                           "phase": phase,
                           "mode": check_enum(spec.get("mode", "Audio"),
                                              questPhoneCallMode,
                                              f"{where} phone call mode"),
                           "prefabNodeRef": noderef(spec.get("prefab", "")),
                           "applyPhoneRestriction": 1 if spec.get(
                               "release", phase == "EndCall") else 0,
                           "isRejectable": 1 if spec.get("rejectable") else 0,
                           "showAvatar": 1 if spec.get("showAvatar") else 0,
                           "visuals": check_enum(spec.get("visuals", "Default"),
                                                 questPhoneCallVisuals,
                                                 f"{where} phone call visuals")})}
    if t == "set_fact":
        return {"$type": "questFactsDBManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questSetVar_NodeType",
                           "factName": spec["fact"],
                           "setExactValue": 1,
                           "value": spec.get("value", 1)})}
    if t in ("pause_fact", "pause"):
        cond = spec["condition"] if t == "pause" else {
            "fact": spec["fact"], "value": spec.get("value", 1),
            "compare": spec.get("compare", "Equal")}
        return {"$type": "questPauseConditionNodeDefinition", "id": nid,
                "condition": build_condition(cond, where)}
    if t == "condition":
        return {"$type": "questConditionNodeDefinition", "id": nid,
                "condition": build_condition(spec["condition"], where)}
    if t == "scene":
        return {"$type": "questSceneNodeDefinition", "id": nid,
                "interruptionOperations": [],
                "notAllowedToBeFrozen": 0,
                "reapplyInterruptionOperationsAfterGameLoad": 0,
                "sceneFile": {"DepotPath": {"$type": "ResourcePath", "$storage": "string",
                                            "$value": spec["file"]},
                              "Flags": "Soft"},
                # Where in the world the scene plays. The scene itself holds no
                # position; this marker is its origin, and every actor and camera
                # inside is placed relative to it.
                #
                # D124 - 'anchor' switches that origin from a fixed marker to a
                # TAG, and the only tag worth having is 'around_player': the
                # scene plays wherever V is standing. That is how vanilla anchors
                # a phone call, and the evidence is unusually clean - of the 15
                # scene nodes in q112_03_infiltration exactly one uses type Tag,
                # and it is the one called q112_01b_market_phonecall. A call
                # pinned to a NodeRef would be a call that stops working as soon
                # as the player drives away from it. Vanilla fills BOTH fields
                # and lets 'type' pick, so the marker below stays populated.
                "sceneLocation": {"$type": "scnWorldMarker",
                                  "nodeRef": {"$type": "NodeRef", "$storage": "string",
                                              "$value": spec["location"]},
                                  "tag": cname(spec.get("anchor", "None")),
                                  "type": "Tag" if spec.get("anchor") else "NodeRef"},
                "syncToMusic": 0}
    if t == "add_item":
        return {"$type": "questItemManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questAddRemoveItem_NodeType",
                           "params": [add_remove_item(spec)]})}
    if t == "inject_loot":
        return {"$type": "questItemManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questInjectLoot_NodeType",
                           "params": [inject_loot(spec, where)]})}
    if t == "spawn":
        acts = spec.get("actions")
        if not isinstance(acts, list) or not acts:
            sys.exit(f"{where}: a spawn node needs a non-empty 'actions' list")
        return {"$type": "questSpawnManagerNodeDefinition", "id": nid,
                "actions": [spawn_action(a, where) for a in acts]}
    if t == "device_action":
        # A quest forcing a device into a state - here, opening a vanilla door.
        # Shape measured off ep1_mq304_airdrops (ForceDetonate on six tanks);
        # Hot Fuzz ships ForceUnlock on a vanilla door through the same node.
        # Both CNames are resolved at runtime (the controller class by name, the
        # action through its GetQuestActionByName switch), so a typo is silent:
        # the node completes and nothing happens. Hence the door check below.
        ctrl, act = spec.get("controller"), spec.get("action")
        if ctrl == "DoorControllerPS" and act not in DOOR_QUEST_ACTIONS:
            sys.exit(f"{where}: DoorControllerPS has no quest action {act!r} - "
                     f"one of {sorted(DOOR_QUEST_ACTIONS)}")
        if not ctrl or not act:
            sys.exit(f"{where}: a device_action node needs 'controller' and 'action'")
        return {"$type": "questInteractiveObjectManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questDeviceManager_NodeType",
                           "params": [H({"$type": "questDeviceManager_NodeTypeParams",
                                         "actionProperties": [],
                                         "deviceAction": cname(act),
                                         "deviceControllerClass": cname(ctrl),
                                         "entityRef": _entity_ref(),
                                         "objectRef": _node_ref(spec["device"], where),
                                         "slotName": cname("None")})]})}
    if t == "remove_item":
        # The same node and the same params block as add_item - only the enum
        # differs (questEAddRemoveItemType: AddItem 0, RemoveByItemID 1,
        # RemoveByTag 2, RemoveAll 3). No reference quest removes an item, so
        # the remove side is attested by the RTTI-generated struct rather than
        # by a shipped instance; every other field keeps the value three vanilla
        # AddItem nodes agree on, isPlayer 0 and refLocalPlayer 1 included.
        # D120 uses it on the endings: an object the player is told they burned,
        # sold or spent must not still be in the backpack afterwards.
        return {"$type": "questItemManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questAddRemoveItem_NodeType",
                           "params": [add_remove_item(spec, "RemoveByItemID")]})}
    if t == "play_fx":
        # A particle/screen effect, started or stopped on one entity. Field
        # shape read off two shipped instances: q005_07_vip_apartment.scene
        # drives #q005_dvc_konpeki_floor_safe's hacking light through three of
        # these (play 1 then play 0), and Undermine's template.scene plays
        # 'fast_travel_glitch' ON THE PLAYER - isPlayer 1 with the nodeRef left
        # as the uint64 0, which is how the player is addressed here (the
        # opposite convention to add_item, where isPlayer is 0 and a
        # questUniversalRef carries refLocalPlayer).
        #
        # effectName is a CName resolved against the TARGET ENTITY's own effect
        # list, so a name that entity does not define is silent - nothing plays,
        # the node still completes. Only names seen on that entity in shipped
        # content are used here.
        on_player = bool(spec.get("player"))
        if not on_player and "target" not in spec:
            sys.exit(f"{where}: a play_fx node needs 'player': true or a 'target' node ref")
        ref = (_entity_ref() if on_player
               else _entity_ref_to(spec["target"], where))
        return {"$type": "questFXManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questPlayFX_NodeType",
                           # NOT H(): questPlayFX_NodeTypeParams is a plain
                           # struct, where questAddRemoveItem_NodeTypeParams
                           # derives from ISerializable and so is a handle. Both
                           # shipped instances write it inline, and WolvenKit
                           # refuses the file outright if it is wrapped.
                           "params": [({"$type": "questPlayFX_NodeTypeParams",
                                         "effectInstanceName": cname("None"),
                                         "effectName": cname(spec["effect"]),
                                         "isPlayer": 1 if on_player else 0,
                                         "objectRef": ref,
                                         "play": 0 if spec.get("stop") else 1,
                                         "save": 0,
                                         "sequenceShift": 0})]})}
    if t == "show_world_node":
        # Hide or show one world node by NodeRef. Shape copied off Hot Fuzz's
        # hide/show pair on #q003_dildo_token: isPlayer 0, componentName None.
        # Used for static presentation states (e.g. the Cynosure elevator's
        # CYN_ELEV_GATE / CYN_ELEV_LANDING_DOOR), which cannot animate.
        if not isinstance(spec.get("show"), bool):
            sys.exit(f"{where}: a show_world_node node needs 'show': true or false")
        return {"$type": "questWorldDataManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questShowWorldNode_NodeType",
                           "componentName": cname("None"),
                           "isPlayer": 0,
                           "objectRef": _node_ref(spec.get("node"), where),
                           "show": 1 if spec["show"] else 0})}
    if t == "progress_bar":
        # The engine's own download bar - the one the Konpeki suite shows while
        # the Relic copies. Shape taken field for field off the single vanilla
        # use, q005_07_vip_apartment.scene: top text, bottom text, a duration in
        # seconds, show=1, type "Undefined". Both texts are LocKey references, so
        # they come out of the reserved block like every other string here.
        #
        # 'type' is hardcoded rather than enum-checked because "Undefined" is the
        # only value the game ships on this node (1 of 1) - inventing the rest of
        # the enum from the name would be guessing at an engine API (rule 8).
        #
        # The node does NOT block: it starts the bar and completes. Whatever
        # should take 'duration' to happen has to be held open by something else
        # - in ash_cache_terminal.scene that is an eventless section of the same
        # length. Wire it without one and the bar animates over a quest that has
        # already moved on.
        return {"$type": "questUIManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questProgressBar_NodeType",
                           "bottomText": lockey_ref(spec["bottom"], where),
                           "duration": float(spec["duration"]),
                           "show": 1,
                           "text": lockey_ref(spec["text"], where),
                           "type": "Undefined"})}
    if t == "warning_message":
        # Big centre-screen text. Vanilla's two uses are both the Konpeki scan
        # ("WARNING: UNAUTHORIZED SCANNING"), which is exactly this register:
        # a machine talking over the HUD, no journal entry, no item.
        #
        # 'message' is the untranslated debug string vanilla keeps beside the
        # LocKey; it is what shows up in logs, so it carries the en-us text.
        return {"$type": "questUIManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questWarningMessage_NodeType",
                           "duration": float(spec.get("duration", 3.5)),
                           "instant": 1 if spec.get("instant") else 0,
                           "localizedMessage": lockey_ref(spec["text"], where),
                           "message": spec.get("debug", ""),
                           "show": 1,
                           "type": "Undefined"})}
    if t == "and":
        n = spec.get("count", 2)
        return {"$type": "questLogicalAndNodeDefinition", "id": nid,
                "inputSocketCount": n, "outputSocketCount": 1}
    if t == "set_tier":
        return {"$type": "questSceneManagerNodeDefinition", "id": nid,
                "type": H(set_tier(spec, where))}
    if t == "prefab_phase":
        # THE mechanism for loading a Quest-category streaming sector. Those
        # sectors are not proximity-streamed - their descriptor in
        # all.streamingblock carries a questPrefabNodeRef and a streamingBox of
        # +/-FLT_MAX, which is distance streaming switched off, not an infinite
        # radius. What loads them is an ACTIVE PHASE that names the prefab.
        # Verified in vanilla two ways: questQuestPhaseResource.phasePrefabs on
        # q305_06_outer_bunker (#q305_pr_outer_bunker) and q305_07_inner_bunker
        # (#q305_pr_inner_bunker), and the per-node form used here,
        # questPhaseNodeDefinition.phaseInstancePrefabs, on q305_07 node 128.
        # The per-node form is the one worth copying: the resource-level list is
        # owned for as long as the whole phase runs, and this mod's phase is
        # attached to the root quest graph, so that would mean "for the entire
        # game".
        prefabs = spec.get("prefabs") or []
        if not prefabs:
            sys.exit(f"{where}: prefab_phase with no 'prefabs' holds nothing open")
        return {"$type": "questPhaseNodeDefinition", "id": nid,
                "phaseGraph": H(hold_graph(spec, where)),
                "phaseInstancePrefabs": [
                    {"$type": "questQuestPrefabEntry",
                     "prefabNodeRef": _node_ref(p, where)} for p in prefabs],
                # Empty path = the graph is inline, not a separate resource.
                "phaseResource": {"DepotPath": {"$type": "ResourcePath",
                                                "$storage": "uint64", "$value": "0"},
                                  "Flags": "Soft"},
                "saveLock": 0,
                "unfreezingTriggerNodeRef": {"$type": "NodeRef",
                                             "$storage": "uint64", "$value": "0"}}
    if t == "set_mortality":
        return {"$type": "questCharacterManagerNodeDefinition", "id": nid,
                "type": H({"$type": "questCharacterManagerParameters_NodeType",
                           "subtype": H(set_mortality(spec, where))})}
    if t == "shoot_at":
        return shoot_at(spec, nid, where)
    if t == "teleport":
        return teleport(spec, nid, where)
    sys.exit(f"unknown node type {t!r} for {where}")


def teleport(spec, nid, where):
    """questTeleportPuppetNodeDefinition - move V to a world marker (D193).

    Copied field for field from vanilla: all 24 teleport nodes in the extracted
    reference quests (mq304, q003, q112_03) agree on healAtTeleport 1, doNavTest 0,
    useFastTravelMechanism 0, lookAtAction Reset and the same questPlayerLookAtParams,
    so none of that is exposed. The puppet is always the local player.

    'destination' is a marker of our own; the Ash Cache sectors are AlwaysLoaded,
    so it resolves from anywhere in the world. 'offset' exists because vanilla has
    it, and should stay [0, 0, 0]: a dedicated marker at the landing point says
    where V goes, and an offset hides it (and its rotation semantics are unverified).
    """
    if "destination" not in spec:
        sys.exit(f"{where}: a teleport node needs 'destination', a marker NodeRef like '#ac_cyn_entry_tp'")
    off = spec.get("offset", [0, 0, 0])
    if (not isinstance(off, list) or len(off) != 3
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in off)):
        sys.exit(f"{where}: teleport 'offset' must be three numbers, got {off!r}")
    player = H({"$type": "questUniversalRef", "entityReference": _entity_ref(),
                "mainPlayerObject": 1, "refLocalPlayer": 1})
    dest = H({"$type": "questUniversalRef",
              "entityReference": _entity_ref_to(spec["destination"], where),
              "mainPlayerObject": 0, "refLocalPlayer": 0})
    return {"$type": "questTeleportPuppetNodeDefinition", "id": nid,
            "entityReference": player,
            "lookAtAction": "Reset",
            "params": H({"$type": "questTeleportPuppetParamsV1",
                         "destinationOffset": {"$type": "Vector3", "X": off[0], "Y": off[1], "Z": off[2]},
                         "destinationRef": dest,
                         "doNavTest": 0, "healAtTeleport": 1, "useFastTravelMechanism": 0}),
            "playerLookAt": H({"$type": "questPlayerLookAtParams",
                               "adjustPitch": 1, "adjustYaw": 1,
                               "cameraInputMagToBreak": 0.200000003, "duration": 0.25,
                               "easeIn": 1, "easeOut": 1, "endOnCameraInputApplied": 1,
                               "endOnTargetReached": 1, "endOnTimeExceeded": 1,
                               "lookAtTarget": _entity_ref(), "maxDuration": 2,
                               "offset": {"$type": "Vector3", "X": 0, "Y": 0, "Z": 0},
                               "precision": 0.100000001, "slotName": cname("None"),
                               "useOffsetToPlayer": 1})}


def shoot_at(spec, nid, where):
    """questCombatNodeDefinition / questCombatNodeParams_ShootAt - send an NPC at V.

    The payload is AIInjectCombatThreatCommandParams, copied field for field from
    ep1_mq304_airdrops (17 of its 19 combat nodes): the target is pushed into the
    NPC's threat list, persistently, so it enters combat and hunts it down.

    D111 first used questCombatNodeParams_CombatTarget (q304_transmitter_tower_04
    node 20). In game that crew spawned and stood still (D112): CombatTarget only
    retargets an NPC that is ALREADY fighting, and an agent on the street has no
    perception of V inside the clinic. 'entry' names one member of a community; a
    spawner has no members, so it is left empty.
    """
    for key in ("attacker", "target"):
        if key not in spec:
            sys.exit(f"{where}: a shoot_at node needs '{key}', a NodeRef like '#player'")
    return {"$type": "questCombatNodeDefinition", "id": nid,
            "entityReference": _entity_ref_to(spec["attacker"], where, spec.get("entry")),
            "function": cname("questCombatNodeParams_ShootAt"),
            "params": H({"$type": "AIInjectCombatThreatCommandParams",
                         "dontForceHostileAttitude": 0,
                         "duration": spec.get("duration", 0),
                         "isPersistent": 1,
                         "targetNodeRef": {"$type": "NodeRef", "$storage": "uint64", "$value": "0"},
                         "targetPuppetRef": _entity_ref_to(spec["target"], where)})}


def set_tier(spec, where):
    """questSetTier_NodeType - what the player may do while a scene is playing.

    Measured across all 7,825 vanilla .scene files: 985 set a tier, and of the 781
    that name one, Tier2_StagedGameplay is 545, Tier3_LimitedGameplay 215,
    Tier4_FPPCinematic 87, Tier5_Cinematic 54. The ladder is not a dimmer switch -
    each step swaps the player onto a different locomotion state machine
    (LocomotionTier3/4/5), except Tier2, which keeps ordinary locomotion and only
    caps speed with a stat modifier. So Tier2 means "walk slowly", and standing
    still starts at Tier3.

    Tier4 and Tier5 hand the camera to an authored cinematic camera. This project
    animates no cameras, so asking for either would surrender the view to
    something that was never built.

    'Tier1_FullGameplay' never appears in any of those 7,825 string tables even
    though scenes plainly restore to it - CR2W omits a field sitting at its
    declared default. Do not read a zero from a string scan as "never authored"
    without checking what the default is.
    """
    tier = check_enum(spec.get("tier", "Tier1_FullGameplay"), GameplayTier,
                      f"{where} tier")
    return {"$type": "questSetTier_NodeType",
            # Holsters the player's weapon and refuses to let it be drawn. Present
            # in 189 of the 985 tier-setting scenes; the string only enters the
            # table when some node sets it to 1, so that is a floor, not a total.
            "forceEmptyHands": 1 if spec.get("emptyHands") else 0,
            "motionConstrainedTierDataParams": {
                "$type": "gameMotionConstrainedTierDataParams",
                "adjustingDuration": 0, "adjustingSpeed": 0,
                "notificationBackwardIndex": 0,
                "splineRef": {"$type": "NodeRef", "$storage": "uint64", "$value": "0"},
                "travellingDuration": 0, "travellingSpeed": 0},
            "tier": tier,
            # All three are 0 in every vanilla instance read for this: the enter
            # and exit animations and the player workspot are for scenes that put
            # V into an authored pose, which this one does not.
            "useEnterAnim": 0, "useExitAnim": 0, "usePlayerWorkspot": 0}


def set_mortality(spec, where):
    """questCharacterManagerParameters_SetMortality - who is allowed to die.

    Worked example, q001_00cd_boss_clean.scene, on the Scavenger boss:

        graph[32] isPlayer=0 state=Immortal source=q001_jackie_terminado
                  ref=#q001_scavengers_boss
        graph[40] isPlayer=0 state=Mortal   source=q001_jackie_terminado

    'source' is a NAMED CLAIM on that character's mortality, and the on and off
    use the same string, so two systems can each hold one without clobbering the
    other. Give every claim its own name.

    Of 7,825 vanilla scenes, 211 set mortality and all 211 also name Mortal - the
    protection is normally released. Not naming a release is therefore a
    deliberate act, and the caller has to say so.

    Note 'Invulnerable' appears in exactly ONE of those 7,825 files: vanilla's
    verb for this is Immortal, which takes damage but cannot be reduced past
    surviving. Invulnerable refuses damage outright.

    isPlayer is NOT the same flag it is on questAddRemoveItem (D12), where the
    player is isPlayer 0 plus refLocalPlayer 1. Here the player is isPlayer 1 with
    a NodeRef of '#player'. The flag is per node type; do not carry it across.
    """
    if "character" not in spec:
        sys.exit(f"{where}: a set_mortality node needs 'character', a NodeRef like "
                 f"'#ac_mara'")
    src = spec.get("source")
    if not isinstance(src, str) or not src:
        sys.exit(f"{where}: a set_mortality node needs a 'source' naming the claim, so "
                 f"that releasing it cannot release somebody else's")
    return {"$type": "questCharacterManagerParameters_SetMortality",
            "isPlayer": 0,
            "puppetRef": _entity_ref_to(spec["character"], where),
            "resetToDefault": 1 if spec.get("resetToDefault") else 0,
            "source": cname(src),
            "state": check_enum(spec.get("state", "Mortal"), gameGodModeType,
                                f"{where} mortality state")}


def spawn_action(a, where):
    """One entry of a questSpawnManagerNodeDefinition.

    Two shapes, and which one you need is decided by the world node, not here:
    a worldPopulationSpawnerNode takes questSpawner_NodeType, a community takes
    questCommunityTemplate_NodeType. 140 of the 178 vanilla spawn nodes carry a
    single action; the rest carry up to eight, which is why 'actions' is a list.
    """
    action = check_enum(a.get("action", "Activate"), populationSpawnerObjectCtrlAction,
                        f"{where} spawn action")
    if "spawner" in a:
        inner = H({"$type": "questSpawner_NodeType", "action": action,
                   "spawnerReference": _node_ref(a["spawner"], where)})
    elif "community" in a:
        inner = H({"$type": "questCommunityTemplate_NodeType", "action": action,
                   "communityEntryName": cname(a.get("entry", "None")),
                   "communityEntryPhaseName": cname(a.get("phase", "None")),
                   "spawnerReference": _node_ref(a["community"], where)})
    else:
        sys.exit(f"{where}: spawn action needs a 'spawner' or a 'community': {a!r}")
    return {"$type": "questSpawnManagerNodeActionEntry", "type": inner}


def endpoint(ref, default_side, sockets, by_id, link):
    """'node' or 'node:Socket'. Returns (node id, socket name or None)."""
    name, _, s = ref.partition(":")
    if name not in by_id:
        sys.exit(f"link {link} references unknown node {name!r}")
    return name, (s or None)


def build_phase(g):
    """graph dict -> the questQuestPhaseResource root chunk."""
    # Annotation-only entries have no id; a node may still carry a "_comment" field.
    specs = [n for n in g["nodes"] if n.get("id")]

    by_id = {}
    for n in specs:
        if n["id"] in by_id:
            sys.exit(f"duplicate node id {n['id']!r}")
        by_id[n["id"]] = n

    # Allocate sockets per node up front so links can wire into them by name.
    sockets = {}
    for n in specs:
        s = {"CutDestination": sock("CutDestination", "CutDestination")}
        for name in inputs_of(n):
            s[name] = sock(name, "Input")
        for name in outputs_of(n):
            s[name] = sock(name, "Output")
        sockets[n["id"]] = s

    def pick(node, socket, side, link):
        """Resolve a named-or-default socket on one end of a link."""
        avail = inputs_of(by_id[node]) if side == "in" else outputs_of(by_id[node])
        if socket is None:
            if len(avail) != 1:
                sys.exit(f"link {link}: node {node!r} has {side} sockets {avail} - "
                         f"name one explicitly")
            socket = avail[0]
        if socket not in avail:
            sys.exit(f"link {link}: node {node!r} has no {side} socket {socket!r} "
                     f"(has {avail})")
        return sockets[node][socket]

    # Wire the links. One connection object, referenced from BOTH endpoints.
    for link in g["links"]:
        src, src_sock = endpoint(link[0], "out", sockets, by_id, link)
        dst, dst_sock = endpoint(link[1], "in", sockets, by_id, link)
        if len(link) > 2:
            if dst_sock:
                sys.exit(f"link {link}: input socket named twice")
            dst_sock = link[2]
        out_s = pick(src, src_sock, "out", link)
        in_s = pick(dst, dst_sock, "in", link)
        conn = S({"$type": "graphGraphConnectionDefinition", "destination": in_s, "source": out_s})
        out_s.obj["connections"].append(conn)
        in_s.obj["connections"].append(conn)

    # Nothing downstream of an unreachable node ever runs, and nothing upstream of a
    # dead end can complete the quest; both are silent at runtime, so flag them here.
    reached = {n["id"] for n in specs if n["type"] == "input"}
    adj = {}
    for link in g["links"]:
        adj.setdefault(link[0].partition(":")[0], []).append(link[1].partition(":")[0])
    stack = list(reached)
    while stack:
        for nxt in adj.get(stack.pop(), []):
            if nxt not in reached:
                reached.add(nxt)
                stack.append(nxt)
    orphans = [n["id"] for n in specs if n["id"] not in reached]
    if orphans:
        sys.exit(f"unreachable from any input node: {orphans}")

    nodes = []
    for i, n in enumerate(specs):
        data = build_node_data(n, i)
        s = sockets[n["id"]]
        data["sockets"] = [s[k] for k in
                           ["CutDestination"] + inputs_of(n) + outputs_of(n)]
        nodes.append(H(data))

    return {
        "$type": "questQuestPhaseResource",
        "cookingPlatform": "PLATFORM_PC",
        "graph": H({"$type": "questGraphDefinition", "nodes": nodes}),
        "inplacePhases": [],
        "phasePrefabs": [],
    }


# Each entry is one injected phase resource: source graph -> built file. They are
# separate resources on purpose. ArchiveXL attaches a phase to the root quest
# graph, so a phase runs from the moment the game starts until its output node
# fires - and ash_cache's output node fires when the quest ends. Anything that has
# to outlive the quest, like holding a world prefab streamed, cannot live in that
# graph: it would be cut the moment the player finishes. See source/cynosure_graph
# .json for the one thing that needs to.
PHASES = [
    ("quest_graph.json",    "ash_cache.questphase.json"),
    ("cynosure_graph.json", "ash_cache_cynosure.questphase.json"),
]


def main():
    for src, dst in PHASES:
        path = ROOT / "source" / src
        if not path.exists():
            continue
        g = json.loads(path.read_text(encoding="utf-8"))
        root = build_phase(g)
        out = ROOT / "build" / dst
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(envelope(root, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}  "
              f"({len(root['graph'].obj['nodes'])} nodes, {len(g['links'])} links)")


if __name__ == "__main__":
    main()
