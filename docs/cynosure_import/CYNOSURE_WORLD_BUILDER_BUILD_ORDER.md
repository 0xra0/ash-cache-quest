# CYNOSURE_WORLD_BUILDER_BUILD_ORDER.md

# Ash Cache — Cynosure World Builder Construction Order

## Purpose

Defines the literal construction sequence for Cynosure: topology first, then greybox, gameplay logic, custom asset replacement, and finally art/audio/polish.

> **Do not decorate a room whose traversal, trigger coverage, or quest progression is not already stable.**

## Construction passes

```text
PASS 1 — TOPOLOGY
PASS 2 — GREYBOX
PASS 3 — GAMEPLAY LOGIC
PASS 4 — CUSTOM ASSET REPLACEMENT
PASS 5 — ART / AUDIO / POLISH
```

## Recommended vertical layout

Design-relative only:

```text
SURFACE              Z = 0
ENTRY/CHECKPOINT     Z = -4 m
MAINTENANCE          Z = -9 m
SECURITY             Z = -14 m
RESEARCH             Z = -20 m
ARCHIVE              Z = -27 m
PREDICTION           Z = -35 m
CONTINUITY           Z = -43 m
CORE                 Z = -52 m
```

Final world coordinates may differ. The important requirement is a continuous sense of descent.

## Vertical transitions

Prefer stairs, ramps, descending service corridors, and landings.

Reserve the strong elevator transition for extraction.

## Macro footprint

Approximate total playable footprint:

```text
length 180–260 m
width 40–80 m
vertical span 50–60 m
```

Use turns, offsets, vertical overlaps, and loops rather than one straight corridor.

## Macro layout

```text
SURFACE
  |
ENTRY
  |
CHECKPOINT
  |
FLOODED ---- optional maintenance side room
  |
PUMP
  |
SECURITY ---- office / bypass
  |
BIOMETRIC
  |
RESEARCH ---- subject records
  |
ARCHIVE ---- purge room
  |
PREDICTION ---- Echo room
  |
COFFINS
  |
COMPARISON
  |
SERVER VAULT
  |
CORE ANTECHAMBER ---- CONTINUITY DOOR
  |
CORE
  |
ENDING CONTROL
  |
ESCAPE
```

---

# Step 01 — Establish world origin

Create:
```text
ANCHOR_CYN_WORLD_ORIGIN
```

Place it at a stable architectural reference and document position, rotation, floor Z.

Do not use a temporary prop as origin.

---

# Step 02 — Surface connection

Create only enough geometry for:
- approach
- main hatch
- vent route
- future exit

No detailed decoration.

Acceptance:
- both entry routes work
- both merge
- no out-of-bounds route
- surface exit reserved

---

# Step 03 — Entry merge

Create `CYN_ROOM_01_ENTRY`.

Greybox:
```text
4–5 m wide
10–12 m long
3.5 m high
```

Merge main/vent at `ANCHOR_CYN_ENTRY_MERGE`.

Reserve `CYN_TRG_ENTRY_MERGE`.

---

# Step 04 — Security checkpoint

Create:
```text
~7 × 10 × 4 m
```

Temporary labeled proxies:
```text
BREAKER
SHUTTER
TERMINAL
CAMERA
```

Before art:
- breaker interaction
- shutter blocker
- power fact
- save/load
- bypass repair

---

# Step 05 — Flooded maintenance

Create:
```text
~4 m wide
~22 m long
~4.5 m high
```

Add:
- main floor route
- hazard volume
- raised bypass
- side-room doorway

A flat temporary plane can represent water/hazard during greybox.

---

# Step 06 — Maintenance side room

Create optional:
```text
~4 × 5 × 3 m
```

Must reconnect and never become required.

---

# Step 07 — Pump hall

Create:
```text
~16 × 21 × 8 m
```

Pump proxy:
```text
~3.2 × 2.0 × 2.4 m
```

Reserve about:
```text
6 × 4 m
```
service/animation clearance.

