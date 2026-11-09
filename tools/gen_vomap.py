#!/usr/bin/env python3
"""vo/<locale>/*.wem  ->  build/vomap_<locale>.json.json  (locVoiceoverMap)

Spoken audio is a THIRD resource per locale, beside the two gen_subtitles.py
writes. All three key off the same locstring ruid that gen_scene.py bakes into
the .scene, so a line's text, its translation and its audio can never drift:

    .scene   scnscreenplayDialogLine.locstringId.ruid
    .xl  localization.subtitles.<locale>  -> the words
    .xl  localization.vomaps.<locale>     -> the audio      <- this file

The 'vomaps' key is ArchiveXL's, verified in its source rather than guessed:
src/App/Extensions/Localization/Config.cpp:10 defines VoiceOverMapsNodeKey, and
Extension.cpp hooks Localization::LoadVoiceOvers to merge ours into the game's
index. Shape confirmed against a shipped mod - AldecaldosHighStakes ships
locVoiceoverMap with locVoLineEntry{stringId, femaleResPath, maleResPath}.

femaleResPath / maleResPath are the PLAYER's gender, not the speaker's. Mara says
the same words to either V, so one file serves both - which is what High Stakes
does for every NPC line it ships. Only V's own lines need a split, and only if
two different V voices were actually recorded.

WHY THE DROP FOLDER DECIDES, AND NOT A LIST
An entry whose .wem is not in the archive is the project's usual silent failure:
the scene plays, the subtitle appears, and there is simply no sound. Nothing logs
it. So the files on disk ARE the manifest - a line gets an entry when, and only
when, its audio exists. Adding voice to a line is one file drop and a rebuild,
with nowhere else to remember to edit.

    vo/en-us/mara.mara_open_1.wem      one file, both Vs
    vo/en-us/mara.mara_open_1.f.wem    split, female V
    vo/en-us/mara.mara_open_1.m.wem    split, male V

The stem is the same "<scene>.<line id>" key as source/subtitle_ids.json, so a
misnamed file is caught here instead of going quiet in game.

Making the .wem itself needs Wwise 2023.1.14 - see docs/voiceover.md.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import H, envelope

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The VOICE locales, which are deliberately NOT the text locales. ua-ua is a real
# translation and keeps its subtitles, onscreens and journal entries - but it has
# no audio of its own, so a Ukrainian player reads Ukrainian and hears English,
# exactly as they do in vanilla. Two independent reasons, either one sufficient:
# the game ships no lang_ua_voice.archive for ArchiveXL to merge into, and the
# RVC targets learned their phonetics from English-only recordings and cannot
# say Ukrainian without an accent. See docs/decisions.md D42.
#
# Every voice-side tool imports this rather than keeping its own copy, so adding
# a voice language later is one edit, here.
VO_LOCALES = ["en-us"]
RES = "mod\\ash_cache\\localization"


def res_path(locale, name):
    return {"DepotPath": {"$type": "ResourcePath", "$storage": "string",
                          "$value": f"{RES}\\{locale}\\vo\\{name}"},
            "Flags": "Soft"}


def split_stem(stem):
    """'mara.mara_open_1.f' -> ('mara.mara_open_1', 'f').

    Lives here because gen_vomap owns the naming rule, and wav_to_wem.py has to
    apply exactly the same one before it writes a .wem - a name checked in two
    places is a name that eventually means two things.
    """
    key, _, tag = stem.rpartition(".")
    if tag not in ("f", "m"):
        return stem, "both"
    return key, tag


def collect(locale, keys):
    """(key -> (female wem, male wem)) for every line with audio in this locale.

    Returns the pairs and the filenames that matched nothing, because a .wem
    dropped under a name no line uses is the same mistake as a missing one and
    fails just as quietly.
    """
    src = ROOT / "vo" / locale
    if not src.is_dir():
        return {}, []
    pairs, stray = {}, []
    for wem in sorted(src.glob("*.wem")):
        key, tag = split_stem(wem.name[: -len(".wem")])
        if key not in keys:
            stray.append(wem.name)
            continue
        f, m = pairs.get(key, (None, None))
        if tag in ("f", "both"):
            f = wem.name
        if tag in ("m", "both"):
            m = wem.name
        pairs[key] = (f, m)
    return pairs, stray


def main():
    alloc = json.loads((ROOT / "source" / "subtitle_ids.json").read_text(encoding="utf-8"))
    alloc.pop("_comment", None)

    outdir = ROOT / "build"
    outdir.mkdir(parents=True, exist_ok=True)
    wrote = {}

    for locale in VO_LOCALES:
        pairs, stray = collect(locale, alloc)
        if stray:
            sys.exit(f"vo/{locale}/ has {len(stray)} file(s) whose name is not a line "
                     f"in subtitle_ids.json: {', '.join(stray[:4])}")
        entries = []
        for key, ruid in sorted(alloc.items(), key=lambda kv: int(kv[1])):
            pair = pairs.get(key)
            if pair is None:
                continue
            female, male = pair
            # One-sided is allowed and deliberate: half the players hear nothing
            # is a worse outcome than both hearing the same take, so a missing
            # side falls back to the one that exists.
            female, male = female or male, male or female
            entries.append({"$type": "locVoLineEntry",
                            "femaleResPath": res_path(locale, female),
                            "maleResPath": res_path(locale, male),
                            "stringId": str(ruid)})
        stale = outdir / f"vomap_{locale}.json.json"
        if not entries:
            # Removing the last .wem for a locale has to remove its map too.
            # build.sh only clears build/tree, so a left-behind map would keep
            # converting, keep packing, and keep pointing at files that are no
            # longer copied in - a dangling raRef, which is silent.
            stale.unlink(missing_ok=True)
            continue
        root = {"$type": "JsonResource", "cookingPlatform": "PLATFORM_PC",
                "root": H({"$type": "locVoiceoverMap", "entries": entries})}
        out = stale
        out.write_text(json.dumps(envelope(root, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        wrote[locale] = len(entries)
        print(f"wrote {out.relative_to(ROOT)}  ({len(entries)} voiced line(s) "
              f"of {len(alloc)})")

    if not wrote:
        print(f"no voiceover: vo/<locale>/ holds no .wem yet "
              f"({len(alloc)} lines are subtitled and silent)")


if __name__ == "__main__":
    main()
