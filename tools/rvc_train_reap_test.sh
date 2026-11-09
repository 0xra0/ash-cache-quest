#!/usr/bin/env bash
# Regression test for the stale-trainer reaper in tools/rvc_train.sh (D34).
#
# The bug it guards against: killing tools/rvc_train.sh does not kill the
# trainer, because the trainer is a grandchild (script -> core.py ->
# rvc/train/train.py) and reparents to init. One such orphan held 4.87 GB of
# VRAM for nine hours and took the supervised run down with a page fault.
#
# Three properties have to hold at once, and they pull against each other:
#   1. a genuine orphan trainer, and its whole child tree, is killed;
#   2. a process this queue started is NEVER killed - is_descendant;
#   3. a pid that merely happens to hold a recycled number is NEVER killed -
#      looks_like_trainer. config.json can be days old and pid_max wraps.
#
# Property 2 is why the first version of this test looked like a failure: with
# plain `setsid` the fake orphan stayed a child of the test shell, and the
# reaper correctly refused to touch it. `setsid --fork` is what actually
# orphans it.
#
# Safe to run beside a live training run - it only ever kills pids it created.
set -u
SCRIPT="$(cd "$(dirname "$0")" && pwd)/rvc_train.sh"
APPLIO=${APPLIO:-/mnt/sata/Applio}
log=/dev/null
REAP_GRACE=1
T="${TMPDIR_TEST:-/mnt/sata/Cyberpunk2077/wk_scratch}/reaptest.$$"
M=reaptest_$$
fail=0

cleanup() {
  [ -s "$T/parent.pid" ] && kill -KILL $(cat "$T/parent.pid") 2>/dev/null
  [ -s "$T/kids.pid" ]   && kill -KILL $(cat "$T/kids.pid")   2>/dev/null
  [ -s "$T/decoy.pid" ]  && kill -KILL $(cat "$T/decoy.pid")  2>/dev/null
  rm -rf "$APPLIO/logs/$M" "$T"
}
trap cleanup EXIT

# Source only the helper block, straight out of the installed script, so this
# test can never drift from what actually ships.
mkdir -p "$T"
sed -n "$(grep -n '^is_descendant() {' "$SCRIPT" | cut -d: -f1),$(( $(grep -n '^run_one() {' "$SCRIPT" | cut -d: -f1) - 1 ))p" \
    "$SCRIPT" > "$T/funcs.sh"
. "$T/funcs.sh"

ARGV="python rvc/train/train.py $M 10 200 pretrained.pth"
# (a) the orphan: Applio's cwd, a trainer argv, three children. Must be reaped.
setsid --fork bash -c "cd $APPLIO; exec -a '$ARGV' bash -c 'echo \$\$ > $T/parent.pid;
  for i in 1 2 3; do ( exec -a fake_pt_data_worker sleep 600 ) & done
  echo \$(jobs -p) > $T/kids.pid; wait'" &
# (b) the decoy: identical argv, wrong cwd. Stands in for a recycled pid. Must survive.
setsid --fork bash -c "cd /mnt/sata/Cyberpunk2077; exec -a '$ARGV' bash -c 'echo \$\$ > $T/decoy.pid; sleep 600'" &

# Wait without calling sleep: a fifo opened read-write gives `read -t` something
# to block on that never delivers, so the timeout is the wait.
mkfifo "$T/wait.fifo"; exec 3<> "$T/wait.fifo"
for _ in $(seq 1 60); do
  [ -s "$T/parent.pid" ] && [ -s "$T/decoy.pid" ] && [ -s "$T/kids.pid" ] && break
  read -t 0.1 -u 3 _ 2>/dev/null || true
done
P=$(cat "$T/parent.pid"); D=$(cat "$T/decoy.pid"); K=$(cat "$T/kids.pid")
[ "$(awk '/^PPid:/{print $2}' "/proc/$P/status")" = "1" ] || { echo "SETUP FAILED: orphan has a parent"; exit 1; }

mkdir -p "$APPLIO/logs/$M"
printf '{\n  "process_pids": [ %s, %s, %s, 4194300 ]\n}\n' "$P" "$D" "$$" > "$APPLIO/logs/$M/config.json"

ck() { # ck <label> <expected pass?> ; reads $? of the preceding test via $2
  if [ "$2" = 1 ]; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi
}
echo "--- predicates ---"
looks_like_trainer "$P"  "$M" && ck "orphan is a trainer" 1                || ck "orphan is a trainer" 0
looks_like_trainer "$D"  "$M" && ck "decoy rejected (wrong cwd)" 0         || ck "decoy rejected (wrong cwd)" 1
looks_like_trainer "$$"  "$M" && ck "test shell rejected" 0                || ck "test shell rejected" 1
is_descendant "$$"            && ck "test shell seen as own work" 1        || ck "test shell seen as own work" 0
is_descendant "$P"            && ck "orphan seen as stale" 0               || ck "orphan seen as stale" 1

echo "--- reap ---"
reap_stale_trainers "$M"

echo "--- outcome ---"
kill -0 "$P" 2>/dev/null && ck "orphan killed" 0 || ck "orphan killed" 1
for k in $K; do kill -0 "$k" 2>/dev/null && ck "child $k killed" 0 || ck "child $k killed" 1; done
kill -0 "$D" 2>/dev/null && ck "decoy survived" 1 || ck "decoy survived" 0

[ $fail -eq 0 ] && echo "PASS" || echo "FAIL"
exit $fail
