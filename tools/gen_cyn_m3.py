#!/usr/bin/env python3
"""Cynosure M3 dressing: cynosure_m2.edl.yaml + cynosure_m3_dressing.yaml -> cynosure_m3.edl.yaml.

Props are Starfield meshes cooked by /mnt/sata/Cyberpunk2077/starfield_kit/sf_cook.sh
(depot mod\\ash_cache\\sf\\<name>\\<name>.mesh, bounds in cooked/<name>/dims.json).
Placement is declarative per room (room frame: origin = room centre, z = floor):
  - {prop: P, wall: north|south|east|west, span: [a, b], gap: 0.3, cycle: [P2, ...], inset: 0.05}
        a row backed against the wall, facing into the room, skipping door openings
  - {prop: P, at: [x, y], yaw: deg}                      free placement (yaw 0 = front towards -Y)
  - {stack: [bot, mid, mid, top], at: [x, y], yaw: 0}    pieces stacked by their bounds
  - {prop|stack: ..., ring: {r: 6, n: 8, start: 0}, face: in|out}
  - {prop: P, wall: W, along: 0.0, z: 3.8, collide: false}  wall mount at height z
Every placed prop gets a box collision from its bounds unless collide: false. Overlaps and door
blockages are reported, not silently fixed. Also writes a top-down plan PNG for review.
    gen_cyn_m3.py [--stage]      --stage copies the used props into LocationStudio/mod_sources
"""
import json, math, os, shutil, sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'source', 'cynosure')
KIT = '/mnt/sata/Cyberpunk2077/starfield_kit/cooked'
LS_SOURCES = ('/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/bin/x64/plugins/cyber_engine_tweaks/mods/'
              'LocationStudio/mod_sources')
DEPOT = 'mod\\ash_cache\\sf\\{0}\\{0}.mesh'
# Starfield props face -Y; yaw that turns -Y into the room for a prop backed against each wall
WALL_YAW = {'north': 0, 'south': 180, 'east': -90, 'west': 90}
DOOR_CLEAR = 0.8          # keep this much free beside a door opening
DOOR_APPROACH = 1.6       # and this deep in front of it


def r(v):
    return round(float(v), 3)


def rot(yaw, x, y):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return x * c - y * s, x * s + y * c


class Dims:
    def __init__(self, fronts):
        self.cache, self.fronts = {}, fronts

    def __call__(self, name):
        if name not in self.cache:
            p = os.path.join(KIT, name, 'dims.json')
            if not os.path.exists(p):
                raise SystemExit(f'prop {name} is not cooked ({p})')
            d = json.load(open(p))
            self.cache[name] = d
        return self.cache[name]

    def yaw_fix(self, name):
        """Extra yaw so the prop's real front becomes -Y."""
        return {'-y': 0, '+y': 180, '-x': 90, '+x': -90}[self.fronts.get(name, '-y')]


class Room:
    def __init__(self, spec, floor_h):
        self.id, self.w, self.d = spec['id'], spec['size'][0], spec['size'][1]
        self.h = spec.get('height', floor_h)
        self.doors = spec.get('doors', [])
        self.boxes = []          # (id, cx, cy, hx, hy) axis-aligned footprints in room frame
        self.warn = []

    def wall_axis(self, wall):
        """(start point on wall, unit along, inward normal, wall length)"""
        w, d = self.w / 2, self.d / 2
        return {'north': ((0, d), (1, 0), (0, -1), self.w), 'south': ((0, -d), (1, 0), (0, 1), self.w),
                'east': ((w, 0), (0, 1), (-1, 0), self.d), 'west': ((-w, 0), (0, 1), (1, 0), self.d)}[wall]

    def door_spans(self, wall):
        return [(dr.get('offset', 0) - dr.get('width', 2) / 2 - DOOR_CLEAR,
                 dr.get('offset', 0) + dr.get('width', 2) / 2 + DOOR_CLEAR) for dr in self.doors if dr['wall'] == wall]

    def door_zones(self):
        out = []
        for dr in self.doors:
            (px, py), (ax, ay), (nx, ny), _ = self.wall_axis(dr['wall'])
            o, hw = dr.get('offset', 0), dr.get('width', 2) / 2 + 0.3
            cx, cy = px + ax * o + nx * DOOR_APPROACH / 2, py + ay * o + ny * DOOR_APPROACH / 2
            hx = abs(ax) * hw + abs(nx) * DOOR_APPROACH / 2
            hy = abs(ay) * hw + abs(ny) * DOOR_APPROACH / 2
            out.append((f"door_{dr['wall']}", cx, cy, hx, hy))
        return out


def footprint(d, yaw):
    """AABB half extents and centre offset of a prop's bounds after yaw (about its origin)."""
    xs, ys = (d['min'][0], d['max'][0]), (d['min'][1], d['max'][1])
    pts = [rot(yaw, x, y) for x in xs for y in ys]
    lo = (min(p[0] for p in pts), min(p[1] for p in pts))
    hi = (max(p[0] for p in pts), max(p[1] for p in pts))
    return (hi[0] - lo[0]) / 2, (hi[1] - lo[1]) / 2, (hi[0] + lo[0]) / 2, (hi[1] + lo[1]) / 2


