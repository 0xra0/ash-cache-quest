# Clinic redesign — overnight report (2026-09-25)

Everything below is live in the running game (hot-loaded, no restart) and in the build.
Decisions: D145–D154 in `docs/decisions.md`. Screenshots: `/mnt/sata/Cyberpunk2077/shots/ls/`.

## What the room is now

| Where | What | Asset |
|---|---|---|
| Centre, on the round grate under the big lamp | procedure table, case on top (opens toward the entrance, foam insert + steel cradle + cyan-rimmed pocket) | `morgue_table_a` + `_top_a`; `ash_case_*` |
| Right end of the table | Mara's spot (only while her scene runs) | marker `ac_mara` |
| Terminal counter (vanilla, kept) | boxy monitor with lit display, military diagnostic unit, closed folder | PL `old_monitor_4_3` (+display), `neo_milit_medical_device_a`, `paper_document_j_file_closed` |
| In front of the counter | stool pushed aside | `morgue_stool_a` |
| Left lane (glass partition) | two instrument trolleys | `medical_cart_a` / `_e` (military) |
| Back-left | supply cart | `medical_cart_d` (military) |
| Right wall, before the counter niche | low lab cabinet | `lab_set_a_locker_a` (military) |
| Table's left end | IV / diagnostic stand | `machine_iv_stand_a` |
| Past the counter | bin | `entropy_trashbin_a` |
| Lights | cyan terminal fill 90 lm; warm Mara face fill 70 lm | `gen_light_ent.py` |

Kept clear: walkway door → table, Mara's bubble, case approach, terminal standing spot.
All dressing exists only while `ashcache_progress` is 2..6 (same window as the Farida hide), so
her room comes back without it.

Best overview: `20260925-025956-lights_entry.png` (from the inner door),
`20260925-030144-mara_wide.png` (table + terminal corner), `20260925-015831-insert1.png` / `cyan1_crop.png` (case).

## Midday pass (D155) — the room was still too empty

20 more props (33 dressing items total), placed from a fresh raycast map of the walls:
left wall — tall military lab cabinet, open empty first-aid box, utility box, wheelchair;
door-left corner — packed cardboard boxes + crate (what was carried out);
right side — scrub sink and an unbolted ripperdoc-chair base by the entry, stripped recovery bed;
far wall — bench with instrument tray and a small unit, half-empty shelf + foam box, open empty
implant freezer, unplugged medical unit, cold practical light (the far wall was black);
table — folded sterile cloth at the left end, standing exam lamp.
Overviews: `20260925-130809-d6_dl.png`, `20260925-130833-d6_fr.png`, `20260925-130757-d6_far.png`.

## Needs you (can't be done without you)

1. **Quick save → quick load.** Sector changes only apply on load: the floating `computer_1`
   terminal (now disabled, D152) disappears for good, and the case/terminal markers settle.
   Tonight it is hidden for this session only.
2. **Check the terminal prompt** still shows at the counter (it is the scene hub on
   `#ac_terminal_origin`; nothing about it changed, but the visible monitor did).
3. **Mara's scene** — play it once: she should stand at the table's right end facing V.
4. After progress 7 (quest resolves), the dressing should vanish and Farida's room return —
   untested tonight (it would mean changing quest state).

## Tools added / changed tonight

- `source/clinic_dressing.json` + `tools/clinic_dressing.py` — one entry per prop or light;
  generates solid `.ent`, world.json pose, glue prop. Room frame documented in the JSON.
- `tools/gen_mesh_ent.py` — solid colliders ("Device solid visible"), extra meshes on one pivot.
- `tools/gen_light_ent.py` — point light entity.
- `tools/ash_case/bl_insert.py`, `mkmesh.py` (emissive materials), `gen_case_ent.py` (insert, light).
- `dev/hotcycle.py` — hot deploy + respawn + screenshot in one command.
- LocationStudio MCP: `screenshot`, `run_lua`, `teleport_player`, `call_scriptable_system`,
  `hot_reload_archives` (+ bridge ops). `loose=` (redscript/tweaks) exists in the server but did
  not appear in the client's schema after reconnects — hotcycle.py covers it.
- `tools/negtest.py` — baseline was failing since the Cynosure asset check (its scratch copy had
  no `assets/`); now linked: **110/110** cases hold. replaytest and shapetest green. Build 0/0.

## Open ideas (not done — optional per the design)

- Wall "absence" details (empty monitor arm, capped ports, rails) behind Mara.
- FIA cabinet: location reserved only (back wall, u≈2, v≈7.3 in the room frame); don't wire
  `ashcache_cabinet_opened` until its content exists.
