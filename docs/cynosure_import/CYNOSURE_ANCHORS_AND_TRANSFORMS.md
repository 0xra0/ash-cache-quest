# CYNOSURE_ANCHORS_AND_TRANSFORMS.md

# Ash Cache — Cynosure Anchor / Transform Registry

## Purpose

Canonical spatial registry for the Cynosure level.

It records real World Builder transforms for:
- facility origin
- room origins
- doorway connections
- player interaction positions
- custom asset transforms
- trigger volumes
- look-at targets
- camera mounts
- NPC scene anchors
- audio emitters
- lighting references
- debug teleports
- streaming transitions
- escape/elevator points

This document must contain measured project coordinates, not guessed coordinates.

Until measured:
```text
TBD
```

Never invent a plausible-looking value.

## Authority

```text
WORLD BUILDER RESOURCE
→ CYNOSURE_ANCHORS_AND_TRANSFORMS.md
→ QUEST / DEBUG REFERENCES
```

If this registry disagrees with the live resource, verify the current source and synchronize them.

## Related documents

```text
CYNOSURE_IDS.md
CYNOSURE_FACTS.md
CYNOSURE_WORLD_ASSET_MAP.md
CYNOSURE_WORLD_BUILDER_BUILD_ORDER.md
CYNOSURE_IMPLEMENTATION.md
CYNOSURE_TEST_MATRIX.md
CYNOSURE_TRANSFORMS.json
```

`CYNOSURE_IDS.md` defines what an anchor is called.
This file defines where it is.

## Transform format

Position:
```yaml
position:
  x: TBD
  y: TBD
  z: TBD
```

Rotation:
```yaml
rotation:
  yaw: TBD
  pitch: TBD
  roll: TBD
```

Use degrees.

Default scale:
```yaml
scale:
  x: 1.000
  y: 1.000
  z: 1.000
```

Hero assets should remain close to 1/1/1. Fix bad source scale rather than compensating with extreme world scaling.

## Entry schema

```text
ID:
Type:
Room:
Stream Group:
Resource:

Position:
  X:
  Y:
  Z:

Rotation:
  Yaw:
  Pitch:
  Roll:

Scale:
  X:
  Y:
  Z:

Parent:
Purpose:

Status:
  UNMEASURED / MEASURED / VERIFIED / LOCKED

Verified Build:
Notes:
```

## Measurement states

**UNMEASURED** — placeholder/TBD.

**MEASURED** — copied from current World Builder placement.

**VERIFIED** — tested in game.

**LOCKED** — should not move without coordinated migration.

---

# Facility root

```text
ANCHOR_CYN_WORLD_ORIGIN
ANCHOR_CYN_FORWARD_REFERENCE
```

Both begin TBD/UNMEASURED.

The forward reference defines the facility's canonical orientation.

---

# Room origins

```text
ANCHOR_CYN_SURFACE_ORIGIN
ANCHOR_CYN_ENTRY_ORIGIN
ANCHOR_CYN_CHECKPOINT_ORIGIN
ANCHOR_CYN_FLOODED_ORIGIN
ANCHOR_CYN_MAINT_SIDE_ORIGIN
ANCHOR_CYN_PUMP_ORIGIN
ANCHOR_CYN_SECURITY_ORIGIN
ANCHOR_CYN_SECURITY_OFFICE_ORIGIN
ANCHOR_CYN_BIOMETRIC_ORIGIN
ANCHOR_CYN_OBSERVATION_ORIGIN
ANCHOR_CYN_SUBJECT_RECORDS_ORIGIN
ANCHOR_CYN_ARCHIVE_ORIGIN
ANCHOR_CYN_PURGE_ORIGIN
ANCHOR_CYN_PREDICTION_ORIGIN
ANCHOR_CYN_ECHO_ORIGIN
ANCHOR_CYN_COFFINS_ORIGIN
ANCHOR_CYN_COMPARISON_ORIGIN
ANCHOR_CYN_SERVERS_ORIGIN
ANCHOR_CYN_CORE_ANTE_ORIGIN
ANCHOR_CYN_CORE_ORIGIN
ANCHOR_CYN_ENDING_ORIGIN
ANCHOR_CYN_ESCAPE_ORIGIN
```

