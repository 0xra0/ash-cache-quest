# CYNOSURE_FACTS.md

# Ash Cache — Cynosure Quest Fact Contract

## Purpose

This file is the single source of truth for Cynosure quest state. Every quest graph, interaction, scene, REDscript helper, CET debug command, World Builder trigger, test case, and Claude session must use these canonical facts.

## Semantic types

```text
BOOL
INT
ENUM
COUNTER
COMPAT
DERIVED
DEBUG
```

BOOL uses `0=false`, `1=true`.

Persistence classes:

- **PERSISTENT** — survives save/load/restart/leaving.
- **RECONSTRUCTED** — canonical fact persists, presentation is rebuilt.
- **SESSION** — runtime helper only.
- **DEBUG_ONLY** — never required for release.

Owners:

```text
ASH_MAIN
CYN_MAIN
CYN_ENTRY
CYN_MAINT
CYN_SECURITY
CYN_RESEARCH
CYN_ARCHIVE
CYN_PREDICTION
CYN_CORE
CYN_ENDINGS
CYN_POST
EXTERNAL
DERIVED
DEBUG
```

## Global phase facts

| Fact | Type | Default | Owner | Persistent |
|---|---|---:|---|---|
| `ash_cynosure_started` | BOOL | 0 | CYN_MAIN | Yes |
| `ash_cyn_phase` | ENUM | 0 | CYN_MAIN | Yes |
| `ash_cynosure_complete` | BOOL | 0 | CYN_MAIN | Yes |

Phases:
```text
0 NOT_STARTED
10 APPROACH
20 ENTRY
30 MAINTENANCE
40 SECURITY
50 RESEARCH
60 ARCHIVE
70 PREDICTION
80 CONTINUITY
90 CORE
100 DECISION
110 ESCAPE
120 COMPLETE
```

Phase may safely advance when later mandatory evidence proves progression. Never automatically move backward.

## Entry facts

```text
ash_cynosure_entrance_found
ash_cynosure_entered
ash_entry_main
ash_entry_vent
```

Normally only one route flag is true. If entry is proven but the route is unknown, keep both route flags false rather than guessing.

Prediction support:
```text
ash_prediction_entry_expected_main
ash_prediction_event_entry_broken
```

## Maintenance facts

```text
ash_checkpoint_power
ash_maintenance_entered
ash_maintenance_log_found
ash_flood_recognition_played
ash_pumps_activated
```

`ash_checkpoint_power` reconstructs lights/terminal/shutter/camera standby.

`ash_pumps_activated` reconstructs pump RUNNING, gauge, drainage, water state, lights, and ambience.

## World power

```text
ash_world_power_stage
```

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

## Security facts

```text
ash_security_entered
ash_security_combat_started
ash_security_combat_resolved
ash_security_resolution
ash_camera_first_move
ash_camera_tracking_enabled
ash_recent_visitor_found
```

Security resolution:
```text
0 UNRESOLVED
1 COMBAT
2 BYPASS
```

Progression checks `ash_security_resolution > 0`; never exact kill count.

Prediction support:
```text
ash_prediction_security_expected_combat
ash_prediction_event_combat_broken
```

## Biometric facts

```text
ash_biometric_scanned
ash_biometric_1140_match
```

A 0-1140 match implies a scan; repair is safe in that direction.

## Research facts

```text
ash_research_entered
ash_observation_chair_found
ash_subject_records_found
ash_mara_override_record_found
```

Only `ash_research_entered` is progression-critical.

## Archive facts

```text
ash_archive_entered
ash_slot_1140_found
ash_destroyed_cartridges_found
ash_alive_cartridge_hint
ash_second_missing_slot_found
```

Only `ash_slot_1140_found` is mandatory.

## Prediction facts

```text
ash_prediction_entered
ash_prediction_counter_seen
ash_branch_projector_used
ash_echo_scanner_used
ash_all_echoes_scanned
ash_branch_coffin_found
ash_branch_coffin_audio
ash_comparison_entered
ash_v_identity_match
```

Mandatory: projector, branch coffin, comparison identity match.

## Existing Echo facts

Read-only from wider quest:
```text
ash_echo_count
ash_echo_01
ash_echo_02
ash_echo_03
ash_echo_04
ash_echo_05
ash_echo_06
```

