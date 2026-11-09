#!/usr/bin/env python3
"""lipsync/<locale>/<character>.anims  ->  build/lipmap_<locale>.lipmap.json

The FOURTH per-locale resource, after onscreens, subtitles and the voiceover map.
It is what makes a speaking NPC's mouth move. Without it a voiced line plays over
a face frozen in its idle - which is worse than silence, because it reads as a
broken NPC rather than as a missing feature.

THE BINDING CHAIN, verified end to end on one vanilla line
Four resources and three different keys have to agree. Getting any one of them
wrong produces a map that loads, merges, logs success, and animates nobody:

    .scene   scnActorDef.voicetagId.id                     WHO is speaking
    .lipmap  scenePaths[i]      = FNV1a64(scene depot path) WHICH scene
    .lipmap  sceneEntries[i].actorVoiceTags[j]              who, again
    .lipmap  sceneEntries[i].animSets[j]  -> that actor's .anims   their mouth
    .scene   screenplayDialogLine.femaleLipsyncAnimationName = f_<ruid:016X>
    .anims   animations[k].name           = f_194725D45D49D000     the take

Proven against base\\quest\\minor_quests\\mq029\\scenes\\mq029_01a_garage.scene:
its FNV1a64 is 3647272176032198475, which is scenePaths[706] of
base\\localization\\en-us.lipmap; entry 706's actorVoiceTags is exactly the one
voicetagId the scene gives its `johnny` actor (1103967280742240508); its
animSets[0] is that scene's johnny.anims; and that animset holds an animation
named f_194725D45D49D000, whose hex IS the line's locstringId.ruid.

The key is the VOICETAG, one level above the line. My first guess was that the
entry keyed off the same locstring id locVoLineEntry uses - it does not. The
line-level key lives inside the animset, as the animation's name.

WHY THE ARRAYS ARE BUILT TOGETHER
ArchiveXL merges this by hooking Localization_LoadLipsyncs, and
LocalizationExtension::MergeLipsyncResource opens with

    if (aSource->scenePaths.Size() != aSource->sceneEntries.Size())
        return false;

- the WHOLE resource is dropped, not the odd entry, and the same holds for
actorVoiceTags against animSets. All 3495 vanilla entries satisfy it. So the two
arrays are never built in separate passes here: one loop appends to both or to
neither.

Ordering is not load-bearing. The merge does a std::lower_bound over the TARGET's
scenePaths, which vanilla has sorted; ours are sorted anyway so a diff of this
file is stable, but Kidnap ships an UNSORTED array and works.

WHY THE DROP FOLDER DECIDES, AND NOT A LIST
Same reason as gen_vomap.py: an animset named in the map but absent from the
archive is a dangling raRef, which is silent. So the files on disk are the
manifest. Drop lipsync/en-us/mara.anims and rebuild; that is the whole edit.

    lipsync/en-us/mara.anims   ->  mod\\ash_cache\\localization\\en-us\\lipsync\\mara.anims

One animset per character per locale, holding every line that character says
anywhere - Kidnap's layout (its johnny.anims serves 5 scenes with 9 animations),
not vanilla's per-scene-per-character layout. Both work: the map hands the engine
an animset and the engine looks up a name in it, so a character's whole corpus
in one file costs nothing and keeps the map small.

MAKING THE .anims IS NOT SOLVED - see OI-17
This generator produces a correct map for animsets that exist. Authoring the
animset itself (animAnimSet: a rig, opaque animationDataChunks, and one
animAnimationBufferCompressed per take at 344 joints / 414 tracks,
AdditiveFromRefPose) has no offline tool here and is NOT verified. Rule 8: that
step is a TODO, and until it is done this file writes nothing at all.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import cname, envelope, respath
from gen_vomap import VO_LOCALES

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = "mod\\ash_cache"


def fnv1a64(s):
    """The engine's ResourcePath hash. Lowercase, backslash-separated, no drive.

    Verified: this returns 3647272176032198475 for
    base\\quest\\minor_quests\\mq029\\scenes\\mq029_01a_garage.scene, which is the
    number sitting in vanilla's own scenePaths for that scene.
    """
    h = 0xCBF29CE484222325
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def scene_depot_path(stem):
    """Where build.sh actually packs a scene. Hashed, so it has to be the real one.

    tools/build.sh step 5 copies build/tree/ash_cache_<stem>.scene into
    $S/mod/ash_cache/quest/. A change there without a change here does not fail
    the build - it produces a hash that matches no scene, and the mouth simply
    never moves. tools/validate.py::check_lipsync re-derives this independently.
    """
    return f"{RES}\\quest\\ash_cache_{stem}.scene"


def animset_depot_path(locale, char_id):
    return f"{RES}\\localization\\{locale}\\lipsync\\{char_id}.anims"


def collect(locale, cast):
    """(character id -> filename) for every animset present in this locale.

    A file whose stem names nobody in any scene's cast is fatal, not ignored: it
    is the same mistake as a missing one and fails just as quietly in game.
    """
    src = ROOT / "lipsync" / locale
    if not src.is_dir():
        return {}
    found, stray = {}, []
    for anims in sorted(src.glob("*.anims")):
        cid = anims.name[: -len(".anims")]
        if cid not in cast:
            stray.append(anims.name)
            continue
        found[cid] = anims.name
    if stray:
        sys.exit(f"lipsync/{locale}/ has {len(stray)} animset(s) naming nobody in any "
                 f"scene's cast: {', '.join(stray[:4])}\n"
                 f"  cast across all scenes: {', '.join(sorted(cast)) or '(none)'}")
    return found


def main():
    chars = json.loads((ROOT / "source" / "characters.json").read_text(encoding="utf-8"))
    known = {c["id"] for c in chars["characters"]}
    voicetags = json.loads((ROOT / "source" / "voicetags.json").read_text(encoding="utf-8"))
    voicetags.pop("_comment", None)

    # scene stem -> its NPC cast, in the order the scene lists them. The player is
    # deliberately absent: V keeps voicetagId 0 and no lipsync animset for the
    # player exists anywhere in the game (0 of 5688 shipped ones name V), because
    # V is normally seen from the inside.
    scenes = {}
    for path in sorted((ROOT / "source").glob("scene_*.json")):
        stem = path.stem[len("scene_"):]
        scene = json.loads(path.read_text(encoding="utf-8"))
        scenes[stem] = [cid for cid in scene.get("actors", []) if cid in known]
    cast = {cid for actors in scenes.values() for cid in actors}

    outdir = ROOT / "build"
    outdir.mkdir(parents=True, exist_ok=True)
    wrote = {}

    for locale in VO_LOCALES:
        have = collect(locale, cast)
        out = outdir / f"lipmap_{locale}.lipmap.json"
        if not have:
            # Same reason gen_vomap.py unlinks: build.sh only clears build/tree, so
            # a map left behind after the last animset is removed keeps converting,
            # keeps packing, and keeps naming files that are no longer copied in.
            out.unlink(missing_ok=True)
            continue

        for cid in sorted(have):
            if cid not in voicetags:
                sys.exit(f"character {cid!r} has an animset but no voicetag - "
                         f"run tools/alloc_voicetags.py")

        rows = []
        for stem, actors in scenes.items():
            speaking = [cid for cid in actors if cid in have]
            if not speaking:
                continue
            # One loop, both arrays. MergeLipsyncResource drops the entire resource
            # if these two ever differ in length, so they are never built apart.
            tags, sets = [], []
            for cid in speaking:
                tags.append(str(voicetags[cid]))
                sets.append(respath(animset_depot_path(locale, cid), flags="Soft"))
            rows.append((fnv1a64(scene_depot_path(stem)),
                         {"$type": "animLipsyncMappingSceneEntry",
                          "actorVoiceTags": tags, "animSets": sets},
                         stem, speaking))
        if not rows:
            out.unlink(missing_ok=True)
            continue
        rows.sort(key=lambda r: r[0])

        root = {"$type": "animLipsyncMapping",
                "cookingPlatform": "PLATFORM_PC",
                "languageCodeName": cname(locale),
                "scenePaths": [str(h) for h, _, _, _ in rows],
                "sceneEntries": [e for _, e, _, _ in rows],
                # Vanilla carries one preview path per entry; Kidnap ships this
                # empty and works. It is not in the runtime struct at all
                # (RED4ext.SDK's animLipsyncMapping has three fields, and Ordinal 3
                # is a hole in WolvenKit's class too), so it is editor-only
                # metadata that survives cooking. Empty is the verified choice.
                "scenePreviewPaths": []}
        out.write_text(json.dumps(envelope(root, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        wrote[locale] = rows
        detail = "; ".join(f"{stem}: {', '.join(who)}" for _, _, stem, who in rows)
        print(f"wrote {out.relative_to(ROOT)}  ({len(rows)} scene(s) - {detail})")

    if not wrote:
        n = sum(len(a) for a in scenes.values())
        print(f"no lipsync: lipsync/<locale>/ holds no .anims yet "
              f"({n} speaking actor slot(s) across {len(scenes)} scene(s) will "
              f"animate no mouth) - see OI-17")


if __name__ == "__main__":
    main()