Every origin remains TBD until copied from the actual level.

---

# Main connection anchors

```text
ANCHOR_CYN_SURFACE_TO_ENTRY
ANCHOR_CYN_ENTRY_TO_CHECKPOINT
ANCHOR_CYN_CHECKPOINT_TO_FLOODED
ANCHOR_CYN_FLOODED_TO_PUMP
ANCHOR_CYN_PUMP_TO_SECURITY
ANCHOR_CYN_SECURITY_TO_BIOMETRIC
ANCHOR_CYN_BIOMETRIC_TO_OBSERVATION
ANCHOR_CYN_OBSERVATION_TO_ARCHIVE
ANCHOR_CYN_ARCHIVE_TO_PREDICTION
ANCHOR_CYN_PREDICTION_TO_COFFINS
ANCHOR_CYN_COFFINS_TO_COMPARISON
ANCHOR_CYN_COMPARISON_TO_SERVERS
ANCHOR_CYN_SERVERS_TO_CORE_ANTE
ANCHOR_CYN_CORE_ANTE_TO_CORE
ANCHOR_CYN_CORE_TO_ENDING
ANCHOR_CYN_ENDING_TO_ESCAPE
```

Optional side routes get separate anchors rather than overloading the main connection.

---

# Surface / entry anchors

```text
ANCHOR_CYN_SURFACE_APPROACH
ANCHOR_CYN_MAIN_ENTRY
ANCHOR_CYN_VENT_ENTRY
ANCHOR_CYN_SURFACE_EXIT
ANCHOR_CYN_SURFACE_MARKER
ANCHOR_CYN_ENTRY_MAIN_IN
ANCHOR_CYN_ENTRY_VENT_IN
ANCHOR_CYN_ENTRY_MERGE
ANCHOR_CYN_ENTRY_CHECKPOINT_VIEW
```

---

# Checkpoint anchors

```text
ANCHOR_CYN_CHECKPOINT_ENTRY
ANCHOR_CYN_CHECKPOINT_BREAKER
ANCHOR_CYN_CHECKPOINT_BREAKER_PLAYER
ANCHOR_CYN_CHECKPOINT_TERMINAL
ANCHOR_CYN_CHECKPOINT_CAMERA
ANCHOR_CYN_CHECKPOINT_SHUTTER
ANCHOR_CYN_CHECKPOINT_EXIT
```

---

# Flooded / maintenance anchors

```text
ANCHOR_CYN_FLOOD_ENTRY
ANCHOR_CYN_FLOOD_HAZARD
ANCHOR_CYN_FLOOD_BYPASS_ENTRY
ANCHOR_CYN_FLOOD_BYPASS_EXIT
ANCHOR_CYN_FLOOD_ECHO_LOOK
ANCHOR_CYN_FLOOD_EXIT
ANCHOR_CYN_MAINT_TERMINAL
```

---

# Pump anchors

```text
ANCHOR_CYN_PUMP_ENTRY
ANCHOR_CYN_PUMP_PRELOAD
ANCHOR_CYN_PUMP_WAKE
ANCHOR_CYN_PUMP_DEVICE
ANCHOR_CYN_PUMP_GAUGE
ANCHOR_CYN_PUMP_TERMINAL
ANCHOR_CYN_PUMP_AUDIO_MOTOR
ANCHOR_CYN_PUMP_AUDIO_PISTONS
ANCHOR_CYN_PUMP_AUDIO_DRAIN
ANCHOR_CYN_PUMP_EXIT
```

Hero object:
```text
CYN_OBJ_PUMP_01
Asset: CYN_ASSET_PUMP
Parent: ANCHOR_CYN_PUMP_DEVICE
Position: TBD
Rotation: TBD
Scale: 1,1,1
Pivot: base-center preferred
Status: UNMEASURED
```

