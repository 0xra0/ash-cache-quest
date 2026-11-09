# CYNOSURE_WORLD_ASSET_MAP.md

# Ash Cache — Cynosure World / Asset Placement Map

## Purpose

Maps each Cynosure room to custom assets, vanilla/environmental roles, logical object IDs, approximate dimensions, anchors, player routes, collision, lighting, audio, triggers, interactions, streaming groups, and sight-line requirements.

Final absolute transforms belong in World Builder resources and `CYNOSURE_TRANSFORMS.json`.

## Coordinate convention

Planning convention:

```text
+X right
-X left
+Y deeper into Cynosure
-Y toward surface
+Z up
```

Use room-local origins until real world coordinates are measured.

## General scale

Typical corridor:
```text
2.5–3.5 m wide
2.8–3.5 m high
```

Major service corridor:
```text
4–5 m wide/high
```

Research room:
```text
8–14 m wide
8–16 m long
4–5 m high
```

Machinery room:
```text
12–22 m wide
15–28 m long
6–10 m high
```

Core:
```text
22–30 m diameter/equivalent
10–16 m high
```

## Asset categories

- **CUSTOM HERO** — unique quest-defining machine/prop.
- **CUSTOM MODULAR** — reusable Cynosure technology.
- **VANILLA STRUCTURAL** — floors, walls, ceilings, stairs, doors, railings, pipes, supports.
- **VANILLA CLUTTER** — tools, crates, furniture, cables, debris.
- **SCRIPTED** — stateful object controlled by quest/runtime logic.

## Streaming groups

```text
CYN_STREAM_A_ENTRY
CYN_STREAM_B_MAINTENANCE
CYN_STREAM_C_SECURITY
CYN_STREAM_D_RESEARCH
CYN_STREAM_E_ARCHIVE
CYN_STREAM_F_PREDICTION
CYN_STREAM_G_CONTINUITY
CYN_STREAM_H_CORE
```

Current room plus adjacent transition should be loaded before sight lines expose it.

---

# CYN_ROOM_00_SURFACE — Surface Access

Approximate playable footprint:
```text
20 × 25 m
```

Purpose: conceal Cynosure beneath believable municipal/Militech/FIA infrastructure.

Vanilla roles:
- concrete retaining walls
- storm drain/service fencing
- barriers
- rusted industrial doors
- utility boxes
- debris
- pipes
- city clutter

Anchors:
```text
ANCHOR_CYN_SURFACE_APPROACH
ANCHOR_CYN_MAIN_ENTRY
ANCHOR_CYN_VENT_ENTRY
ANCHOR_CYN_SURFACE_EXIT
ANCHOR_CYN_SURFACE_MARKER
```

Main hatch and vent should feel like two discoverable routes.

`CYN_TRG_EXTERIOR_APPROACH` must not fire from unrelated roads above/beside the area.

---

# CYN_ROOM_01_ENTRY — Service Entry

Approximate:
```text
5 × 12 × 3.5 m
```

Visual language:
- faded FIA paint
- water infiltration
- broken conduit
- old security strip lighting
- dust/debris

Anchors:
```text
ANCHOR_CYN_ENTRY_MAIN_IN
ANCHOR_CYN_ENTRY_VENT_IN
ANCHOR_CYN_ENTRY_MERGE
ANCHOR_CYN_ENTRY_CHECKPOINT_VIEW
```

From the merge point, the checkpoint should be clearly visible.

---

# CYN_ROOM_02_CHECKPOINT — Security Checkpoint

Approximate:
```text
7 × 10 × 4 m
```

Objects:
```text
CYN_OBJ_BREAKER_01
CYN_OBJ_CHECKPOINT_SHUTTER
CYN_OBJ_CHECKPOINT_TERMINAL
CYN_OBJ_CAMERA_PREVIEW
```

Vanilla roles:
- security arch
- turnstile/barrier
- lockers
- utility cabinet
- terminal frame

Layout should visually communicate:
```text
no power → breaker → locked shutter
```

Before power:
- faint emergency spill
- mostly dead room

After power:
- one overhead bank
- terminal
- camera LED
- shutter response

---

# CYN_ROOM_03_FLOODED — Flooded Maintenance

Approximate:
```text
3.5–5 m wide
18–28 m long
4–5 m high
```

Vanilla roles:
- pipes
- cable trays
- maintenance bridges
- junction boxes
- broken lights

Water depth:
```text
0.25–0.6 m
```

Route A:
```text
disable hazard → use floor route
```

Route B:
```text
raised/climb bypass
```

Both reconnect before the pump hall.

Anchors:
```text
ANCHOR_CYN_FLOOD_ENTRY
ANCHOR_CYN_FLOOD_HAZARD
ANCHOR_CYN_FLOOD_BYPASS_ENTRY
ANCHOR_CYN_FLOOD_BYPASS_EXIT
ANCHOR_CYN_FLOOD_ECHO_LOOK
ANCHOR_CYN_FLOOD_EXIT
```

