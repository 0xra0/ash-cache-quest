# Cynosure locations: how to build them properly

Written 2026-10-01 after M2 (D196) and the Starfield prop pipeline / M3 dressing (D197).

## Principle: generated layers, one EDL

Every layer is generated from hand-edited source data, so a room can be moved or resized and everything follows.
Nothing in the built EDL is hand-placed.

| layer | source | generator | output |
|---|---|---|---|
| 1 shell (walls, floors, door frames, ring) | `cynosure_m1.edl.yaml` (rooms, sizes, doors) | `gen_cyn_m2.py` (vanilla int_common_a kit pieces + box collision) | `cynosure_m2.edl.yaml` |
| 2 dressing (props) | `cynosure_m3_dressing.yaml` | `gen_cyn_m3.py` (wall rows, lines, stacks, rings, door clearance, OBB collision, plan PNG) | `cynosure_m3.edl.yaml` |
| 3 light | per-room light templates in the M1 yaml | (M4) a lights section in the dressing yaml: fixtures snap to props (lamp on a console = a point light) | same EDL |
| 4 navigation | the dressed collision | LS `nav_generate` after M3 is applied | LS nav |
| 5 story anchors | `CYNOSURE_ANCHORS_AND_TRANSFORMS.md` | `gen_cyn_m2.measure_anchors` (structural); prop anchors can come from M3 ids | `cynosure_anchors_measured.yaml` |

Keep the EDL id `cynosure_m1` for every stage, so applying always replaces the build in place.

## What makes each room readable (target, not done)

The design doc's visual language: aged gunmetal, institutional off-white, dark polymer; hazard yellow / amber /
FIA red / limited cyan; flood streaks, scratches, repairs. Not pristine lab sci-fi.

| room | identity | have now | still needed |
|---|---|---|---|
| 01 Entry | the lift you came down in | Starfield industrial lift cage (`elvindsm_bot01`) | matching shaft-head cabin on the surface (needs the stood-on capture) |
| 02 Checkpoint | you are being scanned | overhead body scanner, guard consoles, camera | red FIA light, a barrier |
| 03 / 04 Flood + Pump | water did this | tanks, machines, pipe | the real pump (CYN_ASSET_PUMP), water decals, puddles (vanilla decals) |
| 05 Security | someone watched | server cabinets, consoles, camera | monitors with emissive screens |
| 06 Biometric | the reader | wall laser reader, terminal | interaction device (FIA reader) |
| 07 Observation | they cut people open | autopsy table, IV, carts, specimen tank | surgical lamp, glass partition |
| 08 Archive | rows of minds in tubes | 4 rows of specimen tanks (with glass) | cyan inner glow (emissive), floor cable runs |
| 09 Prediction | the table that sees | digital table, mega screen, consoles | projector/hologram VFX |
| 10 Branch coffins | eight sealed coffins | procedural coffin x8 (amber lamp, window) | a lit interior/body under the glass for the one that matters |
| 11 Comparison | two of you | two MRI scanners | — |
| 12 Server vault | 60 m of servers | server rows both walls | cable trays overhead, blinking lights |
| 14 Core | the machine | 12 m stacked containment column, consoles ring | the column needs glass + inner light; CYN_ASSET_PREDICTIVE_CORE eventually |

## Rules learned the hard way

- Visible geometry is vanilla kit meshes or cooked props, never LS procedural boxes (box UVs break ML masks, D196).
- Starfield props are for the personal build only (D197). Anything for release must be original: procedural
  Blender props with own textures (the coffin pattern) or properly cleaned AI models.
- Every prop gets collision from its cooked bounds. The generator reports overlaps instead of nudging silently.
- Bake atlases are dilated (sentinel mask + 2 px) or mips bleed (ash_case 2026-09-24, starfield 2026-10-01).

## Next steps (in order)

1. Game running: `edl_apply` M3 → `dependency_stage(..., sources=[starfield_kit/depot])` → build → hot-reload.
2. Walk the route with screenshots: prop fronts, the core column's scale, glass, the scanner hang height.
3. Fix fronts in `fronts:`, re-run `gen_cyn_m3.py`, re-apply (a minute).
4. M4 lights: fixtures from the dressing yaml; emissive for screens, lamps and tube glow (metal_base Emissive,
   as `mkmesh.py` EMISSIVE does for the ash case).
5. Nav regenerate; walkability check along the canonical route.
