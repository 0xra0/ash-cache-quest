# Ash case: Trellis2 model -> game prop

Output lands in `assets/mod/ash_cache/props/ash_case/` (prebuilt CR2W; `tools/build.sh`
copies `assets/mod/` into the archive as-is). Work dir: `/mnt/sata/ComfyUI/_ashcase/`
(`venv/` there holds etcpak, texture2ddecoder, libigl, scikit-image, scipy).

| step | script | why it is not the obvious tool |
|---|---|---|
| clean solid | `close.py` | Trellis output is double sheets + 920k fragments; every decimator (pymeshlab, Blender, MeshLib) stalls at 2-3M faces and voxel remesh / winding number drop or blob it. Morphological closing on a 1.3 mm grid gives one watertight solid. Drop <200-face fragments first (`orig_clean.ply`). |
| 400k for texturing | pymeshlab quadric, topology-preserving | `optimalplacement` on the raw mesh throws 5 cm spikes; texturing normalises by bbox |
| texture | `tex_prompt.py` (ComfyUI, Trellis2 GGUF MultiView texturing, 4 photos) | ~2 h on the RX 6800 at 25 steps |
| low poly, bake, cut | `bl_game.py <textured.glb> <out> bake` | 20k tris; bakes d/n/r/m at 2048 (normal green flipped: DirectX); lid cut at 0.61 of the box height, origin on the back hinge; tray built with bmesh (EXACT boolean did nothing) |
| textures | `mkxbm.py` | WolvenKit.CLI can't import images on Linux (no native DirectXTex). BC7 via etcpak into a vanilla xbm's JSON; mip layout byte-identical to vanilla |
| meshes | `mkmesh.py` | `import -k` onto the vanilla splinter mesh; glb meshes must be named `submesh_NN_LOD_1`, triangulated, with tangents |
| entities | `gen_case_ent.py` | from vanilla `q005_broken_suitcase.ent`; edits both `components` and `compiledData` (+ `CruidDict`) |

All of it: `finish.sh <textured.glb>`. The lid angle in the opened .ent is `OPEN_DEG`.

## O-1140 splinter (`splinter/`)

Built from the orthographic sheet `splinter/sc_splinter.png`, not Trellis: a flat 42 mm
part with small print needs exact outlines and sharp projected text.

| step | script | out |
|---|---|---|
| outline + atlas | `prep.py` | front outline (+ key-ring hole), left profile, 1024 atlas d/r/m/n |
| hull + UV | `bl_splinter.py` | front prism ∩ side prism, bevel, planar UV per view, `splinter.glb` |
| all + install | `finish_splinter.sh <sheet>` | `assets/mod/ash_cache/props/splinter/` (mesh + 4 xbm) |

`gen_case_ent.py` points the open case's `full` component at it, `CHIP_SCALE` = 3.
Run from the working dir `/mnt/sata/ComfyUI/_ashcase/splinter/` (it uses `../venv`, `../mkxbm.py`, `../mkmesh.py`).

## Sheet props (`props/`, route A)

Any concept sheet with FRONT / BACK / LEFT / RIGHT views -> `.mesh` + 4 xbm in
`assets/mod/ash_cache/props/<name>/`: `props/build_prop.sh props/<name>/config.json`.
Visual hull (front outline ∩ side profile, see-through gaps kept) + the sheet
pixels projected per face. Keys are documented in `prep_sheet.py`; dark
render sheets use `"bg": "dark"` with `thr` / `close`, and explicit `boxes`
when a lit floor joins the views. Run from `/mnt/sata/ComfyUI/_ashcase/props/`
(uses `../venv`, `../mkxbm.py`, `../mkmesh.py`). Sheets live in ~/Downloads (`sc_*.png`).

## Insert (D150)

`blender -b -P bl_insert.py -- game_final/case_dims.json insert/` -> `insert.glb` + `insert.json`;
cradle textures as flat PNGs through `mkxbm.py`; `mkmesh.py insert insert/cooked
insert:ash_case_insert:ash_case_interior,ash_case_cradle 'mod\ash_cache\props\ash_case'`;
then `gen_case_ent.py game_final/case_dims.json insert/cooked insert/insert.json`.