Document piston sweep as a separate exclusion volume.

---

# Security anchors

```text
ANCHOR_CYN_SECURITY_ENTRY
ANCHOR_CYN_SECURITY_ENCOUNTER_CENTER
ANCHOR_CYN_SECURITY_BYPASS_ENTRY
ANCHOR_CYN_SECURITY_BYPASS_EXIT
ANCHOR_CYN_SECURITY_CAMERA_A
ANCHOR_CYN_SECURITY_CAMERA_B
ANCHOR_CYN_SECURITY_CAMERA_C
ANCHOR_CYN_SECURITY_OFFICE_DOOR
ANCHOR_CYN_SECURITY_EXIT
ANCHOR_CYN_SECURITY_OFFICE_ENTRY
ANCHOR_CYN_SECURITY_LOG_PLAYER
ANCHOR_CYN_SECURITY_LOG_SCREEN
ANCHOR_CYN_SECURITY_RECENT_CLUE
```

For every camera record:
```text
position
rotation
yaw_min
yaw_max
pitch_min
pitch_max
tracking_radius
default_state
```

---

# Biometric anchors

```text
ANCHOR_CYN_BIOMETRIC_ENTRY
ANCHOR_CYN_BIOMETRIC_READER
ANCHOR_CYN_BIOMETRIC_PLAYER
ANCHOR_CYN_BIOMETRIC_SCREEN
ANCHOR_CYN_ARCHIVE_GATE
ANCHOR_CYN_POST_BIOMETRIC
ANCHOR_CYN_BIOMETRIC_EXIT
```

Reader mapping:
```text
Object: CYN_OBJ_READER_01
Asset: CYN_ASSET_FIA_READER
Player Anchor: ANCHOR_CYN_BIOMETRIC_PLAYER
Look Target: CYN_LOOK_BIOMETRIC_SCREEN
Scale: 1,1,1
Position/Rotation: TBD
```

Desired interaction distance ~0.7–1.0 m, subject to real fit.

---

# Observation anchors

```text
ANCHOR_CYN_OBSERVATION_ENTRY
ANCHOR_CYN_OBSERVATION_CHAIR
ANCHOR_CYN_OBSERVATION_CHAIR_PLAYER
ANCHOR_CYN_OBSERVATION_CHAIR_LOOK
ANCHOR_CYN_OBSERVATION_WINDOW
ANCHOR_CYN_SUBJECT_RECORDS_TERMINAL
ANCHOR_CYN_MARA_OVERRIDE_TERMINAL
ANCHOR_CYN_OBSERVATION_EXIT
ANCHOR_MARA_OBSERVATION
```

---

# Archive anchors

```text
ANCHOR_CYN_ARCHIVE_ENTRY
ANCHOR_CYN_ARCHIVE_RACK_A
ANCHOR_CYN_ARCHIVE_RACK_B
ANCHOR_CYN_ARCHIVE_RACK_C
ANCHOR_CYN_SLOT_1140
ANCHOR_CYN_SLOT_1140_PLAYER
ANCHOR_CYN_SLOT_1179
ANCHOR_CYN_SLOT_1179_PLAYER
ANCHOR_CYN_PURGE_ROOM_ENTRY
ANCHOR_CYN_BLINKING_CART
ANCHOR_CYN_ARCHIVE_EXIT
ANCHOR_CYN_PURGE_ENTRY
ANCHOR_CYN_DESTROYED_CART_A
ANCHOR_CYN_DESTROYED_CART_B
ANCHOR_CYN_DESTROYED_CART_C
ANCHOR_CYN_BLINKING_CART_PLAYER
```

If slot 1140 is part of the rack asset, prefer local transform relative to `CYN_OBJ_STORAGE_RACK_A`.

---

# Prediction anchors

```text
ANCHOR_CYN_PREDICTION_ENTRY
ANCHOR_CYN_PREDICTION_COUNTER
ANCHOR_CYN_COUNTER_PLAYER
ANCHOR_CYN_PROJECTOR
ANCHOR_CYN_PROJECTOR_PLAYER
ANCHOR_CYN_PROJECTOR_VOLUME_CENTER
ANCHOR_CYN_PREDICTION_EXIT
```

