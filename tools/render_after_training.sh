#!/usr/bin/env bash
# Render the quest's English lines as soon as the GPU stops training, then measure
# the result. Meant to be launched detached and left alone.
#
# WHY THIS EXISTS AND NOT JUST A LATER COMMAND
# RVC inference wants the GPU, and render_lines.py refuses to start while a
# trainer is visible - correctly, because sharing the card is what destroyed the
# first mara. So the render cannot simply be queued behind the training; it has
# to wait for the card and then take it. That wait is hours, which is the one
# thing a person should not be doing.
#
# WHAT IT WILL NOT DO
# It renders to a dated audition directory, never into vo/. Nothing becomes the
# shipped voice without somebody listening to it first - that is the whole reason
# --out exists. And it health-gates every model it is about to use, because a
# railed checkpoint renders 43 files of confident noise and the numbers that
# would catch it are the ones rvc_check_model.py measures.
set -u

ROOT=/mnt/sata/Cyberpunk2077/ash-cache-quest
LOGS=/mnt/sata/Cyberpunk2077/rvc_logs
STAMP=$(date '+%Y-%m-%d')
OUT=$LOGS/audition_final/$STAMP
LOG=$LOGS/render_after_training.log
POLL=${POLL:-120}
MODELS=${MODELS:-mara}          # the models the render needs healthy; V uses the
                                # downloaded male_v, which no gate here can retrain

say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "waiting for the GPU (poll ${POLL}s)"

# Two consecutive clear polls, not one. rvc_train.sh --wait queues jobs back to
# back: between mara exiting and johnny starting there is a window where no
# trainer exists and the card is about to be taken again. One clear poll would
# walk straight into it. The queue shell outliving the trainer is the tell, so
# both patterns are checked. Brackets keep the pattern from matching this script.
clear_polls=0
while :; do
    busy=$(pgrep -f 'rvc/train/train[.]py' 2>/dev/null | tr '\n' ' ')
    queue=$(pgrep -f 'rvc_train[.]sh' 2>/dev/null | tr '\n' ' ')
    if [ -z "$busy" ] && [ -z "$queue" ]; then
        clear_polls=$((clear_polls + 1))
        [ "$clear_polls" -ge 2 ] && break
    else
        [ "$clear_polls" -ne 0 ] && say "not free after all: trainer($busy) queue($queue)"
        clear_polls=0
    fi
    sleep "$POLL"
done
say "GPU free"

for m in $MODELS; do
    line=$("$ROOT/tools/rvc_check_model.py" "$m" 2>&1 | grep -E "^${m}_[0-9]+e_" | tail -1)
    say "health $m: ${line:-NO OUTPUT}"
    case "$line" in
        *ok*) ;;
        *)  say "REFUSING to render: $m did not pass the health gate."
            say "  Check it by hand:  tools/rvc_check_model.py --all $m"
            exit 1 ;;
    esac
done

mkdir -p "$OUT"
say "rendering en-us -> $OUT"
"$ROOT/tools/render_lines.py" --locale en-us --tts piper --out "$OUT" >>"$LOG" 2>&1
rc=$?
say "render_lines exited $rc"
[ $rc -ne 0 ] && exit $rc

# The render can succeed and still be wrong - RVC emits a full-length file whatever
# it does. rvc_audition compares each line against the piper source it came from,
# which is the only version of "is this clean" that means anything for short lines.
say "auditioning"
"$ROOT/tools/rvc_audition.py" "$OUT" >>"$LOG" 2>&1
arc=$?
n=$(find "$OUT" -name '*.wav' | wc -l)
say "done: $n file(s) in $OUT"

# The audition's exit code IS the verdict - 1 means at least one line failed a
# threshold, and it is the only thing here that can tell a good batch from a
# batch of confident noise. Ignoring it (as this did until it was tested) turns
# a measured failure into a line in a log nobody reads, under a cheerful "done".
case $arc in
    0) say "VERDICT: clean. Listen, then promote:  tools/vo_promote.py $OUT" ;;
    *) say "VERDICT: FAILED (rvc_audition exit $arc). Do NOT promote this batch."
       say "  what failed:  grep -A20 'line(s) failed' $LOG"
       say "  re-measure:   tools/rvc_audition.py $OUT -v" ;;
esac
say "Nothing here is the shipped voice until vo_promote.py copies it."
exit $arc