class Builder:
    def __init__(self, dims):
        self.dims, self.objects, self.collisions, self.used, self.n = dims, [], [], set(), {}

    def uid(self, room, name):
        k = (room.id, name)
        self.n[k] = self.n.get(k, 0) + 1
        short = room.id.replace('CYN_ROOM_', '').split('_')[0].lower()
        return f'sf_{short}_{name}_{self.n[k]:02d}'

    def place(self, room, name, x, y, yaw, z=0.0, collide=True):
        d = self.dims(name)
        yaw_total = (yaw + self.dims.yaw_fix(name)) % 360
        oid = self.uid(room, name)
        self.objects.append({'id': oid, 'resource': DEPOT.format(name), 'appearance': 'default',
                             'at': [r(x), r(y), r(z)], 'yaw': r(yaw_total), 'room': room.id})
        self.used.add(name)
        hx, hy, ox, oy = footprint(d, yaw_total)
        box = (oid, x + ox, y + oy, hx, hy)
        if collide:
            for other in room.boxes + room.door_zones():
                if abs(box[1] - other[1]) < box[3] + other[3] - 0.02 and abs(box[2] - other[2]) < box[4] + other[4] - 0.02:
                    room.warn.append(f'{oid} overlaps {other[0]}')
            if abs(box[1]) + hx > room.w / 2 + 0.01 or abs(box[2]) + hy > room.d / 2 + 0.01:
                room.warn.append(f'{oid} pokes out of the room')
            room.boxes.append(box)
            sz = d['max'][2] - d['min'][2]
            lcx, lcy = [(d['min'][i] + d['max'][i]) / 2 for i in (0, 1)]
            wx, wy = rot(yaw_total, lcx, lcy)   # oriented box: the prop's own bounds, turned with it
            self.collisions.append({'id': 'col_' + oid, 'shape': 'box', 'room': room.id,
                                    'at': [r(x + wx), r(y + wy), r(z + d['min'][2] + sz / 2)], 'yaw': r(yaw_total),
                                    'size': [r(d['max'][0] - d['min'][0]), r(d['max'][1] - d['min'][1]), r(sz)]})
        return d

    def stack(self, room, names, x, y, yaw, z=0.0, collide=True):
        first_col = len(self.collisions)
        for i, nm in enumerate(names):
            d = self.dims(nm)
            # only the bottom piece reserves floor space / collision footprint once
            self.place(room, nm, x, y, yaw, z - d['min'][2] if i else z, collide=collide and i == 0)
            z += d['max'][2] - (d['min'][2] if i else 0)
        if collide and len(names) > 1:  # stretch the bottom box to the whole stack height
            c = self.collisions[first_col]
            c['size'][2] = r(z); c['at'][2] = r(z / 2)

    def row(self, room, spec):
        wall = spec['wall']
        (px, py), (ax, ay), (nx, ny), length = room.wall_axis(wall)
        a, b = spec.get('span', [-length / 2 + 0.3, length / 2 - 0.3])
        gap, inset = spec.get('gap', 0.3), spec.get('inset', 0.05)
        cyc = spec.get('cycle') or [spec['prop']]
        yaw = WALL_YAW[wall]
        doors = room.door_spans(wall)
        t, i, count = a, 0, spec.get('count', 10 ** 6)
        while i < count:
            name = cyc[i % len(cyc)]
            d = self.dims(name)
            yt = (yaw + self.dims.yaw_fix(name)) % 360
            hx, hy, ox, oy = footprint(d, yt)
            half_along = abs(ax) * hx + abs(ay) * hy
            half_depth = abs(nx) * hx + abs(ny) * hy
            lo, hi = t, t + 2 * half_along
            if hi > b:
                break
            blocked = next((s for s in doors if lo < s[1] and hi > s[0]), None)
            if blocked:
                t = blocked[1]
                continue
            c = (lo + hi) / 2
            cx = px + ax * c + nx * (half_depth + inset)
            cy = py + ay * c + ny * (half_depth + inset)
            # place so the rotated footprint centre (not the origin) lands at (cx, cy)
            self.place(room, name, cx - ox, cy - oy, yaw, spec.get('z', 0.0), spec.get('collide', True))
            t = hi + gap
            i += 1

    def item(self, room, spec):
        if 'wall' in spec and 'along' in spec:
            (px, py), (ax, ay), (nx, ny), _ = room.wall_axis(spec['wall'])
            d = self.dims(spec['prop'])
            yt = (WALL_YAW[spec['wall']] + self.dims.yaw_fix(spec['prop'])) % 360
            hx, hy, ox, oy = footprint(d, yt)
            dep = abs(nx) * hx + abs(ny) * hy + spec.get('inset', 0.05)
            cx, cy = px + ax * spec['along'] + nx * dep, py + ay * spec['along'] + ny * dep
            self.place(room, spec['prop'], cx - ox, cy - oy, WALL_YAW[spec['wall']], spec.get('z', 0.0),
                       spec.get('collide', True))
        elif 'wall' in spec:
            self.row(room, spec)
        elif 'line' in spec:        # {line: {from: [x, y], to: [x, y], n: 5}}: n evenly spaced, ends included
            g = spec['line']
            (x0, y0), (x1, y1), n = g['from'], g['to'], g['n']
            for k in range(n):
                f = k / (n - 1) if n > 1 else 0.5
                self.place(room, spec['prop'], x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, spec.get('yaw', 0),
                           spec.get('z', 0.0), spec.get('collide', True))
        elif 'ring' in spec:
            g = spec['ring']
            cx0, cy0 = g.get('center', [0, 0])
            for k in range(g['n']):
                th = math.radians(g.get('start', 0) + 360 * k / g['n'])
                x, y = cx0 + g['r'] * math.cos(th), cy0 + g['r'] * math.sin(th)
                # front (-Y) towards the centre: yaw so that rot(yaw, 0, -1) points at -(cos, sin)
                yaw = math.degrees(th) - 90 if spec.get('face', 'in') == 'in' else math.degrees(th) + 90
                if 'stack' in spec:
                    self.stack(room, spec['stack'], x, y, yaw, spec.get('z', 0.0), spec.get('collide', True))
                else:
                    self.place(room, spec['prop'], x, y, yaw, spec.get('z', 0.0), spec.get('collide', True))
        elif 'stack' in spec:
            self.stack(room, spec['stack'], *spec['at'], spec.get('yaw', 0), spec.get('z', 0.0), spec.get('collide', True))
        else:
            self.place(room, spec['prop'], *spec['at'], spec.get('yaw', 0), spec.get('z', 0.0), spec.get('collide', True))


