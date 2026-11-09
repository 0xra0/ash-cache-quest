#!/usr/bin/env python3
"""Cross-check the source files against each other before anything is built.

Catches the failure modes that are silent at runtime: a graph waiting on a fact
nobody ever sets, a journal path the graph points at that the journal does not
define, a string with no LocKey, a map pin aimed at a world marker that does not
exist.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(n):
    return json.loads((ROOT / "source" / n).read_text(encoding="utf-8"))


def declared_facts(facts):
    out = set()
    for group, body in facts.items():
        if group.startswith("_") or group == "ending_gates":
            continue
        out |= {k for k in body if not k.startswith("_")}
    return out


def journal_paths(j):
    """Every addressable journal path, and separately the SMS thread roots.

    The thread roots come back on their own because they are the one kind of path
    the graph is not expected to activate - a thread appears when its messages
    arrive, so the root is never named by a node. Everything else that no node
    activates is dead UI and gets reported.
    """
    root = "quests/main_quest/prologue"
    q = j["quest"]["id"]
    paths = {f"{root}/{q}"}
    for ph in j["phases"]:
        for o in ph["objectives"]:
            paths.add(f"{root}/{q}/{ph['id']}/{o['id']}")
            # An objective with a 'summary' gets a gameJournalQuestDescription
            # child at the literal id "description" (gen_journal.quest_description).
            # It is addressable, and it HAS to be addressed: QuestLogUtils
            # .UnpackRecursiveWithFilter skips any entry whose own state is
            # Inactive, exempting only JournalQuestMapPinBase - so a description
            # nothing activates is never returned by GetDescriptions and the
            # journal's description panel renders empty. Nothing warns. Adding the
            # path here is what makes an unactivated one show up as dead UI.
            if o.get("summary"):
                paths.add(f"{root}/{q}/{ph['id']}/{o['id']}/description")
    thread_roots = set()
    for conv in j.get("phoneConversations", []):
        # A thread lives at contacts/<contact>/<thread>/<message> - four segments,
        # because the CONTACT is a real entry in between, not part of the folder
        # name. It owns the avatar and the sender name, which is why it exists at
        # all (OI-2, D22). Getting this depth wrong costs nothing at build time and
        # everything at run time: the path still parses, the graph node still
        # loads, and the message simply never arrives.
        c = conv.get("contact")
        if not isinstance(c, dict) or "id" not in c:
            sys.exit(f"journal.json thread {conv['id']!r} has no contact block; every "
                     f"thread needs one, and it is what carries the avatar and the "
                     f"name the phone shows")
        base = f"contacts/{c['id']}"
        paths.add(base)
        thread_roots.add(base)
        thread_roots.add(f"{base}/{conv['id']}")
        paths.add(f"{base}/{conv['id']}")
        for m in conv["messages"]:
            paths.add(f"{base}/{conv['id']}/{m['id']}")
    return paths, thread_roots



def graph_stage_window(graph, stage):
    """Every node reachable while ashcache_progress == stage.

    Walk forward from the node that sets progress to `stage` and stop at the node
    that sets it to anything else. What comes back is the act, as the engine will
    actually run it.
    """
    outs = {}
    for link in graph["links"]:
        # Strip the output socket. A link out of a condition is written
        # "route_wound:True", so keying on the raw string filed those edges under
        # a name no walk ever pops, and the walk stopped dead at the first
        # condition node - which for act 7 meant a window of exactly one node.
        # It never showed because the only two watches that existed sat in acts
        # with no branch between the progress node and the pause. D122 put one
        # behind five conditions and the check fired on a correct graph.
        outs.setdefault(link[0].split(":", 1)[0], []).append(link[1])
    by_id = {n["id"]: n for n in graph["nodes"] if n.get("id")}

    def sets_progress(nid):
        n = by_id.get(nid, {})
        return n.get("type") == "set_fact" and n.get("fact") == "ashcache_progress"

    start = [nid for nid in by_id if sets_progress(nid)
             and by_id[nid].get("value") == stage]
    seen, frontier = set(), list(start)
    while frontier:
        nid = frontier.pop()
        for nxt in outs.get(nid, []):
            if nxt in seen or sets_progress(nxt):
                continue
            seen.add(nxt)
            frontier.append(nxt)
    return seen


def check_glue(glue, facts, world, items, graph, known_facts, errors):
    """source/glue.json against the graph, the world and the item list.

    The glue layer is the only place in this mod where a mistake is invisible in
    every artifact and only shows up as a quest that stops advancing, so the
    checks here are all about the joins between it and everything else.
    """
    markers = {m["id"] for s in world["sectors"] for m in s.get("markers", [])}
    shard_ids = {i["id"] for i in items["items"] if i["kind"] == "shard"}
    external = declared_facts({"w": facts.get("world_triggers", {}),
                               "d": facts.get("discoveries", {}),
                               # facts.json "debug": test facts set by hand from the CET console
                               "x": facts.get("debug", {})})

    prereq = glue["start"]["prerequisite"]
    if prereq.startswith("ashcache_"):
        errors.append(f"glue.json start prerequisite {prereq!r} is one of ours - it has "
                      f"to be a vanilla fact, or the quest gates itself on itself")

    set_by_glue = {glue["start"]["fact"]}
    for a in glue["areas"]:
        set_by_glue.add(a["fact"])
        if a["marker"] not in markers:
            errors.append(f"glue.json area {a['fact']!r} triggers on marker "
                          f"{a['marker']!r}, which world.json does not define")
        # The act the watch is armed in has to be the act the graph waits in.
        # Get this wrong and the fact is set during an act that does not care,
        # or never set at all - and the only symptom is a quest that stops.
        window = graph_stage_window(graph, a["stage"])
        waiting = {n["id"] for n in graph["nodes"]
                   if n.get("type") == "pause_fact" and n.get("fact") == a["fact"]}
        if not waiting:
            errors.append(f"glue.json sets {a['fact']!r} but no graph node waits on it")
        elif not (waiting & window):
            errors.append(f"glue.json arms {a['fact']!r} during ashcache_progress == "
                          f"{a['stage']}, but the graph waits on it outside that act - "
                          f"the trigger would fire in the wrong place or never")

    for s in glue["shards"]:
        set_by_glue.add(s["fact"])
        if s["item"] not in shard_ids:
            errors.append(f"glue.json shard hook {s['fact']!r} reads item {s['item']!r}, "
                          f"which items.json does not define as a shard")

    blocked = {k for k in glue["blocked"] if not k.startswith("_")}
    for f in sorted(set_by_glue | blocked):
        if f not in known_facts:
            errors.append(f"glue.json names fact {f!r} that facts.json does not declare")
        elif f not in external:
            errors.append(f"glue.json sets {f!r}, but facts.json does not list it under "
                          f"world_triggers or discoveries - the graph should own it")
    if set_by_glue & blocked:
        errors.append(f"glue.json both sets and blocks: "
                      f"{', '.join(sorted(set_by_glue & blocked))}")
    return set_by_glue, blocked


WORLD_KINDS = {"marker": "markers", "trigger": "triggers",
               "spawner": "spawners", "prop": "props",
               "mesh": "meshes", "collision": "collisions"}


def placement_tally(world):
    """'6 marker(s), 1 trigger(s)' - only the kinds actually present.

    The summary line is the only place a reader sees what shipped, so a kind that
    appears for the first time has to show up here rather than be folded into a
    single node count.
    """
    counts = {}
    for sec in world["sectors"]:
        for kind, key in WORLD_KINDS.items():
            n = len(sec.get(key, []))
            if n:
                counts[kind] = counts.get(kind, 0) + n
    order = list(WORLD_KINDS)
    return ", ".join(f"{counts[k]} {k}(s)" for k in order if k in counts) or "no world nodes"


def check_placement(kind, mid, m, errors, is_probe=False):
    """The fields one kind of world node needs and the others do not.

    Every one of these is silent in game if it is wrong. A trigger with no size
    collapses to a unit box nobody can walk into; a spawner with no record builds
    nothing; a prop with no template is an entity node pointing at the null path,
    which streams in as nothing at all and reports nothing anywhere.
    """
    if kind == "trigger":
        size = m.get("size")
        if not (isinstance(size, list) and len(size) == 3
                and all(isinstance(v, (int, float)) and v > 0 for v in size)):
            errors.append(f"trigger {mid!r} needs a 'size' of three positive numbers "
                          f"- the half-extent in metres")
        if not isinstance(m.get("height", 2.0), (int, float)):
            errors.append(f"trigger {mid!r} has a non-numeric 'height'")
    elif kind == "spawner":
        if m.get("spawnOnStart") and not is_probe:
            errors.append(f"spawner {mid!r} sets 'spawnOnStart' outside a probe sector - "
                          f"the object would be standing there before the quest begins. "
                          f"Quest content is inert until a graph node activates it; every "
                          f"vanilla quest spawner ships spawnOnStart 0")
        rec = m.get("record")
        if not isinstance(rec, str) or "." not in rec:
            errors.append(f"spawner {mid!r} needs a 'record' TweakDB id like "
                          f"'Vehicle.hackable_thorton_galena'")
    elif kind == "prop":
        tmpl = m.get("template")
        if not isinstance(tmpl, str) or not tmpl.endswith(".ent"):
            errors.append(f"prop {mid!r} needs a 'template' depot path ending '.ent'")
        elif "/" in tmpl:
            errors.append(f"prop {mid!r} template {tmpl!r} uses forward slashes - "
                          f"depot paths are backslash-separated")
        if not isinstance(m.get("zOffset", 0.0), (int, float)):
            errors.append(f"prop {mid!r} has a non-numeric 'zOffset' - it is the\n"
                          f"metres the ENTITY sits above the floor point in 'pos'")
    elif kind == "mesh":
        path = m.get("mesh")
        if not isinstance(path, str) or not path.endswith(".mesh"):
            errors.append(f"mesh {mid!r} needs a 'mesh' depot path ending '.mesh'")
        elif "/" in path:
            errors.append(f"mesh {mid!r} path {path!r} uses forward slashes - "
                          f"depot paths are backslash-separated")
        scale = m.get("scale", [1.0, 1.0, 1.0])
        if not (isinstance(scale, list) and len(scale) == 3
                and all(isinstance(v, (int, float)) and v > 0 for v in scale)):
            errors.append(f"mesh {mid!r} has a 'scale' that is not three positive numbers")
        if not isinstance(m.get("autohide", 1.0), (int, float)):
            errors.append(f"mesh {mid!r} has a non-numeric 'autohide' - it is the metres "
                          f"beyond which the mesh stops drawing")
    elif kind == "collision":
        boxes = m.get("boxes")
        if not (isinstance(boxes, list) and boxes):
            errors.append(f"collision {mid!r} needs at least one entry in 'boxes' - "
                          f"a collision node with no shapes is an invisible nothing")
            return
        for i, b in enumerate(boxes):
            half = b.get("half")
            if not (isinstance(half, list) and len(half) == 3
                    and all(isinstance(v, (int, float)) and v > 0 for v in half)):
                errors.append(f"collision {mid!r} box {i} needs a 'half' of three positive "
                              f"numbers - HALF extents in metres, so a 3 m x 4 m panel is "
                              f"[1.5, thickness/2, 2.0]")
            off = b.get("offset", [0.0, 0.0, 0.0])
            if not (isinstance(off, list) and len(off) == 3
                    and all(isinstance(v, (int, float)) for v in off)):
                errors.append(f"collision {mid!r} box {i} has an 'offset' that is not "
                              f"three numbers")


def check_graph_sockets(graph, errors):
    """Every link names a socket its endpoint actually has.

    D127. This check exists because "validation OK" and "the build works" were
    two different claims and nobody noticed they had come apart. D126 left three
    links naming sockets that did not exist - a condition entered on 'Active',
    which had belonged to the journal node it replaced, and two journal nodes
    entered on nothing when they offer four inputs. gen_questphase sys.exits on
    all three, so the questphase simply never rebuilt; build.sh is set -e and
    failed honestly, but validate.py kept printing OK and the archive kept the
    LAST good phase. The feature was absent from the deploy for a day with every
    tool reporting success.

    The socket names come from gen_questphase itself rather than a copy, so a
    node type that grows a socket cannot make the two disagree.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import gen_questphase as gq

    by_id = {n["id"]: n for n in graph["nodes"] if n.get("id")}
    for link in graph["links"]:
        src, _, src_sock = link[0].partition(":")
        dst, _, dst_named = link[1].partition(":")
        dst_sock = link[2] if len(link) > 2 else (dst_named or None)
        if len(link) > 2 and dst_named:
            errors.append(f"graph link {link}: input socket named twice")
        for node, sock, side, avail in (
                (src, src_sock or None, "output",
                 gq.outputs_of(by_id[src]) if src in by_id else None),
                (dst, dst_sock, "input",
                 gq.inputs_of(by_id[dst]) if dst in by_id else None)):
            if avail is None:
                errors.append(f"graph link {link}: no node {node!r}")
                continue
            if sock is None:
                if len(avail) != 1:
                    errors.append(f"graph link {link}: node {node!r} has {len(avail)} "
                                  f"{side} sockets {avail} - name one explicitly")
            elif sock not in avail:
                errors.append(f"graph link {link}: node {node!r} has no {side} socket "
                              f"{sock!r} (has {avail})")


