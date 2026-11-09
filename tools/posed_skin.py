"""Skin a character .glb (WolvenKit uncook, MeshOnly) into a baked corpse pose (D175).

A generated corpse .app carries its pose as entCorpseParameter.bakedPose: one model-space
QsTransform per bone name, Z up, the same space the .app's component transforms live in.
Wound decals on a corpse are 3 cm boxes, so they have to sit ON the posed skin - a bone
position plus a guessed body thickness misses. This does linear blend skinning of the body
mesh into that pose so a wound can be asked for in bind space ("left of the sternum, 8 cm
below the collarbone") and come back as a posed surface point and normal.
"""
import json, struct
import numpy as np

# glTF is Y up, the game is Z up: WolvenKit writes (x, z, -y).
Y2Z = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)


def qmat(q):
    """(i, j, k, r) -> 3x3."""
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_to_q(m):
    """3x3 -> (i, j, k, r)."""
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1) * 2
        return ((m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, s / 4)
    i = int(np.argmax(np.diag(m)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = np.sqrt(1 + m[i, i] - m[j, j] - m[k, k]) * 2
    q = [0, 0, 0, 0]
    q[i] = s / 4
    q[j] = (m[j, i] + m[i, j]) / s
    q[k] = (m[k, i] + m[i, k]) / s
    q[3] = (m[k, j] - m[j, k]) / s
    return tuple(q)


def trs(t, q):
    m = np.eye(4)
    m[:3, :3] = qmat(q)
    m[:3, 3] = t
    return m


def _acc(g, blob, i):
    a = g["accessors"][i]
    v = g["bufferViews"][a["bufferView"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a["componentType"]]
    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = v.get("byteStride", 0)
    item = n * np.dtype(dt).itemsize
    if stride and stride != item:
        raw = np.frombuffer(blob, np.uint8, count=stride * a["count"], offset=off).reshape(-1, stride)[:, :item]
        return raw.copy().view(dt).reshape(a["count"], n)
    return np.frombuffer(blob, dt, count=a["count"] * n, offset=off).reshape(a["count"], n)


class Body:
    """The LOD 1 (highest detail) submeshes of one .glb, in game space."""

    def __init__(self, glb):
        b = open(glb, "rb").read()
        jl = struct.unpack_from("<I", b, 12)[0]
        g = json.loads(b[20:20 + jl])
        blob = b[20 + jl + 8:]
        joints = g["skins"][0]["joints"]
        self.bones = [g["nodes"][j]["name"] for j in joints]
        self.bind = []
        for j in joints:   # flat under Armature: node TRS is the bind pose in model space
            n = g["nodes"][j]
            m = trs(n.get("translation", [0, 0, 0]), n.get("rotation", [0, 0, 0, 1]))
            c = np.eye(4)
            c[:3, :3] = Y2Z
            self.bind.append(c @ m @ np.linalg.inv(c))
        P, N, J, W = [], [], [], []
        for m in g["meshes"]:
            if not m["name"].endswith("LOD_1"):
                continue
            at = m["primitives"][0]["attributes"]
            P.append(_acc(g, blob, at["POSITION"]) @ Y2Z.T)
            N.append(_acc(g, blob, at["NORMAL"]) @ Y2Z.T)
            sets = [k[-1] for k in at if k.startswith("JOINTS_")]
            j = np.hstack([_acc(g, blob, at["JOINTS_" + s]) for s in sets]).astype(int)
            w = np.hstack([_acc(g, blob, at["WEIGHTS_" + s]) for s in sets])
            J.append(np.pad(j, ((0, 0), (0, 8 - j.shape[1]))))   # submeshes carry 4 or 8 influences
            W.append(np.pad(w, ((0, 0), (0, 8 - w.shape[1]))))
        self.P, self.N = np.vstack(P).astype(float), np.vstack(N).astype(float)
        self.J, self.W = np.vstack(J), np.vstack(W).astype(float)

    def pose(self, baked):
        """baked: {bone: 4x4 model-space}. Returns posed positions and normals."""
        sk = np.stack([baked[b] @ np.linalg.inv(self.bind[i]) if b in baked else np.eye(4)
                       for i, b in enumerate(self.bones)])
        M = np.einsum("vk,vkij->vij", self.W, sk[self.J])
        p = np.einsum("vij,vj->vi", M[:, :3, :3], self.P) + M[:, :3, 3]
        n = np.einsum("vij,vj->vi", M[:, :3, :3], self.N)
        return p, n / np.linalg.norm(n, axis=1, keepdims=True)

    def nearest(self, bind_pt, facing=None):
        """Index of the bind-pose vertex nearest bind_pt; with facing, only vertices whose
        bind normal points that way (so a chest point never lands on the back)."""
        d = np.linalg.norm(self.P - np.asarray(bind_pt), axis=1)
        if facing is not None:
            d = np.where(self.N @ np.asarray(facing, float) > 0.5, d, np.inf)
        return int(np.argmin(d))


def baked_pose(corpse_param):
    """entCorpseParameter JSON -> {bone: 4x4}."""
    out = {}
    for n, t in zip(corpse_param["bakedBoneNames"], corpse_param["bakedPose"]):
        r, p = t["Rotation"], t["Translation"]
        out[n["$value"]] = trs([p["X"], p["Y"], p["Z"]], [r["i"], r["j"], r["k"], r["r"]])
    return out
