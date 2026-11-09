# Cynosure Entrance Access Corridor: build plan (2026-10-02)

Sources: `/mnt/ssd/Downloads/CYNOSURE_ENTRANCE_ACCESS_CORRIDOR.md`, `LOCATIONSTUDIO_CYNOSURE_ENTRANCE_ACCESS_CORRIDOR.md`,
and 34 concept images in `/mnt/ssd/Downloads/` ("Cynosure * Corridor*.png", "ChatGPT Image Oct 1, 2026*.png").

## Measurements to take before placing anything
- The M3 premise `premise_6abe1e0d_1_c440d9` already has an entry room after the Shaft 14 teleport. Read its
  frame from `data/project.json`, and reuse the existing landing point as `ANCHOR_CYN_ENTRY_START`.
- Local frame: +Y toward the bulkhead, +X = right wall, Z up. Origin = floor centre at the entry threshold.

## Shell (passes 1 and 2)
| item | value |
|---|---|
| length | 21.0 m: 6 bays of 3.5 m (bay n spans y = 3.5(n-1) .. 3.5n) |
| width | 3.8 m inside walls; clear walk lane 2.4 m (x -1.2 .. 1.2) |
| height | 4.0 m to the slab; services hang no lower than 2.4 m over the lane |
| ribs | 7 frames at y = 0, 3.5 ... 21; 0.30 m deep. Bay 5 ribs are doubled (heavier framing) |
| wall relief | 0.10-0.40 m: recessed panels between the ribs |
| floor | plate deck; drain channel along x +1.55 (right side); cross grates at y 6.8 and 17.2 |
| side feature | bay 4, left wall: sealed SERVICE AUTH ONLY door in a 0.4 m recess, hazard frame |
| bulkhead | y 21: octagonal frame 3.2 x 3.4 m, 0.6 m deep, "CYNOSURE / ACCESS GATE 01", hazard jambs |

## Dressing per bay (budget: about 90 objects)
- **B1 Arrival:** threshold frame, one bright white strip, one conduit run, empty floor.
- **B2 Identity:** left wall "CYNOSURE / RESTRICTED ACCESS / LEVEL 4 CLEARANCE" stencil at 1.6-2.6 m height, logo,
  a black/yellow band at 0-0.6 m, and a section number "A1".
- **B3 Infrastructure:** densest ceiling (2 main pipes of 25 cm, 3 secondary pipes of 8 cm, a cable tray, a duct),
  a relay cabinet, an environmental box, and a wall-penetration grille. Brightest white light.
- **B4 Maintenance:** side door, a rugged case, a toolbox (red), a detached grille leaning on the wall, coiled cable.
- **B5 Restriction:** dim white, first red caged lamp pair, "CLEARANCE REQUIRED / PRESSURE LOCK" plates, and
  protected conduit.
- **B6 Bulkhead:** red lamp pair flanking the door, an amber status light, floor hazard band at y 20, one
  flickering white fixture (the fault light), and the access reader (dead).

## Lights (white first, red only after the corridor reads in neutral light)
- White strips: B1 at 100 %, B2 70 %, B3 110 %, B4 70 %, B5 40 %, B6 60 % plus one with fault flicker.
- 4 red caged lamps (B5 x2, B6 x2), 1 amber lamp at the bulkhead, 4-6 low amber floor-edge strips (seen in the
  concepts).

## Wetness and FX
- Wet floor-plate material or puddle decals in B2, B4 and B6, running toward the drain. 3 drip emitters (B3 pipe
  joint, B5 ceiling seam, bulkhead frame), 1 low mist at the bulkhead, an optional steam wisp in B3.

## Asset sources
- Use vanilla CP2077 meshes first for pipes, trays, cabinets, cases, grilles and lamps. Search
  `research/cp77wb/meshes.txt` (the catalog dump).
