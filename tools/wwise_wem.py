#!/usr/bin/env python3
"""vo/<locale>/*.wav -> real Wwise Vorbis .wem, using the installed Wwise.

    tools/wwise_wem.py                  convert every stale .wav under vo/
    tools/wwise_wem.py --force          reconvert everything
    tools/wwise_wem.py --check          say whether Wwise is usable, convert nothing

WHY THIS EXISTS ALONGSIDE wav_to_wem.py
wav_to_wem.py writes a PCM .wem with no Wwise at all, and its header is honest
about the hole in that: PCM is proven on the soundbank-media path and NOT on the
locVoiceoverMap path, where all 342 custom voice lines across the installed mods
are Wwise Vorbis. This tool closes that hole - the output here has the same
`fmt` tag 0xFFFF as every shipped custom line, because it came out of the same
encoder.

Wwise 2023.1.14 now runs in the Wine prefix at /mnt/sata/wwise/prefix (D89-D91).
The guides all describe the GUI: new project, Project Settings -> Source
Settings -> Vorbis Quality High, Import Audio Files as Sound SFX, ShareSets ->
Convert. That is not needed. WwiseConsole.exe ships in the same Authoring tree
and does the whole thing headlessly through EXTERNAL SOURCES - Wwise's own batch
route for audio a game provides at runtime, which is exactly what a vomap entry
is: a .wem named by path that no project object references. No hierarchy, no
Sound SFX objects, no saved project state to keep in sync.

The conversion ShareSet is the factory "Vorbis Quality High" the guide names.
Its Channels and SampleRate both read "as input", which the guide papers over by
having you set Mono / 48000 by hand - our sources come out of RVC at 48 kHz mono
already, so "as input" lands on the same numbers. Anything dropped in vo/ at a
different rate follows its source; if that ever matters, the ShareSet is the one
place to change it, in the project below.

WHAT IT LEAVES ALONE
Same rule as wav_to_wem.py: a .wem with no source file beside it was hand-made
and is never touched. A .wem newer than its .wav is current and is skipped, so a
build is cheap. --force is the way to redo one after changing the ShareSet.

ORDER IN THE BUILD
This runs BEFORE wav_to_wem.py, which then finds every .wem current and skips
it. So Wwise wins where Wwise is installed, and the PCM fallback still covers a
machine that has none - which is the whole reason wav_to_wem.py stays.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_vomap import VO_LOCALES, split_stem

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The Wine side. WwiseConsole is a Windows exe; wc.sh is the two-line runner
# that sets WINEPREFIX and the powershell override before exec'ing it.
CONSOLE = pathlib.Path(os.environ.get("WWISE_CONSOLE", "/mnt/sata/wwise/wc.sh"))
PREFIX = pathlib.Path(os.environ.get("WINEPREFIX", "/mnt/sata/wwise/prefix"))
# A throwaway project. It holds nothing but the factory conversion ShareSets and
# a .cache - every .wem this tool makes lands in vo/, never in here.
PROJECT_HOST = PREFIX / "drive_c" / "wwproj" / "ashcache" / "ashcache.wproj"
PROJECT_WIN = r"C:\wwproj\ashcache\ashcache.wproj"
SHARESET = "Vorbis Quality High"
PLATFORM = "Windows"
# Wwise only imports .wav. wav_to_wem.py accepts anything ffmpeg reads because
# ffmpeg is doing the decoding there; here the encoder is the limit, so a .mp3
# in vo/ is left for the fallback rather than silently mis-handled.
SOURCES = (".wav",)

# The scratch list Wwise reads. Not in vo/ - vo/ is a manifest, and a stray
# non-audio file in it is a mistake by design.
WSOURCES = pathlib.Path("/mnt/sata/wwise/conv")


def win(p):
    r"""A host path as Wine sees it. z: -> / in every prefix Wine creates."""
    return "Z:" + str(p).replace("/", "\\")


def available():
    """(ok, why not). Everything this needs, checked before anything is written."""
    if not CONSOLE.exists():
        return False, f"no WwiseConsole runner at {CONSOLE}"
    if not shutil.which("wine"):
        return False, "wine is not installed"
    if not PREFIX.is_dir():
        return False, f"no Wine prefix at {PREFIX}"
    return True, ""


def run(args, what):
    r = subprocess.run([str(CONSOLE), *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{what} failed (rc={r.returncode}):\n"
                 f"{(r.stdout + r.stderr).strip()}")
    return r.stdout


def ensure_project():
    """create-new-project refuses to overwrite, so ask only when it is missing."""
    if PROJECT_HOST.exists():
        return
    PROJECT_HOST.parent.parent.mkdir(parents=True, exist_ok=True)
    print(f"  creating Wwise project {PROJECT_WIN}")
    run(["create-new-project", PROJECT_WIN, "--platform", PLATFORM, "--quiet"],
        "create-new-project")


def convert(jobs, out_dir):
    """jobs: [(src, dst_name)] all under one directory -> .wem in out_dir."""
    root = jobs[0][0].parent
    WSOURCES.mkdir(parents=True, exist_ok=True)
    lst = WSOURCES / f"{out_dir.name}.wsources"
    body = "".join(
        f'  <Source Path="{src.name}" Conversion="{SHARESET}" '
        f'Destination="{dst}"/>\n' for src, dst in jobs)
    lst.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<ExternalSourcesList SchemaVersion="1" Root="{win(root)}">\n'
        f'{body}</ExternalSourcesList>\n', encoding="utf-8")

    # --no-wwise-dat: without it Wwise drops a Wwise.dat dependency file in the
    # output folder, and the output folder here is vo/<locale>/, which must hold
    # audio and nothing else. Staleness is decided by mtime above instead.
    run(["convert-external-source", PROJECT_WIN,
         "--source-file", win(lst),
         "--output", PLATFORM, win(out_dir),
         "--platform", PLATFORM, "--no-wwise-dat", "--quiet"],
        f"convert-external-source ({len(jobs)} file(s))")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="reconvert even when the .wem is newer than its source")
    ap.add_argument("--check", action="store_true",
                    help="report whether Wwise is usable and exit")
    a = ap.parse_args()

    ok, why = available()
    if a.check:
        print(f"wwise: {'ready' if ok else 'unavailable - ' + why}")
        return
    if not ok:
        # Not an error. wav_to_wem.py runs next and covers this case; saying so
        # out loud is the point, because a silent skip here means PCM .wem and
        # nobody would know which encoder made the file they are testing.
        print(f"wwise: unavailable - {why}; leaving it to tools/wav_to_wem.py")
        return

    # Same guard as wav_to_wem.py, and for the same reason: a .wav whose stem
    # names no line would otherwise get a .wem that fails the build later, from
    # a folder away.
    keys = json.loads((ROOT / "source" / "subtitle_ids.json").read_text(encoding="utf-8"))
    keys.pop("_comment", None)

    made = skipped = 0
    created = False
    for locale in VO_LOCALES:
        d = ROOT / "vo" / locale
        if not d.is_dir():
            continue
        jobs = []
        for src in sorted(p for p in d.iterdir() if p.suffix.lower() in SOURCES):
            key, _ = split_stem(src.stem)
            if key not in keys:
                sys.exit(f"vo/{locale}/{src.name} names no line in "
                         f"source/subtitle_ids.json")
            dst = src.with_suffix(".wem")
            if dst.exists() and not a.force and dst.stat().st_mtime >= src.stat().st_mtime:
                skipped += 1
                continue
            jobs.append((src, dst.name))
        if not jobs:
            continue
        if not created:
            ensure_project()
            created = True
        print(f"  vo/{locale}: encoding {len(jobs)} file(s) as {SHARESET}")
        convert(jobs, d)
        for src, name in jobs:
            out = d / name
            if not out.exists():
                sys.exit(f"Wwise reported success but did not write {out}")
            made += 1
            print(f"    {src.name} -> {name}  "
                  f"({out.stat().st_size // 1024} KiB, "
                  f"{100 * out.stat().st_size // max(src.stat().st_size, 1)}% of source)")

    if made or skipped:
        print(f"wwise: {made} encoded, {skipped} already current")
    else:
        print("wwise: nothing to convert")


if __name__ == "__main__":
    main()
