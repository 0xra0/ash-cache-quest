#!/usr/bin/env python3
"""docs/cynosure_import/ (the Cynosure planning bundle) -> source/cynosure_contract.json.

M0 data contract: every canonical ID, phase and fact the bundle defines, in one
file validate.py can check. The bundle's Markdown stays the human source; rerun
this after it changes. Its transform registry is copied as-is to
source/cynosure_transforms.json.

Fact names: the bundle writes ash_<domain>_<state>. Facts are global across all
mods, so this quest's rule is the ashcache_ prefix: ash_X becomes ashcache_X,
except where ALIASES reuses a fact the quest already has.

    cyn_import.py
"""
import hashlib, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "cynosure_import"
PROPS = "assets/mod/ash_cache/props"

# The bundle's enum value blocks, in document order -> the fact each one defines.
ENUM_BLOCKS = ["ash_cyn_phase", "ash_world_power_stage", "ash_security_resolution", "ash_mara_trust",
               "ash_deviation_class", "ash_ending_id", "ash_dialogue_busy"]
# Bundle name -> an existing facts.json fact that already means the same thing.
ALIASES = {"ash_ending_destroy": "ashcache_end_destroy", "ash_ending_absorb": "ashcache_end_absorb",
           "ash_ending_blueeyes": "ashcache_end_blueeyes", "ash_ending_hide": "ashcache_end_hide"}
# Sections whose names are not facts to create.
FORBIDDEN_SECTION = "Do not encode protected mysteries as truth"
EXTERNAL_SECTION = "Existing Echo facts"
PROTECTED_SECTION = "Protected story facts"
REFERENCE_ONLY = {"Minimum completion chain", "Invariants", "Repair policy", "Reconstruction inputs",
                  "Debug status", "Naming", "Validator", "Final principle", PROTECTED_SECTION}
# Bundle concepts the existing quest already stores differently. The quest's facts stay
# authoritative: an alias IS an existing fact, a derived value is computed from existing
# facts and never persisted. Neither creates an ashcache_ fact.
MAPPED = {
    "ash_splinter_acquired": {"alias": "ashcache_splinter_given"},
    **{f"ash_echo_0{i}": {"alias": f"ashcache_chip_frag_{i}"} for i in range(1, 7)},
    "ash_echo_count": {"derived": "sum(chip_frag_1..6)",
                       "inputs": [f"ashcache_chip_frag_{i}" for i in range(1, 7)]},
    "ash_mara_alive": {"derived": "ashcache_mara_dead == 0", "inputs": ["ashcache_mara_dead"]},
    "ash_mara_trust": {"derived": "hostile -> 0; trusted -> 3; neither -> 2",
                       "inputs": ["ashcache_mara_hostile", "ashcache_mara_trusted"],
                       "values": {"0": "LOW", "1": "RESERVED (not produced by the quest)",
                                  "2": "MEDIUM", "3": "HIGH"},
                       "invalid": "ashcache_mara_hostile == 1 && ashcache_mara_trusted == 1"},
}
# Bundle concepts the existing quest models differently and nobody has decided yet.
OPEN = {}
# CYN_ASSET_* -> built prop dirs under PROPS (empty: not built yet, route B).
ASSETS = {
    "CYN_ASSET_SPLINTER_1140": ["splinter"], "CYN_ASSET_CRADLE_1140": ["o1140_cradle"],
    "CYN_ASSET_PERSONALITY_RACK": ["storage_rack"], "CYN_ASSET_SHUTDOWN_CONSOLE": ["shutdown_console"],
    "CYN_ASSET_ARCHIVE_SCANNER": ["archive_scanner"], "CYN_ASSET_FIA_READER": ["fia_bio_reader"],
    "CYN_ASSET_DESTROYED_CARTRIDGE": [f"cartridge_0{i}" for i in range(1, 7)],
    "CYN_ASSET_CONTINUITY_DOOR": ["continuity_vault_door"], "CYN_ASSET_EVIDENCE_CASE": ["evidence_case"],
    **{f"CYN_ASSET_ECHO_FRAGMENT_{c}": [f"echo_fragment_{c.lower()}"] for c in "ABCDEF"},
}


def sections(md):
    """(heading, [code block lines...] per block, prose) for each ## section."""
    out, head, blocks, cur = [], None, [], None
    for line in md.splitlines():
        if line.startswith("```"):
            if cur is None:
                cur = []
            else:
                blocks.append(cur)
                cur = None
        elif cur is not None:
            cur.append(line.strip())
        elif line.startswith("## "):
            if head:
                out.append((head, blocks))
            head, blocks = line[3:].strip(), []
    out.append((head, blocks))
    return out


