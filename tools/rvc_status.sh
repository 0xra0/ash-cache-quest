#!/usr/bin/env bash
# One screenful of RVC training state. No tqdm.
#
# Applio writes its per-epoch summary into the same stream as tqdm's progress
# bar, so `tail` on a training log returns kilobytes of block characters per
# useful line. The summary lines are the only ones containing "| epoch=", so
# everything here filters on that.
set -u
APPLIO=/mnt/sata/Applio
LOGS=/mnt/sata/Cyberpunk2077/rvc_logs

printf '=== %s ===\n' "$(date '+%F %T')"

printf '\n-- on the GPU --\n'
if ! pgrep -af 'rvc/train/train[.]py' | sed 's/ .*train\.py / train.py /'; then
  echo '   (no trainer running)'
fi
if command -v rocm-smi >/dev/null 2>&1; then
  rocm-smi --showuse --showmemuse 2>/dev/null |
    grep -Ei 'GPU use|Memory Allocated|GPU memory use' | head -4
fi

printf '\n-- queue shells --\n'
# Two self-match traps here. Bracketing the dot stops the pattern matching its own
# text, but every OTHER process in this pipeline carries the plain string in its
# argv - a `sed 's/...rvc_train\.sh/'` tidying the output listed itself as a queue
# shell. So filter this script's own name out, and read the pid and the tail of the
# command line with the shell rather than another process.
pgrep -af 'rvc_train[.]sh' 2>/dev/null | grep -v rvc_status |
  while read -r pid rest; do printf '   %s %s\n' "$pid" "${rest##*/}"; done |
  grep . || echo '   (none)'

for m in "$@"; do
  printf '\n-- %s --\n' "$m"
  if [ -f "$LOGS/$m.log" ]; then
    # tqdm ends each update with a carriage return, not a newline, so a whole
    # epoch of progress bars and its summary are ONE line to grep - matching it
    # prints 40 KB of block characters. Split on \r first; that is what actually
    # separates the records.
    tr '\r' '\n' < "$LOGS/$m.log" | grep -a '| epoch=' | tail -3 | sed 's/^/   /'
  else
    echo "   no $LOGS/$m.log"
  fi
  n=$(ls "$APPLIO/logs/$m/${m}_"*e_*s.pth 2>/dev/null | wc -l)
  printf '   checkpoints: %s\n' "$n"
  if [ -f "$LOGS/$m.health.tsv" ]; then
    echo '   health (epoch clip% p95 gap hf verdict):'
    tail -4 "$LOGS/$m.health.tsv" | awk -F'\t' '{printf "     %-6s %7s %8s %8s %7s  %s\n",$1,$3,$4,$5,$6,$7}'
  fi
done

printf '\n-- disk --\n'
df -h /mnt/sata | tail -1