---

# CYN_ROOM_03A_MAINT_SIDE — Maintenance Office

Approximate:
```text
4 × 5 × 3 m
```

Contents:
- maintenance terminal
- tools
- pump schematics
- workbench
- water damage
- technician note

Always optional.

---

# CYN_ROOM_04_PUMP — Pump Control Hall

Approximate:
```text
14–18 m wide
18–24 m long
7–9 m high
```

Hero:
```text
CYN_ASSET_PUMP
CYN_OBJ_PUMP_01
```

Concept footprint:
```text
~3.2 m wide
~2.4 m high
~2.0 m deep
```

Allow roughly:
```text
6 × 4 m
```
for installation/service clearance.

Sight line:
```text
ENTRY
→ gauges
→ pump
→ exit
```

The dead pump must be visible before `CYN_TRG_PUMP_WAKE`.

Collision:
- static machine collision
- animated piston exclusion
- pipe collision

Keep player roughly 0.6–1.0 m away from moving surfaces.

Audio:
```text
CYN_SFX_PUMP_MOTOR
CYN_SFX_PUMP_PISTONS
CYN_SFX_DRAINAGE
```

Lighting:
```text
CYN_LGT_STAGE_2_MAINTENANCE
CYN_LGT_PUMP_WARNING
```

---

# CYN_ROOM_05_SECURITY — Security Spine

Approximate:
```text
4–6 m wide
25–40 m long
~4 m high
```

Suggested sequence:
```text
entry
camera A
combat/stealth zone
security office
camera B
bypass reconnect
camera C
biometric gate
```

Custom:
```text
CYN_ASSET_CAMERA
CYN_OBJ_CAMERA_A
CYN_OBJ_CAMERA_B
CYN_OBJ_CAMERA_C
```

Mount cameras around 2.8–3.5 m high with roughly 8–12 m tracking radius.

Keep combat footprint compact, roughly 12–18 m.

Bypass reconnects before biometric gate.

---

# CYN_ROOM_05A_SECURITY_OFFICE — Security Office

Approximate:
```text
4 × 6 m
```

Contents:
- terminal
- dead monitors
- locker
- recent-visitor clue

No mandatory progression switch.

---

# CYN_ROOM_06_BIOMETRIC — Archive Gate

Approximate:
```text
6 × 8 × 4 m
```

Hero:
```text
CYN_ASSET_FIA_READER
CYN_OBJ_READER_01
```

Reader:
```text
~1.1–1.4 m high
```

Player anchor:
```text
~0.7–1.0 m from device
```

Requirements:
- screen readable at normal FOV
- gate sweep does not hit player
- gate looks more secure than prior service architecture

---

# CYN_ROOM_07_OBSERVATION — Neural Observation Lab

Approximate:
```text
10–14 m × 12–16 m × 4.5 m
```

Hero:
```text
CYN_ASSET_OBSERVATION_CHAIR
CYN_OBJ_OBSERVATION_CHAIR
```

Chair is off-center but visible from entry.

Keep about 2 m primary viewing clearance.

Vanilla roles:
- clinical wall modules
- observation glass
- drain
- workstation
- medical carts
- ceiling cable rack
- old monitors

The room should communicate restraint/study before text explains it.

---

# CYN_ROOM_07A_SUBJECT_RECORDS

Approximate:
```text
4–6 × 7 m
```

Contains:
```text
CYN_INT_SUBJECT_RECORDS
CYN_INT_MARA_OVERRIDE_LOG
```

Optional glass observation booth/records room.

---

# CYN_ROOM_08_ARCHIVE — Cognitive Archive

Approximate:
```text
16–22 m wide
20–30 m long
6–8 m high
```

Hero:
```text
CYN_ASSET_PERSONALITY_RACK
```

Objects:
```text
CYN_OBJ_STORAGE_RACK_A
CYN_OBJ_STORAGE_RACK_B
CYN_OBJ_STORAGE_RACK_C
CYN_OBJ_SLOT_1140
CYN_OBJ_SLOT_1179
```

Use one high-detail hero rack and repeated variants with different damage/emissive/slot population.

0-1140 must be naturally discoverable:
- not directly at entrance
- not hidden in far corner
- empty slot readable from about 2–4 m

0-1179 remains off the main route and optional.

---

# CYN_ROOM_08A_PURGE_ARCHIVE — Purged Branch Storage

Approximate:
```text
7 × 9 m
```

Custom:
```text
CYN_ASSET_DESTROYED_CARTRIDGE
```

Vanilla:
- storage bins
- damaged racks
- discard trays
- cleanup tools

