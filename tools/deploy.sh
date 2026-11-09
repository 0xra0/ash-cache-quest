#!/usr/bin/env bash
# mod/ -> the game. THE ONE PLACE ALLOWED TO WRITE TO THE GAME DIRECTORY (rule 2),
# and it refuses to unless told twice: no --yes means it prints the copies and
# stops.
#
# It exists because the mod lands in five places and three of them are loose files
# outside the archive. Copying the archive and forgetting r6/tweaks gives a quest
# that mounts, shows its journal entry, and cannot grant a single item - which
# from inside the game looks like a broken build rather than a missed copy.
# tools/collect_logs.py detects that state; this prevents it.
#
#   tools/deploy.sh                  say what would be copied
#   tools/deploy.sh --yes            do it
#   tools/deploy.sh --remove         undo it - deletes ONLY the five paths below
#   tools/deploy.sh --only SUBSTR .. restrict to paths containing SUBSTR
#
# --only exists for bisects. A control is only a control if ONE thing moved, and
# a full deploy moves six paths - including an archive rebuilt from unchanged
# inputs, which is the same build but not the same bytes. D79 drew a conclusion
# from a control that had three of six paths left installed; this is how not to
# repeat that.
#
#   tools/deploy.sh --only .archive.xl --yes   # swap the manifest, touch nothing else
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GAME="/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game"

# from (under ROOT)                              to (under GAME)
PAIRS=(
  "mod/archive/pc/mod/ashcache.archive|archive/pc/mod/ashcache.archive"
  "mod/archive/pc/mod/ashcache.archive.xl|archive/pc/mod/ashcache.archive.xl"
  "mod/r6/tweaks/ash_cache.yaml|r6/tweaks/ash_cache.yaml"
  "mod/r6/scripts/AshCache/AshCacheGlue.reds|r6/scripts/AshCache/AshCacheGlue.reds"
  "mod/r6/scripts/AshCache/AshCacheChipData.reds|r6/scripts/AshCache/AshCacheChipData.reds"
  "mod/r6/scripts/AshCache/AshCacheChipTree.reds|r6/scripts/AshCache/AshCacheChipTree.reds"
  "mod/r6/scripts/AshCache/AshCacheIdle.reds|r6/scripts/AshCache/AshCacheIdle.reds"
  "mod/r6/scripts/AshCache/AshCacheTrophy.reds|r6/scripts/AshCache/AshCacheTrophy.reds"
  "dev/cet/ash_cache_debug/init.lua|bin/x64/plugins/cyber_engine_tweaks/mods/ash_cache_debug/init.lua"
)

# Directories, not files. The Audioware bank is a manifest plus the .wav files it
# names by bare filename, so it only means anything as a whole folder - and it
# has to be MIRRORED, not merged: a line dropped from the quest must lose its
# recording in the game too, or the folder slowly fills with audio nothing plays.
DIRS=(
  "mod/r6/audioware/ash_cache|r6/audioware/ash_cache"
)

[ -d "$GAME" ] || { echo "game not found at $GAME"; exit 1; }

mode="dry"
only=""
while [ $# -gt 0 ]; do
  case "$1" in
    --only) only="${2:?--only needs a substring}"; shift 2 ;;
    *) mode="$1"; shift ;;
  esac
done

# Applied to the destination path, which is the half a human reads off a deploy
# listing. An --only that matches nothing is a mistake, not a no-op: it would
# print "deployed" having copied zero files.
if [ -n "$only" ]; then
  kept=0
  for p in "${PAIRS[@]}"; do case "${p#*|}" in *"$only"*) kept=$((kept+1));; esac; done
  for d in "${DIRS[@]}"; do case "${d#*|}" in *"$only"*) kept=$((kept+1));; esac; done
  [ "$kept" -gt 0 ] || { echo "--only '$only' matches none of the deployed paths"; exit 1; }
  echo "--only '$only': $kept of $(( ${#PAIRS[@]} + ${#DIRS[@]} )) path(s)"
