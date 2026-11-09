#!/usr/bin/env python3
"""Cynosure Entrance Access Corridor -> source/cynosure/entrance/cyn_entrance.edl.yaml

Spec: /mnt/ssd/Downloads/LOCATIONSTUDIO_CYNOSURE_ENTRANCE_ACCESS_CORRIDOR.md (plan: docs/cyn_entrance_corridor_plan.md).
Replaces the M3 'Entry (Shaft 14 landing)' room. Premise frame = M3 origin (-1908, -2470, -300), +Y = deeper.
Corridor: x -1.9..1.9 (inner), y Y0..Y1, z 0..3.8. The far end (y 10) is the M3 doorway into the Checkpoint.
All meshes are vanilla (int_common_techpanel_a kit + ep1 Cynosure signs/door), so this part is publishable.
Pivot notes (bounds checked 2026-10-02): techpanel walls span X[-L,0] Y[0,0.25] Z[0,3.8], visible face = local +Y
(seen from local -Y they are back-face culled);
floor/ceiling tiles span X[-L,0] Y[-W,0]; cable_bundle_pipe_01_a runs Y 0..1.
"""
import os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'source', 'cynosure', 'entrance', 'cyn_entrance.edl.yaml')

TP = 'base\\environment\\architecture\\common\\int\\int_common_techpanel_a\\int_common_techpanel_a_'
CYN = 'ep1\\environment\\decoration\\unique\\cynosure\\'
DOOR = 'ep1\\environment\\decoration\\doors\\unique\\cynosure\\'
CABLE = None  # resolved from the catalog below
FUSE = 'base\\environment\\decoration\\electronics\\attachments\\attachments_fuse_box\\attachments_fuse_box_a.mesh'
TOOLBOX = 'base\\environment\\decoration\\containers\\cases\\toolbox\\toolbox_a.mesh'

Y0, Y1 = -11.0, 10.0      # corridor ends (Y1 = M3 checkpoint doorway plane)
HW = 1.9                  # half inner width
H = 3.8                   # wall height
MOD = 3.0                 # wall module length -> 7 modules
WALL_APP = 'default'
RELIEF_L, RELIEF_R = (), ()   # v17 tried (3,), (6,): the cut-outs let orange light through; off

objs, cols, lights, vfx, audios = [], [], [], [], []
DEC = 'base\\surfaces\\textures\\decals\\'


def audio(i, event, at, radius):
    audios.append({'id': i, 'resource': event, 'at': [round(a, 3) for a in at], 'radius': radius})


def decal(i, mi, at, scale, yaw=0.0, pitch=0.0, roll=0.0):
    o = {'id': i, 'resource': {'type': 'decal', 'path': mi}, 'at': [round(a, 3) for a in at], 'scale': scale}
    if pitch or roll:
        o['rotation'] = {'yaw': yaw, 'pitch': pitch, 'roll': roll}
    else:
        o['yaw'] = yaw
    objs.append(o)


def fx(i, particle, at, yaw=0.0, scale=None):
    v = {'id': i, 'resource': particle, 'at': [round(a, 3) for a in at], 'yaw': yaw}
    if scale:
        v['scale'] = scale
    vfx.append(v)


NR = '$/03_night_city/ash_cache/#AshCache/#'   # quest NodeRef prefix (same tree as #ac_* refs)


def obj(i, res, at, yaw=0.0, app='default', pitch=0.0, roll=0.0, scale=None, node_ref=None):
    o = {'id': i, 'resource': res, 'appearance': app, 'at': [round(a, 3) for a in at]}
    if node_ref:
        o['node_ref'] = NR + node_ref
        o['quest_relevant'] = True
    if pitch or roll:
        o['rotation'] = {'yaw': yaw, 'pitch': pitch, 'roll': roll}
    else:
        o['yaw'] = yaw
    if scale:
        o['scale'] = scale
    objs.append(o)


T = 0.25                  # wall thickness


def wall_l(i, res, ya, length, app='default'):
    obj(i, res, (-HW - T, ya), -90, app)


def wall_r(i, res, ya, length, app='default'):
    obj(i, res, (HW + T, ya + length), 90, app)


def col(i, at, size, yaw=0.0):
    cols.append({'id': i, 'shape': 'box', 'at': [round(a, 3) for a in at], 'yaw': yaw, 'size': size})


def light(i, at, color, intensity, radius, flicker=None):
    li = {'id': i, 'at': list(at), 'color': list(color), 'intensity': intensity, 'radius': radius}
    if flicker:
        li['flicker'] = flicker
    lights.append(li)


def find_cable():
    cat = os.path.join(ROOT, 'research', 'cp77wb', 'meshes.txt')
    for line in open(cat):
        if line.strip().endswith('cable_bundle_pipe_01_a.mesh'):
            return line.strip()
    raise SystemExit('cable_bundle_pipe_01_a not in catalog')


