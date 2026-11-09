#!/usr/bin/env python3
"""Mara's lipsync takes, generated from her recorded audio (OI-17, D109).

    vo/en-us/mara.<line>.wem  ->  lipsync/en-us/mara.anims   (one take per line)

A vanilla lipsync take is JALI float tracks (pose weights) plus Neck/Head joints,
not visemes. Nothing here invents pose semantics. Each output frame is a real
frame copied from a vanilla female take (civ_high_f_24_nat_30, same 344-joint /
414-track wa face rig), chosen so its jaw opening matches the loudness of Mara's
audio at that moment, preferring to keep playing the same vanilla take
(concatenative synthesis). So the mouth opens and closes on her syllables with
shapes the rig is known to make. Word-accurate visemes would need a phoneme
aligner; that is not this.

Eye, brow and upper-face tracks are dropped: blinks cut mid-way read as flicker,
and the scene's emotion idle already owns the upper face.

Needs the patched WolvenKit.CLI (`import --gamepath`, see D109) because the
importer resolves the rig from the game archives. Run by hand, not by build.sh:

    python3 tools/gen_lipsync.py           # writes lipsync/en-us/mara.anims
"""
import json, os, struct, subprocess, sys, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESEARCH = "/mnt/sata/Cyberpunk2077/questmod-research/lipsync"
BASIS_GLB = f"{RESEARCH}/glb/civ_high_f_24_nat_30.anims.glb"
BASIS_JSON = f"{RESEARCH}/json/civ_high_f_24_nat_30.anims.json"
GAME = "/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game"
WK = "/mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"
MARA_RIG = "base\\characters\\head\\wa\\h0_009_wa_c__young\\h0_009_wa_c__young_skeleton.rig"
WORK = f"{ROOT}/dev/lipsync_work"
OUT = f"{ROOT}/lipsync/en-us/mara.anims"
FPS = 30.0
JUMP_COST = 0.12       # how much worse a match must be before we stay in the current take
DROP = ("eye", "brow", "muzzleEyes", "muzzleBrows", "upperFace")


def run(*args):
    env = dict(os.environ, DOTNET_ROLL_FORWARD="LatestMajor", GltfImportArgs__ImportFormat="Anims")
    r = subprocess.run(args, capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr
    if r.returncode or "Error" in out:
        sys.exit(f"FAILED: {' '.join(args)}\n{out[-2000:]}")
    return out


def read_glb(path):
    b = open(path, "rb").read()
    jlen = struct.unpack("<I", b[12:16])[0]
    gl = json.loads(b[20:20 + jlen])
    blen = struct.unpack("<I", b[20 + jlen:24 + jlen])[0]
    return gl, bytearray(b[28 + jlen:28 + jlen + blen])


def write_glb(path, gl, binbuf):
    while len(binbuf) % 4:
        binbuf += b"\0"
    gl["buffers"][0]["byteLength"] = len(binbuf)
    j = json.dumps(gl, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    total = 12 + 8 + len(j) + 8 + len(binbuf)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(j), 0x4E4F534A) + j)
        f.write(struct.pack("<II", len(binbuf), 0x004E4942) + binbuf)


def dense(anim, n_tracks):
    """Vanilla take -> frames x tracks, keys linearly interpolated per track."""
    keys = {}
    for k in anim["extras"]["trackKeys"]:
        keys.setdefault(k["trackIndex"], []).append((k["time"], k["value"]))
    dur = max(t for v in keys.values() for t, _ in v)
    times = np.arange(0, dur + 1e-6, 1 / FPS)
    m = np.zeros((len(times), n_tracks), np.float32)
    for i, kv in keys.items():
        kv.sort()
        m[:, i] = np.interp(times, [t for t, _ in kv], [v for _, v in kv])
    return m


