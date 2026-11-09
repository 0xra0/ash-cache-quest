#!/usr/bin/env python3
"""Synthesise Ukrainian with StyleTTS2, in one process for a whole batch.

Why this is a separate script instead of another backend function inside
render_lines.py: three reasons, and none of them is taste.

  1. It needs a different interpreter. StyleTTS2 wants torch 2.8 + transformers
     5, and render_lines.py re-execs itself under the Applio conda env, which is
     mid-training with hours invested. /mnt/sata/Cyberpunk2077/styletts_venv is
     a CPU-only torch on purpose - `torch.cuda.is_available()` is False there,
     so this can never contend for the GPU no matter what it is asked to do.

  2. Model load dominates. The multispeaker checkpoint plus its text encoder
     take tens of seconds to come up; a 5-character line ("А ти?") takes under a
     second to synthesise. Loading per line would spend all of its time in
     __init__, so the batch is the unit of work and the job list arrives as JSON
     on stdin.

  3. The Ukrainian front end is not the same shape as piper's. piper's uk model
     is phoneme_type "text" - raw characters into an id map. This one runs
     stress -> IPA -> tokenizer, which is why it can say a word it never saw and
     piper can only spell one. That pipeline is patriotyk's, copied from the
     reference app so the output matches what the demo produces:

         text -> normalise -> stressify -> ipa() -> tokenizer.encode -> model

Manual stress: a `+` AFTER a vowel marks it stressed, exactly as in the demo.
The automatic stresser resolves homographs by part of speech and will sometimes
pick ні́чого where нічо́го was meant; `+` is how a human overrides it, and it is
worth doing in the source text rather than here.

Usage (stdin is a JSON list of {text, voice, out}; voice "" = single-speaker):
    styletts_venv/bin/python tools/styletts2_render.py < jobs.json
"""
import json
import re
import sys
from unicodedata import normalize

SPACE = "/mnt/sata/styletts2-ukrainian"      # the reference app, for its voices/
SINGLE = "patriotyk/styletts2_ukrainian_single"
MULTI = "patriotyk/styletts2_ukrainian_multispeaker"
RATE = 24000                                  # what the model emits, not a choice


def prepare(text, stressify, StressSymbol):
    """The demo app's exact preprocessing. Deviating from it changes the voice.

    The two non-obvious steps are the last two. A line with no terminal
    punctuation gets a period because the model was trained on sentences and
    trails off without one, and " - " becomes ": " because a spaced hyphen in
    Ukrainian is a dash - a clause break, not a word break - and the tokenizer
    has no dash.
    """
    text = text.replace('"', "")
    text = text.replace("+", StressSymbol.CombiningAcuteAccent)
    text = normalize("NFKC", text)
    text = re.sub(r"[᠆‐‑‒–—―⁻₋−⸺⸻]", "-", text)
    if text and text[-1] not in ".?!:-":
        text += "."
    text = re.sub(r" - ", ": ", text)
    return stressify(text)


def main():
    jobs = json.load(sys.stdin)
    if not jobs:
        print("nothing to render")
        return 0

    import torch
    if torch.cuda.is_available():
        # The venv is built CPU-only precisely so this cannot happen. If it ever
        # does, something re-installed torch and a trainer is at risk.
        sys.exit("refusing to run: this venv is supposed to be CPU-only")

    import soundfile as sf
    from ipa_uk import ipa
    from styletts2_inference.models import StyleTTS2
    from ukrainian_word_stress import Stressifier, StressSymbol

    stressify = Stressifier()
    want_multi = any(j.get("voice") for j in jobs)
    model = StyleTTS2(hf_path=MULTI if want_multi else SINGLE, device="cpu")

    styles, n = {}, 0
    for job in jobs:
        voice = job.get("voice") or ""
        if voice not in styles:
            path = f"{SPACE}/voices/{voice}.pt" if voice else f"{SPACE}/filatov.pt"
            styles[voice] = torch.load(path, weights_only=False)
        ps = ipa(prepare(job["text"], stressify, StressSymbol))
        if not ps:
            print(f"!! nothing to say for {job['out']}", file=sys.stderr)
            continue
        tokens = model.tokenizer.encode(ps)
        wav = model(tokens, speed=job.get("speed", 1.0), s_prev=styles[voice])
        sf.write(job["out"], wav.cpu().numpy(), RATE)
        n += 1
        print(f"  {voice or 'filatov':28} -> {job['out']}")
    print(f"styletts2 rendered {n}/{len(jobs)} line(s) at {RATE} Hz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
