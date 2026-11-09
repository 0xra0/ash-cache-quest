#!/usr/bin/env python3
"""Is this RVC checkpoint actually usable, or does it emit noise?

Written after shipping mara_110e_14410s.pth, which produced full-scale broadband
noise and was recorded as "SALVAGED, VERIFIED, USABLE" because the only thing
measured was overall RMS - and overall RMS was the one statistic that could not
disagree, since the inference ran with volume_envelope=0.0, which rescales the
output until its RMS matches the source. The check was a tautology. See D36.

What this measures instead, all of which survive that rescaling:

  clip%      fraction of samples at or above 0.98 full scale. A healthy vocoder
             sits near 0. The railed mara checkpoints sat at 48-100%.
  silence    level during the frames the SOURCE calls silence. A generator that
             hallucinates noise fills the gaps between words; a good one leaves
             them alone. Healthy models land below -55 dB, the railed one at -0.1.
  hf8k       share of energy above 8 kHz. This is the early warning: it climbed
             1.12 -> 2.59 -> 3.46% over mara's epochs 20/30/40 while the audio
             still sounded acceptable, then the model railed at 50.

The strongest available source is the model's own training material: a model that
cannot reconstruct audio it was trained on is broken, not undertrained.

Runs on CPU only and blanks the visible-device variables, so it is safe to run
against a checkpoint while another model is training on the GPU.

  tools/rvc_check_model.py mara                  # newest checkpoint of a model
  tools/rvc_check_model.py mara --all            # every saved epoch, to see a trend
  tools/rvc_check_model.py --pth /path/x.pth --source ref.wav
"""
import argparse, glob, os, re, sys

APPLIO = "/mnt/sata/Applio"
WORK = "/mnt/sata/Cyberpunk2077/rvc_logs/health"

# Thresholds. Deliberately loose: this is a "did it break" gate, not a quality
# score. Everything healthy measured so far clears them by a wide margin, and the
# broken checkpoints miss by an order of magnitude - there is no grey zone to tune.
CLIP_MAX = 5.0      # %
SIL_MAX = -40.0     # dB; healthy models measured -57 to -96, railed one -0.1
HF_MAX = 12.0       # %


def measure(path, src_db=None):
    import numpy as np, soundfile as sf
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    h = int(sr * 0.02)
    n = len(x) // h
    fr = x[: n * h].reshape(n, h)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-12)
    # The quiet quarter, by rank rather than by threshold. `db < percentile(db,25)`
    # looks equivalent and is not: on a short clip whose frame levels tie, the
    # strict comparison selects NOTHING, the mean of an empty slice is NaN, and
    # NaN <= SIL_MAX is False - so a perfectly good line gets reported BROKEN.
    # Measured on a real 2-second render before this was fixed. Ranking cannot
    # return an empty set.
    def quietest(levels, pick_from=None):
        src = levels if pick_from is None else pick_from
        k = max(1, len(src) // 4)
        idx = np.argsort(src)[:k]
        return float(levels[idx].mean())

    # `sil` alone answers "how loud is the output where the source was quiet", which
    # is only a health statistic if the source HAS quiet. A 2-second TTS line with no
    # pause in it has a quietest quarter of ordinary consonants around -30 dB, and
    # comparing that to a fixed -40 dB threshold reports a clean render as broken.
    # `sil_delta` is the question that survives: how much LOUDER than the source is
    # the output in those frames. A healthy model measures roughly 0 or negative
    # (measured here: -30.0 to +0.8 dB across 50 renders); the railed mara sat at
    # -0.1 dB absolute against training material whose own quiet quarter was near
    # -60, i.e. a delta around +60.
    sil_src = None
    if src_db is None:
        sil = quietest(db)
    else:
        k = min(len(db), len(src_db))
        sil = quietest(db[:k], src_db[:k])
        sil_src = quietest(src_db[:k])
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / sr)
    return dict(
        clip=100.0 * float((np.abs(x) >= 0.98).mean()),
        p95=float(np.percentile(db, 95)),
        sil=sil,
        sil_src=sil_src,
        sil_delta=None if sil_src is None else sil - sil_src,
        hf=100.0 * float(X[f > 8000].sum() / max(X.sum(), 1e-20)),
        db=db,
    )


