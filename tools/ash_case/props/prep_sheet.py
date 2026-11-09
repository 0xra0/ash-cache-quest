#!/usr/bin/env python3
"""Orthographic concept sheet -> hull.json + texture atlas (d01/r01/m01/n01).

Generalises splinter/prep.py to any prop drawn as FRONT / BACK / LEFT / RIGHT
(+ optional TOP), on a light background or a near-black one ("bg": "dark"). Frame: Z up, X right, front faces -Y.

    prep_sheet.py <config.json> <outdir>

config: {"name", "sheet", "band": [y0, y1] (rows between title and captions),
         "views": ["front", "back", "left", "right"] (left to right on the sheet),
         "boxes": {view: [x0, x1]} (optional; else found from the column profile),
         "xrange": [x0, x1] (optional; one item of a multi-item sheet),
         "bg": "light" | "dark", "thr": 38 (dark: luminance above it is the object),
         "close": 3 (dark: closing iterations; raise it for dark-on-dark props),
         "simplify": 0.8 (outline tolerance, px; raise it for noisy backgrounds),
         "height_m": front silhouette height, "atlas": 2048,
         "hole_frac": 0.003 (background islands inside a silhouette bigger than this
                             share of it, and close to the sheet colour, become
                             through-holes: gaps behind pipes, handles, frames)}

Per view, world axes and the direction sheet columns run in (see bl_hull.py):
    front  x+  z     back  x-  z     left  y-  z     right  y+  z     top  x+  y
"""
import json, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure

AXES = {"front": ("x", 1, "z"), "back": ("x", -1, "z"), "left": ("y", -1, "z"),
        "right": ("y", 1, "z"), "top": ("x", 1, "y")}


def fg_mask(rgb):
    mx, mn = rgb.max(2), rgb.min(2)
    return (mn < 150) | ((mx - mn) > 40)  # dark body, or saturated (brass, paint, lamps)


def find_boxes(fg, views):
    cols = np.r_[False, fg.sum(0) > 15, False]  # pad: a view may touch the crop edge
    e = np.flatnonzero(np.diff(cols.astype(int)))
    runs = sorted(zip(e[::2], e[1::2]), key=lambda r: r[1] - r[0])[-len(views):]
    return {v: [max(0, int(a) - 4), min(fg.shape[1], int(b) + 4)] for v, (a, b) in zip(views, sorted(runs))}


