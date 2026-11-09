#!/usr/bin/env python3
"""Turn the quest's written lines into audio: TTS -> RVC -> vo/<locale>/<key>.wav.

The pipeline has three stages and only the first one has a choice in it.

    text  ->  TTS  ->  48 kHz mono  ->  RVC (the character's voice)  ->  vo/

The TTS backend is pluggable because the backends differ in one way that matters
more than quality: whether the line leaves this machine.

    espeak   local. Installed already, speaks uk and en. Robotic prosody, which
             RVC carries through - it replaces timbre, not delivery.
    piper    local. Much better, needs the .onnx models downloaded first; see
             --tts piper for where it looks.
    edge     Microsoft's network service. Sending the quest's lines to it means
             sending them to Microsoft, so it REFUSES to run without
             --allow-network. That is a decision for whoever owns the text, not
             for this script and not for whoever is running it by habit.

Nothing here touches the GPU: it blanks the visible-device variables and refuses
to start if the GPU is still there, because a trainer usually owns it.

    tools/render_lines.py --dry-run                 what it would do, and why not
    tools/render_lines.py --actor V --locale en-us  V's lines, English, local TTS
    tools/render_lines.py --tts piper --locale all
"""
import argparse
import glob
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path("/mnt/sata/Cyberpunk2077/rvc_logs/tts")
REGISTRY = ROOT / "reference" / "rvc_voices.json"
PIPER_DIRS = [pathlib.Path("/mnt/sata/Cyberpunk2077/tts_models"),
              pathlib.Path("/mnt/sata/SoniTranslate/PIPER_MODELS")]
# piper lives in its own venv on purpose. Applio is mid-training with a second run
# queued behind it; pip installing into that env risks moving torch under a job that
# has hours invested in it.
PIPER_EXES = ["/mnt/sata/Cyberpunk2077/tts_venv/bin/piper"]

# StyleTTS2-Ukrainian. Its own venv again, and CPU-only torch this time, so it
# physically cannot contend with a trainer. See tools/styletts2_render.py for why
# it is a subprocess and not a function.
STYLETTS_PY = "/mnt/sata/Cyberpunk2077/styletts_venv/bin/python"
STYLETTS_RENDER = str(ROOT / "tools" / "styletts2_render.py")

# Which locales get audio at all. Owned by gen_vomap.py, which builds the map the
# game reads, so this script cannot render a locale that would then have nowhere
# to be listed. ua-ua is subtitle-only - docs/decisions.md D42.
sys.path.insert(0, str(ROOT / "tools"))
from gen_vomap import VO_LOCALES

# How long a phoneme lasts, as a multiple of the model default. Above 1.0 is slower.
PIPER_LENGTH = 1.0

# Notes are read slower than lines are spoken. A spoken line plays against
# animation and a scene that is waiting for it, so it keeps 1.0; a shard plays
# against nothing at all, and the first pass came out at 165-220 words a minute,
# which is a man skimming. V is reading these to find out what happened. 1.15
# lands around 150, which is somebody taking it in.
NARRATION_LENGTH = 1.15

# Typographic punctuation the quest text uses that no piper alphabet contains.
# Quotation marks are not pronounced, so dropping them is what a reader does too.
TEXT_SUBST = {"\u00ab": "", "\u00bb": "", "\u201c": "", "\u201d": "",
              "\u2019": "'", "\u2018": "'", "\u2026": "...", "\u00a0": " "}

# Which trained voice speaks for which cast member. The keys are the 'actor'
# field in source/scene_*.json; the values are keys in reference/rvc_voices.json.
VOICE_OF = {"Mara": "mara", "V": "male_v",
            # D126, the opening holocall. Two speakers who are not in the room.
            #
            # "Echo" is the two seconds of recording the caller plays down the line:
            # V's own voice, saying words V never said. It maps to male_v because
            # that is not a substitution - the echo was grown off V's scan, so V's
            # model IS its voice. This is the one line in the quest that could not
            # be rendered at all while the male_v checkpoint was missing.
            #
            # "Unknown" maps to None, which means TTS with NO conversion, and that
            # is a decision rather than a gap. The caller is masking their voice; a
            # masked voice that came out sounding like a specific human being would
            # be worse, not better. None is distinct from "absent" below: an actor
            # missing from this table is a bug and gets skipped loudly, an actor
            # mapped to None renders straight from the TTS front end on purpose.
            # Do not "fix" this by pointing it at a model.
            #
            # "BlueEyes" is D130, and it is None for a reason that had to be
            # measured rather than assumed: Mr. Blue Eyes has no voiced lines
            # anywhere in the shipped game. A scan of all 110,495 English VO files
            # for his name, his record (q203_mr_x) and his appearance (gman) finds
            # blue_moon, the singer, and nothing else - he is silent in q203 and the
            # holocall scene under base\\quest\\holocalls\\mr_blue_eyes ships no audio.
            # So there is no performance to clone and no dataset to train on, and a
            # cloned voice here would be an invention wearing a citation. The TTS
            # front end IS his voice: flat, unhurried, slightly wrong. Same value as
            # "Unknown", different reason - that one is masking, this one is a man
            # nobody has ever heard.
            "Echo": "male_v", "Unknown": None, "BlueEyes": None}

