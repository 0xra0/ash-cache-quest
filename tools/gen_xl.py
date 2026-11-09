#!/usr/bin/env python3
"""Emit the ArchiveXL .xl that registers everything with the engine.

Four jobs:
  streaming      - registers the block that makes the mod's world markers exist
  journal        - merges the quest entry into the game's journal tree
  localization   - points every locale at an onscreens resource
  quest.phases   - attaches the quest phase to the root quest graphs

The quest block is emitted only when the .questphase actually exists, so a
partial build still produces a loadable mod.
"""
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = "mod\\ash_cache"


def phase_resource_name(revision, built_name="ash_cache.questphase"):
    """Depot filename of the quest phase for a given source/quest_graph.json
    phase_revision.

    The revision is in the FILENAME on purpose. ArchiveXL identifies the phase
    node it synthesises in the parent quest by CRC16 of "<depot path>:<parent
    node id>", turns that id into a fact id, and on every save load force-starts
    the node only while that fact is 0 - setting it to 1 immediately afterwards
    whether or not the phase actually did anything. So a save that once loaded a
    broken build is permanently marked as having run this path. A new filename is
    a new CRC, a new node id and a new fact id, which is the only way to get a
    clean entry on that save without starting a new game. See D21.
    """
    return f"{built_name.removesuffix('.questphase')}_r{revision}.questphase"


def phase_revision(graph="quest_graph.json"):
    return json.loads((ROOT / "source" / graph).read_text(encoding="utf-8"))["phase_revision"]


# Every phase resource this mod injects: built name -> (depot name, source graph).
# They are separate resources because a phase runs only until its output node
# fires, and the quest's output node fires when the quest ends - so world state
# that has to outlive the quest needs its own. Each gets its own revision, so
# re-cutting one does not force a clean entry on the other.
QUEST_PHASE   = ("ash_cache.questphase",          "quest_graph.json")
CYNOSURE_PHASE = ("ash_cache_cynosure.questphase", "cynosure_graph.json")

# D116: with BOTH phases attached every save crashed at world load
# (WaitUntilLoaded off the main thread); with the quest phase alone, repeated
# loads were clean. The third cell of that table - the Cynosure phase ALONE -
# was never measured, and until it is, "two injected phases is the problem" and
# "the bunker prefab refs are the problem" are both still standing. D129 makes
# that cell buildable instead of theoretical:
#
#   ASHCACHE_CYNOSURE=only   inject the Cynosure phase and NOT the quest
#   ASHCACHE_CYNOSURE=both   inject both - the combination D116 measured as fatal
#   (unset)                  ship the quest phase alone, which is the shipping mod
#
# The mode also decides what tools/build.sh packs, so the experiment is one
# archive plus one manifest and nothing else moves. See docs/decisions.md D129.
_MODE = os.environ.get("ASHCACHE_CYNOSURE", "").strip().lower()
if _MODE not in ("", "only", "both"):
    raise SystemExit(f"gen_xl: ASHCACHE_CYNOSURE={_MODE!r} - expected 'only', 'both' or unset")
PHASES = {"": [QUEST_PHASE],
          "only": [CYNOSURE_PHASE],
          "both": [QUEST_PHASE, CYNOSURE_PHASE]}[_MODE]
if _MODE:
    print(f"gen_xl: ASHCACHE_CYNOSURE={_MODE} - injecting "
          + ", ".join(b for b, _ in PHASES) + "  (EXPERIMENT BUILD, not the shipping mod)")

# Every locale the game ships. en-us and ua-ua have real translations; the rest
# alias to the en-us resource so no locale renders a blank quest UI.
ALL_LOCALES = ["en-us", "ar-ar", "cz-cz", "de-de", "es-es", "es-mx", "fr-fr", "hu-hu",
               "it-it", "jp-jp", "kr-kr", "pl-pl", "pt-br", "ru-ru", "th-th", "tr-tr",
               "ua-ua", "zh-cn", "zh-tw"]
TRANSLATED = {"en-us", "ua-ua"}

# Root graphs a quest phase attaches to. ep1 covers Phantom Liberty standalone;
# the three newgameplus graphs are the NG+ mod, which is installed here.
PARENTS = [
    "base\\quest\\cyberpunk2077.quest",
    "ep1\\quest\\ep1_standalone.quest",
    "mod\\quest\\newgameplus.quest",
    "mod\\quest\\newgameplus_q001.quest",
    "mod\\quest\\newgameplus_standalone.quest",
]


def clinic_deletions():
    """D137: Farida's clinic dressing, deleted for good at sector load. ArchiveXL
    checks expectedNodes and every node's type first and skips the whole sector on
    any mismatch (a patch or another mod changed it), so a stale scan fails safe:
    the room stays vanilla. Indexes are node SETUP indexes, as the scan stores them."""
    data = json.loads((ROOT / "reference" / "clinic_hide.json").read_text(encoding="utf-8"))
    L = ["  sectors:"]
    for sec in data["sectors"]:
        if not sec.get("delete"):
            continue
        L += [f"    - path: {sec['path']}",
              f"      expectedNodes: {sec['setups']}",
              "      nodeDeletions:"]
        for e in sec["delete"]:
            L += [f"        - index: {e['i']}", f"          type: {e['cls']}"]
    # D138: their collision, which lives in separate collision nodes. ArchiveXL
    # checks expectedActors per node as well, with the same skip-on-mismatch.
    col = json.loads((ROOT / "reference" / "clinic_collision.json").read_text(encoding="utf-8"))
    for sec in col["sectors"]:
        if not sec["nodes"]:
            continue
        L += [f"    - path: {sec['path']}",
              f"      expectedNodes: {sec['setups']}",
              "      nodeDeletions:"]
        for n in sec["nodes"]:
            L += [f"        - index: {n['i']}", "          type: worldCollisionNode",
                  f"          expectedActors: {n['actors']}",
                  f"          actorDeletions: [{', '.join(str(k) for k in n['delete'])}]"]
    return L if len(L) > 1 else []


