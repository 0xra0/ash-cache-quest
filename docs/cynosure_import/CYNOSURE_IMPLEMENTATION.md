# CYNOSURE_IMPLEMENTATION.md

# Ash Cache — Cynosure Implementation Plan

## Purpose

This document converts the Cynosure story, room layout, quest-node graph, scene/trigger specification, and custom asset set into concrete development work.

> **Quest logic owns progression. World scripts present it. Custom assets make it visible.**

A broken animation, missing optional interaction, skipped combat encounter, alternate route, companion state, or save/load must never permanently soft-lock the quest.

## Delivery milestones

### M0 — Data Contract
Freeze canonical quest facts, ending IDs, room IDs, trigger IDs, interaction IDs, scene IDs, custom asset IDs, debug state reader/writer, dump, validator, and repair system.

### M1 — Greybox Vertical Slice
The player can enter Cynosure, traverse every mandatory room, reach the core, select any of four endings, and leave. No final custom art is required.

Mandatory areas:

```text
Surface
Entry
Checkpoint
Flooded Maintenance
Pump
Security
Biometric Gate
Observation Lab
Personality Archive
Prediction Hall
Branch Coffins
Comparison Lab
ASH Server Vault
Core Antechamber
Predictive Core
Ending Control
Escape
```

### M2 — Core Custom Assets
Integrate 0-1140 splinter, containment cradle, personality rack, branch projector, prediction counter, comparison apparatus, Predictive Core, and Continuity door.

### M3 — Environmental Systems
Integrate pump, cameras, ASH servers, observation chair, shutdown console, archive scanner, destroyed cartridges, FIA reader, lighting progression, wake sequences, and ambience.

### M4 — Narrative Complete
Add Mara/Johnny variants, Echo callbacks, prediction deviation, optional lore, second missing branch, recent visitor clue, ending callbacks, and post-quest re-entry.

### M5 — Release Candidate
Collision, navmesh, streaming, LOD/performance, audio, localization, save/load matrix, all endings/routes/Mara/Echo/deviation states, packaged build.

## Canonical rooms

```text
CYN_ROOM_00_SURFACE
CYN_ROOM_01_ENTRY
CYN_ROOM_02_CHECKPOINT
CYN_ROOM_03_FLOODED
CYN_ROOM_03A_MAINT_SIDE
CYN_ROOM_04_PUMP
CYN_ROOM_05_SECURITY
CYN_ROOM_05A_SECURITY_OFFICE
CYN_ROOM_06_BIOMETRIC
CYN_ROOM_07_OBSERVATION
CYN_ROOM_07A_SUBJECT_RECORDS
CYN_ROOM_08_ARCHIVE
CYN_ROOM_08A_PURGE_ARCHIVE
CYN_ROOM_09_PREDICTION
CYN_ROOM_09A_ECHO_ANALYSIS
CYN_ROOM_10_BRANCH_COFFINS
CYN_ROOM_11_COMPARISON
CYN_ROOM_12_SERVER_VAULT
CYN_ROOM_13_CORE_ANTE
CYN_ROOM_14_CORE
CYN_ROOM_15_ENDING_CONTROL
CYN_ROOM_16_ESCAPE
```

## Canonical phases

```text
0   NOT_STARTED
10  APPROACH
20  ENTRY
30  MAINTENANCE
40  SECURITY
50  RESEARCH
60  ARCHIVE
70  PREDICTION
80  CONTINUITY
90  CORE
100 DECISION
110 ESCAPE
120 COMPLETE
```

Stored in `ash_cyn_phase`.

## World Builder packages

### Surface / Entry
Build ruined service access, main hatch, alternate vent, signage, debris, and future surface exit.

Anchors:
`ANCHOR_CYN_SURFACE_APPROACH`, `ANCHOR_CYN_MAIN_ENTRY`, `ANCHOR_CYN_VENT_ENTRY`, `ANCHOR_CYN_SURFACE_EXIT`.

Triggers:
`CYN_TRG_EXTERIOR_APPROACH`, `CYN_TRG_ENTRY_MERGE`, `CYN_TRG_SURFACE_EXIT`.

### Checkpoint
Build security arch, shutter, breaker, terminal, preview camera, and visible power conduits.

Objects:
`CYN_OBJ_BREAKER_01`, `CYN_OBJ_CAMERA_PREVIEW`.

Interaction:
`CYN_INT_CHECKPOINT_BREAKER`.

### Flooded Maintenance
Build water/electrical hazard, raised bypass, service side room, drainage infrastructure, and optional maintenance terminal.

### Pump Hall
Place `CYN_OBJ_PUMP_01`, `CYN_TRG_PUMP_PRELOAD`, `CYN_TRG_PUMP_WAKE`, and `CYN_LOOK_PUMP_GAUGE`.
The dead pump must be visible before it wakes. Animated piston sweep must be inaccessible.

### Security Spine
Build compact combat/stealth zone, bypass route, camera sight lines, security office, and merge point.
Use `CYN_OBJ_CAMERA_A/B/C`.
Quest resolution must not depend on every hostile NPC dying.

