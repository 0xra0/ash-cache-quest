#!/usr/bin/env bash
# Type-check the generated redscript against the game's own compiled script
# bundle. This is the strongest form rule 8 can take for a script API: not
# "a reference mod does this", but "the symbol resolved against this exact
# game build".
#
# READ-ONLY on the game directory (rule 2). It opens r6/cache/final.redscripts
# and writes nothing; redscript's `lint` never emits an output bundle. Note it
# reads final.redscripts, not final.redscripts.modded - the glue must compile
# against vanilla alone, with no other installed mod in scope.
#
# Degrades to a printed note rather than failing when the game or the compiler
# is not on this machine, so the build still runs on a box without the game -
# same policy as the TweakDB name check in validate.py (D11).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

REDSCRIPT="${REDSCRIPT_CLI:-/mnt/sata/Cyberpunk2077/everything/redscript/target/release/redscript-cli}"
BUNDLE="${CP2077_SCRIPTS:-/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/r6/cache/final.redscripts}"
SRC="$ROOT/build/scripts"

if [ ! -x "$REDSCRIPT" ]; then
  echo "note: no redscript-cli at $REDSCRIPT - glue not type-checked"
  echo "      build it with: cargo build --release  in /mnt/sata/Cyberpunk2077/everything/redscript"
  exit 0
fi
if [ ! -f "$BUNDLE" ]; then
  echo "note: no script bundle at $BUNDLE - glue not type-checked"
  exit 0
fi
if [ ! -d "$SRC" ]; then
  echo "lint_glue: $SRC does not exist - run tools/gen_glue.py first" >&2
  exit 1
fi

OUT="$("$REDSCRIPT" lint -s "$SRC" -b "$BUNDLE" 2>&1 | grep -Ev "TRACE|DEBUG")"
echo "$OUT" | sed 's/^/  /'
# `lint` exits 0 even when it reports errors, so the verdict has to be read out
# of the text. A silently-not-compiling glue file is a quest that never starts.
if ! echo "$OUT" | grep -q "Compilation successful"; then
  echo "lint_glue: FAILED" >&2
  exit 1
fi

# Second pass for the Splinter tree (D115). Its menu half is behind
# @if(ModuleExists("CustomPerkFramework")), and the bundle is vanilla-only, so the
# pass above never sees that code. Stage read-only copies of the framework and
# Codeware beside ours and count errors in OUR files only - both third-party
# trees trip this newer compiler's stricter rules while compiling fine in game.
GAME="$(dirname "$(dirname "$(dirname "$BUNDLE")")")"
CPF="$GAME/r6/scripts/CustomPerkFramework"
CW="$GAME/red4ext/plugins/Codeware/Scripts"
if [ -d "$CPF" ] && [ -d "$CW" ]; then
  STAGE="$ROOT/build/lint_chip"
  rm -rf "$STAGE"; mkdir -p "$STAGE/ours"
  cp -r "$CPF" "$STAGE/cpf"; rm -rf "$STAGE/cpf/Examples"
  cp -r "$CW" "$STAGE/codeware"
  cp "$SRC"/*.reds "$STAGE/ours/"
  OUT2="$("$REDSCRIPT" lint -s "$STAGE" -b "$BUNDLE" 2>&1 | grep -Ev "TRACE|DEBUG")"
  N="$(echo "$OUT2" | grep -c "ERROR.*/ours/" || true)"
  if [ "$N" != "0" ]; then
    echo "$OUT2" | grep -A4 "ERROR.*/ours/" | sed 's/^/  /'
    echo "lint_glue: chip tree FAILED with CustomPerkFramework in scope ($N error(s))" >&2
    exit 1
  fi
  echo "  chip tree: 0 errors with CustomPerkFramework + Codeware in scope"
else
  echo "  note: CustomPerkFramework or Codeware not installed - chip tree menu not type-checked"
fi
exit 0
