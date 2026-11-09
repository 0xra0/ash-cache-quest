# Conditions on a dialogue choice option

Settled 2026-09-03 against the game's own scenes, after OI-14 had recorded for a
month that this construct has no evidence. It had none because only mods and a
handful of vanilla scenes had been looked at.

## What was actually measured

Every `.scene` in `basegame_4_gamedata.archive` was extracted (7,067 files,
820 MB, regex `.*\.scene$`) and the raw bytes searched for property names. CR2W
omits a property that still holds its default, and a null `CHandle` is the
default - so the *name* of a condition field lands in a file's name table only
when some option actually sets it.

**Search for the name with a null on both sides.** `\x00questCondition\x00`, not
`questCondition`. This is not a detail; see "How to get this measurement wrong"
below, where it is the difference between 1,177 and 2,648.

    name                anchored   real   substring
    questCondition          1177   1177        2648   <- OI-14 said always null
    bluelineCondition        764    764         764
    triggerCondition          65     65          65
    gameplayAction            46     46         257
    emphasisCondition          0      0           0
    iconCondition              0      0           0
    timedCondition             0      0           0

`anchored` is the null-delimited search; `substring` is the naive one; `real` is
what deserialization found. The anchored column was checked against the real one
on a random sample of 25 scenes drawn from the 1,177 (seed 14): **24 of 24 that
deserialized carried at least one genuinely non-null `questCondition`.** No false
positives. Those 24 scenes held 461 choice options, 134 of which (29%) are gated.

So three of the six slots are genuinely unused by the game, and `questCondition`
gates an option in **1,177 scenes, 17% of all of them**.

## How to get this measurement wrong

Three ways, all of them hit while making this table:

  1. **A class name that contains the property name.** `questCondition` is a
     substring of `questConditionNodeDefinition`, the graph node class, and
     scenes embed quest graphs - so 1,471 extra scenes match a naive search
     while setting no option condition at all. Likewise `gameplayAction` inside
     `gameplayActionData`: 46 real, 257 naive. Null-anchoring both ends fixes
     this.
  2. **A CName *value* that happens to equal a property name.** Anchoring does
     not save you here, because the name table interns values and property names
     together. Measured in `.questphase`: 12 files contain `\x00optional\x00`,
     but only 4 set the property - one of the others has a quest socket
     literally named `optional`. Any name short and English enough to be a
     plausible identifier needs deserialization to confirm.
  3. **Class names are decorated, so searching for a bare one finds nothing.**
     They are stored as `handle:X` and `array:handle:X`. `\x00scnChoiceNodeOption\x00`
     matches **0** scenes; the naive search matches 2,711. Here the naive number
     is the right one.

**The control that makes the conclusion safe** regardless of the counting:
`emphasisCondition`, `iconCondition` and `timedCondition` are zero in *both*
columns, and they are siblings of `questCondition` on the very same class. If
name tables listed every property of every class present, those would match
wherever `questCondition` does. They do not. So a name-table hit means the
property was *written*, never merely that its class appears.

## The shape, from vanilla

`base/quest/tertiary_characters/default_dialogues/royce_default.scene`, the
smallest example, gates one option of a two-option hub:

    scnChoiceNodeOption.questCondition ->
      questFactsDBCondition
        type -> questVarComparison_ConditionType
                  comparisonType  Greater
                  factName        q101_done
                  value           0

That is **exactly** what `gen_questphase.build_condition` already emits for
`{"fact": "x", "compare": "Greater", "value": 0}`, which is why `gen_scene.py`
imports that function instead of growing a second one. The other condition
classes seen in option slots are the same family the graph uses, so the whole DSL
transfers. Counted over the 134 gated options in the verification sample:

    questFactsDBCondition     90    a fact comparison - what this project emits
    questTriggerCondition     14    player inside a trigger area
    questLogicalCondition     13    AND/OR over other conditions
    questStatsCondition       11    an attribute or skill threshold
    questCharacterCondition    5
    questPaymentCondition      1

`questStatsCondition` is the interesting one: it is how a dialogue option that
needs Body 12 knows it needs Body 12. That is a *different* mechanism from the
attribute check that renders greyed with a red icon, which arrives through
`gameplayAction` (see below) — so the game has both, and picks per option whether
a failed requirement hides the line or shows it as failed.

Usable today: put `"condition": {...}` on an option in `source/scene_*.json`.

## It hides the option. It does not grey it out.

This is the half of OI-14 that stays open, and it is worth being precise about
because the two behaviours look the same in a file and completely different in
game.

**The greyed-out state is real and the dialogue hub renders it.** The flags live
in `gameinteractionsChoiceTypeWrapper.properties`, a `CUInt32` bitfield:

    QuestImportant 1   AlreadyRead 2   Inactive 4    CheckSuccess 8
    CheckFailed 16     InnerDialog 32  PossessedDialog 64  TimedDialog 128
    Blueline 256       Pay 512         Selected 1024 Illegal 2048  Glowline 4096

and `DialogHubLogicController` (vanilla_scripts.reds:400227) dims a list item on
`Inactive || CheckFailed`; `interactionItemLogicController`:392669 does the same
for world interactions.

**But no author ever writes those bits.** Across 447 options in a 40-scene
sample, `type.properties` takes exactly four values:

    0    88     nothing
    1   340     QuestImportant
    256   4     Blueline
    257  15     both

Never 4, never 8, never 16. `Inactive` and `CheckFailed` are set at runtime -
`CheckFailed` by the attribute-check system, which enters through
`gameplayAction` (a TweakDBID naming a check record) rather than through any
condition slot.

**And the file format carries a tell that conditions remove options.**
`scnChoiceNode.choiceFlags` has a bit called `IsValidInteractionFailsafeDisabled`.
360 scenes set it, and 343 of those - 95% - also carry a `questCondition`. A
failsafe for "no interaction is valid" is only worth disabling if filtering can
empty the hub, which only happens if a failed condition takes the option away.

So: to gate an option, use `questCondition`. To show an option the player can see
they did not earn, there is still no authored route, and D14's two-entry-point
workaround remains the only proven way to vary a hub's contents.

## Re-extracting

    A="/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc/content/basegame_4_gamedata.archive"
    dotnet .../WolvenKit.CLI.dll unbundle "$A" -o <outdir> -r ".*\.scene$"      # 820 MB
    grep -rlaF questCondition --include='*.scene' <outdir> | wc -l

Serialise a folder rather than a file at a time - the CLI pays its startup once,
so 40 scenes cost 13 s against 5.6 s each. Read-only on the game install (rule 2).
