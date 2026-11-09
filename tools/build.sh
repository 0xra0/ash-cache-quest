#!/usr/bin/env bash
# Full build: source/ -> mod/. Never touches the game directory.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WK="DOTNET_ROLL_FORWARD=LatestMajor dotnet /mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
cd "$ROOT"

# Everything below is mirrored into build/build.log. It used to be written by
# hand with a "| tee", which meant the file in build/ could be from a build two
# days older than the archive next to it - a generated directory holding a stale
# record of itself is worse than holding none. Now it cannot lag the build.
mkdir -p build
exec > >(tee build/build.log) 2>&1

echo "== 1. allocate lockeys and subtitle ids"
python3 tools/alloc_lockeys.py
python3 tools/alloc_subtitle_ids.py

echo "== 2. validate source"
python3 tools/validate.py
# The graph invariant validate.py cannot see: what a SECOND entry into the
# phase would do. A phase_revision bump (OI-15) is the only way to repair a
# save whose journal predates a graph change, and it re-walks the graph from
# the start - so every irreversible node needs a guard, and a guard is easy to
# forget when adding one. D50.
python3 tools/replaytest.py
# D54's invariant, which neither validate.py nor replaytest.py can see: the log
# panel concatenates every still-Active description into one field, so two live
# paragraphs render as one run-on block. Held out of the build until D54 landed
# because it failed on the shipped graph. Bypassing any one of the eight
# retirement nodes puts it back to 2 - verified 8/8. It cannot see a severed
# graph (it reports a reassuring 1 when nothing progresses); replaytest above is
# the gate for that, which is why the order matters.
python3 tools/descpanel.py > /dev/null

echo "== 3. generate resources"
# Not CR2W and not packed: TweakXL reads loose YAML from r6/tweaks/. Generated
# here with everything else so a character rename can never leave the record and
# the scene that spawns it disagreeing.
python3 tools/gen_tweak.py
python3 tools/gen_journal.py
python3 tools/gen_onscreens.py
python3 tools/gen_subtitles.py
# Before the map, the audio: any .wav dropped in vo/<locale>/ becomes a .wem
# beside it. A .wem with no source file next to it was hand-encoded and is
# never touched.
#
# Two encoders, in this order on purpose. Wwise 2023.1.14 runs in the Wine
# prefix now (D91), and it writes the SAME Vorbis every shipped custom voice
# line uses - fmt tag 0xFFFF - so it goes first and wins wherever it is
# installed. wav_to_wem.py then finds every .wem current and skips it; on a
# machine with no Wwise it does the whole job in PCM instead, which is the
# fallback its header documents. Neither tool ever converts what the other
# just wrote.
python3 tools/wwise_wem.py
python3 tools/wav_to_wem.py
# Reads vo/<locale>/*.wem, not source/. The files on disk are the manifest:
# a line gets audio when its .wem exists and not before, so there is no second
# place to forget to edit. Emits nothing at all while vo/ is empty.
python3 tools/gen_vomap.py
# The SAME recordings again, as an Audioware bank - and now a FALLBACK, which is
# the opposite of what D67 said. locVoiceoverMap was silent from the day it
# shipped because wav_to_wem.py could only write PCM; since D92 it carries real
# Wwise Vorbis and it works. Audioware's detour plays its copy and then calls the
# engine anyway, so with both live the player hears every line twice - D93, the
# echo. gen_audioware.py now writes nothing while the .wem are Vorbis and the
# .xl ships a vomaps block, and writes the bank when either is missing, which is
# the same primary/fallback shape as wwise_wem.py -> wav_to_wem.py above.
# ASHCACHE_AUDIOWARE=1 forces the bank back for an A/B.
python3 tools/gen_audioware.py
# Same rule, one folder over: lipsync/<locale>/<character>.anims is the
# manifest. Emits nothing while lipsync/ is empty, so a voiced-but-still-faced
# build stays loadable instead of shipping a map naming files that aren't packed.
python3 tools/gen_lipmap.py
python3 tools/gen_scene.py
python3 tools/gen_sector.py
python3 tools/gen_questphase.py
# Also not CR2W and not packed: redscript is loose source under r6/scripts/, which
# the game compiles at launch. Generated from the same source/ as everything else
# so the coordinates it triggers on and the coordinates the map pin uses cannot
# drift apart.
python3 tools/gen_glue.py
# The Splinter perk tree (D115): generated data table + the hand-written tree
# beside it, so lint_glue.sh type-checks all three .reds files together.
python3 tools/gen_chip.py
cp source/scripts/AshCacheChipTree.reds build/scripts/AshCacheChipTree.reds
cp source/scripts/AshCacheIdle.reds build/scripts/AshCacheIdle.reds   # D171
cp source/scripts/AshCacheTrophy.reds build/scripts/AshCacheTrophy.reds   # D186
# Dev only, never shipped: deployed to dev/, and the deploy step copies mod/.
python3 tools/gen_cet.py
echo "== 3b. type-check the glue against the game's script bundle"
tools/lint_glue.sh
# Cheap insurance on the one generated file nothing else parses. CET reports a
# Lua syntax error into its own log and then silently has no window.
if command -v luajit >/dev/null 2>&1; then
  luajit -e 'local f,e=loadfile("build/cet/init.lua"); if not f then io.stderr:write("cet: "..tostring(e).."\n"); os.exit(1) end' \
    && echo "  cet init.lua parses"