Projector registry must store:
- world transform
- projection origin
- visualization radius/height
- player anchor
- status

Projected volume has collision OFF.

---

# Echo anchors

```text
ANCHOR_CYN_ECHO_ENTRY
ANCHOR_CYN_ECHO_SCANNER
ANCHOR_CYN_ECHO_SCANNER_PLAYER
ANCHOR_CYN_ECHO_DISPLAY
ANCHOR_CYN_ECHO_EXIT
```

---

# Coffin anchors

```text
ANCHOR_CYN_COFFINS_ENTRY
ANCHOR_CYN_COFFIN_1140
ANCHOR_CYN_COFFIN_1140_PLAYER
ANCHOR_CYN_COFFIN_1137
ANCHOR_CYN_COFFIN_1139
ANCHOR_CYN_COFFIN_1141
ANCHOR_CYN_COFFIN_AUDIO
ANCHOR_CYN_COFFIN_AUDIO_EMITTER
ANCHOR_CYN_COFFINS_EXIT
```

0-1140 mapping:
```text
Object: CYN_OBJ_COFFIN_1140
Asset: CYN_ASSET_BRANCH_COFFIN
Door State: OPEN
Player Anchor: ANCHOR_CYN_COFFIN_1140_PLAYER
Look Target: CYN_LOOK_COFFIN_1140
Position/Rotation: TBD
Scale: 1,1,1
```

---

# Comparison anchors

```text
ANCHOR_CYN_COMPARISON_ENTRY
ANCHOR_CYN_COMPARISON_DEVICE
ANCHOR_CYN_COMPARISON_PLAYER
ANCHOR_CYN_COMPARISON_SOURCE_PANEL
ANCHOR_CYN_COMPARISON_INSTANCE_PANEL
ANCHOR_CYN_COMPARISON_LOOK
ANCHOR_CYN_COMPARISON_EXIT
```

Record that both Source and Instance panels are visible from the player scan position.

---

# Server vault anchors

```text
ANCHOR_CYN_SERVERS_ENTRY
ANCHOR_CYN_SERVER_GROUP_A
ANCHOR_CYN_SERVER_GROUP_B
ANCHOR_CYN_SERVER_GROUP_C
ANCHOR_CYN_SERVER_WAKE_A
ANCHOR_CYN_SERVER_WAKE_B
ANCHOR_CYN_SERVER_WAKE_C
ANCHOR_CYN_SERVER_MIDPOINT
ANCHOR_CYN_ASHCACHE_TERMINAL
ANCHOR_CYN_ASHCACHE_PLAYER
ANCHOR_CYN_SERVERS_EXIT
```

Each server group should store:
```text
origin
rotation
spacing_x
spacing_y
rows
columns
LOD strategy
wake group
```

---

# Core antechamber anchors

```text
ANCHOR_CYN_CORE_ANTE_ENTRY
ANCHOR_CYN_CONTINUITY_DOOR
ANCHOR_CYN_CONTINUITY_PLAYER
ANCHOR_CYN_CONTINUITY_AUDIO
ANCHOR_CYN_CORE_AUTH
ANCHOR_CYN_CORE_AUTH_PLAYER
ANCHOR_CYN_CORE_MAIN_DOOR
ANCHOR_CYN_CORE_ANTE_EXIT
```

Continuity door:
```text
Asset: CYN_ASSET_CONTINUITY_DOOR
Scale: 1,1,1
Audio anchor behind door
Position/Rotation: TBD
```

---

# Core anchors

