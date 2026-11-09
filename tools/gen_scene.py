#!/usr/bin/env python3
"""source/scene_<name>.json  ->  build/ash_cache_<name>.scene.json

A .scene is three stores that index each other by integer id, not one graph:

  sceneGraph       flow: start -> section -> choice -> end, plus embedded quest nodes
  screenplayStore  the lines and choice options, addressed by itemId
  locStore         per-locale text EMBEDDED in the scene

This generator leaves locStore empty and ships the text as a separate subtitle
resource instead (tools/gen_subtitles.py). Both routes are real - Hot Fuzz embeds
en_us/pl_pl in its locStore, Undermine Quest Series ships an empty locStore and an
external subtitle file - and external wins here because the text then lives in one
place per locale for the whole mod rather than once per scene, and because ua-ua
is a locale the base game has no scene pipeline for anyway.

Three id schemes are not guessable and were read off the references:

  1. screenplay itemId = (index << 8) | kind, kind 1 = spoken line, 2 = choice
     option, with a separate index sequence per kind. Verified across all 22 lines
     and 4 options of Hot Fuzz.
  2. A link's destination carries no socket NAME, only {name: 0, ordinal: N} where
     N indexes the target's inputs. Scene-native nodes have one input (ordinal 0);
     an embedded scnQuestNode has [CutDestination, In] so entering it is ordinal 1.
  3. A choice node's option i leaves by the output socket whose stamp.name is i.

Almost everything animation-related is omitted deliberately: no anim events, no
workspots, no rid resources, empty animSets on every actor. The one exception is
the lipsync table, and the exception is the whole point:

  - OBSERVED: an actor with animSets: []. Hot Fuzz's Nibbles and Johnny ship that,
    so an actor carrying no animation of its own is fine.
  - OBSERVED: a wrong anim reference being tolerated. The Undermine template's
    cinematicAnimSets point at sq031_07_cinema, a completely unrelated quest it was
    cloned from, and its two lipsync paths belong to a Japantown vendor. It ships
    and works, so these references do not have to MATCH the actor.
  - OBSERVED, and the reason this generator no longer leaves lipsync unset: across
    all three reference scenes, every one of the seven actors indexes a lipsync
    entry, and the table is always exactly as long as the cast. Nibbles and Johnny
    do it with animSets: [] - so "no animation" and "no lipsync" are separate
    claims, and only the first one has a sample behind it.

An earlier draft emitted lipsyncAnimSet: 0xFFFFFFFF into an empty table on the
reasoning that it is the sentinel every OTHER unset id in this format uses. Those
are scnActorId/scnPropId/scnReferencePointId; an SRRefId is an array index, and
whether the engine sentinel-checks one before dereferencing is a claim about code
nobody here has read. Following the observed shape costs two soft references to
base-game paths and removes the question. OI-10 records what that replaced.

Actors ARE emitted now (source/characters.json). An actor is a spawn instruction:
acquisitionPlan spawnDespawn + a TweakDB character record + an appearance CName +
a spawnMarkerNodeRef naming a marker in source/world.json. V is the exception - the
player is acquired with findInContext and never spawned.

Two details of that look arbitrary until you check the references, and both would
have been wrong if assumed:

  - spawnMarkerNodeRef takes the SHORT NodeRef form. Hot Fuzz ships
    '#nq_judy_spawner' - a bare '#name', not the long '$/03_night_city/...' path
    that a quest node's sceneLocation uses for the very same kind of marker. One
    mod therefore references one marker two ways, on purpose.
    SUPERSEDED BY D87: we now ship no spawnMarkerNodeRef at all, as
    AldecaldosHighStakes does. The short form is real - it is just a second name
    to resolve for a position the scene is already anchored on, and the spawn is
    where the Act 3 crash lived. See actor_def().
  - The PLAYER takes the LAST actor id. Hot Fuzz numbers judy_max 0, Nibbles 1,
    Johnny 2, Player 3; the Undermine template, having no NPCs, numbers its Player
    0. An actorId is an index into a table the engine reads by position, so the
    observed order is followed even though nothing visibly demands it.
"""
import math
import json
import os
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import H, check_enum, cname, envelope, noderef, respath, tweakdbid
from enums import scnContextualActorName, scnSceneCategoryTag
from gen_questphase import build_condition, build_node_data

# ---------------------------------------------------------------- D86 control
# A one-variable bisect for the Act 3 clinic crash (ID 1912746313+0x1E, read at
# 0xFFFFFFFFFFFFFFFF on a redDispatcher job thread).
#
# Act 3 reaches this scene: box_opened_set -> guard_splinter -> give_splinter ->
# progress_4 -> obj_mara_on -> guard_meet_mara -> route_mara -> meet_mara. So the
# crash is inside the scene, and the scene does exactly two things that can
# resolve a name and fault: it SPAWNS an actor, and it PLAYS lines.
#
# AC_ACTOR_SPAWN=0 removes the first one and nothing else. The scene still loads,
# still carries Character.ashcache_mara and the #ac_mara NodeRef, still runs every
# line and every embedded quest node - only the spawn does not proceed. That is
# the half of the split we can move without touching audio at all.
#
#   survives  -> the actor spawn is the fault. -- THIS IS WHAT HAPPENED, on
#                2026-09-10 at 17:00: same click, same graph, no crash. The fix
#                is D87 in actor_def() below.
#   crashes   -> the actor is cleared and the fault is in the dialogue path,
#                which is where the .wem encoding finally becomes testable.
#
# The switch is KEPT rather than deleted: it is the only one-variable way back to
# "is it the actor again?" if a future crash lands on the same instruction.
#
# Why not just change the three fields now: three variables at once answers
# nothing when it fails. This answers something either way.
_ACTOR_SPAWN = os.environ.get("AC_ACTOR_SPAWN", "1") != "0"

ROOT = pathlib.Path(__file__).resolve().parent.parent

NO_ACTOR = 4294967295           # 0xFFFFFFFF - scnActorId "unset". Hot Fuzz uses it throughout.
LINE, OPTION = 1, 2             # low byte of a screenplay itemId

# An SRRefId is an INDEX into resouresReferences. Every one of those tables is
# emitted empty EXCEPT lipsyncAnimSets, because across all three reference scenes
# the lipsync table is the one an actor is never allowed to dangle into:
#
#   dialog_only_template   1 actor  (player 0)                1 entry
#   template.scene         2 actors (songbird 0, player 1)    2 entries
#   hot_fuzz               4 actors (judy 0, Nibbles 1,       4 entries
#                                    Johnny 2, player 3)
#
# and in every one of the seven cases actor N carries lipsyncAnimSet id == N. One
# entry per actor, indexed by actor id, no exceptions - including Nibbles and
# Johnny, who have animSets: [] and a valid lipsync id at the same time. So "empty
# animSets" and "unset lipsync" are two different questions and only the first has
# evidence behind it. See LIPSYNC_PLACEHOLDERS.
UNSET_SRREF = 4294967295

# What those entries point AT does not have to match the actor. template.scene is a
# songbird conversation whose two lipsync paths are a Japantown vendor's, left over
# from whatever it was cloned from - the same leftover-reference tolerance its
# cinematicAnimSets show. It ships and works, so a real vanilla path that resolves
# is worth more here than a correct one, and there is no correct one to use: this
# mod has no VO (D2), so nothing ever plays these.
#
# The pair below is template.scene's own table, in its own order, because its cast
# is exactly this mod's - one NPC at 0, the player last. NPCs take the first path,
# the player takes the second, which is how that scene assigns them.
#
# The NPC path was never checked against the archives, and it does not ship.
# template.scene's `lipsync\en\` spelling is an editor-side path; every shipped
# lipsync animset lives under base\localization\<locale>\lipsync\ (lang_en_voice.list).
# Mara has no lipmap entry (lipsync/ is empty), so the engine falls back to this
# entry. At 2026-09-15 19:07:46.144 RedHotTools logged "Resource not found" for it on
# thread 556 - the redDispatcher8 that faulted on 1912746313+0x1E in that same
# millisecond, and the only time the path was logged in six sessions (OI-21).
# A real set that lacks a line's f_ name is harmless - vanilla ships every m_ name
# with nothing behind it - so Mara points at the shipped copy of the same set. It is
# the en-us voice pack's, which is the VO language here. The player path stays: no
# player animset ships at all, and vanilla dangles V's entry too (mq029).
LIPSYNC_NPC = ("base\\localization\\en-us\\lipsync\\base\\open_world\\vendors\\westbrook\\japantown"
               "\\wbr_jpn_prostitute_female\\wbr_jpn_prostitute_female\\civ_prst_f_01_enus_30.anims")
LIPSYNC_PLAYER = ("base\\open_world\\vendors\\westbrook\\japantown\\wbr_jpn_prostitute_female"
                  "\\lipsync\\en\\wbr_jpn_prostitute_female\\v.anims")

