# Scene interruption: what the engine offers and what vanilla actually uses

Measured 2026-09-03 over **all 2,860 `.questphase` files the game ships**
(`base` + `ep1`, every content archive), plus the RED4ext.SDK generated headers
for the field lists. Method and controls at the bottom.

## The short version

A scene interruption **pauses and resumes a conversation. It never ends one.**
There is no engine mechanism that abandons a dialogue because the player walked
away, and vanilla does not simulate one. An NPC left mid-sentence stays
mid-sentence until the player comes back — in this game that is correct
behaviour, not a bug.

## Where the pieces live

An interruption scenario is authored **inside the `.scene`**, as
`scnInterruptionScenario` on the scene resource:

    interruptConditions   [] of scnI...InterruptCondition
    returnConditions      [] of scnI...ReturnCondition
    postInterruptSignalFactCondition   handle scnInterruptFactConditionType
    postReturnSignalFactCondition      handle scnInterruptFactConditionType
    postInterruptSignalTimeDelay       float
    postReturnSignalTimeDelay          float
    playingLinesBehavior               Default | Vehicle | Holocall
    enabled, talkOnReturn, playInterruptLine, forcePlayReturnLine,
    interruptionSpammingSafeguard      bool
    id                                 scnInterruptionScenarioId
    name, queueName                    CName

The **quest** node that plays that scene can then override it, without touching
the `.scene`. `questSceneNodeDefinition.interruptionOperations` is an array of
`scnIInterruptionOperation`, and there are exactly two implementations:

| operation | what it does |
|---|---|
| `scnToggleInterruption_InterruptionOperation` | `enable: bool` — turn interruption on or off for this play |
| `scnOverrideInterruptionScenario_InterruptionOperation` | `scenarioId` + `scenarioOperations[]`, which are `scnOverrideInterruptConditions_...` and `scnOverrideReturnConditions_...` |

Counted across the 2,860 phases: **203 files toggle**, **128 files override**.
A complete override is in `examples/scene_interruption_override.json` — V's
first visit to Viktor Vector, which replaces the scene's speaker-distance test
with a player-to-Vic distance of Greater 17 / return Less 16.

## The interrupt and return conditions

Every implementation in the RTTI, with the file count that authors it:

| condition | files | params |
|---|---|---|
| `scnCheckSpeakersDistanceInterruptCondition` | 61 | `comparisonType`, `distance` |
| `scnCheckPlayerTargetEntityDistanceInterruptCondition` | 11 | `distance`, `targetEntity` (gameEntityReference), `comparisonType` |
| `scnCheckFactInterruptCondition` | 8 | `factCondition` → `scnVarComparison_FactConditionType` |
| `scnCheckTriggerInterruptCondition` | 7 | `inside: bool`, `triggerArea: NodeRef` |
| `scnCheckPlayerCombatInterruptCondition` | 5 | `isInCombat: bool` |
| `scnCheckPlayerTargetNodeDistanceInterruptCondition` | 4 | `distance`, `targetNode: NodeRef`, `comparisonType` |
| `scnCheckAnyoneDistractedInterruptCondition` | — | no params |
| `scnCheckSpeakerDistractedInterruptCondition` | — | no params |
| `scnCheckSpeakerOrAddressDistractedInterruptCondition` | — | no params |
| `scnCheckMountedVehicleImpactInterruptCondition` | — | no params |

Return conditions mirror the ones that have a return form, plus
`scnDummyAlwaysTrueReturnCondition`.

### Distances vanilla actually ships

From the 128 override-authoring phases, every distance literal:

    interrupt  Greater  6   20 uses     return  Less  5   39 uses
    interrupt  Greater 10   29 uses     return  Less  8   16 uses
    interrupt  Greater 15   16 uses     return  Less  3    5 uses
    interrupt  Greater 20   12 uses     return  Less  4    5 uses
    interrupt  Greater  8   11 uses     return  Less 10    4 uses
    ... a long tail out to Greater 70

`Greater 6` / `Less 5` — the pair this project inherited from the Undermine
template — is the **second most common interrupt distance and the most common
return distance in the game**. It is not a guess that happened to survive; it is
the vanilla mode. The hysteresis gap (interrupt at 6, return at 5) is universal:
no scene in the sample uses the same number for both.

