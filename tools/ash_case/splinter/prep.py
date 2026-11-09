#!/usr/bin/env python3
"""Splinter sheet -> outline.json + 1024 texture atlas (d01/r01/m01/n01).

The sheet is an orthographic FRONT / BACK / LEFT / RIGHT set. The front
silhouette (with the key-ring hole) and the left profile become the two prisms
bl_splinter.py intersects; each view's pixels become one strip of the atlas,
and outline.json carries the linear mm -> uv map for every view.

    prep.py <sheet.png> <outdir>
"""
import json, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure

LENGTH_MM = 42.0
TOP, BOT = 110, 930                     # rows between the title and the captions
VIEWS = {"front": (115, 385), "back": (547, 813), "left": (922, 1038), "right": (1181, 1297)}
ATLAS, K = 1024, 1.2                    # atlas size, sheet px -> atlas px


def mask_of(rgb):
    mx, mn = rgb.max(2), rgb.min(2)
    return (mn < 150) | ((mx - mn) > 40)  # dark body, or saturated (gold)


def main(sheet, out):
    im = np.asarray(Image.open(sheet).convert("RGB")).astype(np.float32)
    raw = {v: mask_of(im[TOP:BOT, a:b]) for v, (a, b) in VIEWS.items()}
    solid = {}
    for v, m in raw.items():
        m = ndimage.binary_opening(m, iterations=1)
        lab, n = ndimage.label(m)
        m = lab == 1 + np.argmax(ndimage.sum(m, lab, range(1, n + 1)))  # the body only
        solid[v] = ndimage.binary_fill_holes(m)

    # key-ring hole: the largest background island in the bottom tenth of the front
    holes, n = ndimage.label(solid["front"] & ~raw["front"])
    rows = np.arange(holes.shape[0])[:, None]
    best, hole = 0, None
    for i in range(1, n + 1):
        h = holes == i
        if h.sum() > best and (rows * h).sum() / h.sum() > 0.88 * h.shape[0]:
            best, hole = h.sum(), h
    ys, xs = np.nonzero(solid["front"])
    s = LENGTH_MM / (ys.max() - ys.min() + 1)          # mm per sheet px
    cy = (ys.max() + ys.min()) / 2
    cx = {v: (lambda c: (c.min() + c.max()) / 2)(np.nonzero(solid[v])[1]) for v in VIEWS}
    lz = np.nonzero(solid["left"])[1]
    rz = np.nonzero(solid["right"])[1]
    T = (lz.max() - lz.min() + 1) * s

    def contour(m, fx, fy):
        c = max(measure.find_contours(np.pad(m, 1).astype(float), 0.5), key=len) - 1
        c = measure.approximate_polygon(c, 0.8)[:-1]
        return [[round(fx(p[1]), 4), round(fy(p[0]), 4)] for p in c]

    def yy(r):
        return (cy - r) * s
    outline = {
        "length": LENGTH_MM, "thickness": round(T, 3),
        "outer": contour(solid["front"], lambda c: (c - cx["front"]) * s, yy),
        "hole": contour(hole, lambda c: (c - cx["front"]) * s, yy) if hole is not None else [],
        "profile": contour(solid["left"], lambda c: (c - lz.min()) * s, yy),  # (z, y)
    }

    # atlas: the four crops side by side, background replaced by the nearest body pixel
    atlas = np.zeros((ATLAS, ATLAS, 3), np.float32)
    gold = np.zeros((ATLAS, ATLAS), bool)
    uv, x0 = {}, 0
    for v, (a, b) in VIEWS.items():
        crop = im[TOP:BOT, a:b]
        idx = ndimage.distance_transform_edt(~solid[v], return_distances=False, return_indices=True)
        crop = crop[idx[0], idx[1]]
        w, h = round((b - a) * K), round((BOT - TOP) * K)
        atlas[:h, x0:x0 + w] = np.asarray(Image.fromarray(crop.astype(np.uint8)).resize((w, h), Image.LANCZOS))
        # linear map: object mm -> uv. u = au*coord + bu, v = av*y + bv
        c = cx[v]
        if v in ("front", "back"):
            sign = 1 if v == "front" else -1            # the back view is seen mirrored
            au, bu = sign / s * K / ATLAS, ((c - 0) * K + x0) / ATLAS
        else:  # side views: horizontal is z; LEFT looks +X (z grows right), RIGHT looks -X
            zs = lz if v == "left" else rz
            if v == "left":
                au, bu = 1 / s * K / ATLAS, (zs.min() * K + x0) / ATLAS
            else:
                au, bu = -1 / s * K / ATLAS, ((zs.max() + 1) * K + x0) / ATLAS
        av, bv = 1 / s * K / ATLAS, 1 - cy * K / ATLAS
        uv[v] = [au, bu, av, bv]
        x0 += w + 8
    outline["uv"] = uv

    r, g, b = atlas[..., 0], atlas[..., 1], atlas[..., 2]
    sat = atlas.max(2) - atlas.min(2)
    gold = (sat > 45) & (r > g) & (g > b) & (r > 90)
    gold = ndimage.binary_opening(gold, iterations=1)
    lum = atlas.mean(2) / 255
    detail = lum - ndimage.gaussian_filter(lum, 3)            # scratches, edges, print
    rough = np.clip(0.62 - 0.6 * detail, 0.3, 0.85)
    rough[gold] = 0.32
    metal = np.where(gold, 1.0, 0.15)
    h = ndimage.gaussian_filter(-detail, 0.7)                 # scratches read as dents
    gy, gx = np.gradient(h)
    n = np.dstack([-gx * 4, -gy * 4, np.ones_like(h)])        # DirectX: green = -dh/dv(up)
    n /= np.linalg.norm(n, axis=2, keepdims=True)

    def save(a, name):
        Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(f"{out}/o1140_splinter_{name}.png")
    save(atlas, "d01")
    save(np.repeat(rough[..., None] * 255, 3, 2), "r01")
    save(np.repeat(metal[..., None] * 255, 3, 2), "m01")
    save((n * 0.5 + 0.5) * 255, "n01")
    json.dump(outline, open(f"{out}/outline.json", "w"), indent=1)
    print(f"{s:.4f} mm/px, {LENGTH_MM} x {len(outline['outer'])}-pt outline, hole {len(outline['hole'])} pts, "
          f"thickness {T:.2f} mm, gold {gold.mean() * 100:.1f}% of atlas")


if __name__ == "__main__":
    main(*sys.argv[1:3])