# A choice node's outputs (D104). Every option leaves from stamp {name 0, ordinal i};
# names 1..6 are six RESERVED sockets that exist once whatever the option count.
# royce_default.scene is the only extracted hub with more than one option and shows
# it plainly: (0,0) (0,1) then (1,0)..(6,0). The single-option samples this was first
# read from cannot tell "name = option" from "ordinal = option", and the wrong guess
# put option 1 and 2 on reserved sockets 1 and 2: picking option 0 ALSO fired
# whatever hung off socket 2 (two sections at once), picking 1 or 2 found no
# (0,i) socket and crashed on a null read.
CHOICE_RESERVED_SOCKETS = 6

# How many inputs each node type exposes, so a link can address the right ordinal.
# Only scnQuestNode has more than the one implicit input, because it carries the
# CutDestination socket that every questphase node carries.
QUEST_NODE_IN = 1               # ordinal of "In" on an embedded quest node

# No VO is authored (decision D2), so a subtitle stays up for as long as it takes
# to read. 55 ms/char is about 200 wpm; the floor keeps one-word lines legible.
MS_PER_CHAR = 55
MIN_LINE_MS = 1200
GAP_MS = 250

# A line that HAS audio is not a guess any more, and the reading-speed formula
# stops applying to it. A subtitle that disappears on the audio's last sample
# reads as clipped, so the event is held a little past the end. This tail is a
# choice, not a measurement - erring long costs a beat of silence, erring short
# eats the end of a word. Same direction as sectionDuration below.
VO_TAIL_MS = 250

_vo_ms = None       # key -> longest measured audio length across locales
_vo_timed = []      # keys whose duration came from real audio, for the report
_vo_unmeasured = set()   # keys that HAVE audio nobody here can measure


def riff_duration_ms(path):
    """Length of a RIFF/WAVE file in ms, or None if it is not one we can read.

    Covers exactly the two formats this pipeline produces: the .wav that comes
    out of RVC, and the PCM .wem that wav_to_wem.py wraps around it - a .wem IS
    a RIFF, which is the entire basis of the no-Wwise route documented there. A
    Vorbis or Opus .wem falls through to None and the line keeps its guess.

    Read off the header rather than decoded: nothing here needs the samples.
    """
    try:
        b = path.read_bytes()
    except OSError:
        return None
    if len(b) < 12 or b[:4] != b"RIFF" or b[8:12] != b"WAVE":
        return None
    import struct
    pos, rate, chans, bits, avg, data = 12, 0, 0, 0, 0, None
    while pos + 8 <= len(b):
        cid, size = b[pos:pos + 4], struct.unpack_from("<I", b, pos + 4)[0]
        body = pos + 8
        if cid == b"fmt " and size >= 16:
            _, chans, rate, avg, _, bits = struct.unpack_from("<HHIIHH", b, body)
        elif cid == b"data":
            # A truncated file lies about its size; trust whatever is really there.
            data = min(size, len(b) - body)
        pos = body + size + (size & 1)
    if not data or not rate:
        return None
    per_sec = avg or (rate * chans * max(bits, 8) // 8)
    return int(round(1000 * data / per_sec)) if per_sec else None


def ffprobe_duration_ms(path):
    """Fallback for a compressed drop (.flac/.ogg/.mp3/.m4a). Optional by design:
    if ffprobe is not installed the line simply keeps its reading-speed guess."""
    import shutil
    import subprocess
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=20)
        return int(round(float(out.stdout.strip()) * 1000))
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def vo_lengths():
    """key -> longest audio length in ms, over every locale and both voice tags.

    Built once. The longest wins for the same reason the longest locale sets the
    reading pace: whichever recording runs longest is the one that would be cut
    off. split_stem comes from gen_vomap because that module owns the naming
    rule, and a name applied in two places eventually means two things.
    """
    global _vo_ms
    if _vo_ms is not None:
        return _vo_ms
    import gen_vomap
    import wav_to_wem
    _vo_ms = {}
    # VO_LOCALES, not every locale: since D42 only en-us has audio, so the
    # Ukrainian subtitle is timed to the English take it now sits over. That
    # is the recording the player actually hears, so it is the one a line may
    # not be shorter than.
    for locale in gen_vomap.VO_LOCALES:
        d = ROOT / "vo" / locale
        if not d.is_dir():
            continue
        for f in sorted(p for p in d.iterdir() if p.is_file()):
            ext = f.suffix.lower()
            if ext != ".wem" and ext not in wav_to_wem.SOURCES:
                continue
            ms = riff_duration_ms(f)
            if ms is None and ext != ".wem":
                ms = ffprobe_duration_ms(f)
            key, _ = gen_vomap.split_stem(f.stem)
            if not ms:
                # A Vorbis or Opus .wem is audio this reader cannot measure. Left
                # unsaid, the line would keep its reading-speed guess while having
                # a recording of a different length - and a subtitle two seconds
                # short of its audio truncates the line. Say so instead.
                _vo_unmeasured.add(key)
                continue
            _vo_ms[key] = max(_vo_ms.get(key, 0), ms)
    _vo_unmeasured.difference_update(_vo_ms)
    return _vo_ms


def read_time(line, key):
    """Duration for a line: an explicit override, else the audio, else reading speed.

    `key` is the full "<scene>.<line>" subtitle key, not the bare line id, because
    that is how vo/ names its files. It is a required argument on purpose: passing
    the bare id would look right, match nothing, and leave every voiced line on
    its reading-speed guess with no error anywhere.

    Ukrainian runs longer than English for the same beat, so timing off en-us
    alone would clip every ua-ua subtitle. An explicit "ms" on the line wins;
    that is the escape hatch for a beat that wants to land slower or faster
    than its character count suggests.

    Once a line has audio the character count stops being evidence about
    anything, so a measured length beats the formula - that is OI-8's answer for
    every voiced line, and the formula survives only for the unvoiced ones.
    """
    if "ms" in line:
        return line["ms"]
    ms = vo_lengths().get(key)
    if ms:
        _vo_timed.append(key)
        return max(MIN_LINE_MS, ms + VO_TAIL_MS)
    longest = max((len(v) for k, v in line.items() if "-" in k and isinstance(v, str)),
                  default=0)
    return max(MIN_LINE_MS, longest * MS_PER_CHAR)


def scene_time(stu):
    return {"$type": "scnSceneTime", "stu": stu}


def node_id(n):
    return {"$type": "scnNodeId", "id": n}


def out_socket(name, dests, ordinal=0):
    return {"$type": "scnOutputSocket", "destinations": dests,
            "stamp": {"$type": "scnOutputSocketStamp", "name": name, "ordinal": ordinal}}


def in_socket_id(target_nid, ordinal):
    return {"$type": "scnInputSocketId",
            "isockStamp": {"$type": "scnInputSocketStamp", "name": 0, "ordinal": ordinal},
            "nodeId": node_id(target_nid)}


def dialog_event(ruid, item_id, start, dur, holocall=False):
    return H({
        "$type": "scnDialogLineEvent",
        "additionalSpeakers": {"$type": "scnAdditionalSpeakers", "executionTag": 0,
                               "role": "Full", "speakers": []},
        "duration": dur,
        "executionTagFlags": 0,
        # The event id may be anything unique; both references reuse the line's own
        # locstring ruid, which keeps a crash log traceable to a line of dialogue.
        "id": {"$type": "scnSceneEventId", "id": str(ruid)},
        "scalingData": None,
        "screenplayLineId": {"$type": "scnscreenplayItemId", "id": item_id},
        "startTime": start,
        "type": "0",
        "visualStyle": "regular",
        "voParams": {
            "$type": "scnDialogLineVoParams",
            # 0 since 2026-09-10. This forces the male/female pick to come from
            # brain gender rather than from the VO, and it is what a scene with
            # no recordings sets - the dialogue-only template does. Every scene
            # that HAS voice lines leaves it 0: Hot Fuzz does, and so does
            # AldecaldosHighStakes, whose 11 lines were read field for field
            # against ours. We have 43 recordings, so we are the second kind.
            "alwaysUseBrainGender": 0,
            "customVoEvent": cname("None"),
            "disableHeadMovement": 0,
            "ignoreSpeakerIncapacitation": 0,
            # D124. Both of these are per LINE, not per scene or per actor, and
            # only the REMOTE speaker gets them: in sq025_08_backoffice exactly 2
            # of the 5 line events carry isHolocallSpeaker 1, and they are
            # Delamain's - V, standing in the room, speaks normally. So the
            # caller's voice is band-limited and routed to the phone while V's
            # is not, which is the whole audible difference between a holocall
            # and two people talking.
            "isHolocallSpeaker": 1 if holocall else 0,
            "voContext": "Vo_Context_Quest",
            "voExpression": "Vo_Expression_Phone" if holocall else "Vo_Expression_Spoken",
        },
    })


# A scnAudioEvent's id has to be unique inside the scene and must not collide
# with a dialogue event's, which reuses the line's own locstring ruid. The ruids
# come from one append-only block and increment by one, so an offset this large
# cannot be reached until the quest has a billion lines.
AUDIO_EVENT_ID_OFFSET = 10 ** 9