# Per-locale TTS voice for each backend. The RVC model supplies the character's
# timbre, so what matters here is that the phonetics are right for the language.
# A value is either one voice for everybody, or a voice per gender. RVC shifts F0,
# but it shifts it further and less convincingly the bigger the gap, so a female
# character starts from a female read. After "#" is a named speaker inside a
# multi-speaker model.
TTS_VOICE = {
    "espeak": {"en-us": "en-us", "ua-ua": "uk"},
    # StyleTTS2 is Ukrainian only, and deliberately has no en-us entry: asking it
    # for English would get Ukrainian phonetics wrapped around English words.
    # The voice names are files in /mnt/sata/styletts2-ukrainian/voices/ and both
    # are None until somebody has LISTENED to rvc_logs/styletts_voices/ and
    # chosen. Guessing from a name is not choosing.
    "styletts2": {"ua-ua": {"m": None, "f": None}},
    "piper":  {"en-us": {"m": "en_US-ryan-high", "f": "en_US-lessac-high"},
               "ua-ua": {"m": "uk_UA-ukrainian_tts-medium#mykyta",
                         "f": "uk_UA-ukrainian_tts-medium#tetiana"}},
    "edge":   {"en-us": {"m": "en-US-GuyNeural", "f": "en-US-AriaNeural"},
               "ua-ua": {"m": "uk-UA-OstapNeural", "f": "uk-UA-PolinaNeural"}},
}

# Which gender of source read each cast member starts from.
# Which TTS front end a character starts from. The default is "m", so both D126
# voices could be left out - they are written down anyway, because "Unknown" is the
# one entry here that is NOT a statement about a person. It picks a starting timbre
# for a caller the quest never identifies, and leaving it to a default would have
# made that silence look like an oversight the next time somebody reads this table.
GENDER_OF = {"Mara": "f", "V": "m", "Echo": "m", "Unknown": "m"}

# Ukrainian stress is phonemic and not predictable from spelling, and this model was
# trained on stressed text - its id map carries U+0301 COMBINING ACUTE. Unstressed
# input does not fail; it stresses the wrong syllable, fluently and confidently.
# Measured, not assumed: the same sentence renders 2.496 s unstressed and 2.659 s
# stressed, so the mark reaches the model rather than being ignored.
STRESS_LOCALES = {"ua-ua"}
STRESS_PY = "/mnt/sata/Cyberpunk2077/tts_venv/bin/python"


def stress_all(texts):
    """Add Ukrainian stress marks to every text, in one subprocess.

    The stresser lives in the piper venv, not in Applio's environment, and loading
    its dictionary costs seconds - so this runs once for the whole batch instead of
    once per line. Returns {original: stressed}. If the package is missing this
    returns {} and the caller renders unstressed with a warning: wrong stress is a
    quality problem to be judged by ear, and not a reason to render nothing.

    Homographs stay a human's job. The stresser disambiguates by part of speech and
    will still pick "ni'chogo" where "nicho'go" was meant; both are real words.
    """
    texts = sorted(set(texts))
    if not texts:
        return {}
    src = ("import json,sys\n"
           "from ukrainian_word_stress import Stressifier, StressSymbol\n"
           "s = Stressifier(stress_symbol=StressSymbol.CombiningAcuteAccent)\n"
           "t = json.load(sys.stdin)\n"
           "json.dump({x: s(x) for x in t}, sys.stdout)\n")
    try:
        r = subprocess.run([STRESS_PY, "-c", src], input=json.dumps(texts).encode(),
                           capture_output=True, check=True)
        return json.loads(r.stdout)
    except (OSError, subprocess.CalledProcessError, ValueError) as e:
        detail = getattr(e, "stderr", b"")
        print(f"!! no Ukrainian stress marks: {type(e).__name__}. "
              f"Lines will be synthesised with default stress, which is wrong for many "
              f"words. Fix with: {STRESS_PY} -m pip install ukrainian-word-stress")
        if detail:
            print("   " + detail.decode(errors="replace").strip().splitlines()[-1])
        return {}