def main(cfg_path, out):
    cfg = json.load(open(cfg_path))
    y0, y1 = cfg["band"]
    im = np.asarray(Image.open(cfg["sheet"]).convert("RGB")).astype(np.float32)[y0:y1]
    xa, xb = cfg.get("xrange", [0, im.shape[1]])
    im = im[:, xa:xb]
    dark = cfg.get("bg") == "dark"
    if dark:  # rendered on black: bright enough is object; close the gaps dark paint leaves
        raw_all = ndimage.binary_opening(ndimage.binary_closing(im.mean(2) > cfg.get("thr", 38),
                                                                 iterations=cfg.get("close", 3)),
                                         iterations=2)
    else:
        raw_all = fg_mask(im)
    boxes = cfg.get("boxes") or find_boxes(raw_all, cfg["views"])
    ATLAS = cfg.get("atlas", 2048)

    bgcol = im[5, 5]
    crops, solid, holes = {}, {}, {}
    for v, (a, b) in boxes.items():
        crops[v], m = im[:, a:b], raw_all[:, a:b]
        m2 = ndimage.binary_opening(m, iterations=1)
        lab, n = ndimage.label(m2)
        big = lab == 1 + np.argmax(ndimage.sum(m2, lab, range(1, n + 1)))
        solid[v] = ndimage.binary_fill_holes(big)
        lab, n = ndimage.label(solid[v] & ~m)
        near = np.abs(crops[v] - bgcol).max(2) < 18
        holes[v] = []
        for i in range(1, n + 1 if not dark else 1):  # dark sheets: dark paint, not gaps
            h = lab == i
            if h.sum() > cfg.get("hole_frac", 0.003) * solid[v].sum() and near[h].mean() > 0.8:
                holes[v].append(ndimage.binary_opening(h, iterations=1))

    # per-view scale (m/px): uprights by height, the top view by the front's width
    def ext(m):
        ys, xs = np.nonzero(m)
        return ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    H = cfg["height_m"]
    f = ext(solid["front"])
    width = (f[3] - f[2]) * H / (f[1] - f[0])
    geo = {}
    for v in boxes:
        r0, r1, c0, c1 = ext(solid[v])
        s = width / (c1 - c0) if v == "top" else H / (r1 - r0)
        geo[v] = dict(s=s, ch=(c0 + c1) / 2, rref=(r0 + r1) / 2 if v == "top" else r1)

    def contour(m, v):
        g, (_, sign, va) = geo[v], AXES[v]
        c = max(measure.find_contours(np.pad(m, 1).astype(float), 0.5), key=len) - 1
        c = measure.approximate_polygon(c, cfg.get("simplify", 0.8))[:-1]
        return [[round(sign * (p[1] - g["ch"]) * g["s"], 5), round((g["rref"] - p[0]) * g["s"], 5)] for p in c]

    hull = {"name": cfg["name"], "height": H, "width": round(width, 4),
            "loops": {v: [contour(solid[v], v)] + [contour(h, v) for h in holes[v]]
                      for v in ("front", "left", "top") if v in boxes}}

    # atlas: views side by side, uniform scale K, background replaced by the nearest body pixel
    ws = {v: b - a for v, (a, b) in boxes.items()}
    K = min((ATLAS - 8 * len(ws)) / sum(ws.values()), ATLAS / im.shape[0])
    atlas = np.zeros((ATLAS, ATLAS, 3), np.float32)
    uv, x0 = {}, 0
    for v in boxes:
        keep = solid[v].copy()
        for h in holes[v]:
            keep &= ~ndimage.binary_dilation(h, iterations=2)
        idx = ndimage.distance_transform_edt(~keep, return_distances=False, return_indices=True)
        c = crops[v][idx[0], idx[1]]
        w, h = round(ws[v] * K), round(im.shape[0] * K)
        atlas[:h, x0:x0 + w] = np.asarray(Image.fromarray(c.astype(np.uint8)).resize((w, h), Image.LANCZOS))
        g, (_, sign, _) = geo[v], AXES[v]
        # world (h, vert) -> uv:  u = au*h + bu,  v = av*vert + bv
        uv[v] = [sign * K / (g["s"] * ATLAS), (g["ch"] * K + x0) / ATLAS,
                 K / (g["s"] * ATLAS), 1 - g["rref"] * K / ATLAS]
        x0 += w + 8
    hull["uv"], hull["axes"] = uv, {v: AXES[v] for v in boxes}

    sat = atlas.max(2) - atlas.min(2)
    r, gg, b = atlas[..., 0], atlas[..., 1], atlas[..., 2]
    brass = ndimage.binary_opening((sat > 45) & (r > gg) & (gg > b) & (r > 90), iterations=1)
    lum = atlas.mean(2) / 255
    detail = lum - ndimage.gaussian_filter(lum, 3)
    rough = np.clip(0.62 - 0.6 * detail, 0.3, 0.85)
    rough[brass] = 0.32
    metal = np.where(brass, 1.0, 0.15)
    hgt = ndimage.gaussian_filter(-detail, 0.7)
    gy, gx = np.gradient(hgt)
    n = np.dstack([-gx * 4, -gy * 4, np.ones_like(hgt)])  # DirectX green
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    name = cfg["name"]

    def save(a, k):
        Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(f"{out}/{name}_{k}.png")
    save(atlas, "d01")
    save(np.repeat(rough[..., None] * 255, 3, 2), "r01")
    save(np.repeat(metal[..., None] * 255, 3, 2), "m01")
    save((n * 0.5 + 0.5) * 255, "n01")
    json.dump(hull, open(f"{out}/hull.json", "w"), indent=1)
    dep = {v: round(max(p[0] for p in l[0]) - min(p[0] for p in l[0]), 3) for v, l in hull["loops"].items()}
    print(f"{name}: boxes {boxes}, H {H} m, W {width:.3f} m, extents {dep}, "
          f"holes { {v: len(h) for v, h in holes.items()} }, brass {brass.mean() * 100:.1f}%")


if __name__ == "__main__":
    main(*sys.argv[1:3])
