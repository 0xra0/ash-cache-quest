#!/usr/bin/env bash
# Train one or more RVC voice models headless, overnight, unattended.
#
#     tools/rvc_train.sh mara                 one model
#     tools/rvc_train.sh mara johnny v        a queue, in order
#     tools/rvc_train.sh --detach mara        survives closing the terminal
#     tools/rvc_train.sh --status             what is running, how far along
#
# The settings are the ones in each dataset's SETTINGS.txt, and the reasons are
# written there. Two of them are not preferences:
#
#   sample rate 48000 - the game's voice lines decode as 48 kHz mono, so any
#     other rate resamples the training data for no reason.
#   vocoder HiFi-GAN - it is the only one with a 48000 pretrained pair present
#     (f0G48k.pth + f0D48k.pth). RefineGAN ships 24k and 32k only, so choosing
#     it at 48000 silently means training from scratch instead of from a
#     pretrained model, which does not finish in a night.
#
# On this machine the GPU is an AMD RX 6800 (gfx1030) and torch is a ROCm build,
# so `torch.cuda.is_available()` returning True is HIP keeping the CUDA API names,
# not a mistake. That brings one trap that will waste a whole night if it is not
# handled, and it is handled below - do not remove those three exports.
#
# MIOpen keys its kernel-tuning databases on `<arch>_<num_cu>`, and on RDNA2
# num_cu counts WORK-GROUP PROCESSORS, not compute units: this card has 60 CUs,
# so the key is gfx1030_30. ROCm 7.2 ships exactly one gfx1030 database,
# gfx1030_36 - the 72-CU RX 6800 XT. Every lookup therefore misses. A miss on
# its own would be survivable, but Applio sets torch.backends.cudnn.benchmark
# = True, which on ROCm means MIOpen EXHAUSTIVE find: compile and time every
# candidate solver, for every unique tensor shape. Measured here on mara:
# 2 h 35 m elapsed, 2 h 09 m of it one core in the compiler, GPU at 0%, 144 MB
# of compiled kernels cached, and step 1 of epoch 1 still had not run.
#
# The other half is shape churn. data_utils.TextAudioCollateMultiNSFsid pads
# each batch to the longest item IN THAT BATCH - not to the bucket boundary -
# and DistributedBucketSampler reshuffles every epoch, so epoch 2 asks for a
# fresh set of ~131 padded lengths. It is not unbounded: the padded length is
# always the max of a real sample, so the shape space is capped by the number of
# slices (~1k here) and saturates after the first several epochs. That is why
# the fix is FAST find and not a patch to the collate - quantising the padding
# would cap the shapes at ~10, but it touches the tensor the model masks and
# slices against, and a bounded cost that disappears on its own is not worth
# risking a silently wrong model for.
#
# Three fixes, in the order they matter:
#   MIOPEN_FIND_MODE=FAST     - use the immediate-mode heuristic instead of
#     benchmarking. One kernel compiled per shape instead of every candidate.
#   MIOPEN_SYSTEM_DB_PATH     - a directory of symlinks to the shipped db with
#     gfx1030_36 also exposed under this card's gfx1030_30 key, so the 106,105
#     tuned entries are actually consulted. Same ISA, different WGP count: the
#     tuning is not optimal for 30 WGPs, but it is valid, and "not optimal"
#     beats "search from nothing" by orders of magnitude.
#   APPLIO_CUDNN_BENCHMARK=0  - read by the one line patched into Applio's
#     rvc/train/train.py (original kept beside it as train.py.orig). The default
#     there is still True, so the GUI behaves exactly as it always did.
#
# What remains normal on a first run: a few minutes at `0%|  | 0/N` and a stream
# of  MIOpen(HIP): Warning [IsEnoughWorkspace] ... provided ptr: 0 size: 0
# which is solver selection, not an error. It caches to ~/.cache/miopen and
# later epochs and later models start immediately. Minutes are expected; hours
# mean one of the three exports below is not reaching the trainer.
#
# Two trainers in one experiment directory is not hypothetical. On 2026-09-04 this
# queue was restarted while the previous trainer was still alive, and for 43 minutes
# both trained `mara` into logs/mara - interleaved epoch numbers in the log, two
# lineages writing G_*.pth over each other, and both at half speed from sharing the
# GPU. It is invisible from the outside because the trainer is a GRANDCHILD:
# rvc_train.sh -> core.py train -> rvc/train/train.py. Killing the queue kills the
# shell and core.py; the trainer is reparented to init, keeps its GPU context and
# its append-mode log handle, and pgrep on the queue name finds nothing. The two
# guards below - a queue-wide flock and a per-model check for a live trainer - are
# the reason that cannot happen twice. Do not remove them either.
#
# Resuming is the default and it matters here. Applio's trainer picks up from
# the newest G_*.pth / D_*.pth in the experiment directory on its own, and
# preprocessing and feature extraction are skipped when their output is already
# there. So this script can be killed at any point - power cut, closed laptop,
# out of tokens - and re-running the same command continues instead of
# restarting. Nothing is ever deleted without --fresh.
set -uo pipefail