```text
ANCHOR_CYN_CORE_ENTRY
ANCHOR_CYN_CORE_TRIGGER
ANCHOR_CYN_CORE_CENTER
ANCHOR_CYN_CORE_TERMINAL
ANCHOR_CYN_CORE_TERMINAL_PLAYER
ANCHOR_CYN_CORE_CAMERA_A
ANCHOR_CYN_CORE_CAMERA_B
ANCHOR_CYN_CORE_COOLANT_A
ANCHOR_CYN_CORE_COOLANT_B
ANCHOR_CYN_CORE_SERVER_A
ANCHOR_CYN_CORE_SERVER_B
ANCHOR_CYN_CORE_EXIT_TO_ENDING
ANCHOR_MARA_CORE
```

Core mapping:
```text
Object: CYN_OBJ_CORE
Asset: CYN_ASSET_PREDICTIVE_CORE
Anchor: ANCHOR_CYN_CORE_CENTER
Scale: 1,1,1
Position/Rotation: TBD
```

Record animated sweep radius, clearance radius, and whether the core is visible from the trigger center.

Core terminal:
```text
Position/Rotation: TBD
Player Anchor: ANCHOR_CYN_CORE_TERMINAL_PLAYER
Look Target: CYN_LOOK_CORE_TERMINAL
Distance from Core: TBD
```

---

# Ending anchors

```text
ANCHOR_CYN_ENDING_ENTRY
ANCHOR_CYN_FINAL_CONSOLE
ANCHOR_CYN_FINAL_PLAYER
ANCHOR_CYN_FINAL_CORE_VIEW
ANCHOR_CYN_ENDING_EXIT
```

From `ANCHOR_CYN_FINAL_PLAYER`, the core should remain visible where practical.

---

# Escape anchors

```text
ANCHOR_CYN_ESCAPE_ENTRY
ANCHOR_CYN_ESCAPE_CALLBACK
ANCHOR_CYN_ESCAPE_ELEVATOR_DOOR
ANCHOR_CYN_ESCAPE_ELEVATOR_PLAYER
ANCHOR_CYN_ESCAPE_ELEVATOR_INTERIOR
ANCHOR_CYN_ESCAPE_ELEVATOR_EXIT
ANCHOR_CYN_SURFACE_EXIT
```

---

# Debug teleports

```text
CYN_TP_SURFACE
CYN_TP_ENTRY
CYN_TP_CHECKPOINT
CYN_TP_FLOODED
CYN_TP_PUMP
CYN_TP_SECURITY
CYN_TP_BIOMETRIC
CYN_TP_OBSERVATION
CYN_TP_ARCHIVE
CYN_TP_PREDICTION
CYN_TP_ECHO_ANALYSIS
CYN_TP_COFFINS
CYN_TP_COMPARISON
CYN_TP_SERVER_VAULT
CYN_TP_CORE_ANTE
CYN_TP_CORE
CYN_TP_ENDING
CYN_TP_ESCAPE
CYN_TP_SURFACE_EXIT
```

Every teleport needs:
- clear floor
- safe headroom
- useful facing
- no collision overlap
- no accidental trigger overlap unless intended

---

# Trigger transform schema

Every trigger stores:
```text
Trigger ID
Room
Center XYZ
Rotation yaw/pitch/roll
Dimensions XYZ
Shape
Entry direction
One-shot
Repair trigger
Status
Verified build
Notes
```

All values remain TBD until measured.

---

# Interaction mapping

Canonical pattern:
```text
Interaction ID
→ World Object
→ Player Anchor
→ Look Target
→ Radius
→ Status
```

Examples:
```text
CYN_INT_BIOMETRIC_READER
→ CYN_OBJ_READER_01
→ ANCHOR_CYN_BIOMETRIC_PLAYER
→ CYN_LOOK_BIOMETRIC_SCREEN

CYN_INT_COMPARISON_APPARATUS
→ CYN_OBJ_COMPARISON
→ ANCHOR_CYN_COMPARISON_PLAYER
→ CYN_LOOK_COMPARISON_SCREEN

CYN_INT_CORE_TERMINAL
→ CYN_OBJ_CORE_TERMINAL
→ ANCHOR_CYN_CORE_TERMINAL_PLAYER
→ CYN_LOOK_CORE_TERMINAL
```

---

# Look targets