def check_scene_tier(scenes, graph, errors):
    """A scene that takes control away has to be able to give it back.

    Raising the gameplay tier is how a conversation stops the player walking off
    and holsters their weapon. The engine has no notion of a player who abandons
    a dialogue - scene interruption is pause/resume only, with no abandon path -
    so if the player is interrupted out of a raised-tier scene and nothing lowers
    it again, they are left unable to move and nothing anywhere reports it.

    The guard is the scene node's 'Default INT' and 'Default RET' outputs. Across
    the shipped game only 13 of 128 interruption-aware phases wire them, and every
    one of the 15 wired paths is the same four nodes: a 500 ms realtime delay into
    questSetTier Tier1_FullGameplay. The 115 that skip it are the ones that never
    change tier, so the rule is not "always wire it" - it is exactly this:

        raise the tier in a scene  =>  wire that scene's INT and RET

    Two halves, because each fails on its own: a raise with no restore inside the
    scene strands a player who finishes it normally, and a raise with no INT/RET
    strands one who gets interrupted. See reference/interruption.md and D28.
    """
    raises, restores = {}, set()
    for key, sc in scenes.items():
        for n in sc.get("nodes", []):
            spec = n.get("node") or {}
            if spec.get("type") != "set_tier":
                continue
            if spec.get("tier", "Tier1_FullGameplay") == "Tier1_FullGameplay":
                restores.add(key)
            else:
                raises.setdefault(key, []).append(n["id"])

    for key in sorted(raises):
        if key not in restores:
            errors.append(f"scene {key!r} raises the gameplay tier at "
                          f"{', '.join(raises[key])} and never sets it back to "
                          f"Tier1_FullGameplay - the player finishes the conversation "
                          f"unable to move, and nothing reports it")

    wired = {}
    for link in graph["links"]:
        src = link[0]
        if ":" in src:
            node, sock = src.split(":", 1)
            wired.setdefault(node, set()).add(sock)

    for n in graph["nodes"]:
        if n.get("type") != "scene":
            continue
        stem = n["file"].replace("\\", "/").rsplit("/", 1)[-1]
        key = stem[len("ash_cache_"):-len(".scene")]
        if key not in raises:
            continue
        have = wired.get(n["id"], set())
        for sock in ("Default INT", "Default RET"):
            if sock not in have:
                errors.append(f"graph node {n['id']!r} plays scene {key!r}, which raises "
                              f"the gameplay tier, but its {sock!r} output is not wired. "
                              f"A player interrupted out of it is left unable to move. "
                              f"Wire it to a 500ms pause into a set_tier "
                              f"Tier1_FullGameplay node, as all 15 vanilla INT paths do")


def check_verified(world, graph, chars, errors):
    """Which world positions have actually been stood on, and which are guesses.

    Three of this project's ten positions were arrived at by offsetting a known
    one, and in game all three were wrong: the black box was inside solid rock
    (its capture screenshot is an all-black frame), motel room 7 was in an
    underground parking garage, and the car probe was never reachable. Every
    position that was stood on was right. That is the whole record, and it is
    lopsided enough to be worth enforcing.

    What this CANNOT do is prove a position is safe - the walls are not in any
    data we hold, and the old black-box guess sat 4.8m from a verified point and
    was still buried. So it does not pretend to. It makes 'never stood on'
    countable, and it refuses the two places where being wrong is both silent and
    unrecoverable: a scene origin (the scene plays at the world origin instead)
    and a character spawn (the actor arrives inside whatever is there).
    """
    verified, unverified = set(), set()
    for sec in world["sectors"]:
        for key in WORLD_KINDS.values():
            for m in sec.get(key, []):
                mid = m.get("id")
                if not mid:
                    continue
                if "verified" not in m:
                    errors.append(f"world node {mid!r} has no 'verified' flag - say whether "
                                  f"this position was stood on in game (true) or derived "
                                  f"from one that was (false)")
                    continue
                (verified if m["verified"] else unverified).add(mid)

    prefix = world["nodeRefPrefix"]
    for n in graph["nodes"]:
        if n.get("type") != "scene":
            continue
        mid = n.get("location", "")[len(prefix) + 2:]
        if mid in unverified:
            errors.append(f"graph node {n['id']!r} anchors its scene at '#{mid}', whose "
                          f"position has never been stood on. A scene origin that is inside "
                          f"geometry does not error - it plays, wrong, wherever it lands. "
                          f"Stand on it and capture it before shipping the scene")

    for c in chars["characters"]:
        # A voice never arrives anywhere (D126), so there is no position for it to
        # arrive inside. check_characters() is where the marker's absence is
        # allowed; this is the other place that assumed every character had one.
        if c.get("voice"):
            continue
        mid = c["marker"].lstrip("#")
        if mid in unverified:
            errors.append(f"character {c['id']!r} spawns at '#{mid}', whose position has "
                          f"never been stood on - she would arrive inside whatever is there, "
                          f"silently")

    return sorted(verified), sorted(unverified)


def graph_node_refs(graph, prefix):
    """Every world node the GRAPH names, and which node named it.

    The graph reaches into the world in two shapes and both are silent when
    wrong. A short '#ac_thing' is what questInteraction / questDevice /
    questSpawner take; a condition aimed at a name that does not exist never
    becomes true, so the quest simply stops with no error anywhere. A scene's
    'location' is the long prefixed form and lands the scene at the world
    origin instead. Walk for both rather than listing key names, so a node type
    added later is covered without anyone remembering to come back here.
    """
    out = {}

    def walk(o, owner):
        if isinstance(o, dict):
            owner = o.get("id", owner)
            for k, v in o.items():
                # '_comment' may quote a NodeRef while discussing it; a mention
                # in prose is not a use, and counting it would mask a marker
                # that nothing actually points at.
                if not k.startswith("_"):
                    walk(v, owner)
        elif isinstance(o, list):
            for v in o:
                walk(v, owner)
        elif isinstance(o, str):
            m = re.fullmatch(r"#(ac_[a-z0-9_]+)", o)
            if not m and o.startswith(prefix + "/#"):
                m = re.fullmatch(r"(ac_[a-z0-9_]+)", o[len(prefix) + 2:])
            if m:
                out.setdefault(m.group(1), set()).add(f"graph node {owner!r}")

    walk(graph.get("nodes", []), "?")
    return out