Validator can warn if count disagrees with individual flags, but Cynosure should not silently rewrite external state.

## Server/core facts

```text
ash_server_vault_entered
ash_ashcache_meaning_known
ash_server_wake_event

ash_core_ante_entered
ash_continuity_door_seen
ash_continuity_door_checked
ash_continuity_audio_heard

ash_core_authorized
ash_core_entered
ash_core_activated
ash_truth_1140_known
ash_counter_post_reveal_changed
```

Logical core order:
```text
authorized → entered → activated → truth
```

Later canonical state may repair earlier state when progression makes it certain.

## Mara facts

Cynosure-owned:
```text
ash_mara_confession
ash_mara_archive_reveal
```

External/read-only:
```text
ash_mara_alive
ash_mara_trust
```

Recommended trust semantics unless wider quest already differs:
```text
0 HOSTILE/VERY LOW
1 LOW
2 MEDIUM
3 HIGH
```

Mara alive path and archive fallback should not both normally be true.

## Knowledge facts

```text
ash_knows_1140_came_from_cynosure
ash_knows_1140_is_predictive_branch
ash_knows_v_is_source
ash_knows_mara_removed_1140
ash_knows_thousands_branches
ash_knows_other_branch_missing
ash_knows_recent_visitor
```

Knowledge facts describe what V actually knows and should be used for dialogue.

Canonical setters:
- Cynosure origin: 0-1140 slot or explicit scanner evidence.
- predictive branch: branch-coffin reveal.
- V is Source 0: comparison apparatus only.
- Mara removed 0-1140: confession or archive fallback.
- other missing branch: 0-1179 discovery.
- recent visitor: security evidence.

## Prediction deviation

```text
ash_prediction_deviation
ash_deviation_class
```

Deviation range 0..7.

Class:
```text
0 LOW
1 MEDIUM
2 HIGH
```

Mapping:
```text
0–1 LOW
2–3 MEDIUM
4–7 HIGH
```

Guard facts:
```text
ash_pd01_entry
ash_pd02_security
ash_pd03_dialogue
ash_pd04_object
ash_pd05_route
ash_pd06_mara
ash_pd07_precore
```

All deviation awards must go through the questphase graph's per-event guarded subgraph so an event cannot award twice.

## Ending facts

```text
ash_final_console_enabled
ash_ending_selected
ash_ending_id
ash_core_post_state
```

Canonical ending ID:
```text
0 NONE
1 DESTROY
2 ABSORB
3 BLUE_EYES
4 HIDE
```

Compatibility:
```text
ash_ending_destroy
ash_ending_absorb
ash_ending_blueeyes
ash_ending_hide
```

Canonical `ash_ending_id` always wins over compatibility flags.

Absorb-specific:
```text
ash_1140_in_v
```

Only valid for ending 2.

Escape:
```text
ash_escape_started
```

Ending ID > 0 can safely repair `ash_ending_selected` and `ash_escape_started`.

## Runtime-only state

Do not persist unnecessary presentation values:
```text
pump_current_rpm
camera_current_yaw
camera_current_pitch
core_ring_angle
projector_animation_time
door_animation_percentage
server_led_frame
```

Recommended session-only dialogue lock:
```text
ash_dialogue_busy
```

Values:
```text
0 FREE
1 MANDATORY
2 MARA
3 JOHNNY
4 AMBIENT
```

A reload must not leave a stale lock that suppresses all dialogue.

## Optional facts that never gate completion

```text
ash_maintenance_log_found
ash_recent_visitor_found
ash_subject_records_found
ash_mara_override_record_found
ash_destroyed_cartridges_found
ash_alive_cartridge_hint
ash_second_missing_slot_found
ash_prediction_counter_seen
ash_echo_scanner_used
ash_all_echoes_scanned
ash_branch_coffin_audio
ash_continuity_door_seen
ash_continuity_door_checked
ash_continuity_audio_heard
```

## Minimum completion chain

```text
ash_cynosure_started = 1
ash_cynosure_entered = 1
ash_checkpoint_power = 1
ash_pumps_activated = 1
ash_security_resolution > 0
ash_biometric_1140_match = 1
ash_research_entered = 1
ash_slot_1140_found = 1
ash_branch_projector_used = 1
ash_branch_coffin_found = 1
ash_v_identity_match = 1
ash_server_vault_entered = 1
ash_core_activated = 1
ash_truth_1140_known = 1
ash_ending_id > 0
ash_escape_started = 1
ash_cynosure_complete = 1
```

