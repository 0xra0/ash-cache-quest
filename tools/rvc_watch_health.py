#!/usr/bin/env python3
"""Measure every checkpoint as training writes it, and shout when the rot starts.

The health gate in rvc_train.sh runs once, at the end. That is too late, and mara
proved it: the model railed between epoch 40 and 50 and then trained for sixty
more epochs, writing a .pth and an .index that looked exactly like a finished
model. Worse, the failure was visible long before it was audible - the share of
energy above 8 kHz climbed 1.12 -> 2.59 -> 3.46% across epochs 20/30/40 while the
renders still sounded like a voice.

So this watches the log directory, renders each new checkpoint against the
model's own training slices, and appends a row to

    rvc_logs/<model>.health.tsv

It shouts in two situations:

  BROKEN   a checkpoint fails the absolute gate (clipping, or noise filling the
           source's silences). This is the failure that already happened.

  ROT      the last three checkpoints show a strictly rising high-frequency
           share AND the newest is at least 1.5x the oldest of the three. This
           is the early warning. Checked against both real series: mara's
           1.12/2.59/3.46 fires at epoch 40, ten epochs before it railed;
           johnny's 4.92/4.50/4.14 does not fire, even though johnny's absolute
           HF share is four times mara's. The trend is the signal, not the level
           - which is why there is no absolute HF threshold here.

Runs on CPU with the GPU blanked out, niced, and on two threads, so it can sit
alongside a live trainer. It never touches the GPU and never writes into an
Applio log directory.

    tools/rvc_watch_health.py johnny --until-idle
    tools/rvc_watch_health.py mara --poll 300
"""
import argparse
import glob
import importlib.util
import os
import re
import sys
import time

APPLIO = "/mnt/sata/Applio"
LOGS = "/mnt/sata/Cyberpunk2077/rvc_logs"
WORK = f"{LOGS}/health"
TOOLS = os.path.dirname(os.path.abspath(__file__))

COLS = ["epoch", "step", "clip", "p95", "gap", "hf", "verdict", "when"]


def load_checker():
    """Reuse rvc_check_model's measurement so there is exactly one definition."""
    spec = importlib.util.spec_from_file_location(
        "rvc_check_model", os.path.join(TOOLS, "rvc_check_model.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def checkpoints(model):
    out = []
    for p in glob.glob(f"{APPLIO}/logs/{model}/{model}_*e_*s.pth"):
        m = re.search(r"_(\d+)e_(\d+)s\.pth$", p)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), p))
    return sorted(out)


def trainer_alive(model):
    """Is a trainer running for THIS model? Read /proc rather than shelling out,
    so the pattern in our own command line can never match us."""
    me = os.getpid()
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) == me:
            continue
        try:
            with open(f"/proc/{d}/cmdline", "rb") as fh:
                parts = fh.read().split(b"\0")
        except OSError:
            continue
        if not any(p.endswith(b"rvc/train/train.py") for p in parts):
            continue
        if model.encode() in parts:
            return True
    return False


def read_rows(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) == len(COLS) and f[0] != "epoch":
                rows.append(dict(zip(COLS, f)))
    return rows


def append_row(path, row):
    new = not os.path.exists(path)
    with open(path, "a") as fh:
        if new:
            fh.write("\t".join(COLS) + "\n")
        fh.write("\t".join(str(row[c]) for c in COLS) + "\n")


def rot_warning(rows):
    """Rising high-frequency share over three consecutive checkpoints."""
    hf = []
    for r in rows[-3:]:
        try:
            hf.append(float(r["hf"]))
        except ValueError:
            return None
    if len(hf) < 3:
        return None
    if not hf[0] < hf[1] < hf[2]:
        return None
    # Two triggers. The first is the mara shape: a moderate climb that has already
    # reached a level worth worrying about. The second catches a steep climb from a
    # low base, which the first would miss for another ten epochs - and ten epochs
    # was mara's entire remaining margin. The 0.75% floor stops a jitter from 0.01
    # to 0.04 counting as a quadrupling.
    ratio = hf[2] / max(hf[0], 1e-9)
    if (ratio >= 1.5 and hf[2] > 2.0) or (ratio >= 2.5 and hf[2] > 0.75):
        return f"hf8k rising {hf[0]:.2f} -> {hf[1]:.2f} -> {hf[2]:.2f}% ({ratio:.1f}x)"
    return None