```text
CYN_LOOK_SIGN
CYN_LOOK_FLOODED_CORRIDOR
CYN_LOOK_PUMP_GAUGE
CYN_LOOK_PUMP_BODY
CYN_LOOK_CAMERA_A
CYN_LOOK_BIOMETRIC_SCREEN
CYN_LOOK_OBSERVATION_CHAIR
CYN_LOOK_SLOT_1140
CYN_LOOK_SLOT_1179
CYN_LOOK_PREDICTION_COUNTER
CYN_LOOK_BRANCH_TREE
CYN_LOOK_ECHO_SCANNER
CYN_LOOK_COFFIN_1140
CYN_LOOK_COMPARISON_SCREEN
CYN_LOOK_SERVER_ROWS
CYN_LOOK_ASHCACHE_TERMINAL
CYN_LOOK_CONTINUITY_DOOR
CYN_LOOK_CORE
CYN_LOOK_CORE_TERMINAL
CYN_LOOK_FINAL_CONSOLE
CYN_LOOK_MARA
```

Use local-space targets for subcomponents attached to machines where supported; world-space for rooms, triggers, scene anchors, and teleports.

---

# Audio anchors

```text
ANCHOR_SFX_PUMP_MOTOR
ANCHOR_SFX_PUMP_PISTONS
ANCHOR_SFX_DRAINAGE
ANCHOR_SFX_CAMERA_A
ANCHOR_SFX_COFFIN_AUDIO
ANCHOR_SFX_SERVER_GROUP_A
ANCHOR_SFX_SERVER_GROUP_B
ANCHOR_SFX_SERVER_GROUP_C
ANCHOR_SFX_CONTINUITY
ANCHOR_SFX_CORE_COOLANT
ANCHOR_SFX_CORE_HUM
ANCHOR_SFX_CORE_ROTATION
ANCHOR_SFX_ESCAPE_ELEVATOR
```

For each store min/max radius, occlusion, loop flag, attachment, and status.

---

# Lighting anchors

```text
ANCHOR_LGT_PUMP_WARNING
ANCHOR_LGT_ARCHIVE_WAKE_A
ANCHOR_LGT_ARCHIVE_WAKE_B
ANCHOR_LGT_PROJECTOR
ANCHOR_LGT_SERVER_WAKE_A
ANCHOR_LGT_SERVER_WAKE_B
ANCHOR_LGT_SERVER_WAKE_C
ANCHOR_LGT_CORE_FLOOR_A
ANCHOR_LGT_CORE_FLOOR_B
ANCHOR_LGT_CORE_PROCESSOR
ANCHOR_LGT_FINAL_CONSOLE
```

---

# Streaming boundaries

```text
ANCHOR_STREAM_A_B
ANCHOR_STREAM_B_C
ANCHOR_STREAM_C_D
ANCHOR_STREAM_D_E
ANCHOR_STREAM_E_F
ANCHOR_STREAM_F_G
ANCHOR_STREAM_G_H
```

Store:
```text
position
orientation
preload distance
source stream group
destination stream group
```

---

# Hero pivot requirements

| Asset | Pivot |
|---|---|
| Splinter | geometric center/insertion reference |
| Cradle | base center |
| Personality Rack | floor/base center |
| Branch Projector | floor center |
| Observation Chair | floor center under seat |
| Server Module | floor center |
| Pump | base center |
| Shutdown Console | base center |
| Archive Scanner | base center |
| FIA Reader | mount/base center |
| Continuity Door | frame center/hinge system |
| Prediction Counter | base or wall-mount center |
| Camera Head | mount joint |
| Comparison Apparatus | base center |
| Branch Coffin | floor center |
| Predictive Core | floor center/rotational axis |

Camera asset should expose mount/yaw/pitch pivots.

Core should expose stable ring/processor pivots.

Pump should expose motor/piston/gauge pivots.

Final console should expose control pivots.

---

# Parent/child rule

Prefer local transforms for screen/look targets and machine subcomponents.

Prefer world-space anchors for:
- room entry
- debug teleport
- trigger center
- NPC scene position
- streaming boundary
- quest marker