export MIOPEN_FIND_MODE=${MIOPEN_FIND_MODE:-FAST}
export MIOPEN_SYSTEM_DB_PATH=${MIOPEN_SYSTEM_DB_PATH:-/mnt/ssd/miopen_db}
export APPLIO_CUDNN_BENCHMARK=${APPLIO_CUDNN_BENCHMARK:-0}
# Deliberately NO cache-dir export here. Two names look usable and both are traps:
#   MIOPEN_CACHE_DIR        is a CMake define MIOpen reads as #ifdef, never from
#                           the environment. Exporting it does nothing at all.
#   MIOPEN_CUSTOM_CACHE_DIR is real, but it replaces the WHOLE path including the
#                           3.5.1.<buildhash> segment. Pointing it at
#                           /mnt/ssd/miopen_cache aimed MIOpen one level above the
#                           92MB of compiled kernels and it silently began an empty
#                           database - a fresh 2h compile. Measured 2026-09-08.
# The default path already resolves correctly: ~/.cache/miopen is a symlink to
# /mnt/ssd/miopen_cache, so the kernels land on the SSD either way, AND the build
# hash segment is kept - which is what stops a rebuilt MIOpen from loading
# incompatible kernel blobs. Leave this alone.
export TMPDIR=/mnt/ssd/tmp

APPLIO=/mnt/sata/Applio
PY=/mnt/sata/anaconda3/envs/Applio/bin/python
DATASETS=/mnt/sata/Cyberpunk2077/rvc_datasets
LOGS=/mnt/sata/Cyberpunk2077/rvc_logs
CHECK=/mnt/sata/Cyberpunk2077/ash-cache-quest/tools/rvc_check_model.py
WATCH=/mnt/sata/Cyberpunk2077/ash-cache-quest/tools/rvc_watch_health.py

SR=48000
VOCODER="HiFi-GAN"
F0=rmvpe
EMBEDDER=contentvec
BATCH=8
EPOCHS=300
SAVE_EVERY=10
GPU=0