def rename(n):
    return ALIASES.get(n, "ashcache_" + n[4:])


def main():
    facts_md = (DOCS / "CYNOSURE_FACTS.md").read_text()
    ids_md = (DOCS / "CYNOSURE_IDS.md").read_text()
    impl_md = (DOCS / "CYNOSURE_IMPLEMENTATION.md").read_text()

    facts, forbidden, external, protected, enums = {}, [], [], [], []
    for head, blocks in sections(facts_md):
        names = [l for b in blocks for l in b if re.fullmatch(r"ash_[a-z0-9_]+", l)]
        for b in blocks:
            vals = [re.fullmatch(r"(\d+)\s+(.+)", l) for l in b if l]
            if vals and all(vals):
                enums.append({m[1]: m[2] for m in vals if m})
        if head == FORBIDDEN_SECTION:
            forbidden += names
        elif head == EXTERNAL_SECTION:
            external += names
        elif head == PROTECTED_SECTION:
            protected += names
        elif head not in REFERENCE_ONLY:
            for n in names:
                facts.setdefault(n, {"section": head})
    # the global phase facts are a table, not a code block
    for n, typ, default in re.findall(r"^\| `(ash_[a-z0-9_]+)` \| (\w+) \| (\d+) \|", facts_md, re.M):
        facts.setdefault(n, {"section": "Global phase facts"}).update(type=typ, default=int(default))
    if len(enums) != len(ENUM_BLOCKS):
        raise SystemExit(f"CYNOSURE_FACTS.md has {len(enums)} enum blocks, ENUM_BLOCKS names "
                         f"{len(ENUM_BLOCKS)} - the doc changed; update ENUM_BLOCKS")
    for n, vals in zip(ENUM_BLOCKS, enums):
        facts.setdefault(n, {"section": "Runtime-only state"})["values"] = vals
    for n in protected:
        facts[n]["protected"] = True
    facts["ash_dialogue_busy"]["persistence"] = "SESSION"
    for n in MAPPED:
        facts.pop(n, None)

    ids = {}
    for head, blocks in sections(ids_md):
        got = [l.split("=")[0].strip() for b in blocks for l in b if re.fullmatch(r"CYN_[A-Z0-9_]+(\s*=\s*\d+)?", l)]
        if got and head != "Naming rule":  # its IDs are examples
            ids[head] = got
    prefixes = re.findall(r"^\| `(CYN_[A-Z]+_)` \|", ids_md, re.M)
    phase_block = next(b for h, bs in sections(impl_md) if h == "Canonical phases" for b in bs)
    phases = {m[1]: m[2] for m in (re.fullmatch(r"(\d+)\s+(\S+)", l) for l in phase_block) if m}
    if phases != facts["ash_cyn_phase"]["values"]:
        raise SystemExit("IMPLEMENTATION and FACTS disagree on the phase list")

    registered = {i for v in ids.values() for i in v}
    contract = {
        "_comment": "Generated by tools/cyn_import.py from docs/cynosure_import/ - do not edit; "
                    "change the bundle and rerun. Keys are ashcache_ names; 'doc' is the bundle's name.",
        "sources": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in sorted(DOCS.glob("*"))},
        "id_prefixes": prefixes,
        "ids": ids,
        "facts": {rename(n): {"doc": n, **v} for n, v in sorted(facts.items())},
        "external_facts": [n for n in external if n not in MAPPED],
        "mapped": MAPPED,
        "forbidden_facts": [rename(n) for n in forbidden],
        "open_questions": OPEN,
        "assets": {a: {"props": ASSETS.get(a, []), "path": PROPS} for a in ids.get("Custom assets", [])},
    }
    unknown = set(ASSETS) - set(contract["assets"])
    if unknown:
        raise SystemExit(f"ASSETS maps IDs CYNOSURE_IDS.md does not register: {sorted(unknown)}")
    (ROOT / "source" / "cynosure_contract.json").write_text(json.dumps(contract, indent=1) + "\n")
    shutil.copyfile(DOCS / "CYNOSURE_TRANSFORMS.json", ROOT / "source" / "cynosure_transforms.json")
    built = sum(bool(v["props"]) for v in contract["assets"].values())
    print(f"cynosure_contract.json: {len(registered)} ids, {len(contract['facts'])} facts "
          f"({len(ALIASES)} aliased), {len(MAPPED)} mapped, {len(forbidden)} forbidden, {len(OPEN)} open, "
          f"assets built {built}/{len(contract['assets'])}")


if __name__ == "__main__":
    main()
