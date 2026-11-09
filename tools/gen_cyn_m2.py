#!/usr/bin/env python3
"""Cynosure M2: derive cynosure_m2.edl.yaml from the M1 greybox.

Adds, built from the room kit's own vanilla int_common_a meshes (so textures match the M1 walls):
  - a vanilla framed door piece on each room's side of every door slot (the kit's door role is never
    exported, so M1 doorways were full-height 2 m gaps), plus kit wall above 3.8 m in taller rooms;
  - a round hall inside the 40x40 Predictive Core: a ring of tangent kit wall pieces, door pieces at
    its openings, and short lined passages from those openings to the square's doors.
Collision is separate EDL boxes. M1 stays untouched; rerun this after editing M1.
(An LS procedural-geometry version was tried first: its box-projected UVs smear the kit's multilayer
mask, see D195/D196.)
"""
import math, re, sys, yaml
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / 'source' / 'cynosure'
class NoAlias(yaml.SafeDumper):
    def ignore_aliases(self, data): return True

M1, M2 = SRC / 'cynosure_m1.edl.yaml', SRC / 'cynosure_m2.edl.yaml'
ANCHOR_DOC = SRC.parent.parent / 'docs' / 'cynosure_import' / 'CYNOSURE_ANCHORS_AND_TRANSFORMS.md'
ANCHORS = SRC / 'cynosure_anchors_measured.yaml'

KIT = 'base\\environment\\architecture\\common\\int\\int_common_a\\'
WALL = KIT + 'int_common_a_wall_h400_l200_a.mesh'              # 2 x 0.23 x 3.8 m, pivot at the max-x corner
DOOR = KIT + 'int_common_a_wall_door_single_h400_l200_a.mesh'  # same size; framed hole x -1.74..-0.26, z 0..2.49
CEIL = KIT + 'int_common_a_ceiling_tiles_b_l300_w200_a.mesh'   # 3 x 2 m, pivot at the max corner
KIT_H, KIT_D = 3.8, 0.23          # native height and depth of WALL/DOOR
HOLE_HALF, HOLE_TOP = 0.74, 2.5   # DOOR's opening: half-width, height
CORE_ID = 'CYN_ROOM_14_CORE'
RING_R, RING_N = 19.2, 32         # ring line (kit depth goes inward from it), sides
# wall pieces face into their room: local +y is the textured side
INTO_ROOM_YAW = {'north': 180, 'south': 0, 'east': 90, 'west': -90}

def r(v): return round(v, 3)

def rot(yaw, x, y):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return x * c - y * s, x * s + y * c

def piece(pid, mesh, cx, cy, yaw, width, z0, height):
    """A kit piece whose span is centred on (cx, cy) along its local x, bottom at z0, facing local +y."""
    ox, oy = rot(yaw, width / 2, 0)          # the pivot is the max-x end of a [-2, 0] span
    return {'id': pid, 'resource': mesh, 'appearance': 'default', 'at': [r(cx + ox), r(cy + oy), r(z0)],
            'yaw': r(yaw), 'scale': [r(width / 2), 1, r(height / KIT_H)]}

def box(bid, cx, cy, yaw, sx, sy, z0, sz):
    return {'id': bid, 'shape': 'box', 'at': [r(cx), r(cy), r(z0 + sz / 2)], 'yaw': r(yaw), 'size': [r(sx), r(sy), r(sz)]}

def room_doors(doc):
    floor_h = {f['id']: f.get('height', 5) for f in doc['floors']}
    for f in doc['floors']:
        for room in f['rooms']:
            (cx, cy), (w, d) = room['at'], room['size']
            for door in room.get('doors', []):
                off, wall = door.get('offset', 0), door['wall']
                x, y = {'north': (cx + off, cy + d / 2), 'south': (cx + off, cy - d / 2),
                        'east': (cx + w / 2, cy + off), 'west': (cx - w / 2, cy + off)}[wall]
                yield room, room.get('height', floor_h[f['id']]), wall, x, y

def doorways(doc):
    """Door piece (+ wall above 3.8 m) on each room's side of each slot; one collision set per slot."""
    objs, cols, slots = [], [], {}
    for room, h, wall, x, y in room_doors(doc):
        tag = room['id'].split('_')[2] + '_' + wall[0]
        yaw = INTO_ROOM_YAW[wall]
        objs.append(piece(f'door_{tag}', DOOR, x, y, yaw, 2.0, 0, KIT_H))
        if h > KIT_H:
            objs.append(piece(f'door_{tag}_above', WALL, x, y, yaw, 2.0, KIT_H, h - KIT_H))
        s = slots.setdefault((r(x), r(y)), {'x': x, 'y': y, 'yaw': 0 if wall in ('north', 'south') else 90, 'h': 0, 'tag': tag})
        s['h'] = max(s['h'], h)
    for s in slots.values():
        jw = 1.0 - HOLE_HALF
        for side in (-1, 1):
            jx, jy = rot(s['yaw'], side * (HOLE_HALF + jw / 2), 0)
            cols.append(box(f"col_{s['tag']}_{'lr'[side > 0]}", s['x'] + jx, s['y'] + jy, s['yaw'], jw, 2 * KIT_D, 0, s['h']))
        cols.append(box(f"col_{s['tag']}_top", s['x'], s['y'], s['yaw'], 2 * HOLE_HALF, 2 * KIT_D, HOLE_TOP, s['h'] - HOLE_TOP))
    return objs, cols

