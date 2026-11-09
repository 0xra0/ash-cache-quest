#!/usr/bin/env python3
"""Move an RVC render toward the measured character of the game's own VO.

Not a taste preset. Every number below was measured by --measure against
rvc_datasets/mara/, the same ripped Cyberpunk 2077 dialogue the voice model
was trained on, and can be re-derived at any time.

Method. Comparing a render's long-term average spectrum against the corpus
average is misleading, because the corpus averages over speech containing
fricatives and a short test line may contain none - "Hello" is /h E l oU/,
entirely sonorant, and reads as 11 dB dark against a mixed corpus purely for
that reason. So both sides are split into sonorant and fricative frames (a
frame is sonorant when >70% of its energy sits below 1 kHz) and only like is
compared with like. That drops the apparent high-frequency deficit from ~11 dB
to 3-5 dB and exposes a +3 to +4 dB midrange bump that the biased comparison
had hidden.

Measured 2026-09-09 against mara_70e_9170s, 40 corpus clips, 1210 sonorant
frames, edge-tts en-US-AriaNeural source:

      band          game(sonorant)   render    delta
      120-  250 Hz        -2.2       -4.6      -2.3   thin
      250-  500 Hz        -4.8       -7.2      -2.4   thin
      500- 1000 Hz       -11.5       -8.4      +3.1   boxy
     1000- 2000 Hz       -20.4      -16.2      +4.2   nasal
     2000- 3000 Hz       -23.9      -29.1      -5.2   dull
     3000- 5000 Hz       -30.1      -30.8      -0.7
     5000- 8000 Hz       -36.8      -39.9      -3.2   no air
     8000-16000 Hz       -41.8      -55.2    -3.8/-4.2

Below 120 Hz the render is 30 dB down on the corpus, and that gap is left
alone: Mara's fundamental is around 200 Hz, so corpus energy under 120 Hz is
room rumble and handling noise, not voice. Restoring it would restore noise.

No compression. Measured over active speech only - whole-file crest is
inflated by leading silence and says nothing useful - the corpus runs 16.7 dB
crest (IQR 15.2-17.8) against this render's 12.2 dB. The render is already the
flatter of the two, so compression widens the gap it would be meant to close.
The EQ itself costs about 1 dB of crest, which is the price of the chain.

Caveat on that number. Crest, RMS and loudness range are all unreliable on the
1.6 s single-word render they were taken from: one syllable cannot show the
stressed/unstressed span a sentence does. The spectral comparison above is
frame-matched and holds; the dynamics comparison needs re-measuring on a full
line before anything is concluded from it.

No reverb. Wwise applies dialogue reverb per space at runtime from its own
buses; the shipped assets are dry and these must stay dry, or the space gets
applied twice.

Level matches the corpus by peak, not by EBU R128: loudnorm is a dynamic
normaliser and would flatten exactly the dynamics measured above. Corpus mean
peak is -3.0 dBFS.
"""

import argparse
import pathlib
import re
import subprocess
import sys

CORPUS = pathlib.Path("/mnt/sata/Cyberpunk2077/rvc_datasets")
TARGET_PEAK_DBFS = -3.0

# Corpus speech RMS with silence stripped at -45 dBFS: mean -20.61 dBFS over 60
# clips, median -20.75, IQR -21.60..-19.30. Every corpus file is peak-normalised
# to exactly -3.0 dBFS, so peak-matching is what a delivered asset wants. It is
# the wrong thing for an A/B: the EQ moves the peak, so peak-matching silently
# re-gains each variant by a different amount and the strength knob partly
# cancels itself. Auditioning wants --match rms.
TARGET_SPEECH_RMS_DBFS = -20.75

# (ffmpeg filter, gain in dB, human name). Gains scale with --strength; the
# frequencies and widths do not. Each corrects one row of the table above.
BANDS = [
    ("equalizer=f=350:t=q:w=0.8:g={g}",   +2.0, "chest      250-500 Hz"),
    ("equalizer=f=1200:t=q:w=1.1:g={g}",  -3.5, "boxy/nasal 500-2000 Hz"),
    ("equalizer=f=2600:t=q:w=1.2:g={g}",  +3.0, "presence   2-3 kHz"),
    ("treble=f=5500:t=q:w=0.7:g={g}",     +3.5, "air        5 kHz up"),
]


