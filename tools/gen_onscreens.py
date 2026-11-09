#!/usr/bin/env python3
"""source/strings.json + lockeys.json  ->  build/onscreens_<locale>.json.json

Onscreens are what actually turn a LocKey number into visible text. Without a
matching entry, the game renders the string as blank - which is exactly the
'blank quest UI' failure mode that hits locales a mod forgets to declare.

One resource per locale. maleVariant is left empty; the game falls back to
femaleVariant, which is how the reference mods ship.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import H, envelope

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCALES = ["en-us", "ua-ua"]


def main():
    strings = json.loads((ROOT / "source" / "strings.json").read_text(encoding="utf-8"))
    lockeys = {k: v for k, v in
               json.loads((ROOT / "source" / "lockeys.json").read_text(encoding="utf-8")).items()
               if not k.startswith("_")}

    outdir = ROOT / "build"
    outdir.mkdir(parents=True, exist_ok=True)

    for locale in LOCALES:
        entries = []
        missing = []
        for sid, num in sorted(lockeys.items(), key=lambda kv: kv[1]):
            spec = strings.get(sid)
            if spec is None:
                missing.append(sid)
                continue
            text = spec.get(locale)
            if not text:
                missing.append(sid)
                # Fall back to en-us rather than emitting an empty string, which
                # would render as a blank line in the quest UI.
                text = spec.get("en-us", "")
            entries.append({
                "$type": "localizationPersistenceOnScreenEntry",
                "femaleVariant": text,
                "maleVariant": "",
                "primaryKey": str(num),
                "secondaryKey": spec.get("note", sid),
            })

        root = {
            "$type": "JsonResource",
            "cookingPlatform": "PLATFORM_PC",
            "root": H({
                "$type": "localizationPersistenceOnScreenEntries",
                "entries": entries,
            }),
        }
        out = outdir / f"onscreens_{locale}.json.json"
        out.write_text(json.dumps(envelope(root, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        flag = f"  MISSING/fell back: {missing}" if missing else ""
        print(f"wrote {out.relative_to(ROOT)}  ({len(entries)} entries){flag}")


if __name__ == "__main__":
    main()