def tts_voice(backend, locale, actor):
    table = TTS_VOICE[backend]
    if locale not in table:
        raise RuntimeError(f"--tts {backend} has no voice for {locale}")
    v = table[locale]
    if isinstance(v, str):
        return v
    voice = v[GENDER_OF.get(actor, "m")]
    if voice is None:
        raise RuntimeError(
            f"TTS_VOICE['{backend}']['{locale}'] has no voice picked for {actor}. "
            f"Listen to /mnt/sata/Cyberpunk2077/rvc_logs/styletts_voices/ and put "
            f"the chosen name in the table - it is a judgement about how a "
            f"character sounds, and nothing here can make it.")
    return voice

# D36: leave the model's output alone. The old 0.0 rescaled RVC's output until
# its RMS matched the source, which is exactly what made the mara verification a
# tautology - it could not have failed.
INFER = dict(pitch=0, index_rate=0.5, volume_envelope=1.0, protect=0.33,
             f0_method="rmvpe", embedder_model="contentvec")

APPLIO = "/mnt/sata/Applio"
APPLIO_PY = "/mnt/sata/anaconda3/envs/Applio/bin/python"


def lines_of(locale):
    """Every spoken line as (key, actor, text), in scene order.

    "lines" AND "options", because a choice here is not a wheel paraphrase with a
    spoken line waiting behind it - the option text IS V's line ("Then start
    talking. What's in the box?") and no other node carries it. validate.py has
    always counted both, which is where its 43 comes from; reading only "lines"
    gives 29, renders them, reports success, and leaves V mute for a third of the
    quest. Options have no "actor" field, and V is the default for that reason.
    """
    out = []
    for p in sorted(ROOT.glob("source/scene_*.json")):
        stem = p.stem[len("scene_"):]
        d = json.loads(p.read_text(encoding="utf-8"))
        for n in d["nodes"]:
            for l in list(n.get("lines", [])) + list(n.get("options", [])):
                text = l.get(locale)
                if text:
                    out.append((f"{stem}.{l['id']}", l.get("actor", "V"), text))
    return out


def narration_text(text):
    """A shard body as something a voice can read straight through.

    Shard bodies are laid out for the eye - paragraph breaks, and bracketed
    headers that are labels ON the document rather than sentences IN it. Two of
    those features have to be dealt with here, and the first one is not obvious.

    Piper's CLI treats ONE LINE as ONE utterance and writes each one to the file
    named by -f. Hand it a five-paragraph shard and the last paragraph overwrites
    the previous four: a forty-second note that plays as its own closing
    sentence. Well-formed audio of the wrong text, with nothing in any log - the
    exact failure class this project keeps finding. So the newlines are collapsed
    here, before any backend sees them, and never left to a backend's goodwill.

    The brackets go because a person reading aloud says "VOSS slash private" and
    not "open square bracket". The words inside them stay, because V is reading a
    document that has a header on it. A paragraph that does not already end in
    terminal punctuation gets a full stop, so it lands as its own sentence
    instead of running into the line below; and a dash left dangling at either
    end is an interruption on the page, not a sound.
    """
    out = []
    for para in re.split(r"\n+", text.strip()):
        para = para.strip()
        if para.startswith("[") and para.endswith("]"):
            para = para[1:-1]
        para = para.replace("[", "").replace("]", "").strip()
        # A dash at either end is an interruption on the page. Leading, it is the
        # start of a recording already in progress and the reader simply begins.
        # Trailing, the speaker was cut off - which is an ellipsis to a voice, not
        # a full stop. "Take the-" read as "Take the." is a man finishing his
        # sentence, and the whole point of that line is that he did not.
        para = para.lstrip(" -—–")
        cut = para.rstrip() != para.rstrip(" -—–")
        para = para.rstrip(" -—–")
        if not para:
            continue
        if cut:
            para += "..."
        elif para[-1] not in ".!?":
            para += "."
        out.append(para)
    return " ".join(out)


