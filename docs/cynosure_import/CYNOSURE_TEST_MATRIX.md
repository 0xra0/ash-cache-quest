# CYNOSURE_TEST_MATRIX.md

# Ash Cache — Cynosure Test Matrix

## Purpose

Defines repeatable functional, narrative, persistence, performance, and regression tests for the Cynosure section of Ash Cache.

A test passes only when both canonical quest state and visible world state are correct.

## Result values

```text
PASS
FAIL
BLOCKED
NOT_RUN
EXPECTED_ISSUE
```

Failed tests should record build, test ID, save, room, phase, reproduction steps, expected/actual results, relevant facts, logs, and screenshots/video when useful.

## Priority

```text
P0 release blocking
P1 major
P2 optional/polish
P3 cosmetic
```

## Baseline fresh state

All Cynosure-owned facts are zero before start. See `CYNOSURE_FACTS.md`.

---

# Entry / Start

## CYN-T001 — Start Cynosure — P0

Setup:
```text
ash_splinter_acquired = 1
ash_cynosure_started = 0
```

Expected:
```text
ash_cynosure_started = 1
ash_cyn_phase = 10
```

Objective:
`Find the old Cynosure facility.`

## CYN-T002 — Start Cannot Duplicate — P1

Trigger start twice.

Expected:
- no duplicate objective
- no duplicate call
- no duplicate marker
- phase remains valid

## CYN-T010 — Exterior Approach — P0

Cross `CYN_TRG_EXTERIOR_APPROACH`.

Expected:
```text
ash_cynosure_entrance_found = 1
```

Objective:
`Find a way into Cynosure.`

## CYN-T011 — Backward Crossing — P1

Cross approach trigger, leave, re-enter.

Expected: no replay/reset.

## CYN-T020 — Main Entry — P0

Use `CYN_INT_SERVICE_HATCH`.

Expected:
```text
ash_entry_main = 1
ash_entry_vent = 0
ash_cynosure_entered = 1
ash_cyn_phase = 20
```

## CYN-T021 — Vent Entry — P0

Expected:
```text
ash_entry_main = 0
ash_entry_vent = 1
ash_cynosure_entered = 1
ash_cyn_phase = 20
```

## CYN-T022 — Route Exclusivity — P1

Second route must not overwrite established canonical route.

## CYN-T023 — Entry Merge Repair — P0

Debug-enter with no route facts, cross `CYN_TRG_ENTRY_MERGE`.

Expected:
```text
ash_cynosure_entered = 1
ash_entry_main = 0
ash_entry_vent = 0
```

Warn that route is unknown.

## CYN-T024 / T025 — Predicted Main Entry

If main route was predicted:
- main route: no deviation
- vent route: +1 deviation exactly once

---

# Checkpoint

## CYN-T030 — Checkpoint Power — P0

Use breaker.

Expected:
```text
ash_checkpoint_power = 1
ash_world_power_stage >= 1
```

World:
- lights activate
- terminal boots
- standby camera indicator
- shutter unlocks

## CYN-T031 — Breaker Spam — P1

Repeated input produces one fact write and one sequence.

## CYN-T032 — Checkpoint Save/Load — P0

Reload after activation.

Expected:
- power fact remains
- lights/terminal/shutter restore
- sequence does not replay

## CYN-T033 — Checkpoint Bypass Repair — P0

Reach post-checkpoint with power fact 0.

Expected repair:
```text
ash_checkpoint_power = 1
```

---

# Maintenance / Pump

## CYN-T040 — Enter Maintenance — P0

Expected:
```text
ash_maintenance_entered = 1
ash_cyn_phase = 30
```

## CYN-T041 — Standard Flooded Route — P1

Disable hazard and traverse.

## CYN-T042 — Alternate Raised Route — P1

Bypass hazard and still progress.

## CYN-T043 — Echo Recognition — P1

With relevant Echo fact, recognition line plays once.

## CYN-T044 — Maintenance Log — P2

Sets `ash_maintenance_log_found = 1`; never gates completion.

## CYN-T050 — Pump Activation — P0

Cross wake trigger.

Immediate:
```text
ash_pumps_activated = 1
ash_world_power_stage = 2
```

