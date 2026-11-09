#!/usr/bin/env python3
"""Turn a game speaker into an Applio/RVC training set, with the settings sheet.

    tools/vo_dataset.py --list
    tools/vo_dataset.py songbird --as mara          build ~35 min for model 'mara'
    tools/vo_dataset.py johnny                      model name defaults to speaker

`vo_rip.py` answers "get me this character's audio". This answers "make that
audio trainable", which is a different job with different failure modes:

  * A clip under a second is a grunt, a breath or "yeah". It carries almost no
    phonetic content and Applio's slicer still pays a file's overhead for it.
  * A clip over ~12 s is a rare monologue that dominates the loudness statistics.
  * More audio is not better. RVC plateaus somewhere around half an hour of
    clean speech; feeding it Panam's full 2161 lines makes each epoch four times
    longer for no gain, which matters a lot when the budget is one night.
  * The takes must be sampled, not taken in order. The index is sorted by depot
    path, so the first N lines of any speaker all come from one quest - one
    emotional register, one recording session, one director. Seeded shuffle
    keeps the whole performance range and stays reproducible.

What this deliberately does NOT do is trim silence. Applio's preprocessing step
owns that (`--cut-preprocess Automatic` slices on silence), and doing it twice
risks clipping plosives off the front of a word. Room tone at the head of a
line is not a defect here, it is the slicer's input.

Everything lands under /mnt/sata (rule 3) and nothing writes to the game
directory (rule 2) - the extraction is `vo_rip.py`, which only reads it.
"""
import argparse
import collections
import json
import pathlib
import random
import re
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
CORPUS = pathlib.Path("/mnt/sata/Cyberpunk2077/vo_corpus")
DATASETS = pathlib.Path("/mnt/sata/Cyberpunk2077/rvc_datasets")
INDEX = pathlib.Path("/mnt/sata/Cyberpunk2077/vo_en_files.txt")
NAME = re.compile(r"^(?P<speaker>.+?)_(?P<quest>q\d+[a-z]?|sq\d+|mq\d+|ep1_\w+?)?_?"
                  r"(?P<gender>[fm])_(?P<ruid>[0-9a-f]{16})\.wem$")
SEED = 27  # the project's sampling seed, so a rebuild gives the same set