def chain(strength):
    """The polish chain, at a given fraction of the measured correction."""
    # 70 Hz is below Mara's fundamental, so this removes only rumble the RVC
    # generator invents in the gaps between phonemes. It is close to a no-op on
    # a clean render and cheap insurance on a dirty one.
    parts = ["highpass=f=70:poles=2"]
    parts += [f.format(g=round(g * strength, 2)) for f, g, _ in BANDS]
    return ",".join(parts)


# Strip anything below -45 dBFS before measuring, so leading and trailing
# silence cannot dilute a level reading. This is the same gate the crest
# measurement in the docstring uses, and the reason its numbers disagree with
# the whole-file ones.
_DESILENCE = ("silenceremove=start_periods=1:stop_periods=-1:"
              "stop_threshold=-45dB:stop_duration=0.05,")


def level_dbfs(path, mode):
    """max_volume for mode 'peak', speech-only mean_volume for mode 'rms'."""
    af = "volumedetect" if mode == "peak" else _DESILENCE + "volumedetect"
    key = "max_volume" if mode == "peak" else "mean_volume"
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", af, "-f", "null", "-"],
        capture_output=True, text=True).stderr
    m = re.search(rf"{key}:\s*(-?[\d.]+) dB", out)
    if not m:
        sys.exit(f"could not measure {key} of {path}")
    return float(m.group(1))


def polish(src, dst, chain_str, match="peak"):
    # Pass 1 filters, pass 2 sets the level. Splitting them keeps the gain
    # honest: the EQ changes the level, so it has to be measured after the EQ.
    tmp = dst.with_suffix(".stage1.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                    "-af", chain_str, "-c:a", "pcm_s16le", str(tmp)], check=True)
    target = TARGET_PEAK_DBFS if match == "peak" else TARGET_SPEECH_RMS_DBFS
    gain = target - level_dbfs(tmp, match)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp),
                    "-af", f"volume={gain:.2f}dB", "-c:a", "pcm_s16le", str(dst)], check=True)
    tmp.unlink()
    return gain