Presentation:
- warning beacon
- gauges
- motor
- pistons
- drainage
- lights

## CYN-T051 — Leave Pump Scene Early — P0

Sprint out during startup.

Expected: persistent running state resolves correctly.

## CYN-T052 — Save During Pump Startup — P0

Reload after canonical fact set.

Expected:
- pump RUNNING
- water DRAINED
- lights active
- startup does not replay

## CYN-T053 — Pump Re-entry — P1

No duplicate startup.

---

# Security / Cameras

## CYN-T060 — Security Entry — P0

Expected:
```text
ash_cyn_phase = 40
ash_world_power_stage = 3
```

## CYN-T061 — Combat Resolution — P1

Expected:
```text
ash_security_resolution = 1
ash_security_combat_resolved = 1
```

## CYN-T062 — Security Bypass — P0

Expected:
```text
ash_security_resolution = 2
```

If combat was predicted, deviation +1 exactly once.

## CYN-T063 — Partial Combat Then Bypass — P1

Quest progresses without exact kill count.

## CYN-T064 — Enemy Stuck / Leaves Area — P1

Merge/failsafe still allows progression.

## CYN-T070 — First Camera Wake — P0

Expected:
```text
ash_camera_first_move = 1
ash_camera_tracking_enabled = 1
```

No combat alarm.

## CYN-T071 — Camera Limits — P2

No impossible 360° rotation or snapping.

## CYN-T072 — Through-Wall Camera — P2

Prefer LOS-aware tracking; at minimum avoid obvious impossible behavior.

## CYN-T073 — Camera Save/Load — P1

Tracking restores without replaying reveal.

## CYN-T074 — Recent Visitor Log — P2

Sets:
```text
ash_recent_visitor_found = 1
ash_knows_recent_visitor = 1
```

No identity assignment.

---

# Biometric Gate

## CYN-T080 — Biometric Reader — P0

Expected:
```text
ash_biometric_scanned = 1
ash_biometric_1140_match = 1
```

Display:
```text
IDENTITY UNKNOWN
SEARCHING LEGACY RECORDS
MATCH FOUND
SUBJECT 0-1140
ACCESS CONTINUITY
```

Gate unlocks.

## CYN-T081 — Interaction Spam — P1

One scan, one fact write, one unlock.

## CYN-T082 — Save During Scan — P0

Reload into completed/accessible state.

## CYN-T083 — Gate Bypass Repair — P0

Teleport behind gate with facts 0, cross repair trigger.

Expected scan/match repaired.

---

# Observation / Research

## CYN-T090 — Observation Entry — P0

Expected:
```text
ash_research_entered = 1
ash_cyn_phase = 50
```

## CYN-T091 — Observation Chair — P1

Sets `ash_observation_chair_found = 1`.

No early Source 0 reveal.

## CYN-T092 — Subject Records — P2

May show:
```text
SOURCE 0 — 94%
```

Must not identify Source 0 as V yet.

## CYN-T093 — Mara Override — P2

Sets override evidence only; does not set Mara-removal knowledge.

---

# Archive

## CYN-T100 — Archive Entry — P0

Expected:
```text
ash_archive_entered = 1
ash_cyn_phase = 60
ash_world_power_stage = 4
```

## CYN-T101 — 0-1140 Slot — P0

Expected:
```text
ash_slot_1140_found = 1
ash_knows_1140_came_from_cynosure = 1
```

Display instance/status/removal evidence.

## CYN-T102 — Skip Optional Archive Content — P0

Main route works after 0-1140 discovery only.

## CYN-T103 — Destroyed Cartridge — P2

Sets optional discovery.

## CYN-T104 — Blinking Cartridge — P2

Sets ambiguous hint; no definitive consciousness fact.

## CYN-T105 — 0-1179 Slot — P2

Sets second-missing-slot knowledge, no mandatory objective, no explanation.

---

# Prediction Hall

## CYN-T110 — Prediction Entry — P0

Expected:
```text
ash_prediction_entered = 1
ash_cyn_phase = 70
ash_world_power_stage = 5
```

## CYN-T111 — Prediction Counter — P1

Displays:
```text
GENERATED 031884
STABLE 000217
RETAINED 000001
```

## CYN-T112 — Counter Optionality — P0