### Biometric Gate
Use `CYN_OBJ_READER_01`, `CYN_INT_BIOMETRIC_READER`, `CYN_TRG_POST_BIOMETRIC`, and `CYN_LOOK_BIOMETRIC_SCREEN`.
Gate must recover from interrupted presentation.

### Observation Lab
Use `CYN_OBJ_OBSERVATION_CHAIR`, chair scan, subject records, and Mara override terminal.

### Personality Archive
Use storage racks, the empty `CYN_OBJ_SLOT_1140`, optional `CYN_OBJ_SLOT_1179`, purge room, and destroyed cartridges.
The mandatory exit depends only on discovering 0-1140.

### Prediction Hall
Use `CYN_OBJ_PREDICTION_COUNTER`, `CYN_OBJ_BRANCH_PROJECTOR`, and `CYN_OBJ_ECHO_SCANNER`.
The projection volume must remain free of obstructing geometry.

### Branch Coffins
Use `CYN_OBJ_COFFIN_1140` as the mandatory open unit plus optional damaged/mystery units.

### Comparison Lab
Use `CYN_OBJ_COMPARISON` and `CYN_INT_COMPARISON_APPARATUS`.

### Server Vault
Use grouped server banks and sequential wake triggers rather than hundreds of independent scripted devices.

### Core Antechamber
Place the sealed Continuity door as an optional mystery and the core authorization device on the mandatory path.

### Predictive Core
Use `CYN_OBJ_CORE`, core cameras, coolant/server groups, and a separate readable terminal.
The wake trigger must fire only after the core is already in view.

### Ending Control / Escape
Use one physical shutdown console with four logical ending actions, then a short service route/elevator to the surface.

## Custom asset IDs

```text
CYN_ASSET_SPLINTER_1140
CYN_ASSET_CRADLE_1140
CYN_ASSET_PERSONALITY_RACK
CYN_ASSET_BRANCH_PROJECTOR
CYN_ASSET_OBSERVATION_CHAIR
CYN_ASSET_ASH_SERVER
CYN_ASSET_RECONSTRUCTION_TABLE
CYN_ASSET_ECHO_FRAGMENT_A
CYN_ASSET_ECHO_FRAGMENT_B
CYN_ASSET_ECHO_FRAGMENT_C
CYN_ASSET_ECHO_FRAGMENT_D
CYN_ASSET_ECHO_FRAGMENT_E
CYN_ASSET_ECHO_FRAGMENT_F
CYN_ASSET_PUMP
CYN_ASSET_SHUTDOWN_CONSOLE
CYN_ASSET_ARCHIVE_SCANNER
CYN_ASSET_FIA_READER
CYN_ASSET_DESTROYED_CARTRIDGE
CYN_ASSET_CONTINUITY_DOOR
CYN_ASSET_EVIDENCE_CASE
CYN_ASSET_MARA_FIELD_KIT
CYN_ASSET_COUNTER
CYN_ASSET_CAMERA
CYN_ASSET_COMPARISON
CYN_ASSET_BRANCH_COFFIN
CYN_ASSET_PREDICTIVE_CORE
```

## Asset import checklist

For every Pixal3D/custom model:

- clean topology and remove hidden geometry
- correct real-world scale and transforms
- stable pivot
- moving/emissive parts separated as needed
- UV/PBR materials verified
- minimized material count
- simplified collision
- LODs
- resource path documented
- isolated spawn test
- shadow/streaming/collision test

## World power

Canonical `ash_world_power_stage`:

```text
0 DEAD
1 CHECKPOINT
2 MAINTENANCE
3 SECURITY
4 ARCHIVE
5 PREDICTION
6 CONTINUITY
7 CORE
```

Implement `CYN_ApplyPowerStage(stage)` as presentation that reads the power-stage fact the quest graph writes, to control grouped lights, terminal availability, server emissives, camera standby, pump state, ambience, and machinery.

## Trigger rules

Every mandatory trigger must have a stable ID, debug bounds, enable condition, one-shot guard where appropriate, immediate canonical fact write, reverse-crossing safety, teleport safety, save/load safety, and logging.

**Never gate mandatory progression solely on an animation-finished callback.**

## Interaction rules

Every interaction needs a localized prompt, enable condition, radius, player alignment, spam protection, processing/completed/post state, save/load restoration, and fallback.

Generic states:

```text
0 DISABLED
1 AVAILABLE
2 PROCESSING
3 COMPLETE
4 POST_STATE
```

## Key stateful devices

### Pump
Persistent authority: `ash_pumps_activated`.
Runtime states: OFF, STARTING, RUNNING, POST_STATE.
On reload after activation, restore RUNNING directly without replaying startup.

### Cameras
States: OFF, STANDBY, TRACK, LOCKED.
Clamp mechanical yaw/pitch; no snapping or impossible 360-degree movement.

### Prediction Counter
Initial:
```text
GENERATED 031884
STABLE    000217
RETAINED  000001
```
Later may show `RETAINED 000002`.
Destroy may briefly show `000000` and then `000001`.