def build_source(model, out):
    """Glue a few of the model's own training slices into one reference clip."""
    import numpy as np, soundfile as sf
    slices = sorted(glob.glob(f"{APPLIO}/logs/{model}/sliced_audios/*.wav"))[:5]
    if not slices:
        return None
    parts = []
    for f in slices:
        a, sr = sf.read(f, dtype="float32")
        parts.append(a if a.ndim == 1 else a.mean(1))
        parts.append(np.zeros(int(sr * 0.25), dtype="float32"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sf.write(out, np.concatenate(parts), 48000)
    return out


APPLIO_PY = "/mnt/sata/anaconda3/envs/Applio/bin/python"


def reexec_under_applio(script=None):
    """Same trick, same reason as render_lines.py: this needs torch, soundfile and
    numpy, and the system python has none of them. Run under the wrong interpreter
    the failure is a ModuleNotFoundError from an import three call frames deep,
    which reads like a broken script rather than a wrong python.

    `script` is the file to re-exec, and it is a parameter rather than this
    module's own __file__ because this file is BOTH a script and a library.
    rvc_audition.py imports measure() from here, and measure() imports numpy and
    soundfile inside its body - so the import that fails is deferred until the
    first line is measured, long after the caller decided everything was fine.
    Guarding main() only covers the script half. The importer has to be able to
    say "re-exec ME", so it passes its own __file__ and gets the whole process
    under the right interpreter before any measuring starts.
    """
    if os.environ.get("_RVC_CHECK_REEXEC"):
        return
    try:
        import torch, soundfile  # noqa: F401
        return
    except ImportError:
        pass
    if not os.path.exists(APPLIO_PY):
        sys.exit(f"no audio stack here and no {APPLIO_PY} to borrow it from")
    os.environ["_RVC_CHECK_REEXEC"] = "1"
    target = os.path.abspath(script or __file__)
    os.execv(APPLIO_PY, [APPLIO_PY, target] + sys.argv[1:])


def main():
    reexec_under_applio(__file__)
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="?", help="model name under Applio/logs")
    ap.add_argument("--pth", help="explicit checkpoint instead of a model name")
    ap.add_argument("--index", default="", help="optional .index; not needed for a health check")
    ap.add_argument("--source", help="reference wav; default is the model's own training material")
    ap.add_argument("--all", action="store_true", help="check every saved epoch, to show the trend")
    a = ap.parse_args()

    if a.pth:
        pths = [a.pth]
        model = a.model or os.path.basename(a.pth).split("_")[0]
    elif a.model:
        model = a.model
        pths = sorted(
            glob.glob(f"{APPLIO}/logs/{model}/{model}_*e_*s.pth"),
            key=lambda p: int(re.search(r"_(\d+)e_", p).group(1)),
        )
        if not pths:
            sys.exit(f"no checkpoints for '{model}' under {APPLIO}/logs/{model}")
        if not a.all:
            pths = pths[-1:]
    else:
        sys.exit("name a model or pass --pth")

    src = a.source or build_source(model, f"{WORK}/{model}_selftest.wav")
    if not src or not os.path.exists(src):
        sys.exit(
            f"no reference source. Pass --source, or train far enough that\n"
            f"{APPLIO}/logs/{model}/sliced_audios exists."
        )

    # CPU only: another model may own the GPU right now.
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    for v in ("CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES"):
        os.environ[v] = ""
    sys.path.insert(0, APPLIO)
    os.chdir(APPLIO)
    import torch
    if torch.cuda.is_available():
        sys.exit("refusing to run: the GPU is still visible and may be training")
    import numpy as np
    from core import run_infer_script

    os.makedirs(WORK, exist_ok=True)
    src_db = measure(src)["db"]
    print(f"source: {src}")
    print(f"{'checkpoint':32} {'clip%':>7} {'p95 dB':>8} {'gap dB':>8} {'hf8k':>7}  verdict")
    print("-" * 78)
    worst = 0
    for p in pths:
        out = f"{WORK}/{model}_{os.path.basename(p)}.wav"
        if not os.path.exists(out):
            run_infer_script(
                pitch=0, index_rate=0.0, volume_envelope=1.0, protect=0.33,
                f0_method="rmvpe", input_path=src, output_path=out,
                pth_path=p, index_path=a.index,
                split_audio=False, f0_autotune=False, f0_autotune_strength=1.0,
                proposed_pitch=False, proposed_pitch_threshold=155.0,
                clean_audio=False, clean_strength=0.5,
                export_format="WAV", embedder_model="contentvec",
            )
        m = measure(out, src_db)
        bad = [n for n, ok in (("clipping", m["clip"] <= CLIP_MAX),
                               ("noise in gaps", m["sil"] <= SIL_MAX),
                               ("hf hash", m["hf"] <= HF_MAX)) if not ok]
        verdict = "ok" if not bad else "BROKEN: " + ", ".join(bad)
        worst = max(worst, 1 if bad else 0)
        print(f"{os.path.basename(p):32} {m['clip']:6.2f}% {m['p95']:8.1f} "
              f"{m['sil']:8.1f} {m['hf']:6.2f}%  {verdict}")
    print()
    print(f"renders kept in {WORK} - listen before trusting any number here.")
    sys.exit(worst)


if __name__ == "__main__":
    main()
