"""Helpers for the CR2W JSON envelope that WolvenKit.CLI convert consumes.

WolvenKit serialises every RED4 resource as {"Header": ..., "Data": {"RootChunk": ...}}
with handle-based object identity: every ref<> is {"HandleId": "N", "Data": {...}}
and back-references are {"HandleRefId": "N"}. HandleIds must be unique and dense
within a file, so we allocate them in a single depth-first pass at emit time
rather than tracking them by hand while building the tree.
"""
import sys

WKIT_VERSION = "8.16.0"


class Handles:
    """Assigns HandleIds depth-first. Wrap a dict in H(obj) to mark it as a handle."""

    def __init__(self):
        self._n = 0

    def next(self):
        v = str(self._n)
        self._n += 1
        return v


class H:
    """Marks a dict as needing a HandleId wrapper. Emitted in full every time."""

    __slots__ = ("obj",)

    def __init__(self, obj):
        self.obj = obj


class S:
    """A SHARED object: one canonical definition, back-references everywhere else.

    Quest graphs need this. A socket is inlined in full inside the connection that
    targets it, and the owning node's own `sockets` array then points back at it with
    {"HandleRefId": n}. Connections are shared the same way - the destination socket
    lists the connection by reference. The two therefore form a reference CYCLE, which
    resolves only because an id is assigned BEFORE recursing into the object.
    """

    __slots__ = ("obj", "_id")

    def __init__(self, obj):
        self.obj = obj
        self._id = None


def _resolve(node, handles):
    if isinstance(node, H):
        hid = handles.next()
        return {"HandleId": hid, "Data": _resolve(node.obj, handles)}
    if isinstance(node, S):
        if node._id is not None:
            return {"HandleRefId": node._id}
        # Claim the id BEFORE descending, or a cycle recurses forever.
        node._id = handles.next()
        return {"HandleId": node._id, "Data": _resolve(node.obj, handles)}
    if isinstance(node, dict):
        return {k: _resolve(v, handles) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve(v, handles) for v in node]
    return node


def envelope(root_chunk, data_type):
    """Wrap a root chunk in the Header/Data envelope WolvenKit expects."""
    handles = Handles()
    resolved = _resolve(root_chunk, handles)
    return {
        "Header": {
            "WKitJsonVersion": "0.0.9",
            "GameVersion": 2210,
            "ExportedDateTime": "2026-09-01T00:00:00Z",
            "DataType": "CR2W",
            "ArchiveFileName": "",
            "WKitVersion": WKIT_VERSION,
        },
        "Data": {
            "Version": 195,
            "BuildVersion": 0,
            "RootChunk": resolved,
            "EmbeddedFiles": [],
        },
    }


# --- small typed-value constructors -------------------------------------------------

def cname(v):
    return {"$type": "CName", "$storage": "string", "$value": v}


def tweakdbid(v):
    """A null/empty TweakDBID is encoded as uint64 0, NOT as an empty string -
    WolvenKit's TweakDBIDConverter rejects an empty string outright."""
    if not v:
        return {"$type": "TweakDBID", "$storage": "uint64", "$value": "0"}
    return {"$type": "TweakDBID", "$storage": "string", "$value": v}


def noderef(v):
    """Same null encoding rule as tweakdbid()."""
    if not v:
        return {"$type": "NodeRef", "$storage": "uint64", "$value": "0"}
    return {"$type": "NodeRef", "$storage": "string", "$value": v}


def lockey(n):
    """A LocalizationString. Mod-authored journals use unk1 "0" throughout -
    verified against Aldecaldos High Stakes (34/34 occurrences)."""
    return {"unk1": "0", "value": f"LocKey#{n}"}


def vector3(x=0.0, y=0.0, z=0.0):
    return {"$type": "Vector3", "X": x, "Y": y, "Z": z}


def respath_null():
    return {"DepotPath": {"$type": "ResourcePath", "$storage": "uint64", "$value": "0"},
            "Flags": "Soft"}



def vector4(x=0.0, y=0.0, z=0.0, w=0.0):
    return {"$type": "Vector4", "W": w, "X": x, "Y": y, "Z": z}


def quaternion_yaw(degrees):
    """Rotation about Z only. World markers never pitch or roll - a scene origin
    or a map pin cares which way it faces and nothing else."""
    import math
    h = math.radians(degrees) / 2.0
    return {"$type": "Quaternion", "i": 0.0, "j": 0.0,
            "k": round(math.sin(h), 9), "r": round(math.cos(h), 9)}


def box(mn, mx):
    return {"$type": "Box", "Max": mx, "Min": mn}


def respath(value, flags="Soft"):
    """A non-null resource path. Note CookedPrefabData uses Flags 'Default' where
    almost everything else uses 'Soft', so the flag is a parameter."""
    if not value:
        return {"DepotPath": {"$type": "ResourcePath", "$storage": "uint64", "$value": "0"},
                "Flags": flags}
    return {"DepotPath": {"$type": "ResourcePath", "$storage": "string", "$value": value},
            "Flags": flags}


def check_enum(value, valid, what):
    """Validate against the real RED4 enum up front. WolvenKit fails an invalid enum
    with a bare CEnum.Parse stack that names neither the field nor the value.
    Valid value lists come from tools/enums.py (tools/refresh_enums.py regenerates)."""
    if value not in valid:
        near = [v for v in valid if value.lower()[:4] in v.lower()][:5]
        sys.exit(f"invalid {what}: {value!r}" + (f"  did you mean {near}?" if near else ""))
    return value