def check_world(world, ref_txt, graph, errors):
    """world.json against everything that references a NodeRef.

    All of these are silent in game. A map pin whose NodeRef resolves to nothing
    renders no pin and reports no error; a scene anchored to a missing marker
    plays at the world origin rather than failing. So the only place they can be
    caught is here.
    """

    defined, positions, placed = {}, {}, {}
    sector_ids = set()
    for sec in world["sectors"]:
        sid = sec["id"]
        if sid in sector_ids:
            errors.append(f"world.json defines sector {sid!r} twice")
        sector_ids.add(sid)
        if not sid.startswith("ash_cache_"):
            errors.append(f"sector {sid!r} must be prefixed 'ash_cache_' (rule 5)")
        # Every kind shares one NodeRef namespace and one set of coordinates, so
        # the duplicate-id and same-point checks have to see all four together. A
        # prop sharing a name with a marker is the nastier version of the bug the
        # marker check was written for: the map pin and the object both resolve,
        # to whichever node the engine happened to index last.
        for kind, key in WORLD_KINDS.items():
            for m in sec.get(key, []):
                mid = m["id"]
                if mid in placed:
                    other, okind = placed[mid]
                    errors.append(f"{kind} {mid!r} is also defined as a {okind} in "
                                  f"{other!r} - two nodes would claim the same NodeRef")
                placed[mid] = (sid, kind)
                # Every kind, not just markers. All four share one NodeRef
                # namespace - the comment above says so - and the graph addresses
                # three of them: 'interaction' and 'device' conditions and
                # inject_loot take a prop, 'spawned'/'killed' take a spawner, a
                # trigger condition takes a trigger. While this said 'marker'
                # only, wiring a condition to a prop that really exists failed
                # here as if the prop had been misspelt.
                defined[mid] = sid
                if not mid.startswith("ac_"):
                    errors.append(f"{kind} {mid!r} must be prefixed 'ac_' (rule 5)")
                pos = m.get("pos")
                if not (isinstance(pos, list) and len(pos) == 3
                        and all(isinstance(v, (int, float)) for v in pos)):
                    errors.append(f"{kind} {mid!r} needs a 'pos' of exactly three numbers")
                    continue
                # Per KIND, not globally. Two markers at one point is a
                # copy-paste; a trigger centred on a marker, or a prop standing
                # where a marker points, is how these are meant to be used.
                pkey = (kind,) + tuple(round(float(v), 2) for v in pos)
                if pkey in positions:
                    # Deliberate collapse is a real move: when no interior point
                    # has ever been stood on, pinning the door is honest and a
                    # guessed offset is not. It has to be DECLARED, so that the
                    # one case that is intentional cannot quietly cover for the
                    # copy-paste this check exists to catch.
                    onto = m.get("collapsedOnto")
                    if onto != positions[pkey] and positions[pkey] != mid:
                        if onto is not None:
                            errors.append(f"{kind} {mid!r} declares collapsedOnto {onto!r} but "
                                          f"actually sits on {positions[pkey]!r}")
                        else:
                            errors.append(f"{kind}s {positions[pkey]!r} and {mid!r} sit at the "
                                          f"same point {pkey[1:]} - one of them is a "
                                          f"copy-paste. If it is deliberate, say so with "
                                          f"\"collapsedOnto\": \"{positions[pkey]}\"")
                positions[pkey] = mid
                if not isinstance(m.get("yaw", 0.0), (int, float)):
                    errors.append(f"{kind} {mid!r} has a non-numeric 'yaw'")
                check_placement(kind, mid, m, errors, bool(sec.get("probe")))

    # A Quest-category sector's questPrefab is a NodeRef too (D133): it is what a
    # prefab_phase node names, and the sector descriptor is what defines it.
    for sec in world["sectors"]:
        if sec.get("questPrefab") and not sec.get("disabled"):
            if sec.get("category") != "Quest":
                errors.append(f"sector {sec['id']!r} has a questPrefab but category "
                              f"{sec.get('category', 'AlwaysLoaded')!r} - only a Quest "
                              f"sector is streamed by a phase")
            defined[sec["questPrefab"]] = sec["id"]
    deferred = {k for k in world.get("deferred", {}) if not k.startswith("_")}
    for d in sorted(deferred & set(defined)):
        errors.append(f"{d!r} is listed as deferred but world.json also defines it - "
                      f"delete the deferred entry")

    # Every '#ac_*' anyone asks for must be defined here or explicitly deferred.
    # Explicit deferral is what lets 'not built yet' coexist with a hard failure
    # on a typo, instead of having to choose between blocking the build and
    # letting a misspelt NodeRef ship silently.
    wanted = {}
    for name, text in ref_txt.items():
        for ref in re.findall(r"#(ac_[a-z0-9_]+)", text):
            wanted.setdefault(ref, set()).add(name)
    for ref, owners in graph_node_refs(graph, world["nodeRefPrefix"]).items():
        wanted.setdefault(ref, set()).update(owners)
    for ref in sorted(wanted):
        if ref in defined or ref in deferred:
            continue
        who = sorted(wanted[ref])
        # Both are silent, but they are silent in different ways and the fix
        # differs, so say which one this is.
        why = ("the condition would never become true and the quest would stop there"
               if all(w.startswith("graph node") for w in who)
               else "the map pin would point at nothing")
        errors.append(f"{', '.join(who)} references NodeRef '#{ref}' that no world node "
                      f"defines - {why}. Add it to world.json, or list it under "
                      f"'deferred' if it is intentionally later")
    probes = {s["id"] for s in world["sectors"] if s.get("probe")}
    # A prop placed only to be SEEN (D102: the Relic case, whose Use prompt is a
    # scene hub, not the entity). Exempt only with a written reason - a bare
    # true would let a misspelt NodeRef hide behind it.
    scenery = {p["id"] for s in world["sectors"] for p in s.get("props", [])
               if isinstance(p.get("scenery"), str) and p["scenery"].strip()}
    # Geometry is anonymous BY CONSTRUCTION, not by exemption: gen_sector writes
    # QuestPrefabRefHash 0 for a mesh or a collision box and leaves it out of the
    # sector's nodeRefs entirely, exactly as vanilla does. There is no NodeRef for
    # anything to reference, so "nothing references it" is the correct state
    # rather than a symptom, and requiring a written reason per wall would be
    # noise on the one kind of node that is never addressed by name.
    geometry = {m["id"] for s in world["sectors"]
                for key in ("meshes", "collisions") for m in s.get(key, [])
                if m.get("id")}
    for mid in sorted(set(defined) - set(wanted)):
        if defined[mid] in probes or mid in scenery or mid in geometry:
            continue
        errors.append(f"world node {mid!r} is defined but nothing references it - "
                      f"either it is dead weight or a NodeRef elsewhere is misspelt")
    for d in sorted(deferred - set(wanted)):
        errors.append(f"{d!r} is listed as deferred but nothing references it - stale entry")

    # A scene's sceneLocation uses the LONG NodeRef form; check it names a real
    # marker rather than only looking well-formed.
    prefix = world["nodeRefPrefix"]
    for n in graph["nodes"]:
        if n.get("type") != "scene":
            continue
        loc = n.get("location", "")
        if not loc.startswith(prefix + "/#"):
            errors.append(f"graph node {n['id']!r} anchors its scene at {loc!r}, which is not "
                          f"under world.json's nodeRefPrefix {prefix!r}")
            continue
        mid = loc[len(prefix) + 2:]
        if mid not in defined:
            errors.append(f"graph node {n['id']!r} anchors its scene at marker '#{mid}', "
                          f"which world.json does not define - the scene would play at the "
                          f"world origin")
    return defined, deferred


def check_cast(chars, scenes, defined, deferred, strings, errors):
    """source/characters.json against the world it stands in and the scripts that
    cast it.

    Every failure here is silent in game, and each is silent differently: a record
    whose marker does not exist spawns the NPC at the world origin, a line naming an
    actor the scene never cast plays with no speaker and no nameplate, and a display
    name with no string behind it renders as a raw key over her head.
    """
    by_id, records = {}, {}
    for c in chars["characters"]:
        cid = c["id"]
        if cid in by_id:
            errors.append(f"characters.json defines character {cid!r} twice")
        by_id[cid] = c

        rec = c["record"]
        if not rec.startswith("ashcache_"):
            errors.append(f"character record {rec!r} must be prefixed 'ashcache_' (rule 5)")
        if rec in records:
            errors.append(f"characters {records[rec]!r} and {cid!r} share the TweakDB record "
                          f"{rec!r} - one $base would silently overwrite the other")
        records[rec] = cid

        # A voice has no body (D126, characters.json "_voices"): gen_scene.py builds
        # it with voice_actor_def(), which never reads a marker because there is no
        # entity to place. Demanding one would mean inventing a spot in the world
        # for somebody who is on the far end of a phone. The cast check below is
        # what keeps this honest - a voice cast in a scene that is not a holocall
        # goes back through actor_def(), which WOULD want the marker.
        if c.get("voice"):
            if "marker" in c:
                errors.append(f"character {cid!r} is a voice and also carries a marker "
                              f"{c['marker']!r} - nothing spawns, so the marker is a claim "
                              f"about a body that does not exist. Drop one of the two")
        else:
            ref = c.get("marker", "")
            if not ref.startswith("#"):
                errors.append(f"character {cid!r} marker {ref!r} must be a NodeRef starting '#'")
            elif ref[1:] in deferred:
                errors.append(f"character {cid!r} spawns at {ref!r}, which world.json only "
                              f"defers - she would spawn at the world origin. Build the "
                              f"marker, or take her out of the scene's cast until it exists")
            elif ref[1:] not in defined:
                errors.append(f"character {cid!r} spawns at {ref!r}, which no marker defines "
                              f"- she would spawn at the world origin")

        for key in ("displayName", "fullDisplayName"):
            if key in c and c[key] not in strings:
                errors.append(f"character {cid!r} {key} names string {c[key]!r}, which "
                              f"strings.json does not define")

    # A speaker has to be someone the scene actually cast, or the line is voiced by
    # nobody - which the format permits, so nothing would complain in game.
    cast_anywhere = set()
    for name, sc in scenes.items():
        names = {chars["player"]["actorName"]}
        for cid in sc.get("actors", []):
            if cid not in by_id:
                errors.append(f"scene_{name}.json casts {cid!r}, which characters.json "
                              f"does not define")
                continue
            cast_anywhere.add(cid)
            # The other half of the voice rule above. A voice is allowed to have no
            # marker only because every scene that casts it goes through
            # voice_actor_def(), which never asks for one. Any scene that is NOT a
            # holocall goes through actor_def() instead, which would spawn a body -
            # at the world origin, since there is no marker to read. Caught here
            # rather than at the KeyError, because the KeyError names a dict key and
            # this names the mistake.
            if by_id[cid].get("voice") and not sc.get("scene", {}).get("holocall"):
                errors.append(f"scene_{name}.json casts {cid!r}, which characters.json "
                              f"marks as a voice, but the scene is not a holocall - the "
                              f"voice would be spawned as a body, and it has no marker "
                              f"to spawn at. Set scene.holocall, or give {cid!r} a body")
            an = by_id[cid]["actorName"]
            if an in names:
                errors.append(f"scene_{name}.json casts two actors both called {an!r} - "
                              f"a line naming that actor would be ambiguous")
            names.add(an)

        for node in sc["nodes"]:
            uses = [("attachTo", node)] if "attachTo" in node else []
            for item in node.get("lines", []) + node.get("options", []):
                uses += [(k, item) for k in ("actor", "to") if k in item]
            for key, item in uses:
                if item[key] not in names:
                    errors.append(f"scene_{name}.json {item.get('id', node['id'])!r} names "
                                  f"actor {item[key]!r} on {key!r}, which this scene does not "
                                  f"cast (has {sorted(names)}) - it would play with no speaker "
                                  f"and no nameplate")

    for cid in sorted(set(by_id) - cast_anywhere):
        errors.append(f"character {cid!r} is defined but no scene casts them - either dead "
                      f"weight, or a scene's 'actors' list is misspelt")
    return by_id


# Item ids a graph node moves that items.json does NOT define: vanilla records
# this mod borrows rather than ships. Filled by check_items, verified against the
# game's name dump by check_tweakdb - which is the only place that can tell the
# difference between borrowing Items.money and misspelling it.
VANILLA_ITEMS = {}