# scnPerformerId's "nobody". 0xFFFFFF00, not NO_ACTOR's 0xFFFFFFFF - they are
# different id spaces and vanilla uses this one for an unattached performer
# (see the itemOwnerId above, and mq029_01a_garage.scene).
NO_PERFORMER = 4294967040

# D105 - a line's "emotion" becomes the facial event vanilla uses for it: a
# scnChangeIdleAnimEvent on the "head" component whose bakedFacialTransition names
# idle__<emotion>__<gender> as the idle to blend to and, optionally, a
# idle__<emotion>__<gender>__<variant> key on top. Field for field with
# mq029_01a_garage.scene (johnny, a spawnDespawn actor with facialAnimSets [] -
# the same shape as Mara) and q005_07_vip_apartment.scene (68 of them). The ids
# get their own offset for the same reason audio events do.
EMOTION_EVENT_ID_OFFSET = 2 * 10 ** 9
# Every female facial idle that appears in the 73 extracted vanilla scenes. A name
# outside this set is a typo until a vanilla scene shows otherwise.
FACIAL_EMOTIONS = {
    "aggression", "anger", "anger/defensive", "anger/full", "disappointed",
    "disappointed/offended", "disgust", "disgust/contempt", "disinterested",
    "disinterested/sceptical", "disinterested/uncertain", "fear", "fear/worried",
    "happy", "happy/charming", "happy/excited", "interested", "interested/awed",
    "interested/cautious", "interested/confident", "interested/focused",
    "interested/respectful", "interested/suspicious", "joy", "joy/fake_smile",
    "joy/pleased", "nervous", "nervous/full", "neutral", "sadness", "sadness/bored",
    "surprise", "tiredness"}


def performer_of(actor_id):
    """scnPerformerId of an actor: (actorId << 8) | 1. q005_07_vip_apartment gives
    actor 0 performer 1 and actor 1 performer 257."""
    return (actor_id << 8) | 1


def emotion_event(event_id, emotion, performer, start):
    base, _, variant = emotion.partition("/")
    idle = {g: f"idle__{base}__{g}" for g in ("female", "male")}
    key = {g: (f"{idle[g]}__{variant}" if variant else "None") for g in idle}
    return H({
        "$type": "scnChangeIdleAnimEvent",
        "actorComponent": cname("head"),
        "addIdleAnimName": cname("None"),
        "animData": {"$type": "scneventsPlayAnimEventExData",
                     "basic": {"$type": "scneventsPlayAnimEventData", "blendIn": 0.5,
                               "blendInCurve": "SinusoidalEaseInOut", "blendOut": 0.5,
                               "blendOutCurve": "SinusoidalEaseInOut", "clipEnd": 0,
                               "clipFront": 0, "stretch": 1},
                     "bodyPartMask": cname("None"), "weight": 1},
        "animName": cname("None"),
        "bakedFacialTransition": {
            "$type": "animFacialEmotionTransitionBaked",
            "customTransitionAnim": cname("None"),
            "facialKey_Female": cname(key["female"]), "facialKey_Male": cname(key["male"]),
            "facialKeyWeight": 1, "timeScale": 1,
            "toIdleFemale": cname(idle["female"]), "toIdleMale": cname(idle["male"]),
            "toIdleNeckWeight": 0.75, "toIdleWeight": 1,
            # vanilla's "Fast" pairs 2.73 s with a 2730 ms event every time
            "transitionDuration": 2.73, "transitionType": "Fast"},
        "convertToAdditive": 0, "duration": 2730, "executionTagFlags": 0,
        "eyesBlendAdditive": 1, "facialInstantTransition": 0,
        "id": {"$type": "scnSceneEventId", "id": str(event_id)},
        "idleAnimName": cname("None"), "isEnabled": 1, "lowerFaceBlendAdditive": 1,
        "muteAnimEvents": "0", "neckWeight": 1,
        "performer": {"$type": "scnPerformerId", "id": performer},
        "scalingData": None, "startTime": start, "type": "0",
        "upperFaceBlendAdditive": 1})


def audio_event(event_id, name, performer, start):
    """A scene-driven Wwise event. UNUSED since 2026-09-10 - kept because the
    shape is right and a real bank event may want it one day, but no longer
    emitted for dialogue.

    It used to fire once per voiced line, on the belief that this is how the
    recordings reach the player. That belief was wrong, and three independent
    reads of the source say so:

      - Audioware never looks at a scnAudioEvent. Its only scene-dialogue path
        is the AUDIO_PLAY_DIALOG_LINE detour in crates/audioware/src/hooks/
        audio.rs, keyed on the line's own string_id (our locstring ruid), and
        the bank registered 774 scene ids from that key alone. Its
        AudioInterface::PostEvent hook, the one a scene event would pass
        through, only logs and calls straight on.
      - AldecaldosHighStakes - a shipping voiced quest mod with 23 recordings -
        carries exactly ONE scnAudioEvent in the scene read here, and it names
        mus_q114_saul_briefing_02_STOP, a vanilla bank event. Not one of its
        dialogue lines has one.
      - The CName we were writing, ash_cache_vo_<line>, is defined in no
        soundbank at all, and emitterName was the literal "default", which is
        no emitter either. Two unresolvable CNames per line, handed to the
        audio system on the frame the line starts - and an unresolvable hash
        used unchecked is the exact shape of the crashes this quest keeps
        producing (read at 0xFFFFFFFFFFFFFFFF with a small integer in the
        index register).

    Shape copied field for field from mq029_01a_garage.scene, which ships two of
    them (mq029_show_photo_01 / mq029_hide_photo_01) on a prop performer. Rule 8:
    nothing here is invented, including duration 0, which is what vanilla sets on
    a one-shot - the sound's own length ends it, not this field.

    `performer` is who makes the sound. Vanilla maps actor N to performer N+1
    (johnny is actorId 0 and performerId 1 in that scene's debugSymbols), so a
    line with a speaker attaches to the speaker and one without falls back to
    NO_PERFORMER rather than guessing at somebody.
    """
    return H({
        "$type": "scnAudioEvent",
        "ambientUniqueName": cname("None"),
        "audioEventName": cname(name),
        "duration": 0,
        "emitterName": cname("default"),
        "executionTagFlags": 0,
        "fastForwardSupport": "MuteDuringFastForward",
        "id": {"$type": "scnSceneEventId", "id": str(event_id)},
        "performer": {"$type": "scnPerformerId", "id": performer},
        "scalingData": None,
        "startTime": start,
        "type": "0",
    })


def _entity_ref(node_ref=""):
    return {"$type": "gameEntityReference",
            "dynamicEntityUniqueName": cname("None"), "names": [],
            "reference": noderef(node_ref), "sceneActorContextName": cname("None"),
            "slotName": cname("None"), "type": "EntityRef"}


def lipsync_ref(path):
    """One entry in resouresReferences.lipsyncAnimSets.

    Both fields are present in every reference entry: the real path hangs off
    asyncRefLipsyncAnimSet as a Soft ref, and the eager lipsyncAnimSet beside it is
    always null. Soft is what makes this safe to point at a base-game path - it is
    a load-if-present reference, not a packing dependency.
    """
    return {"$type": "scnLipsyncAnimSetSRRef",
            "asyncRefLipsyncAnimSet": respath(path, flags="Soft"),
            "lipsyncAnimSet": respath("", flags="Default")}


def lipsync_name(prefix, ruid):
    """CName of one line's facial animation, in the game's own convention.

    Vanilla names it "f_" or "m_" plus the line's locstring ruid as 16 uppercase
    hex digits. Verified end to end on one line: mq029_01a_garage.scene carries
    locstringId 1821466168323067904 with femaleLipsyncAnimationName
    f_194725D45D49D000, and 0x194725D45D49D000 IS 1821466168323067904; the
    animation of that exact name lives in base\\localization\\en-us\\lipsync\\
    base\\quest\\minor_quests\\mq029\\scenes\\mq029_01a_garage\\johnny.anims,
    which the .lipmap binds to Johnny's voicetag for that scene.

    The prefix is the PLAYER's gender, the same split the .wem pair uses - not
    the speaker's. Vanilla sets BOTH fields and then ships only the f_ animation
    (every one of the 5688 shipped lipsync animsets does), so an m_ name that
    resolves to nothing is demonstrably harmless rather than a crash.

    Nothing in the engine forces the name to be derived from the ruid - it just
    looks the CName up in whatever animset the lipmap hands it. Following the
    convention anyway means an animset built the way the game builds them lines
    up with no translation table in between.
    """
    return cname(f"{prefix}_{int(ruid):016X}")


