#!/usr/bin/env python3
"""Did a batch of rendered lines survive the voice conversion?

Not the same question as tools/rvc_check_model.py, which asks whether a CHECKPOINT
is healthy by rendering its own training material. This asks whether the lines that
were actually produced are clean, and it has to be told what they were made from,
because the interesting statistic is a difference.

Why a difference. "How loud is the output where the source was quiet" is only a
health number when the source has quiet in it. A short choice line - "What's your
cut in this?" - has no pause anywhere, so its quietest quarter is ordinary
consonants around -30 dB, and a fixed -40 dB threshold calls a clean render broken.
Measured: 22 of 25 English piper renders "failed" that way while sitting within
1-3 dB of their own source, three of them QUIETER than it.

And the difference is only an answer on the same condition. Changing the statistic
did not change the fact that an unpadded single-sentence line contains no silence
to hallucinate into - it just produced a number where there had been a wrong one.
Two of eleven RVC renders failed on a gap the summary line had already called
unjudgeable ("0/11 have real silence to judge"), with clip 0.00% and hf under 2%.
So the gap test is now SCOPED rather than retuned: a source whose quiet quarter
sits above HAS_SILENCE is reported unjudged for gap noise and carries its verdict
on clip and hf, and the final line says how many lines that was. Where there IS
silence, the absolute level is checked too - that is the number that decides
whether the noise would be audible, and it is what caught the railed checkpoint.

  tools/rvc_audition.py /mnt/sata/Cyberpunk2077/rvc_logs/audition_piper
  tools/rvc_audition.py <dir> --tts-work /mnt/sata/Cyberpunk2077/rvc_logs/tts -v
"""
import argparse
import importlib.util
import os
import pathlib
import sys

TOOLS = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path("/mnt/sata/Cyberpunk2077/rvc_logs/tts")