def check_items(items, graph, strings, errors):
    """source/items.json against the graph that grants the items and the strings
    that name them.

    Everything here is silent in game. An item the graph never grants simply never
    appears; a grant naming an item nobody defines adds nothing to the inventory
    and reports no error; a shard whose onscreen strings are missing opens a reader
    with an empty page.
    """
    known = {}
    for it in items["items"]:
        iid, rec = it["id"], it.get("record", "")
        if iid in known:
            errors.append(f"items.json defines {iid!r} twice")
        if not rec.startswith("ashcache_"):
            errors.append(f"items.json {iid!r} has record {rec!r}, which breaks the "
                          f"rule 5 'ashcache_' prefix")
        if it.get("kind") not in ("item", "shard"):
            errors.append(f"items.json {iid!r} has kind {it.get('kind')!r}; "
                          f"it must be 'item' or 'shard'")
        if it.get("kind") == "item" and not it.get("base"):
            errors.append(f"items.json {iid!r} is kind 'item' and names no 'base' "
                          f"to inherit from")
        for key in ("displayName", "description"):
            sid = it.get(key)
            if sid not in strings:
                errors.append(f"items.json {iid!r} {key} is {sid!r}, which "
                              f"strings.json does not define")
        if it.get("kind") == "shard":
            o = it.get("onscreen") or {}
            for key in ("group", "entry"):
                if not o.get(key):
                    errors.append(f"items.json {iid!r} is a shard with no "
                                  f"onscreen.{key} - its Read action would point "
                                  f"at a journal path that does not exist")
            for key in ("title", "body"):
                if o.get(key) not in strings:
                    errors.append(f"items.json {iid!r} onscreen.{key} is "
                                  f"{o.get(key)!r}, which strings.json does not "
                                  f"define - the shard would open an empty reader")
        # D186: an item a script hands out (the Last Word is a loot drop, not a
        # graph grant) names that script; it must actually mention the record.
        if it.get("granted_by"):
            gb = ROOT / it["granted_by"]
            if not gb.exists() or f"Items.{rec}" not in gb.read_text(encoding="utf-8"):
                errors.append(f"items.json {iid!r} granted_by {it['granted_by']!r}, "
                              f"which does not mention Items.{rec}")
            continue
        known[iid] = rec

    by_record = {}
    for iid, rec in known.items():
        by_record.setdefault(rec, []).append(iid)
    for rec, who in sorted(by_record.items()):
        if len(who) > 1:
            errors.append(f"items.json {sorted(who)} all claim record {rec!r}")

    # Two node types put an item into the world, and both have to be counted.
    # add_item hands it straight to the player; inject_loot puts it inside a
    # container the player then opens. Counting only the first would report a
    # shard that ships inside the black box as "nothing grants it" - a failure
    # for a build that is correct - and would let a typo'd item id inside a
    # loot node through unchecked, which is the same bug pointing the other way.
    granted = set()
    for n in graph["nodes"]:
        if n.get("type") == "add_item":
            wants = [(n.get("item", ""), "grants")]
        elif n.get("type") == "remove_item":
            # D120: removing takes an item id exactly like granting one, and a
            # typo here is the quietest failure of the three - the node completes,
            # the object stays in the backpack, and the ending that just said it
            # was burned is contradicted by the inventory screen.
            wants = [(n.get("item", ""), "removes")]
        elif n.get("type") == "inject_loot":
            wants = [(it.get("item", ""), "injects")
                     for it in n.get("items") or []]
        else:
            continue
        for want, verb in wants:
            if want not in set(known.values()):
                if want.startswith("ashcache_"):
                    # Ours by rule 5, and items.json has never heard of it: a
                    # typo, or a record nobody wrote. This stays a hard error
                    # here rather than degrading to the TweakDB check below,
                    # because that check is allowed to go quiet when the game's
                    # name dump is missing and this must not.
                    errors.append(f"graph node {n['id']!r} {verb} item {want!r}, "
                                  f"which items.json does not define (has "
                                  f"{sorted(set(known.values()))})")
                else:
                    # Not ours, so it has to be one of the game's. D120 pays the
                    # Blue Eyes ending in Items.money - the currency is a real
                    # record and nothing this mod could define would stand in for
                    # it. check_tweakdb verifies the id against the game's own
                    # name dump; what would be wrong is inventing one here.
                    VANILLA_ITEMS[f"Items.{want}"] = f"graph node {n['id']!r} ({verb})"
            if verb != "removes":
                granted.add(want)
    # An item nothing grants can never reach the player - it is a record that
    # ships and does nothing.
    for iid, rec in sorted(known.items()):
        if rec not in granted:
            errors.append(f"items.json defines {iid!r} but no graph node grants it")
    return known


# A dump of every string in the game's TweakDB, one per line. Not part of this
# project and not guaranteed to be here, so every check that uses it degrades to a
# printed note rather than a failure - a missing dump means "unverified", which is
# where this project was before it, not "broken".
TWEAKDB = pathlib.Path("/mnt/sata/Cyberpunk2077/everything/cp2077-tweakdb/tweakdbstr.txt")


def check_tweakdb(chars, journal, items, world, errors):
    """Every vanilla TweakDB record this mod leans on, against the real TweakDB.

    Rule 8 says do not invent engine APIs, and a record id is the easiest kind to
    invent by accident: `Character.q306_fia_agent_corpo_scene_wa` is unguessable,
    and a wrong one is silent. Mara would spawn as nothing at all, or the journal
    entry would carry a district that does not exist - which is not hypothetical,
    Undermine ships `District.Watson` and the real record is `Districts.Watson`.
    It works anyway, so the engine tolerates it; that is exactly why nothing but a
    check like this would ever tell you.

    Two directions are checked, because they fail differently:

      MUST EXIST    anything inherited or referenced. A typo means no record.
      MUST NOT      anything this mod defines. A collision means the mod silently
                    overwrites a vanilla record instead of adding one.
    """
    need, forbid = {}, {}
    for c in chars["characters"]:
        need[c["base"]] = f"characters.json {c['id']}.base"
        forbid[f"Character.{c['record']}"] = f"characters.json {c['id']}.record"
        for name, alt in (c.get("_alternatives") or {}).items():
            if isinstance(alt, dict) and "base" in alt:
                need[alt["base"]] = f"characters.json {c['id']} _alternatives.{name}"
    for e in chars.get("enemies", []):
        if not e["record"].startswith("ashcache_"):
            errors.append(f"enemy record {e['record']!r} must be prefixed 'ashcache_' (rule 5)")
        need[e["base"]] = f"characters.json enemies.{e['id']}.base"
        forbid[f"Character.{e['record']}"] = f"characters.json enemies.{e['id']}.record"
    need[chars["player"]["record"]] = "characters.json player.record"
    for it in items["items"]:
        forbid[f"Items.{it['record']}"] = f"items.json {it['id']}.record"
        if it.get("base"):
            need[it["base"]] = f"items.json {it['id']}.base"
        if it.get("kind") == "shard":
            # gen_tweak.py inherits both of these; a rename in the game would make
            # the shard inherit nothing and lose its Readable type outright.
            need["Items.mq006_body_shard"] = "gen_tweak.py SHARD_BASE"
            need["Items.mq006_body_shard_inline0"] = "gen_tweak.py SHARD_ACTION_BASE"
    for key in ("districtID", "recommendedLevelID"):
        if journal["quest"].get(key):
            need[journal["quest"][key]] = f"journal.json quest.{key}"

    # The phone avatar. This is the portrait the messages arrive under, and it is
    # the one field on a contact that has any art behind it - a wrong id gets the
    # blank silhouette, which is indistinguishable from having set nothing at all.
    for conv in journal.get("phoneConversations", []):
        av = conv["contact"].get("avatar")
        if av:
            need[av] = f"journal.json {conv['contact']['id']}.avatar"
    # Written by tools/gen_tweak.py into every generated record.
    need["UINameplate.Always"] = "gen_tweak.py nameplate"
    # Vanilla items the graph moves - see VANILLA_ITEMS. check_items runs first
    # (main calls it one line above this one), so the register is already full.
    need.update(VANILLA_ITEMS)
    # A spawner asks the record system for its object by id. A wrong one builds
    # nothing and says nothing, exactly like a wrong .ent path.
    for sec in world["sectors"]:
        for sp in sec.get("spawners", []):
            # .get, not [], because a spawner with no record at all is already
            # reported by check_placement and this must not crash ahead of it -
            # a validator that dies mid-run reports whatever it reached, not what
            # is wrong.
            # A record this mod defines is checked the other way round (forbid), so
            # it only has to be one characters.json actually generates.
            if sp.get("record") in forbid:
                continue
            if sp.get("record"):
                need[sp["record"]] = f"world.json {sp['id']}.record"

    if not TWEAKDB.exists():
        print(f"note: {TWEAKDB} not found - {len(need)} TweakDB record(s) unverified")
        return 0

    want = set(need) | set(forbid)
    found = set()
    with TWEAKDB.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            name = line.rstrip("\n")
            if name in want:
                found.add(name)

    for name, where in sorted(need.items()):
        if name not in found:
            errors.append(f"{where} names TweakDB record {name!r}, which the game "
                          f"does not have - check the spelling against "
                          f"{TWEAKDB.name}")
    for name, where in sorted(forbid.items()):
        if name in found:
            errors.append(f"{where} defines TweakDB record {name!r}, but the game "
                          f"already has one by that name - this mod would overwrite "
                          f"it rather than add to it (rule 5 exists to stop this)")
    return len(want)


# Every depot path in the game's archives, one per line, the resource-side twin of
# TWEAKDB above. Built with
#
#     WolvenKit.CLI archive "<game>/archive/pc/content" "<game>/archive/pc/ep1" -l
#
# then sorted -u: 544,497 paths, 47 MB. Same degradation rule as TWEAKDB - if it is
# not here the check prints a note and passes, because "unverified" is where this
# project was before it existed, not "broken".
DEPOT = pathlib.Path("/mnt/sata/Cyberpunk2077/depot_files.txt")


# The nine gameJournalQuestType members QuestsListController.GetDisplayedCategory
# actually names. The enum has ten. Read out of the game's own scripts; the atlas
# part each one ends up drawing is in reference/examples/journal_icons.json.
DRAWABLE_QUEST_TYPES = {
    "MainQuest", "SideQuest", "MinorQuest", "CourierSideQuest", "StreetStory",
    "CyberPsycho", "Contract", "ApartmentQuest", "CourierQuest",
}


DISTRICT_ICONS = ROOT / "reference" / "district_icons.txt"


def check_district_icon(journal, errors):
    """The tracked-quest widget builds its icon id by STRING CONCATENATION:

        QuestItemController.SetQuestData, last line:
          RequestSetImage(this, m_QuestIcon, "UIIcon." + ToString(GetDistrict()))

    so the icon record must be named for the gamedataDistrict ENUM, and the enum
    name is not the record name. `Districts.Akebono.enumName` is "Dogtown_Akebono";
    105 of the game's 132 district records differ from their enum that way, so
    deriving the icon id from the record name is wrong for four fifths of them.
    The mapping is read out of TweakDB values into reference/district_icons.txt.

    Of the 132, twelve have no UIIcon at all. Those are real districts that pass
    every other check and still draw the placeholder, so this is the only place
    that can say no.
    """
    d = journal["quest"].get("districtID", "")
    if not d:
        # Legal and common - 16 of the 55 vanilla ep1 quests ship with no district.
        return 0
    if not DISTRICT_ICONS.exists():
        print(f"note: {DISTRICT_ICONS} not found - district icon unverified")
        return 0
    table = {}
    for line in DISTRICT_ICONS.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        rec, enum, has = line.split("\t")
        table[rec] = (enum, has)
    if d not in table:
        errors.append(f"journal.json quest.districtID {d!r} is not a district record "
                      f"in reference/district_icons.txt")
        return 0
    enum, has = table[d]
    if has != "icon":
        errors.append(
            f"journal.json quest.districtID {d!r} is a real district whose enum is "
            f"{enum!r}, but there is no UIIcon.{enum} - the tracked-quest widget "
            f"builds its icon id as \"UIIcon.\" + enum, so this draws the generic "
            f"placeholder. See reference/examples/journal_icons.json.")
        return 0
    return 1


def check_journal_icon(journal, errors):
    """The journal list icon is derived from `type`, through two switches that
    both fall through silently.

        SimpleQuestListItemController -> QuestTypeIconUtils.GetIcon(questType)
        QuestsListController.GetDisplayedCategory(gameJournalQuest.type)

    GetDisplayedCategory names nine of the enum's ten members. The tenth,
    VehicleQuest, falls through to QuestListItemType.Invalid, and GetIcon's own
    fallthrough then returns the atlas part "invalid" - the generic (!) glyph.

    Nothing catches that anywhere else. The value is a legal enum member, so
    check_enum in gen_journal.py accepts it, it serializes cleanly, the journal
    entry works, and the only symptom is a broken-looking icon in the list. This
    is the check that says so.
    """
    t = journal["quest"].get("type", "SideQuest")
    if t not in DRAWABLE_QUEST_TYPES:
        errors.append(
            f"journal.json quest.type is {t!r}, which the journal list cannot draw: "
            f"GetDisplayedCategory does not name it, so the icon falls through to "
            f"the generic (!). Use one of {', '.join(sorted(DRAWABLE_QUEST_TYPES))}.")
        return 0
    return 1