def core_ring(core, h):
    """Kit pieces around the core centre (core room frame), facing inward; door pieces face the square's doors."""
    seg = 2 * RING_R * math.tan(math.pi / RING_N) + 0.04
    door_deg = {'south': 270, 'east': 0, 'north': 90, 'west': 180}
    doors = {door_deg[d['wall']] for d in core.get('doors', [])}
    objs, cols = [], []
    def at(th, radial, tangent):
        c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
        return radial * c - tangent * s, radial * s + tangent * c
    for i in range(RING_N):
        th = 360 * i / RING_N
        yaw = th + 90                                    # local +y points at the centre
        cx, cy = at(th, RING_R, 0)
        if round(th) % 360 in doors:
            side = (seg - 2.0) / 2
            objs.append(piece(f'ring_{i:02d}_door', DOOR, cx, cy, yaw, 2.0, 0, KIT_H))
            objs.append(piece(f'ring_{i:02d}_above', WALL, cx, cy, yaw, seg, KIT_H, h - KIT_H))
            for k, sg in (('a', 1), ('b', -1)):
                px, py = at(th, RING_R, sg * (1.0 + side / 2))
                objs.append(piece(f'ring_{i:02d}_{k}', WALL, px, py, yaw, side, 0, KIT_H))
            # collision: jambs, header
            for k, sg in (('a', 1), ('b', -1)):
                jw = seg / 2 - HOLE_HALF
                px, py = at(th, RING_R - KIT_D / 2, sg * (HOLE_HALF + jw / 2))
                cols.append(box(f'col_ring_{i:02d}_{k}', px, py, yaw, jw, KIT_D, 0, h))
            px, py = at(th, RING_R - KIT_D / 2, 0)
            cols.append(box(f'col_ring_{i:02d}_top', px, py, yaw, 2 * HOLE_HALF, KIT_D, HOLE_TOP, h - HOLE_TOP))
        else:
            objs.append(piece(f'ring_{i:02d}', WALL, cx, cy, yaw, seg, 0, h))
            px, py = at(th, RING_R - KIT_D / 2, 0)
            cols.append(box(f'col_ring_{i:02d}', px, py, yaw, seg, KIT_D, 0, h))
    # passage: from the ring line out to the core-side face of the square wall's door piece
    outer = core['size'][0] / 2 - KIT_D
    gap, mid = outer - RING_R, (outer + RING_R) / 2
    for th in sorted(doors):
        for k, sg in (('a', 1), ('b', -1)):
            px, py = at(th, mid, sg * (HOLE_HALF + 0.02))
            # the wall runs radially; its textured side (+y) faces the passage axis
            objs.append(piece(f'pass_{th}_{k}', WALL, px, py, th + (90 if sg > 0 else -90) + 90, gap, 0, HOLE_TOP + 0.1))
            px, py = at(th, mid, sg * (HOLE_HALF + 0.12))
            cols.append(box(f'col_pass_{th}_{k}', px, py, th, gap + 0.1, 0.2, 0, HOLE_TOP + 0.1))
        px, py = at(th, mid, 0)
        cols.append(box(f'col_pass_{th}_top', px, py, th, gap + 0.1, 2 * HOLE_HALF + 0.4, HOLE_TOP, 0.2))
        # ceiling tile under the roof, axis-aligned: pivot at its max corner
        ext = [(min(a, b), max(a, b)) for a, b in zip(at(th, RING_R, -HOLE_HALF - 0.1), at(th, outer, HOLE_HALF + 0.1))]
        (x0, x1), (y0, y1) = ext
        objs.append({'id': f'pass_{th}_ceil', 'resource': CEIL, 'appearance': 'default', 'at': [r(x1), r(y1), HOLE_TOP],
                     'yaw': 0, 'scale': [r((x1 - x0) / 3), r((y1 - y0) / 2), 1]})
    for o in objs + cols:
        o['room'] = core['id']
    return objs, cols

# EDL room order -> anchor room key (CYNOSURE_ANCHORS_AND_TRANSFORMS.md naming)
ROOM_KEYS = ['ENTRY', 'CHECKPOINT', 'FLOODED', 'MAINT_SIDE', 'PUMP', 'SECURITY', 'SECURITY_OFFICE', 'BIOMETRIC',
             'OBSERVATION', 'SUBJECT_RECORDS', 'ARCHIVE', 'PURGE', 'PREDICTION', 'ECHO', 'COFFINS', 'COMPARISON',
             'SERVERS', 'CORE_ANTE', 'CORE', 'ENDING', 'ESCAPE']