# A model that fills the source's silence with its own noise measures far above it.
# Healthy renders here measured -30.0 to +0.8 dB; the railed mara checkpoint sat at
# -0.1 dB absolute against material whose quiet quarter was near -60, a delta near
# +60. Anywhere in between is a wide, empty gap, so the exact number is not delicate.
DELTA_MAX = 6.0
# Below this the source has real silence and the absolute level is meaningful too.
HAS_SILENCE = -45.0


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="a render directory holding <locale>/<key>.wav")
    ap.add_argument("--tts-work", default=str(WORK),
                    help="where the pre-RVC 48k sources live")
    ap.add_argument("-v", "--verbose", action="store_true", help="one row per line")
    ap.add_argument("--allow-unsourced", action="store_true",
                    help="report on the lines that can be measured and pass anyway; "
                         "for inspecting an old directory whose sources are gone")
    a = ap.parse_args()

    # Never contend with a trainer for the GPU; this is arithmetic on a few MB.
    for v in ("CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES"):
        os.environ[v] = ""
    chk = load("rvc_check_model")
    # Loading that module is safe under any python - its numpy/soundfile imports
    # live inside measure(). Calling it is not. Re-exec now, before the argparse
    # and the directory walk, so a wrong interpreter costs nothing instead of
    # failing on the first line of a batch that already took hours to render.
    chk.reexec_under_applio(__file__)

    root, work = pathlib.Path(a.dir), pathlib.Path(a.tts_work)
    locales = sorted(p for p in root.iterdir() if p.is_dir())
    if not locales:
        sys.exit(f"{root} holds no <locale>/ directories")

    gaps, measured, unsourced, unjudged, failed = [], 0, [], [], []
    for loc in locales:
        rows = []
        for w in sorted(loc.glob("*.wav")):
            src = work / loc.name / f"{w.stem}.48k.wav"
            if not src.exists():
                unsourced.append(f"{loc.name}/{w.stem}")
                continue
            m = chk.measure(w, chk.measure(src)["db"])
            bad = []
            if m["clip"] > chk.CLIP_MAX:
                bad.append(f"clip {m['clip']:.1f}%")
            if m["hf"] > chk.HF_MAX:
                bad.append(f"hf {m['hf']:.1f}%")
            # The gap statistic answers one question - did the model hallucinate
            # noise into the source's silence - and it is an answer only when the
            # source HAS silence. On a single-sentence piper line there is none:
            # the quietest quarter is ordinary consonants around -30 dB, and the
            # difference between two voices' consonants is not a defect. This tool
            # already knew that; it printed "(0/11 have real silence to judge)" in
            # the summary and then failed three of those eleven lines on the
            # judgement it had just disclaimed. Measured before this guard:
            # mara.trust_3 "FAIL: gap +15.5 dB" with clip 0.00% and hf 1.04%.
            # Scope, not threshold: a line with nothing to judge is reported
            # unjudged, and clip and hf - which caught the railed checkpoint on
            # their own - carry its verdict.
            if m["sil_src"] <= HAS_SILENCE:
                gaps.append(m["sil_delta"])
                if m["sil_delta"] > DELTA_MAX:
                    bad.append(f"gap +{m['sil_delta']:.1f} dB over source")
                # With real silence present the absolute level is meaningful too,
                # and it is the number that decides whether the noise is audible.
                if m["sil"] > chk.SIL_MAX:
                    bad.append(f"noise in gaps {m['sil']:.1f} dB")
            else:
                unjudged.append(f"{loc.name}/{w.stem}")
            rows.append((w.stem, m, bad))
            if bad:
                failed.append(f"{loc.name}/{w.stem}: {', '.join(bad)}")
        if not rows:
            continue
        d = [m["sil_delta"] for _, m, _ in rows]
        quiet = sum(1 for _, m, _ in rows if m["sil_src"] <= HAS_SILENCE)
        measured += len(rows)
        print(f"{loc.name}: {len(rows)} line(s)  "
              f"clip max {max(m['clip'] for _, m, _ in rows):.2f}%  "
              f"hf {min(m['hf'] for _, m, _ in rows):.2f}-{max(m['hf'] for _, m, _ in rows):.2f}%  "
              f"gap vs source {min(d):+.1f}..{max(d):+.1f} dB  "
              f"({quiet}/{len(rows)} have real silence to judge)")
        if a.verbose:
            for k, m, bad in rows:
                print(f"    {k:28} clip {m['clip']:5.2f}  hf {m['hf']:5.2f}  "
                      f"src {m['sil_src']:7.1f}  out {m['sil']:7.1f}  "
                      f"delta {m['sil_delta']:+6.1f}  {'FAIL: ' + '; '.join(bad) if bad else 'ok'}")

    if unsourced:
        # Not a warning to skip past: rvc_logs/tts is overwritten by each run, so a
        # missing source means these lines cannot be judged at all, and reporting
        # them as clean would be a lie of omission.
        #
        # It used to print exactly that and then return 0, which told the truth to
        # a reader and the opposite to a caller - and the callers are the ones that
        # act on it (tools/vo_promote.py gates a promote on this exit code, and
        # render_after_training.sh prints VERDICT: clean from it). A batch where 18
        # of 43 lines were never measured passed both. Unmeasured is not clean.
        print(f"!! {len(unsourced)} line(s) have no surviving source and were NOT "
              f"measured: {', '.join(unsourced[:6])}"
              f"{' ...' if len(unsourced) > 6 else ''}")
        if not a.allow_unsourced:
            print("   (--allow-unsourced to inspect what IS measurable anyway)")
    if failed:
        print(f"!! {len(failed)} line(s) failed:")
        for f in failed:
            print(f"     {f}")
        return 1
    if not measured:
        # Every line was unsourced, or the directory holds no .wav at all. Saying
        # "all 0 lines clean" would be the most dangerous sentence this tool can
        # print, and max() over an empty list would crash instead of explaining.
        print("!! nothing could be measured - no line had a surviving source. "
              "This is NOT a pass.")
        return 1
    # Say what was NOT tested. A batch where no line had silence to judge passed
    # on clip and hf alone, which is a narrower pass than "clean" sounds.
    gap_note = (f"worst gap {max(gaps):+.1f} dB against a {DELTA_MAX:+.1f} limit "
                f"over {len(gaps)} line(s) with real silence"
                if gaps else
                f"gap noise UNJUDGED on all {measured} line(s) - no source had "
                f"silence below {HAS_SILENCE:.0f} dB; clip and hf carried this pass")
    print(f"all {measured} measured line(s) clean ({gap_note})")
    if unjudged and gaps:
        print(f"   {len(unjudged)} of {measured} had no silence to judge gap noise in")
    return 1 if (unsourced and not a.allow_unsourced) else 0


if __name__ == "__main__":
    sys.exit(main())