def plan_png(rooms, builder, path):
    from PIL import Image, ImageDraw
    S, M = 8, 20
    xs = [rm['at'][0] + s * rm['size'][0] / 2 for rm in rooms for s in (-1, 1)]
    ys = [rm['at'][1] + s * rm['size'][1] / 2 for rm in rooms for s in (-1, 1)]
    x0, y1 = min(xs), max(ys)
    W, H = int((max(xs) - x0) * S) + 2 * M, int((y1 - min(ys)) * S) + 2 * M
    im = Image.new('RGB', (W, H), 'white')
    dr = ImageDraw.Draw(im)
    P = lambda x, y: (M + (x - x0) * S, M + (y1 - y) * S)
    at = {rm['id']: rm['at'] for rm in rooms}
    for rm in rooms:
        cx, cy = rm['at']; w, d = rm['size']
        dr.rectangle([P(cx - w / 2, cy + d / 2), P(cx + w / 2, cy - d / 2)], outline='black')
        dr.text(P(cx - w / 2 + 0.3, cy + d / 2 - 0.3), rm['id'].replace('CYN_ROOM_', ''), fill='#555')
    for c in builder.collisions:
        cx, cy = at[c['room']]
        x, y = cx + c['at'][0], cy + c['at'][1]
        hx, hy = c['size'][0] / 2, c['size'][1] / 2
        dr.rectangle([P(x - hx, y + hy), P(x + hx, y - hy)], fill='#7aa7d6', outline='#1d4f86')
    im.save(path)


def main():
    m2 = yaml.safe_load(open(os.path.join(SRC, 'cynosure_m2.edl.yaml')))
    cfg = yaml.safe_load(open(os.path.join(SRC, 'cynosure_m3_dressing.yaml')))
    dims = Dims(cfg.get('fronts', {}))
    fl = m2['floors'][0]
    rooms = {rm['id']: Room(rm, fl.get('height', 5)) for rm in fl['rooms']}
    b = Builder(dims)
    for rid, items in cfg['rooms'].items():
        for spec in items or []:
            b.item(rooms[rid], spec)
    m3 = dict(m2)
    m3['name'] = 'Cynosure M3'
    m3['objects'] = m2['objects'] + b.objects
    m3['collisions'] = m2['collisions'] + b.collisions
    out = os.path.join(SRC, 'cynosure_m3.edl.yaml')
    yaml.safe_dump(m3, open(out, 'w'), sort_keys=False, width=140)
    plan_png(fl['rooms'], b, os.path.join(SRC, 'cynosure_m3_plan.png'))
    warns = [w for rm in rooms.values() for w in rm.warn]
    print(f'{out}: +{len(b.objects)} props ({len(b.used)} kinds), +{len(b.collisions)} collision boxes, '
          f'{len(warns)} warnings')
    for w in warns:
        print('  WARN', w)
    if '--stage' in sys.argv:
        for n in sorted(b.used):
            dst = os.path.join(LS_SOURCES, 'mod', 'ash_cache', 'sf', n)
            if os.path.exists(dst):
                continue
            shutil.copytree(os.path.join(KIT, n), dst, ignore=shutil.ignore_patterns('dims.json'))
        print('staged', len(b.used), 'props into', LS_SOURCES)


if __name__ == '__main__':
    main()
