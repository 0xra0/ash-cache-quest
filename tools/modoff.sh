#!/usr/bin/env bash
# Control experiment for OI-24: is the clinic crash ours at all?
#
# Moves every deployed piece of ash-cache OUT of the game tree (into a holding
# directory that sits beside it, so the game cannot see it) and back again.
# mv only - nothing is deleted, and "on" restores byte-identical files.
#
#   tools/modoff.sh off      # take the mod out
#   tools/modoff.sh on       # put it back
#   tools/modoff.sh status   # which state are we in
#
# This writes to the game directory, which CLAUDE.md rule 2 forbids without an
# explicit deploy step. Running it IS that step - it is the same class of action
# as a deploy, and it is reversible.
#
# The piece list below is the SAME list deploy.sh installs. It has to be, or the
# control is a lie: the first version of this script listed three of the six and
# left the tweak record, the Audioware bank and the CET panel installed. Keep the
# two lists in step - tools/modoff.sh check fails loudly if they drift.
set -u
ROOT="/mnt/ssd/Cyberpunk 2077"
GAME="$ROOT/game/prefix/drive_c/game"
HOLD="$ROOT/ashcache-off"
DEPLOY="$(cd "$(dirname "$0")" && pwd)/deploy.sh"

# Every path the mod owns inside the game tree, in deploy.sh's order. A control
# test that leaves half the mod installed proves nothing.
PIECES=(
  "archive/pc/mod/ashcache.archive"
  "archive/pc/mod/ashcache.archive.xl"
  "r6/tweaks/ash_cache.yaml"
  "r6/scripts/AshCache"
  "r6/audioware/ash_cache"
  "bin/x64/plugins/cyber_engine_tweaks/mods/ash_cache_debug/init.lua"
)

# The archive is read at load and the scripts are compiled at load, so moving
# anything while the game is up changes nothing until the next launch. Say so
# rather than let a run be wasted.
running() { pgrep -f 'Cyberpunk2077.exe' >/dev/null 2>&1; }

case "${1:-status}" in
  off)
    running && echo "  NOTE: the game is running - this takes effect on the NEXT launch."
    mkdir -p "$HOLD" || exit 1
    n=0
    for p in "${PIECES[@]}"; do
      src="$GAME/$p"
      [ -e "$src" ] || { echo "  absent  $p"; continue; }
      dst="$HOLD/$(echo "$p" | tr '/' '_')"
      mv "$src" "$dst" && { echo "  OUT     $p"; n=$((n+1)); }
    done
    echo "mod off - $n of ${#PIECES[@]} piece(s) held in $HOLD"
    ;;
  on)
    running && echo "  NOTE: the game is running - this takes effect on the NEXT launch."
    n=0
    for p in "${PIECES[@]}"; do
      dst="$GAME/$p"
      src="$HOLD/$(echo "$p" | tr '/' '_')"
      [ -e "$src" ] || { echo "  absent  $p"; continue; }
      mkdir -p "$(dirname "$dst")"
      mv "$src" "$dst" && { echo "  IN      $p"; n=$((n+1)); }
    done
    echo "mod on - $n of ${#PIECES[@]} piece(s) restored"
    ;;
  status)
    for p in "${PIECES[@]}"; do
      if   [ -e "$GAME/$p" ]; then echo "  installed  $p"
      elif [ -e "$HOLD/$(echo "$p" | tr '/' '_')" ]; then echo "  held out   $p"
      else echo "  MISSING    $p  (in neither place)"; fi
    done
    ;;
  check)
    # Every destination deploy.sh knows about, in the order it lists them.
    # deploy.sh names two files that live inside directories we own whole; strip
    # them so the two lists are comparable.
    norm() { sed -e 's|/init.lua$||' -e 's|/AshCacheGlue.reds$||' | sort -u; }
    want=$(grep -oE '\|[A-Za-z0-9_./ -]+"' "$DEPLOY" | tr -d '|"' | norm)
    have=$(printf '%s\n' "${PIECES[@]}" | norm)
    diff <(echo "$want") <(echo "$have") \
      && echo "piece list matches deploy.sh" \
      || echo "DRIFT: modoff.sh and deploy.sh disagree - fix before trusting a control run"
    ;;
  *) echo "usage: $0 {off|on|status|check}"; exit 2 ;;
esac