def actor_def(actor_id, char, marker_ref, voicetag):
    """One NPC, spawned by the scene itself at the scene's own origin.

    marker_ref is no longer written into the actor (D87, see spawnDespawnParams).
    It stays in the signature because source/characters.json still declares the
    marker and negtest still enforces that it names a real one - the quest node's
    sceneLocation is what consumes it now.

    Field-for-field this is the Undermine template's actor with the animation
    stripped out. Two things differ from Hot Fuzz's, deliberately:

      - communityParams is left unset. Hot Fuzz names a community entry, which ties
        the actor to a vanilla crowd definition that does not exist for a mod NPC.
        Undermine leaves it None and spawns fine.
      - specCharacterRecordId is WRITTEN as a string and SHIPS as a hash. WolvenKit
        cooks it: 'Character.ashcache_mara' comes back out of the packed .scene as
        102920621884. That is the right number - a TweakDBID is
        (len(name) << 32) | crc32(name), which computes to exactly that, and the
        same formula reproduces the 81306071356 Hot Fuzz ships for
        Character.judy_max. So writing the readable form costs nothing at runtime
        and survives a rename, while the reference mods only look different because
        their editor cooked the same value earlier.
    """
    return {
        "$type": "scnActorDef",
        "acquisitionPlan": "spawnDespawn",
        "actorId": {"$type": "scnActorId", "id": actor_id},
        "actorName": char["actorName"],
        "animSets": [], "bodyCinematicAnimSets": [],
        "communityParams": {"$type": "scnCommunityParams", "entryName": cname("None"),
                            "forceMaxVisibility": 0, "reference": noderef("")},
        "cyberwareAnimSets": [], "cyberwareCinematicAnimSets": [],
        "deformationAnimSets": [], "dynamicAnimSets": [],
        "facialAnimSets": [], "facialCinematicAnimSets": [],
        "findActorInContextParams": {
            "$type": "scnFindEntityInContextParams", "contextActorName": cname("None"),
            "contextualName": "Player", "forceMaxVisibility": 0,
            "specRecordId": tweakdbid(""), "voiceVagId": {"$type": "scnVoicetagId", "id": "0"}},
        "findActorInWorldParams": {"$type": "scnFindEntityInWorldParams",
                                   "actorRef": _entity_ref(), "forceMaxVisibility": 0},
        "holocallInitScn": respath("", flags="Default"),
        "lipsyncAnimSet": {"$type": "scnLipsyncAnimSetSRRefId", "id": actor_id},
        "spawnDespawnParams": {
            "$type": "scnSpawnDespawnEntityParams",
            # D87 - field-for-field with AldecaldosHighStakes' regina_fake, the
            # one actor on this machine that demonstrably spawns AND speaks. D86
            # proved the fault is in the spawn: with AC_ACTOR_SPAWN=0 the same
            # click ran the same graph and did not crash. Five values differed,
            # and every one of them sits on the async prefetch/spawn path the
            # crash landed on - thread "redDispatcher14", not the game thread.
            #
            #   alwaysSpawned      1 -> 0  spawn on the graph's schedule, not at
            #                              resource-prepare time.
            #   prefetchAppearance 1 -> 0  there was nothing to prefetch AGAINST:
            #                              specRecordId was empty, so the
            #                              appearance CName had no character
            #                              record to resolve through.
            #   specRecordId      "" -> Character.<record>. This is the field the
            #                              spawnDespawn plan reads. The record was
            #                              only ever in the actor-level
            #                              specCharacterRecordId. D95 then clears
            #                              that one: see the field below.
            #   spawnMarkerNodeRef   -> 0  the quest node's sceneLocation already
            #                              anchors this scene AT #ac_mara, so a
            #                              Local marker of 0 with a zero offset
            #                              puts her on the same spot with one less
            #                              NodeRef to resolve.
            #   validateSpawnPostion 1 -> 0  as regina_fake ships. The marker is a
            #                              hand-placed position, so "place her"
            #                              beats "check the placement first".
            #
            # she is still standing there when the scene opens (spawnOnStart), she
            # just is not spawned before the scene asks for her.
            "alwaysSpawned": 0,
            "appearance": cname(char["appearance"]),
            "dynamicEntityUniqueName": cname(char["record"]),
            "findInWorld": 0, "forceMaxVisibility": 0,
            "isEnabled": 1 if _ACTOR_SPAWN else 0,
            "itemOwnerId": {"$type": "scnPerformerId", "id": 4294967040},
            # D105 - 0 despawns the actor the frame the scene ends, which is the
            # "vanishes in front of V" the user saw. No extracted scene sets it to
            # 1, so characters.json opts in per character and the game decides.
            "keepAlive": 1 if char.get("keepAlive") else 0,
            "prefetchAppearance": 0,
            "spawnMarker": cname("None"),
            "spawnMarkerNodeRef": noderef(""),
            "spawnMarkerType": "Local",
            "spawnOffset": {"$type": "Transform",
                            "orientation": {"$type": "Quaternion", "i": 0, "j": 0, "k": 0, "r": 1},
                            "position": {"$type": "Vector4", "W": 0, "X": 0, "Y": 0, "Z": 0}},
            "spawnOnStart": 1 if _ACTOR_SPAWN else 0,
            "specRecordId": tweakdbid(f"Character.{char['record']}"),
            # sic - the engine field really is spelled "Postion".
            "validateSpawnPostion": 0},
        "spawnerParams": {"$type": "scnSpawnerParams", "forceMaxVisibility": 0,
                          "reference": noderef("")},
        "spawnSetParams": {"$type": "scnSpawnSetParams", "entryName": cname("None"),
                           "forceMaxVisibility": 0, "reference": noderef("")},
        "specAppearance": cname(char["appearance"]),
        # 0, deliberately (D95). A spawnDespawn actor names its record in ONE
        # place, spawnDespawnParams.specRecordId above. Every spawnDespawn actor in
        # the extracted references (vanilla Johnny x3, T-Bug, Undermine's TweakXL
        # Songbird) leaves this at 0; D87 set both and the Act 3 crash
        # 1912746313+0x1E came back from a loaded save. findInContext actors are
        # the other convention - see player_actor_def.
        "specCharacterRecordId": tweakdbid(""),
        # The one key the lipsync map has. See tools/alloc_voicetags.py: the
        # .lipmap addresses an actor by this number and nothing else, so an actor
        # left at 0 can never be given a mouth. Vanilla gives every actor one.
        "voicetagId": {"$type": "scnVoicetagId", "id": str(voicetag)},
    }


def voice_actor_def(actor_id, char, voicetag):
    """Somebody who is on the phone, not in the room (D124).

    Field for field with q005_07_vip_apartment's "AI" actor - the penthouse Siri,
    the one vanilla actor on this machine that speaks without a body. The whole
    difference from actor_def() is the acquisition plan: findInContext with
    contextualName "Voice" hands the scene a voice with no entity to place, so
    there is nothing to spawn, nothing to stand anywhere, and no marker to
    measure. spawnDespawnParams is left inert for the same reason.

    Note specCharacterRecordId stays 0 and the record is named ONCE, inside
    findActorInContextParams.specRecordId - the mirror image of the spawnDespawn
    convention in actor_def(), and exactly how the vanilla Siri ships. D95 is the
    reason that matters: naming a record twice is what the Act 3 crash looked like.
    """
    return {
        "$type": "scnActorDef",
        "acquisitionPlan": "findInContext",
        "actorId": {"$type": "scnActorId", "id": actor_id},
        "actorName": char["actorName"],
        "animSets": [], "bodyCinematicAnimSets": [],
        "communityParams": {"$type": "scnCommunityParams", "entryName": cname("None"),
                            "forceMaxVisibility": 0, "reference": noderef("")},
        "cyberwareAnimSets": [], "cyberwareCinematicAnimSets": [],
        "deformationAnimSets": [], "dynamicAnimSets": [],
        "facialAnimSets": [], "facialCinematicAnimSets": [],
        "findActorInContextParams": {
            "$type": "scnFindEntityInContextParams", "contextActorName": cname("None"),
            "contextualName": check_enum("Voice", scnContextualActorName,
                                         "voice actor contextualName"),
            "forceMaxVisibility": 0,
            "specRecordId": tweakdbid(f"Character.{char['record']}"),
            "voiceVagId": {"$type": "scnVoicetagId", "id": str(voicetag)}},
        "findActorInWorldParams": {"$type": "scnFindEntityInWorldParams",
                                   "actorRef": _entity_ref(), "forceMaxVisibility": 0},
        "holocallInitScn": respath("", flags="Default"),
        "lipsyncAnimSet": {"$type": "scnLipsyncAnimSetSRRefId", "id": actor_id},
        "spawnDespawnParams": {
            "$type": "scnSpawnDespawnEntityParams",
            "alwaysSpawned": 0, "appearance": cname("None"),
            "dynamicEntityUniqueName": cname("None"),
            "findInWorld": 0, "forceMaxVisibility": 0, "isEnabled": 1,
            "itemOwnerId": {"$type": "scnPerformerId", "id": 4294967040},
            "keepAlive": 0, "prefetchAppearance": 0,
            "spawnMarker": cname("None"), "spawnMarkerNodeRef": noderef(""),
            "spawnMarkerType": "Local",
            "spawnOffset": {"$type": "Transform",
                            "orientation": {"$type": "Quaternion", "i": 0, "j": 0, "k": 0, "r": 1},
                            "position": {"$type": "Vector4", "W": 0, "X": 0, "Y": 0, "Z": 0}},
            "spawnOnStart": 0, "specRecordId": tweakdbid(""),
            "validateSpawnPostion": 0},
        "spawnerParams": {"$type": "scnSpawnerParams", "forceMaxVisibility": 0,
                          "reference": noderef("")},
        "spawnSetParams": {"$type": "scnSpawnSetParams", "entryName": cname("None"),
                           "forceMaxVisibility": 0, "reference": noderef("")},
        "specAppearance": cname("default"),
        "specCharacterRecordId": tweakdbid(""),
        "voicetagId": {"$type": "scnVoicetagId", "id": str(voicetag)},
    }


