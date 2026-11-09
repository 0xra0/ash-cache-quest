#!/usr/bin/env python3
"""What does the quest graph DO if the phase enters a second time?

ArchiveXL force-starts an injected phase once per depot path (OI-15). Bumping
`phase_revision` renames the path, so the phase enters again on a save that has
already run it - which is the only way to repair a save whose journal predates a
graph change (D49/D50). But re-entry does not resume: the graph re-walks from
`start`, and every fact the player already set is still set, so every pause_fact
upstream of them passes instantly. The walk races to wherever the player actually
is, firing everything along the way.

Re-firing a journal node is the entire point - that is the repair. Re-firing an
add_item or a scene is not: it duplicates items and replays conversations.

This tool measures the difference instead of arguing about it. It walks the graph
the way the engine would, for every save state the player can be in, and reports
which side-effect nodes a re-entry would fire.

Graph semantics modelled here, and why:

  pause_fact   blocks until its fact matches. This is the only thing that stops
               a walk, and it is what makes a replay stop at the player.
  pause        the 500 ms INT/RET safety nets. Reachable only from a scene's
               "Default INT"/"Default RET" exits, so they never gate the spine.
  condition    evaluates immediately and takes exactly ONE of True/False. Not a
               wait - that is what pause_fact is for.
  scene        a normal completion leaves by its named exit; "Default INT" and
               "Default RET" are the interrupt/return nets. The walk follows
               named exits only, which is what a player who finishes the scene
               does.
  everything   fires and continues. Several links off one node are parallel
  else         branches and all are followed.

Exit code is 0 when the guard invariant holds: no side-effect node fires twice
across a whole playthrough. Run it before and after touching the graph.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# argv[1] overrides the graph, so the guards can be checked against the
# pre-guard backup: a test that does not fail on the old graph proves nothing.
GRAPH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "source" / "quest_graph.json"

# Nodes that change the world. Re-firing one of these on a replay is a defect;
# re-firing a journal node is the repair, so journal nodes are not in this set.
SIDE_EFFECT = {"add_item", "inject_loot", "spawn", "scene", "set_tier", "shoot_at"}


def evaluate(cond, facts):
    """The condition DSL, as the engine would read it against a fact store."""
    if "all" in cond or "any" in cond:
        terms = cond.get("all") or cond.get("any")
        results = [evaluate(t, facts) for t in terms]
        return all(results) if "all" in cond else any(results)
    if "fact" in cond:
        have = facts.get(cond["fact"], 0)
        want = cond.get("value", 1)
        cmp = cond.get("compare", "Equal")
        return {"Equal": have == want, "NotEqual": have != want,
                "Greater": have > want, "GreaterOrEqual": have >= want,
                "Less": have < want, "LessOrEqual": have <= want}[cmp]
    if "delay" in cond:
        return True          # a wall-clock net always elapses
    if "journal" in cond:
        return True          # journal state is downstream of this walk
    if "spawned" in cond or "killed" in cond:
        return True          # the crew appears and V puts them down (D111)
    if "interaction" in cond:
        # The player presses the thing. This walk is about what the graph does
        # once each beat happens, not about whether the player performs it, so
        # this is the same assumption 'delay' makes. What it deliberately does
        # NOT model is a prop that offers no prompt at all - that failure is
        # invisible to every headless check here and is why the fact stays in
        # the OR beside it (D65).
        return True
    raise SystemExit(f"replaytest: condition it cannot evaluate: {cond!r}")


def scene_facts(root):
    """Facts a scene is GUARANTEED to set, keyed by entry-point name.

    A scene sets facts from inside, and the graph cannot see that - but a guard
    on a scene depends on it entirely. Only facts whose node DOMINATES the
    scene's exit are guaranteed: delete that node and the exit must become
    unreachable. A fact set on one branch of a choice hub is not guaranteed and
    is deliberately not returned here, because a guard must never be built on
    one.
    """
    table = {}
    for path in sorted((root / "source").glob("scene_*.json")):
        d = json.loads(path.read_text())
        adj = {}
        for link in d["links"]:
            adj.setdefault(link[0].partition(":")[0], []).append(link[1].partition(":")[0])
        entries = [e["node"] if isinstance(e, dict) else e for e in d["entryPoints"]]
        exits = [e["node"] if isinstance(e, dict) else e for e in d["exitPoints"]]
        names = [e["name"] for e in d["entryPoints"] if isinstance(e, dict)]

        def reach(blocked):
            seen, queue = set(), list(entries)
            while queue:
                cur = queue.pop(0)
                if cur in seen or cur == blocked:
                    continue
                seen.add(cur)
                queue += adj.get(cur, [])
            return seen

        live = reach(None)
        if not any(e in live for e in exits):
            raise SystemExit(f"replaytest: {path.name} has no reachable exit - "
                             f"the dominance test below would pass vacuously")
        guaranteed = {}
        for node in d["nodes"]:
            inner = node.get("node")
            if isinstance(inner, dict) and inner.get("fact"):
                after = reach(node["id"])
                if not any(e in after for e in exits):
                    guaranteed[inner["fact"]] = inner.get("value", 1)
        for name in names:
            table[name] = guaranteed
    return table


def load():
    g = json.loads(GRAPH.read_text())
    nodes = {n["id"]: n for n in g["nodes"]}
    adj = {}
    for link in g["links"]:
        src = link[0]
        sid, _, socket = src.partition(":")
        adj.setdefault(sid, []).append((socket, link[1]))
    roots = [n["id"] for n in g["nodes"] if n["type"] == "input"]
    if len(roots) != 1:
        raise SystemExit(f"replaytest: expected exactly one input node, got {roots}")
    return nodes, adj, roots[0], scene_facts(ROOT)


def walk(nodes, adj, root, facts, scenefacts):
    """One pass of the engine over the graph. Returns (fired, blocked)."""
    fired, blocked, seen = [], [], set()
    queue = [root]
    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        node = nodes[nid]
        kind = node["type"]

        if kind == "pause_fact":
            cond = {k: v for k, v in node.items()
                    if k in ("fact", "value", "compare")}
            if not evaluate(cond, facts):
                blocked.append((nid, node["fact"], node.get("value", 1)))
                continue
        elif kind == "pause":
            if not evaluate(node["condition"], facts):
                blocked.append((nid, None, None))
                continue

        fired.append(nid)
        if kind == "set_fact":
            facts[node["fact"]] = node.get("value", 1)
        if kind == "scene":
            # What the scene sets from inside, for the guards that read it.
            for entry in node["entries"]:
                facts.update(scenefacts.get(entry, {}))

        if kind == "condition":
            take = "True" if evaluate(node["condition"], facts) else "False"
            outs = [(s, d) for s, d in adj.get(nid, []) if s == take]
        elif kind == "scene":
            # A player who finishes the scene leaves by the named exit. The
            # "Default INT"/"Default RET" nets fire only on interruption, and
            # following them here would report tier changes no normal run makes.
            outs = [(s, d) for s, d in adj.get(nid, [])
                    if not s.startswith("Default ")]
        else:
            outs = adj.get(nid, [])
        queue.extend(d for _, d in outs)
    return fired, blocked


def playthrough(nodes, adj, root, scenefacts):
    """Every save state the player can be parked in, with its real fact store.

    The store PERSISTS across states, which is the whole point: a save carries
    every fact the graph has already set - progress, and the D50 guard markers -
    not just the world triggers the player tripped. An earlier version of this
    tool copied the store per walk, so markers never survived and the guards
    measured as having no effect. They had none, in the model.
    """
    facts, states = {}, []   # (fact store, where it parks, what fired)
    while True:
        fired, blocked = walk(nodes, adj, root, facts, scenefacts)
        states.append((dict(facts), [b[0] for b in blocked], fired))
        if not blocked:
            return states
        nid, fact, value = blocked[0]
        if fact is None:
            raise SystemExit(f"replaytest: stuck on non-fact pause {nid}")
        facts[fact] = value


def endings(final):
    """The four endings, which the pause-driven walk never reaches.

    Every ending fact is set inside the decision scene's choice hub, so it is
    branch-specific and not guaranteed - which is exactly why the walk above
    stops short of them, and exactly why they need spelling out here. Without
    these, give_fia_key is never exercised and its guard is never tested.
    """
    out = []
    for name in ("destroy", "absorb", "blueeyes", "hide"):
        facts = dict(final)
        facts["ashcache_decision_made"] = 1
        facts[f"ashcache_end_{name}"] = 1
        if name == "hide":
            facts["ashcache_mara_trusted"] = 1
            facts["ashcache_mara_dead"] = 0
            facts["ashcache_hide_available"] = 1
        out.append((f"ending: {name}", facts))
    return out


def dispositions(final):
    """How V left Mara, which the pause-driven walk cannot know either (D121).

    Same problem as endings() and the same answer. ashcache_mara_trusted and
    ashcache_mara_hostile are set on opposite branches of her choice hub, so
    neither dominates the scene's exit and scene_facts() is right to withhold
    both - but everything hanging off that conversation (her sidearm, and which
    of the two counts she sends during the cleanup) reads exactly those facts.
    Without this, give_liberty and its guard are never exercised at all.

    The scene guard has to be re-opened to get there: on a finished save
    guard_meet_mara is shut, meet_mara is skipped, and every node downstream of
    its exit is unreachable. So drop the marker the scene itself sets, and the
    walk plays the conversation again with the disposition decided in advance.
    """
    out = []
    for name in ("trusted", "hostile"):
        facts = dict(final)
        facts.pop("ashcache_mara_choice_made", None)
        facts[f"ashcache_mara_{name}"] = 1
        out.append((f"mara: {name}", facts))
    return out


def aftermath(final):
    """The landfill, which needs an ending AND an arrival AND a disposition (D122).

    Three things the walk cannot supply on its own stand between it and the two
    coroner's notes. An ending that leaves the cache alive in the world, because
    Mara only turns up dead in absorb and blueeyes - burn it or bury it and
    nobody has a reason to look for her, so there is no body and no grant. The
    arrival fact, which the glue sets off a proximity watch the simulator has no
    model of. And whether V handed her the sidearm, which decides which of the
    two notes is granted.

    One grant is reachable per walk by construction - they are the two sides of
    one condition - so both wounds need a walk of their own. That is the same
    shape as endings() and dispositions() and for the same reason: the walk is
    right to refuse to guess, and the harness has to say the quiet part out loud.
    """
    out = []
    for wound, given in (("shot", 1), ("cut", 0)):
        facts = dict(final)
        facts["ashcache_decision_made"] = 1
        facts["ashcache_end_absorb"] = 1
        facts["ashcache_at_landfill"] = 1
        facts["ashcache_mara_liberty_given"] = given
        out.append((f"landfill: {wound}", facts))
    return out

def site(final):
    """The shaft head worked rather than glanced at (D131).

    Both shards there hang off options inside the scene's own hub, so neither
    fact dominates its exit and scene_facts() is right to withhold them - the
    same shape as dispositions(), and for the same reason. Without this walk
    the two grants are unreachable and report 0x, which is indistinguishable
    from a guard stuck shut.

    The site marker has to be dropped for the same reason dispositions() drops
    hers: on a finished save guard_shaft_site is closed, the scene is skipped,
    and everything downstream of its exit is unreachable. One walk covers both
    grants because they are not alternatives - a player can pull the plate AND
    jack the port, and most will.
    """
    facts = dict(final)
    facts.pop("ashcache_cynosure_site", None)
    facts["ashcache_cynosure_plate"] = 1
    facts["ashcache_cynosure_port"] = 1
    return [("shaft head: worked", facts)]


def main():
    nodes, adj, root, scenefacts = load()
    if not scenefacts:
        raise SystemExit("replaytest: found no scene entry points - the scene "
                         "guards would go untested and pass by default")
    states = playthrough(nodes, adj, root, scenefacts)
    side = [n for n, d in nodes.items() if d["type"] in SIDE_EFFECT]
    fails = []

    # ---- A. a fresh playthrough still does everything ---------------------
    # Each forward walk is one live step: the player trips a trigger, the graph
    # advances. Summed over the run, every side-effect node must fire ONCE.
    # Zero means a guard is stuck shut and the quest is broken; more than one
    # means it is not guarding.
    print("A. fresh playthrough - each side effect must happen exactly once\n")
    live = {n: 0 for n in side}
    for _, _, fired in states:
        for n in fired:
            if n in live:
                live[n] += 1
    base = {n for _, _, fired in states for n in fired}
    # Everything any walk so far has already been credited for. Each extra walk
    # replays the quest from the root to get where it is going, so without this
    # the later ones would re-credit the earlier ones' side effects and a correct
    # graph would report "fires 3x".
    covered = set(base)
    # The four ending walks are four counterfactuals of ONE save - the player
    # takes exactly one - so a node downstream of the point where the four
    # converge is reached by all four and summing them reports "fires 4x" for a
    # graph that is correct. D124's holocall is the first such node.
    #
    # The blanket fix (credit everything once, like the two loops below) was
    # wrong: it would also silence a guard that is SUPPOSED to read the ending
    # and has quietly stopped, which is the exact defect this loop exists to
    # find. So the graph says which nodes mean it, and only those are exempt.
    # Anything else reaching all four endings still reports 4x and still fails.
    every_ending = {n for n, d in nodes.items() if d.get("every_ending")}
    for label, facts in endings(states[-1][0]):
        fired, _ = walk(nodes, adj, root, dict(facts), scenefacts)
        for n in fired:
            if n in live and not (n in every_ending and n in covered):
                live[n] += 1
        covered |= set(fired)
    # The disposition walks re-open Mara's scene guard to get past it (see
    # dispositions()), so they necessarily replay the conversation itself. Credit
    # only what the ordinary playthrough could not reach - the branch behind her
    # hub - or meet_mara would count three times for a graph that is correct.
    for label, facts in dispositions(states[-1][0]):
        fired, _ = walk(nodes, adj, root, dict(facts), scenefacts)
        for n in fired:
            if n in live and n not in base:
                live[n] += 1
        covered |= set(fired)
    # The aftermath walks run the whole quest AND an ending AND the landfill, so
    # they overlap everything above; credit them only for what nothing else could
    # reach, which is the one coroner's note each.
    for label, facts in aftermath(states[-1][0]):
        fired, _ = walk(nodes, adj, root, dict(facts), scenefacts)
        for n in fired:
            if n in live and n not in covered:
                live[n] += 1
        covered |= set(fired)
    # The shaft head is optional twice over: the objective is optional, and so
    # is each thing on the site. Same credit rule as the aftermath walks.
    for label, facts in site(states[-1][0]):
        fired, _ = walk(nodes, adj, root, dict(facts), scenefacts)
        for n in fired:
            if n in live and n not in covered:
                live[n] += 1
        covered |= set(fired)
    for n in sorted(side, key=lambda n: (live[n] != 1, n)):
        verdict = "ok" if live[n] == 1 else ("NEVER FIRES" if live[n] == 0
                                             else f"fires {live[n]}x")
        if live[n] != 1:
            fails.append(f"{n}: fires {live[n]}x in a fresh playthrough, want 1")
        print(f"   {nodes[n]['type']:9} {n:20} {verdict}")
    # The tier nodes hang off a scene's Default INT/RET nets, which a normal
    # completion never takes, so they are expected to be unreached here.
    expected_quiet = {n for n in side if nodes[n]["type"] == "set_tier"}
    fails = [f for f in fails if f.split(":")[0] not in expected_quiet]

    # ---- B. a re-entry repeats nothing ------------------------------------
    print("\nB. re-entry on that save - must fire no side effect at all\n")
    cases = [(b[0] if b else "<quest complete>", f) for f, b, _ in states]
    for label, facts in (endings(states[-1][0]) + dispositions(states[-1][0])
                         + aftermath(states[-1][0]) + site(states[-1][0])):
        # Walk once to bank what the ending itself sets, then re-enter on top.
        after = dict(facts)
        walk(nodes, adj, root, after, scenefacts)
        cases.append((label + ", replayed", after))
    for label, facts in cases:
        fired, _ = walk(nodes, adj, root, dict(facts), scenefacts)
        hits = [n for n in fired if n in live]
        if hits:
            fails.append(f"{label}: re-entry fires {', '.join(hits)}")
        print(f"   {label:28} {len(hits):2}  {', '.join(hits) if hits else '-'}")

    print()
    if fails:
        print(f"FAIL ({len(fails)}):")
        for f in fails:
            print("   " + f)
        return 1
    print("OK: every side effect happens exactly once on a fresh run, and a "
          "re-entry repeats none of them.\n    A phase_revision bump re-activates "
          "the journal without duplicate items or replayed scenes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
