#!/usr/bin/env python3
"""Fill the atlas background of baked textures with the nearest island texel.

The Trellis bake is thousands of small UV islands on black with ~6 px of margin.
At the mips the game samples at bench distance that margin is gone and every
island averages with black: the case reads as black noise with red specks
(2026-09-24). The Blender preview samples near mip 0 and hides it. Filling the
whole background makes every mip of the chain clean; nothing is rebaked.

    dilate.py <game_final dir> [prefix=ash_case]
      reads body.glb + lid.glb UVs (shell material only) for the island mask,
      rewrites <prefix>_{d01,r01,m01,n01}.png in place (originals -> *.orig.png once)
"""
import json, os, shutil, struct, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

d = sys.argv[1]
prefix = sys.argv[2] if len(sys.argv) > 2 else "ash_case"
src = f"{d}/{prefix}_d01.orig.png"  # a rerun must pick the mask on the unfilled bake
ref = np.asarray(Image.open(src if os.path.exists(src) else f"{d}/{prefix}_d01.png").convert("RGB"))
H, W = ref.shape[:2]

def glb_shell_uv_tris(path):
    """UV triangles of every submesh_00 primitive (the shell), straight from the glb."""
    b = open(path, "rb").read()
    jl = struct.unpack_from("<I", b, 12)[0]
    js = json.loads(b[20:20 + jl])
    binc = b[20 + jl + 8:]
    ct = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    nc = {"SCALAR": 1, "VEC2": 2}

    def acc(i):
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        dt = np.dtype(ct[a["componentType"]])
        n = nc[a["type"]]
        stride = bv.get("byteStride", dt.itemsize * n)
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        raw = np.frombuffer(binc, np.uint8, count=stride * (a["count"] - 1) + dt.itemsize * n, offset=off)
        return np.lib.stride_tricks.as_strided(raw.view(dt), (a["count"], n), (stride, dt.itemsize)).copy()

    out = []
    for m in js["meshes"]:
        if not m["name"].startswith("submesh_00"):
            continue
        for pr in m["primitives"]:
            uv = acc(pr["attributes"]["TEXCOORD_0"])
            idx = acc(pr["indices"]).reshape(-1, 3)
            out.append(uv[idx])
    return out


tris = []
for part in ("body", "lid"):
    tris += glb_shell_uv_tris(f"{d}/{part}.glb")
tris = np.concatenate(tris)


def mask_for(flip):
    m = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(m)
    for t in tris:
        v = (1 - t[:, 1]) if flip else t[:, 1]
        dr.polygon([(u * W, y * H) for u, y in zip(t[:, 0], v)], fill=255)
    return np.asarray(m) > 0


# glTF V runs down the image, but check: the right mask is the one that sits on the paint.
lum = ref.mean(axis=2)
mask = max((mask_for(f) for f in (True, False)), key=lambda m: lum[m].mean() - lum[~m].mean())
mask = ndimage.binary_dilation(mask, iterations=2)  # keep the baker's own edge margin
print(f"islands cover {mask.mean():.1%} of {W}x{H}")
_, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)

for suf in ("d01", "r01", "m01", "n01"):
    p = f"{d}/{prefix}_{suf}.png"
    orig = p[:-4] + ".orig.png"
    if not os.path.exists(orig):
        shutil.copy(p, orig)
    im = Image.open(orig)
    a = np.asarray(im)
    Image.fromarray(a[iy, ix], im.mode).save(p)
    print("filled", p)