def player_actor_def(actor_id, player):
    """V. Never spawned - findInContext hands the scene whoever the player is."""
    return {
        "$type": "scnPlayerActorDef",
        "acquisitionPlan": "findInContext",
        "actorId": {"$type": "scnActorId", "id": actor_id},
        "animSets": [], "bodyCinematicAnimSets": [],
        "cyberwareAnimSets": [], "cyberwareCinematicAnimSets": [],
        "deformationAnimSets": [], "dynamicAnimSets": [],
        "facialAnimSets": [], "facialCinematicAnimSets": [],
        "findActorInContextParams": {
            "$type": "scnFindEntityInContextParams", "contextActorName": cname("None"),
            "contextualName": "Player", "forceMaxVisibility": 0,
            "specRecordId": tweakdbid(player["record"]),
            "voiceVagId": {"$type": "scnVoicetagId", "id": "0"}},
        "findNetworkPlayerParams": {"$type": "scnFindNetworkPlayerParams", "networkId": 0},
        "lipsyncAnimSet": {"$type": "scnLipsyncAnimSetSRRefId", "id": actor_id},
        "playerName": "Player",
        "specAppearance": cname("default"),
        "specCharacterRecordId": tweakdbid(player["record"]),
        "specTemplate": cname("(None)"),
        # V's own vanilla voicetag, not 0. 16 of the 17 census scenes with a player
        # actor carry this number (12 vanilla, Hot Fuzz, Regina, both WolvenKit
        # templates); only q108_00_chicken_test, an empty test scene, has 0.
        # A 0 here beside lipsyncAnimSet 1 matched nothing that ships. OI-21.
        "voicetagId": {"$type": "scnVoicetagId", "id": "1103967280742240864"},
    }


def build_cast(scene, chars, stem, voicetags):
    """The scene's 'actors' list -> (scnActorDefs, scnPlayerActorDefs, name -> id).

    The cast is named by character id (source/characters.json); dialogue lines name
    the same people by actorName, because a script reads better with names in it.
    This is the one place the two namespaces meet.

    It also builds the lipsync table, because that table is per-actor and has to
    stay the same length as the cast - actor N reads entry N. Building it anywhere
    else would let a cast change silently leave an actor indexing past the end.
    """
    by_id = {c["id"]: c for c in chars["characters"]}
    actors, name_of = [], {}
    for i, cid in enumerate(scene.get("actors", [])):
        if cid not in by_id:
            sys.exit(f"scene_{stem}.json casts {cid!r}, which source/characters.json "
                     f"does not define (has {sorted(by_id)})")
        c = by_id[cid]
        if c["actorName"] in name_of:
            sys.exit(f"scene_{stem}.json casts two characters both called "
                     f"{c['actorName']!r} - a line naming that actor would be ambiguous")
        if cid not in voicetags:
            sys.exit(f"character {cid!r} has no voicetag - run tools/alloc_voicetags.py")
        # D124. A holocall casts nobody into the world - everyone who is not V is
        # a voice on the other end of the phone. It is a whole-scene property
        # rather than a per-actor one because a scene where one speaker is
        # physically present and another is on the phone does not exist in this
        # quest, and inventing the option would mean inventing its test.
        if scene.get("scene", {}).get("holocall"):
            actors.append(voice_actor_def(i, c, voicetags[cid]))
        else:
            actors.append(actor_def(i, c, c["marker"], voicetags[cid]))
        name_of[c["actorName"]] = i

    player = chars["player"]
    if player["actorName"] in name_of:
        sys.exit(f"a character is named {player['actorName']!r}, which is the player's "
                 f"own actorName - rename one of them")
    name_of[player["actorName"]] = len(actors)
    lipsync = [lipsync_ref(LIPSYNC_NPC) for _ in actors] + [lipsync_ref(LIPSYNC_PLAYER)]
    return actors, [player_actor_def(len(actors), player)], name_of, lipsync


def interruption_scenario():
    """Pause the conversation if the speakers walk apart OR the player is attacked.

    The distance pair is copied from the Undermine dialogue-only template; Greater
    6 / Less 5 is the second most common interrupt distance and the most common
    return distance in the shipped game (reference/interruption.md). Without it a
    player who wanders off mid-scene leaves the dialogue playing to an empty room.

    The COMBAT pair is D127, and it is the fix for a reported soft-lock. An
    interruption pauses and resumes a conversation - it never ends one - so a
    scene only pauses for reasons it has declared, and combat was not one of them.
    When Barghest opened fire during a choice hub the engine therefore did
    nothing: the game hides the dialogue HUD in combat, so the options vanished,
    but the scene stayed parked on the choice node waiting for a selection the
    player could no longer make, and the quest graph waited on an exit that could
    never fire. On the four scenes that raise the tier (mara, aftertalk, decision,
    epilogue) V was also pinned at Tier3_LimitedGameplay with empty hands while
    being shot at.

    Declaring combat turns all of that into the engine's own pause/resume: INT
    fires, the wired net hands back Tier1 after 500 ms so the player can fight,
    and when combat ends RET fires and the conversation picks up where it stopped.
    Five shipped files author this condition; both halves carry a single bool, and
    the wrapper is the one already proven by the distance pair beside it.

    It is added to EVERY scene, holocalls included - a call that keeps talking
    over a firefight is the same bug with a smaller blast radius, and vanilla
    holocalls pause for combat too.
    """
    return {
        "$type": "scnInterruptionScenario", "enabled": 1, "forcePlayReturnLine": 0,
        "id": {"$type": "scnInterruptionScenarioId", "id": 0},
        "interruptConditions": [
            H({"$type": "scnCheckSpeakersDistanceInterruptCondition",
               "params": {"$type": "scnCheckSpeakersDistanceInterruptConditionParams",
                          "comparisonType": "Greater", "distance": 6}}),
            H({"$type": "scnCheckPlayerCombatInterruptCondition",
               "params": {"$type": "scnCheckPlayerCombatInterruptConditionParams",
                          "isInCombat": 1}})],
        "interruptionSpammingSafeguard": 0, "name": cname("Default"),
        "playingLinesBehavior": "Default", "playInterruptLine": 1,
        "postInterruptSignalFactCondition": None, "postInterruptSignalTimeDelay": 0,
        "postReturnSignalFactCondition": None, "postReturnSignalTimeDelay": 0,
        "queueName": cname("None"),
        "returnConditions": [
            H({"$type": "scnCheckSpeakersDistanceReturnCondition",
               "params": {"$type": "scnCheckSpeakersDistanceReturnConditionParams",
                          "comparisonType": "Less", "distance": 5}}),
            H({"$type": "scnCheckPlayerCombatReturnCondition",
               "params": {"$type": "scnCheckPlayerCombatReturnConditionParams",
                          "isInCombat": 0}})],
        "talkOnReturn": 1,
    }