Route:
```text
door
→ 5–7 m approach
→ wake trigger
→ pump
→ exit
```

---

# Step 08 — Prototype pump logic

Implement temporary:
- startup animation
- lights
- water change
- objective update

Test:
- save before
- save during
- save after
- leave during startup
- return later

---

# Step 09 — Security spine

Create:
```text
~5 m wide
~32 m long
~4.5 m high
```

Break into:
- entry
- encounter
- office junction
- bypass reconnect
- camera reveal
- biometric vestibule

---

# Step 10 — Security bypass

Create:
```text
~1.5–2 m wide
```

Reconnect before biometric gate.

Place:
```text
CYN_TRG_SECURITY_BYPASS_COMPLETE
```

---

# Step 11 — Security office

Create optional:
```text
~4 × 6 m
```

No mandatory switch.

---

# Step 12 — Prototype security

Test:
- combat
- stealth
- bypass
- partial combat then bypass
- stuck enemy
- enemy leaves area
- camera trigger

All paths must reach biometric gate.

---

# Step 13 — Biometric gate

Create:
```text
~6 × 8 × 4 m
```

Reader proxy:
```text
~0.6 × 0.5 × 1.4 m
```

Create player anchor about 0.8 m away.

Ensure screen is visible and gate sweep is safe.

---

# Step 14 — Prototype biometric reveal

Implement 0-1140 recognition with placeholder UI.

Test:
- scan
- gate unlock
- save during scan
- bypass repair

---

# Step 15 — Observation lab

Create:
```text
~12 × 14 × 4.5 m
```

Chair proxy:
```text
~1.2 × 1.5 × 2.2 m
```

Place off-center with ~2 m clearance.

Chair silhouette must be visible from entry.

---

# Step 16 — Subject records

Create optional:
```text
~5 × 6 m
```

Observation/records booth.

---

# Step 17 — Archive descent

Create ~6–8 m vertical drop using stairs/landings/service conduits.

Use the descent as a streaming buffer.

---

# Step 18 — Personality archive

Create:
```text
~18 × 26 × 7 m
```

Use 8–14 greybox rack blocks.

Typical rack proxy:
```text
1.0 m deep
2.5–4 m wide
4–5 m high
```

---

# Step 19 — Reserve 0-1140 rack

Create:
```text
CYN_OBJ_STORAGE_RACK_A
CYN_OBJ_SLOT_1140
```

Development marker:
```text
0-1140
EMPTY
```

Make it easy to find during testing.

---

# Step 20 — Purge side room

Create optional:
```text
~7 × 9 m
```

Use cartridge proxies only.

---

# Step 21 — Prototype archive progression

Implement:
- archive wake
- 0-1140 interaction
- exit unlock

Test with every optional archive clue ignored.

---

# Step 22 — Prediction descent

Another ~6–8 m descent using wide industrial stairs, shaft views, cables, conduits.

---

# Step 23 — Prediction hall

Create:
```text
~20 × 24 × 9 m
```

Counter proxy and projector proxy:
```text
~2.4 × 1.8 × 3.0 m projector
```

Reserve:
```text
~7 m diameter
```
projection volume.

Keep the center open.

---

# Step 24 — Echo analysis room

Create optional:
```text
~7 × 8 m
```

Place scanner proxy.

---

# Step 25 — Prototype prediction logic

Implement:
- counter scan
- projector interaction
- branch collapse
- 0-Echo fallback
- 6-Echo full case

Verify Source 0 is not yet identified as V.

---

# Step 26 — Branch-coffin chamber

Create:
```text
~16 m diameter
~7 m high
```

Use five greybox coffin proxies:
```text
~1 × 1 × 2.4 m
```

Place open 0-1140 unit as strongest sight-line endpoint.

---

# Step 27 — Prototype coffin reveal

Display:
```text
COGNITIVE CONTINUITY UNIT
BIOLOGICAL CAPACITY: NONE
SOURCE: 0
BRANCH: 1140
```