def already(dst, is_shard):
    """Has this one been rendered? The marker differs, and it matters.

    For a spoken line the .wem beside the .wav is the marker, because the .wav
    is only an intermediate: a run that produced a .wav and died before
    converting it has NOT delivered the line, and re-running must finish it.

    A shard has no .wem and never will - Audioware reads the .wav itself, and
    the engine has no voiceover path to a journal entry to convert it for. Its
    .wav is the deliverable, so its .wav is the marker. Asking for a .wem here
    would find none, re-render all five notes on every run, and hide a failure
    by drowning it in work that always looks like work.
    """
    return dst.exists() if is_shard else dst.with_suffix(".wem").exists()


def shards_of(locale):
    """Every note V can pick up and read, as (onscreen entry, actor, text).

    The text is the shard body itself - the same string the journal draws, not a
    second script written for the voice. That IS the beat: V reads what is in
    front of him. It also means this list needs no upkeep and can never drift
    from what is on screen, and that a note added later is voiced by writing
    nothing new.

    Keyed by the onscreen entry rather than the item id because the audio belongs
    to the text, and mara_autopsy_shot / mara_autopsy_cut are two items whose
    whole difference is which body the player ends up reading.
    """
    items = json.loads((ROOT / "source" / "items.json").read_text(encoding="utf-8"))
    strings = json.loads((ROOT / "source" / "strings.json").read_text(encoding="utf-8"))
    out = []
    for it in items["items"]:
        if it.get("kind") != "shard":
            continue
        entry = it["onscreen"]
        text = (strings.get(entry["body"]) or {}).get(locale)
        if text:
            out.append((entry["entry"], "V", narration_text(text)))
    return out


def tts_espeak(text, voice, out_wav):
    subprocess.run(["espeak-ng", "-v", voice, "-s", "145", "-p", "45",
                    "-w", str(out_wav), text], check=True, capture_output=True)


def piper_model(voice):
    for d in PIPER_DIRS:
        p = d / f"{voice}.onnx"
        if p.exists() and (d / f"{voice}.onnx.json").exists():
            return p
    return None


def piper_text(text, cfg):
    """Prepare text for a piper model that eats characters instead of phonemes.

    `phoneme_type: "text"` means there is no espeak stage - every character goes
    straight into the id map, and anything absent is DROPPED with nothing but a log
    line. The Ukrainian model's alphabet is lowercase only, so left alone it would
    delete every sentence-initial capital and every proper noun in the script - 22
    distinct letters in this one - and still hand back confident, fluent audio for
    the wrong words. Measured, not guessed: piper logged "Missing phoneme from id
    map" for the first two letters of the first Ukrainian line rendered here.

    Returns the prepared text and the set of characters it still cannot say.
    """
    if cfg.get("phoneme_type") != "text":
        return text, set()          # espeak normalises for the phoneme models
    text = text.lower()
    for a, b in TEXT_SUBST.items():
        text = text.replace(a, b)
    return text, {c for c in text if c not in cfg.get("phoneme_id_map", {})}


def tts_piper(text, voice, out_wav):
    voice, _, speaker = voice.partition("#")
    model = piper_model(voice)
    if model is None:
        raise RuntimeError(
            f"no piper model {voice}.onnx (+ .json) in "
            f"{' or '.join(str(d) for d in PIPER_DIRS)}")
    exe = next((e for e in PIPER_EXES if os.access(e, os.X_OK)),
               shutil.which("piper") or shutil.which("piper-tts"))
    if not exe:
        raise RuntimeError("piper is not installed; --tts espeak works with no download")

    cfg = json.loads((model.parent / (model.name + ".json")).read_text(encoding="utf-8"))
    text, missing = piper_text(text, cfg)
    if missing:
        raise RuntimeError(
            f"{voice} has no phoneme for {sorted(missing)} - piper would drop those "
            f"characters and synthesise the rest as if the line were complete. Add a "
            f"substitution to TEXT_SUBST or fix the text.")

    cmd = [exe, "-m", str(model), "-f", str(out_wav),
           "--length-scale", str(PIPER_LENGTH)]
    if speaker:
        smap = cfg.get("speaker_id_map") or {}
        if speaker not in smap:
            raise RuntimeError(f"{voice} has no speaker {speaker!r}; it has {sorted(smap)}")
        cmd += ["-s", str(smap[speaker])]
    subprocess.run(cmd, input=text.encode(), check=True, capture_output=True)


def tts_edge(text, voice, out_wav):
    import asyncio
    sys.path.insert(0, "/mnt/sata/anaconda3/envs/SoniTranslate/lib/python3.10/site-packages")
    import edge_tts
    mp3 = out_wav.with_suffix(".mp3")
    asyncio.run(edge_tts.Communicate(text, voice).save(str(mp3)))
    to_48k(mp3, out_wav)


