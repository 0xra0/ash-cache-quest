#!/usr/bin/env python3
"""The second delivery route for the same recordings: an Audioware sound bank.

WHY THERE ARE TWO
-----------------
gen_vomap.py wires vo/<locale>/*.wem into locVoiceoverMap, which is how the
engine's own scene voiceover works. Every link of that chain has been verified
(D66): the .xl declares the map, ArchiveXL merges it into the en-us entry, the
player's VoiceOver setting IS en-us, all 43 stringIds are byte-equal to the
scene's locstring ruids, those same ruids already resolve the subtitle on
screen, every resPath is present in the archive, and the scene asks for voice.
Nine links, eight proven, and the ninth - the codec - is the one wav_to_wem.py's
own header flagged as unverified:

    "NOT verified: that PCM is accepted on the VOICEOVER path specifically ...
     The failure mode if it does not work is exactly today's status quo -
     a subtitle with no sound."

That is what the player reported. The PCM census that justified the gamble
sampled base\\sound\\soundbanks\\media - BANK media, resident, read as bank
data. The voiceover path is external sources streamed by resource path, and on
THAT path the score is 110,495 vanilla lines and 342 modded lines, every one of
them Vorbis, and no PCM anywhere. Writing real Wwise Vorbis needs Wwise.

WHAT THIS DOES INSTEAD
----------------------
Audioware is already installed and running on the target machine, and it takes
.wav outright. What makes it usable from a .scene rather than from glue is a
fact read off two OTHER installed mods, not off Audioware's own documentation:

  r6/scripts/shardaudioframework/shardaudioframework.reds plays a shard by
  calling ONLY the vanilla API -

      GameInstance.GetAudioSystem(GetGameInstance()).Play(StringToName(text))

  where `text` is the shard's LocKey string, e.g. "LocKey#6139". Its companion
  pack, r6/audioware/shard_audio_pack_official_english/, ships no .wem and no
  soundbank - just 6139.mp3 and a YAML `voices:` map keyed by LocKey#6139.

Two mods, two authors, one working feature. The only way that works is if
Audioware hooks the vanilla AudioSystem::Play(CName). So any vanilla caller
naming one of our keys plays one of our files - including a scnAudioEvent,
which is a scene event, not glue. gen_scene.py emits one beside every
scnDialogLineEvent (verified shape: mq029_01a_garage.scene ships two of them).

Result: the scene still owns the line, the timing and the subtitle. Audioware
only supplies the sound. Rule 1 is untouched - no quest state moves to script.

SHAPE, AND WHY THIS EXACT ONE
-----------------------------
Both proven manifest shapes were measured from installed mods:

  voices:                       voices:
    LocKey#6139:                  tt_dispatch_voiceline_premium_1:
      en-us: ./6139.mp3             en-us:
      ...18 locales                   fem: file.mp3
                                      male: file.mp3
                                      subtitle: "..."
  (shard pack, CName-by-LocKey,   (TraumaTeam, plain CName key)
   NO subtitle field at all)

We take the intersection: a plain CName key (TraumaTeam proves CName keys work),
plain per-locale files exactly as the shard pack writes them, and NO subtitle
field (the shard pack proves it is optional). Omitting `subtitle` is not a
shortcut - it is the point. The scene already renders the line, in Ukrainian,
from its own locstring. If this file also declared one, the player would read
the beat twice.

The first build of this bank wrote fem/male under each locale - same file twice,
on the reasoning that V's brain gender must not change who Mara is. That was
true and it was still wrong. Audioware reads fem/male as "this key is gendered",
and a gendered key can only be played by a caller that supplies a gender. Ours
supply none, so it refused all 43 with "Registry error: requires gender". The
shape below is the shard pack's, because the shard pack is the one installed
bank played by the same no-entity Play(CName) this quest uses. See D70.

Every locale maps to the same en-us file, exactly as the shard pack maps 18
locales to one mp3. D42 ships English audio under Ukrainian text on purpose,
and doing it here means Audioware's locale pick can never be the thing that
goes quiet.

NOT VERIFIED, and say so (rule 8): that a scnAudioEvent's audioEventName
reaches the same hooked AudioSystem::Play that shardaudioframework's does. The
scene event type is verified vanilla; Audioware's hook is verified by two
shipped mods; that those two meet is the inference this build tests. The CET
debug panel gets a button that calls the vanilla Play() directly on one of
these keys, which separates the two halves: button silent = Audioware or this
manifest; button speaks but Mara does not = the scene event.

That test ran on 2026-09-09 and returned the second answer.

TWO SECTIONS, TWO REGISTRIES
This file writes `voices:` and `dialogs:`, and they are not alternatives.
Audioware keeps them in separate registries and reports them separately - the
log's "ids" block and its "scene ids" block. `voices:` is keyed by CName and is
what AudioSystem::Play(CName) reaches: the CET Voice button and the shard
framework. `dialogs:` is keyed by the line's CRUID and is the ONLY thing a
scene's dialogue line can reach. A build with the first and not the second
plays fine from a debug button and is silent in the scene it was made for,
with the subtitles still appearing - which is the exact bug this quest shipped
on 2026-09-09. See D71.

"""