---

# Change policy

Moving a LOCKED anchor requires:
1. old transform
2. new transform
3. dependency review
4. interaction test
5. trigger test
6. navmesh test
7. save/load test
8. registry update

Suggested change ID:
```text
CYN-XFORM-###
```

---

# World Builder workflow

```text
1 select object/anchor
2 copy exact transform
3 paste into this registry/JSON
4 mark MEASURED
5 launch game
6 verify
7 mark VERIFIED
8 mark LOCKED only after local layout stabilizes
```

---

# Claude coordinate rule

Claude must never invent real-looking coordinates.

If unavailable:
```text
Position: TBD
```

Relative design relationships are allowed, e.g.:
```text
camera ~3 m above floor
pump wake trigger ~5–7 m into room
core trigger ~4–6 m into chamber
reader player anchor ~0.8 m from device
```

These are design constraints, not final transforms.

---

# Debug transform tools

Recommended:
```text
ash.cyn.debug.anchors 1
ash.cyn.xform <ID>
ash.cyn.anchor.nearest
ash.cyn.anchor.tp <ID>
```

---

# Validation

Detect:
- TBD/null transform used in release
- NaN
- extreme scale
- invalid rotation
- anchor below floor
- debug teleport inside collision
- zero-size mandatory trigger
- interaction anchor too far from device
- duplicate anchor IDs

Mandatory release data may not remain TBD for:
- room origins
- mandatory triggers
- mandatory interaction anchors
- hero transforms
- release-used debug teleports
- escape elevator
- surface completion

---

# Useful placement constraints

Not final coordinates:

```text
wall terminal center ~1.2–1.5 m above floor
biometric reader ~1.1–1.4 m
camera ~2.8–3.5 m
prediction counter ~2.5–4 m if elevated
normal interaction target ~1.0–1.5 m
large-machine interaction ~1.0–1.6 m
```

Player interaction anchor:
```text
~0.8 m width
~2.1 m headroom
no door sweep
no moving geometry
```

NPC anchor:
```text
~0.6–0.8 m clear radius minimum
```

---

# Critical spatial constraints

Core:
- terminal 2–4 m away
- entry trigger 4–6 m into chamber
- walkway >=2.5 m
- animation exclusion documented
- final console should retain core sight line

Projector:
- clear projection volume
- interaction outside arm sweep
- walk-around possible
- visible from approach

Server vault:
- sequential wake triggers
- activation ahead of player
- path >=1.8 m
- far fake geometry inaccessible

Continuity:
- visible but not mandatory blocker
- clear interaction area
- audio behind door
- no core-door interference

Biometric:
- reader before gate
- screen visible
- gate safe
- post-gate repair trigger cannot fire early

Pump:
- visible dead before wake
- trigger not at threshold
- gauge readable
- piston sweep inaccessible
- exit remains clear

---

# Machine-readable companion

Use:
```text
CYNOSURE_TRANSFORMS.json
```

Unknown coordinates use JSON `null`, never `0`.

Optional CSV columns:
```text
id,type,room,x,y,z,yaw,pitch,roll,scale_x,scale_y,scale_z,parent,status,verified_build
```

---

# Drift detection

Suggested warning thresholds:
```text
interaction position delta > 0.10 m
hero asset position delta > 0.25 m
interaction/camera rotation delta > 5°
locked hero rotation delta > 2°
hero scale delta > 1%
```

Undocumented room-origin movement should always warn.

---

# Anchor locking order

```text
1 room origins
2 doorway connections
3 hero asset positions
4 mandatory interaction anchors
5 mandatory triggers
6 NPC scene anchors
7 cameras
8 audio anchors
9 optional interactions
10 decorative anchors
```

## Final principle

Do not scatter raw coordinates through scripts.

Bad:
```text
TeleportPlayer(1283.77, -482.19, 37.55)
```

Good:
```text
TeleportPlayer(CYN_TP_CORE)
```

The anchor system separates **what the quest means** from **where the world currently places it**.