Test progression to comparison.

---

# Step 28 — Comparison lab

Create:
```text
~12 × 12 × 5 m
```

Proxy:
```text
~2.5 × 1.2 × 2.2 m
```

Keep room sparse.

---

# Step 29 — Prototype Source 0 reveal

Implement:
```text
SOURCE 0
INSTANCE 1140
91.3%
8.7%
```

Set identity-match fact before presentation completes.

Test save/load immediately.

---

# Step 30 — Server vault

Create:
```text
~15 × 40 × 10 m
```

Use three large proxy groups instead of hundreds of servers.

---

# Step 31 — Server wake path

Place A/B/C wake triggers roughly 8–12 m apart.

Activate server groups ahead of V.

---

# Step 32 — ASH terminal alcove

Reserve:
```text
~3 × 4 m
```

Never obstruct the main route.

---

# Step 33 — Prototype server vault

Test:
- group A/B/C wake
- optional terminal
- reach core antechamber
- early performance

---

# Step 34 — Core antechamber

Create:
```text
~14 × 16 × 6 m
```

Place distinct CORE and CONTINUITY door proxies.

---

# Step 35 — Continuity door

Proxy:
```text
~4 × 1 × 4 m
```

Place 30–60° off mandatory core route.

Reserve 3–4 m interaction area.

---

# Step 36 — Core door / authorization

Keep mandatory core route visually obvious.

Place authorization reader clearly associated with core door.

---

# Step 37 — Prototype Continuity states

Test:
- normal denial
- six Echoes
- high deviation
- door never opens

Fix any opening condition before continuing.

---

# Step 38 — Core chamber shell

Create:
```text
~26 m diameter
~14 m high
```

Do not add detailed clutter yet.

---

# Step 39 — Core placeholder

Place:
```text
~4.2 m diameter
~6.5 m high
```

at `ANCHOR_CYN_CORE_CENTER`.

Reserve ~9 m installation footprint.

---

# Step 40 — Core walkway

Provide:
```text
>= 2.5 m
```
clearance around accessible sides.

Target:
```text
180–270°
```
of orbit.

---

# Step 41 — Core terminal

Separate proxy:
```text
~1.2 × 0.7 × 1.4 m
```

Place 2–4 m from core.

---

# Step 42 — Core cameras

Add A/B mounts approximately 5–8 m high.

---

# Step 43 — Core entry trigger

Place roughly 4–6 m inside the room.

The core must already be visible.

---

# Step 44 — Prototype core wake

Order:
```text
door
floor lights
cooling
servers
cameras
core movement
terminal
```

Commit canonical facts before presentation finishes.

Immediately test save/load.

---

# Step 45 — Prototype core truth

Test:
- Mara alive
- Mara dead
- low/high trust
- low/high deviation

Do not build ending art until truth flow is stable.

---

# Step 46 — Ending control

Create:
```text
~8 × 10 m
```

Prefer slight elevation and a view of the core.

---

# Step 47 — Ending console proxy

Use:
```text
~2.0 × 0.8 × 1.4 m
```

Provide four broad logical interaction zones.

---

# Step 48 — Implement all four endings

Finish all four logically before over-polishing any one.

Each ending must:
- commit canonical ID
- disable alternatives
- set post-state
- enable escape

---

# Step 49 — Escape corridor

Create short:
```text
~20 m
```
service route.

---

# Step 50 — Escape elevator

Reserve at least:
```text
2.5 × 2.5 m
```

Internal teleport/streaming is acceptable if player perception stays coherent.

---

# Step 51 — Full greybox regression

Run:
```text
Surface
→ Entry
→ Checkpoint
→ Flooded
→ Pump
→ Security
→ Biometric
→ Observation
→ Archive
→ Prediction
→ Coffins
→ Comparison
→ Server Vault
→ Antechamber
→ Core
→ Ending
→ Escape
→ Surface
```

Repeat with:
- vent
- security bypass
- 0 Echoes
- Mara dead