Skipping counter does not block progression.

## CYN-T113 — Branch Projector — P0

Expected:
```text
ash_branch_projector_used = 1
```

Projection collapses toward `SOURCE 0`.

## CYN-T114 — High-Deviation Visual — P2

More instability only; no progression change.

## CYN-T115 — Projector Save/Load — P1

Restore post-analysis state.

## CYN-T116 — Echo Scanner: 0 Echoes — P0

Fallback metadata analysis works.

## CYN-T117 — Echo Scanner: 1 Echo — P1

Fragment analysis works.

## CYN-T118 — Echo Scanner: 6 Echoes — P1

Sets:
```text
ash_all_echoes_scanned = 1
```

Displays branch completeness.

---

# Branch Coffins

## CYN-T120 — 0-1140 Coffin — P0

Expected:
```text
ash_branch_coffin_found = 1
ash_knows_1140_is_predictive_branch = 1
```

Display:
```text
COGNITIVE CONTINUITY UNIT
BIOLOGICAL CAPACITY NONE
SOURCE 0
BRANCH 1140
STATUS REMOVED
```

## CYN-T121 — Mystery Coffin Audio — P2

Ambiguous only; no definitive consciousness claim.

---

# Comparison

## CYN-T130 — Comparison Entry — P0

Expected:
```text
ash_comparison_entered = 1
ash_cyn_phase = 80
```

## CYN-T131 — Source 0 Reveal — P0

Expected:
```text
ash_v_identity_match = 1
ash_knows_v_is_source = 1
```

Display:
```text
SOURCE 0
INSTANCE 1140
CONTINUITY MATCH 91.3%
DIVERGENCE 8.7%
```

## CYN-T132 — Source Reveal Save/Load — P0

Completed state restores; exit available.

## CYN-T133 — Reveal Order Protection — P0

Nothing earlier may directly state `SOURCE 0 IS V`.

---

# Server Vault

## CYN-T140 — Server Vault Entry — P0

Expected:
```text
ash_server_vault_entered = 1
ash_world_power_stage = 6
```

## CYN-T141 — Wake Direction — P2

Groups wake ahead of V, not random full-room flicker.

## CYN-T142 — ASH Definition — P1

Sets `ash_ashcache_meaning_known = 1`.

Definition must not claim every branch was conscious.

## CYN-T143 — Skip ASH Terminal — P0

Quest remains completable.

---

# Core Antechamber

## CYN-T150 — Enter Antechamber — P0

Expected:
```text
ash_core_ante_entered = 1
ash_cyn_phase = 90
```

## CYN-T151 — Continuity Normal — P2

`ACCESS DENIED`, door closed.

## CYN-T152 — Continuity with 6 Echoes — P2

`SOURCE VERIFIED / ACCESS DEFERRED`, door closed.

## CYN-T153 — Continuity High Deviation — P2

`SOURCE UNRESOLVED / ACCESS DEFERRED`, door closed.

## CYN-T154 — Door Cannot Open — P0

Test every state. It never opens in Ash Cache.

## CYN-T155 — Core Authorization — P0

Expected:
```text
ash_core_authorized = 1
```

Display:
```text
WELCOME BACK
0-1140
```

---

# Core

## CYN-T160 — Core Entry — P0

Immediate:
```text
ash_core_entered = 1
ash_core_activated = 1
ash_world_power_stage = 7
```

## CYN-T161 — Save During Core Wake — P0

Reload into active, usable core. No relock or replay.

## CYN-T162 — Authorization Repair — P0

Debug-enter with auth 0; repair auth and continue.

## CYN-T170 — Core Truth — P0

Expected:
```text
ash_truth_1140_known = 1
```

Display canonical Project Continuity fields and self-awareness confirmation.

## CYN-T171 — Self-Awareness Reveal Order — P0

No earlier source may definitively confirm self-awareness.

---

# Mara

## CYN-T172 — Alive / Low Trust — P1
## CYN-T173 — Alive / Medium Trust — P1
## CYN-T174 — Alive / High Trust — P1

All must eventually set:
```text
ash_mara_confession = 1
ash_knows_mara_removed_1140 = 1
```

## CYN-T175 — Mara Dead — P0

