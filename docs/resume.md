# Resume — written 2026-09-04 18:30, for 2026-09-08

Run these in order. `cd /mnt/sata/Cyberpunk2077/ash-cache-quest` first; every
path below is absolute or relative to that.

Tonight's chain renders **43 English lines** (25 V + 18 Mara) into a dated
audition directory and measures them. It never writes to `vo/` and never touches
the game. Nothing ships without you listening first.

---

## 1. What happened while you were away

```bash
tail -25 /mnt/sata/Cyberpunk2077/rvc_logs/render_after_training.log
```

The last line is the verdict. It is one of:

| Last line | Meaning | Go to |
|---|---|---|
| `VERDICT: clean. Listen, then promote: ...` | 43 lines rendered and measured clean | §2 |
| `VERDICT: FAILED (rvc_audition exit 1)...` | rendered, but at least one line failed | §4 |
| `REFUSING to render: mara did not pass...` | the checkpoint is bad; nothing rendered | §5 |
| `waiting for the GPU` and nothing after | the machine rebooted, or training never ended | §6 |

**The directory is dated 2026-09-04, not the day the render ran.** The chain
stamps its output folder when it *starts*, and it started at 17:51 on Sep 4. Even
though the render lands around 02:00 on Sep 5, the files are in:

```bash
ls /mnt/sata/Cyberpunk2077/rvc_logs/audition_final/2026-09-04/en-us/ | wc -l   # expect 43
```

If that says 25, the Mara fix did not take — see §5.

---

## 2. Listen. This is the only step no tool can do.

```bash
cd /mnt/sata/Cyberpunk2077/rvc_logs/audition_final/2026-09-04/en-us
ls *.wav | head
mpv mara.trust_3.wav          # or any player; vlc, aplay, ffplay -nodisp
mpv --loop=no *.wav           # all 43 back to back, ~4 minutes
```

Listen for what the numbers cannot see: does it sound like a *person*, and does
Mara sound like a different person from V. Clipping, hiss and noise-in-the-gaps
are already measured and passed. "Sounds like a robot" and "sounds like the wrong
character" are not measurable and are the actual reasons to reject a batch.

---

## 3. Promote, build, deploy

```bash
cd /mnt/sata/Cyberpunk2077/ash-cache-quest

tools/vo_promote.py /mnt/sata/Cyberpunk2077/rvc_logs/audition_final/2026-09-04
```

That is a **dry run** — it prints what would move and touches nothing. It
re-measures the batch and refuses an incomplete one. Read its output, then:

```bash
tools/vo_promote.py /mnt/sata/Cyberpunk2077/rvc_logs/audition_final/2026-09-04 --yes
tools/build.sh                       # converts wav -> wem, rebuilds mod/
tools/deploy.sh                      # prints what WOULD be copied to the game
tools/deploy.sh --yes                # actually copies. Your call, always.
```

Then in game: start the quest, and listen to it in context.

Once you are happy, mark the voice certified so future renders stop warning:

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("reference/rvc_voices.json")
d = json.loads(p.read_text())
d["voices"]["mara"]["status"] = "VERIFIED 2026-09-08 by listening - <your one-line note>"
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
PY
```

---

## 4. If the verdict was FAILED

```bash
tools/rvc_audition.py /mnt/sata/Cyberpunk2077/rvc_logs/audition_final/2026-09-04 -v
```

`-v` prints one row per line: clip%, hf%, source level, output level, gap. The
failing lines are named. Then decide:

- **A few lines failed, the rest sound fine** — re-render just those:
  ```bash
  tools/render_lines.py --locale en-us --tts piper --force --only mara.trust_3 \
      --out /mnt/sata/Cyberpunk2077/rvc_logs/audition_final/2026-09-04
  ```
- **Most lines failed** — the checkpoint is the problem, not the lines. §5.
- **A line fails `gap` but sounds clean** — that check is only meaningful when the
  source has real silence; see D44. Lines whose source has none are reported
  `unjudged`, not failed. If a *judged* line fails, believe it.

Do not raise a threshold to make a batch pass. That is D36, and it is the reason
half the tooling in `tools/` exists.

---

## 5. If mara failed the health gate, or only 25 lines rendered

```bash
tools/rvc_check_model.py --all mara        # the whole trend, epoch by epoch
```

Read the `hf8k` column down the list. It is the early warning: it climbed
1.12 → 2.59 → 3.46% before the first mara railed at epoch 50. If it is flat and
low, the model is fine. If it climbs and then `clip%` jumps, that run railed too
and the usable model is an *earlier* epoch.

To render from a specific epoch instead of the newest, edit the registry's `pth`
to name that one file rather than the glob:

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("reference/rvc_voices.json")
d = json.loads(p.read_text())
d["voices"]["mara"]["pth"] = "/mnt/sata/Applio/logs/mara/mara_120e_15720s.pth"
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
PY
tools/render_lines.py --locale en-us --tts piper --dry-run | grep 'to render'
```