def check_depot(world, errors):
    """Every vanilla resource this mod points at, against the game's real archives.

    A worldEntityNode whose entityTemplate does not resolve streams in as nothing.
    No log line, no missing-asset placeholder, no error - the sector loads and the
    object is simply absent, which is indistinguishable from "the coordinates are
    wrong" and from "instanceData cannot be null". Three different conclusions from
    one silent symptom is exactly the situation this check exists to prevent.

    Paths under mod\\ are ours and are not in the game's archives; build.sh is what
    proves those, by failing to pack a file it cannot find.
    """
    need = {}
    for sec in world["sectors"]:
        for p in sec.get("props", []):
            tmpl = p.get("template")
            if isinstance(tmpl, str) and not tmpl.lower().startswith("mod\\"):
                need.setdefault(tmpl, []).append(f"world.json {p['id']}.template")
        # A mesh path that does not resolve fails the same silent way an entity
        # template does - the sector loads and there is simply nothing there -
        # except that a wall nobody can see is still a wall the player walks
        # into, so the two halves of a piece of geometry disagree instead of
        # both being absent. Worth catching here rather than in game.
        for m in sec.get("meshes", []):
            path = m.get("mesh")
            if isinstance(path, str) and not path.lower().startswith("mod\\"):
                need.setdefault(path, []).append(f"world.json {m['id']}.mesh")
    if not need:
        return 0
    if not DEPOT.exists():
        print(f"note: {DEPOT} not found - {len(need)} depot path(s) unverified")
        return 0
    want = set(need)
    found = set()
    with DEPOT.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            name = line.rstrip("\n")
            if name in want:
                found.add(name)
    for name in sorted(want - found):
        errors.append(f"{', '.join(need[name])} points at {name!r}, which is not in "
                      f"the game's archives - the entity would stream in as nothing "
                      f"at all, silently. Check it against {DEPOT.name}")
    return len(want)


# Two proper nouns that differ by a single letter are almost always one name
# spelled two ways. Pairs that are genuinely both real go here and stop being
# reported; keep the reason on the line, because an entry here silences a check
# forever.
NAME_TWINS = {
    # Ukrainian declines its nouns, so one name legitimately has several forms,
    # and two of them can land a single letter apart. "Агенція вважає" is
    # nominative and "кур'єр Агенції" is genitive - both required, and writing
    # one of them in the other's case to satisfy this check would be writing bad
    # Ukrainian to keep a tool quiet (rule 7). D119.
    #
    # This is the shape every future entry here will have. The check stays strict
    # for everything else on purpose: it exists to catch Ґ-for-Г and Восс-for-Ворс
    # typos, which look exactly like a case ending and are not one.
    frozenset(("Агенція", "Агенції")),
}

# English contracts the pronoun "I" into words that are capitalised in the middle
# of a sentence and so look exactly like names to PROPER_NOUN below. They are not
# names, and treating them as a NAME_TWINS exception instead would be recording a
# false pair as if both halves were real people: "I'm"/"I'd" is one letter apart
# and fires, "I'll"/"I've" is two and does not, so the check's silence on the
# second pair would have been luck rather than correctness. D121 - the first line
# in the project to put "I'm" anywhere but the start of a sentence.
PRONOUN_I = {"I'd", "I'm", "I'll", "I've", "I’d", "I’m", "I’ll", "I’ve"}

# A capitalised word that is NOT the first word of its sentence. The exclusion is
# the whole trick: "Burn it", "Then start talking", "Say it to my face" are
# grammar, not names, and pairing sentence-openers against each other was 11 of
# the 12 hits the first draft produced. Ukrainian capitals need Ґ Є І Ї spelled
# out - they sit outside the А-Я block, and Ґ vs Г is exactly the kind of typo
# this is here to catch.
PROPER_NOUN = re.compile(r"(?<=[^.!?\n\"'\u2014\u2013\s])[\s,;:(\u2014\u2013-]+"
                         r"([A-ZА-ЯҐЄІЇ][\w'\u2019\u02bc]{2,})")


# Every gameJournalCodex* path in the shipped game, one per line as
# "<className>\t<path>", built from base/journal/cooked_journal.journal and
# ep1/journal/cooked_journal.journal:
#
#     WolvenKit.CLI convert serialize cooked_journal.journal -o .
#
# then walked recursively, joining each level's `id`. 1013 paths, 55 KB, small
# enough to live in the repo rather than be rebuilt. Same degradation rule as
# TWEAKDB and DEPOT - a missing file notes and passes.
CODEX = ROOT / "reference" / "codex_paths.txt"


def check_codex(journal, errors):
    """Every codex path this mod links, against the game's real journal tree.

    A gameJournalQuestCodexLink whose realPath resolves to nothing is a valid
    string pointing at nobody. The link entry loads, the objective loads, the
    journal renders - and the icon is simply absent, with no log line. The
    failure has no symptom other than the feature not being there.

    That is not hypothetical twice over. Vanilla's own paths are misspelt
    (`locations/distrcts`, `cyanosure`), so the spelling cannot be reasoned
    about and has to be looked up; and this mod shipped
    `ep1/codex/quest/locations/cyanosure` when the real path is
    `ep1/codex/locations/quest/cyanosure` - the segments the wrong way round,
    written after verifying only that the famously-misspelt leaf was right.

    The class is checked too, not just the path. gameJournalPath carries a
    className, and every level of the codex tree (Category, Group, Entry,
    Description) is a different class at a valid path - so a link that names the
    right string at the wrong level fails exactly the same silent way.
    """
    links = journal.get("codexLinks") or []
    if not links:
        return 0
    if not CODEX.exists():
        print(f"note: {CODEX} not present - codex paths unverified")
        return 0
    known = {}
    for line in CODEX.read_text(encoding="utf-8").splitlines():
        if "\t" not in line:
            continue
        cls, path = line.split("\t", 1)
        known[path] = cls
    want = "gameJournalCodexEntry"
    for spec in links:
        path = spec.get("path", "")
        cls = known.get(path)
        if cls is None:
            near = [p for p in known if p.rsplit("/", 1)[-1] == path.rsplit("/", 1)[-1]]
            hint = f" - did you mean {near[0]!r}?" if len(near) == 1 else ""
            errors.append(f"journal.json {spec['id']}.path is {path!r}, which is not "
                          f"a codex entry in the game's journal{hint}")
        elif cls != want:
            errors.append(f"journal.json {spec['id']}.path is {path!r}, which is a "
                          f"{cls} - a quest codex link has to point at a {want}")
    return len(links)


def check_proper_nouns(errors):
    """One character, one spelling, in every locale.

    The clinic's antagonist shipped as 'Hale' in seven spoken lines and 'Gale' in
    the journal shard - and as Гейл against Ґейла in ua-ua, which is the same slip
    made twice. Nothing downstream can catch that: both spellings are valid text,
    both localise, both build. The player just meets two men.

    Only SAME-LENGTH single-substitution pairs are compared. An inserted or
    deleted letter is how Slavic case endings work - Гейл/Гейла, Мара/Мари/Марою
    are one word inflected, not two names - so counting those would bury the
    signal under correct grammar.
    """
    seen = {}
    for path in sorted((ROOT / "source").glob("*.json")):
        def walk(o, key=None):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, k)
            elif isinstance(o, list):
                for v in o:
                    walk(v, key)
            elif isinstance(o, str) and key in ("en-us", "ua-ua"):
                for m in PROPER_NOUN.finditer(o):
                    # "Hale's" and "Hale" are the same name; the apostrophe-s is
                    # English possessive grammar riding along on the noun.
                    word = re.sub(r"['\u2019\u02bc]s$", "", m.group(1))
                    if word in PRONOUN_I:
                        continue
                    seen.setdefault(word, set()).add(f"{path.name} ({key})")
        walk(json.loads(path.read_text(encoding="utf-8")))

    names = sorted(seen)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if len(a) != len(b) or frozenset((a, b)) in NAME_TWINS:
                continue
            if sum(x != y for x, y in zip(a, b)) != 1:
                continue
            errors.append(f"proper noun {a!r} ({', '.join(sorted(seen[a]))}) and {b!r} "
                          f"({', '.join(sorted(seen[b]))}) differ by one letter - one "
                          f"name spelled two ways reads as two characters. Fix the "
                          f"spelling, or add the pair to NAME_TWINS if both are real")
    return len(seen)


def check_voiceover(errors):
    """Every way a dropped audio file can be packed and still make no sound.

    vo/<locale>/ is a drop folder, so the mistakes here are the mistakes of
    copying files around, and all of them are silent: the scene plays, the
    subtitle appears, and nothing is heard.

      - a name that matches no line   -> gen_vomap.py never writes an entry
      - a plain .wav renamed to .wem  -> Wwise has no codec for format 0x0001
      - a truncated or empty file     -> the source reader gets no samples
      - a codec nothing in the game uses

    The renamed-.wav case is the one worth the code. This project's audio comes
    out of an RVC pipeline as .wav, the extension is one keystroke from .wem,
    and a .wav renamed by hand is a well-formed RIFF that packs without
    complaint - so nothing else in the build would ever look at it twice.
    """
    import gen_vomap
    import wav_to_wem

    keys = json.loads((ROOT / "source" / "subtitle_ids.json").read_text(encoding="utf-8"))
    keys.pop("_comment", None)

    # The three the shipped data actually uses, read off a census of every .wem
    # in audio_1_general, audio_2_soundbanks and 24 installed mods. Anything else
    # may still work, but nothing here has ever seen it work.
    CODECS = {0xFFFF: "Wwise Vorbis", 0xFFFE: "PCM", 0x8311: "Wwise Opus"}

    n_wem = n_pending = 0
    # Audio dropped under a locale the mod does not voice is the same class of
    # mistake as a misnamed file: it converts, it packs, it is never played. Since
    # D42 that is every locale but en-us, so say so here rather than let the file
    # sit there looking like progress.
    # Every directory that exists, not a list of locales - a vo/fr-fr/ nobody
    # planned is exactly the case worth catching.
    vo_root = ROOT / "vo"
    for d in sorted(p for p in vo_root.iterdir() if p.is_dir()) if vo_root.is_dir() else []:
        locale = d.name
        if locale in gen_vomap.VO_LOCALES:
            continue
        stray = [f.name for f in sorted(d.iterdir()) if f.is_file() and
                 (f.suffix.lower() == ".wem" or f.suffix.lower() in wav_to_wem.SOURCES)]
        if stray:
            errors.append(
                f"vo/{locale}/ holds {len(stray)} audio file(s) but {locale} ships no "
                f"voiceover (gen_vomap.VO_LOCALES): {', '.join(stray[:3])}"
                f"{' ...' if len(stray) > 3 else ''}. Delete them, or add the locale "
                f"to VO_LOCALES - see docs/decisions.md D42.")
    for locale in gen_vomap.VO_LOCALES:
        d = ROOT / "vo" / locale
        if not d.is_dir():
            continue
        for f in sorted(p for p in d.iterdir() if p.is_file()):
            ext = f.suffix.lower()
            if ext != ".wem" and ext not in wav_to_wem.SOURCES:
                errors.append(f"vo/{locale}/{f.name} is not audio the build knows "
                              f"how to use (.wem, or {'/'.join(wav_to_wem.SOURCES)} "
                              f"to be converted)")
                continue

            key, _ = gen_vomap.split_stem(f.stem)
            if key not in keys:
                errors.append(f"vo/{locale}/{f.name} names no line in "
                              f"source/subtitle_ids.json - it would be packed and "
                              f"never played")
                continue

            if ext != ".wem":
                # A source file with no .wem yet is normal: validate runs before
                # the generators, so the first build sees exactly this. One that
                # HAS its .wem is not pending anything - counting it said "43
                # awaiting conversion" on a run where all 43 were converted,
                # which is the one number a reader would check to see whether
                # the audio built.
                if not f.with_suffix(".wem").exists():
                    n_pending += 1
                continue

            n_wem += 1
            head = f.read_bytes()[:24]
            if len(head) < 24 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
                errors.append(f"vo/{locale}/{f.name} is not a RIFF/WAVE file at all "
                              f"({f.stat().st_size} bytes)")
                continue
            if head[12:16] != b"fmt ":
                errors.append(f"vo/{locale}/{f.name} has no fmt chunk where a .wem "
                              f"keeps one")
                continue
            codec = int.from_bytes(head[20:22], "little")
            if codec == 0x0001:
                errors.append(f"vo/{locale}/{f.name} is a plain Microsoft WAV that "
                              f"has been renamed - format 0x0001, which Wwise has no "
                              f"codec for. Give it back its real extension and let "
                              f"tools/wav_to_wem.py convert it")
            elif codec not in CODECS:
                errors.append(f"vo/{locale}/{f.name} is codec {codec:#06x}, which "
                              f"nothing in the game or in any installed mod uses "
                              f"(expected one of "
                              f"{', '.join(f'{c:#06x} {n}' for c, n in CODECS.items())})")

    return n_wem, n_pending


