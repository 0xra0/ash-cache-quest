#!/bin/bash
# sc_splinter.png sheet -> O-1140 splinter mesh + textures in the quest's assets/ tree.
#   finish_splinter.sh <sheet.png>
set -e
cd "$(dirname "$0")"
SHEET=$(realpath "$1")
PY=../venv/bin/python
G=$PWD/game
DST=/mnt/sata/Cyberpunk2077/ash-cache-quest/assets/mod/ash_cache/props/splinter
T=/mnt/sata/Cyberpunk2077/ash-cache-quest/research/case_ex/json/q003__splinter_d01.xbm.json
N=o1140_splinter
rm -rf "$G" && mkdir -p "$G/cooked/textures"
echo "== outline + atlas"
$PY prep.py "$SHEET" "$G"
echo "== blender: visual hull, uv, preview"
blender -b -P bl_splinter.py -- "$G" 2>&1 | grep -E "^SPLINTER|Traceback|Error:"
echo "== xbm"
for k in d01:color n01:normal r01:linear m01:linear; do
  $PY ../mkxbm.py "$G/${N}_${k%:*}.png" $T "$G/cooked/textures/${N}_${k%:*}.xbm.json" ${k#*:}
done
DOTNET_ROLL_FORWARD=LatestMajor dotnet /mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll \
  convert deserialize "$G"/cooked/textures/*.xbm.json -o "$G/cooked/textures" 2>&1 | grep -cE "Success.*Converted" | sed 's/^/  xbm converted: /'
rm "$G"/cooked/textures/*.json
echo "== mesh"
python3 ../mkmesh.py "$G" "$G/cooked" splinter:$N:$N 'mod\ash_cache\props\splinter'
echo "== install into the quest's assets/"
rm -rf "$DST" && mkdir -p "$DST/textures"
cp "$G/cooked/$N.mesh" "$DST/" && cp "$G"/cooked/textures/*.xbm "$DST/textures/"
find "$DST" -type f -printf "  %P  %s\n"