## The quest graph's side: `<scenario> INT` and `<scenario> RET`

A `questSceneNodeDefinition` grows one output socket pair per interruption
scenario the scene declares, named after the scenario:

    Default INT     Default RET
    Holocall INT    Holocall RET

They exist on every scene node whether or not anything is wired to them. This
project's generator already emits `Default INT` / `Default RET`
(`tools/gen_questphase.py`, `outputs_of`).

**How often are they wired?** Of 213 scene nodes in the 128 interruption-aware
phases, **15 INT and 15 RET connections in 13 files** — about 7%. Every single
one does the same thing:

    scene node --Default INT--> questPauseConditionNodeDefinition
                                  questTimeCondition
                                    questRealtimeDelay_ConditionType 500 ms
                                --Out--> questSceneManagerNodeDefinition
                                           questSetTier_NodeType
                                             tier: Tier1_FullGameplay

and the RET path is the identical four nodes. Worked example:
`q112_00c_wakako.questphase`, scene node 22 (Wakako Okada), nodes 126–129. The
other twelve files are holocalls and do the same with the `Holocall` scenario.

So the INT output is **a tier safety net, not an exit**: it makes sure a player
interrupted out of a constrained-movement conversation is handed back full
gameplay control after half a second. Nothing in the game routes INT to a
cleanup, a despawn, or a cut.

**Consequence for this project.** `tools/gen_scene.py` never changes tier — the
Mara and decision scenes run at `Tier1_FullGameplay` throughout — so the vanilla
safety net would be a no-op here and is deliberately not built. *If anyone adds
a tier change to a scene, they must wire `Default INT` and `Default RET` to the
four-node pattern above at the same time*, or an interrupted player can be left
unable to move.

## Two dead classes

`questSceneInterrupt_ConditionType` and `questSceneReturn_ConditionType` exist
in the RTTI, take a `sceneFile` plus their own `interruptConditions` /
`returnConditions` arrays, and look exactly like the way a quest graph would
wait on "this scene got interrupted". **Neither is authored once in 2,860
files.** Do not reach for them; the wired INT/RET sockets are the supported
route.

Live siblings of the same base, for contrast: `questSceneNode_ConditionType`
(127 files; `SceneConditionType` = Undefined/IsInside/IsOutside/Entered/Exited
against an `ActorName`) and `questSceneTalking_ConditionType` (7 files).

## Method

    unbundle .*\.questphase from all 32 content archives    -> 2,860 files
    anchored name-table scan: b"\x00" + name + b"\x00"
    also counted handle: and array:handle: decorations       -> all zero here
    128 files carrying an override or a player-distance condition
      were deserialised with WolvenKit.CLI and read field by field

Per D27 the scan shipped negative controls — `questMultiplayerAIDirectorNodeDefinition`,
`questMultiplayerTeleportPuppetNodeDefinition`,
`questMultiplayerChoiceTokenNodeDefinition`, all real RTTI classes from the cut
multiplayer mode. All three returned **0**, so a non-zero count means the class
was authored, not merely resolvable.

## The trap this file predicted is now live   (2026-09-04, D29)

When this was written, `gen_scene.py` never changed tier, so the safety net was a
no-op and the note was a warning for later. Later arrived in the same week: both
`ash_cache_mara.scene` and `ash_cache_decision.scene` now raise the tier to
`Tier3_LimitedGameplay` with `forceEmptyHands`, so a player interrupted out of
either one would have been left unable to move with no error anywhere.

Both are wired, each with the four-node shape measured above:

    meet_mara  --Default INT--> mara_int_wait (500 ms) --> mara_int_tier (Tier1)
    meet_mara  --Default RET--> mara_ret_wait (500 ms) --> mara_ret_tier (Tier1)

and the same for `decide_scene`. `gen_questphase.py` grew a `delay` condition to
emit `questRealtimeDelay_ConditionType` - the field really is spelled
**`miliseconds`**, one L, which is the engine's name and not a typo to correct.

It is no longer possible to forget. `validate.py:check_scene_tier` fails the
build when a scene raises the tier without restoring `Tier1_FullGameplay` inside
itself, or when the graph node that plays it leaves either socket unwired. Three
cases in `negtest.py` hold it.
