#!/usr/bin/env python3
"""What does the quest log's description field actually SAY, at every stage?

questLogDetailsPanel.script:151-171 concatenates EVERY description the journal
returns into one inkTextRef, joined with a single space - the intended "\n" is
an expression statement whose result is discarded, so it never lands. And
QuestLogUtils.GetDescriptions walks with succeeded=true, so a finished
objective's still-Active description keeps coming back.

This renders that field. It reuses replaytest's engine model, tracks journal
entry state per depot path, applies the panel's own filter, and prints the
string the player would read.

    descpanel.py [graph.json]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.argv = [sys.argv[0], sys.argv[1]] if len(sys.argv) > 1 else [sys.argv[0]]
import replaytest as R

GRAPH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "source" / "quest_graph.json"
g = json.loads(GRAPH.read_text())
nodes = {n["id"]: n for n in g["nodes"]}
strings = json.loads((ROOT / "source" / "strings.json").read_text())
journal = json.loads((ROOT / "source" / "journal.json").read_text())

# path -> the str.* key its text comes from, for both kinds of journal entry.
text_of = {}
qroot = "quests/main_quest/prologue/ash_cache"
for ph in journal["phases"]:
    for o in ph["objectives"]:
        base = f"{qroot}/{ph['id']}/{o['id']}"
        text_of[base] = o["description"]
        if o.get("summary"):
            text_of[base + "/description"] = o["summary"]

# Which socket each link enters its target through. Third element, or the
# node's default input when omitted.
entry_socket = {}
for link in g["links"]:
    src, dst = link[0], link[1]
    sock = link[2] if len(link) > 2 else None
    entry_socket.setdefault((src.partition(":")[0], dst.partition(":")[0]), sock)

DEFAULT_IN = {"journal_entry": "Active", "journal_quest": "Active"}


def journal_states(fired):
    """Replay the fired list in order, tracking every journal path's state."""
    state = {}
    order = {n: i for i, n in enumerate(fired)}
    for nid in fired:
        n = nodes[nid]
        if n["type"] not in ("journal_entry", "journal_quest"):
            continue
        sock = None
        for (s, d), k in entry_socket.items():
            if d == nid and s in order and order[s] < order[nid]:
                sock = k or DEFAULT_IN[n["type"]]
                break
        state[n["path"]] = sock or DEFAULT_IN[n["type"]]
    return state


def panel_text(state, lang):
    """GetDescriptions + the render loop, exactly as shipped.

    A description shows iff its own entry is Active AND its parent objective
    passes the quest-level filter {active, succeeded, failed} - i.e. anything
    but Inactive. That conjunction is the accumulation defect.
    """
    parts, seen, used = [], [], []
    for path, st in state.items():
        if not path.endswith("/description") or st != "Active":
            continue
        parent = state.get(path.rsplit("/", 1)[0])
        if parent in (None, "Inactive"):
            continue
        txt = strings[text_of[path].split(".", 1)[1]][lang]
        if txt in seen:
            continue
        seen.append(txt)
        parts.append(txt)
        used.append(path)
    # the join is a space, not "\n"
    return " ".join(parts), len(parts), used


def main():
    nodes_, adj, root, sf = R.load()
    states = R.playthrough(nodes_, adj, root, sf)
    cases = [(b[0] if b else "<complete>", f, fired) for f, b, fired in states]
    for label, facts in R.endings(states[-1][0]):
        fired, _ = R.walk(nodes_, adj, root, dict(facts), sf)
        cases.append((label, facts, fired))

    # Every shipped language, not just en-us. ua-ua is a real translation, and a
    # panel that fits in English can still overflow in Ukrainian.
    langs = sorted({k for v in strings.values() if isinstance(v, dict)
                   for k in v if k != "note"})

    print(f"{GRAPH.name}\n")
    worst, longest, rendered = 0, {}, set()
    for lang in langs:
        print(f"[{lang}]")
        print(f"{'parked at':30} {'#':>2}  {'chars':>5}  text")
        print("-" * 100)
        for label, facts, fired in cases:
            st = journal_states(fired)
            txt, n, used = panel_text(st, lang)
            rendered.update(used)
            worst = max(worst, n)
            longest[lang] = max(longest.get(lang, 0), len(txt))
            show = txt if len(txt) <= 58 else txt[:55] + "..."
            print(f"{label:30} {n:2}  {len(txt):5}  {show}")
        print()
    # A description that renders at no park is authored text the player may never
    # read. Two are expected: talk_mara and decide both activate immediately
    # before a scene node and retire when it ends, and the replay parks at waits,
    # not inside scenes - so this tool cannot see them either way. Reported, not
    # asserted, because the count is a property of where scenes sit in the graph.
    # A jump in this list means the quest was severed: replaytest.py is the gate
    # that catches that, and it runs first.
    never = sorted(p for p in text_of
                   if p.endswith("/description") and p not in rendered)
    if never:
        print(f"never rendered at any park ({len(never)}):")
        for pth in never:
            print(f"  {pth.split('ash_cache/')[-1]}")
    print(f"peak simultaneous descriptions: {worst}")
    print("longest field: " + ", ".join(f"{k} {v}" for k, v in sorted(longest.items())))
    return 0 if worst <= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