Do not begin detailed art until both paths work.

---

# Streaming setup

Recommended boundaries:

```text
A→B after checkpoint
B→C before security
C→D after biometric
D→E during archive descent
E→F during prediction descent
F→G after comparison
G→H in core antechamber
```

Preload major reveals 5–15 m early.

Core stream must preload in antechamber.

---

# Trigger pass

Order:
```text
1 progression triggers
2 mandatory interactions
3 fail-safes
4 optional lore
5 cinematic triggers
```

Test every mandatory trigger by walking, sprinting, jumping, crouching, hugging both walls, and crossing backward.

---

# Interaction pass

Every mandatory device gets:
- object
- player anchor
- look target
- radius
- collision check

Test front/left/right approach, crouched state, weapon drawn, and rapid input.

---

# Custom asset replacement order

```text
1 FIA reader
2 personality rack
3 prediction counter
4 branch projector
5 branch coffins
6 comparison apparatus
7 server modules
8 Continuity door
9 Predictive Core
10 pump
11 cameras
12 observation chair
13 shutdown console
14 scanner/destroyed cartridges/secondary assets
```

After each replacement verify scale, pivot, collision, interaction anchors, animation, and LOD.

---

# Structural art pass

Replace greybox with vanilla/base-game structural pieces:

```text
floors
walls
stairs
ceilings
doors
railings
pipes
supports
```

Do one zone at a time and rerun navigation.

Use custom architecture only where unique machine mounting/Continuity/core framing requires it.

---

# Collision / navmesh

Perform collision after major geometry stabilizes, then navmesh.

Test:
```text
walk
sprint
jump
crouch
combat movement
NPC movement
Mara pathing if present
```

Pay special attention to pump, projector, coffins, server rows, core walkway, final console.

---

# Lighting blockout

Implement power-stage groups 0–7 before individual fixture polish.

Take screenshots from identical locations at multiple stages.

---

# Audio blockout

Add rough:
- water
- pump
- camera servo
- archive fans
- projector
- coffin ambience
- server wake
- core hum

Check occlusion, especially pump through walls and Continuity movement behind the sealed door.

---

# Environmental storytelling

Only after mechanics stabilize, add:
```text
decals
labels
repair welds
water marks
tools
damaged panels
FIA markings
serials
maintenance notes
```

Zone themes:
```text
Entry — closure / abandonment
Maintenance — survival / repair / water
Security — classification / control
Research — human experimentation
Archive — scale / deletion
Prediction — modeling / probability
Coffins — persistent simulation
Server Vault — discarded futures
Core — continuing machinery/intelligence
```

---

# Clutter / materials / LOD

Clutter must never obscure interactions, labels, routes, or hero silhouettes.

Shared palette:
```text
aged gunmetal
off-white institutional panels
hazard yellow
muted amber
small cyan diagnostics
limited red warning accents
```

LOD priority:
```text
server modules
archive racks
coffins
camera heads
core peripherals
```

---

# Runtime tests

Sprint through the level for trigger/streaming coverage.

Explore/backtrack for optional-content stability.

Run all debug teleports.

Walk the level while ignoring terminals and ask whether the environment alone still communicates the major story beats.

---

# Completion gates

A room is not complete until:
- correct ID/stream group
- entry/exit work
- sight line works
- mandatory trigger covers all routes
- interaction accessible
- collision/navmesh safe
- audio/light assigned
- custom asset fits proxy volume
- save/load reconstructs
- debug teleport works

Greybox is complete only when all rooms, connections, mandatory triggers/interactions, endings, escape, save/load, and alternate paths work with no optional dependency.

## Final principle

```text
CAN THE PLAYER GET THERE?
→ CAN THE QUEST RECOGNIZE IT?
→ CAN THE PLAYER INTERACT?
→ CAN THE STATE SURVIVE SAVE/LOAD?
→ DOES THE ROOM TELL THE RIGHT STORY?
→ ONLY THEN: DOES IT LOOK FINISHED?
```