fi
skip() { [ -n "$only" ] && case "$1" in *"$only"*) return 1;; *) return 0;; esac; return 1; }

if [ "$mode" = "--remove" ]; then
  for p in "${PAIRS[@]}"; do
    skip "${p#*|}" && continue
    dst="$GAME/${p#*|}"
    if [ -f "$dst" ]; then rm -f "$dst"; echo "removed  ${p#*|}"; else echo "absent   ${p#*|}"; fi
  done
  for d in "${DIRS[@]}"; do
    skip "${d#*|}" && continue
    dst="$GAME/${d#*|}"
    if [ -d "$dst" ]; then rm -rf "$dst"; echo "removed  ${d#*|}/"; else echo "absent   ${d#*|}/"; fi
  done
  rmdir "$GAME/r6/audioware" 2>/dev/null || true
  # Only our own directories, only if empty. rmdir refuses a non-empty one, which
  # is the safety: if something else lives there, it stays.
  rmdir "$GAME/r6/scripts/AshCache" 2>/dev/null || true
  rmdir "$GAME/bin/x64/plugins/cyber_engine_tweaks/mods/ash_cache_debug" 2>/dev/null || true
  echo
  echo "the game is back to how it was. A running game keeps what it loaded -"
  echo "restart it before believing this."
  exit 0
fi

missing=0
for p in "${PAIRS[@]}"; do
  src="$ROOT/${p%|*}"
  [ -f "$src" ] || { echo "NOT BUILT  ${p%|*}"; missing=1; }
done
# A directory is allowed to be absent - gen_audioware.py writes no bank when
# vo/ is empty, and a quest with no recordings is a buildable state. What is not
# allowed is a bank with no manifest in it.
for d in "${DIRS[@]}"; do
  src="$ROOT/${d%|*}"
  if [ -d "$src" ] && ! ls "$src"/*.yml >/dev/null 2>&1; then
    echo "NOT BUILT  ${d%|*} (no manifest)"; missing=1
  fi
done
[ "$missing" = 0 ] || { echo; echo "run tools/build.sh first"; exit 1; }

for p in "${PAIRS[@]}"; do
  skip "${p#*|}" && continue
  src="$ROOT/${p%|*}"; rel="${p#*|}"; dst="$GAME/$rel"
  if [ "$mode" = "--yes" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "copied   $rel"
  else
    printf '%-9s %s\n' "$([ -f "$dst" ] && echo replace || echo new)" "$rel"
  fi
done

for d in "${DIRS[@]}"; do
  skip "${d#*|}" && continue
  src="$ROOT/${d%|*}"; rel="${d#*|}"; dst="$GAME/$rel"
  # A source directory that is GONE has to take the deployed one with it. It is
  # not "nothing to copy": gen_audioware.py stops writing the bank the moment
  # the engine can play the lines itself (D93), and skipping here would leave
  # the old bank installed, still doubling every line. Mirroring means both
  # directions.
  if [ ! -d "$src" ]; then
    if [ -d "$dst" ]; then
      if [ "$mode" = "--yes" ]; then rm -rf "$dst"; echo "removed  $rel/ (no longer built)"
      else printf '%-9s %s\n' "remove" "$rel/ (no longer built)"; fi
    fi
    continue
  fi
  n=$(ls -1 "$src" | wc -l)
  if [ "$mode" = "--yes" ]; then
    rm -rf "$dst"
    mkdir -p "$dst"
    cp "$src"/* "$dst"/
    echo "copied   $rel/ ($n file(s))"
  else
    printf '%-9s %s\n' "$([ -d "$dst" ] && echo replace || echo new)" "$rel/ ($n file(s))"
  fi
done

echo
if [ "$mode" = "--yes" ]; then
  echo "deployed. The CET panel is dev-only and is the one piece a player never gets."
  echo "Launch, open CET's overlay, and read the Status tab before anything else."
else
  echo "nothing was written. Re-run with --yes to do it."
fi