import os
import pathlib
import json
import shutil
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_vomap
import wav_to_wem

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "audioware"

# The bank's folder name under r6/audioware/, and the manifest inside it.
BANK = "ash_cache"

# Rule 5: everything this quest names is prefixed. A CName collision with
# another mod's bank would have one of us playing the other's audio.
EVENT_PREFIX = "ash_cache_vo_"

# Read off shard_audio_pack_official_english.yml, which lists exactly these and
# points all 18 at one file. Not a guess at Audioware's locale enum - a copy of
# the list a shipped pack uses.
LOCALES = ["pl-pl", "en-us", "es-es", "fr-fr", "it-it", "de-de", "es-mx",
           "kr-kr", "zh-cn", "ru-ru", "pt-br", "jp-jp", "zh-tw", "ar-ar",
           "cz-cz", "hu-hu", "tr-tr", "th-th"]


# The ruid a line is known by everywhere else in this build: allocated once in
# source/subtitle_ids.json, baked into the .scene as
# scnscreenplayDialogLine.locstringId.ruid, used as the subtitle entry's
# stringId and as the locVoiceoverMap entry's stringId. Audioware's scene-dialog
# registry is keyed by that SAME number - see below.
SUBTITLE_IDS = ROOT / "source" / "subtitle_ids.json"

# ------------------------------------------------------------ the third route
# THE NOTES, READ ALOUD (D125)
#
# `voices:` and `dialogs:` above are the two routes a SPOKEN line can take. A
# shard takes neither, because the engine has no voiceover path to a journal
# entry at all: a gameJournalOnscreen has a title and a description and nowhere
# to hang a sound, and no scene is playing when the player opens one.
#
# What exists instead is Shard Audio Framework, installed on this machine, whose
# "Toggle Audio" button is the feature this implements against. Read what it
# actually does - r6/scripts/shardaudioframework/shardaudioframework.reds:
#
#     let text = StringToName(this.m_data.text);
#     GameInstance.GetAudioSystem(GetGameInstance()).Play(text);
#
# and `m_data.text` is set by vanilla's own ReadAction:
#
#     shardUIevent.text = entry.GetDescription();          readAction.script:18
#
# GetDescription() hands back the onscreen entry's RAW description string, not
# the localised prose - which is why the official pack is keyed "LocKey#6139".
# So the CName SAF will ask for is precisely the LocKey we already allocated for
# that shard's body, and the key is derived below from source/items.json plus
# source/lockeys.json - the same two files gen_journal.py derives the entry from.
# Nothing is written down twice, so the key cannot drift from the note.
#
# This is also why the `wanted()` switch below must not reach these entries. That
# switch exists to stop the SCENE lines doubling once the .wem are real Wwise
# Vorbis and the engine plays them itself. There is no engine route to double
# here, so a bank deleted on that reasoning would take the narration with it and
# the button would go quiet for a reason unrelated to anything it does.
NARRATION = ROOT / "narration"


