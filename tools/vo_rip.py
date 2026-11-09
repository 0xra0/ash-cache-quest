#!/usr/bin/env python3
"""Rip one speaker's voice lines out of the game, as .wav, for voice training.

    tools/vo_rip.py --list                 who is in the game, by line count
    tools/vo_rip.py songbird               every Songbird line -> .wav
    tools/vo_rip.py johnny --limit 400 --mono

The game names every voice file after the character who says it:

    base\\localization\\en-us\\vo\\johnny_sq031_f_1a589ce2ca2c5000.wem
                                  ^^^^^^ ^^^^^ ^  ^^^^^^^^^^^^^^^^
                                  speaker quest |  locstring ruid, hex
                                                player gender variant

so a speaker's whole corpus is one prefix match. 110,495 English lines across
the base game and Phantom Liberty; `--list` ranks them.

The _f_ / _m_ is the PLAYER's gender, not the speaker's - the two takes of an NPC
line differ only in which V they were recorded against. For training that means
_f_ and _m_ of the same ruid are near-duplicates of each other, so --one-take
keeps whichever comes first and halves the corpus without losing any voice.

That reasoning inverts for V, and only for V. When the speaker IS the player,
the tag stops meaning "who was in the room" and starts meaning "who is talking":
14560 _f_ lines are the female V actress, 14690 _m_ lines the male V actor, and
14538 ruids ship both. --one-take there keeps whichever sorts first per line and
builds a corpus that is half one actor and half the other - a voice model
trained on it learns the average of two people and sounds like neither. Pass
--gender f or --gender m for any v* speaker. Rogue, by contrast, is 794 _f_ to
3 _m_, so the flag changes nothing for her.

.wem is Wwise's container; the payload here is Custom Vorbis, 48 kHz. vgmstream
decodes it (`vgmstream-cli`, in the repos). --mono downmixes and is what RVC
training front ends generally want.

Rule 2: the game directory is READ ONLY. Nothing here writes to it, and the
output goes under /mnt/sata (rule 3).
"""
import argparse
import collections
import pathlib
import re
import shutil
import subprocess
import sys

GAME = pathlib.Path("/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc")
ARCHIVES = [GAME / "content" / "lang_en_voice.archive", GAME / "ep1" / "lang_en_voice.archive"]
INDEX = pathlib.Path("/mnt/sata/Cyberpunk2077/vo_en_files.txt")
OUT = pathlib.Path("/mnt/sata/Cyberpunk2077/vo_corpus")
WK = ["dotnet", "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"]
ENV = {"DOTNET_ROLL_FORWARD": "LatestMajor"}

# <speaker>_<quest>_<gender>_<ruid>.wem, where <speaker> itself may hold
# underscores (victor_vector, haru_kasai, elizabeth_peralez).
NAME = re.compile(r"^(?P<speaker>.+?)_(?P<quest>q\d+[a-z]?|sq\d+|mq\d+|ep1_\w+?)?_?"
                  r"(?P<gender>[fm])_(?P<ruid>[0-9a-f]{16})\.wem$")


def build_index():
    """One line per .wem across both voice archives. ~110k lines, 8 MB, cached."""
    print(f"indexing {len(ARCHIVES)} voice archive(s) - one-off, about a minute")
    seen = set()
    for a in ARCHIVES:
        if not a.exists():
            print(f"  skipped (absent): {a}")
            continue
        r = subprocess.run(WK + ["archive", "-l", str(a)], capture_output=True,
                           text=True, env={**dict(__import__("os").environ), **ENV})
        seen.update(l.strip() for l in r.stdout.splitlines() if l.strip().endswith(".wem"))
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text("\n".join(sorted(seen)) + "\n", encoding="utf-8")
    print(f"  wrote {INDEX} ({len(seen)} files)")