Fallback:
```text
ash_mara_archive_reveal = 1
ash_knows_mara_removed_1140 = 1
```

No wait for Mara.

## CYN-T176 — Override Evidence Callback — P2

Earlier evidence changes wording, not mandatory progression.

---

# Prediction Deviation

## CYN-T180 — 0 → LOW — P1
## CYN-T181 — 2 → MEDIUM — P1
## CYN-T182 — 4 → HIGH — P1
## CYN-T183 — 1 boundary → LOW — P1
## CYN-T184 — 3 boundary → MEDIUM — P1
## CYN-T185 — 7 boundary → HIGH — P1

## CYN-T186 — Duplicate Event — P0

Same event can increment only once.

## CYN-T187 — Counter Post-Reveal — P2

May show `RETAINED 000002`.

---

# Final Console / Endings

## CYN-T190 — Enable Final Console — P0

Expected:
```text
ash_final_console_enabled = 1
ash_cyn_phase = 100
```

## CYN-T191 — Cannot Activate Early — P0

No ending choices before truth.

## CYN-T200 — Destroy — P0

Expected ending ID 1, Destroy compatibility flag only, post-state 1, escape started.

## CYN-T201 — Absorb — P0

Expected ending ID 2, `ash_1140_in_v = 1`, post-state 2, escape started.

## CYN-T202 — Blue Eyes — P0

Expected ending ID 3, unknown remote credential, escape started.

## CYN-T203 — Hide — P0

Expected ending ID 4, severed links/location unknown/prediction continues, escape started.

## CYN-T204 — Ending Exclusivity — P0

Second ending unavailable.

## CYN-T205 — Ending Spam — P0

Only first valid commit succeeds.

## CYN-T206 — Save Immediately After Commit — P0

Reload restores canonical ending, post-state, and exit.

## CYN-T207 — Compatibility Repair — P1

Canonical ending ID repairs contradictory compatibility booleans.

---

# Escape / Completion

## CYN-T210 — Escape Route — P0

Service exit and elevator available; no full dungeon backtracking.

## CYN-T211 — Escape Elevator — P0

No stuck transition.

## CYN-T212–215 — Ending-Specific Escape Callbacks — P2

Destroy: instance-count hint.
Absorb: reader reacts to Source.
Blue Eyes: record erased.
Hide: offline camera may track briefly.

## CYN-T220 — Surface Completion — P0

Expected:
```text
ash_cynosure_complete = 1
ash_cyn_phase = 120
```

## CYN-T221 — Completion Requires Ending — P0

Cannot falsely complete with ending ID 0.

---

# Re-entry

## CYN-T230 — Destroy — P1
Core mostly dark; servers off; Continuity sealed.

## CYN-T231 — Absorb — P1
Readers react to V; selected devices auto-wake.

## CYN-T232 — Blue Eyes — P1
Selected files/logs erased with no explicit ownership label.

## CYN-T233 — Hide — P1
Network isolated; most cameras dormant; intermittent signaling.

---

# Leave / Return

## CYN-T240 — Leave after Archive — P0
Phase/power/reveals persist.

## CYN-T241 — Leave after Prediction — P1
Projector stays post-use.

## CYN-T242 — Leave after Core Wake — P0
Core remains active; truth terminal available.

---

# Debug / Validator

## CYN-T250 — Teleport Archive --setup — P1
## CYN-T251 — Teleport Core --setup — P1
## CYN-T252 — Ending Preset — P1

Presets apply only minimum prerequisites.

## CYN-T260 — Invalid Phase — P1
Value 77 must error.

## CYN-T261 — Invalid Ending — P1
Value 9 must error.

## CYN-T262 — Invalid Deviation — P1
Value 9 must error or clamp only under explicit repair.

## CYN-T263 — Complete Without Ending — P0
Must error.

## CYN-T264 — Repair Ending Escape — P0
Ending >0 repairs selected/escape.

## CYN-T265 — Repair Core Authorization — P1
Core-entered repairs authorization with log.

## CYN-T266 — Do Not Guess Entry Route — P1
Entered with both route facts zero remains route-unknown.

---

# Dialogue / Localization

## CYN-T270 — Mandatory vs Ambient — P1
Mandatory scene wins.

