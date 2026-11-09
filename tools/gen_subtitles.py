#!/usr/bin/env python3
"""source/scene_*.json + subtitle_ids.json  ->  build/subtitles*_<locale>.json.json

Spoken scene text does not go through LocKeys. The engine resolves a line by the
locstring ruid stored in the .scene, through TWO resources per locale:

    .xl  localization.subtitles.<locale>
      -> localizationPersistenceSubtitleMap      (group "quest")
      -> localizationPersistenceSubtitleEntries  (stringId -> male/female text)

Both hops are required; the map is not optional indirection. Verified against
Undermine Quest Series, which ships exactly this pair for five locales.

Each entry carries a male and a female variant, selected by the player's brain
gender. Where a line reads the same either way both variants get the same text -
unlike onscreens, an empty maleVariant here is not known to fall back, and the
one shipping reference always fills both.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import H, envelope

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCALES = ["en-us", "ua-ua"]

# Where the pair lands inside the archive. The map points at the entries file by
# depot path, so this layout is baked into the emitted resource, not just the tree.
RES = "mod\\ash_cache\\localization"
MAP_NAME = "ash_cache.json"
ENTRIES_NAME = "ash_cache_lines.json"


def spoken(scene):
    """Every subtitle-bearing item in one scene, in file order."""
    for node in scene.get("nodes", []):
        for item in node.get("lines", []) + node.get("options", []):
            yield item


def main():
    alloc = json.loads((ROOT / "source" / "subtitle_ids.json").read_text(encoding="utf-8"))
    alloc.pop("_comment", None)

    items = {}
    for path in sorted((ROOT / "source").glob("scene_*.json")):
        stem = path.stem[len("scene_"):]
        for item in spoken(json.loads(path.read_text(encoding="utf-8"))):
            items[f"{stem}.{item['id']}"] = item

    outdir = ROOT / "build"
    outdir.mkdir(parents=True, exist_ok=True)

    for locale in LOCALES:
        entries, missing = [], []
        for key, ruid in sorted(alloc.items(), key=lambda kv: int(kv[1])):
            item = items.get(key)
            if item is None:
                # Allocated but no longer spoken. Skipping keeps the number
                # reserved (alloc is append-only) without shipping dead text.
                continue
            text = item.get(locale)
            if not text:
                missing.append(key)
                text = item.get("en-us", "")
            entries.append({
                "$type": "localizationPersistenceSubtitleEntry",
                "femaleVariant": text,
                "maleVariant": item.get(f"{locale}_m", text),
                "stringId": str(ruid),
            })

        lines_root = {
            "$type": "JsonResource", "cookingPlatform": "PLATFORM_PC",
            "root": H({"$type": "localizationPersistenceSubtitleEntries",
                       "entries": entries}),
        }
        out = outdir / f"subtitlelines_{locale}.json.json"
        out.write_text(json.dumps(envelope(lines_root, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")

        map_root = {
            "$type": "JsonResource", "cookingPlatform": "PLATFORM_PC",
            "root": H({
                "$type": "localizationPersistenceSubtitleMap",
                "entries": [{
                    "$type": "localizationPersistenceSubtitleMapEntry",
                    "subtitleFile": {
                        "DepotPath": {"$type": "ResourcePath", "$storage": "string",
                                      "$value": f"{RES}\\{locale}\\subtitles\\{ENTRIES_NAME}"},
                        "Flags": "Default"},
                    "subtitleGroup": {"$type": "CName", "$storage": "string",
                                      "$value": "quest"},
                }],
            }),
        }
        outm = outdir / f"subtitlemap_{locale}.json.json"
        outm.write_text(json.dumps(envelope(map_root, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")

        flag = f"  MISSING/fell back: {missing}" if missing else ""
        print(f"wrote {out.relative_to(ROOT)} + map  ({len(entries)} subtitle lines){flag}")


if __name__ == "__main__":
    main()
