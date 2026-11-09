#!/bin/bash
# Concept sheet -> game prop (.mesh + 4 xbm) in the quest's assets/ tree.
#   build_prop.sh <config.json>      (config: see prep_sheet.py; plus "flat", "bevel")
set -eo pipefail
cd "$(dirname "$0")"
CFG=$(realpath "$1")
D=$(dirname "$CFG")/game
PY=../venv/bin/python
read -r N FLAT BEVEL < <($PY -c "import json;c=json.load(open('$CFG'));print(c['name'],'flat' if c.get('flat') else '-',c.get('bevel',0.004))")
T=/mnt/sata/Cyberpunk2077/ash-cache-quest/research/case_ex/json/q003__splinter_d01.xbm.json
DST=/mnt/sata/Cyberpunk2077/ash-cache-quest/assets/mod/ash_cache/props/$N
rm -rf "$D" && mkdir -p "$D/cooked/textures"
$PY prep_sheet.py "$CFG" "$D"
blender -b -P bl_hull.py -- "$D" $FLAT $BEVEL 2>&1 | grep -E "^HULL|Traceback|Error:"
for k in d01:color n01:normal r01:linear m01:linear; do
  $PY ../mkxbm.py "$D/${N}_${k%:*}.png" $T "$D/cooked/textures/${N}_${k%:*}.xbm.json" ${k#*:} >/dev/null
done
n=$(DOTNET_ROLL_FORWARD=LatestMajor dotnet /mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll \
  convert deserialize "$D"/cooked/textures/*.xbm.json -o "$D/cooked/textures" 2>&1 | grep -cE "Success.*Converted" || true)
[ "$n" = 4 ] || { echo "xbm: only $n/4 converted"; exit 1; }
rm "$D"/cooked/textures/*.json
python3 ../mkmesh.py "$D" "$D/cooked" "$N:$N:$N" "mod\\ash_cache\\props\\$N"
rm -rf "$DST" && mkdir -p "$DST/textures"
cp "$D/cooked/$N.mesh" "$DST/"
cp "$D"/cooked/textures/*.xbm "$DST/textures/"
echo "  installed $(find "$DST" -type f | wc -l) files, $(du -sh "$DST" | cut -f1)"