Show 6–12 visible cartridges but only 2–4 need high-detail variants.

`CYN_OBJ_BLINKING_CART` should be subtle and optional.

---

# CYN_ROOM_09_PREDICTION — Prediction Processing Hall

Approximate:
```text
18–24 m wide
20–28 m long
8–10 m high
```

Hero assets:
```text
CYN_ASSET_COUNTER
CYN_ASSET_BRANCH_PROJECTOR
```

Composition:
```text
ENTRY
→ Prediction Counter
→ open processing floor
→ Branch Projector
→ Echo side room
→ Branch Coffins
```

Counter can sit 2.5–4 m above floor for room-scale readability.

Projector:
```text
~3.0 m high
~2.4 m wide
~1.8 m deep
```

Reserve active projection volume:
```text
6–8 m diameter
5–7 m high
```

Projection has no collision; base does.

Keep center visually open.

---

# CYN_ROOM_09A_ECHO_ANALYSIS — Echo Analysis

Approximate:
```text
7 × 8 × 4 m
```

Hero:
```text
CYN_ASSET_ARCHIVE_SCANNER
CYN_OBJ_ECHO_SCANNER
```

Provide at least 1.5 m working clearance.

---

# CYN_ROOM_10_BRANCH_COFFINS — Continuity Unit Chamber

Approximate:
```text
14–18 m diameter
6–8 m high
```

Hero:
```text
CYN_ASSET_BRANCH_COFFIN
```

Use circular or semi-circular arrangement, not straight warehouse rows.

Approximate unit:
```text
2.2–2.5 m tall
0.8–1.2 m wide/deep
```

`CYN_OBJ_COFFIN_1140`:
- door open
- missing central module
- disconnected cables
- exposed cooling
- readable labels

Mystery coffin:
- off main route
- small 2–4 m audio radius
- ambiguous only

---

# CYN_ROOM_11_COMPARISON — Source / Instance Lab

Approximate:
```text
10–14 × 12 × 5 m
```

Hero:
```text
CYN_ASSET_COMPARISON
CYN_OBJ_COMPARISON
```

Provide:
- Source display left
- Instance display right
- scan point center/front

The apparatus should be the only clearly active object when entering.

---

# CYN_ROOM_12_SERVER_VAULT — ASH Cache Vault

Approximate playable:
```text
12–18 m wide
35–50 m long
8–12 m high
```

Hero modular asset:
```text
CYN_ASSET_ASH_SERVER
```

Use:
- high-detail foreground rows
- repeated mid-distance modules
- far LOD/silhouette geometry

Control groups:
```text
CYN_OBJ_ASH_SERVER_GROUP_A
CYN_OBJ_ASH_SERVER_GROUP_B
CYN_OBJ_ASH_SERVER_GROUP_C
```

Avoid hundreds of independent device scripts.

Central walkway remains simple.

Wake triggers:
```text
CYN_TRG_SERVER_WAKE_A
CYN_TRG_SERVER_WAKE_B
CYN_TRG_SERVER_WAKE_C
```

Roughly 8–12 m apart and activate groups ahead of V.

Audio should spatially travel through the room.

---

# CYN_ROOM_13_CORE_ANTE — Core Antechamber

Approximate:
```text
12–16 × 14–18 × 6 m
```

Hero:
```text
CYN_ASSET_CONTINUITY_DOOR
CYN_OBJ_CONTINUITY_DOOR
```

Composition:
```text
Continuity Door
      |
ENTRY / staging ---- Core Door
```

Continuity is visibly important but not the mandatory route.

Door:
```text
~3–4.5 m wide
~3–4 m high
```

Place 30–60° off main core path with audio emitter behind it.

---

# CYN_ROOM_14_CORE — Predictive Core Chamber

Approximate:
```text
24–30 m diameter
12–16 m high
```

Hero:
```text
CYN_ASSET_PREDICTIVE_CORE
CYN_OBJ_CORE
```

Concept:
```text
~6.5 m high
~4.2 m diameter
```

Allow 8–10 m installation footprint.

Placement:
- at/near architectural center
- 2–3 m clear walkway
- 180–270° accessible orbit
- direct sight line from core entry trigger

Place core terminal 2–4 m from the machine, not on moving geometry.

Lighting wake:
```text
floor guidance
coolant indicators
server perimeter
amber core ring
central processor
```

Audio:
```text
CYN_SFX_CORE_COOLANT
CYN_SFX_CORE_HUM
CYN_SFX_CORE_ROTATION
```

---

# CYN_ROOM_15_ENDING_CONTROL — Emergency Control

Approximate:
```text
7–10 × 8–12 m
```

Hero:
```text
CYN_ASSET_SHUTDOWN_CONSOLE
CYN_OBJ_FINAL_CONSOLE
```

Prefer a location where the core is visible while choosing.