def check_audioware(errors):
    """The Audioware bank's names, checked before anything generates them.

    The bank is the route the recordings actually travel (D67): a scnAudioEvent
    names a CName, Audioware answers it, the .wav plays. Every failure on that
    route is silent - a CName that matches no bank entry is not an error to the
    audio system, it is a sound that is not there.

    Two of those failures are visible from source alone:

      - Two different lines whose keys collapse to the SAME event name. The
        rule is "dot becomes underscore", so mara.open_1 and mara_open.1 would
        both become ash_cache_vo_mara_open_1. One line would play the other
        line's audio, and the build would be perfectly happy.
      - A name a CName cannot carry cleanly, or one missing the ash_cache_
        prefix rule 5 exists to enforce - a bare "mara_open_1" is exactly the
        kind of name another mod's bank would also pick.

    What this CANNOT check is whether the game answers the event at all. That
    is what the CET Voice tab is for.
    """
    import gen_audioware

    seen = {}
    n = 0
    for key in sorted(gen_audioware.sources()):
        name = gen_audioware.event_name(key)
        n += 1
        if name in seen:
            errors.append(f"vo/ lines {seen[name]!r} and {key!r} both become the "
                          f"audioware event {name!r} - one of them would play the "
                          f"other's recording. Rename a line id so the two keys "
                          f"differ by more than a dot")
        seen[name] = key
        if not name.startswith("ash_cache_"):
            errors.append(f"audioware event {name!r} is not prefixed ash_cache_ "
                          f"(rule 5) - it could collide with another mod's bank")
        bad = [c for c in name if not (c.isascii() and (c.isalnum() or c == "_"))]
        if bad:
            errors.append(f"audioware event {name!r} holds {bad[0]!r}, which a "
                          f"Wwise event name cannot carry - fix the line id")
    return n


def check_narration(errors):
    """The notes V reads aloud: does every recording still name a shard? (D125)

    narration/<locale>/<onscreen entry>.wav is a drop folder like vo/, and it
    fails the same way: the "Toggle Audio" button is drawn by Shard Audio
    Framework for EVERY uncrypted shard whether or not a recording answers it,
    so a file named after a shard that has been renamed, or never existed, is a
    button that does nothing and a build that says nothing.

    The file's stem is the onscreen entry id rather than the LocKey it becomes,
    because the number is not something a person should have to be right about
    by hand - gen_audioware derives it from source/items.json and
    source/lockeys.json, the same two files the journal is built from.

    Returns (recordings, shards) so the summary can say 3/5 rather than 3.
    """
    import gen_audioware
    import wav_to_wem
    import gen_vomap

    keys = gen_audioware.shard_keys()
    n = 0
    root = ROOT / "narration"
    for d in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
        if d.name not in gen_vomap.VO_LOCALES:
            stray = [f.name for f in sorted(d.iterdir())
                     if f.is_file() and f.suffix.lower() in wav_to_wem.SOURCES]
            if stray:
                errors.append(
                    f"narration/{d.name}/ holds {len(stray)} recording(s) but {d.name} "
                    f"ships no voiceover (gen_vomap.VO_LOCALES): {', '.join(stray[:3])}. "
                    f"See docs/decisions.md D42.")
            continue
        for f in sorted(p for p in d.iterdir() if p.is_file()):
            if f.suffix.lower() not in wav_to_wem.SOURCES:
                errors.append(f"narration/{d.name}/{f.name} is not audio Audioware can "
                              f"read ({'/'.join(sorted(wav_to_wem.SOURCES))})")
                continue
            if f.stem not in keys:
                errors.append(f"narration/{d.name}/{f.name} names no shard in "
                              f"source/items.json - the Toggle Audio button on every "
                              f"shard would still be drawn, and this one would never "
                              f"play. Known: {', '.join(sorted(keys))}")
                continue
            n += 1
    return n, len(keys)


def check_line_timing(scenes, errors):
    """An explicit "ms" that contradicts the recording sitting next to it.

    Both are legitimate on their own. Together they are a trap: someone sets
    "ms": 3000 while the line is unvoiced, a 6-second recording is dropped in
    later, and the subtitle now vanishes three seconds before the audio stops.
    The override wins by design - that is what an override is for - so nothing
    downstream would ever notice.

    Only the too-short direction is an error. Erring long costs a beat of
    silence; erring short eats the end of a spoken line.
    """
    import gen_scene

    audio = gen_scene.vo_lengths()
    if not audio:
        return 0
    n = 0
    for stem, scene in scenes.items():
        for node in scene.get("nodes", []):
            for line in node.get("lines", []):
                if "ms" not in line:
                    continue
                key = f"{stem}.{line['id']}"
                have = audio.get(key)
                if have and line["ms"] < have:
                    n += 1
                    errors.append(
                        f"scene_{stem}.json line {line['id']!r} sets \"ms\": "
                        f"{line['ms']} but its recording runs {have} ms - the "
                        f"override wins, so the subtitle would disappear "
                        f"{have - line['ms']} ms before the voice stops. Raise it "
                        f"or drop it and let the audio set the timing")
    return n


def check_lipsync(chars, scenes, graph, errors):
    """The voicetag namespace, and the two places a lipsync map can silently miss.

    Lipsync binds through numbers, not names, and every way it can be wrong is
    quiet: an actor left on voicetag 0 has no key the map can answer, two
    characters sharing a tag get each other's mouth, and a scene whose depot path
    moved hashes to nothing so the map matches no scene at all. None of those
    fail a build or log a line - the face just never moves.

    See tools/gen_lipmap.py for the whole chain and the vanilla line it was
    verified against.
    """
    # Imported rather than restated: the hash input has to be the one string the
    # generator actually hashes, or this check would pass while agreeing only
    # with itself.
    import alloc_voicetags
    import gen_lipmap

    tags = json.loads((ROOT / "source" / "voicetags.json").read_text(encoding="utf-8"))
    tags.pop("_comment", None)
    known = {c["id"] for c in chars["characters"]}
    cast = {cid for sc in scenes.values() for cid in sc.get("actors", []) if cid in known}

    for cid in sorted(cast):
        if cid not in tags:
            errors.append(f"character {cid!r} speaks in a scene but has no voicetag - "
                          f"run tools/alloc_voicetags.py, or the lipsync map has no "
                          f"key for her and her face never moves")

    seen = {}
    for cid, raw in sorted(tags.items()):
        try:
            n = int(raw)
        except (TypeError, ValueError):
            errors.append(f"voicetag for {cid!r} is {raw!r}, which is not a number")
            continue
        if n == 0:
            errors.append(f"voicetag for {cid!r} is 0, which is the PLAYER's tag - "
                          f"the game ships no lipsync for V, so 0 is a key nothing "
                          f"can ever answer")
        elif not alloc_voicetags.BLOCK_START <= n <= alloc_voicetags.BLOCK_END:
            errors.append(f"voicetag for {cid!r} is {n}, outside the reserved block "
                          f"{alloc_voicetags.BLOCK_START}-{alloc_voicetags.BLOCK_END} - "
                          f"it could collide with a vanilla character's tag")
        if n in seen:
            errors.append(f"characters {seen[n]!r} and {cid!r} share voicetag {n} - "
                          f"one would be given the other's mouth animation")
        seen[n] = cid

    # The hash target. gen_lipmap.py turns a scene's depot path into the uint64 the
    # map keys on; quest_graph.json names the same scene by the same path for the
    # questphase. They are authored in different files and nothing else compares
    # them, so a scene renamed in one place and not the other produces a map whose
    # scenePaths match no scene in the game - and ArchiveXL merges it happily.
    for n in graph["nodes"]:
        if n.get("type") != "scene":
            continue
        name = n["file"].replace("\\", "/").rsplit("/", 1)[-1]
        if not (name.startswith("ash_cache_") and name.endswith(".scene")):
            continue
        stem = name[len("ash_cache_"):-len(".scene")]
        want = gen_lipmap.scene_depot_path(stem)
        if n["file"] != want:
            errors.append(f"graph node {n['id']!r} plays {n['file']!r}, but the lipsync "
                          f"map hashes {want!r} - the map would key on a path no scene "
                          f"has and animate nobody")

    # Animsets that are on disk now. A file naming nobody is the same silent
    # nothing as a missing one, so it is caught here as well as in the generator.
    n_sets = 0
    for locale in gen_lipmap.VO_LOCALES:
        src = ROOT / "lipsync" / locale
        if not src.is_dir():
            continue
        for anims in sorted(src.glob("*.anims")):
            cid = anims.name[: -len(".anims")]
            n_sets += 1
            if cid not in cast:
                errors.append(f"lipsync/{locale}/{anims.name} names {cid!r}, who is in "
                              f"no scene's cast - nothing would ever load it")
            elif cid not in tags:
                errors.append(f"lipsync/{locale}/{anims.name} names {cid!r}, who has no "
                              f"voicetag - the map cannot address it")

    return len(tags), n_sets