def duration(path):
    r = subprocess.run(["soxi", "-D", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def census(gender=None):
    """Clean (vo/) line counts per speaker. Holocall rows are excluded here for
    the same reason vo_rip.py drops them: they are a band-limited mix. With a
    gender, counts only that take - which is the honest number for V, where the
    two takes are two actors rather than two recordings of one."""
    tally = collections.Counter()
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if "vo_holocall" in line:
            continue
        m = NAME.match(line.rsplit("\\", 1)[-1])
        if m and (gender is None or m.group("gender") == gender):
            tally[m.group("speaker")] += 1
    return tally


def settings_sheet(model, speaker, n_files, minutes, sample_rate):
    """The card that goes in the dataset folder.

    It names both routes on purpose. The GUI route is what the Applio tabs
    actually look like; the headless route is the same numbers as one command,
    which is the one that can run overnight without a person present.
    """
    ds = DATASETS / model
    return f"""\
+==============================================================================+
|  APPLIO / RVC TRAINING SHEET                                                 |
|  model: {model:<20}  donor voice: {speaker:<25}      |
|  dataset: {n_files:>5} files, {minutes:>5.1f} minutes, {sample_rate} Hz mono wav          |
+==============================================================================+

  dataset folder:  {ds}

+-- 1. PREPROCESS tab ---------------------------------------------------------+
|                                                                              |
|   Model Name .................. {model:<28} |
|   Dataset Path ................ (the folder above)                           |
|   Sample Rate ................. {sample_rate}                                     |
|   CPU Cores ................... (leave default)                              |
|   Cut Preprocess .............. Automatic                                    |
|   Chunk Length ................ 3.0                                          |
|   Overlap Length .............. 0.3                                          |
|   Process Effects ............. OFF   <-- IMPORTANT                          |
|   Noise Reduction ............. OFF   <-- IMPORTANT                          |
|                                                                              |
|   Why both OFF: this audio came out of a game, not a microphone. It was      |
|   already recorded in a booth, denoised and mastered. A second denoise pass   |
|   removes breath and sibilance, which is exactly the part of a voice that     |
|   makes it recognisable.                                                     |
+------------------------------------------------------------------------------+

+-- 2. EXTRACT tab ------------------------------------------------------------+
|                                                                              |
|   Model Name .................. {model:<28} |
|   Sample Rate ................. {sample_rate}                                     |
|   Pitch Extractor (f0) ........ rmvpe                                        |
|   Embedder Model .............. contentvec                                   |
|   GPU ......................... 0                                            |
|                                                                              |
|   rmvpe and contentvec are the two that are already downloaded here          |
|   (rvc/models/predictors/rmvpe.pt, rvc/models/embedders/contentvec).         |
|   Choosing crepe would start a download instead of a training run.           |
+------------------------------------------------------------------------------+

+-- 3. TRAIN tab --------------------------------------------------------------+
|                                                                              |
|   Model Name .................. {model:<28} |
|   Sample Rate ................. {sample_rate}                                     |
|   Vocoder ..................... HiFi-GAN   <-- NOT optional at {sample_rate}      |
|   Batch Size .................. 8                                            |
|   Total Epoch ................. 300                                          |
|   Save Every Epoch ............ 10                                           |
|   Save Only Latest ............ OFF                                          |
|   Save Every Weights .......... ON                                           |
|   Pretrained .................. ON                                           |
|   Cache Dataset in GPU ........ OFF                                          |
|   GPU ......................... 0                                            |
|                                                                              |
|   Vocoder is forced, not preferred. Only hi-fi-gan ships a 48000 pretrained  |
|   pair here (f0G48k.pth + f0D48k.pth); RefineGAN ships 24k and 32k only, so   |
|   picking it at 48000 means training from nothing.                           |
|                                                                              |
|   Save Only Latest is OFF so every 10th epoch is kept. A voice model does     |
|   not simply get better - it overfits, and the epoch that sounds right is     |
|   usually not the last one. Keeping them costs disk and nothing else.        |
+------------------------------------------------------------------------------+

  FIRST RUN IS SLOW AND LOOKS BROKEN. On this AMD card, MIOpen compiles a kernel
  for each new tensor shape before the first batch: several minutes stuck at
  0%, GPU at 0%, one CPU core busy, "IsEnoughWorkspace" warnings scrolling. That
  is normal and it is cached afterwards. Do not kill it.

  HEADLESS - the same settings, no GUI, survives a closed terminal:

      tools/rvc_train.sh {model}

  Output when it finishes:
      /mnt/sata/Applio/logs/{model}/{model}.pth      the voice model
      /mnt/sata/Applio/logs/{model}/*.index          the retrieval index
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("speaker", nargs="?", help="game speaker to draw the voice from")
    ap.add_argument("--as", dest="model", help="model name (default: the speaker)")
    ap.add_argument("--list", action="store_true", help="clean line counts per speaker")
    ap.add_argument("--minutes", type=float, default=35.0, help="target dataset length")
    ap.add_argument("--min-sec", type=float, default=1.2, help="drop clips shorter than this")
    ap.add_argument("--max-sec", type=float, default=12.0, help="drop clips longer than this")
    ap.add_argument("--quest", help="restrict to one quest, e.g. q301")
    ap.add_argument("--gender", choices=("f", "m"),
                    help="which take to keep - mandatory for any v* speaker")
    ap.add_argument("--keep-corpus", action="store_true",
                    help="do not delete the raw rip after the dataset is built")
    a = ap.parse_args()

    if a.list:
        for who, n in census().most_common(40):
            print(f"{n:7d}  {who}")
        return
    if not a.speaker:
        ap.error("name a speaker, or pass --list")
    for tool in ("soxi", "sox", "vgmstream-cli"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not installed")

    model = a.model or a.speaker

    # For an NPC the _f_/_m_ tag says which V was in the recording booth, so the
    # two takes are the same actor and --one-take dedupes them harmlessly. When
    # the speaker IS the player the tag says which V is talking, and the two
    # takes are two different actors: 14560 female to 14690 male, 14538 lines
    # shipping both. Building that without choosing produces a dataset that is
    # half one voice and half the other, and nothing downstream would complain -
    # the model trains, converges, and sounds like neither of them. This is the
    # one place the flag has to be mandatory rather than defaulted.
    if (a.speaker == "v" or a.speaker.startswith("v_")) and not a.gender:
        sys.exit(f"{a.speaker!r} is the player, so _f_ and _m_ are two different "
                 f"actors, not two takes of one.\n"
                 f"  --gender m   male V\n"
                 f"  --gender f   female V")

    have = census(a.gender).get(a.speaker, 0)
    if not have:
        sys.exit(f"no clean lines for {a.speaker!r} - run --list")

    # Rip more than the target needs: the duration filter throws some away, and
    # a second rip to top up would cost another pass over an 18 GB archive.
    # 4 s is roughly the average line, so this asks for about 3x the target.
    want = min(have, int(a.minutes * 60 / 4 * 3))
    rip = CORPUS / a.speaker
    cmd = [sys.executable, str(HERE / "vo_rip.py"), a.speaker,
           "--one-take", "--mono", "--limit", str(want)]
    if a.quest:
        cmd += ["--quest", a.quest]
    if a.gender:
        cmd += ["--gender", a.gender]
    print(f"[1/3] ripping up to {want} of {have} clean line(s) for {a.speaker!r}")
    t0 = time.time()
    if subprocess.run(cmd).returncode:
        sys.exit("vo_rip.py failed")
    print(f"      {time.time() - t0:.0f}s")

    print(f"[2/3] filtering {a.min_sec}-{a.max_sec}s and sampling to {a.minutes} min")
    wavs = sorted(rip.glob("*.wav"))
    graded = [(w, duration(w)) for w in wavs]
    keep = [(w, d) for w, d in graded if a.min_sec <= d <= a.max_sec]
    dropped_short = sum(1 for _, d in graded if d < a.min_sec)
    dropped_long = sum(1 for _, d in graded if d > a.max_sec)
    random.Random(SEED).shuffle(keep)

    out = DATASETS / model
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    total, picked = 0.0, []
    for w, d in keep:
        if total >= a.minutes * 60:
            break
        dest = out / w.name
        # gain -n peak-normalises. Not loudnorm: EBU R128 is a dynamic
        # process, and anything dynamic applied before training is a change to
        # the timbre the model is supposed to be learning. -3 dBFS leaves
        # headroom so no clip ends up inter-sample clipped.
        r = subprocess.run(["sox", str(w), str(dest), "gain", "-n", "-3"],
                           capture_output=True, text=True)
        if r.returncode or not dest.exists():
            continue
        picked.append((w.name, round(d, 3)))
        total += d

    if not picked:
        sys.exit(f"every clip was filtered out - loosen --min-sec/--max-sec")

    minutes = total / 60
    (out / "SETTINGS.txt").write_text(
        settings_sheet(model, a.speaker, len(picked), minutes, 48000), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({
        "model": model, "speaker": a.speaker, "quest": a.quest, "gender": a.gender,
        "built": time.strftime("%Y-%m-%d %H:%M"), "seed": SEED,
        "sample_rate": 48000, "channels": 1,
        "files": len(picked), "minutes": round(minutes, 2),
        "filter": {"min_sec": a.min_sec, "max_sec": a.max_sec,
                   "dropped_short": dropped_short, "dropped_long": dropped_long},
        "clips": picked,
    }, indent=2), encoding="utf-8")

    if not a.keep_corpus:
        shutil.rmtree(rip, ignore_errors=True)

    print(f"[3/3] {out}")
    print(f"      {len(picked)} clip(s), {minutes:.1f} min "
          f"(dropped {dropped_short} under {a.min_sec}s, {dropped_long} over {a.max_sec}s)")
    print(f"      SETTINGS.txt written - or run: tools/rvc_train.sh {model}")


if __name__ == "__main__":
    main()