- Starfield kit (`mod\ash_cache\sf\`, personal build only), where it fits: `mfg_electron_pump` style
  pipework only. No servers, tanks, coffins or core pieces here: the spec forbids those room types.
- Decals are needed for the stencils. The Starfield bake drops decals, so use vanilla decals or LS `create_decal`.

## Build route
- Under 600 objects, so LS `edl_apply` is safe (memory `ls-large-premise-apply`).
- Then `build_mod_from_project`, hot reload, and the screenshot set SHOT_01..10 from the spec.

## State (2026-10-02, 03:20): built and in game, art pass 1 done (v7)
- **Generator:** `tools/gen_cyn_entrance.py` -> `source/cynosure/entrance/cyn_entrance.edl.yaml`.
  - 224 meshes, 15 decals, 9 static lights, 4 particles, 6 box colliders.
  - All vanilla (int_common_techpanel_a kit + ep1 Cynosure signs, door and light boxes), so it can ship.
- **Placement:** own LS premise "Cynosure Entrance Access Corridor", own archive `ash_cache_cyn_entrance.archive` + .xl
  in `archive/pc/mod`. Corridor x -1.9..1.9, y -11..10 premise (world y -2481..-2460), z -300..-296.2.
- **Old M3 room:** the 29 objects of "Entry (Shaft 14 landing)" are disabled (enabled=false) and M3 is rebuilt
  without them (1268 nodes). The backup archive is `ash_cache_cynosure.archive.bak-2026-10-02-entrance`.
- **Bays:** arrival (puddle, floor arrow), identity (CYNOSURE plate + chevrons at eye height, left wall), infrastructure
  (floor grate + steam, wall duct, relay cabinets, cross pipes), maintenance (sealed yellow side door, rugged case,
  toolbox), restriction (dim, dead light panel, red panel, yellow panel, warning sign), bulkhead (4 m yellow frame,
  Cynosure bunker door slab jammed 2.35 m open, vertical Cynosure plate, caution lettering, flickering white light).
- **Screenshots:** SHOT_01..10 in `shots/cyn_entrance_2026-10-02/` (+ `final_sheet.jpg`).
- **Iteration loop:** `dev/cyn_entrance/iter.sh <tag>` = generate, edl_apply(save), batch spawn, build, despawn
  live copies, hot reload, wait for the re-stream, 4 views. `finalshots.py <tag>` = the 10 spec shots.
  `lsc.py` calls LS MCP tools without the MCP connection.

## v8-v10 (2026-10-02 morning, after user review)
- Ribs: techpanel `pillar_h400_l50_a` (0.6 x 0.6, `annodised_dark`) on every module joint, half sunk, 0.25 m proud.
- The relay cabinets (`attachments_fuse_box_a`) were free-standing 0.3 m off the wall and read as black monoliths in
  the lane; now flush on the wall, centred between ribs. One duct instead of two (the second clipped the cabinet).
- New: caged red lamp housings (`base\lighting\warning_light.mesh`), dead access reader (`hand_scanner_a`) on the
  left bulkhead jamb, cable coil by the side door, a vent grille (`ceiling_vent_l100_w100_a`, `black`, roll +75
  stands it against the left wall; roll -75 sinks it into the floor), 4 low amber floor-edge lights, 7 audio
  emitters (drips x3, grate steam, vent hum, fault-light flicker, relay buzz; names from WB `sounds.txt`).
- Chevron sign moved to the arrival bay (a rib now stands where it was); high-voltage sign above the relay cabinet.

## v11-v14 (2026-10-02, 11:15)
- Spec gaps filled: B2 Cynosure hazard band (both walls, 0-0.6 m) + section "A1" stencil, bay 5 doubled ribs,
  "PERSONNEL ONLY" on the yellow bay 5 panel, Cynosure "no entry" mark in bay 6, floor hazard band 1.3 m before the
  bulkhead (caution lettering moved to 2.3 m), amber status lamp housing + light on the right jamb, low floor mist.
- **Wall decals were all invisible until v12** (incl. the v7 volt/warning signs): decals project along local -Z, so a
  left-wall decal is yaw 90 pitch 90, right wall yaw -90 pitch 90. Decals on the see-through floor grates don't show.
- `cynosure_01_warning_a.mi` renders as sideways green text: not usable as a sign.

## v15-v18 detail pass (2026-10-02, 16:40; user: "looks somewhat empty")
- Wall conduits (`pipes_small_01_b`, 'metal'): left z 0.85, right z 1.85, ending in `pipes_small_01_e` elbows into
  the wall (roll 180 mirrors the bend). Two black `pipes_smallest_01_b` runs at the base of each wall. Skip ranges keep
  them clear of the cabinets, duct, signs, side door and grille.
- Wall boxes (`electric_box_entropy_a_case`) x4, intercom, 2 wall vents, 2 extinguishers, 2 blue drums with an oil trail
  and a warning symbol, section stencils A2..A6 high on the left wall, rust leaks, dust, yellow lane-edge strips.
- 399 objects / 43 decals. Dev views: `dev/cyn_entrance/detail.sh <tag>` -> `<tag>d.jpg`.
- Tried and dropped: `cable_fusebox_small_a` risers (two stray white strips); techpanel `wall_h400_l300_c` over a black
  backing for relief (the cut-outs let orange light through). `RELIEF_L/R` in the generator re-enables it.

## v19-v20 (2026-10-02, 17:20; user review)
- Only "A1" kept (A2..A6 read as too many location labels). Floor arrow removed (it pointed sideways).
- `col_ceiling` box over the whole corridor at z H+0.2: before it V could jump onto the wall tops.
- South end: blank wall replaced by a yellow techpanel double-door frame + a closed Cynosure bunker slab
  (`door_int_mlt_bunker_b`, z 0.12 so its lit bottom edge is under the floor). The wall collider still blocks it.

## v21-v22 (2026-10-02, 17:30)
- Drain channel (spec x +1.55): techpanel `floor_grate_l200_w100_a` scaled [1, 0.35, 0.06], flush on the floor at
  x 1.38..1.73, one per 2 m floor row, skipped on the two cross-grate rows. The industrial gutter
  (`int_ent_industrial_a_gutter_w100_l200_a`, v21) rendered almost black here: dropped.
- B3 cable tray: `floor_grate_l300_w100_a` scaled to 0.45 x 2.8 x 0.05 at z 3.0, x -1.45..-1.0, two cable bundles
  on it, four hanger rods (cable_bundle_pipe pitch 90 = rod goes up). There is no vanilla cable-tray mesh.
- Next asset for the elevator: techpanel `wall_door_elevator_h400_l300_a` (X -3..0, faces +Y, 3.8 m); cp77wb has
  `wb_elevator_wire`.

## v23 elevator, lower landing (2026-10-02, 18:20; spec /mnt/ssd/Downloads/LOCATIONSTUDIO_CYNOSURE_ELEVATOR.md + 8 concepts)
- `elevator()` in the generator. The south door is now the lift's lower landing: bunker slab removed, `col_wall_s` split
  into two jambs (opening x -1..1). Cab = `wat_nhr_maelstrom_hideout_elevator_a` (X-braced freight cage, 4.8 x 4.4,
  open at +/-Y) centred 2.3 m behind the frame, inside a black techpanel shaft box (x +/-2.6, 4.8 deep, ceiling 4.4)
  with its own colliders. Dressing: intercom as cab panel, caged red lamp + pulsing red light, cold white practical,
  dim amber panel light, Cynosure plate on the back, warning sign, threshold stripes, vent hum.
- Lineup test (`CYN_LINEUP=1`) compared Maelstrom a/cage_a/cage_b, Steinbeck cage_inside, elevator_door_large,
  techpanel elevator frame. Light colours in EDL are 0..1 (0..255 fails edl_apply).
- Not done (needs the user): surface landing above the motel, moving `ac_cyn_entry_tp` into the cab, quest
  descent sequence (doors/facts/timing).

## v24 elevator: match the motel lift (2026-10-02, ChatGPT review + user "go")
- Folding scissor gate `int_public_utility_002__elevator_industrial_front.mesh` closes the cab back (same gate language as the
  vanilla motel service elevator). Its geometry sits ~1.5 m +Y of the mesh origin: placed at cy - 3.5. Landing side open.
- Control post: PL Cynosure bunker lift panel `ep1\...\q305_bunker_elevator\bunker_elevator_panel.mesh` (replaces intercom).
- Shaft: Maelstrom `rails_structure_a` behind the cab. Floor: dust strip, two oil stains, sill grime. White light warmed.
- Other finds: `q305_bunker_elevator.mesh` = big open grated platform lift; megabuilding `elevator_a_rails_a` = pillars.
- The blank grey plate on the cab side is part of the Maelstrom cab mesh (not a mis-oriented sign).
- **`ac_cyn_entry_tp` moved into the cab (user OK):** source/world.json (-1908, -2484.9, -300) yaw 0; quest rebuilt,
  `ashcache.archive` deployed + hot-reloaded (game backup `.bak-2026-10-02-cabtp`). Not yet walked through the quest teleport.
- Open: v24b screenshots (capture grabbed the desktop: the game was not in front), surface landing = existing motel
  service elevator (find it in the world), hidden reader + service override, 11-12 s ride sequence (ChatGPT timeline).

## v25 elevator: sealed cab (ChatGPT review 3)

- `elev_gate_front`: a second folding gate on the corridor side (yaw 180, origin cy+3.5), built CLOSED. Verified in shot `dev/cyn_entrance/v25.jpg`: the cab is sealed from the corridor.
- The scissor lattice is see-through, so the corridor stays visible from inside. Added `elev_landing_door` (Maelstrom slide doors, solid) at the landing frame yf. NOT yet verified: the capture caught the desktop.
- Shaft depth: ladder cage on the left shaft wall (visible). The megabuilding `rails_a` and `railing_a_cables_a` on both shaft walls do not show in the side views; they need a lineup or a reposition.
- Descent quest: hide `elev_landing_door` + `elev_gate_front` (NodeRefs still to add) when the lift opens. Panel readout states (SURFACE / DESCENT / LOWER ARRIVAL) are reserved; state lights only until decals exist.

## v26 elevator: single-entry cab, solid landing door (ChatGPT review 4)

- Rear folding gate removed (two lattices read as a double cage). Shaft back moved to `yf - 5.2`: 0.68 m dark recess
  behind the open cab end with 2 black techpanel guide pillars, 3 megabuilding cable runs, 3 caged amber lamps.
  Invisible collider `elev_col_cabback` at `cy - 2.3` keeps V in the cab (teleport spot `cy - 1.35`: 0.95 m behind,
  2.8 m to the gate, 1.85 m from the panel).
- Landing door = `door_int_mlt_bunker_b` (solid, 3.2 x 4.2 m) at `yf - 0.1`. Rejected: Maelstrom `slide_doors_a`
  (renders nothing as a static node), `elevator_door_large_a/b` (grille panels, corridor light shows through).
- Verified (`dev/cyn_entrance/v26b.jpg`): corridor sees only the bunker door; teleport view sees gate + solid door,
  no corridor light. Wear: rust strip on the gate track, 4 rust anchor plates, rust leaks on the cab sides.
- Blocker for the descent: LS cannot give a placed object a NodeRef. The EDL has no field for it, and
  `modules/build_export.lua` `_serialize` never sets `spawnable.nodeRef` (export JSON has `nodeRef: ""`;
  `lsbuild/native.py` already writes non-empty ones into the sector). Needs a small LS patch:
  EDL `node_ref` -> object.metadata -> `data.spawnable.nodeRef`. Refs wanted: `CYN_ELEV_GATE`, `CYN_ELEV_LANDING_DOOR`.

## v27 NodeRefs on the elevator doors (LS patch, user-approved 2026-10-02)

- Built sector nodeRefs: `$/03_night_city/ash_cache/#AshCache/#CYN_ELEV_GATE` (node 62, cab folding gate, moves with the cab)
  and `...#CYN_ELEV_LANDING_DOOR` (node 63, bunker slab, stationary landing door, not part of the cab). Both are static
  `worldMeshNode`s: they cannot animate. Open/close = quest graph `questShowWorldNode_NodeType` hide/show pairs
  (LANDING_DOOR_CLOSED/OPEN, GATE_CLOSED/OPEN); must be proven in game before the ride is built.
- LS patch (backups `*.bak-2026-10-02-noderef`): EDL element `node_ref` (optional; missing/null/empty = old behaviour;
  must match `$/path/#name`; duplicates and malformed values are compile errors; `quest_relevant: true` without one
  warns; never generated) -> plan step -> `object.metadata.node_ref` (`authoring_plans.lua` `_run_step`) ->
  `data.spawnable.nodeRef` (`build_export.lua` `_serialize`) -> sector (`native.py`, errors on duplicate in a sector).
  `is_ref` no longer treats `$/...` as a plan alias. The running game got an equivalent in-memory hot patch
  (`dev/cyn_entrance/hotpatch_noderef*.lua`); the disk Lua loads on next restart and is not yet run in game.
- Generator: `obj(..., node_ref='CYN_ELEV_GATE')` adds the prefix `NR` and `quest_relevant`.

## Open items
1. **Arrival anchor (user: later, 11:00):** quest marker `ac_cyn_entry_tp` (source/world.json) still lands
   at world y -2467, which is mid-corridor (bay 4/5). The spec arrival is about y -2479.5 facing +Y. Changing it is
   one coordinate in world.json plus a quest-sector rebuild; I have not done it.
2. SHOT_07/08 framing is too close (spec shots not re-taken after v10).
3. Audio emitters are in the sector (7 `worldStaticSoundEmitterNode`) but not yet confirmed audible by ear.
4. The red eye-level line in captures is the user's cyberpsychosis mod overlay, not the build (user, 10:15).
6. ~~Mara's bubble~~: closed. ac_mara is in the clinic at z 24; the corridor is at z -300, so the HUD figure was not
   about this room.
5. The spec's "LS_CYN_ENT_*" child groups are not created; the EDL ids carry the role prefixes instead.

## Gotchas found tonight
- `LoadLastCheckpoint` from the title screen ("press Space") hangs on a black loading backdrop with no HUD, even
  though V and collision are loaded. Press Space (xdotool on DISPLAY=:4) to reach the main menu first.
- Techpanel walls and Cynosure decal meshes face local +Y; seen from -Y they are culled.
- Techpanel wall variants b/c have window/vent cut-outs.
- Every `edl_apply` makes a new premise id (the old one is replaced). The build only exports spawned objects, so
  batch spawn first, then `despawn_all_objects` after the build or the live copies double the geometry.
- AutoSave-10 (written at 01:52 while the game was being killed) is parked in
  `/mnt/ssd/Cyberpunk 2077/save-backups/2026-10-02-suspect/` with the older AutoSave-5/6 (the game has since written
  new ones in those slots); autosaves 7-9 were moved back.