def measure(render, voice):
    """Re-derive the table in the docstring from the corpus. No magic numbers."""
    import glob, random
    import numpy as np

    nfft, sr = 4096, 48000
    win = np.hanning(nfft)
    freq = np.fft.rfftfreq(nfft, 1 / sr)
    below_1k = freq < 1000

    def sonorant_frames(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path),
                              "-f", "s16le", "-ar", str(sr), "-ac", "1", "-"],
                             capture_output=True).stdout
        x = np.frombuffer(raw, dtype="<i2").astype(float) / 32768
        out = []
        for i in range(0, max(1, len(x) - nfft), nfft // 2):
            seg = x[i:i + nfft]
            if len(seg) < nfft or np.sqrt((seg ** 2).mean()) < 10 ** (-45 / 20):
                continue
            p = np.abs(np.fft.rfft(seg * win)) ** 2
            if p[below_1k].sum() / p.sum() > 0.70:
                out.append(p)
        return out

    clips = sorted(glob.glob(str(CORPUS / voice / "*.wav")))
    if not clips:
        sys.exit(f"no corpus clips under {CORPUS / voice}")
    random.seed(0)
    game = []
    for c in random.sample(clips, min(40, len(clips))):
        game += sonorant_frames(c)
    got = sonorant_frames(render)
    if not game or not got:
        sys.exit("not enough sonorant frames to compare")
    g, r = np.mean(game, axis=0), np.mean(got, axis=0)
    print(f"{voice} corpus: {len(game)} sonorant frames from "
          f"{min(40, len(clips))} clips; render: {len(got)}\n")
    print(f"{'band':>16}  {'game':>7} {'render':>7} {'delta':>7}")
    for lo, hi in [(60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000),
                   (2000, 3000), (3000, 5000), (5000, 8000), (8000, 12000),
                   (12000, 16000), (16000, 20000)]:
        m = (freq >= lo) & (freq < hi)
        a = 10 * np.log10(g[m].mean() / g.max())
        b = 10 * np.log10(r[m].mean() / r.max() + 1e-20)
        print(f"{lo:7d}-{hi:6d}  {a:7.1f} {b:7.1f} {b - a:+7.1f}")


# ---------------------------------------------------------------------------
# Fitting: solve for the gains instead of carrying a table.
#
# The gains in BANDS are one measurement frozen at one moment against one
# render, and they are in a fixed ratio. That ratio is close enough for a direct
# RVC render of real speech, whose defect runs about 2.5 dB of midrange against
# 2.2 dB of missing top, but wrong for a TTS-sourced one at 4.8 against 2.0 -
# there no single --strength corrects both, because correcting the midrange
# overshoots the top by a factor of three.
#
# Fitting removes the ratio from the author's hands. Measure what each filter
# actually puts into each band, measure what this particular render needs, and
# least-squares solve. The two steps below are what make it work.
# ---------------------------------------------------------------------------

FIT_BANDS = [(250, 500), (500, 2000), (2000, 5000), (5000, 16000)]
PROBE_DB = 6.0          # large enough to measure over noise, small enough to stay linear


def _decode(path, af=None):
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-i", str(path)]
    if af:
        cmd += ["-af", af]
    cmd += ["-f", "s16le", "-ar", "48000", "-ac", "1", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(float) / 32768


def _sonorant_mean(x):
    """Mean power spectrum over active sonorant frames, or None if there are none.

    Sonorant-only because a corpus average includes fricatives and a short test
    line may contain none, which reads as a large false top-end deficit. Compare
    like with like.
    """
    import numpy as np
    nfft = 4096
    win = np.hanning(nfft)
    freq = np.fft.rfftfreq(nfft, 1 / 48000)
    below_1k = freq < 1000
    acc = []
    for i in range(0, max(1, len(x) - nfft), nfft // 2):
        seg = x[i:i + nfft]
        if len(seg) < nfft or np.sqrt((seg ** 2).mean()) < 10 ** (-45 / 20):
            continue
        p = np.abs(np.fft.rfft(seg * win)) ** 2
        if p[below_1k].sum() / p.sum() > 0.70:
            acc.append(p)
    return (np.mean(acc, axis=0), len(acc), freq) if acc else (None, 0, freq)


def _shape(P, freq):
    """Band levels with the overall offset removed, so this is shape not level."""
    import numpy as np
    b = np.array([10 * np.log10(P[(freq >= lo) & (freq < hi)].mean())
                  for lo, hi in FIT_BANDS])
    return b - b.mean()


def _basis():
    """M[band][filter]: dB each filter puts into each band per dB of its gain.

    Not an identity matrix, which is the whole point. A wide bell at 350 and one
    at 2600 both bleed into 500-2000, so raising them injects midrange that the
    1200 cut must cancel before it removes anything - which is why a nominal
    -3.5 dB there has only ever delivered about -2.7. Measured, so it stays true
    if the frequencies or widths in BANDS are ever changed.
    """
    import numpy as np
    src = "anoisesrc=d=12:c=white:r=48000:a=0.3"

    def noise_shape(af):
        cmd = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", src, "-ac", "1"]
        if af:
            cmd += ["-af", af]
        cmd += ["-f", "s16le", "-"]
        x = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout,
                          dtype="<i2").astype(float) / 32768
        nfft = 1 << 15
        win = np.hanning(nfft)
        freq = np.fft.rfftfreq(nfft, 1 / 48000)
        acc = np.zeros(nfft // 2 + 1)
        for i in range(0, len(x) - nfft, nfft // 2):
            acc += np.abs(np.fft.rfft(x[i:i + nfft] * win)) ** 2
        return np.array([10 * np.log10(acc[(freq >= lo) & (freq < hi)].mean())
                         for lo, hi in FIT_BANDS])

    ref = noise_shape(None)
    M = np.zeros((len(FIT_BANDS), len(BANDS)))
    for j, (f, _, _) in enumerate(BANDS):
        M[:, j] = (noise_shape(f.format(g=PROBE_DB)) - ref) / PROBE_DB
    return M


def corpus_shape(voice):
    import glob, random
    import numpy as np
    clips = sorted(glob.glob(str(CORPUS / voice / "*.wav")))
    if not clips:
        sys.exit(f"no corpus clips under {CORPUS / voice}")
    random.seed(0)
    acc = []
    for c in random.sample(clips, min(40, len(clips))):
        P, n, freq = _sonorant_mean(_decode(c))
        if P is not None:
            acc.append(_shape(P, freq))
    if not acc:
        sys.exit("no sonorant frames in corpus")
    a = np.array(acc)
    # The spread matters as much as the mean. Real dialogue varies clip to clip
    # by more than any correction worth applying, so a fitted gain smaller than
    # this is inside the target's own scatter and means nothing.
    return a.mean(axis=0), a.std(axis=0)


def fit(render, voice, strength):
    """Gains that move this render onto the corpus shape. Returns (chain, report)."""
    import numpy as np
    P, n, freq = _sonorant_mean(_decode(render))
    if P is None:
        sys.exit("no sonorant frames in the render - nothing to fit against")
    have = _shape(P, freq)
    target, spread = corpus_shape(voice)
    want = target - have
    g = np.linalg.lstsq(_basis(), want, rcond=None)[0] * strength
    chain = ",".join(["highpass=f=70:poles=2"] +
                     [f.format(g=round(v, 2)) for (f, _, _), v in zip(BANDS, g)])

    after, _, freq2 = _sonorant_mean(_decode(render, chain))
    resid = _shape(after, freq2) - target
    report = [f"fitted against {voice} on {n} sonorant frames, strength {strength}"]
    if n < 300:
        report.append(f"  WARNING: {n} frames is thin. The same model measured on "
                      f"different 10 s windows of one passage moves by up to 4.7 dB "
                      f"in 500-2000 Hz; fit on the longest take available.")
    for (lo, hi), w, v, sd in zip(FIT_BANDS, want, g, spread):
        mark = "  (inside corpus scatter)" if abs(w) < sd else ""
        report.append(f"  {lo:>5}-{hi:<5} Hz  needs {w:+5.1f} dB  "
                      f"+/-{sd:.1f} corpus sd   gain {v:+6.2f}{mark}")
    report.append(f"  residual RMS {np.sqrt((resid ** 2).mean()):.2f} dB "
                  f"(was {np.sqrt((want ** 2).mean()):.2f})")
    return chain, "\n".join(report)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=pathlib.Path)
    ap.add_argument("-o", "--output", type=pathlib.Path,
                    help="default: <input>.polished.wav beside the input")
    ap.add_argument("-s", "--strength", type=float, default=0.75,
                    help="fraction of the measured correction to apply "
                         "(default 0.75; full EQ-matching usually overshoots)")
    ap.add_argument("--fit", metavar="VOICE", nargs="?", const="mara",
                    help="solve the band gains from this render against "
                         "rvc_datasets/VOICE instead of using the fixed table. "
                         "The table's gains are in one ratio, which suits a "
                         "direct RVC render but not a TTS-sourced one; fitting "
                         "removes the ratio from the author's hands")
    ap.add_argument("--match", choices=("peak", "rms"), default="peak",
                    help="peak: pin to -3.0 dBFS like every corpus file, for a "
                         "delivered asset (default). rms: pin speech-only RMS "
                         "to -20.75 dBFS, for comparing strengths by ear - "
                         "peak-matching lets loudness stand in for the "
                         "difference and hides the knob")
    ap.add_argument("--measure", metavar="VOICE", nargs="?", const="mara",
                    help="print the sonorant-matched spectral delta against "
                         "rvc_datasets/VOICE and exit, instead of filtering")
    a = ap.parse_args()
    if not a.input.is_file():
        sys.exit(f"no such file: {a.input}")
    if a.measure:
        return measure(a.input, a.measure)
    dst = a.output or a.input.with_suffix(f".polished{a.input.suffix}")
    if a.fit:
        chain_str, report = fit(a.input, a.fit, a.strength)
        print(report)
    else:
        chain_str = chain(a.strength)
    gain = polish(a.input, dst, chain_str, a.match)
    print(f"{dst}   strength {a.strength}  match {a.match}  make-up {gain:+.2f} dB")
    print(f"  chain: {chain_str}")


if __name__ == "__main__":
    sys.exit(main() or 0)
