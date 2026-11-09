#!/usr/bin/env python3
"""What the game said about us last launch. READ-ONLY on the game directory.

Rule 2 forbids writing there; this only reads, and it exists because the logs are
unusable by hand. The installed mod set produces 2,145 error lines in one TweakXL
log and 597 in one ArchiveXL log, none of them ours. Asking "did my quest load"
by scrolling is how you conclude the mod is broken because somebody else's
vehicle pack has an unknown property.

So this greps five log families for our identifiers only, and then turns
ArchiveXL's own vocabulary into a verdict per layer. ArchiveXL announces exactly
the four merges the mod depends on, which is far better evidence than anything
the panel can infer from inside the game:

    [QuestPhase]    Merged phase "..." from "ashcache.archive.xl".
    [Journal]       Merging entries from "mod\\ash_cache\\journal\\...".
    [Localization]  Merging entries from "...\\localization\\ua-ua\\...".
    [WorldStreaming] Merging streaming block / Patching sector ...

A missing announcement is as informative as an error: no [QuestPhase] line for us
means the .xl never named the phase, not that the phase failed.

Pairs with the CET panel (tools/gen_cet.py). The panel says what the running game
believes; this says what the loaders did on the way in. When they disagree, the
loader is right and something is stale - which is why both carry the same source
hash, and why this compares them.

    python3 tools/collect_logs.py           verdicts and our lines
    python3 tools/collect_logs.py --full    every matching line, untruncated
"""
import hashlib
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAME = pathlib.Path("/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game")

# Everything the mod puts on disk, and where. Kept in one place because a
# half-deploy - archive copied, loose files forgotten - is the single most common
# way for the quest to be "installed" and inert, and the panel cannot see it: a
# missing r6/tweaks looks exactly like a TweakXL parse error from inside the game.
DEPLOY = [
    ("archive",  "archive/pc/mod/ashcache.archive",              "mod/archive/pc/mod/ashcache.archive"),
    ("manifest", "archive/pc/mod/ashcache.archive.xl",           "mod/archive/pc/mod/ashcache.archive.xl"),
    ("tweaks",   "r6/tweaks/ash_cache.yaml",                     "mod/r6/tweaks/ash_cache.yaml"),
    ("glue",     "r6/scripts/AshCache/AshCacheGlue.reds",        "mod/r6/scripts/AshCache/AshCacheGlue.reds"),
    ("cet",      "bin/x64/plugins/cyber_engine_tweaks/mods/ash_cache_debug/init.lua",
                 "dev/cet/ash_cache_debug/init.lua"),
]

# (label, directory, filename glob). Newest file wins - every one of these rotates
# per launch, so "newest" means "last time the game ran".
LOGS = [
    ("archivexl", "red4ext/plugins/ArchiveXL", "ArchiveXL-*.log"),
    ("tweakxl",   "red4ext/plugins/TweakXL",   "TweakXL-*.log"),
    ("redscript", "r6/logs",                   "redscript_rCURRENT.log"),
    ("cet",       "bin/x64/plugins/cyber_engine_tweaks", "scripting.log"),
    ("red4ext",   "red4ext/logs",              "red4ext-*.log"),
]

OURS = re.compile(r"ash_?cache", re.I)

# ArchiveXL says these on success. Absence is a finding, so each carries the
# sentence to print when it never appeared.
MERGES = [
    ("questphase", re.compile(r"\[QuestPhase\].*(Merged|Patching)", re.I),
     "the .questphase was never merged - ashcache.archive.xl did not name it, or "
     "the archive it points into is not there"),
    ("journal", re.compile(r"\[Journal\]", re.I),
     "the .journal was never merged - no quest entry, no objectives, no map pins"),
    ("localization", re.compile(r"\[Localization\]", re.I),
     "no locale merge - every line will render as its own LocKey number"),
    ("sectors", re.compile(r"\[WorldStreaming\]", re.I),
     "no streaming block or sector patch - markers, triggers and spawners are absent"),
]

BAD = re.compile(r"\[(error|warning)\]", re.I)


def source_stamp():
    """Same hash tools/gen_cet.py bakes into the panel. Kept identical on purpose."""
    h = hashlib.sha1()
    for path in sorted((ROOT / "source").glob("*.json")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:8]


def newest(directory, pattern):
    d = GAME / directory
    if not d.is_dir():
        return None
    files = sorted(d.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def stamp(path):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime))