def elevator():
    """v23 Cynosure service lift (LOCATIONSTUDIO_CYNOSURE_ELEVATOR.md), lower landing state: cab parked, doors open.
    Cab = Maelstrom hideout freight cage (X-braced sides, open +/-Y ends), inside a black techpanel shaft box."""
    yf = Y0 - T                     # landing frame plane (corridor side of the south door frame)
    cy = yf - 2.3                   # cab centre
    SW, SB = 2.6, yf - 5.2          # shaft half width, shaft back plane (v26: 0.68 m dark recess behind the cab)
    E = 'base\\environment\\architecture\\watson\\north_harbor\\meat_factory\\elevator\\wat_nhr_maelstrom_hideout_elevator_'
    DT = DEC + 'dirt\\'
    obj('elev_cab', E + 'a.mesh', (0, cy, 0), 0)
    # shaft: side walls face the cab, back wall faces +Y, fillers beside the 4 m door frame face -Y
    for k, y in enumerate((SB, SB + 3.0)):
        ln = min(3.0, yf - y)
        obj(f'elev_shaft_l_{k}', TP + 'wall_h400_l300_a.mesh', (-SW, y), -90, 'black')
        obj(f'elev_shaft_r_{k}', TP + 'wall_h400_l300_a.mesh', (SW, y + 3.0), 90, 'black')
    for k, x in enumerate((-SW + 3.0, SW)):
        obj(f'elev_shaft_back_{k}', TP + 'wall_h400_l300_a.mesh', (x, SB), 0, 'black')
    obj('elev_shaft_fill_l', TP + 'wall_h400_l100_a.mesh', (-2.0, yf + 0.01), 180, 'black')
    obj('elev_shaft_fill_r', TP + 'wall_h400_l100_a.mesh', (SW, yf + 0.01), 180, 'black')
    for k, x in enumerate((-SW + 2.0, SW)):
        obj(f'elev_shaft_ceil_{k}', TP + 'floor_l200_w200_a.mesh', (x, yf, 4.4), 0, 'black', pitch=180)
        obj(f'elev_shaft_ceil_{k}b', TP + 'floor_l200_w200_a.mesh', (x, yf - 2.6, 4.4), 0, 'black', pitch=180)
        obj(f'elev_shaft_ceil_{k}c', TP + 'floor_l200_w200_a.mesh', (x, yf - 4.0, 4.4), 0, 'black', pitch=180)
    # cab dressing: control panel + dead reader on the right post, Cynosure plate on the back gate, red lamp, load sign
    # v24 (ChatGPT review): read as the SAME lift as the motel service elevator -> vanilla folding scissor gate
    # (int_public_utility_002 industrial elevator) closes the cab back; landing side stays open (doors-open arrival)
    PU = 'base\\items\\interactive\\public_utility\\int_public_utility_002__elevator_industrial\\int_public_utility_002__elevator_industrial_'
    # v26 (ChatGPT review 4): single-entry freight cab. Back = open to the shaft recess (rails, cables, lamps), no
    # rear gate (two lattices read as a double cage). Front: folding gate (cab) + solid split landing door, both built
    # CLOSED; the descent quest opens them (door first, gate 0.4 s later) once they carry NodeRefs.
    obj('elev_gate_front', PU + 'front.mesh', (0, cy + 3.5, 0), 180, node_ref='CYN_ELEV_GATE')   # geometry 2 m +Y of origin -> lands at cy+1.45
    # landing door = solid Cynosure bunker slab (3.2 x 4.2 m). The Maelstrom slide_doors mesh renders nothing as a
    # static node and elevator_door_large has see-through grille panels (v25/v26 shots)
    obj('elev_landing_door', DOOR + 'door_int_mlt_bunker_b.mesh', (0, yf - 0.1, 0), 0, node_ref='CYN_ELEV_LANDING_DOOR')
    # shaft recess: two dark guide rails, vertical cable bundle, 3 small amber apertures
    for k, x in enumerate((-1.5, 2.05)):
        obj(f'elev_guide_{k}', TP + 'pillar_h400_l50_a.mesh', (x, SB + 0.55, 0), 0, 'black')
    for k, x in enumerate((0.75, 0.83, 0.91)):
        obj(f'elev_cable_{k}', 'base\\environment\\architecture\\megabuilding\\structural\\elevator\\common_megabuilding_elevator_a_railing_a_cables_a.mesh',
            (x, SB + 0.2, -2.0), 0)
    for k, (x, z) in enumerate(((-2.1, 0.6), (1.5, 3.6), (-0.2, 3.9))):
        obj(f'elev_aperture_{k}', 'base\\lighting\\warning_light.mesh', (x, SB + 0.1, z))
        light(f'elev_aperture_l{k}', (x, SB + 0.3, z), (1.0, 0.5, 0.15), 3, 1.2)
    # Cynosure bunker-lift control post (PL q305) replaces the intercom: the SHAFT 14 / depth readout surface
    obj('elev_panel', 'ep1\\environment\\decoration\\unique\\quest\\q305\\q305_bunker_elevator\\bunker_elevator_panel.mesh',
        (1.85, yf - 0.7, 0), -90)
    # shaft: guide-rail structure behind the cab, so the gaps read as a shaft, not a blocked room
    obj('elev_rails', E + 'rails_structure_a.mesh', (0, SB + 0.35, 0), 0)
    # floor wear: scraped centre strip, oil at the corners, grime at the threshold
    decal('elev_scrape', DT + 'dust_patch_01_dark.mi', (0, cy, 0), [1.0, 3.6, 0.5], 0)
    decal('elev_oil_l', DT + 'oil_trail_asphalt_a.mi', (-1.7, cy - 1.4, 0), [0.7, 0.9, 0.5], 35)
    decal('elev_oil_r', DT + 'oil_trail_asphalt_a.mi', (1.6, cy + 1.2, 0), [0.6, 0.8, 0.5], -50)
    decal('elev_rust_track', DT + 'rust_a.mi', (0, cy + 1.45, 0), [3.0, 0.35, 0.5], 0)
    for k, (x, y) in enumerate(((-1.6, cy - 1.5), (1.6, cy - 1.5), (-1.6, cy + 0.9), (1.6, cy + 0.9))):
        decal(f'elev_anchor_{k}', DT + 'rust_a.mi', (x, y, 0), [0.22, 0.22, 0.4], 0)
    decal('elev_rust_l', DT + 'rust_leak_a.mi', (-2.3, cy + 0.6, 0.7), [0.9, 1.2, 0.3], 90, 90)
    decal('elev_rust_r', DT + 'rust_leak_a.mi', (2.3, cy - 0.8, 0.7), [0.9, 1.2, 0.3], -90, 90)
    decal('elev_dirt_sill', DT + 'dirt_p_dark.mi', (0, yf - 0.3, 0), [2.2, 0.6, 0.5], 0)
    obj('elev_lamp_red', 'base\\lighting\\warning_light.mesh', (-1.3, yf - 0.5, 2.7))
    obj('elev_sign_plate', CYN + 'cynosure_sign_b_plate_a.mesh', (0, SB + 0.3, 1.8), 0)
    obj('elev_sign_decal', CYN + 'cynosure_sign_b_decals_a.mesh', (0, SB + 0.31, 1.8), 0)
    decal('elev_load_sign', 'ep1\\surfaces\\textures\\decals\\signs\\warning_sign_a.mi', (SW - 0.02, cy, 1.6), [0.5, 0.5, 0.3], -90, 90)
    decal('elev_threshold', 'ep1\\environment\\decoration\\unique\\cynosure\\decals\\cynosure_01_markings_stripes_a.mi',
          (0, Y0 + 0.4, 0), [2.2, 0.5, 0.5], 0)
    # spec 14: one cold white ceiling practical, one dim amber panel light, red emergency pulse
    light('elev_white', (0, cy, 3.4), (1.0, 0.88, 0.7), 40, 6)   # v24: warm dirty utility light (motel match)
    light('elev_amber', (1.1, yf - 0.6, 1.5), (1.0, 0.55, 0.15), 8, 2)
    light('elev_red', (-1.3, yf - 0.5, 2.6), (1.0, 0.12, 0.08), 25, 4, flicker={'period': 1.6, 'strength': 0.7, 'offset': 0.0})
    audio('aud_elev_hum', 'amb_bl_g_airvents_med', (0, cy, 3.5), 6)
    # collision: shaft box (cab floor at z 0, walls, ceiling)
    my = (yf + SB) / 2
    col('elev_col_floor', (0, my, -0.1), [2 * SW, yf - SB, 0.2])
    col('elev_col_cabback', (0, cy - 2.3, 1.5), [2 * SW, 0.1, 3.0])
    col('elev_col_back', (0, SB - 0.15, 2.2), [2 * SW, 0.3, 4.4])
    col('elev_col_l', (-SW - 0.15, my, 2.2), [0.3, yf - SB, 4.4])
    col('elev_col_r', (SW + 0.15, my, 2.2), [0.3, yf - SB, 4.4])
    col('elev_col_ceil', (0, my, 4.5), [2 * SW, yf - SB, 0.2])