## Invariants

If `ash_v_identity_match == 1`, branch-coffin discovery should normally already be true.

If `ash_truth_1140_known == 1`, expect identity match and core activation.

If `ash_ending_id > 0`, require truth known, ending selected, and escape started.

If `ash_cynosure_complete == 1`, require ending ID > 0, escape started, and phase 120.

Ending compatibility booleans are repaired from canonical ending ID.

## Repair policy

**SAFE**: automatic and unambiguous.

**CONTEXTUAL**: only if current phase/location proves missing state.

**MANUAL**: never guess ambiguous history.

Safe examples:
- ending ID > 0 → ending selected + escape started
- pump activated → running/drained world state
- post-gate player → biometric scan/match
- core-entered → authorization when impossible otherwise

Do not guess which entry route V used.

## Reconstruction inputs

`CYN_ApplyPersistentWorldState()` should primarily read:
```text
ash_cyn_phase
ash_checkpoint_power
ash_pumps_activated
ash_world_power_stage
ash_camera_first_move
ash_camera_tracking_enabled
ash_archive_entered
ash_branch_projector_used
ash_core_authorized
ash_core_activated
ash_truth_1140_known
ash_ending_id
ash_escape_started
ash_cynosure_complete
```

## Debug status

Always display:
```text
ash_cyn_phase
ash_world_power_stage
ash_echo_count
ash_prediction_deviation
ash_deviation_class
ash_mara_alive
ash_mara_trust
ash_slot_1140_found
ash_branch_projector_used
ash_branch_coffin_found
ash_v_identity_match
ash_truth_1140_known
ash_ending_id
ash_escape_started
ash_cynosure_complete
```

## Naming

Use:
```text
ash_<domain>_<state>
```

Avoid ambiguous `flag3`, `coreThing`, or duplicate aliases.

## Helper API

State authority is the quest/questphase graph (ash-cache-quest CLAUDE.md rule 1).
These names are concepts, not REDscript functions:

```text
QUEST / QUESTPHASE GRAPH (writes canonical state)
  set phase             - phase fact writes at graph nodes
  set power stage       - fact writes at graph nodes
  add prediction deviation(eventId) - one guarded subgraph per event
  commit ending(endingId)           - ending nodes; exclusivity and failsafe in the graph
  repair state          - repair/failsafe branches in the graph
  mandatory reveal progression

REDSCRIPT / CET (reads facts, presents them; never writes story state)
  CYN_ApplyPersistentWorldState()  - reconstruct devices from facts
  apply pump / camera / server emissive / core visual state
  CYN_ValidateState(), CYN_DumpState() - debug read-only status
  non-authoritative animation helpers
```

`CYN_ApplyPersistentWorldState()` may only read facts and rebuild presentation. It must
not advance phases, repair story facts, commit endings or award deviations.

## Protected story facts

These must only be set at intended reveals:
```text
ash_knows_1140_is_predictive_branch
ash_knows_v_is_source
ash_knows_mara_removed_1140
ash_truth_1140_known
```

Premature writes are narrative bugs.

## Do not encode protected mysteries as truth

Do not create:
```text
ash_opening_caller_is_blueeyes
ash_cynosure_controlled_by_blueeyes
ash_1179_is_someone_specific
ash_continuity_door_contains_ai
ash_all_branches_are_people
ash_prediction_is_deterministic
```

Evidence facts are fine; speculative conclusions are not.

## Validator

ERROR:
- invalid phase
- invalid power stage
- deviation outside 0..7
- ending outside 0..4
- complete with no ending
- ending with truth unknown
- ending incompatibility after repair

WARNING:
- core activated without authorization
- identity match without coffin discovery
- prediction entered before slot found
- archive entered before biometric match
- Echo count mismatch
- both Mara confession and fallback
- both entry route flags

## Final principle

Store what happened and what V actually knows—not every animation, interpretation, or theory.

Good:
```text
ash_second_missing_slot_found = 1
```

Bad:
```text
ash_second_missing_slot_means_secret_ai_survived = 1
```