def deploy_state():
    print("== deployed ==")
    live = 0
    for label, rel, built in DEPLOY:
        there = GAME / rel
        here = ROOT / built
        if not here.exists():
            print(f"  {label:<9} not built    {built}")
        elif not there.exists():
            print(f"  {label:<9} NOT THERE    {rel}")
        else:
            live += 1
            same = there.read_bytes() == here.read_bytes()
            print(f"  {label:<9} {'deployed ' if same else 'DIFFERS  '}   "
                  f"{stamp(there)}  {rel}")
    if live == 0:
        print("  nothing is deployed - the logs below cannot mention us")
    elif live < len(DEPLOY):
        print(f"  {len(DEPLOY) - live} piece(s) missing. A half deploy loads and "
              f"does nothing, which reads exactly like a broken build.")
    print()
    return live


def panel_report():
    """The last report the in-game panel wrote, if the tester wrote one.

    This is the only channel that runs the other way - the game telling us what it
    saw - so it is worth reading before the logs. Its build line says whether the
    session being reported was even running this source.
    """
    path = (GAME / "bin/x64/plugins/cyber_engine_tweaks/mods/ash_cache_debug/report.txt")
    if not path.exists():
        return
    print("== panel report ==")
    print(f"  {path}")
    print(f"  written {stamp(path)}")
    text = path.read_text(encoding="utf-8", errors="replace")
    here = source_stamp()
    m = re.search(r"^build\s+(.*?)\s+source\s+(\w+)", text, re.M)
    if m and m.group(2) != here:
        print(f"  STALE: the report is from source {m.group(2)}, this tree is {here}. "
              f"Everything in it describes a different build.")
    elif m:
        print(f"  source {m.group(2)} - matches this tree")
    for line in text.splitlines():
        if line.startswith("  [XX]") or line.startswith("  [ok]"):
            print("  " + line.strip())
    print()


def scan(full):
    print("== last launch ==")
    found = {}
    for label, directory, pattern in LOGS:
        path = newest(directory, pattern)
        found[label] = path
        print(f"  {label:<10} {stamp(path) + '  ' + path.name if path else 'no log found'}")
    print()

    print("== lines naming us ==")
    total = 0
    for label, _, _ in LOGS:
        path = found[label]
        if not path:
            continue
        hits = [l.rstrip() for l in
                path.read_text(encoding="utf-8", errors="replace").splitlines()
                if OURS.search(l)]
        total += len(hits)
        if not hits:
            print(f"  {label}: nothing")
            continue
        print(f"  {label}: {len(hits)} line(s)")
        show = hits if full else hits[:20]
        for l in show:
            # The timestamp and thread id are the same on every line of a launch
            # and eat half the terminal width.
            print("    " + re.sub(r"^\[[^]]*\] \[\d+\] ", "", l)[:200])
        if len(show) < len(hits):
            print(f"    ... {len(hits) - len(show)} more (--full)")
    if total == 0:
        print("  no log mentions the mod at all. Either it is not deployed, or the "
              "game has not been launched since it was.")
    print()

    axl = found.get("archivexl")
    if axl:
        print("== archivexl verdicts ==")
        lines = [l for l in axl.read_text(encoding="utf-8", errors="replace").splitlines()
                 if OURS.search(l)]
        for name, pattern, absent in MERGES:
            ours = [l for l in lines if pattern.search(l)]
            bad = [l for l in ours if BAD.search(l)]
            if not ours:
                print(f"  XX {name:<13} {absent}")
            elif bad:
                print(f"  XX {name:<13} {len(ours)} line(s), {len(bad)} not clean:")
                for l in bad[:6]:
                    print("       " + re.sub(r"^\[[^]]*\] \[\d+\] ", "", l)[:180])
            else:
                print(f"  ok {name:<13} {len(ours)} line(s), clean")
        print()

    red = found.get("redscript")
    if red:
        text = red.read_text(encoding="utf-8", errors="replace")
        print("== redscript ==")
        if "Compilation complete" in text:
            print("  ok compilation complete - the glue is in final.redscripts.modded")
        else:
            print("  XX no 'Compilation complete' in the log. If redscript fails the "
                  "whole game falls back to vanilla scripts and NO mod's redscript runs.")
        ours = [l for l in text.splitlines() if OURS.search(l)]
        for l in ours[:20] if not full else ours:
            print("    " + l[:200])
        print()


def main():
    full = "--full" in sys.argv
    if not GAME.is_dir():
        sys.exit(f"game not found at {GAME}")
    print(f"source {source_stamp()}   game {GAME}\n")
    deploy_state()
    panel_report()
    scan(full)


if __name__ == "__main__":
    main()