def styletts2_prepass(jobs):
    """Synthesise every StyleTTS2 line in ONE subprocess, before the RVC loop.

    StyleTTS2 spends tens of seconds loading its checkpoint and under a second
    saying a five-character line, so per-line invocation would be almost entirely
    startup. It also needs an interpreter this script cannot be: torch 2.8 +
    transformers 5, versus the Applio env this script re-execs into. One
    subprocess for the batch solves both.
    """
    if not jobs:
        return
    if not os.access(STYLETTS_PY, os.X_OK):
        raise RuntimeError(
            f"no interpreter at {STYLETTS_PY}. StyleTTS2 needs its own venv - see "
            f"docs/decisions.md D41 for what goes in it.")
    r = subprocess.run([STYLETTS_PY, STYLETTS_RENDER],
                       input=json.dumps(jobs, ensure_ascii=False).encode(),
                       capture_output=True)
    tail = r.stdout.decode(errors="replace").strip().splitlines()
    for line in tail[-2:]:
        print("  " + line)
    if r.returncode != 0:
        err = r.stderr.decode(errors="replace").strip().splitlines()
        raise RuntimeError("styletts2 failed:\n   " + "\n   ".join(err[-6:]))


def tts_styletts2(text, voice, out_wav):
    """A no-op with teeth: styletts2_prepass already wrote this file.

    Raising rather than silently re-rendering matters. If the prepass skipped a
    line - empty phonemisation, a missing style - the loop would otherwise carry
    on and RVC would convert whatever stale audio happened to be at that path.
    """
    if not pathlib.Path(out_wav).exists():
        raise RuntimeError(f"the batch prepass produced nothing for {out_wav}")


# D191: FireRedTTS3 clones the cast member from one reference clip, so its output IS
# the character's voice and the RVC stage is skipped for it. Only the actors named
# here are FireRed voices; anyone else (Unknown, BlueEyes - D126) is left out of a
# firered run and keeps whatever render they already have, because mapping them to a
# clone would give a caller nobody identifies somebody else's face.
FIRERED_PY = "/mnt/sata/anaconda3/envs/fireredtts3/bin/python"
FIRERED_RENDER = str(ROOT / "tools" / "firered_render.py")
FIRERED_VOICES = ROOT / "reference" / "firered_voices.json"
FIRERED_OF = {"Mara": "mara", "V": "v_male", "Echo": "v_male"}


def firered_prepass(jobs, env):
    """Every FireRed line in ONE subprocess, before the loop - as styletts2_prepass.

    `env` is the environment from BEFORE the GPU was hidden: this backend needs it,
    and main() has already refused to run if a trainer holds it.
    """
    if not jobs:
        return
    if not os.access(FIRERED_PY, os.X_OK):
        raise RuntimeError(f"no interpreter at {FIRERED_PY} (conda env fireredtts3)")
    r = subprocess.run([FIRERED_PY, FIRERED_RENDER],
                       input=json.dumps(jobs, ensure_ascii=False).encode(), env=env)
    if r.returncode != 0:
        raise RuntimeError(f"firered_render.py failed (exit {r.returncode})")


BACKENDS = {"espeak": tts_espeak, "piper": tts_piper, "edge": tts_edge,
            "styletts2": tts_styletts2, "firered": tts_styletts2}
NETWORK = {"edge"}
# Backends whose stress marks come from their own front end. StyleTTS2 runs
# stress -> IPA internally, so pre-stressing here would double-accent the text.
OWN_STRESS = {"styletts2"}


def to_48k(src, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
                   check=True)


_warned = set()   # one uncertified-voice warning per run, not one per line


def newest_checkpoint(pattern):
    """The highest-epoch checkpoint matching a glob, or None.

    Sorted on the epoch NUMBER, never lexically. `sorted(glob)[-1]` looks
    equivalent and picks mara_90e over mara_200e, because "9" > "2" as text.
    rvc_check_model.py:157-159 already sorts this way; this is the same rule
    deliberately spelled the same, because the whole point of the pattern is
    that the gate and the renderer land on the SAME file. See D45.
    """
    hits = glob.glob(pattern)
    if not hits:
        return None
    def epoch(p):
        m = re.search(r"_(\d+)e_", os.path.basename(p))
        return int(m.group(1)) if m else -1
    return sorted(hits, key=epoch)[-1]