def build(scene, alloc, stem, chars, voicetags):
    _vo_timed.clear()
    actors, players, name_of, lipsync = build_cast(scene, chars, stem, voicetags)

    def actor_id(name, where):
        if name not in name_of:
            sys.exit(f"{where} names actor {name!r}, which is not in this scene's cast "
                     f"({sorted(name_of)}) - add the character to 'actors' in "
                     f"scene_{stem}.json, or fix the name")
        return name_of[name]

    def holo_line(line_id, who):
        """Is this line coming down a phone? (D124)

        True for everyone in a holocall except V, who is standing in the world
        holding the phone. Guarding on the player's actorName rather than on "is
        this actor a voice actor" keeps the two decisions - how the actor is
        acquired, how the line is mixed - reading off the same single flag.
        """
        if not scene.get("scene", {}).get("holocall"):
            return False
        return actor_id(who, f"line {stem}.{line_id!r}") != name_of[
            chars["player"]["actorName"]]

    def speaks(item, where):
        """Who says it, and who it is aimed at.

        An explicit 'to' always wins. Otherwise, in a two-hander - which is every
        scene in this quest - the addressee is just the other party, the shape Hot
        Fuzz ships: Judy addresses the player, the player addresses Judy back. With
        three people in the room there is no such default, and guessing would put a
        character's attention on the wrong person, so it stays unset until someone
        says which.
        """
        spk = actor_id(item["actor"], where) if "actor" in item else NO_ACTOR
        if "to" in item:
            return spk, actor_id(item["to"], f"{where} ('to')")
        if spk == NO_ACTOR or len(name_of) != 2:
            return spk, NO_ACTOR
        return spk, next(i for i in name_of.values() if i != spk)

    specs = scene["nodes"]
    by_id = {}
    for n in specs:
        if n["id"] in by_id:
            sys.exit(f"duplicate scene node id {n['id']!r}")
        by_id[n["id"]] = n

    # Scene node ids are engine-facing integers. Allocating them densely from 1 in
    # source order keeps a dumped graph readable against the source file.
    nid = {n["id"]: i + 1 for i, n in enumerate(specs)}

    def ruid(line_id):
        key = f"{stem}.{line_id}"
        if key not in alloc:
            sys.exit(f"line {key!r} has no subtitle id - run tools/alloc_subtitle_ids.py")
        return alloc[key]

    # --- screenplay store: one entry per spoken line and per choice option ---
    lines, options = [], []
    item_of = {}
    for n in specs:
        for line in n.get("lines", []):
            item_of[line["id"]] = (len(lines) << 8) | LINE
            spk, adr = speaks(line, f"line {line['id']!r}")
            lines.append({
                "$type": "scnscreenplayDialogLine",
                "addressee": {"$type": "scnActorId", "id": adr},
                "femaleLipsyncAnimationName": lipsync_name("f", ruid(line["id"])),
                "itemId": {"$type": "scnscreenplayItemId", "id": item_of[line["id"]]},
                "locstringId": {"$type": "scnlocLocstringId", "ruid": str(ruid(line["id"]))},
                "maleLipsyncAnimationName": lipsync_name("m", ruid(line["id"])),
                "speaker": {"$type": "scnActorId", "id": spk},
                # mask 3 = both player genders. Hot Fuzz uses 3 on all 22 lines.
                "usage": {"$type": "scnscreenplayLineUsage",
                          "playerGenderMask": {"$type": "scnGenderMask", "mask": 3}},
            })
        for opt in n.get("options", []):
            item_of[opt["id"]] = (len(options) << 8) | OPTION
            options.append({
                "$type": "scnscreenplayChoiceOption",
                "itemId": {"$type": "scnscreenplayItemId", "id": item_of[opt["id"]]},
                "locstringId": {"$type": "scnlocLocstringId", "ruid": str(ruid(opt["id"]))},
                "usage": {"$type": "scnscreenplayOptionUsage",
                          "playerGenderMask": {"$type": "scnGenderMask", "mask": 3}},
            })

    # --- links: collect destinations per (source node, output socket index) ---
    dests = {}
    for link in scene["links"]:
        src, _, out_name = link[0].partition(":")
        dst = link[1]
        for end, ref in (("source", src), ("target", dst)):
            if ref not in by_id:
                sys.exit(f"link {link} references unknown scene node {ref!r}")
        src_spec = by_id[src]
        if src_spec["type"] == "choice":
            if not out_name:
                sys.exit(f"link {link}: leaving a choice node needs an option id, "
                         f"e.g. \"{src}:opt_something\"")
            ids = [o["id"] for o in src_spec["options"]]
            if out_name not in ids:
                sys.exit(f"link {link}: choice {src!r} has no option {out_name!r} (has {ids})")
            index = ids.index(out_name)
        else:
            if out_name:
                sys.exit(f"link {link}: only a choice node has named outputs")
            index = 0
        ordinal = QUEST_NODE_IN if by_id[dst]["type"] in ("quest", "workspot") else 0
        dests.setdefault((src, index), []).append(in_socket_id(nid[dst], ordinal))

    # --- graph nodes ---
    graph = []
    workspots, workspot_instances, ws_paths = [], [], []
    for n in specs:
        t = n["type"]
        socks = [out_socket(i, d) for (s, i), d in sorted(dests.items()) if s == n["id"]]
        if t == "choice":
            have = {i: d for (src, i), d in dests.items() if src == n["id"]}
            socks = [out_socket(0, have.get(i, []), ordinal=i)
                     for i in range(len(n["options"]))]
            socks += [out_socket(k, []) for k in range(1, CHOICE_RESERVED_SOCKETS + 1)]

        if t == "start":
            graph.append(H({"$type": "scnStartNode", "ffStrategy": "automatic",
                            "nodeId": node_id(nid[n["id"]]),
                            "outputSockets": socks or [out_socket(0, [])]}))
        elif t == "end":
            graph.append(H({"$type": "scnEndNode", "ffStrategy": "automatic",
                            "nodeId": node_id(nid[n["id"]]), "outputSockets": [],
                            "type": n.get("exit", "Terminating")}))
        elif t == "section":
            events, cursor, face = [], GAP_MS, {}
            for line in n.get("lines", []):
                key = f"{stem}.{line['id']}"
                dur = read_time(line, key)
                events.append(dialog_event(ruid(line["id"]), item_of[line["id"]],
                                           cursor, dur,
                                           holocall=holo_line(line["id"], line["actor"])))
                emo = line.get("emotion")
                if emo is not None:
                    if emo not in FACIAL_EMOTIONS:
                        sys.exit(f"line {key!r}: unknown emotion {emo!r}")
                    who = actor_id(line["actor"], f"line {key!r}")
                    # only on a change - the face holds its idle until told otherwise
                    if face.get(who) != emo:
                        events.append(emotion_event(EMOTION_EVENT_ID_OFFSET + int(ruid(line["id"])),
                                                    emo, performer_of(who), cursor))
                        face[who] = emo
                # NO scnAudioEvent here - see audio_event() below. It was one
                # per voiced line until 2026-09-10, naming a CName no soundbank
                # defines, and nothing ever read it.
                cursor += dur + GAP_MS
            graph.append(H({
                # D106: every shipped section lists its cast here (63/65 vanilla
                # sections with performer events; the two that don't are props and
                # template.scene.json, where the old [] came from). With [] the
                # performer events - emotions - never reached Mara in game.
                "$type": "scnSectionNode", "events": events,
                "actorBehaviors": [{"$type": "scnSectionInternalsActorBehavior",
                                    "actorId": {"$type": "scnActorId", "id": i},
                                    "behaviorMode": "OnlyIfAlive"}
                                   for i in sorted(set(name_of.values()))],
                "ffStrategy": "automatic", "isFocusClue": 0,
                "nodeId": node_id(nid[n["id"]]), "outputSockets": socks,
                # Long enough for the last line to finish. The template ships a
                # duration SHORTER than its last line's end; erring the other way
                # can only cost a beat of silence, never a truncated subtitle.
                # An explicit "seconds" wins, and a section with no lines needs
                # one: that shape is how a scene HOLDS TIME with nothing to say.
                # D119 uses it to keep the terminal scene alive while the engine's
                # download bar fills, because questProgressBar only starts the bar
                # and returns. Precedent is Hot Fuzz, the one reference scene with
                # an eventless section (stu 5000); stu is milliseconds here.
                "sectionDuration": scene_time(int(float(n["seconds"]) * 1000)
                                              if "seconds" in n else cursor)}))
        elif t == "choice":
            # The hub hangs on whoever V is talking to. Defaulting to the first NPC
            # cast is right for a two-hander and wrong the moment there are two
            # NPCs, which is why 'attachTo' exists to say so explicitly.
            host = (actor_id(n["attachTo"], f"choice node {n['id']!r} attachTo")
                    if "attachTo" in n else (0 if actors else NO_ACTOR))
            graph.append(H(choice_node(n, nid[n["id"]], socks, item_of, host)))
        elif t == "quest":
            # build_node_data reports errors against spec["id"]; the inner spec
            # has no id of its own, so it borrows the scene node's.
            inner = build_node_data(dict(n["node"], id=n["id"]), nid[n["id"]])
            inner["sockets"] = [
                H({"$type": "questSocketDefinition", "connections": [],
                   "name": cname(s), "type": ty})
                for s, ty in (("CutDestination", "CutDestination"),
                              ("In", "Input"), ("Out", "Output"))]
            graph.append(H({
                "$type": "scnQuestNode", "ffStrategy": "automatic",
                "isockMappings": [cname("CutDestination"), cname("In")],
                "nodeId": node_id(nid[n["id"]]),
                "osockMappings": [cname("Out")],
                "outputSockets": socks, "questNode": H(inner)}))
        elif t == "workspot":
            ws_data, ws_inst, ws_node = workspot_node(n, nid[n["id"]], socks, actor_id, chars, scene)
            if n["workspot"] not in ws_paths:
                ws_paths.append(n["workspot"])
                workspots.append(ws_data)
            workspot_instances.append(ws_inst)
            graph.append(H(ws_node))
        else:
            sys.exit(f"unknown scene node type {t!r} for node {n['id']!r}")

    entry = [{"$type": "scnEntryPoint", "name": cname(e["name"]),
              "nodeId": node_id(nid[e["node"]])} for e in scene["entryPoints"]]
    exits = [{"$type": "scnExitPoint", "name": cname(e["name"]),
              "nodeId": node_id(nid[e["node"]])} for e in scene["exitPoints"]]

    root = {
        "$type": "scnSceneResource",
        "actors": actors, "cookingPlatform": "PLATFORM_PC",
        "debugSymbols": {"$type": "scnDebugSymbols", "performersDebugSymbols": [],
                           "sceneEventsDebugSymbols": [], "sceneNodesDebugSymbols": [],
                           "workspotsDebugSymbols": []},
        "effectDefinitions": [], "effectInstances": [],
        "entryPoints": entry, "executionTagEntries": [], "executionTags": [],
        "exitPoints": exits,
        "interruptionScenarios": [interruption_scenario()],
        "localMarkers": [],
        "locStore": {"$type": "scnlocLocStoreEmbedded",
                     "vdEntries": [], "vpEntries": []},
        "notablePoints": [], "playerActors": players, "props": [], "referencePoints": [],
        "resouresReferences": {   # sic - the field really is spelled this way
            "$type": "scnSRRefCollection",
            "cinematicAnimNames": [], "cinematicAnimSets": [], "dynamicAnimNames": [],
            "dynamicAnimSets": [], "gameplayAnimNames": [], "gameplayAnimSets": [],
            # The one table that is NOT empty: one entry per actor, because every
            # reference actor indexes one and none of them dangles. See OI-10.
            "lipsyncAnimSets": lipsync,
            "ridAnimationContainers": [], "ridAnimations": [],
            "ridAnimSets": [], "ridCameraAnimations": [], "ridCyberwareAnimSets": [],
            "ridDeformationAnimSets": [], "ridFacialAnimSets": []},
        "ridResources": [],
        "sceneCategoryTag": check_enum(scene["scene"].get("categoryTag", "sideQuests"),
                                       scnSceneCategoryTag, "scene categoryTag"),
        "sceneGraph": H({"$type": "scnSceneGraph",
                         "endNodes": [node_id(nid[e["node"]]) for e in scene["exitPoints"]],
                         "graph": graph,
                         "startNodes": [node_id(nid[e["node"]]) for e in scene["entryPoints"]]}),
        "sceneSolutionHash": {"$type": "scnSceneSolutionHash",
                              "sceneSolutionHash": {"$type": "scnSceneSolutionHashHash",
                                                    "sceneSolutionHashDate": "0"}},
        "screenplayStore": {"$type": "scnscreenplayStore", "lines": lines, "options": options},
        "version": 5,
        "voInfo": [], "workspotInstances": workspot_instances, "workspots": workspots,
    }
    return root, len(lines), len(options), len(actors)