def say(msg, alert_path=None):
    line = f"[{time.strftime('%F %T')}] {msg}"
    print(line, flush=True)
    if alert_path:
        with open(alert_path, "a") as fh:
            fh.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--poll", type=int, default=180, help="seconds between scans")
    ap.add_argument("--until-idle", action="store_true",
                    help="exit once the trainer is gone and every checkpoint is measured")
    ap.add_argument("--source", help="reference wav; default is the model's own training slices")
    a = ap.parse_args()

    tsv = f"{LOGS}/{a.model}.health.tsv"
    alert = f"{LOGS}/{a.model}.health.alert"

    # CPU only, and politely: a trainer owns the machine.
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    for v in ("CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES"):
        os.environ[v] = ""
    try:
        os.nice(10)
    except OSError:
        pass

    check = load_checker()
    sys.path.insert(0, APPLIO)
    os.chdir(APPLIO)
    import torch
    if torch.cuda.is_available():
        sys.exit("refusing to run: the GPU is still visible")
    torch.set_num_threads(2)
    from core import run_infer_script

    os.makedirs(WORK, exist_ok=True)
    src = a.source
    broken = 0
    src_db = None

    say(f"watching {a.model}: {tsv}")
    # --until-idle must not mean "exit because the trainer has not started yet".
    # mara's watcher is launched while mara is still queued behind johnny, so the
    # exit condition only arms once a trainer for this model has actually been seen.
    seen_trainer = bool(checkpoints(a.model))
    while True:
        if trainer_alive(a.model):
            if not seen_trainer:
                say(f"{a.model}: trainer started")
            seen_trainer = True
        if src is None:
            src = check.build_source(a.model, f"{WORK}/{a.model}_selftest.wav")
            if src:
                say(f"reference built from {a.model}'s own training slices: {src}")
        if src and src_db is None:
            src_db = check.measure(src)["db"]

        done = {int(r["epoch"]) for r in read_rows(tsv)}
        pending = [c for c in checkpoints(a.model) if c[0] not in done]

        if src and pending:
            for epoch, step, pth in pending:
                out = f"{WORK}/{a.model}_{os.path.basename(pth)}.wav"
                row = dict(epoch=epoch, step=step, when=time.strftime("%F %T"))
                try:
                    if not os.path.exists(out):
                        run_infer_script(
                            pitch=0, index_rate=0.0, volume_envelope=1.0, protect=0.33,
                            f0_method="rmvpe", input_path=src, output_path=out,
                            pth_path=pth, index_path="",
                            split_audio=False, f0_autotune=False, f0_autotune_strength=1.0,
                            proposed_pitch=False, proposed_pitch_threshold=155.0,
                            clean_audio=False, clean_strength=0.5,
                            export_format="WAV", embedder_model="contentvec",
                        )
                    m = check.measure(out, src_db)
                except Exception as exc:                      # noqa: BLE001
                    row.update(clip="-", p95="-", gap="-", hf="-",
                               verdict=f"ERROR: {type(exc).__name__}: {exc}"[:120])
                    append_row(tsv, row)
                    say(f"{a.model} e{epoch}: render failed - {exc}", alert)
                    continue
                bad = [n for n, ok in (
                    ("clipping", m["clip"] <= check.CLIP_MAX),
                    ("noise in gaps", m["sil"] <= check.SIL_MAX),
                    ("hf hash", m["hf"] <= check.HF_MAX)) if not ok]
                row.update(clip=f"{m['clip']:.2f}", p95=f"{m['p95']:.1f}",
                           gap=f"{m['sil']:.1f}", hf=f"{m['hf']:.2f}",
                           verdict="ok" if not bad else "BROKEN: " + ", ".join(bad))
                append_row(tsv, row)
                say(f"{a.model} e{epoch}: clip {row['clip']}%  gap {row['gap']} dB  "
                    f"hf {row['hf']}%  {row['verdict']}")
                if bad:
                    broken = 1
                    say(f"!! {a.model} e{epoch} is BROKEN ({', '.join(bad)}). "
                        f"Stop the run - later epochs will not recover.", alert)
                else:
                    warn = rot_warning(read_rows(tsv))
                    if warn:
                        say(f"!! {a.model} e{epoch} ROT WARNING: {warn}. This is the "
                            f"pattern mara showed ten epochs before it railed.", alert)

        if a.until_idle and seen_trainer and not trainer_alive(a.model):
            # One last scan already happened above; if nothing is pending, stop.
            if not [c for c in checkpoints(a.model)
                    if c[0] not in {int(r["epoch"]) for r in read_rows(tsv)}]:
                say(f"{a.model}: trainer gone, {len(read_rows(tsv))} checkpoint(s) measured")
                return broken
        time.sleep(a.poll)


if __name__ == "__main__":
    sys.exit(main())