### Branch Projector
States:
```text
OFF
BOOTING
TREE_FULL
TREE_COLLAPSING
SOURCE_0
POST_ANALYSIS
```

### Comparison Apparatus
Final display:
```text
SOURCE: 0
INSTANCE: 1140
CONTINUITY MATCH: 91.3%
DIVERGENCE: 8.7%
```
Set `ash_v_identity_match` and `ash_knows_v_is_source` before presentation completes.

### Predictive Core
Persistent state derives from authorization, activation, truth, and ending facts—not raw animation time.

Wake order:
```text
entrance seal
floor guidance
coolant
server bank A
server bank B
cameras
outer ring
inner processor
terminal
```

Truth display:
```text
PROJECT: CONTINUITY
SOURCE: 0
GENERATIONS: 031884
STABLE: 000217
RETAINED: 000001
INSTANCE: 0-1140
SELF-AWARENESS EVENT: CONFIRMED
STATUS: REMOVED
```

## Prediction deviation

Canonical fact: `ash_prediction_deviation`, range 0..7.

Suggested events:
```text
PD01 alternate entry
PD02 security combat avoided
PD03 predicted dialogue rejected
PD04 predicted object left
PD05 predicted path ignored
PD06 predicted Mara response contradicted
PD07 pre-core divergence
```

Class:
```text
0–1 LOW
2–3 MEDIUM
4–7 HIGH
```

Deviation changes interpretation only. It does not lock endings.

## Endings

Canonical:
```text
0 NONE
1 DESTROY
2 ABSORB
3 BLUE_EYES
4 HIDE
```

The questphase ending node (not REDscript) must commit the canonical ending, synchronize compatibility booleans, disable alternatives, set post-state, persist, and enable escape before fragile presentation begins.

Destroy: purge, server shutdown, counter callback.

Absorb: `ash_1140_in_v = 1`; reconciliation remains unresolved.

Blue Eyes: remote authorization received, credential unknown.

Hide: external links severed, instance external/location unknown, prediction continues.

## Escape / completion

Any valid ending sets:
```text
ash_escape_started = 1
ash_cyn_phase = 110
```

Surface exit sets:
```text
ash_cynosure_complete = 1
ash_cyn_phase = 120
```

## Save/load reconstruction

Implement `CYN_ApplyPersistentWorldState()` (read-only: reads facts, never writes story state) for checkpoint power, water, pump, cameras, archive lights, projector, server power, core state, ending state, and exit availability.

One-shot cinematics are never required to reconstruct final state.

## Repair

Implement `CYN_ValidateAndRepairState()`.

Safe examples:
- ending ID > 0 → ending-selected and escape-started
- core-entered → authorization, when logically proven
- post-gate location → biometric scan/match
- post-checkpoint location → checkpoint power

Never guess ambiguous history such as which entry route was used.

## Debug tooling

```text
ash.cyn.status
ash.cyn.dump
ash.cyn.validate
ash.cyn.repair
ash.cyn.fact <name>
ash.cyn.set <name> <value>
ash.cyn.phase <value>
ash.cyn.power <0..7>
ash.cyn.deviation <0..7>
ash.cyn.ending <0..4>
ash.cyn.tp <room> [--setup]
```

Overlay should show phase, room, power, Echoes, deviation, Mara state, key reveal facts, ending, nearest trigger/interaction, current objective, and dialogue lock.

## Visual language

Primary: aged gunmetal, institutional off-white, dark polymer, black ceramic, oxidized steel.

Accents: hazard yellow, muted amber, old FIA red, limited cold cyan.

Condition: flood streaks, mineral buildup, scratches, chipped paint, repair welds, replaced panels, exposed fasteners.

Avoid pristine clean-lab sci-fi.

## Minimum playable route

```text
Enter
→ checkpoint
→ pump
→ security
→ biometric
→ observation
→ 0-1140 slot
→ projector
→ branch coffin
→ comparison
→ server vault
→ core
→ truth
→ ending
→ escape
```

Must work with 0 Echoes, Mara dead, Johnny unavailable, and all optional logs ignored.

## Protected mysteries

Do not resolve in this quest:

- opening caller
- exact Blue Eyes knowledge
- current Cynosure controller
- nature/status of 0-1179
- what is behind Continuity door
- whether every branch is conscious
- whether prediction is deterministic
- whether 0-1140 predicted the whole quest
- whether Cynosure still generates branches

## Release gate

Release-ready only when the vertical slice works, mandatory assets are integrated, all endings and save/load states pass, no progression soft locks remain, localization/collision/navmesh/performance are complete, story reveal order passes, and debug-only content is disabled.

## Final principle

```text
SPACE CHANGES
→ PLAYER NOTICES
→ PLAYER INTERACTS
→ QUEST FACT CHANGES
→ MACHINE RESPONDS
→ WORLD CHANGES
→ STORY MEANING CHANGES
```

Cynosure should tell its core story through space and machines even if the player ignores every optional log.