FRESH=0
DETACH=0
WAIT=0
MODELS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --fresh)   FRESH=1 ;;
    --wait)    WAIT=1 ;;
    --detach)  DETACH=1 ;;
    --epochs)  shift; EPOCHS="$1" ;;
    --batch)   shift; BATCH="$1" ;;
    --status)
      echo "== running =="
      ps -eo pid=,etime=,args= |
        grep -E "rvc/train/(train|extract|preprocess)\.py" |
        grep -v grep |
        sed 's|[^ ]*/python[0-9.]*|py|' || echo "  nothing"
      echo "== models =="
      for d in "$APPLIO"/logs/*/; do
        m=$(basename "$d"); [ "$m" = zips ] && continue
        [ -f "$d/config.json" ] || continue
        # G_<n>.pth is named for global_step, NOT the epoch - reading it as an epoch
        # says "epoch 2620" for epoch 20 of 200, which looks finished. The epoch is
        # only spelled out in the weights filename, <model>_<epoch>e_<step>s.pth.
        ep=$(ls -1 "$d"/*e_*s.pth 2>/dev/null |
             sed 's/.*_\([0-9]*\)e_[0-9]*s\.pth$/\1/' | sort -n | tail -1)
        st=$(ls -1 "$d"/G_*.pth 2>/dev/null | sed 's/.*G_//;s/\.pth//' | sort -n | tail -1)
        # Applio never prunes process_pids. A pid still alive in here when you
        # believe nothing is training is a reparented orphan eating VRAM (D34).
        live=$(sed -n '/"process_pids"/,/]/p' "$d/config.json" | grep -o '[0-9]\+' |
               while read -r p; do kill -0 "$p" 2>/dev/null && printf '%s ' "$p"; done)
        printf "  %-18s epoch %-6s step %-8s %s%s\n" "$m" "${ep:-?}" "${st:-none}" \
               "$([ -f "$d/$m.pth" ] && echo FINISHED)" \
               "${live:+  live-pid(s): $live}"
      done
      exit 0 ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *)  MODELS+=("$1") ;;
  esac
  shift
done
[ ${#MODELS[@]} -eq 0 ] && { echo "name at least one model (or --status)" >&2; exit 2; }

mkdir -p "$LOGS"

if [ "$DETACH" = 1 ]; then
  # setsid + nohup, so it is not in this shell's process group and does not die
  # with the terminal. The log is the only channel back.
  DETACH=0 exec setsid nohup "$0" --epochs "$EPOCHS" --batch "$BATCH" \
       $([ "$FRESH" = 1 ] && echo --fresh) $([ "$WAIT" = 1 ] && echo --wait) "${MODELS[@]}" \
       >>"$LOGS/queue.log" 2>&1 &
  echo "detached. follow with:  tail -f $LOGS/queue.log"
  exit 0
fi

# Walk /proc up from $pid to init. A process started by THIS queue is our own
# work, not a leftover, and must never be killed. /proc/<pid>/status is used
# rather than /proc/<pid>/stat because a comm containing a space shifts every
# field in stat and would make the ppid read garbage.
is_descendant() {
  local pid="$1" ppid
  while [ -n "$pid" ] && [ "$pid" -gt 1 ] 2>/dev/null; do
    [ "$pid" = "$$" ] && return 0
    ppid=$(awk '/^PPid:/{print $2}' "/proc/$pid/status" 2>/dev/null)
    [ -z "$ppid" ] && return 1
    pid="$ppid"
  done
  return 1
}

# Children first: killing a dataloader's parent leaves four pt_data_workers
# behind, and those are what actually hold the queues open on the GPU.
kill_tree() {
  local pid="$1" c
  for c in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$c"; done
  kill -TERM "$pid" 2>/dev/null
}

# A pid in config.json can be days old, and Linux recycles pids (pid_max here is
# ~4194304). kill -0 proves only that SOME process holds that number; killing on
# that alone would SIGTERM, then SIGKILL, a stranger - a browser, a game, anything.
# Demand proof of identity instead: Applio's cwd, a trainer entry point in argv,
# and this model's name. Anything unreadable - a different uid - fails closed.
looks_like_trainer() {
  local pid="$1" m="$2" cmd
  [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$APPLIO" ] || return 1
  cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null) || return 1
  [ -n "$cmd" ] || return 1
  case "$cmd" in
    *rvc/train/train.py*|*core.py*train*) ;;
    *) return 1 ;;
  esac
  case " $cmd " in *" $m "*) return 0 ;; esac
  return 1
}

reap_stale_trainers() {
  local m="$1" cfg="$APPLIO/logs/$1/config.json" pid p stale=()
  [ -f "$cfg" ] || return 0
  # process_pids is a flat array of ints; one field does not justify a jq dependency
  for pid in $(sed -n '/"process_pids"/,/]/p' "$cfg" | grep -o '[0-9]\+'); do
    kill -0 "$pid" 2>/dev/null || continue
    is_descendant "$pid" && continue
    looks_like_trainer "$pid" "$m" || {
      echo "   pid $pid is alive but is not a $m trainer - recycled, leaving it alone" | tee -a "$log"
      continue
    }
    stale+=("$pid")
  done
  [ ${#stale[@]} -eq 0 ] && return 0
  echo "!! stale trainer(s) for $m still alive from an earlier run: ${stale[*]}" | tee -a "$log"
  echo "   killing them - two trainers sharing one GPU is what crashed mara" | tee -a "$log"
  for pid in "${stale[@]}"; do kill_tree "$pid"; done
  sleep "${REAP_GRACE:-5}"
  for pid in "${stale[@]}"; do
    kill -0 "$pid" 2>/dev/null && { echo "   $pid ignored SIGTERM, SIGKILL" | tee -a "$log"; kill -KILL "$pid" 2>/dev/null; }
  done
  # The multiprocessing resource_tracker is a sibling of the trainer, not a child,
  # so kill_tree never reaches it. It holds no VRAM but it outlived its trainer by
  # nine hours, and a live pid is a confusing thing to leave behind.
  for p in $(pgrep -f "multiprocessing.resource_tracker" 2>/dev/null); do
    is_descendant "$p" && continue
    # ppid 1 as well as the right cwd: a tracker that still has a parent belongs
    # to somebody's live run - the Applio GUI, say - and is not ours to kill.
    [ "$(awk '/^PPid:/{print $2}' "/proc/$p/status" 2>/dev/null)" = "1" ] || continue
    [ "$(readlink "/proc/$p/cwd" 2>/dev/null)" = "$APPLIO" ] && kill -TERM "$p" 2>/dev/null
  done
  return 0
}

run_one() {
  local m="$1" ds="$DATASETS/$1" exp="$APPLIO/logs/$1" log="$LOGS/$1.log"

  # A trainer left over from an earlier queue owns this directory even though its
  # parent is gone. Match on the trainer's own argv, not on this script's - a
  # pattern that appears in the caller's command line matches the caller too, and
  # pgrep will happily count the shell that is asking.
  local stray; stray=$(pgrep -f "rvc/train/train\.py $m " | head -1)
  if [ -n "$stray" ]; then
    echo "!! $m: pid $stray is already training this model - refusing to start a" | tee -a "$log"
    echo "   second one in $exp. Kill it first if it is stale:  kill $stray" | tee -a "$log"
    return 1
  fi

  if [ ! -d "$ds" ]; then
    echo "!! no dataset at $ds - build it first:" | tee -a "$log"
    echo "   tools/vo_dataset.py <game_speaker> --as $m" | tee -a "$log"
    return 1
  fi
  local n; n=$(find "$ds" -name '*.wav' | wc -l)
  [ "$n" -eq 0 ] && { echo "!! $ds has no .wav" | tee -a "$log"; return 1; }

  [ "$FRESH" = 1 ] && rm -rf "$exp"
  echo "=== $m : $n clip(s) : $(date '+%F %T') ===" | tee -a "$log"

  if [ -d "$exp/sliced_audios" ] && [ -n "$(ls -A "$exp/sliced_audios" 2>/dev/null)" ]; then
    echo "--- preprocess: already done, skipping" | tee -a "$log"
  else
    echo "--- preprocess" | tee -a "$log"
    ( cd "$APPLIO" && "$PY" core.py preprocess \
        --model-name "$m" --dataset-path "$ds" --sample-rate "$SR" \
        --cut-preprocess Automatic --chunk-len 3.0 --overlap-len 0.3 \
      ) >>"$log" 2>&1 || { echo "!! preprocess failed, see $log"; return 1; }
  fi

  if [ -d "$exp/extracted" ] && [ -n "$(ls -A "$exp/extracted" 2>/dev/null)" ]; then
    echo "--- extract: already done, skipping" | tee -a "$log"
  else
    echo "--- extract ($F0 / $EMBEDDER)" | tee -a "$log"
    ( cd "$APPLIO" && "$PY" core.py extract \
        --model-name "$m" --sample-rate "$SR" --f0-method "$F0" \
        --embedder-model "$EMBEDDER" --gpu "$GPU" \
      ) >>"$log" 2>&1 || { echo "!! extract failed, see $log"; return 1; }
  fi

  # Applio writes every trainer that has ever touched this model into
  # logs/<model>/config.json:process_pids and never checks whether the older ones
  # are still breathing. On 2026-09-04 that list held three pids for mara and the
  # FIRST one was still running nine hours later - reparented to init when its
  # core.py wrapper was killed, still holding 4.8 GB of VRAM, still writing into
  # this same log file and this same weights directory. Two trainers on one
  # gfx1030 is how that run ended: hipErrorIllegalAddress at epoch 118 of 200.
  reap_stale_trainers "$m"

  # Measure every checkpoint as it lands, not just the final one.
  #
  # The health gate further down runs once, at the end. That would have caught
  # mara - but only after it had spent six more hours on the GPU training an
  # already-railed model. This watcher renders each saved checkpoint against the
  # model's own training slices and shouts as soon as the high-frequency share
  # starts climbing, which preceded mara's audible failure by at least twenty
  # epochs. CPU only, GPU blanked, niced; it exits by itself once this trainer is
  # gone. Bracketed pattern so the guard cannot match its own command line.
  if [ -x "$WATCH" ] && ! pgrep -f "rvc_watch_health[.]py $m" >/dev/null 2>&1; then
    nohup setsid nice -n 10 "$PY" "$WATCH" "$m" --until-idle --poll 180 \
      >"$LOGS/$m.health.log" 2>&1 &
    echo "--- health watcher started (pid $!): $LOGS/$m.health.tsv" | tee -a "$log"
  fi

  echo "--- train (resumes from the newest checkpoint if there is one)" | tee -a "$log"
  
  # Point to TITAN 48k pretrains if available, else fall back to default Applio 48k
  PRETRAIN_G="$APPLIO/rvc/models/pretraineds/custom/titan/G-f048k-TITAN-Medium.pth"
  PRETRAIN_D="$APPLIO/rvc/models/pretraineds/custom/titan/D-f048k-TITAN-Medium.pth"
  if [ ! -f "$PRETRAIN_G" ]; then
      PRETRAIN_G="$APPLIO/rvc/models/pretraineds/hifi-gan/f0G48k.pth"
      PRETRAIN_D="$APPLIO/rvc/models/pretraineds/hifi-gan/f0D48k.pth"
      echo "--- TITAN not found, falling back to default 48k pretrains" | tee -a "$log"
  else
      echo "--- using TITAN 48k custom pretrains" | tee -a "$log"
  fi

  # Call train.py directly to pass custom pretrains and force cache_data_in_gpu=True.
  #
  # CACHE_GPU / CHECKPOINTING are overridable because fp32 activations are twice
  # the size of fp16 ones, and cache_data_in_gpu=True additionally parks the whole
  # extracted dataset in VRAM. Measured 2026-09-08 with the trainer at 10.57 GB and
  # a user whisper-cli job at 4.16 GB: 16.35 of 17.16 GB, 95%. Neither flag changes
  # the model or the training dynamics - both trade memory for speed - so if a run
  # dies with an allocator error, relaunch with:
  #     CACHE_GPU=False ./tools/rvc_train.sh mara          # frees the dataset
  #     CACHE_GPU=False CHECKPOINTING=True ./tools/rvc_train.sh mara   # + activations
  # Args: model_name, save_every_epoch, total_epoch, pretrainG, pretrainD, 
  # gpus, batch_size, sample_rate, save_only_latest, save_every_weights, 
  # cache_data_in_gpu, cleanup, vocoder, checkpointing
  ( cd "$APPLIO" && "$PY" rvc/train/train.py \
      "$m" "$SAVE_EVERY" "$EPOCHS" \
      "$PRETRAIN_G" "$PRETRAIN_D" \
      "$GPU" "$BATCH" "$SR" \
      True True "${CACHE_GPU:-True}" False "$VOCODER" "${CHECKPOINTING:-False}" \
    ) >>"$log" 2>&1 || { echo "!! train stopped, see $log"; return 1; }

  # core.py is a wrapper: killing the inner rvc/train/train.py still lets the
  # wrapper exit 0, so a zero status is not evidence a model exists. It said
  # "mara done" once for a run that never completed a single step. Check the
  # artifact, not the exit code.
  # A crashed run is not a lost run, it is a shorter one. --save-every-epoch
  # writes <model>_<epoch>e_<step>s.pth, which is the SAME small inference
  # checkpoint as the final $m.pth - the downloaded JohnnySilverhand_365e_12410s
  # .pth is literally one of these. So before calling a run a failure, look for
  # the newest one and say how far it got. Sorted on the step, not the epoch,
  # because only the step is guaranteed to increase monotonically.
  local final="$exp/$m.pth" partial="" pep=""
  if [ ! -f "$final" ]; then
    partial=$(ls -1 "$exp"/${m}_*e_*s.pth 2>/dev/null |
              sed 's/.*_\([0-9]*\)s\.pth$/\1 &/' | sort -n | tail -1 | cut -d" " -f2-)
    if [ -n "$partial" ]; then
      pep=$(basename "$partial" | sed 's/.*_\([0-9]*\)e_[0-9]*s\.pth$/\1/')
      echo "!! $m: training stopped before the end - $final was never written." | tee -a "$log"
      echo "   Newest usable checkpoint: $partial" | tee -a "$log"
      echo "   That is epoch $pep of $EPOCHS, in the same format a finished model" | tee -a "$log"
      echo "   uses. Take it with the .index and it works; or re-run this script" | tee -a "$log"
      echo "   and training resumes from it." | tee -a "$log"
    else
      echo "!! $m: training returned success but $final was never written," | tee -a "$log"
      echo "   and there is no ${m}_<n>e_<n>s.pth to fall back on." | tee -a "$log"
    fi
  fi

  # The .pth alone is a voice with no retrieval. Inference quality depends on the
  # .index, and without one Applio silently runs at index-rate 0 - which sounds
  # like a worse model rather than a missing file.
  if ls "$exp"/*.index >/dev/null 2>&1; then
    echo "--- index: already built, skipping" | tee -a "$log"
  else
    echo "--- index" | tee -a "$log"
    ( cd "$APPLIO" && "$PY" core.py index --model-name "$m" \
        --index-algorithm Auto ) >>"$log" 2>&1 \
      || echo "!! index failed - the .pth is still usable, quality will be lower" | tee -a "$log"
  fi

  # A model can train to the last epoch, write its .pth and its .index, and still
  # emit nothing but full-scale noise. mara_110e did exactly that, and was recorded
  # as "SALVAGED, VERIFIED, USABLE" because the only thing measured was overall RMS -
  # which the inference settings had already forced to match the source. The file
  # existing is not evidence. Measure the audio it produces. See D36.
  local best="$final"
  [ -f "$best" ] || best="$partial"
  if [ -n "$best" ] && [ -f "$best" ]; then
    echo "--- health check: $(basename "$best")" | tee -a "$log"
    if "$PY" "$CHECK" "$m" --pth "$best" >>"$log" 2>&1; then
      echo "   health: ok" | tee -a "$log"
    else
      echo "!! $m FAILED its health check - it emits noise, not speech." | tee -a "$log"
      echo "   Do not ship it. The measured table is in $log." | tee -a "$log"
      return 3
    fi
  fi

  if [ -f "$final" ]; then
    echo "=== $m done: $final ===" | tee -a "$log"
    return 0
  elif [ -n "$partial" ]; then
    echo "=== $m incomplete but usable: $partial (epoch $pep) ===" | tee -a "$log"
    return 2
  fi
  return 1
}

# One queue at a time. The lock is held on a descriptor for as long as this shell
# lives, so it is released by a kill, a crash or a power cut with no cleanup step -
# which matters because the whole point of this script is being killable.
exec 9>"$LOGS/queue.lock"
if [ "$WAIT" = 1 ]; then
  # Queue behind whatever is running instead of refusing.
  #
  # Waiting on the lock alone is NOT enough, and the first version of this that
  # did so put a second job on the GPU inside one second. The queue that was
  # running had been started from a build of this script that predates the flock,
  # so it held no lock: /proc/<pid>/fd/9 did not exist. An uncontended lock is
  # indistinguishable from a free one.
  #
  # The lock guards queue shells. The invariant that actually matters is ONE
  # TRAINER ON THE GPU - the thing whose violation destroyed mara. So wait on a
  # live trainer process, which also covers a hand-run core.py, the Applio web
  # UI, and any older copy of this script. Bracketed so the pattern in this very
  # command line cannot match the shell running it.
  waited=0
  while :; do
    others=$(pgrep -f 'rvc/train/train[.]py' 2>/dev/null | tr '\n' ' ')
    [ -z "$others" ] && break
    [ $((waited % 10)) -eq 0 ] &&
      echo "--- waiting for trainer(s) $others : $(date '+%F %T')"
    waited=$((waited + 1))
    sleep "${WAIT_POLL:-120}"
  done
  [ "$waited" -gt 0 ] && echo "--- GPU free after $((waited * ${WAIT_POLL:-120} / 60)) min : $(date '+%F %T')"
  flock 9
  echo "--- lock acquired : $(date '+%F %T')"
elif ! flock -n 9; then
  echo "!! another rvc_train.sh already holds $LOGS/queue.lock - not starting." >&2
  echo "   see what it is doing with:  tools/rvc_train.sh --status" >&2
  exit 1
fi

for m in "${MODELS[@]}"; do
  run_one "$m"
  case $? in
    0) ;;
    2) echo "!! $m stopped early but left a checkpoint that passed its health check - the queue continues" ;;
    3) echo "!! $m trained but the result is NOISE - do not ship it. See $LOGS/$m.log" ;;
    *) echo "!! $m did not finish - the queue continues" ;;
  esac
done
echo "queue finished $(date '+%F %T')"