def voice_paths(key):
    """(pth, index) for a registry voice, or a reason it cannot be used.

    A `pth` containing "*" is a POINTER AT A TRAINING RUN rather than at one
    file, and resolves to the newest epoch present when the render actually
    starts. That indirection exists because of a real near-miss (D45): the
    registry named a specific quarantined checkpoint while the overnight chain
    health-gated whatever was newest under Applio/logs, so the two files
    disagreed about which Mara existed. render_lines skipped all 18 Mara lines,
    exited 0, and the chain printed "VERDICT: clean" over a batch missing 42%
    of the quest. A glob cannot drift from the gate: both pick the newest epoch
    in the same directory by the same rule.

    It also means a run that stops early is still renderable - the pattern finds
    epoch 120 instead of 200 - which is correct, because the health gate, not
    the filename, is what decides whether a checkpoint is usable.
    """
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["voices"]
    if key not in reg:
        return None, None, f"reference/rvc_voices.json has no voice {key!r}"
    v = reg[key]
    status = str(v.get("status", ""))
    if status.startswith("BROKEN"):
        return None, None, f"{key} is quarantined: {status.split('.')[0]}"
    pth = (v.get("pth") or "").split("  ")[0].strip()
    idx = (v.get("index") or "").split("  ")[0].strip()
    if "*" in pth:
        found = newest_checkpoint(pth)
        if not found:
            return None, None, f"{key}: no checkpoint matches {pth} yet"
        pth = found
    if "*" in idx:
        idx = newest_checkpoint(idx) or ""
    if not pth or not os.path.exists(pth):
        return None, None, f"{key} has no usable .pth yet ({v.get('pth')})"
    # Not a certified voice: say so on every render rather than in a file nobody
    # opens. The chain health-gates before it calls this; a person running the
    # renderer by hand gets no gate at all, and silence here would read as one.
    if not status.startswith(("VERIFIED", "DOWNLOADED")) and key not in _warned:
        _warned.add(key)
        print(f"  !! {key}: {os.path.basename(pth)} is NOT certified ({status.split('.')[0]}).\n"
              f"     Gate it before trusting the output:  tools/rvc_check_model.py {key}")
    return pth, (idx if idx and os.path.exists(idx) else ""), None


def reexec_under_applio():
    """RVC lives in the Applio env, so this script must run on that python.

    Re-exec rather than document it: running it with the system python fails at
    `import torch`, thirty seconds and one TTS pass into the job, which is a
    confusing place to learn about an interpreter. The env var stops a loop if
    the Applio python somehow has no torch either.
    """
    if os.environ.get("_RENDER_LINES_REEXEC"):
        return
    try:
        import torch  # noqa: F401
        return
    except ImportError:
        pass
    if not os.path.exists(APPLIO_PY):
        sys.exit(f"no torch here and no {APPLIO_PY} to borrow it from")
    os.environ["_RENDER_LINES_REEXEC"] = "1"
    os.execv(APPLIO_PY, [APPLIO_PY, os.path.abspath(__file__)] + sys.argv[1:])