Use broad logical interaction zones for the four endings rather than tiny precision buttons.

Only the chosen ending control animates.

---

# CYN_ROOM_16_ESCAPE — Service Extraction

Short route:
```text
15–30 m
```
plus elevator.

No second dungeon.

Use:
```text
short service corridor
ending callback
elevator
surface
```

Elevator interior:
```text
~2.5 × 2.5 m minimum
```

---

# Secondary custom assets

`CYN_ASSET_MARA_FIELD_KIT` and `CYN_ASSET_RECONSTRUCTION_TABLE` primarily belong in Mara's workspace.

`CYN_ASSET_CRADLE_1140` fits near Archive/cold-storage and should show the missing-cartridge story physically.

Use one canonical `CYN_ASSET_SPLINTER_1140` in inventory/scripted placements rather than arbitrary duplicates.

Echo fragment props in scanner sequences should be temporary display props, not duplicate collectibles.

---

# Discovery hierarchy

Reveal unique models in increasing scale:

```text
FIA reader
→ observation chair
→ storage rack
→ counter/projector
→ branch coffins
→ comparison apparatus
→ server vault
→ Continuity door
→ Predictive Core
```

---

# Density rhythm

```text
Entry: low
Maintenance: medium industrial
Security: controlled
Research: sparse/clinical
Archive: dense repetition
Prediction: open around hero devices
Coffins: sparse
Server Vault: dense repetition
Core: large negative space
```

---

# Trigger placement rules

Mandatory triggers:
- span every legal route
- extend beyond doorway edges
- avoid tiny narrow volumes
- fire only after genuine room entry

Typical depth:
```text
1.5–3 m
```

Cinematic room:
```text
3–6 m inside
```

Fail-safe triggers should be impossible to hit early during normal play.

---

# Interaction placement

Typical player distance:
```text
0.7–1.5 m normal device
1.5–2.5 m large machine
```

Avoid:
- extreme look angles
- standing inside collision
- tiny aim points
- door/machine sweep overlap

---

# Readability

Critical text:
```text
0-1140
SOURCE 0
031884
000217
000001
```

must be readable directly or via UI.

Do not rely only on tiny baked texture text.

---

# Dynamic object policy

Real animation:
```text
pump
camera heads
reader scan/shutter
branch projector
comparison scanner
core
shutdown console
```

Mostly emissive/material state:
```text
server racks
prediction counter
storage racks
destroyed cartridges
```

---

# Lighting palette

Surface/entry: dirty neutral, sodium, emergency red.

Maintenance: green-grey, amber machinery.

Security: cold white, hazard yellow.

Research: degraded institutional white, limited cyan diagnostic.

Archive: dark with amber storage LEDs.

Prediction: black, amber/gold projection, limited cyan.

Continuity: controlled dark amber.

Core: deep black, warm amber/gold, small red warnings.

---

# Audio progression

```text
Night City
→ water/building creaks
→ distant machinery
→ pump impact
→ security servos
→ quiet research electronics
→ archive fans/drives
→ synthetic prediction pulse
→ coffin near-silence
→ distributed server hum
→ low core resonance
→ escape back to city ambience
```

---

# Streaming/performance

Never place a major reveal trigger directly on a streaming boundary.

Use roughly 5–15 m preload buffers.

`CYN_STREAM_H_CORE` should preload in the core antechamber.

Server vault detail tiers:
```text
high detail foreground
medium detail next rows
low detail farther rows
silhouette/fake deep background
```

---

# Placeholder dimensions

During greybox:

```text
Pump: ~3.2 × 2.0 × 2.4 m
Projector: ~2.4 × 1.8 × 3.0 m
Core: ~4.2 m diameter × 6.5 m high
Branch coffin: ~1.0 × 1.0 × 2.4 m
Comparison: ~2.5 × 1.2 × 2.2 m
Continuity door: ~4 × 1 × 4 m
```

---

# Room-to-asset summary

```text
SURFACE — vanilla infrastructure
ENTRY — vanilla infrastructure
CHECKPOINT — camera + breaker
FLOODED — vanilla maintenance
PUMP — CYN_ASSET_PUMP
SECURITY — CYN_ASSET_CAMERA
BIOMETRIC — CYN_ASSET_FIA_READER
OBSERVATION — CYN_ASSET_OBSERVATION_CHAIR
ARCHIVE — personality rack + destroyed cartridges + optional cradle
PREDICTION — counter + projector + archive scanner
COFFINS — branch coffin
COMPARISON — comparison apparatus
SERVER VAULT — ASH servers
CORE ANTECHAMBER — Continuity door
CORE — Predictive Core
ENDING — shutdown console
ESCAPE — mostly vanilla infrastructure
```

## Final rule

Every custom asset must have an explicit story reason for its exact location. World placement and story meaning should be the same system.