def workspot_node(n, nid_, socks, actor_id, chars, scene):
    """D171: a cast NPC idles in a vanilla .workspot while the scene runs, instead of standing
    in a bind pose. Shape copied from q005_07_vip_apartment.scene (Jackie, node 2603):

      workspots[]          scnWorkspotData_ExternalWorkspotResource -> the .workspot
      workspotInstances[]  scnWorkspotInstance, id == the graph node id, placed at the
                           actor's own marker (Global scnMarker, identity localTransform)
      graph                scnQuestNode wrapping questUseWorkspotNodeDefinition with
                           scnUseSceneWorkspotParamsV1; nothing links out of it (q005's
                           sockets Success / Work Started are both empty).

    The actor is addressed as type SceneActorContextName with sceneActorContextName =
    its actorName. Our actors are spawned by the scene, so there is no world NodeRef, and
    EntityRef + names (q001's community 'boss' shape) did not find her in game.
    isWorkspotInfinite=1 keeps the idle going.
    """
    for key in ("actor", "workspot"):
        if not n.get(key):
            sys.exit(f"workspot node {n['id']!r} needs '{key}'")
    if not n["workspot"].endswith(".workspot"):
        sys.exit(f"workspot node {n['id']!r}: {n['workspot']!r} is not a .workspot path")
    if scene.get("scene", {}).get("holocall"):
        sys.exit(f"workspot node {n['id']!r}: a holocall has nobody in the world to animate")
    actor_id(n["actor"], f"workspot node {n['id']!r}")
    char = next((c for c in chars["characters"] if c["actorName"] == n["actor"]), None)
    if char is None:
        sys.exit(f"workspot node {n['id']!r}: {n['actor']!r} is not an NPC in characters.json")
    world = json.loads((ROOT / "source" / "world.json").read_text(encoding="utf-8"))
    marker = f"{world['nodeRefPrefix']}/{char['marker']}"
    data_id = zlib.crc32(n["workspot"].encode("utf-8"))
    empty_ref = {"$type": "gameEntityReference", "dynamicEntityUniqueName": cname("None"),
                 "names": [], "reference": noderef(""), "sceneActorContextName": cname("None"),
                 "slotName": cname("None"), "type": "EntityRef"}
    ws_data = H({"$type": "scnWorkspotData_ExternalWorkspotResource",
                 "dataId": {"$type": "scnSceneWorkspotDataId", "id": data_id},
                 "workspotResource": respath(n["workspot"], flags="Default")})
    ws_inst = {"$type": "scnWorkspotInstance",
               "dataId": {"$type": "scnSceneWorkspotDataId", "id": data_id},
               "localTransform": {"$type": "Transform",
                                  "orientation": {"$type": "Quaternion", "i": 0, "j": 0, "k": 0, "r": 1},
                                  "position": {"$type": "Vector4", "W": 0, "X": 0, "Y": 0, "Z": 0}},
               "originMarker": {"$type": "scnMarker", "entityRef": empty_ref, "isMounted": 1,
                                "localMarkerId": cname("None"), "nodeRef": noderef(marker),
                                "slotName": cname("None"), "type": "Global"},
               "playAtActorLocation": 0,
               "workspotInstanceId": {"$type": "scnSceneWorkspotInstanceId", "id": nid_}}
    params = {
        "$type": "scnUseSceneWorkspotParamsV1", "changeWorkspot": 1, "continueInCombat": 0,
        "dangleResetSimulation": 0, "enableIdleMode": 1,
        "entryId": {"$type": "workWorkEntryId", "id": 4294967295},
        "entryTag": cname("None"), "exitAnimName": cname("None"),
        "exitEntryId": {"$type": "workWorkEntryId", "id": 4294967295},
        "finishAnimation": 0, "forceEntryAnimName": cname("None"), "function": "UseWorkspot",
        "instant": 1, "isPlayer": 0, "isWorkspotInfinite": 1,
        "itemOverride": {"$type": "workWorkspotItemOverride", "itemOverrides": [], "propOverrides": []},
        "jumpToEntry": 0, "maxAnimTimeLimit": 0, "meshDissolvingEnabled": 1, "movementType": "Walk",
        "playAtActorLocation": 0,
        "playerParams": {"$type": "questUseWorkspotPlayerParams", "applyCameraParams": 0,
                         "cameraSettings": {"$type": "gameTier3CameraSettings", "pitchBottomLimit": 45,
                                            "pitchSpeedMultiplier": 1, "pitchTopLimit": 60,
                                            "yawLeftLimit": 60, "yawRightLimit": 60,
                                            "yawSpeedMultiplier": 1},
                         "cameraUseTrajectorySpace": 1, "emptyHands": 0, "parallaxSpace": "Trajectory",
                         "parallaxWeight": 1, "tier": "Tier3", "vehicleProceduralCameraWeight": 1},
        "repeatCommandOnInterrupt": 0, "teleport": 1, "workExcludedGestures": [],
        "workspotInstanceId": {"$type": "scnSceneWorkspotInstanceId", "id": nid_},
        "workspotNode": noderef("")}
    # gameEntityReferenceType (live RTTI, 2026-09-26): 0 EntityRef, 1 Tag, 2 SlotID,
    # 3 SceneActorContextName. EntityRef + names never resolved our scene-spawned Mara
    # (first in-game test: IsActorInWorkspot false); names are community/spawner entry names.
    ref = dict(empty_ref, sceneActorContextName=cname(n["actor"]), type="SceneActorContextName")
    inner = {"$type": "questUseWorkspotNodeDefinition", "entityReference": ref, "id": nid_,
             "paramsV1": H(params),
             "sockets": [H({"$type": "questSocketDefinition", "connections": [], "name": cname(s), "type": ty})
                         for s, ty in (("CutDestination", "CutDestination"), ("In", "Input"),
                                       ("Success", "Output"), ("Work Started", "Output"))]}
    node = {"$type": "scnQuestNode", "ffStrategy": "automatic",
            "isockMappings": [cname("CutDestination"), cname("In")],
            "nodeId": node_id(nid_),
            "osockMappings": [cname("Success"), cname("Work Started")],
            "outputSockets": socks or [out_socket(0, []), out_socket(1, [])],
            "questNode": H(inner)}
    return ws_data, ws_inst, node


