#!/usr/bin/env python3
"""Synthesise lines with FireRedTTS3 voice cloning, in one process for a whole batch.

D191: FireRedTTS3 replaces TTS -> RVC for V and Mara. It clones a voice from one
7-10 s reference clip plus that clip's exact transcript, so there is no model to
train and no conversion stage: what it writes is the shipped voice.

A separate script for the same reasons as styletts2_render.py. It needs its own
interpreter (the fireredtts3 conda env: torch 2.14 ROCm, FireRed's deps), and model
load is tens of seconds against a second or two per line, so the batch is the unit
of work and the job list arrives as JSON on stdin.

The model is loaded straight from the checkout rather than through gradio_base.py's
server: nothing here needs a web UI, and a server left running would hold ~GPU
memory after the batch is done.

Each job: {text, ref_wav, ref_text, out, language?, seed?, cfg?, steps?}.
Reference transcripts are the game's own subtitles (reference/firered_voices.json),
not an ASR guess - a wrong prompt_text misaligns the clone for every line after it.

    /mnt/sata/anaconda3/envs/fireredtts3/bin/python tools/firered_render.py < jobs.json
"""
import json
import os
import pathlib
import sys

REPO = "/mnt/ssd/FireRedTTS3"


def main():
    jobs = json.load(sys.stdin)
    if not jobs:
        return 0
    # MIOpen on this RX 6800 has no tuning db for gfx1030_30 (memory: rocm-miopen-
    # gfx1030-30-exhaustive-search); FAST find stops it compiling forever.
    os.environ.setdefault("MIOPEN_FIND_MODE", "FAST")
    os.environ.setdefault("MIOPEN_SYSTEM_DB_PATH", "/mnt/sata/Cyberpunk2077/miopen_db")
    sys.path.insert(0, REPO)
    os.chdir(REPO)                                  # pretrained_models/ is relative
    import torch
    import torchaudio
    from fireredtts3.core import FireRedTTS3

    if not torch.cuda.is_available():
        sys.exit("no GPU visible - FireRedTTS3 on CPU would take hours for this batch")
    tts = FireRedTTS3("pretrained_models", use_fasttext=False,
                      use_wetext=False, use_llm_tn=False)
    refs = {}
    for i, j in enumerate(jobs, 1):
        if j["ref_wav"] not in refs:
            refs[j["ref_wav"]] = torchaudio.load(j["ref_wav"])
        audio, sr = refs[j["ref_wav"]]
        # A runaway: the stop token never fires and the model talks on to its
        # length cap. Seen on the first audition - a 7 s line came back 64 s long.
        # Conversational speech runs ~2.5 words/s; allow 3x that line's worth
        # before calling it runaway, and re-roll the seed rather than ship it.
        limit = max(6.0, 3.0 * len(j["text"].split()) / 2.5)
        seed = int(j.get("seed", 1234))
        for attempt in range(4):
            out, out_sr = tts.generate(
                text=j["text"], language=j.get("language", "English"),
                prompt_text=j["ref_text"], prompt_audio=audio, prompt_audio_sr=sr,
                seed=seed + attempt, inference_cfg=float(j.get("cfg", 2.0)),
                n_timesteps=int(j.get("steps", 10)), do_tn=False)
            if out.shape[-1] / out_sr <= limit:
                break
            print(f"  runaway {out.shape[-1] / out_sr:.1f}s > {limit:.1f}s, "
                  f"re-rolling seed {seed + attempt + 1}", flush=True)
        else:
            sys.exit(f"{j['out']}: runaway on 4 seeds - check ref_text matches ref_wav")
        dst = pathlib.Path(j["out"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(str(dst), out.cpu(), out_sr)
        print(f"[{i}/{len(jobs)}] {dst.name}  {out.shape[-1] / out_sr:.2f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