def ruids():
    """key -> the line's locstring ruid, as a decimal string.

    Entries whose name starts with "_" are the file's own comment fields.
    """
    d = json.loads(SUBTITLE_IDS.read_text(encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def event_name(key):
    """The CName a scnAudioEvent names to play line `key`.

    `key` is "<scene>.<line>", the same key gen_vomap.split_stem() produces and
    the same one vo/ names its files with. The dot cannot survive into a CName
    used as a Wwise event name, so it becomes an underscore.

    This rule lives HERE and gen_scene.py imports it, for the reason gen_scene
    already imports split_stem from gen_vomap: a name applied in two places
    eventually means two things, and the failure that produces is silence.
    """
    return EVENT_PREFIX + key.replace(".", "_")


def sources():
    """key -> the .wav (or other source) Audioware will play, per gen_vomap's rule.

    vo/<locale>/ is the manifest, exactly as it is for the .wem path: a line has
    audio when its file is there and not before. Only VO_LOCALES are scanned, so
    this cannot start shipping a ua-ua bank the moment someone drops a file.

    The SOURCE is what goes in the bank, not the .wem beside it. Audioware reads
    ordinary audio; the .wem is the engine path's problem, and re-encoding for
    Audioware would only add a generation of loss.
    """
    found = {}
    for locale in gen_vomap.VO_LOCALES:
        d = ROOT / "vo" / locale
        if not d.is_dir():
            continue
        for f in sorted(p for p in d.iterdir() if p.is_file()):
            if f.suffix.lower() not in wav_to_wem.SOURCES:
                continue
            key, _ = gen_vomap.split_stem(f.stem)
            # Two voice tags (fem/male) can share a key. One recording is what
            # this quest has, and the first one sorted wins deterministically.
            found.setdefault(key, f)
    return found


def shard_keys():
    """onscreen entry id -> the CName Shard Audio Framework will ask for.

    See the NARRATION note above for where that CName comes from. Keyed by the
    onscreen entry and not the item id because two items, mara_autopsy_shot and
    mara_autopsy_cut, exist only to put different bodies behind the same shard -
    and it is the body that gets read.
    """
    items = json.loads((ROOT / "source" / "items.json").read_text(encoding="utf-8"))
    lockeys = {k: v for k, v in
               json.loads((ROOT / "source" / "lockeys.json").read_text(encoding="utf-8")).items()
               if not k.startswith("_")}
    out = {}
    for it in items["items"]:
        if it.get("kind") != "shard":
            continue
        entry = it["onscreen"]
        # A body with no LocKey is skipped, not fatal, and deliberately so: this
        # function is called from validate.py, which reaches that state on the way
        # to reporting it far better than here ("would open an empty reader" - the
        # shard is broken in the journal, and the missing narration is the least
        # of it). Exiting here instead replaced that message with this one and
        # took a negtest case down with it.
        if entry["body"] in lockeys:
            out[entry["entry"]] = "LocKey#%d" % lockeys[entry["body"]]
    return out


def narration():
    """CName -> the file that reads that note aloud.

    narration/<locale>/ is a drop folder on the same terms as vo/: a note has a
    voice when its file is there and not before. A file naming no shard is a
    build failure and not a warning, for the reason vo/ has the same rule - the
    cost of a typo is a button that does nothing, in a UI that shows the button
    either way, and nothing anywhere would say why.
    """
    keys = shard_keys()
    found = {}
    for locale in gen_vomap.VO_LOCALES:
        d = NARRATION / locale
        if not d.is_dir():
            continue
        for f in sorted(p for p in d.iterdir() if p.is_file()):
            if f.suffix.lower() not in wav_to_wem.SOURCES:
                sys.exit(f"gen_audioware: narration/{locale}/{f.name} is not audio "
                         f"Audioware can read ({'/'.join(sorted(wav_to_wem.SOURCES))})")
            if f.stem not in keys:
                sys.exit(f"gen_audioware: narration/{locale}/{f.name} names no shard in "
                         f"source/items.json - it would be shipped and never played. "
                         f"Known: {', '.join(sorted(keys))}")
            found.setdefault(keys[f.stem], f)
    return found


# ---------------------------------------------------------------- which route
# WHY THIS TOOL CAN NOW DECIDE TO EMIT NOTHING
#
# Audioware's dialogue detour does not REPLACE the engine's playback. Read it
# in crates/audioware/src/hooks/audio.rs:
#
#     let modded = Engine::exists_for_scene(&string_id);
#     if modded { queue::send(Command::PlaySceneDialog { .. }); }
#     // still let the engine carry on, to handle subtitle
#     let out = cb(a1, a2, a3, a4, a5, a6, a7, a8, a9);
#
# It plays its copy and then calls the original unconditionally. That is right
# for Audioware's ordinary user, whose modded line has no locVoiceoverMap entry
# at all: the call-through finds no audio and only fetches the subtitle. We are
# the exception. Since D92 the vomap entry resolves to real Wwise Vorbis, so the
# call-through plays it - and the player hears the same line twice, once through
# Audioware's mixer and once through the dialogue bus with the room's reverb on
# it. Reported 2026-09-10 as "a lot of echo in Rogue's voice", which is what a
# dry copy and a wet copy a few milliseconds apart sound like. D93.
#
# So the two routes are now mutually exclusive, and the engine's own is primary:
# it gets 3D placement on the speaker, per-space reverb (vo_polish.py ships the
# renders dry precisely so Wwise can apply it once), music ducking, and it is
# the only path lipsync can hang off. The bank stays as the fallback for a
# machine that cannot make Vorbis, which is the same shape as wwise_wem.py ->
# wav_to_wem.py in build.sh.

WWISE_VORBIS = 0xFFFF


def fmt_tag(wem):
    """wFormatTag out of a RIFF header, or None if this is not one.

    Same field validate.py names in its CODECS table. A .wem is a RIFF: "RIFF",
    size, "WAVE", "fmt ", size, then the tag. 0xFFFF is Wwise Vorbis; 0xFFFE is
    the PCM wav_to_wem.py writes when there is no Wwise to write the real thing.
    """
    with wem.open("rb") as fh:
        head = fh.read(22)
    if len(head) < 22 or head[:4] != b"RIFF" or head[12:16] != b"fmt ":
        return None
    return struct.unpack("<H", head[20:22])[0]


def vomap_carries_audio():
    """(bool, why) - can the ENGINE'S own voiceover path play these lines?

    Three ways it cannot, each checkable here rather than guessed at:
      - the .xl ships no vomaps block, so nothing maps a line to a file;
      - vo/ holds no .wem at all;
      - a .wem is not Wwise Vorbis, which means wav_to_wem.py wrote it because
        this machine has no Wwise. PCM on the voiceover path is the silence
        this tool was written to work around in the first place.
    """
    if os.environ.get("ASHCACHE_NO_VOMAP") == "1":
        return False, "ASHCACHE_NO_VOMAP=1 - the .xl ships no vomaps block"
    wems = [f for loc in gen_vomap.VO_LOCALES
            for f in sorted((ROOT / "vo" / loc).glob("*.wem"))]
    if not wems:
        return False, "no .wem in vo/"
    bad = [f for f in wems if fmt_tag(f) != WWISE_VORBIS]
    if bad:
        return False, (f"{len(bad)}/{len(wems)} .wem are not Wwise Vorbis "
                       f"(first: {bad[0].name}) - no Wwise on this machine")
    return True, f"{len(wems)} Wwise Vorbis .wem"


def wanted():
    """(bool, why) - should a bank be written at all?

    ASHCACHE_AUDIOWARE=1 forces it back on regardless, which is what makes a
    one-thing-moved A/B possible: build once each way and the only difference
    is which route carries the sound.
    """
    if os.environ.get("ASHCACHE_AUDIOWARE") == "1":
        return True, "ASHCACHE_AUDIOWARE=1 - forced"
    carries, why = vomap_carries_audio()
    if carries:
        return False, why
    return True, why


def main():
    files = sources()
    notes = narration()
    on, why = wanted()
    if not on:
        # The spoken lines drop out, the notes do not. This switch is about ONE
        # failure - a line played twice, once by the engine and once by the bank -
        # and a shard cannot have it, because the engine will never read a journal
        # entry aloud. Dropping the whole bank here would silence the notes for a
        # reason that has nothing to do with them.
        print(f"gen_audioware: scene lines left to the engine ({why}). "
              f"ASHCACHE_AUDIOWARE=1 puts them back.")
        files = {}
    if not files and not notes:
        # Same contract as gen_vomap: emit nothing rather than a bank naming
        # files that are not there. A missing bank is a silent quest; a bank
        # full of missing files is a mod that fails to load.
        #
        # Removed, not merely left unwritten. A bank already sitting in
        # build/audioware would be copied to the game by build.sh and would go
        # on doubling every line - the failure the switch above exists to end.
        if OUT.is_dir():
            shutil.rmtree(OUT)
        print("gen_audioware: no audio sources - no bank written")
        return
    clash = set(f.name for f in files.values()) & set(f.name for f in notes.values())
    if clash:
        sys.exit(f"gen_audioware: {', '.join(sorted(clash))} is the filename of both a "
                 f"spoken line and a note - one would overwrite the other in the bank")

    if OUT.is_dir():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    lines = [
        "# GENERATED by tools/gen_audioware.py - do not edit.",
        "# Drop-in for r6/audioware/%s/. See the tool's header for why this" % BANK,
        "# exists alongside the locVoiceoverMap, and what it is verified against.",
        "version: 1.0.0",
        "voices:",
    ]
    for key, src in sorted(files.items()):
        shutil.copy2(src, OUT / src.name)
        lines.append("  %s:" % event_name(key))
        for loc in LOCALES:
            # PLAIN, not fem/male. Audioware rejected every gendered key on
            # 2026-09-09 with, verbatim:
            #     cannot play sound: Registry error: requires gender:
            #     ash_cache_vo_decision_dec_absorb_1
            # A gendered entry is only playable by a caller that hands the
            # registry a gender. Neither caller this quest has does: the CET
            # panel and shardaudioframework both use the bare
            # AudioSystem::Play(CName), and a scnAudioEvent names an event with
            # no speaker gender attached. The shard pack is the proof of shape -
            # it is the one installed bank driven by that same no-entity call,
            # and every entry in it is plain. One take is still one take; the
            # file on disk is identical either way. See D70.
            lines.append("    %s: %s" % (loc, src.name))
        lines.append("    settings:")
        lines.append("      volume: 1.0")

    # The notes, in the same registry and for the same reason: AudioSystem::Play
    # takes a CName and does not care who allocated it. The only difference is
    # that this CName was allocated by the journal rather than by us, so it is
    # NOT ash_cache_-prefixed - "LocKey#77315028" is the name the game itself
    # will ask for, and a prefixed variant of it would be a name nobody says.
    # Rule 5 is satisfied a stronger way here: the number comes out of this
    # quest's own reserved LocKey block, so no other mod can be holding it.
    for cname_, src in sorted(notes.items()):
        shutil.copy2(src, OUT / src.name)
        lines.append("  %s:" % cname_)
        for loc in LOCALES:
            lines.append("    %s: %s" % (loc, src.name))
        lines.append("    settings:")
        lines.append("      volume: 1.0")

    # ------------------------------------------------------------------ dialogs
    # THE SCENE PATH. `voices:` above is a second, unrelated registry: Audioware
    # logs the two separately as "ids" and "scene ids", and only the first is
    # reachable by AudioSystem::Play(CName). On 2026-09-09 the bank registered
    # 842 ids and 0 scene ids, and the result in game was exactly that split -
    # the CET Voice button spoke, and Mara's scene showed subtitles in silence.
    #
    # A scnAudioEvent was never the door. Audioware hooks the engine's
    # audio::PlayDialogLine and keys off DialogLineEventData.string_id, the
    # line's CRUID - crates/audioware/src/hooks/audio.rs:83, whose next comment
    # reads "still let the engine carry on, to handle subtitle". That single
    # line predicts the observed symptom precisely: the subtitle is drawn by the
    # engine's own path, which always runs, and the voice only happens when the
    # CRUID is registered here.
    #
    # The CRUID is the ruid we already allocate. book/pages/SCENE_DIALOG_LINES.md:
    # "you can notice the stringId ... is the same as the one defined for the
    # Voice". So this section needs nothing new invented - it is the contents of
    # source/subtitle_ids.json pointed at the files the voices: block just copied.
    #
    # Shape is the single-inline form: one plain path per locale. Verified twice
    # over - crates/manifest/src/de/dialog.rs's own doc tests, and the one
    # installed bank that ships a dialogs: section, sonoraapex, whose 2 keys x 11
    # locales are precisely the "scene ids -> 22" this machine reported.
    #
    # This ALSO makes the .wem's codec a non-issue on the voice path. Our .wem is
    # PCM, and tools/wav_to_wem.py says under rule 8 that PCM is NOT verified on
    # the voiceover path. Audioware decodes the source itself, so the .wem only
    # has to exist for the engine to raise the dialogue line (and, later, lipsync).
    alloc = ruids()
    dialog = [(alloc[key], src) for key, src in sorted(files.items()) if key in alloc]
    missing = sorted(k for k in files if k not in alloc)
    if missing:
        sys.exit("gen_audioware: no subtitle id for %s - run tools/alloc_subtitle_ids.py"
                 % ", ".join(missing))
    # Only when there is something under it. A bare "dialogs:" is YAML null, not
    # an empty map, and a bank that fails to parse takes the notes down with it -
    # which is the case a notes-only build is.
    if dialog:
        lines.append("dialogs:")
        for ruid, src in sorted(dialog, key=lambda x: int(x[0])):
            lines.append("  %s:" % ruid)
            for loc in LOCALES:
                lines.append("    %s: %s" % (loc, src.name))

    (OUT / f"{BANK}.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"gen_audioware: {len(files)} line(s) x {len(LOCALES)} locale(s), "
          f"{len(dialog)} scene dialog(s), {len(notes)}/{len(shard_keys())} note(s) "
          f"read aloud -> build/audioware/{BANK}.yml")


if __name__ == "__main__":
    main()