def main():
    tree = ROOT / "build" / "tree"
    lines = ["# Generated by tools/gen_xl.py - do not hand-edit.", ""]

    # Without this the mod's .streamingsector files are inert: every NodeRef the
    # journal's map pins and the scene node reference resolves to nothing, with no
    # error reported anywhere. Verified as the mechanism in both reference mods.
    if (tree / "ash_cache.streamingblock").exists():
        lines += ["streaming:", "  blocks:",
                  f"    - {RES}\\worlds\\ash_cache.streamingblock"]
        lines += clinic_deletions()
        lines.append("")
    else:
        lines += ["# streaming: omitted - build/tree/ash_cache.streamingblock not built yet", ""]

    lines += ["journal:", f"  - {RES}\\journal\\ash_cache.journal", ""]

    lines += ["localization:", "  onscreens:"]
    for loc in ALL_LOCALES:
        src = loc if loc in TRANSLATED else "en-us"
        lines.append(f"    {loc}: {RES}\\localization\\{src}\\onscreens.json")

    # Spoken scene text is a separate pipeline from onscreens: this points at the
    # subtitle MAP, which in turn points at the file holding the actual lines.
    # Emitted only once a scene exists, so a journal-only build stays loadable.
    if (tree / "ash_cache_mara.scene").exists():
        lines.append("  subtitles:")
        for loc in ALL_LOCALES:
            src = loc if loc in TRANSLATED else "en-us"
            lines.append(f"    {loc}: {RES}\\localization\\{src}\\subtitles\\ash_cache.json")

    # Voiceover. 'vomaps' is ArchiveXL's own key, not a guess: it is defined at
    # src/App/Extensions/Localization/Config.cpp:10 (VoiceOverMapsNodeKey) and
    # merged by hooking Localization::LoadVoiceOvers. Only locales that actually
    # have a map are listed - an untranslated locale must NOT fall back to en-us
    # audio the way its text does, because hearing English under Ukrainian
    # subtitles is a worse bug than hearing nothing.
    # ASHCACHE_NO_VOMAP=1 builds the control archive for the crash bisect: the
    # .wem files are still packed, but nothing in the engine resolves them, so
    # the vanilla voiceover path is never entered. Audioware is a separate path
    # and keeps working. If the crash survives this, it is not the .wem.
    voiced = [loc for loc in ALL_LOCALES if (tree / f"vomap_{loc}.json").exists()]
    if os.environ.get("ASHCACHE_NO_VOMAP") == "1":
        if voiced:
            print("gen_xl: ASHCACHE_NO_VOMAP=1 - vomaps block SUPPRESSED "
                  f"({len(voiced)} locale(s) withheld)")
        voiced = []
    if voiced:
        lines.append("  vomaps:")
        for loc in voiced:
            lines.append(f"    {loc}: {RES}\\localization\\{loc}\\vo\\ash_cache_vo.json")

    # Lipsync. 'lipmaps' is ArchiveXL's own key beside 'vomaps', defined at
    # src/App/Extensions/Localization/Config.cpp:9 (LipMapsNodeKey) and merged by
    # hooking Localization::LoadLipsyncs. Same per-locale rule as vomaps, and for
    # a sharper reason: a lipmap listed for a locale whose .anims were not packed
    # is a dangling raRef that merges, logs success and animates nobody.
    lipsynced = [loc for loc in ALL_LOCALES if (tree / f"lipmap_{loc}.lipmap").exists()]
    if lipsynced:
        lines.append("  lipmaps:")
        for loc in lipsynced:
            lines.append(f"    {loc}: {RES}\\localization\\{loc}\\lipsync.lipmap")
    lines.append("")

    # The name a phase is PACKED under is not the name it is built under -
    # build/tree keeps one stable filename so every other tool can find it, while
    # the depot path carries the revision.
    built = [(f, g) for f, g in PHASES if (tree / f).exists()]
    if built:
        lines += ["quest:", "  phases:"]
        for fname, graph in built:
            depot_name = phase_resource_name(phase_revision(graph), fname)
            for parent in PARENTS:
                lines += [f"    - path: {RES}\\quest\\{depot_name}",
                          f"      parent: {parent}"]
        lines.append("")
    else:
        lines += ["# quest: phases: omitted - no phase built yet", ""]

    out = ROOT / "mod" / "archive" / "pc" / "mod" / "ashcache.archive.xl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    subs = (tree / "ash_cache_mara.scene").exists()
    sectors = len(list(tree.glob("ash_cache_*.streamingsector")))
    print(f"wrote {out.relative_to(ROOT)}  "
          f"({len(ALL_LOCALES)} locales, {len(TRANSLATED)} translated, "
          f"quest block: {', '.join(phase_resource_name(phase_revision(g), f) for f, g in built) or 'not yet'}, "
          f"subtitles: {'yes' if subs else 'not yet'}, "
          f"sectors: {sectors})")


if __name__ == "__main__":
    main()
