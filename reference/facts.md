# Vanilla facts this mod depends on

Facts are the engine's global int store, keyed by bare CName. There is no registry
and no schema: a misspelt fact name reads 0 forever and nothing anywhere reports
it. So every vanilla fact this mod reads gets its provenance written down here
before it is used (rule 8).

`tools/validate.py` cannot check these the way it checks TweakDB ids against
`tweakdbstr.txt` (D11), because no equivalent dump of fact names exists — facts
live inside `.questphase` and `.quest` resources, not in a table. The check is
therefore manual and one-off, and this file is the record of having done it.

## `q304_done` — Somewhat Damaged is finished

Used by `source/glue.json` as the prerequisite for `ashcache_start`. Phantom
Liberty's Q304 is where V goes into the Cynosure facility and is scanned, and
that scan is the thing this quest is about, so the story cannot start before it.

**Two independent confirmations.**

1. The game reads it. Extracted from `ep1_2_gamedata.archive`:

       ep1/quest/minor_quests/mq304/mq304.questphase

   contains a `questPauseConditionNodeDefinition` holding

       questFactsDBCondition
         questVarComparison_ConditionType
           comparisonType: "Greater"
           factName:       "q304_done"
           value:          0

   That is vanilla gating its own Somewhat Damaged follow-up minor quest on the
   fact, waiting on it exactly the way `await_start` waits on `ashcache_start`.
   The same file *sets* a different fact, `mq304_done`, via `questSetVar_NodeType`
   — which is how a read and a write are told apart in these files.

2. An installed mod gates on it. `r6/scripts/DisclosedHiddenGems/Globals/CreateGems.reds`
   uses `FactRequisite.Initialize(gem293, n"q304_done", EComparisonType.Equal, 1)`.

Neither on its own would be enough: (1) proves the name exists and means what the
label says, (2) proves a third party reached the same conclusion independently.

Rejected alternatives, for the record:

| fact | why not |
|---|---|
| `ep1_side_content` | Fires when Dogtown side content unlocks, long before Cynosure. V has not been scanned yet, so the premise of the quest is not true. |
| `q304_lab_done` | Fires inside the mission, in the lab. Correct in fiction, wrong in practice — the SMS would arrive mid-mission. |
| `q306_postcontent` | Fires after the whole Phantom Liberty ending. Correct but far too late; it would strand the quest behind the epilogue. |

## Re-checking one of these

    A="/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc/ep1/ep1_2_gamedata.archive"
    dotnet .../WolvenKit.CLI.dll unbundle "$A" -o <outdir> -r ".*q304.*\.questphase"
    find <outdir> -name '*.questphase' -exec strings -a {} \; | grep -E '^q304_[a-z0-9_]+$' | sort -u

Then serialise the one file that mentions it and look at whether the fact sits
under a `questSetVar_NodeType` (written) or a `questVarComparison_ConditionType`
(read). Basegame facts are in `content/basegame_4_gamedata.archive` instead.