def choice_node(n, nid_, socks, item_of, host):
    # An option may carry "condition", in the same DSL the graph uses - the
    # builder is imported rather than rewritten so there is one definition of it.
    # Vanilla puts exactly this shape here: royce_default.scene gates an option
    # on questFactsDBCondition{questVarComparison_ConditionType q101_done > 0}.
    # See reference/choice_conditions.md - and read it before using this, because
    # a failing condition REMOVES the option, it does not grey it out (OI-14).
    opts = [{
        "$type": "scnChoiceNodeOption", "blueline": 0, "bluelineCondition": None,
        "caption": cname("None"), "emphasisCondition": None, "exDataFlags": 0,
        "gameplayAction": {"$type": "TweakDBID", "$storage": "uint64", "$value": "0"},
        "iconCondition": None, "iconTagIds": [], "isFixedAsRead": 0, "isSingleChoice": 0,
        "mappinReferencePointId": {"$type": "scnReferencePointId", "id": 4294967295},
        "questCondition": (build_condition(o["condition"],
                                           f"scene option {o['id']!r}")
                           if o.get("condition") else None),
        "screenplayOptionId": {"$type": "scnscreenplayItemId", "id": item_of[o["id"]]},
        "timedCondition": None, "timedParams": None, "triggerCondition": None,
        "type": {"$type": "gameinteractionsChoiceTypeWrapper", "properties": 1},
    } for o in n["options"]]
    # A hub that hangs on a POINT, not a person: the prologue's own "use this
    # object" prompts. q005_07_vip_apartment.scene ships four such hubs; node 4162
    # (caption 'użyj') is the one copied here - mode attachToWorld, the point in
    # atwParams.entityPosition RELATIVE TO THE SCENE'S LOCATION marker, a 2 m
    # interaction shape, and the Interaction/SceneDialogObjectSettings mappin
    # instead of an NPC nameplate. Extracted to questmod-research/vanilla_ex/q005_json.
    world = n.get("attachToWorld")
    wx = wy = wz = 0.0
    rng = 2.0
    if world is not None:
        wx, wy, wz = (float(v) for v in world["offset"])
        rng = float(world.get("range", 2))
    return {
        "$type": "scnChoiceNode", "alwaysUseBrainGender": 0,
        # 'mode' and 'visualizerStyle' are independent, which is not obvious from
        # their names: Hot Fuzz ships attachToActor WITH visualizerStyle onScreen.
        # The mode decides what the hub is anchored to - so the engine knows whose
        # nameplate it belongs to and where V is looking - while the style still
        # draws it as a normal screen list. Attaching costs nothing visually.
        "ataParams": {"$type": "scnChoiceNodeNsAttachToActorParams",
                      "actorId": {"$type": "scnActorId", "id": host},
                      "visualizerStyle": "onScreen"},
        "atgoParams": {"$type": "scnChoiceNodeNsAttachToGameObjectParams",
                       "nodeRef": {"$type": "NodeRef", "$storage": "uint64", "$value": "0"},
                       "visualizerStyle": "inWorld"},
        "atpParams": {"$type": "scnChoiceNodeNsAttachToPropParams",
                      "propId": {"$type": "scnPropId", "id": 4294967295},
                      "visualizerStyle": "inWorld"},
        "atsParams": {"$type": "scnChoiceNodeNsAttachToScreenParams"},
        "atwParams": {"$type": "scnChoiceNodeNsAttachToWorldParams", "customEntityRadius": 0,
                      # D158: activationYawLimit is a wedge of APPROACH directions around this
                      # orientation's forward (+Y), not V's view cone. Identity inherits the
                      # marker's yaw 45, whose forward is +v - the far wall, i.e. behind the case.
                      "entityOrientation": _yaw_quat(float(world.get("yaw", 0)) if world is not None else 0.0),
                      "entityPosition": ({"$type": "Vector3", "X": wx, "Y": wy, "Z": wz}
                                         if world is not None else
                                         {"$type": "Vector3", "X": 0, "Y": 0, "Z": 0}),
                      "visualizerStyle": "onScreen"},
        "choiceFlags": "0", "choiceGroup": cname("None"), "choicePriority": 0,
        "cpoHoldInputActionSection": 0,
        "customPersistentLine": {"$type": "scnscreenplayItemId", "id": 4294967040},
        "displayNameOverride": "", "doNotTurnOffPreventionSystem": 0,
        "ffStrategy": "automatic", "forceAttachToScreenCondition": None, "hubPriority": 0,
        "interruptCapability": "Interruptable",
        "interruptionSpeakerOverride": {"$type": "scnActorId", "id": NO_ACTOR},
        "localizedDisplayNameOverride": {"unk1": "0", "value": ""},
        "lookAtParams": H({"$type": "scnChoiceNodeNsAdaptiveLookAtParams",
                           "auxiliaryRelativePoint": {"$type": "Vector3", "X": 0, "Y": 0, "Z": 0},
                           "blendLimit": 0.300000012, "distantSlotName": cname("Chest"),
                           "nearbySlotName": cname("Head"), "referencePointFullEffectAngle": 0,
                           "referencePointFullEffectDistance": 5,
                           "referencePointNoEffectAngle": 63, "referencePointNoEffectDistance": 0,
                           "referencePoints": []}),
        "mappinParams": H({"$type": "scnChoiceNodeNsMappinParams",
                           "locationType": "Interaction" if world is not None else "Nameplate",
                           "mappinSettings": {"$type": "TweakDBID", "$storage": "string",
                                              "$value": ("MappinUISettings.SceneDialogObjectSettings"
                                                         if world is not None else
                                                         "MappinUISettings.SceneDialogNPCSettings")}}),
        # With no actor cast there is nothing in the world to hang the hub on, so
        # the generator falls back rather than emitting attachToActor at 0xFFFFFFFF.
        # D181: 'attachToScreen' in the source forces a screen hub even with an actor
        # cast. attachToActor only shows the hub within customActivationRange (3.3 m)
        # of the actor, and a Tier3 scene freezes V wherever it opened.
        "mode": ("attachToWorld" if world is not None else
                 "attachToScreen" if n.get("attachToScreen") else
                 "attachToActor" if host != NO_ACTOR else "attachToScreen"),
        "nodeId": node_id(nid_), "options": opts,
        "outputSockets": socks, "persistentLineEvents": [],
        "reminderCondition": None, "reminderParams": None,
        "shapeParams": H({"$type": "scnInteractionShapeParams", "activationBaseLength": 1,
                          "activationHeight": 3,
                          # D158: the approach wedge's width in degrees (vanilla 4162: 200)
                          "activationYawLimit": float(world.get("yaw_limit", 120)) if world is not None else 180,
                          "customActivationRange": rng if world is not None else 3.29999995,
                          "customIndicationRange": rng if world is not None else 3.29999995,
                          "offset": {"$type": "Vector3", "X": 0, "Y": 0, "Z": 0},
                          "preset": "normal",
                          "rotation": {"$type": "Quaternion", "i": 0, "j": 0, "k": 0, "r": 1}}),
        "timedParams": None, "timedSectionCondition": None,
    }


def _yaw_quat(deg):
    h = math.radians(deg) / 2
    return {"$type": "Quaternion", "i": 0, "j": 0, "k": round(math.sin(h), 6), "r": round(math.cos(h), 6)}


def main():
    if not _ACTOR_SPAWN:
        print("       !! AC_ACTOR_SPAWN=0 - actors are NOT spawned in this build.\n          This is the D86 control, not a shippable state. Rebuild without it.")
    alloc = json.loads((ROOT / "source" / "subtitle_ids.json").read_text(encoding="utf-8"))
    alloc.pop("_comment", None)
    chars = json.loads((ROOT / "source" / "characters.json").read_text(encoding="utf-8"))
    voicetags = json.loads((ROOT / "source" / "voicetags.json").read_text(encoding="utf-8"))
    voicetags.pop("_comment", None)

    for path in sorted((ROOT / "source").glob("scene_*.json")):
        stem = path.stem[len("scene_"):]
        scene = json.loads(path.read_text(encoding="utf-8"))
        root, n_lines, n_opts, n_actors = build(scene, alloc, stem, chars, voicetags)
        out = ROOT / "build" / f"ash_cache_{stem}.scene.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(envelope(root, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}  "
              f"({len(scene['nodes'])} nodes, {n_lines} lines, {n_opts} options, "
              f"{n_actors} actor(s) + player, "
              f"entry {[e['name'] for e in scene['entryPoints']]}, "
              f"exit {[e['name'] for e in scene['exitPoints']]})")
        # Say which lines stopped being a reading-speed guess. Silence here means
        # every subtitle is still timed off its character count (OI-8).
        if _vo_timed:
            print(f"       {len(_vo_timed)} of {n_lines} line(s) timed from real audio")
        mine = sorted(k for k in _vo_unmeasured if k.startswith(stem + "."))
        if mine:
            print(f"       !! {len(mine)} line(s) have audio this build cannot measure "
                  f"(not PCM): {', '.join(mine[:3])}{' ...' if len(mine) > 3 else ''}\n"
                  f"          they keep their reading-speed guess, which will not match "
                  f"the recording - see OI-8")


if __name__ == "__main__":
    main()