def envelope(wav_path, n):
    with wave.open(wav_path) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    a = a.reshape(-1, ch).mean(1) / 32768
    hop, win = sr / FPS, int(sr * 0.04)
    a = np.concatenate([a, np.zeros(int(hop * n) + win, np.float32)])  # last windows run past the end
    rms = np.array([np.sqrt(np.mean(a[int(i * hop):int(i * hop) + win] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(rms / rms.max())
    e = np.clip((db + 40) / 40, 0, 1) ** 1.5
    out, s = np.zeros(n), 0.0
    for i, x in enumerate(e):            # fast attack, slower release
        s += (x - s) * (0.7 if x > s else 0.35)
        out[i] = s
    return out


def main():
    gl, binbuf = read_glb(BASIS_GLB)
    skin = next(s for s in gl["skins"] if s.get("name") == "Armature")
    names = skin["extras"]["trackNames"]
    jaw = names.index("jaw_mid_openLipsyncPoseOutput")
    keep = [i for i, n in enumerate(names) if not any(d in n for d in DROP)]

    basis, takes = [], []
    for a in gl["animations"]:
        m = dense(a, len(names))
        basis.append(m)
        takes += [(len(basis) - 1, f) for f in range(len(m))]
    allf = np.concatenate(basis)
    opening = np.concatenate([np.clip(m[:, jaw] / max(np.percentile(m[:, jaw], 95), 1e-3), 0, 1) for m in basis])
    template = gl["animations"][0]["extras"]
    moving = sorted({k["trackIndex"] for a in gl["animations"] for k in a["extras"]["trackKeys"]} & set(keep))
    const_keys = [k for k in template["constTrackKeys"] if k["trackIndex"] not in moving]

    scene = json.load(open(f"{ROOT}/source/scene_mara.json"))
    ids = json.load(open(f"{ROOT}/source/subtitle_ids.json"))

    def lines(o):
        if isinstance(o, dict):
            if o.get("actor") == "Mara" and "id" in o:
                yield o["id"]
            for v in o.values():
                yield from lines(v)
        elif isinstance(o, list):
            for v in o:
                yield from lines(v)

    os.makedirs(WORK, exist_ok=True)
    head = next(i for i, n in enumerate(gl["nodes"]) if n.get("name") == "Head")
    head_rot = gl["nodes"][head].get("rotation", [0, 0, 0, 1])
    new_anims = []
    for lid in dict.fromkeys(lines(scene)):
        wem = f"{ROOT}/vo/en-us/mara.{lid}.wem"
        if not os.path.exists(wem):
            print(f"  skip {lid}: no audio")
            continue
        wav = f"{WORK}/mara.{lid}.wav"
        run("vgmstream-cli", "-o", wav, wem)
        with wave.open(wav) as w:
            dur = w.getnframes() / w.getframerate()
        n = int(np.ceil(dur * FPS)) + 1
        target = envelope(wav, n)
        assert np.isfinite(target).all(), lid

        rng = np.random.default_rng(int(ids[f"mara.{lid}"]) % 2**32)
        pick, cur = [], None
        for t in range(n):
            err = np.abs(opening - target[t])
            best = rng.choice(np.argsort(err)[:8])
            if cur is not None and cur + 1 < len(takes) and takes[cur + 1][0] == takes[cur][0] \
                    and err[cur + 1] <= err[best] + JUMP_COST:
                best = cur + 1
            pick.append(best)
            cur = best
        frames = allf[pick]
        frames = (np.roll(frames, 1, 0) + 2 * frames + np.roll(frames, -1, 0)) / 4  # soften cuts
        fade = np.minimum(1, np.minimum(np.arange(n) / 4, (n - 1 - np.arange(n)) / 6))
        frames *= fade[:, None]

        tk = []
        for i in moving:
            col = frames[:, i]
            for f in range(n):
                if f in (0, n - 1) or abs(col[f] - col[f - 1]) > 1e-3 or abs(col[f + 1] - col[f]) > 1e-3:
                    tk.append({"trackIndex": i, "time": round(min(f / FPS, dur), 6), "value": round(float(col[f]), 5)})

        # one constant Head channel: sets the duration, adds no motion (additive)
        acc_t = add_accessor(gl, binbuf, np.array([0, dur], np.float32), "SCALAR", minmax=True)
        acc_r = add_accessor(gl, binbuf, np.array([head_rot, head_rot], np.float32), "VEC4")
        name = "f_%016X" % int(ids[f"mara.{lid}"])
        extras = dict(template, trackKeys=tk, constTrackKeys=const_keys, fallbackFrameIndices=[], animEvents=None)
        new_anims.append({"name": name, "channels": [{"sampler": 0, "target": {"node": head, "path": "rotation"}}],
                          "samplers": [{"input": acc_t, "output": acc_r, "interpolation": "LINEAR"}],
                          "extras": extras})
        print(f"  {lid:14s} {name}  {dur:5.2f}s  {len(tk)} keys")

    gl["animations"] = new_anims
    write_glb(f"{WORK}/mara.anims.glb", gl, binbuf)

    base = json.load(open(BASIS_JSON))
    base["Data"]["RootChunk"]["rig"]["DepotPath"]["$value"] = MARA_RIG
    json.dump(base, open(f"{WORK}/mara.anims.json", "w"))
    run("dotnet", WK, "convert", "deserialize", f"{WORK}/mara.anims.json", "-o", WORK)
    log = run("dotnet", WK, "import", f"{WORK}/mara.anims.glb", "-o", WORK, "-k", "-gp", GAME)
    print("\n".join(l for l in log.splitlines() if "total:" in l or "Rebuilt" in l))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    os.replace(f"{WORK}/mara.anims", OUT)
    print(f"wrote {OUT} ({len(new_anims)} takes)")


def add_accessor(gl, binbuf, arr, typ, minmax=False):
    while len(binbuf) % 4:
        binbuf += b"\0"
    gl["bufferViews"].append({"buffer": 0, "byteOffset": len(binbuf), "byteLength": arr.nbytes})
    binbuf += arr.tobytes()
    acc = {"bufferView": len(gl["bufferViews"]) - 1, "componentType": 5126,
           "count": len(arr), "type": typ}
    if minmax:
        acc["min"], acc["max"] = [float(arr.min())], [float(arr.max())]
    gl["accessors"].append(acc)
    return len(gl["accessors"]) - 1


if __name__ == "__main__":
    main()