TRAVEL_YAW = {'north': 0, 'west': 90, 'south': 180, 'east': -90}   # CP2077 yaw 0 faces +Y

def measure_anchors(doc):
    """Structural anchors derived from the EDL: origins, main connections, room entry/exit. World coords."""
    known = set(re.findall(r'\bANCHOR_[A-Z0-9_]+', ANCHOR_DOC.read_text()))
    (ox, oy, oz), oyaw = doc['origin']['position'], doc['origin'].get('yaw', 0)
    assert oyaw == 0, 'anchor maths assumes an unrotated CYN frame'
    rooms = [rm for f in doc['floors'] for rm in f['rooms']]
    assert len(rooms) == len(ROOM_KEYS)
    key = {rm['id']: k for rm, k in zip(rooms, ROOM_KEYS)}
    out = {}
    def put(aid, x, y, yaw, how):
        if aid in known:
            out[aid] = {'position': [r(ox + x), r(oy + y), oz], 'yaw': yaw, 'status': 'MEASURED', 'from': how}
    put('ANCHOR_CYN_WORLD_ORIGIN', 0, 0, 0, 'EDL origin')
    put('ANCHOR_CYN_FORWARD_REFERENCE', 0, 10, 0, 'EDL origin + 10 m along +Y (canonical route)')
    main = [rm for rm in rooms if not re.search(r'_\d+A_', rm['id'])]
    for rm in rooms:
        put(f"ANCHOR_CYN_{key[rm['id']]}_ORIGIN", *rm['at'], 0, f"{rm['id']} centre, floor")
    for a, b in zip(main, main[1:]):
        for d in a.get('doors', []):
            (cx, cy), (w, dd), off = a['at'], a['size'], d.get('offset', 0)
            x, y = {'north': (cx + off, cy + dd / 2), 'south': (cx + off, cy - dd / 2),
                    'east': (cx + w / 2, cy + off), 'west': (cx - w / 2, cy + off)}[d['wall']]
            bx, by = b['at']; bw, bd = b['size']
            if abs(x - bx) <= bw / 2 + 0.01 and abs(y - by) <= bd / 2 + 0.01:   # door lies on b's boundary
                t = TRAVEL_YAW[d['wall']]
                put(f"ANCHOR_CYN_{key[a['id']]}_TO_{key[b['id']]}", x, y, t, f"door slot {a['id']} -> {b['id']}")
                ux, uy = -math.sin(math.radians(t)), math.cos(math.radians(t))
                put(f"ANCHOR_CYN_{key[a['id']]}_EXIT", x - ux, y - uy, t, 'exit door, 1 m inside')
                put(f"ANCHOR_CYN_{key[b['id']]}_ENTRY", x + ux, y + uy, t, 'entry door, 1 m inside')
    return out

def main():
    doc = yaml.safe_load(M1.read_text())
    doc['name'] = 'Cynosure M2'   # id stays cynosure_m1: re-applying replaces the M1 build in place
    doc['scene']['name'] = 'Cynosure M2'
    core = next(rm for f in doc['floors'] for rm in f['rooms'] if rm['id'] == CORE_ID)
    core_h = core.get('height', 5)
    # corner work lights sat at radius 21 m, outside the ring: pull them inside
    for light in core['lights']:
        if light['id'] in ('core_ring', 'core_ring2'):
            light['at'][0] = -11
            light['at'][1] = -11 if light['id'] == 'core_ring' else 11
            light['repeat']['step'] = [22, 0, 0]
    d_objs, d_cols = doorways(doc)
    r_objs, r_cols = core_ring(core, core_h)
    doc.setdefault('objects', []).extend(d_objs + r_objs)
    doc.setdefault('collisions', []).extend(d_cols + r_cols)
    # the M1 core camera stood at 22.7 m from the centre, outside the new 19 m ring
    for cam in doc['cameras']:
        if cam['id'] == 'cyn_cam_core':
            cam['at'] = [-9, 299, 3]
    M2.write_text('# GENERATED by tools/gen_cyn_m2.py from cynosure_m1.edl.yaml; do not edit by hand.\n'
                  + yaml.dump(doc, Dumper=NoAlias, sort_keys=False, allow_unicode=True, width=140))
    anchors = measure_anchors(doc)
    ANCHORS.write_text('# GENERATED by tools/gen_cyn_m2.py: structural Cynosure anchors measured from the EDL (world coords,\n'
                       '# yaw in degrees, CP2077 yaw 0 = +Y). Everything not listed here is still UNMEASURED.\n'
                       + yaml.dump(anchors, Dumper=NoAlias, sort_keys=True, width=140))
    print(f'{M2}: {len(d_objs) + len(r_objs)} kit meshes, {len(d_cols) + len(r_cols)} collision boxes; '
          f'{ANCHORS.name}: {len(anchors)} anchors')

if __name__ == '__main__':
    sys.exit(main())