def build():
    cable = find_cable()
    n_mod = int(round((Y1 - Y0) / MOD))
    variants = 'aaaaaaa'   # b/c variants have window/vent cut-outs that show the void (v2)
    # --- floor: 2 x 2 m tiles, last 1 m row is a threshold grate
    y = Y0
    while y + 2 <= Y1 - 1 + 1e-6:
        grate = int(y - Y0) in (6, 16)
        for x in (0.0, 2.0):
            res = TP + ('floor_grate_l200_w200_a.mesh' if grate else 'floor_l200_w200_a.mesh')
            obj(f'floor_{int(y - Y0):02d}_{int(x)}', res, (x, y + 2, 0))
        if not grate:   # spec drain channel at x +1.55: techpanel grate strip 0.35 wide, flush (v21 industrial gutter rendered black)
            obj(f'drain_{int(y - Y0):02d}', TP + 'floor_grate_l200_w100_a.mesh', (1.38, y + 2, 0.012), 90, scale=[1, 0.35, 0.06])
        y += 2
    for x in (0.0, 2.0):
        obj(f'floor_grate_end_{int(x)}', TP + 'floor_grate_l200_w100_a.mesh', (x, Y1, 0))
    col('col_floor', (0, (Y0 + Y1) / 2, -0.1), [2 * HW + 0.5, Y1 - Y0, 0.2])
    # --- side walls (front face assumed at local Y=0, toward the corridor)
    for m in range(n_mod):
        y0 = Y0 + m * MOD
        v = variants[m % len(variants)]
        right = TP + f'wall_h400_l300_{v}.mesh'
        left = TP + f'wall_h400_l300_{variants[(m + 3) % len(variants)]}.mesh'
        if m == 4:   # bay 'maintenance': side door on the left wall
            # left wall: yaw -90 at (-HW-T, ya) covers y ya..ya+L, face at x=-HW looking +X
            wall_l(f'wall_l_{m}_fill2', TP + 'wall_h400_l100_c.mesh', y0, 1)
            wall_l(f'wall_l_{m}_door', TP + 'wall_door_single_h400_l200_a.mesh', y0 + 1, 2, 'yellow')
            obj(f'wall_l_{m}_seal', TP + 'wall_h400_l200_a.mesh', (-HW - T - 0.02, y0 + 1), -90, 'black')
        elif m in RELIEF_L:
            wall_l(f'wall_l_{m}', TP + 'wall_h400_l300_c.mesh', y0, MOD, WALL_APP)
            obj(f'wall_l_{m}_back', TP + 'wall_h400_l300_a.mesh', (-HW - T - 0.25, y0), -90, 'black')
        else:
            wall_l(f'wall_l_{m}', left, y0, MOD, WALL_APP)
        if m in RELIEF_R:   # v17: vent cut-out variant over a black backing 0.25 m behind = recessed relief
            wall_r(f'wall_r_{m}', TP + 'wall_h400_l300_c.mesh', y0, MOD, WALL_APP)
            obj(f'wall_r_{m}_back', TP + 'wall_h400_l300_a.mesh', (HW + T + 0.25, y0 + MOD), 90, 'black')
        else:
            wall_r(f'wall_r_{m}', right, y0, MOD, 'yellow' if m == 5 else WALL_APP)
    col('col_wall_l', (-HW - 0.15, (Y0 + Y1) / 2, H / 2), [0.3, Y1 - Y0, H])
    col('col_wall_r', (HW + 0.15, (Y0 + Y1) / 2, H / 2), [0.3, Y1 - Y0, H])
    # --- south end wall (behind the arrival point)
    # v19: user asked for a door: techpanel double-door frame (X[-4,0], faces +Y) + closed Cynosure bunker slab
    obj('door_s_frame', TP + 'wall_door_double_h400_l400_a.mesh', (2.0, Y0 - T), 0, 'yellow')
    # v23: the south door is now the elevator's lower landing (spec LS_CYN_ELEV_LOWER_FRAME): slab removed, open
    col('col_wall_s_l', (-1.45, Y0 - 0.15, H / 2), [0.9, 0.3, H])
    col('col_wall_s_r', (1.45, Y0 - 0.15, H / 2), [0.9, 0.3, H])
    elevator()
    # v19: no ceiling collider before -> V could jump onto the wall tops; slab over the whole corridor closes it
    col('col_ceiling', (0, (Y0 + Y1) / 2, H + 0.2), [2 * HW + 1.0, Y1 - Y0 + 0.6, 0.4])
    # --- ceiling: 2 x 2 tiles at z H; a light panel per module on the centre line
    y = Y0
    k = 0
    while y + 2 <= Y1 + 1e-6:
        for x in (0.0, 2.0):
            obj(f'ceil_{k}_{int(x)}', TP + 'ceiling_l200_w200_a.mesh', (x, y + 2, H + 0.02))
        y += 2
        k += 1
    # light panel states per module: arrival..bulkhead (spec 32: bright, medium, bright utility, medium, dim, emphasis)
    panel = ['default', 'default', 'default', 'default', 'off', 'red', 'default']
    for m in range(n_mod):
        yc = Y0 + m * MOD + MOD / 2
        obj(f'ceil_light_{m}', TP + 'ceiling_light_l200_w100_a.mesh', (1.0, yc + 0.5, H - 0.01), 0, panel[m])
    # --- real lights (white rhythm, red accents, one fault)
    white = (0.86, 0.93, 1.0)
    level = [120, 80, 140, 70, 0, 0, 60]
    for m in range(n_mod):
        yc = Y0 + m * MOD + MOD / 2
        if level[m]:
            light(f'lgt_white_{m}', (0, yc, H - 0.3), white, level[m], 7.5,
                  {'period': 2.7, 'strength': 0.6, 'offset': 0.4} if m == 6 else None)
    red = (1.0, 0.12, 0.08)
    light('lgt_red_a', (-HW + 0.3, Y0 + 5 * MOD + 1.5, 2.9), red, 30, 5)
    light('lgt_red_b', (HW - 0.3, Y1 - 1.2, 2.9), red, 30, 5)
    light('lgt_red_c', (-HW + 0.3, Y1 - 1.2, 2.9), red, 30, 5)
    light('lgt_bulkhead', (0, Y1 - 1.0, 2.6), (1.0, 0.55, 0.2), 25, 4)
    # --- overhead cable runs in the two upper corners (spec: dense ceiling, clear head room >= 2.3 m)
    for side, x in (('l', -HW + 0.25), ('r', HW - 0.25)):
        for i in range(int(Y1 - Y0)):
            obj(f'cable_{side}_{i:02d}', cable, (x, Y0 + i, H - 0.35))
    # --- infrastructure (bay 3): second, lower pipe run on the right wall, wall duct, relay cabinet, floor grate
    for i in range(int(Y1 - Y0)):
        obj(f'pipe_r_low_{i:02d}', cable, (HW - 0.18, Y0 + i, 2.75))
    for i in range(6, 15):
        obj(f'pipe_l_low_{i:02d}', cable, (-HW + 0.18, Y0 + i, 3.05))
    # two more overhead runs either side of the light line, and cross pipes on every module joint
    for side, x in (('cl', -0.75), ('cr', 0.55)):
        for i in range(int(Y1 - Y0)):
            obj(f'pipe_{side}_{i:02d}', cable, (x, Y0 + i, H - 0.2))
    for m in range(1, n_mod):
        for k in range(4):   # yaw 90: local +Y -> world -X, so start at the right wall
            obj(f'pipe_x_{m}_{k}', cable, (HW - k * 1.0, Y0 + m * MOD, H - 0.45), 90)
    ya = Y0 + 2 * MOD
    # v8: one duct between the ribs (local X[-2,0] -> world y ya+0.3..ya+2.3), clear of the relay cabinet
    obj('duct_r_a', TP + 'duct_h150_l200_a.mesh', (HW + 0.0, ya + 2.3, 1.4), 90, 'baremetal')   # face -X
    # v21 spec B3 cable tray: perforated techpanel grate scaled to 0.45 x 2.8 x 0.05, under the left overhead run,
    # two cable bundles on it, four hanger rods to the ceiling
    obj('tray_b3', TP + 'floor_grate_l300_w100_a.mesh', (-1.45, ya + 2.9, 3.0), 90, scale=[0.933, 0.45, 0.25])
    for j, x in enumerate((-1.34, -1.12)):
        obj(f'tray_cable_{j}', cable, (x, ya + 0.1, 3.06), 0, scale=[0.5, 2.8, 0.5])
    for j, (x, y) in enumerate(((-1.43, 0.5), (-1.02, 0.5), (-1.43, 2.5), (-1.02, 2.5))):
        obj(f'tray_rod_{j}', cable, (x, ya + y, 3.0), 0, pitch=90, scale=[0.12, 0.8, 0.12])
    # fuse box: X[-0.11,0.36] Y[+-0.65] Z[0,1.67]; v8 backs flush on the wall, centred between ribs (were
    # free-standing 0.3 m off the wall and read as black monoliths in the lane)
    obj('relay_cab_a', FUSE, (HW - 0.11, Y0 + 3 * MOD + 1.5, 0), 180)
    obj('relay_cab_b', FUSE, (-HW + 0.11, Y0 + 2 * MOD + 1.5, 0), 0)
    # --- ribs (spec: 7 frames, 0.30 deep): techpanel pillar 0.6 x 0.6 (X,Y[-0.55,0.05]) half sunk into the wall,
    # 0.25 m proud of the panel face, on every module joint
    for m in range(1, n_mod):
        yj = Y0 + m * MOD
        obj(f'rib_r_{m}', TP + 'pillar_h400_l50_a.mesh', (HW + 0.3, yj + 0.25, 0), 0, 'annodised_dark')
        obj(f'rib_l_{m}', TP + 'pillar_h400_l50_a.mesh', (-HW - 0.3, yj - 0.25, 0), 180, 'annodised_dark')
    # loose props (spec 65: start with three; keep the side door sweep y 2..4 clear)
    cases = 'base\\environment\\decoration\\containers\\cases\\'
    obj('toolbox_a', TOOLBOX, (-HW + 0.45, Y0 + 4 * MOD + 3.6, 0), 12, 'red')
    obj('case_rugged_b', cases + 'military_case\\military_case_b.mesh', (-HW + 0.33, Y0 + 4 * MOD + 0.8, 0), 90, 'default_LED_RED')
    obj('case_rugged_a', cases + 'military_case\\military_case_a.mesh', (HW - 0.33, Y1 - 4.0, 0), -88, 'grey')
    obj('toolbox_c', cases + 'toolbox\\toolbox_c.mesh', (HW - 0.35, Y1 - 5.0, 0), 4)
    # spec 65: coiled cable by the side door, a vent grille pulled off and leaned on the left wall (bay 5)
    obj('cable_coil', 'base\\environment\\decoration\\industrial\\equipment\\cable_coil\\cable_coil_a.mesh',
        (-HW + 0.45, Y0 + 4 * MOD - 1.0, 0), 30)
    # ceiling vent tile X[-1,0] Y[-1,0] Z[0,0.08]: stood up, face toward +X, foot 0.25 m off the wall
    obj('grille_loose', TP + 'ceiling_vent_l100_w100_a.mesh', (-HW + 0.3, Y1 - 3.4, 0.0), 0, 'black', 0, 75)
    # --- wetness (spec 18-19): puddles in the low spots that lead to the grates, dark wet bands at the wall bases
    puddle = DEC + 'wetness\\puddle_rough_a.mi'
    puddle_d = DEC + 'wetness\\puddle_rough_a_dirty.mi'
    wet = DEC + 'wetness\\wetness_black_a.mi'
    decal('wet_puddle_b1', puddle, (0.3, Y0 + 2.2, 0), [1.8, 2.6, 0.6], 15)
    decal('wet_puddle_b3', puddle_d, (-0.4, Y0 + 5.2, 0), [2.2, 1.6, 0.6], -10)
    decal('wet_puddle_b3b', puddle, (0.6, Y0 + 9.4, 0), [1.4, 2.4, 0.6], 40)
    decal('wet_puddle_b5', puddle_d, (0.9, Y0 + 15.0, 0), [1.6, 2.8, 0.6], 5)
    decal('wet_puddle_b6', puddle, (-0.2, Y1 - 2.4, 0), [2.6, 2.0, 0.6], 0)
    for k, yy in enumerate((Y0 + 4.5, Y0 + 11.5, Y0 + 17.5)):
        decal(f'wet_base_r_{k}', wet, (HW - 0.3, yy, 0), [0.9, 5.0, 0.6])
        decal(f'wet_base_l_{k}', wet, (-HW + 0.3, yy + 1.5, 0), [0.7, 3.5, 0.6])
    # --- markings: one floor arrow at arrival, caution lettering before the bulkhead, two wall warnings
    if 0: decal('mark_arrow', DEC + 'industrial\\industrial_symbols_arrow.mi', (0, Y0 + 1.6, 0), [1.0, 1.0, 0.5], 0)
    decal('mark_caution', DEC + 'industrial\\industrial_lettering_caution.mi', (0, Y1 - 2.3, 0), [2.4, 0.8, 0.5], 0)
    decal('mark_volt', DEC + 'signs\\danger_horiz_high_volt_a_d.mi', (HW - 0.02, Y0 + 3 * MOD + 1.5, 2.2), [0.9, 0.4, 0.3], -90, 90)
    decal('mark_warn', 'ep1\\surfaces\\textures\\decals\\signs\\warning_sign_a.mi', (-HW + 0.02, Y0 + 5 * MOD + 1.5, 1.7), [0.6, 0.6, 0.3], 90, 90)
    # --- water drips over the puddles, low steam at the infrastructure grate
    drip = 'ep1\\fx\\enviroment\\water\\e_water_dripping_low.particle'
    fx('fx_drip_a', drip, (0.4, Y0 + 9.4, H - 0.3))
    fx('fx_drip_b', drip, (0.9, Y0 + 15.0, H - 0.3))
    fx('fx_drip_c', drip, (-0.3, Y1 - 2.2, H - 0.3))
    fx('fx_steam_grate', 'base\\fx\\environment\\smoke\\e_steam_interior_grate_strong.particle', (1.0, Y0 + 7.0, 0.05), 0, [0.5, 0.5, 0.5])
    # --- Cynosure identity (bay 2, left wall, eye height); plates face +Y, so yaw -90 faces +X
    yc = Y0 + 1 * MOD + MOD / 2
    # plate/decal front is local -Y (v3: yaw -90 showed the black back), so yaw 90 turns it to +X
    obj('sign_cyn_plate', CYN + 'cynosure_sign_a_plate_a.mesh', (-HW + 0.03, yc, 2.0), 90)
    # Cynosure decal meshes face local +Y (verified v5): yaw -90 on the left wall faces +X
    obj('sign_cyn_decal', CYN + 'cynosure_sign_a_decals_a.mesh', (-HW + 0.05, yc, 2.0), -90)
    # v8: chevron moved off the rib at y -8 into the arrival bay, under the light box
    obj('sign_cyn_chevron', CYN + 'cynosure_sign_e.mesh', (-HW + 0.04, Y0 + 1.6, 1.6), -90)
    # vertical Cynosure plate on the bulkhead frame (faces -Y = yaw 180)
    obj('sign_bulk_plate', CYN + 'cynosure_sign_b_plate_a.mesh', (1.45, Y1 - 0.27, 1.7), 180)
    obj('sign_bulk_decal', CYN + 'cynosure_sign_b_decals_a.mesh', (1.45, Y1 - 0.28, 1.7), 180)
    # Cynosure light boxes as visible wall practicals (front local +Y)
    box = CYN + 'cynosure_light_box_b.mesh'
    obj('lbox_l_b1', box, (-HW, Y0 + 1.6, 2.7), -90)
    obj('lbox_r_b3', box, (HW, Y0 + 2 * MOD + 0.6, 2.95), 90)
    obj('lbox_l_b4', box, (-HW, Y0 + 3 * MOD + 1.5, 2.7), -90)
    obj('lbox_r_b6', box, (HW, Y1 - 2.0, 2.7), 90)
    # --- bulkhead: 4 m techpanel double-door wall as the frame (yellow), the Cynosure bunker door slab jammed
    # ~2.35 m open in front of it, amber status lamp. The M3 checkpoint doorway behind it is x -1..1, 2.2 m high.
    obj('bulkhead_frame', TP + 'wall_door_double_h400_l400_a.mesh', (-2.0, Y1), 180, 'yellow')
    obj('bulkhead_main', DOOR + 'door_int_mlt_bunker_b.mesh', (0, Y1 - 0.62, 2.62), 180)
    col('col_wall_n_l', (-1.45, Y1 - 0.15, H / 2), [0.9, 0.3, H])
    col('col_wall_n_r', (1.45, Y1 - 0.15, H / 2), [0.9, 0.3, H])
    # v8: dead access reader on the left jamb (thin axis = local X, so yaw -90 turns its face to -Y)
    obj('access_reader', 'base\\environment\\decoration\\electronics\\security\\hand_scanner\\hand_scanner_a.mesh',
        (-1.45, Y1 - 0.29, 1.1), -90)
    # caged red lamp housings at the red light positions (warning_light is a 0.32 m housing, centred pivot)
    for i, (x, yy) in enumerate(((-HW + 0.17, Y0 + 5 * MOD + 1.5), (HW - 0.17, Y1 - 1.2), (-HW + 0.17, Y1 - 1.2))):
        obj(f'lamp_red_{i}', 'base\\lighting\\warning_light.mesh', (x, yy, 2.9))
    # low amber floor-edge glow (concepts): 4 small lights at the wall bases in the last two bays
    for i, (x, yy) in enumerate(((-HW + 0.15, Y1 - 6.5), (HW - 0.15, Y1 - 5.5), (-HW + 0.15, Y1 - 2.5), (HW - 0.15, Y1 - 2.0))):
        light(f'lgt_amber_floor_{i}', (x, yy, 0.12), (1.0, 0.5, 0.12), 6, 1.6)
    # --- v11 spec gaps: B2 hazard band + section "A1", B5 clearance plates + doubled ribs, bulkhead floor band,
    # amber status lamp housing, low mist at the bulkhead. Wall decals project along local -Z (floor: down), so
    # left wall = yaw 90, right wall = yaw -90, pitch 90 (v11: the opposite signs projected into the air).
    CD = 'ep1\\environment\\decoration\\unique\\cynosure\\decals\\cynosure_01_'
    IND = DEC + 'industrial\\industrial_'
    decal('band_b2_l', CD + 'markings_stripes_a.mi', (-HW + 0.02, Y0 + MOD + 1.5, 0.35), [2.4, 0.6, 0.3], 90, 90)
    decal('band_b2_r', CD + 'markings_stripes_a.mi', (HW - 0.02, Y0 + MOD + 1.5, 0.35), [2.4, 0.6, 0.3], -90, 90)
    decal('sect_a', IND + 'lettering_large_a_white.mi', (-HW + 0.02, Y0 + MOD + 0.55, 1.15), [0.5, 0.5, 0.3], 90, 90)
    decal('sect_1', IND + 'numbers_large_1_white.mi', (-HW + 0.02, Y0 + MOD + 0.95, 1.15), [0.5, 0.5, 0.3], 90, 90)
    decal('plate_clear_r', IND + 'lettering_personnel_only_a.mi', (HW - 0.02, Y0 + 5 * MOD + 1.5, 1.9), [0.95, 0.33, 0.3], -90, 90)
    decal('plate_noentry_l', CD + 'no_entry_a.mi', (-HW + 0.02, Y0 + 6 * MOD + 0.9, 1.7), [0.8, 0.8, 0.3], 90, 90)
    decal('band_bulk_floor', CD + 'markings_stripes_b.mi', (0, Y1 - 1.3, 0), [3.6, 0.5, 0.5], 0)
    for jm, dy in ((5, 0.7), (6, -0.7)):   # bay 5 heavier framing: a second rib inside each joint
        yj = Y0 + jm * MOD + dy
        obj(f'rib2_r_{jm}', TP + 'pillar_h400_l50_a.mesh', (HW + 0.3, yj + 0.25, 0), 0, 'annodised_dark')
        obj(f'rib2_l_{jm}', TP + 'pillar_h400_l50_a.mesh', (-HW - 0.3, yj - 0.25, 0), 180, 'annodised_dark')
    obj('lamp_amber', 'base\\lighting\\warning_light.mesh', (1.45, Y1 - 0.35, 3.0))
    light('lgt_amber_status', (1.45, Y1 - 0.55, 3.0), (1.0, 0.55, 0.15), 12, 2.5)
    fx('fx_mist_bulk', 'base\\fx\\environment\\smoke\\e_steam_floor_spread_subtle.particle', (0, Y1 - 1.2, 0.05))
    # --- v15 detail pass (user: "looks empty"): the walls were bare between 0 and 2.4 m. Wall conduits (pipes run
    # local +Y from the origin), cable risers beside the ribs, small wall boxes, vents, extinguishers, barrels, lane
    # edge lines and grime. Skip ranges keep the runs out of the cabinets, duct, signs, side door and loose grille.
    IND_ = DEC + 'industrial\\industrial_'
    IP = 'base\\environment\\decoration\\industrial\\pipes\\'
    elbow = IP + 'pipes_small_01\\pipes_small_01_e.mesh'   # runs +Y 0.62, bends +X 0.5 (v16: caps the open stubs)
    def run(tag, res, x, z, step, skips, app, side=0):
        y, prev = Y0 + 0.3, False
        while y + step <= Y1 - 0.6:
            ok = not any(a < y + step and y < b for a, b in skips)
            if ok:
                obj(f'{tag}_{int((y - Y0) * 10):03d}', res, (x, y, z), 0, app)
            if side and ok != prev:   # group edge: elbow into the wall; start points back (-Y) from y, end forward
                obj(f'{tag}_elb_{int((y - Y0) * 10):03d}', elbow, (x, y, z), 180 if ok else 0, app, 0,
                    (180 if side < 0 else 0) if not ok else (0 if side < 0 else 180))
            prev = ok
            y += step
        if side and prev:
            obj(f'{tag}_elb_end', elbow, (x, y, z), 0, app, 0, 180 if side < 0 else 0)
    small, tiny = IP + 'pipes_small_01\\pipes_small_01_b.mesh', IP + 'pipes_smallest_01\\pipes_smallest_01_b.mesh'
    sk_l = [(Y0 + 3.3, Y0 + 4.2), (Y0 + 6.8, Y0 + 8.2), (Y0 + 12.9, Y0 + 15.1), (Y0 + 16.8, Y0 + 18.6)]
    sk_r = [(Y0 + 6.2, Y0 + 8.4), (Y0 + 9.8, Y0 + 11.2), (Y0 + 15.8, Y0 + 17.2)]
    run('cond_l', small, -HW + 0.13, 0.85, 1.0, sk_l, 'metal', -1)
    run('cond_r', small, HW - 0.13, 1.85, 1.0, sk_r, 'metal', 1)
    for k, z in enumerate((0.1, 0.24)):
        run(f'flr_l{k}', tiny, -HW + 0.08, z, 1.03, sk_l, 'black')
        run(f'flr_r{k}', tiny, HW - 0.08, z, 1.03, sk_r[1:], 'black')
    # v16: cable_fusebox_small risers dropped (read as two stray white strips). Section stencils A2..A6 at the start of
    # each bay, high on the left wall (A1 is the large one in the identity bay); warning symbol over the drums.
    for m in ():   # v19: user wants only A1 (one location label); A2..A6 dropped
        y0 = Y0 + m * MOD + (1.0 if m == 5 else 0.55)   # bay 5: clear of the doubled rib
        decal(f'sect_a{m}', IND_ + 'lettering_large_a_white.mi', (-HW + 0.02, y0, 2.4), [0.32, 0.32, 0.3], 90, 90)
        decal(f'sect_n{m}', IND_ + f'numbers_large_{m}_white.mi', (-HW + 0.02, y0 + 0.3, 2.4), [0.32, 0.32, 0.3], 90, 90)
    decal('sym_warn_drums', IND_ + 'symbol_warning_e.mi', (HW - 0.02, Y0 + 12.9, 1.45), [0.35, 0.35, 0.3], -90, 90)
    ebox = 'base\\environment\\decoration\\electronics\\devices\\electric_box_entropy\\electric_box_entropy_a_case.mesh'
    for i, yy in enumerate((Y0 + 10.5, Y0 + 19.6)):
        obj(f'ebox_l_{i}', ebox, (-HW, yy, 1.25), 90)
    for i, yy in enumerate((Y0 + 1.2, Y0 + 13.5)):
        obj(f'ebox_r_{i}', ebox, (HW, yy, 1.3), -90)
    obj('intercom_r', 'base\\environment\\decoration\\electronics\\devices\\device_neomilitary\\device_neomilitary_d_intercom.mesh',
        (HW, Y0 + 2.2, 1.45), 0)
    vent = 'base\\environment\\decoration\\public_utility\\vents\\wall_vents\\wall_vent_01_a.mesh'
    for i, yy in enumerate((Y0 + 1.0, Y0 + 10.0)):
        obj(f'vent_l_{i}', vent, (-HW + 0.01, yy, 0.5), -90, 'metal_dark')
    ext = 'base\\environment\\decoration\\industrial\\equipment\\fire_extinguisher\\fire_extinguisher_a.mesh'
    obj('ext_r', ext, (HW - 0.3, Y0 + 1.9, 0), 0)
    obj('ext_l', ext, (-HW + 0.3, Y0 + 9.6, 0), 0)
    drum = 'base\\environment\\decoration\\containers\\barrel\\drum\\barrel_drum_a.mesh'
    obj('drum_a', drum, (HW - 0.35, Y0 + 12.6, 0), 20)
    obj('drum_b', drum, (HW - 0.38, Y0 + 13.25, 0), 75)
    strip = DEC + 'megabuiding\\strip\\decal_strip_yellow_d.mi'
    for yy in (1, 3, 5, 9, 11, 13, 15, 19):
        for s, x in (('l', -1.25), ('r', 1.25)):
            decal(f'lane_{s}_{yy:02d}', strip, (x, Y0 + yy, 0), [0.1, 1.9, 0.5], 0)
    DT = DEC + 'dirt\\'
    decal('dirt_b4', DT + 'dirt_p_dark.mi', (0.0, Y0 + 12.5, 0), [1.5, 2.0, 0.5], 30)
    decal('dirt_b2', DT + 'dust_patch_01_dark.mi', (-0.5, Y0 + 4.5, 0), [1.6, 1.6, 0.5], -20)
    decal('oil_drums', DT + 'oil_trail_asphalt_a.mi', (1.1, Y0 + 13.0, 0), [0.8, 1.6, 0.5], 20)
    decal('rust_l_b4', DT + 'rust_leak_a.mi', (-HW + 0.02, Y0 + 10.9, 1.4), [0.4, 1.2, 0.3], 90, 90)
    decal('rust_r_b5', DT + 'rust_leak_a.mi', (HW - 0.02, Y0 + 14.2, 1.2), [0.4, 1.4, 0.3], -90, 90)
    # --- audio (spec 38): drips at the drip FX, steam at the grate, vent hum, fault-light flicker, relay buzz
    audio('aud_drip_a', 'amb_g_fx_water_drip_medium_04_close', (0.4, Y0 + 9.4, H - 0.5), 6)
    audio('aud_drip_b', 'amb_g_fx_water_drip_medium_01', (0.9, Y0 + 15.0, H - 0.5), 6)
    audio('aud_drip_c', 'amb_g_fx_water_drip_medium_02_far', (-0.3, Y1 - 2.2, H - 0.5), 6)
    audio('aud_steam', 'amb_g_fx_steam_small_02_loop', (1.0, Y0 + 7.0, 0.2), 6)
    audio('aud_vent', 'amb_bl_g_airvents_med', (HW - 0.3, Y0 + 2 * MOD + 1.3, 2.1), 9)
    audio('aud_flicker', 'amb_g_city_el_neon_high_03_flicker', (0, Y0 + 6 * MOD + 1.5, H - 0.3), 7)
    audio('aud_relay', 'amb_int_EM_elem_electronic_circuit_buzz_loop_01_low', (HW - 0.4, Y0 + 3 * MOD + 1.5, 1.0), 5)

    if os.environ.get('CYN_LINEUP'):   # elevator asset lineup in the void south of the corridor (test only)
        E = 'base\\environment\\architecture\\watson\\north_harbor\\meat_factory\\elevator\\wat_nhr_maelstrom_hideout_elevator_'
        PU = 'base\\items\\interactive\\public_utility\\int_public_utility_002__elevator_industrial\\int_public_utility_002__elevator_industrial_'
        Q5 = 'ep1\\environment\\decoration\\unique\\quest\\q305\\q305_bunker_elevator\\bunker_elevator'
        cands = [('lu_pu_front', PU + 'front.mesh'), ('lu_pu_back', PU + 'back.mesh'),
                 ('lu_q305', Q5 + '.mesh'), ('lu_q305_panel', Q5 + '_panel.mesh'),
                 ('lu_mael_rails', E + 'rails_structure_a.mesh'),
                 ('lu_mb_rails', 'base\\environment\\architecture\\megabuilding\\structural\\elevator\\common_megabuilding_elevator_a_rails_a.mesh')]
        for k, (i, r) in enumerate(cands):
            x = -15 + 6 * k
            obj(i, r, (x, Y0 - 14, 0), 0, 'yellow' if 'tp_' in i else 'default')
            light(i + '_l', (x, Y0 - 9, 3.0), (1.0, 0.96, 0.9), 40, 12)
        col('lu_floor', (-0, Y0 - 14, -0.1), [40, 14, 0.2])

    doc = {
        'edl': 1, 'id': 'cyn_entrance', 'name': 'Cynosure Entrance Access Corridor',
        'origin': {'position': [-1908, -2470, -300], 'yaw': 0},
        'streaming': {'category': 'interior', 'level': 1, 'cell': [64, 64, 32], 'range': 400},
        'objects': objs, 'lights': lights, 'collisions': cols, 'vfx': vfx,
        'audio': {'emitters': audios},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    yaml.safe_dump(doc, open(OUT, 'w'), sort_keys=False, width=200)
    print(f'{OUT}: {len(objs)} objects, {len(lights)} lights, {len(cols)} collisions, {len(vfx)} vfx')


if __name__ == '__main__':
    build()
