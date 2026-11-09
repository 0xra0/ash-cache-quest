#!/usr/bin/env python3
"""Move an audition batch into vo/, once a person has heard it.

    tools/vo_promote.py /mnt/sata/Cyberpunk2077/rvc_logs/audition_final/2026-09-04
    tools/vo_promote.py <dir> --dry-run          show what would move, touch nothing
    tools/vo_promote.py <dir> --yes              actually copy

WHY A TOOL AND NOT `cp`
Copying 43 files is not the hard part. Noticing that you copied 30 is. The drop
folder IS the manifest (vo/README.md), which is a good design with one sharp
edge: an INCOMPLETE batch is indistinguishable from a deliberate one. Thirteen
missing lines do not fail the build, do not warn, and do not appear in any log -
they play as a subtitle over silence, three hours into a playthrough. Every check
here exists because `cp` cannot make it:

  complete   every line the locale has text for has audio. A render that died at
             line 30 is the likeliest way this batch is wrong, and the only place
             it can still be caught cheaply is here.
  measured   rvc_audition must pass on the batch, freshly, now. Not "it passed
             when it was rendered" - the log is from hours ago and the directory
             is editable. A railed model emits full-length files of confident
             noise, so file COUNT proves nothing at all.
  right dir  a locale outside VO_LOCALES is skipped, not copied. Auditioning
             ua-ua is supported and useful; shipping it is a build error (D42).
  no .wem    only sources are copied, and any .wem already in vo/ for a promoted
             key is deleted first. See below - this one is subtle.

WHY THE .wem IS DELETED RATHER THAN COPIED
render_lines writes both a .wav and a matching .wem into the audition directory,
and the .wem is byte-identical to what the build would produce. Copying it looks
like a free optimisation. It is not: wav_to_wem skips a .wem whose mtime is >=
its source's, so whether the shipped audio is the new take or a leftover from the
previous promote comes down to the order two files happened to be copied in. That
is a coin flip deciding which voice ships. So: copy the source, delete the target
.wem, let the build convert. One rule, no race, and the conversion is cheap
(a 96-byte header in front of the samples).

WHAT IT DELIBERATELY DOES NOT DO
It does not listen for you, and it cannot. Every check here is a floor - clipping,
high-frequency junk, noise where the source was quiet. "Does this sound like Mara"
is not a number, which is why --yes is required and why the default is a dry run.
"""
import argparse
import importlib.util
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import gen_vomap
import wav_to_wem


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="an audition directory holding <locale>/<key>.wav")
    ap.add_argument("--yes", action="store_true",
                    help="actually copy; without it this is a dry run")
    ap.add_argument("--dry-run", action="store_true", help="explicit no-op, the default")
    ap.add_argument("--partial", action="store_true",
                    help="promote a batch that does not cover every line")
    ap.add_argument("--force", action="store_true",
                    help="promote even if rvc_audition fails the batch")
    a = ap.parse_args()

    # This tool prints, then shells out to rvc_audition.py which prints too. Piped,
    # our stdout is block-buffered and the child's is not, so without this the
    # child's verdict appears ABOVE the findings it is supposed to follow, and the
    # report reads back to front.
    sys.stdout.reconfigure(line_buffering=True)

    src_root = pathlib.Path(a.dir).resolve()
    if not src_root.is_dir():
        sys.exit(f"{src_root} is not a directory")

    render = load("render_lines")

    # 1. WHAT IS THERE, AND IS IT ALL THERE
    plan, problems = [], []
    for d in sorted(p for p in src_root.iterdir() if p.is_dir()):
        locale = d.name
        if locale not in gen_vomap.VO_LOCALES:
            print(f"skip {locale}/: subtitle-only, ships no voiceover (D42)")
            continue
        wavs = sorted(p for p in d.iterdir() if p.suffix.lower() in wav_to_wem.SOURCES)
        have = {gen_vomap.split_stem(p.stem)[0] for p in wavs}
        want = {k for k, _, _ in render.lines_of(locale)}
        missing, unknown = sorted(want - have), sorted(have - want)
        print(f"{locale}: {len(wavs)} file(s) covering {len(have & want)}/{len(want)} line(s)")
        if unknown:
            # A name matching no line is caught by the build too, but catching it
            # before the copy means never having to work out which of 43 files in
            # vo/ was the stray one.
            problems.append(f"{locale}: {len(unknown)} file(s) match no line: "
                            f"{', '.join(unknown[:4])}{' ...' if len(unknown) > 4 else ''}")
        if missing and not a.partial:
            problems.append(f"{locale}: {len(missing)} line(s) have no audio: "
                            f"{', '.join(missing[:4])}{' ...' if len(missing) > 4 else ''}"
                            f"  (--partial to promote anyway)")
        elif missing:
            print(f"  --partial: leaving {len(missing)} line(s) unvoiced")
        plan += [(p, ROOT / "vo" / locale / p.name) for p in wavs]

    if not plan:
        sys.exit("nothing to promote")
    for p in problems:
        print(f"!! {p}")

    # 2. IS IT ANY GOOD - measured now, not when it was rendered
    print(f"\nmeasuring {src_root} ...")
    rc = subprocess.call([str(TOOLS / "rvc_audition.py"), str(src_root)])
    if rc != 0:
        problems.append(f"rvc_audition failed this batch (exit {rc})"
                        f"{' - overridden by --force' if a.force else ''}")
        if not a.force:
            print("\n!! " + problems[-1])
            sys.exit("refusing to promote a batch that did not measure clean")
    if problems and not (a.partial or a.force):
        sys.exit("refusing to promote; see the !! lines above")

    # 3. COPY
    if not a.yes:
        print(f"\ndry run: {len(plan)} file(s) would be copied into vo/. "
              f"Listen first, then re-run with --yes.")
        for s, d in plan[:5]:
            print(f"  {s} -> {d}")
        if len(plan) > 5:
            print(f"  ... and {len(plan) - 5} more")
        return 0

    n = 0
    for s, d in plan:
        d.parent.mkdir(parents=True, exist_ok=True)
        stale = d.with_suffix(".wem")
        if stale.exists():
            stale.unlink()
        shutil.copyfile(s, d)
        n += 1
    print(f"\npromoted {n} file(s) into vo/. Now: tools/validate.py && tools/build.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
