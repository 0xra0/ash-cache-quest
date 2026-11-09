#!/usr/bin/env python3
"""Regenerate tools/enums.py from WolvenKit's cp77enums.cs.

WolvenKit's own failure mode for a bad enum value is a bare CEnum.Parse stack
that names neither the field nor the value, so every enum the generators write
is checked here first. Add a name to WANTED and re-run.
"""
import pathlib
import re

SRC = pathlib.Path("/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.RED4/Types/Enums/cp77enums.cs")
OUT = pathlib.Path(__file__).resolve().parent / "enums.py"

WANTED = [
    "gamedataMappinVariant",       # journal map pins
    "gameJournalQuestType",        # quest record
    "gameJournalEntryState",       # journal-state conditions
    "EComparisonType",             # fact comparisons
    "questLogicalOperation",       # AND / OR in questLogicalCondition
    "questExitType",               # questOutputNodeDefinition.type
    "questJournalQuestEntry_NodeTypeNodeVersion", "scnSceneCategoryTag",
    "questObjectInteractionEventType",   # questInteraction_ConditionType.eventType
    "populationSpawnerObjectCtrlAction",  # questSpawnManagerNodeType.action
    "gameContactType",
    "GameplayTier",                # questSetTier_NodeType.tier
    "gameGodModeType",             # questCharacterManagerParameters_SetMortality.state
    "questInjectLootOperationType",  # questInjectLoot_NodeTypeParams_OperationData
    # D124, the holocall. The first three are questCallContact_NodeType's own
    # fields; the fourth is how a scene acquires somebody who is on the phone
    # rather than in the room - scnFindEntityInContextParams.contextualName.
    "questPhoneCallPhase", "questPhoneCallMode", "questPhoneCallVisuals",
    "scnContextualActorName",
]


def main():
    text = SRC.read_text(encoding="utf-8", errors="replace")
    out = ['"""Valid RED4 enum values, extracted from '
           'WolvenKit.RED4/Types/Enums/cp77enums.cs.',
           "Regenerate with tools/refresh_enums.py if WolvenKit is updated.",
           '"""', ""]
    missing = []
    for name in WANTED:
        m = re.search(r"enum\s+%s\s*(?::\s*\w+\s*)?\{(.*?)\}" % re.escape(name),
                      text, re.S)
        if not m:
            missing.append(name)
            continue
        vals = sorted({v for v in re.findall(r"^\s*([A-Za-z_]\w*)\s*=", m.group(1), re.M)})
        out.append(f"{name} = {vals!r}")
        out.append("")
        print(f"  {name}: {len(vals)} values")
    if missing:
        raise SystemExit("not found in cp77enums.cs: " + ", ".join(missing))
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