## CYN-T271 — Johnny/Mara Collision — P1
Priority prevents overlap.

## CYN-T272 — Dialogue Lock Reload — P1
Stale session lock cannot permanently suppress dialogue.

## CYN-T280 — English — P1
No raw keys or placeholder strings.

## CYN-T281 — Ukrainian — P1
Verify journal, prompts, terminal text, subtitles, ending choices, and layout.

---

# Collision / Navmesh / Performance

## CYN-T290 — Pump Collision — P1
No trapping or piston overlap.

## CYN-T291 — Core Collision — P1
No invisible blockers or moving-geometry exploits.

## CYN-T292 — Storage Racks — P2
No snagging on decorative detail.

## CYN-T293 — Coffins — P2
Interactions reachable; closed units inaccessible.

## CYN-T300 — Security Navmesh — P1
AI can reach intended positions.

## CYN-T301 — Mara Pathing — P1
All physical companion scene anchors reachable.

## CYN-T310 — Server Vault Performance — P1
Measure frame rate, frame time, streaming, VRAM, and lighting cost.

## CYN-T311 — Core Wake Performance — P1
Check simultaneous lighting/animation/audio/server/camera activation.

## CYN-T312 — Camera Runtime Cost — P2
Off-room cameras do not run expensive tracking.

---

# Narrative Mystery Regression

P0 narrative checks:

- opening caller remains unidentified
- current Cynosure controller remains unresolved
- 0-1179 remains unexplained
- Continuity door remains sealed/unexplained
- only 0-1140 self-awareness is explicit
- prediction is not stated as deterministic metaphysical truth

---

# Full Regression Suites

## CYN-R001 — Minimum Route — P0

```text
0 Echoes
Mara dead
Johnny unavailable
main entrance
security bypass
no optional clues
low deviation
```

Must finish.

## CYN-R002 — Full Investigation — P0

```text
6 Echoes
Mara alive / trust 3
vent entry
all optional logs
security bypass
0-1179 found
destroyed cartridge found
recent visitor found
Continuity checked
high deviation
```

Must finish.

## CYN-R003 — Combat Route — P0

Mara alive, 3 Echoes, main entry, security combat, medium deviation. Test all endings from separate saves.

## CYN-R004 — Reload-Heavy — P0

Save/reload after every mandatory reveal through ending/escape.

## CYN-R005 — Alternate Routes — P0

Vent, maintenance bypass, security bypass, optional-log skip, counter skip, 0-Echo path.

## CYN-R006 — All Endings — P0

From one pre-ending save:
```text
commit
save
reload
escape
complete
re-enter
```
for each ending.

---

# Release checklist

Before release candidate:

- all P0 tests pass
- CYN-R001..R006 pass
- no progression blocker
- no double ending
- no duplicate deviation
- Mara dead path works
- 0-Echo path works
- save/load during core and ending works
- post-quest re-entry works or is intentionally disabled
- Continuity door cannot open
- protected mysteries remain protected

## Bug severity

**BLOCKER**: quest cannot continue, save corruption, ending impossible, player trapped, mandatory interaction missing, wrong ending permanently committed.

**CRITICAL**: reveal skipped/out of order, save/load destroys progression, Mara state breaks mandatory scene, ending exclusivity fails.

**MAJOR**: optional route broken, important world state wrong, major animation/dialogue issue, debug repair required during normal play.

**MINOR/COSMETIC**: small collision, optional line, lighting, decal, or text issue.

## Bug report template

```text
BUG ID:
TEST ID:
SEVERITY:
BUILD:
ROOM:
PHASE:
ENDING:
MARA STATE:
ECHO COUNT:
DEVIATION:
SAVE FILE:

STEPS:
1.
2.
3.

EXPECTED:

ACTUAL:

FACT DUMP:

LOG:

SCREENSHOT / VIDEO:

REPRODUCIBILITY:
Always / Frequent / Rare
```

## Final QA principle

The core question is whether the player can act, save, reload, take another route, miss optional content, return later, and still reach a valid ending with reveal order intact.

```text
PLAYER ACTION
→ CANONICAL FACT
→ PERSISTENT WORLD STATE
→ STORY REACTION
→ SAFE CONTINUATION
```