def entries():
    if not INDEX.exists():
        build_index()
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        name = line.rsplit("\\", 1)[-1]
        m = NAME.match(name)
        if m:
            yield line, name, m.groupdict()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("speaker", nargs="?", help="speaker prefix, e.g. songbird, johnny, v")
    ap.add_argument("--list", action="store_true", help="rank every speaker by line count")
    ap.add_argument("--quest", help="only lines from one quest, e.g. q304")
    ap.add_argument("--limit", type=int, default=0, help="stop after N files (0 = all)")
    ap.add_argument("--one-take", action="store_true",
                    help="one gender variant per line - halves a corpus of duplicates")
    ap.add_argument("--mono", action="store_true", help="downmix to mono for RVC training")
    ap.add_argument("--gender", choices=("f", "m"),
                    help="keep only the _f_ or _m_ take - REQUIRED for V, see below")
    ap.add_argument("--include-holocall", action="store_true",
                    help="keep the vo_holocall mixes too - see the note on the filter below")
    ap.add_argument("--reindex", action="store_true", help="rebuild the file index first")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args()

    if a.reindex:
        INDEX.unlink(missing_ok=True)
    if a.list:
        tally = collections.Counter(g["speaker"] for _, _, g in entries())
        for who, n in tally.most_common(60):
            print(f"{n:7d}  {who}")
        print(f"\n{len(tally)} speakers, {sum(tally.values())} lines")
        return
    if not a.speaker:
        ap.error("name a speaker, or pass --list")

    for tool in ("vgmstream-cli",) + (("sox",) if a.mono else ()):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not installed - it decodes the .wem payload")

    picked, seen_ruid = [], set()
    for path, name, g in entries():
        if g["speaker"] != a.speaker:
            continue
        if a.quest and g["quest"] != a.quest:
            continue
        if a.gender and g["gender"] != a.gender:
            continue
        if not a.include_holocall and "vo_holocall" in path:
            continue
        if a.one_take and g["ruid"] in seen_ruid:
            continue
        seen_ruid.add(g["ruid"])
        picked.append((path, name))
        if a.limit and len(picked) >= a.limit:
            break
    if not picked:
        sys.exit(f"no lines for {a.speaker!r} - run --list to see the real names")

    out = a.out or (OUT / a.speaker)
    raw = out / "_wem"
    raw.mkdir(parents=True, exist_ok=True)
    print(f"{len(picked)} line(s) for {a.speaker!r} -> {out}")

    # One unbundle per archive with an alternation regex, not one per file: a
    # dotnet start costs ~4 s and a per-file loop would spend hours starting the
    # same program. The regex is capped so the command line stays sane.
    import os
    names = [n for _, n in picked]
    for chunk in (names[i:i + 400] for i in range(0, len(names), 400)):
        pat = ".*(" + "|".join(re.escape(n) for n in chunk) + ")$"
        for arch in ARCHIVES:
            if arch.exists():
                subprocess.run(WK + ["unbundle", str(arch), "-o", str(raw), "-r", pat],
                               capture_output=True, text=True, env={**os.environ, **ENV})

    # rglob, because the same line can live at two depot paths - vo/ and
    # vo_holocall/ hold separate mixes of one recording under the SAME file
    # name. Both decode; the second overwrites the first, so the count of
    # decodes is deliberately not the count of files.
    # vo/ and vo_holocall/ hold two DIFFERENT mixes of one recording under the
    # same file name, and the unbundle regex matches on the name, so asking for
    # a line gets both. They land in separate directories, `vo` sorts before
    # `vo_holocall`, and the loop below writes to the same .wav - so the
    # holocall take always won. It is band-limited on purpose (it is meant to
    # sound like a phone), and 451 of Songbird's 1863 lines have one. A voice
    # model trained on that mixture learns the radio filter as part of the
    # timbre. Measured across the index: 8332 names exist in both trees.
    wems = [w for w in sorted(raw.rglob("*.wem"))
            if a.include_holocall or "vo_holocall" not in str(w)]
    ok = 0
    for wem in wems:
        wav = out / (wem.stem + ".wav")
        r = subprocess.run(["vgmstream-cli", "-o", str(wav), str(wem)],
                           capture_output=True, text=True)
        if r.returncode or not wav.exists():
            continue
        if a.mono:
            # `channels 1`, not `remix 1,2`: the game ships BOTH - scene lines
            # tend to be stereo and holocall lines mono, and remix with an
            # explicit channel list fails outright on a file that already has
            # one. The rename only happens if sox actually produced something,
            # so a failure leaves the stereo original rather than nothing.
            tmp = wav.with_name(wav.stem + ".mono.wav")
            r = subprocess.run(["sox", str(wav), str(tmp), "channels", "1"],
                               capture_output=True, text=True)
            if tmp.exists() and not r.returncode:
                wav.unlink()
                tmp.rename(wav)
        ok += 1
    shutil.rmtree(raw, ignore_errors=True)

    secs = 0.0
    for wav in out.glob("*.wav"):
        p = subprocess.run(["soxi", "-D", str(wav)], capture_output=True, text=True)
        try:
            secs += float(p.stdout.strip())
        except ValueError:
            pass
    print(f"{len(list(out.glob('*.wav')))} file(s) in {out} "
          f"({ok}/{len(wems)} decoded, {secs / 60:.1f} minutes of audio)")


if __name__ == "__main__":
    main()
