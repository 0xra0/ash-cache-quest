#!/usr/bin/env python3
"""PNG -> CP2077 .xbm (BC7, full mip chain) without DirectXTex.

WolvenKit.CLI on Linux cannot import textures: RedImage needs DirectXTexNet's
native half, which has no Linux build. So: take a vanilla xbm serialised to
JSON as the template, swap in our own BC7 data and header, and let
`WolvenKit.CLI convert deserialize` write the CR2W.

    mkxbm.py <png> <template.xbm.json> <out.xbm.json> color|normal|linear
"""
import base64, copy, json, sys
import etcpak, numpy as np
from PIL import Image

SETUP = {  # (group, isGamma) per kind; compression stays TCM_QualityColor = BC7
    "color": ("TEXG_Generic_Color", 1),
    "linear": ("TEXG_Generic_Grayscale", 0),
    "normal": ("TEXG_Generic_Normal", 0),
}


def mips(img):
    out = [img]
    while img.size != (1, 1):
        img = img.resize((max(1, img.size[0] // 2), max(1, img.size[1] // 2)), Image.LANCZOS)
        out.append(img)
    return out


def bc7(img):
    w, h = img.size
    # bc7enc works on whole 4x4 blocks; the 2x2 and 1x1 mips are padded.
    pw, ph = max(4, (w + 3) // 4 * 4), max(4, (h + 3) // 4 * 4)
    if (pw, ph) != (w, h):
        pad = Image.new("RGBA", (pw, ph))
        pad.paste(img, (0, 0))
        img = pad
    return etcpak.compress_bc7(img.tobytes(), pw, ph, None), pw // 4 * 16


def main(png, tmpl, out, kind):
    img = Image.open(png).convert("RGBA")
    w, h = img.size
    assert w == h and w & (w - 1) == 0, "square power-of-two only"
    doc = json.load(open(tmpl))
    root = doc["Data"]["RootChunk"]
    blob = root["renderTextureResource"]["renderResourceBlobPC"]["Data"]
    hdr = blob["header"]
    info_t = hdr["mipMapInfo"][0]
    data, infos, off = b"", [], 0
    for m in mips(img):
        c, pitch = bc7(m)
        mi = copy.deepcopy(info_t)
        mi["layout"]["rowPitch"] = pitch
        mi["layout"]["slicePitch"] = len(c)
        mi["placement"]["offset"] = off
        mi["placement"]["size"] = len(c)
        infos.append(mi)
        data += c
        off += len(c)
    hdr["mipMapInfo"] = infos
    hdr["sizeInfo"]["width"] = hdr["sizeInfo"]["height"] = w
    ti = hdr["textureInfo"]
    ti["mipCount"] = len(infos)
    ti["sliceSize"] = ti["textureDataSize"] = len(data)
    blob["textureData"]["Bytes"] = base64.b64encode(data).decode()
    root["width"] = root["height"] = w
    g, gamma = SETUP[kind]
    root["setup"]["group"], root["setup"]["isGamma"] = g, gamma
    root["setup"]["compression"] = "TCM_QualityColor"
    json.dump(doc, open(out, "w"), indent=1)
    print(f"{out}: {w}x{h}, {len(infos)} mips, {len(data)} bytes BC7, {kind}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