fi

echo "== 4. convert to engine resources"
rm -rf build/tree && mkdir -p build/tree/staging
# One process for all of them. This used to be a loop, and since a dotnet start
# costs ~30 s against a converted file's ~1 s, the build spent minutes doing
# nothing but starting the same program fourteen times. The files are named
# explicitly rather than passing the directory, because build/ also holds
# negtest/'s copy of source/ and a recursive *.json would sweep that in too.
if ! eval $WK convert deserialize build/*.json -o build/tree >/dev/null 2>&1; then
  # The batch says which file it choked on only in its own output, so fall back
  # to one at a time to name the culprit and show the error.
  for f in build/*.json; do
    eval $WK convert deserialize "$f" -o build/tree >/dev/null 2>&1 || {
      echo "FAILED converting $f"
      eval $WK convert deserialize "$f" -o build/tree 2>&1 | sed -n '2,4p'; exit 1; }
  done
  echo "FAILED converting (batch failed but every file converts alone - "
  echo "  something about the batch itself, not the JSON)"; exit 1
fi
for f in build/*.json; do
  out="build/tree/$(basename "${f%.json}")"
  [ -f "$out" ] || { echo "FAILED: $f produced no $out"; exit 1; }
done

echo "== 5. lay out the archive tree"
S=build/tree/staging
mkdir -p "$S/mod/ash_cache/journal" "$S/mod/ash_cache/quest" "$S/mod/ash_cache/worlds"
for loc in en-us ua-ua; do
  mkdir -p "$S/mod/ash_cache/localization/$loc/subtitles"
done
cp build/tree/ash_cache.journal        "$S/mod/ash_cache/journal/ash_cache.journal"
for loc in en-us ua-ua; do
  L="$S/mod/ash_cache/localization/$loc"
  cp "build/tree/onscreens_$loc.json"       "$L/onscreens.json"
  # The map and the lines it points at. gen_subtitles.py bakes these two names
  # into the map's depot path, so renaming here silently breaks the lookup.
  cp "build/tree/subtitlemap_$loc.json"     "$L/subtitles/ash_cache.json"
  cp "build/tree/subtitlelines_$loc.json"   "$L/subtitles/ash_cache_lines.json"
  # Voiceover, when there is any. The map's raRefs name each .wem by the depot
  # path it lands at HERE, so the map and the audio have to be copied together
  # or not at all - a map whose files are missing plays silence and logs nothing.
  if [ -f "build/tree/vomap_$loc.json" ]; then
    mkdir -p "$L/vo"
    cp "build/tree/vomap_$loc.json" "$L/vo/ash_cache_vo.json"
    cp vo/$loc/*.wem "$L/vo/"
  fi
  # Lipsync, copied together with its animsets for the same reason: the map's
  # animSets name each .anims by the depot path it lands at HERE, and a lipmap
  # whose animsets are missing merges cleanly and moves no mouth. The map sits
  # BESIDE the lipsync/ directory, not in it - that is Kidnap's layout
  # (mod\kidnap\localization\en-us\lipsync.lipmap + .../lipsync/johnny.anims)
  # and gen_lipmap.py writes exactly those two paths.
  if [ -f "build/tree/lipmap_$loc.lipmap" ]; then
    mkdir -p "$L/lipsync"
    cp "build/tree/lipmap_$loc.lipmap" "$L/lipsync.lipmap"
    cp lipsync/$loc/*.anims "$L/lipsync/"
  fi
done
# The phase is BUILT under one stable name and PACKED under a revisioned one.
# The depot path is what ArchiveXL hashes into the phase node id, and the node id
# is what decides whether a save that already ran this phase will run it again -
# so the revision has to reach the archive, not just the manifest. gen_xl.py owns
# the name; asking it here keeps the two spellings from drifting apart.
python3 -c 'import sys; sys.path.insert(0, "tools"); import gen_xl
for built, graph in gen_xl.PHASES:
    print(built, gen_xl.phase_resource_name(gen_xl.phase_revision(graph), built))' |
while read -r built packed; do
  [ -f "build/tree/$built" ] && cp "build/tree/$built" "$S/mod/ash_cache/quest/$packed"
done
for f in build/tree/ash_cache_*.scene; do
  [ -f "$f" ] && cp "$f" "$S/mod/ash_cache/quest/"
done
# The block's descriptors name each sector by depot path, so these two must land
# under the same mod\ash_cache\worlds directory gen_sector.py wrote into them.
[ -f build/tree/ash_cache.streamingblock ] && cp build/tree/ash_cache.streamingblock "$S/mod/ash_cache/worlds/"
# Art the build does not generate: meshes, textures and the two case .ent made by
# tools/ash_case/ from the Trellis2 model (see its README). Already CR2W, so they
# go in as they are; the depot path is the folder layout under assets/.
if [ -d assets/mod ]; then
  cp -r assets/mod/. "$S/mod/"
  echo "  + $(find assets/mod -type f | wc -l) prebuilt asset(s) from assets/mod"
fi
for f in build/tree/ash_cache_*.streamingsector; do
  [ -f "$f" ] && cp "$f" "$S/mod/ash_cache/worlds/"
done

echo "== 6. pack"
mkdir -p mod/archive/pc/mod
eval $WK pack "$S" -o build 2>&1 | grep -E "Success|Error" || true
mv build/staging.archive mod/archive/pc/mod/ashcache.archive

echo "== 7. deploy loose files"
mkdir -p mod/r6/tweaks mod/r6/scripts/AshCache
cp build/tweaks/ash_cache.yaml mod/r6/tweaks/ash_cache.yaml
cp build/scripts/AshCacheGlue.reds mod/r6/scripts/AshCache/AshCacheGlue.reds
cp build/scripts/AshCacheChipData.reds mod/r6/scripts/AshCache/AshCacheChipData.reds
cp build/scripts/AshCacheChipTree.reds mod/r6/scripts/AshCache/AshCacheChipTree.reds
cp build/scripts/AshCacheIdle.reds mod/r6/scripts/AshCache/AshCacheIdle.reds
cp build/scripts/AshCacheTrophy.reds mod/r6/scripts/AshCache/AshCacheTrophy.reds
# The Audioware bank is a DIRECTORY of loose files, not one file - the manifest
# names its .wav files by bare filename, so the two only mean anything together.
# Removed first: a line deleted from source/ has to lose its recording here too,
# and a stale .wav in an Audioware folder is a file the mod ships and nothing
# plays.
rm -rf mod/r6/audioware/ash_cache
if [ -d build/audioware ]; then
  mkdir -p mod/r6/audioware/ash_cache
  cp build/audioware/* mod/r6/audioware/ash_cache/
fi
# dev/ is not part of the mod. It lands outside mod/ on purpose, so that whatever
# deploys mod/ to the game cannot pick it up by accident.
mkdir -p dev/cet/ash_cache_debug
cp build/cet/init.lua dev/cet/ash_cache_debug/init.lua

echo "== 8. archivexl manifest"
python3 tools/gen_xl.py

echo
echo "== contents of the built archive:"
eval $WK archive -l mod/archive/pc/mod/ashcache.archive 2>/dev/null
echo
ls -la mod/archive/pc/mod/
echo
echo "== loose files (deploy to the game's r6/, NOT into the archive):"
ls -la mod/r6/tweaks/ mod/r6/scripts/AshCache/
if [ -d mod/r6/audioware/ash_cache ]; then
  echo "   r6/audioware/ash_cache/: $(ls mod/r6/audioware/ash_cache | wc -l) file(s), $(du -sh mod/r6/audioware/ash_cache | cut -f1)"
fi
echo
echo "== dev only, NOT shipped (copy to bin/x64/plugins/cyber_engine_tweaks/mods/):"
ls -la dev/cet/ash_cache_debug/