def check_extra_phases(known_facts, quest_graph, errors, extra_read):
    """Validate every injected phase that is NOT the quest graph.

    source/cynosure_graph.json ships as its own questphase resource, so nothing
    in the quest checks above ever looks at it. Left unchecked, the two things
    that can go wrong are both silent in game: a prefab NodeRef with a typo
    streams nothing and reports nothing, and a fact the quest sets by accident
    would turn a deliberately opt-in world change on for everybody.

    The prefab refs are checked against reference/examples/quest_prefab_streaming
    .json, which records where each one was read out of vanilla. That file is the
    provenance - the point is that these two names are not remembered, they are
    quoted, and a third name added later has to be quoted too.
    """
    src = ROOT / "source" / "cynosure_graph.json"
    if not src.exists():
        return 0
    g = json.loads(src.read_text(encoding="utf-8"))
    ref = json.loads((ROOT / "reference" / "examples" /
                      "quest_prefab_streaming.json").read_text(encoding="utf-8"))
    verified = set(ref["verified_prefab_refs"])

    n = 0
    used = set()
    for node in g["nodes"]:
        t = node.get("type")
        if t == "pause_fact":
            used.add(node["fact"])
        elif t == "prefab_phase":
            rel = node.get("release") or {}
            if "fact" in rel:
                used.add(rel["fact"])
            for pref in node.get("prefabs", []):
                n += 1
                if not pref.startswith("#"):
                    errors.append(f"cynosure_graph.json: prefab ref {pref!r} must start "
                                  f"with '#'")
                elif pref not in verified:
                    errors.append(
                        f"cynosure_graph.json holds prefab {pref!r}, which is not one of "
                        f"the refs verified against vanilla in reference/examples/"
                        f"quest_prefab_streaming.json ({', '.join(sorted(verified))}). "
                        f"A prefab ref the engine does not know streams nothing and says "
                        f"nothing - read it out of a real questphase before naming it.")
    for f in sorted(used - known_facts):
        errors.append(f"cynosure_graph.json uses fact {f!r} that facts.json does not declare")
    extra_read.update(used)

    # Opt-in by construction. The whole safety argument for shipping an untested
    # world change is that it is off until the player turns it on, so anything
    # that would set it from inside the mod has to fail the build, not surprise
    # a playthrough.
    opt_in = "ashcache_cynosure_open"
    if any(x.get("type") == "set_fact" and x.get("fact") == opt_in
           for x in quest_graph["nodes"]):
        errors.append(f"the quest graph sets {opt_in!r}. That fact streams two vanilla "
                      f"q305 sectors outside their quest and has never been tested in "
                      f"game; it is opt-in on purpose. Nothing in this mod may set it.")
    glue = load("glue.json")
    glue_sets = ({glue["start"]["fact"]}
                 | {a["fact"] for a in glue["areas"]}
                 | {x["fact"] for x in glue["shards"]})
    if opt_in in glue_sets:
        errors.append(f"glue.json sets {opt_in!r} - see above, it is opt-in on purpose.")
    return n


def check_cynosure(known_facts, errors):
    """The Cynosure M0 contract (tools/cyn_import.py) against the quest and the disk.

    Errors are things that would ship wrong: a contract fact that collides with a
    quest fact it does not alias, a fact name without the global prefix, a name
    the bundle forbids, a transform marked measured with holes in it or marked
    unmeasured with numbers in it (the registry's rule: null is never 0), an asset
    mapped to a prop that is not built. IDs the transform registry uses but the ID
    registry never lists are the bundle's own gaps - notes, not failures.
    """
    c, t = load("cynosure_contract.json"), load("cynosure_transforms.json")
    aliases = {v["doc"]: k for k, v in c["facts"].items() if not k.startswith("ashcache_")
               or v["doc"][4:] != k[len("ashcache_"):]}
    for name, v in c["facts"].items():
        if not name.startswith("ashcache_"):
            errors.append(f"cynosure fact {name!r} lacks the ashcache_ prefix")
        elif v["doc"] in aliases and name not in known_facts:
            errors.append(f"cynosure fact {v['doc']!r} aliases {name!r}, which facts.json does not declare")
        elif v["doc"] not in aliases and name in known_facts:
            errors.append(f"cynosure fact {v['doc']!r} renames to {name!r}, which facts.json already "
                          f"declares - alias it in tools/cyn_import.py or rename one of them")
    for name in c["forbidden_facts"]:
        if name in known_facts or name in c["facts"]:
            errors.append(f"fact {name!r} encodes a protected mystery as truth - CYNOSURE_FACTS.md forbids it")
    for doc, m in c.get("mapped", {}).items():
        for name in [m["alias"]] if "alias" in m else m["inputs"]:
            if name not in known_facts:
                errors.append(f"cynosure {doc!r} maps to {name!r}, which facts.json does not declare")
        if "ashcache_" + doc[4:] in c["facts"]:
            errors.append(f"cynosure {doc!r} is mapped to existing facts but the contract also stores it")

    status = set(t["status_values"])
    records = [(sec, k, r) for sec, body in t.items() if isinstance(body, dict)
               for k, r in body.items() if isinstance(r, dict) and "status" in r]
    for sec, k, r in records:
        if r["status"] not in status:
            errors.append(f"cynosure_transforms.json {sec}.{k} has status {r['status']!r}")
            continue
        nums = [x for f in ("position", "rotation") for x in (r.get(f) or {}).values()]
        if r["status"] == "UNMEASURED" and any(x is not None for x in nums):
            errors.append(f"cynosure_transforms.json {sec}.{k} is UNMEASURED but has numbers - "
                          f"measure it and set the status, or null them")
        if r["status"] != "UNMEASURED" and any(x is None for x in nums):
            errors.append(f"cynosure_transforms.json {sec}.{k} is {r['status']} with null fields")

    for aid, a in c["assets"].items():
        for d in a["props"]:
            if not list((ROOT / a["path"] / d).glob("*.mesh")):
                errors.append(f"{aid} maps to {a['path']}/{d}, which has no .mesh")

    registered = {i for v in c["ids"].values() for i in v}
    used = set(re.findall(r"\bCYN_[A-Z0-9_]+", (ROOT / "source" / "cynosure_transforms.json").read_text()))
    unregistered = sorted(used - registered)
    measured = sum(r["status"] != "UNMEASURED" for _, _, r in records)
    unbuilt = sorted(aid[len("CYN_ASSET_"):] for aid, a in c["assets"].items() if not a["props"])
    return len(registered), measured, len(records), unregistered, unbuilt, c["open_questions"]


