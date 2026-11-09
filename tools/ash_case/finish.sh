#!/bin/bash
# Textured Trellis2 glb -> finished ash case assets in the quest's assets/ tree.
#   finish.sh <textured.glb>
set -e
cd /mnt/sata/ComfyUI/_ashcase  # venv and working files live there
SRC=$(realpath "$1")
G=$PWD/game_final
DST=/mnt/sata/Cyberpunk2077/ash-cache-quest/assets/mod/ash_cache/props/ash_case
T=/mnt/sata/Cyberpunk2077/ash-cache-quest/research/case_ex/json/q003__splinter_d01.xbm.json
rm -rf "$G" && mkdir -p "$G/cooked/textures"
echo "== blender: low poly, bake, cut"
blender -b -P bl_game.py -- "$SRC" "$G" bake 2>&1 | grep -E "^\[case\]|Traceback|Error:"
echo "== fill atlas background (mips average islands with black otherwise)"
venv/bin/python /mnt/sata/Cyberpunk2077/ash-cache-quest/tools/ash_case/dilate.py "$G"
echo "== interior textures (flat dark foam)"
venv/bin/python - "$G" <<'P'
import sys; from PIL import Image
g = sys.argv[1]
for k, c in (("d01", (22, 22, 24)), ("r01", (217, 217, 217)), ("m01", (0, 0, 0)), ("n01", (128, 128, 255))):
    Image.new("RGB", (64, 64), c).save(f"{g}/ash_case_interior_{k}.png")
P
echo "== xbm"
for p in ash_case ash_case_interior; do
  venv/bin/python mkxbm.py "$G/${p}_d01.png" $T "$G/cooked/textures/${p}_d01.xbm.json" color
  venv/bin/python mkxbm.py "$G/${p}_n01.png" $T "$G/cooked/textures/${p}_n01.xbm.json" normal
  venv/bin/python mkxbm.py "$G/${p}_r01.png" $T "$G/cooked/textures/${p}_r01.xbm.json" linear
  venv/bin/python mkxbm.py "$G/${p}_m01.png" $T "$G/cooked/textures/${p}_m01.xbm.json" linear
done
DOTNET_ROLL_FORWARD=LatestMajor dotnet /mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll \
  convert deserialize "$G"/cooked/textures/*.xbm.json -o "$G/cooked/textures" 2>&1 | grep -cE "Success.*Converted" | sed 's/^/  xbm converted: /'
rm "$G"/cooked/textures/*.json
echo "== meshes"
python3 mkmesh.py "$G" "$G/cooked"
echo "== entities"
python3 gen_case_ent.py "$G/case_dims.json" "$G/cooked"
rm -f "$G"/cooked/*.json
echo "== install into the quest's assets/"
rm -rf "$DST" && mkdir -p "$DST/textures"
cp "$G"/cooked/*.mesh "$G"/cooked/*.ent "$DST/" && cp "$G"/cooked/textures/*.xbm "$DST/textures/"
find "$DST" -type f -printf "  %P  %s\n"
echo "== preview"
blender -b -P bl_prev.py -- "$G" tex >/dev/null 2>&1