def main():
    reexec_under_applio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", default="en-us", choices=["en-us", "ua-ua", "all"])
    ap.add_argument("--tts", default="espeak", choices=sorted(BACKENDS))
    ap.add_argument("--actor", help="only this actor, e.g. Mara")
    ap.add_argument("--only", help="only this subtitle key")
    ap.add_argument("--allow-network", action="store_true",
                    help="permit a TTS backend that sends the text off this machine")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-render existing files")
    ap.add_argument("--out", help="write somewhere other than vo/ - use this to audition a "
                                  "backend without the result becoming the shipped voice")
    ap.add_argument("--shards", action="store_true",
                    help="render the NOTES instead of the spoken lines: every shard body, "
                         "in V's voice, into narration/<locale>/. These are played by the "
                         "Audioware bank alone - no .wem, nothing in the archive - because "
                         "the engine has no voiceover path for a journal entry at all.")
    ap.add_argument("--no-rvc", action="store_true",
                    help="ship the TTS voice as-is instead of converting it to the "
                         "character's timbre. This is the right answer for a language "
                         "the RVC model has never heard: RVC learned its phonetics from "
                         "the target's recordings, so an English-only target speaks "
                         "every other language with an English accent.")
    a = ap.parse_args()

    if a.tts in NETWORK and not a.allow_network:
        sys.exit(
            f"--tts {a.tts} sends every line to a third party. Nothing in this quest\n"
            f"has been sent anywhere, and that is a decision for whoever owns the\n"
            f"text. Pass --allow-network to make it deliberately, or use\n"
            f"--tts espeak (local, installed) or --tts piper (local, needs models).")

    outdir = pathlib.Path(a.out).resolve() if a.out else None
    # Auditioning any locale is fine - that is what --out is for. Rendering one
    # INTO vo/ that gen_vomap will never map is not: the files would sit in the
    # archive, cost space, and never play.
    locales = list(VO_LOCALES) if a.locale == "all" else [a.locale]
    if outdir is None:
        unshipped = [x for x in locales if x not in VO_LOCALES]
        if unshipped:
            sys.exit(
                f"{', '.join(unshipped)} is subtitle-only: the game ships no voice\n"
                f"archive for it and the RVC targets are English-only, so nothing\n"
                f"here would ever be played. See docs/decisions.md D42.\n"
                f"To audition it anyway, give --out somewhere outside vo/.")
    # narration/ is a separate drop folder, not a vo/ subfolder, and deliberately
    # so: validate.py treats every directory under vo/ as a locale that must ship
    # voiceover, which is a guard worth keeping rather than carving an exception
    # into. The two folders also have nothing in common downstream - vo/ is
    # converted to .wem, packed into the archive and mapped by locVoiceoverMap;
    # narration/ is none of those things.
    base = pathlib.Path(a.out).resolve() if a.out else \
        ROOT / ("narration" if a.shards else "vo")
    if a.shards:
        global PIPER_LENGTH
        PIPER_LENGTH = NARRATION_LENGTH
    todo, skipped = [], []
    for locale in locales:
        for key, actor, text in (shards_of(locale) if a.shards else lines_of(locale)):
            if a.actor and actor != a.actor:
                continue
            if a.only and key != a.only:
                continue
            if a.tts == "firered":
                # D191: the clone is the voice - no RVC model to find or load.
                if actor not in FIRERED_OF:
                    skipped.append((locale, key, f"{actor} is not a FireRed voice"))
                else:
                    todo.append((locale, key, actor, text, "", ""))
                continue
            if a.no_rvc:
                # No conversion step, so a missing or quarantined .pth is not a
                # reason to skip the line - there is nothing to load.
                todo.append((locale, key, actor, text, "", ""))
                continue
            if actor not in VOICE_OF:
                skipped.append((locale, key, f"no voice mapped for actor {actor!r}"))
                continue
            vkey = VOICE_OF[actor]
            if vkey is None:
                # Mapped to nothing ON PURPOSE - see VOICE_OF. The empty .pth is
                # the same signal --no-rvc uses, and it is read per line below, so
                # one unconverted speaker does not turn conversion off for the rest
                # of the cast sharing this run.
                todo.append((locale, key, actor, text, "", ""))
                continue
            pth, idx, why = voice_paths(vkey)
            if why:
                skipped.append((locale, key, why))
                continue
            todo.append((locale, key, actor, text, pth, idx))

    print(f"{len(todo)} line(s) to render, {len(skipped)} skipped")
    if skipped:
        reasons = {}
        for locale, key, why in skipped:
            reasons.setdefault(why, []).append(f"{locale}/{key}")
        for why, keys in reasons.items():
            print(f"  skip {len(keys):3}: {why}")
    if a.dry_run or not todo:
        for locale, key, actor, text, _, _ in todo[:5]:
            print(f"  would render {locale}/{key} ({actor}): {text[:52]}...")
        return 0

    # Only piper reads the stress marks: they are characters in ITS alphabet. espeak
    # and edge do their own normalisation and have not been shown to want them.
    stress = {}
    if a.tts == "piper" and a.tts not in OWN_STRESS:
        stress = stress_all([t for loc, _, _, t, _, _ in todo if loc in STRESS_LOCALES])
        if stress:
            print(f"stress-marked {len(stress)} Ukrainian line(s)")

    # A trainer usually owns the GPU. Never contend with it - that is what
    # destroyed the first mara model. FireRed needs the GPU itself, so it gets a
    # copy of the environment from before it was hidden - and only if no trainer
    # is running.
    gpu_env = dict(os.environ)
    if a.tts == "firered" and subprocess.run(
            ["pgrep", "-f", "rvc/train/train[.]py"], capture_output=True).returncode == 0:
        sys.exit("refusing --tts firered: an RVC trainer holds the GPU")
    for v in ("CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES"):
        os.environ[v] = ""
    sys.path.insert(0, APPLIO)
    import torch
    if torch.cuda.is_available():
        sys.exit("refusing to run: the GPU is still visible and may be training")
    run_infer_script = None
    if not a.no_rvc:
        # chdir only for RVC: Applio resolves its own model paths relative to its
        # tree. --out may be a relative path the caller typed, so it is made
        # absolute above rather than left to survive a chdir it never expected.
        os.chdir(APPLIO)
        from core import run_infer_script
    sys.path.insert(0, str(ROOT / "tools"))
    import wav_to_wem

    if a.tts == "styletts2":
        prepass = []
        for locale, key, actor, text, _, _ in todo:
            raw = WORK / locale / f"{key}.tts.wav"
            if already(base / locale / f"{key}.wav", a.shards) and not a.force:
                continue
            raw.parent.mkdir(parents=True, exist_ok=True)
            prepass.append({"text": text, "voice": tts_voice(a.tts, locale, actor),
                            "out": str(raw)})
        print(f"styletts2 prepass: {len(prepass)} line(s) in one process")
        styletts2_prepass(prepass)

    if a.tts == "firered":
        voices = json.loads(FIRERED_VOICES.read_text(encoding="utf-8"))
        prepass = []
        for locale, key, actor, text, _, _ in todo:
            if already(base / locale / f"{key}.wav", a.shards) and not a.force:
                continue
            ref = voices[FIRERED_OF[actor]]
            prepass.append({"text": text, "ref_wav": ref["wav"], "ref_text": ref["text"],
                            "out": str(WORK / locale / f"{key}.tts.wav"),
                            "seed": ref.get("seed", 1234), "cfg": ref.get("cfg", 2.0),
                            "steps": ref.get("steps", 10)})
        print(f"firered prepass: {len(prepass)} line(s) in one process")
        firered_prepass(prepass, gpu_env)

    n = 0
    for locale, key, actor, text, pth, idx in todo:
        raw = WORK / locale / f"{key}.tts.wav"
        src = WORK / locale / f"{key}.48k.wav"
        dst = base / locale / f"{key}.wav"
        wem = dst.with_suffix(".wem")
        if already(dst, a.shards) and not a.force:
            continue
        raw.parent.mkdir(parents=True, exist_ok=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        voice = "" if a.tts == "firered" else tts_voice(a.tts, locale, actor)
        BACKENDS[a.tts](stress.get(text, text), voice, raw)
        to_48k(raw, src)
        if run_infer_script is None or not pth:
            # The TTS voice IS the shipped voice, either because --no-rvc turned
            # conversion off for the whole run or because this actor is mapped to
            # no model on purpose (VOICE_OF, D126). Still resampled, because the
            # game's voice lines decode as 48 kHz mono and the .wem writer takes
            # that rate as given rather than checking it.
            shutil.copyfile(src, dst)
        else:
            run_infer_script(input_path=str(src), output_path=str(dst),
                             pth_path=pth, index_path=idx,
                             split_audio=False, f0_autotune=False, f0_autotune_strength=1.0,
                             proposed_pitch=False, proposed_pitch_threshold=155.0,
                             clean_audio=False, clean_strength=0.5,
                             export_format="WAV", **INFER)
        if a.shards:
            pass
        elif outdir:
            # An audition. Nothing downstream reads this .wem, but it is what the
            # batch would ship as, which is the point of auditioning.
            wav_to_wem.convert(dst, wem, 48000, 1)
        elif wem.exists():
            # Rendering STRAIGHT INTO vo/, where writing a .wem here is a trap
            # rather than a saving (D126a). wav_to_wem.py writes PCM, fmt tag
            # 0xFFFE; tools/wwise_wem.py writes real Wwise Vorbis, 0xFFFF, and
            # runs FIRST in build.sh precisely so Wwise wins where Wwise is
            # installed. But both skip a .wem that is newer than its .wav, so a
            # .wem written here is already "current" and Wwise never gets to
            # touch it - the line then ships PCM on the locVoiceoverMap path,
            # which is the silence this whole chain exists to avoid.
            # vo_promote.py has always deleted the .wem for exactly this reason;
            # a render straight into vo/ simply never went through it. So: leave
            # the .wav, clear any stale .wem, let the build do the conversion.
            wem.unlink()
        n += 1
        # Name what this call actually left on disk. Into vo/ that is the .wav;
        # the .wem beside it is the build's to make, with Wwise.
        out_name = wem.name if (outdir and not a.shards) else dst.name
        print(f"  {locale}/{key:28} {actor:5} -> {dst.parent}/{out_name}")
    if outdir:
        print(f"rendered {n} line(s) into {outdir} - an audition, not the shipped voice. "
              f"Listen before copying any of it into vo/.")
    else:
        print(f"rendered {n} line(s). Run tools/validate.py, then tools/build.sh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