def main():
    facts, journal, graph = load("facts.json"), load("journal.json"), load("quest_graph.json")
    strings = load("strings.json")
    lockeys = {k for k in load("lockeys.json") if not k.startswith("_")}
    errors = []

    known_facts = declared_facts(facts)
    known_paths, thread_roots = journal_paths(journal)

    scenes = {path.stem[len("scene_"):]: load(path.name)
              for path in sorted((ROOT / "source").glob("scene_*.json"))}
    subtitle_ids = {k for k in load("subtitle_ids.json") if not k.startswith("_")}

    def condition_facts(c, out_facts, out_paths):
        """Facts and journal paths can be nested arbitrarily deep inside a
        condition, because questLogicalCondition contains other conditions."""
        if not isinstance(c, dict):
            return
        for term in (c.get("all") or c.get("any") or []):
            condition_facts(term, out_facts, out_paths)
        if "fact" in c:
            out_facts.add(c["fact"])
        if "journal" in c:
            out_paths.add(c["journal"])

    # Which input socket each node is entered on. Naming a journal path is not
    # the same as activating it: since D54 every description carries a second
    # node entered on Inactive, whose whole job is to retire the paragraph. If
    # the activating node were deleted the path would still be *named*, so a
    # membership test on "path" alone would stop catching the bug below. A
    # journal node with no incoming link at all falls back to its type default,
    # which for both journal kinds is Active.
    entered_on = {}
    for link in graph["links"]:
        dst = link[1].partition(":")[0]
        entered_on.setdefault(dst, set()).add(link[2] if len(link) > 2 else None)

    used_facts, used_paths, activated = set(), set(), set()
    for n in graph["nodes"]:
        if not n.get("id"):
            continue
        if "fact" in n:
            used_facts.add(n["fact"])
        condition_facts(n.get("condition"), used_facts, used_paths)
        if "path" in n:
            used_paths.add(n["path"])
            socks = entered_on.get(n["id"]) or {None}
            if any(s in (None, "Active") for s in socks):
                activated.add(n["path"])
    for path in sorted(used_paths):
        if path not in known_paths:
            errors.append(f"graph points at journal path {path!r}, "
                          f"which journal.json does not define")

    # An objective the graph never touches is dead UI - it can never appear.
    for path in sorted(known_paths - activated - thread_roots):
        errors.append(f"journal defines {path!r} but no graph node ever activates it")

    # The phase entry socket. ArchiveXL merges this phase into the parent quest by
    # synthesising a questPhaseNodeDefinition whose sockets it hardcodes to In1/Out1
    # (cp2077-archive-xl/src/App/Extensions/QuestPhase/Extension.cpp, PatchPhase:
    # AddConnection(inputNode, ..., modPhaseNode, "In1") - the name is a literal, not
    # read from us). The engine enters a child phase by matching the parent's socket name
    # against an input node here. Any other name merges without complaint, resolves
    # in every layer check, and then runs nothing at all - the single most expensive
    # silent failure this build can have, so it is asserted rather than trusted.
    XL_SOCKETS = {"input": "In1", "output": "Out1"}
    for kind, want in XL_SOCKETS.items():
        found = [n for n in graph["nodes"] if n.get("type") == kind]
        if not found:
            errors.append(f"quest_graph.json has no {kind} node - ArchiveXL cannot "
                          f"wire the phase into its parent without one")
            continue
        for n in found:
            got = n.get("socket")
            if got != want:
                errors.append(f"quest_graph.json {kind} node {n['id']!r} has socket "
                              f"{got!r}, but ArchiveXL wires the parent to {want!r} - "
                              f"the phase would merge and never execute")

    # The phase revision. ArchiveXL force-starts an injected phase on a loaded save
    # exactly once per depot path, remembers that in a fact keyed by CRC16 of that
    # path, and sets the fact whether or not the phase actually ran. So the path is
    # not cosmetic: it is the identity a save remembers the phase by, and a build
    # that reuses the path of a build that already failed on this save cannot start.
    rev = graph.get("phase_revision")
    if not isinstance(rev, int) or isinstance(rev, bool) or rev < 1:
        errors.append(f"quest_graph.json phase_revision is {rev!r}, must be an "
                      f"integer >= 1 - it names the phase resource and is what "
                      f"lets a save that already ran an older build start this one")

    # A scene node's sockets are generated from the graph's own "entries"/"exits",
    # not read from the .scene. If they disagree, the questphase gets a socket that
    # names an entry point the scene does not have: no error, just flow that stops.
    scene_facts = set()
    for n in graph["nodes"]:
        if n.get("type") != "scene":
            continue
        name = n["file"].replace("\\", "/").rsplit("/", 1)[-1]
        name = name[len("ash_cache_"):-len(".scene")]
        sc = scenes.get(name)
        if sc is None:
            errors.append(f"graph node {n['id']!r} plays scene {name!r}, "
                          f"but source/scene_{name}.json does not exist")
            continue
        for kind, key in (("entry", "entries"), ("exit", "exits")):
            declared = {e["name"] for e in sc[f"{kind}Points"]}
            for want in n[key]:
                if want not in declared:
                    errors.append(f"graph node {n['id']!r} names {kind} point {want!r}, "
                                  f"which scene_{name}.json does not declare "
                                  f"(has {sorted(declared)})")

    for name, sc in scenes.items():
        # 'goto' on a choice option is documentation - gen_scene.py never reads it,
        # the "hub:opt_id" entry in 'links' is what actually routes the option. That
        # is survivable with one hub and three options and a trap with two hubs and
        # seven, so the annotation has to agree with the wiring or say nothing.
        routed = {}
        for link in sc["links"]:
            src, _, opt = link[0].partition(":")
            if opt:
                routed[(src, opt)] = link[1]
        for node in sc["nodes"]:
            for opt in node.get("options", []):
                if "goto" not in opt:
                    continue
                dst = routed.get((node["id"], opt["id"]))
                if dst is None:
                    errors.append(f"scene_{name}.json option {opt['id']!r} says it goes to "
                                  f"{opt['goto']!r}, but no link leaves {node['id']!r} on it "
                                  f"- the option would be offered and lead nowhere")
                elif dst != opt["goto"]:
                    errors.append(f"scene_{name}.json option {opt['id']!r} says it goes to "
                                  f"{opt['goto']!r}, but its link goes to {dst!r} - the link "
                                  f"wins, so the file lies about where the choice leads")

        for node in sc["nodes"]:
            if node.get("type") == "quest" and "fact" in node.get("node", {}):
                scene_facts.add(node["node"]["fact"])
            # A conditional option is REMOVED when its condition fails, not greyed
            # out (reference/choice_conditions.md). So a hub whose every option is
            # conditional can be reached with nothing in it - the hub opens empty
            # and the conversation stops with no error anywhere. Vanilla has a
            # failsafe flag for deliberately doing that; this project does not want
            # it, so require one option that is always offered.
            opts = node.get("options", [])
            for opt in opts:
                condition_facts(opt.get("condition"), scene_facts, used_paths)
            if opts and all(o.get("condition") for o in opts):
                errors.append(f"scene_{name}.json hub {node['id']!r} has {len(opts)} "
                              f"option(s) and every one of them is conditional - if "
                              f"they all fail the player gets an empty hub and the "
                              f"scene stalls; leave at least one unconditional")
            for item in node.get("lines", []) + node.get("options", []):
                if f"{name}.{item['id']}" not in subtitle_ids:
                    errors.append(f"scene_{name}.json line {item['id']!r} has no subtitle id "
                                  f"- run tools/alloc_subtitle_ids.py")
                if not item.get("ua-ua"):
                    errors.append(f"scene_{name}.json line {item['id']!r} has no ua-ua text "
                                  f"- it would play the English line to a Ukrainian player")

    extra_read = set()
    n_prefabs = check_extra_phases(known_facts, graph, errors, extra_read)
    cyn_ids, cyn_measured, cyn_records, cyn_unreg, cyn_unbuilt, cyn_open = check_cynosure(known_facts, errors)

    # D193: the Cynosure M0 contract declares its own facts (ashcache_cyn_phase and
    # the rest of the phase ladder); check_cynosure already refuses a collision with
    # facts.json, so a contract fact is declared exactly once and the graph may use it.
    contract_facts = set(load("cynosure_contract.json")["facts"])
    for f in sorted((used_facts | scene_facts) - known_facts - contract_facts):
        errors.append(f"graph uses fact {f!r} that neither facts.json nor the Cynosure contract declares")

    # A fact the graph waits on but nothing sets is a permanent stall.
    waited = set()
    for n in graph["nodes"]:
        if n.get("type") == "pause_fact":
            waited.add(n["fact"])
        elif n.get("type") == "pause":
            condition_facts(n["condition"], waited, set())
    set_in_graph = {n["fact"] for n in graph["nodes"] if n.get("type") == "set_fact"}
    set_in_graph |= scene_facts       # a scene's embedded quest nodes set facts too
    external = declared_facts({"w": facts.get("world_triggers", {}),
                               "d": facts.get("discoveries", {}),
                               "m": facts.get("mara", {}),
                               # facts.json "debug": test facts set by hand from the CET console
                               "x": facts.get("debug", {})})
    for f in sorted(waited - set_in_graph - external):
        errors.append(f"graph waits on fact {f!r} that nothing sets - the quest would stall there")

    # Facts the graph waits on and does not set. Legitimate by design - something
    # outside the graph is supposed to set them - but "by design" and "written
    # yet" are different things, and every one of these that nothing sets is a
    # point where the quest silently stops advancing (OI-12).
    glue = load("glue.json")
    set_by_glue, blocked = check_glue(glue, facts, load("world.json"), load("items.json"),
                                      graph, known_facts, errors)
    unset_external = sorted((waited & external) - set_in_graph - set_by_glue)

    # glue.json's own list of what it cannot do yet has to match what is actually
    # left over, or the file quietly stops describing reality: a fact dropped from
    # 'blocked' without being implemented is exactly the kind of gap that gets
    # rediscovered by installing the mod and watching nothing happen.
    if set(unset_external) != blocked:
        for f in sorted(set(unset_external) - blocked):
            errors.append(f"nothing sets {f!r} and glue.json does not list it under "
                          f"'blocked' - either hook it up or write down what it needs")
        for f in sorted(blocked - set(unset_external)):
            errors.append(f"glue.json lists {f!r} as blocked, but the graph no longer "
                          f"waits on it - remove it from 'blocked'")

    # A fact nothing sets AND nothing reads is a declaration the design believes
    # in and the build does not implement. ashcache_mara_hostile sat here: facts.json
    # said the intimidate branch set it, the scene ran straight past, and the
    # cleanup encounter had no way to know. Reported rather than failed, because a
    # fact can legitimately be declared ahead of the content that uses it.
    read_anywhere = used_facts | waited | scene_facts
    # A fact read only by an extra injected phase (cynosure_graph.json) is live;
    # the scans above only walk the quest graph, so without this it reports as
    # dead and the note trains you to ignore the note.
    read_anywhere = read_anywhere | extra_read
    dead_facts = sorted(known_facts - set_in_graph - external - read_anywhere)
    # A world_triggers/discoveries fact is "set" from outside by definition, so it
    # is only dead if nothing reads it either.
    dead_facts += sorted(f for f in (external & known_facts)
                         if f not in read_anywhere and f not in set_in_graph)

    for sid in sorted({k for k in strings if not k.startswith("_")} - lockeys):
        errors.append(f"string {sid!r} has no LocKey - run tools/alloc_lockeys.py")

    journal_refs = ({o["description"] for ph in journal["phases"] for o in ph["objectives"]}
                    | {o["summary"] for ph in journal["phases"] for o in ph["objectives"]
                       if "summary" in o}
                    | {c["contact"]["name"] for c in journal.get("phoneConversations", [])}
                    | {journal["quest"]["title"]})
    for ref in sorted(journal_refs):
        if ref[4:] not in strings:
            errors.append(f"journal references {ref!r} which strings.json does not define")

    world = load("world.json")
    # A blunt raw-text sweep for '#ac_*' across the source files that have no
    # structured walker - it cannot tell a use from a mention, but for those
    # files every mention IS a use. quest_graph.json is walked properly by
    # graph_node_refs, and world.json is where nodes are DEFINED, so its prose
    # naming one is not a reference to it; scanning either here would let a
    # sentence in a _comment stand in for a real link.
    STRUCTURED = {"quest_graph.json", "world.json"}
    ref_txt = {p.name: p.read_text(encoding="utf-8")
               for p in sorted((ROOT / "source").glob("*.json"))
               if p.name not in STRUCTURED}
    # D193: a glue area names its marker bare ("marker": "ac_cyn_escape"), and the
    # arrival watch built from it IS a use of that node. Structured, not a regex
    # over glue.json, so a marker merely mentioned in an _about does not count.
    ref_txt["glue.json areas"] = "\n".join(f"#{a['marker']}" for a in glue["areas"])
    markers, deferred = check_world(world, ref_txt, graph, errors)
    chars = load("characters.json")
    cast = check_cast(chars, scenes, markers, deferred, strings, errors)
    n_verified, unverified = check_verified(world, graph, chars, errors)
    check_graph_sockets(graph, errors)
    check_scene_tier(scenes, graph, errors)
    items = load("items.json")
    known_items = check_items(items, graph, strings, errors)
    n_tweak = check_tweakdb(chars, journal, items, world, errors)
    n_depot = check_depot(world, errors)
    n_names = check_proper_nouns(errors)
    n_codex = check_codex(journal, errors)
    n_qicon = check_journal_icon(journal, errors)
    n_dicon = check_district_icon(journal, errors)
    n_wem, n_pending = check_voiceover(errors)
    n_bank = check_audioware(errors)
    n_read, n_shards = check_narration(errors)
    # Names are checked either way - a collision is a latent bug whether or not
    # this build ships the bank - but the count must not read as "43 lines play
    # through Audioware" when the engine is the one playing them.
    import gen_audioware
    bank_on, bank_why = gen_audioware.wanted()
    check_line_timing(scenes, errors)
    n_tags, n_anims = check_lipsync(chars, scenes, graph, errors)

    if errors:
        print(f"VALIDATION FAILED ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    n_lines = sum(len(n.get("lines", [])) + len(n.get("options", []))
                  for sc in scenes.values() for n in sc["nodes"])
    print(f"validation OK  ({len(known_facts)} facts, {len(known_paths)} journal paths, "
          f"{len(lockeys)} lockeys, {len([n for n in graph['nodes'] if n.get('id')])} graph nodes, "
          f"{len(scenes)} scene(s), {n_lines} spoken lines, "
          f"{len(world['sectors'])} sector(s), {placement_tally(world)}, "
          f"{len(n_verified)}/{len(n_verified) + len(unverified)} position(s) stood on, "
          f"{len(deferred)} deferred, {len(cast)} character(s), "
          f"{len(known_items)} item(s), {n_tweak} tweakdb record(s), "
          f"{n_depot} depot path(s), "
          f"{n_names} proper noun(s), {n_codex} codex link(s), "
          f"{n_qicon} drawable quest type, {n_dicon} district icon, "
          f"{n_wem} voiced line file(s)"
          f"{f' (+{n_pending} awaiting conversion)' if n_pending else ''}, "
          f"{n_bank} audioware name(s)"
          f"{' IN BANK' if bank_on else ' (bank off: engine plays them)'}, "
          f"{n_read}/{n_shards} note(s) read aloud, "
          f"{n_tags} voicetag(s), {n_anims} lipsync animset(s), "
          f"{len(set_by_glue)} fact(s) set by the glue, "
          f"{n_prefabs} held prefab(s), "
          f"cynosure {cyn_ids} id(s) {cyn_measured}/{cyn_records} transform(s) measured)")
    if cyn_unreg:
        print(f"note: {len(cyn_unreg)} id(s) in cynosure_transforms.json that CYNOSURE_IDS.md does not "
              f"register: {', '.join(cyn_unreg)}")
    if cyn_unbuilt:
        print(f"note: {len(cyn_unbuilt)} cynosure asset(s) not built yet: {', '.join(cyn_unbuilt)}")
    for k, q in cyn_open.items():
        print(f"note: cynosure open question {k}: {q}")
    if unverified:
        print(f"note: {len(unverified)} world position(s) never stood on in game - "
              f"safe to pin, not safe to place an object on: {', '.join(unverified)}")
    if dead_facts:
        print(f"note: {len(dead_facts)} declared fact(s) that nothing sets and "
              f"nothing reads: {', '.join(f[len('ashcache_'):] for f in sorted(set(dead_facts)))}")
    if unset_external:
        # Each of these needs a thing in the world - a prop to open, a terminal
        # to read, an encounter to survive, a choice hub - not more glue. The
        # reason lives in glue.json next to the fact so it cannot rot (OI-13).
        print(f"note: {len(unset_external)} fact(s) gate this graph and nothing sets "
              f"yet - each needs world content, see OI-13:")
        for f in unset_external:
            print(f"        {f[len('ashcache_'):]:<16} needs {glue['blocked'][f]}")


if __name__ == "__main__":
    main()