That last line must say **43 line(s) to render, 0 skipped**. If it says 25, the
registry is refusing Mara — check `status` does not begin with `BROKEN` and that
the `pth` actually exists. This is the exact failure D45 was written about.

---

## 6. If the chain never ran (reboot, or training stopped early)

```bash
ps -o pid,etime,cmd -C bash,python | grep -E 'rvc_train|train\.py|render_after'
nvidia-smi 2>/dev/null || rocm-smi --showuse
```

Nothing running? Start the whole chain again — it waits for a free GPU, gates
the model, renders, and measures, unattended:

```bash
cd /mnt/sata/Cyberpunk2077/ash-cache-quest
nohup tools/render_after_training.sh >/dev/null 2>&1 &
tail -f /mnt/sata/Cyberpunk2077/rvc_logs/render_after_training.log
```

It will stamp a **new** dated folder (`audition_final/2026-09-08`). Use that date
everywhere above instead.

To skip the wait and do it by hand, three commands:

```bash
tools/rvc_check_model.py mara                                   # must end "ok"
OUT=/mnt/sata/Cyberpunk2077/rvc_logs/audition_final/manual
tools/render_lines.py --locale en-us --tts piper --out $OUT
tools/rvc_audition.py $OUT                                      # exit 0 = clean
```

Training itself, if it needs restarting:

```bash
tools/rvc_train.sh --epochs 200 --batch 8 mara
tools/rvc_status.sh mara johnny        # one screenful, no progress bars
```

---

## 7. Two decisions waiting for you

**Johnny.** `tools/rvc_train.sh --wait johnny` is queued behind mara and takes
~4 more hours of GPU. **Johnny speaks no line in this quest** — 43 lines are 25 V
and 18 Mara. The chain waits for the queue to empty, so johnny delays your
renders by roughly four hours and buys nothing for this mod. If it is still
queued when you read this and you want the renders sooner:

```bash
pkill -f 'rvc_train.sh.*johnny'
```

**Disk — currently 93% full, 251 GB free.** Reclaimable without touching a
usable model:

```bash
du -sh /mnt/sata/Applio/logs/mara.railed-2026-09-04     # 16G, the railed run, dead
ls -la /mnt/sata/Applio/logs/mara/D_*.pth /mnt/sata/Applio/logs/mara/G_*.pth
```

The `D_*.pth` / `G_*.pth` pairs are ~1.3 GB *each save* and exist only to resume
an interrupted training run. Once mara is finished and promoted they are dead
weight; the `mara_NNNe_NNNNs.pth` inference checkpoints are 57 MB each and are the
ones that matter. Roughly 40 GB is recoverable. Delete only after you have
promoted a voice you are happy with.

---

## 8. Still open, none of it blocking

`docs/open_issues.md` is the list. The ones only you can close, in the order they
cost least:

- **OI-19** — CET console: `Game.SetFactValue("ashcache_cynosure_open", 1)`, then
  check the Cynosure location is reachable.
- **OI-18** — screenshot the journal list; the lead is `QuestListItemData.m_questType`.
- **OI-9** — 3 coordinates never stood on: `ac_motel_room7`, `ac_splinter_case`,
  `ac_probe_car`. `validate.py` names them every run.
- **OI-20** — put one `.wem` on `mara.opt_level` and listen at the dialogue wheel.
- **OI-13** — the real blocker for a playable quest: `box_opened`, `terminal_read`,
  `cabinet_opened`, `cleanup_done` have no world content behind them yet.
