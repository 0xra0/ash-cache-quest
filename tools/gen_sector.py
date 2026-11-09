#!/usr/bin/env python3
"""source/world.json  ->  build/<sector>.streamingsector.json + ash_cache.streamingblock.json

A quest needs places. A map pin points at a NodeRef, and a scene node anchors its
whole performance to one - but a NodeRef only resolves if some streaming sector
actually declares a node with that name. Nothing in the journal or the quest graph
creates world geometry; this is the file that makes those names exist.

Four node types, in ascending order of how much they cost to author:

    markers    worldStaticMarkerNode        a named point. No mesh, no entity.
    triggers   worldTriggerAreaNode         a volume that notifies the quest graph.
                                            Needs no .ent and no TweakDB record.
    spawners   worldPopulationSpawnerNode   an object the graph turns on later.
                                            Needs a TweakDB record, no .ent.
    props      worldEntityNode              an entity template placed in the world.
    meshes     worldStaticMeshNode          a static mesh. Visual only - no collision.
    collisions worldCollisionNode           box collision. Invisible - no mesh.
                                            Needs an .ent - vanilla ones are fine.

Shapes verified against shipped mods AND vanilla - see reference/sectors.md for the
measurement table and what each claim rests on:
  - Undermine Quest Series  mod\\uqs\\worlds\\uqs_mappins.streamingsector    (9 markers)
  - Undermine Quest Series  mod\\uqs\\worlds\\uqs_airdrop_01.streamingsector (entity,
                                                                    device, trigger)
  - Hot Fuzz                base\\journal\\hotfuzz.streamingsector           (1 trigger)
  - vanilla EP1             quest_9694582f55685f39   (trigger + spawner, 2 nodes)
  - vanilla EP1             quest_73110a178d6e7404   (a computer, and a cover entity
                                                      whose instanceData is null)
  - vanilla EP1             quest_e495c59e9949e75b   (the spawners a
                                                      questSpawner_NodeType drives)

Mods register their block through the .xl's `streaming: blocks:` key, which is what
makes a mod-authored sector load at all.

Two things make an all-marker sector cheap enough to keep resident:

  * category AlwaysLoaded with a streamingBox of +/-FLT_MAX. The sector opts out
    of the world grid entirely, so no cell index or bounds have to be computed.
    Legitimate only because the payload is empty markers - a sector full of
    meshes could not do this.
  * worldStaticMarkerNode wrapping an EMPTY scnSceneMarker. No mesh, no entity,
    no collision: a named coordinate and nothing else.

A sector holding props keeps the same treatment: an .ent placed by a mod is one
entity, not a city block, and both reference mods stream theirs the same way.
"""
import base64
import itertools
import math
import json
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import (H, box, cname, envelope, noderef, quaternion_yaw, respath,
                  respath_null, vector3, vector4)

ROOT = pathlib.Path(__file__).resolve().parent.parent

FLT_MAX = 3.40282347e+38

# The worldNodeDataBuffer is a cooked buffer rather than a plain field. Flags is
# identical (4063232) in both reference mods, so it is a constant to carry, not a
# value to derive. The Type string names the WolvenKit buffer class that will
# deserialize it.
BUFFER_TYPE = ("WolvenKit.RED4.Archive.Buffer.worldNodeDataBuffer, WolvenKit.RED4, "
               "Version=8.19.1.0, Culture=neutral, PublicKeyToken=null")
BUFFER_FLAGS = 4063232

SECTOR_VERSION = 62

# A marker is scaled to 0.1 in the reference. It draws nothing, so this only
# affects editor gizmo size, but matching the reference costs nothing.
MARKER_SCALE = 0.1

# Every trigger outline in every sample is the SAME unit quad, scaled by the
# node's Scale in nodeData. So a trigger's real size lives in `size`, not here.
UNIT_QUAD = [(-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 0.0), (-1.0, 1.0, 0.0)]
TRIGGER_HEIGHT = 2.0

# worldNodeData carries two flag words nobody has decoded, and they are NOT the
# same for every node type. Guessing zero is not free: markers ship zeros in the
# only mod that ships markers, and triggers ship 0xFF00/0xFE00 in all three
# samples that ship triggers, so zero is a value with evidence behind it exactly
# where it was measured and nowhere else. Each row below is copied from a real
# file rather than derived, and reference/sectors.md records which file.
#
# Default autohide for a mesh, in metres. Vanilla scales this to the object -
# 4.5 m for a cigarette, 121 m for a truss - so anything structural gets a big
# number or it pops out from across the lot.
MESH_AUTOHIDE = 300.0

#                       Uk10   Uk11   maxStreamingDistance   UkFloat1
COOKED = {
    # uqs_mappins, all 9 nodes. A marker is looked up by name and never drawn.
    "marker":  (0,     0,     0.0,                   0.0),
    # hotfuzz.streamingsector - the one shipped mod whose entire mechanism is a
    # quest trigger, so these are the numbers a trigger is known to work with.
    # uqs_airdrop_01 and vanilla quest_9694582f55685f39 both say 65024 (0xFE00)
    # instead of 65280 (0xFF00); the meaning of the differing bit is unknown.
    # FLT_MAX because a trigger has to stay live at any distance.
    "trigger": (288,   65280, FLT_MAX,               29.8995686),
    # vanilla quest_9694582f55685f39 and quest_e495c59e9949e75b agree.
    "spawner": (288,   512,   9520.28027,            150.0),
    # 10762 (0x2A0A) for an entity node in BOTH vanilla and Undermine - two
    # independent authors, same constant. Uk10 they disagree on (1312 vs 288),
    # and 288 is the value the mod uses, which is the situation we are in.
    "prop":    (288,   10762, 9513.75586,            53.7016792),
    # exterior_-30_-39_0_0, the row 226 of its 406 static meshes ship - among
    # them int_ent_industrial_a trusses, the same kit this mod builds with.
    # UkFloat1 is NOT a constant for a mesh: in six of that sector's eight
    # distinct rows it equals the node's own forceAutoHideDistance to the last
    # decimal, so node_instance overrides it per node and the number here is
    # only the fallback. Uk14 is 1 for a mesh and 0 for everything else, which
    # is why UK1314 exists below.
    "mesh":    (1040,  20610, 1745.70105,            MESH_AUTOHIDE),
    # The 17 collision nodes of one Dogtown exterior sector, all three LOD
    # values, agree on 1024/512. FLT_MAX because collision that streams out
    # underneath the player is worse than no collision at all - and it is what
    # all 17 ship.
    "collision": (1024, 512,  FLT_MAX,               6.5),
}

# Uk13/Uk14 per kind. Every sample says Uk13 0; Uk14 is 1 on 464 of 464 static
# meshes and 0 on every marker, trigger, spawner, entity and collision node
# measured. Nobody knows what it selects, so it is copied, not reasoned about.
UK1314 = {"mesh": ("0", "1")}

# 2^17. A worldCollisionNode stores actor positions as WorldPosition/FixedPoint
# rather than float: Bits / 131072 is metres. Checked against a shipped node -
# Bits -247428704 reads -1887.731, which lands in Dogtown where that sector is.
FIXED_POINT = 131072.0

COLLISION_BUFFER_TYPE = ("WolvenKit.RED4.Archive.Buffer.CollisionBuffer, WolvenKit.RED4, "
                         "Version=8.19.1.0, Culture=neutral, PublicKeyToken=null")

# Both are CNames stored as uint64. The preset resolves: FNV1a64("World Static")
# is exactly 11199900243055890879, which is the preset 134 of one sector's 184
# shapes use. The material does not resolve against any name tried, so it is
# copied verbatim from a shipped shape - it picks a footstep sound, and a wrong
# guess there is cosmetic where an invented hash is not.
COLLISION_PRESET = "11199900243055890879"
COLLISION_MATERIAL = "875637379034262679"



def load():
    return json.loads((ROOT / "source" / "world.json").read_text(encoding="utf-8"))


def placements(spec):
    """Every node in a sector, in emit order, tagged with its kind.

    One flat list so ids, positions, nodeData and nodeRefs stay in lockstep no
    matter how many kinds a sector mixes. Order is fixed by kind rather than by
    however world.json happens to be written, so adding a prop cannot renumber
    the markers a scene is already anchored to.

    A node carrying "disabled" is skipped here and nowhere else. Here is the
    only correct place: everything downstream reads this list, so a node that
    leaves it leaves the sector completely - no id, no position, no nodeData
    entry, no nodeRef - while the ones that remain keep the numbering they
    already had for their kind. Filtering later would renumber the markers a
    scene's sceneLocation is anchored to, which is a different change than the
    one being tested. The node stays in source/world.json, so validate.py still
    sees it defined and a graph reference to it stays legal; the interaction
    simply never fires, which is what a bisect wants.
    """
    out = []
    for kind in ("marker", "trigger", "spawner", "prop", "mesh", "collision"):
        for p in spec.get(KEY[kind], []):
            if p.get("disabled"):
                continue
            out.append((kind, p))
    return out


KEY = {"marker": "markers", "trigger": "triggers",
       "spawner": "spawners", "prop": "props",
       "mesh": "meshes", "collision": "collisions"}


def full_ref(world, node_id):
    """'ac_mara' -> '$/03_night_city/ash_cache/#AshCache/#ac_mara'.

    The trailing '#name' segment also resolves on its own from anywhere, which is
    why source/journal.json can use the short form for map pins, and why the quest
    graph can drive a spawner with a bare '#ac_...'. A scene's sceneLocation uses
    this long form, matching the only observed sample.
    """
    return f"{world['nodeRefPrefix']}/#{node_id}"


def debug_name(p):
    """Vanilla wraps every debugName in braces; both reference mods do too.

    It is cosmetic - it shows in the editor's node list - but it is also the only
    field that says which of our source ids a node came from when reading a packed
    sector back, so it is worth keeping identical to the samples.
    """
    return cname("{%s}" % p["id"])


def marker_node(p):
    return H({
        "$type": "worldStaticMarkerNode",
        # An empty scnSceneMarker is the whole point: a place a scene can happen,
        # carrying no markers or workspots of its own.
        "data": H({"$type": "scnSceneMarker", "markers": [], "workspotMarkers": []}),
        "debugName": cname(p["id"]),
        "isEnabled": 1,
        "isHostOnly": 0,
        "isVisibleInGame": 1,
        "proxyScale": None,
        # 0 = no source prefab. Proven safe: uqs_mappin_penthouse ships with 0 and
        # is the marker Undermine anchors a scene's sceneLocation to.
        "sourcePrefabHash": "0",
        "tag": "None",
        "tagExt": "None",
        "tags": {"$type": "redTagList", "tags": []},
    })


def outline_buffer(points, height):
    """The cooked twin of AreaShapeOutline.points.

    Layout, decoded from hotfuzz.streamingsector and re-encoded to the same bytes:
    a uint32 point count, then one Vector4 per point with w pinned to 1.0, then the
    height as a float. 72 bytes for a quad, little-endian throughout.

    Both this and `points` ship, and they must agree - the shipped Hot Fuzz buffer
    differs from its own points array only by editor float noise on one corner.
    """
    out = struct.pack("<I", len(points))
    for x, y, z in points:
        out += struct.pack("<4f", x, y, z, 1.0)
    return base64.b64encode(out + struct.pack("<f", height)).decode()


def trigger_node(p):
    height = float(p.get("height", TRIGGER_HEIGHT))
    return H({
        "$type": "worldTriggerAreaNode",
        # Editor gizmo colour. Hot Fuzz and vanilla both ship fully transparent;
        # Undermine ships opaque green. It draws nothing in game either way.
        "color": {"$type": "Color", "Alpha": 0, "Blue": 0, "Green": 0, "Red": 0},
        "debugName": debug_name(p),
        "isHostOnly": 0,
        "isVisibleInGame": 1,
        # This is the entire reason a trigger area is cheap: the notifier posts to
        # the quest system, so a questTriggerCondition in the .questphase can wait
        # on the volume with no entity, no device record and no redscript at all.
        "notifiers": [H({"$type": "questTriggerNotifier_Quest",
                         "excludeChannels": 0,
                         "includeChannels": "TC_Default",
                         "isEnabled": 1})],
        "outline": H({"$type": "AreaShapeOutline",
                      "buffer": outline_buffer(UNIT_QUAD, height),
                      "height": height,
                      "points": [vector3(x, y, z) for x, y, z in UNIT_QUAD]}),
        "proxyScale": None,
        "sourcePrefabHash": "0",
        "tag": "None",
        "tagExt": "None",
    })


def spawner_node(p):
    return H({
        "$type": "worldPopulationSpawnerNode",
        "alwaysSpawned": "default__false_",
        "appearanceName": cname(p.get("appearance", "default")),
        "debugName": debug_name(p),
        "isHostOnly": 0,
        "isVehicle": 1 if p.get("isVehicle") else 0,
        "isVisibleInGame": 1,
        # A TweakDB record, not a resource path - the spawner asks the record
        # system what to build. Every vanilla sample is a Vehicle.* record; see
        # OI-13 for why a Character.* one is not yet a verified claim.
        "objectRecordId": {"$type": "TweakDBID", "$storage": "string",
                           "$value": p["record"]},
        "prefetchAppearance": 0,
        "proxyScale": None,
        "sourcePrefabHash": "0",
        "spawnInView": "default__true_",
        # 0, always. A spawner that spawns on start puts its object in the world
        # the moment the sector streams in, which for quest content means before
        # the quest has started. The graph turns it on with questSpawner_NodeType.
        # 0 in every vanilla quest sample: the object is inert until a graph node
        # activates it, and that is exactly what makes it quest content rather
        # than set dressing. A probe sector sets it so the thing appears on its
        # own, because a probe with no graph behind it would otherwise show you
        # nothing whether the mechanism works or not.
        "spawnOnStart": 1 if p.get("spawnOnStart") else 0,
        "tag": "None",
        "tagExt": "None",
    })


# Device state buffers, loaded once and deep-copied per node. Keyed by the name
# a prop puts in world.json's "device".
_DEVICES = {}


def device_instance(kind, where):
    """The instanceData buffer that makes a placed device an actual device.

    A worldEntityNode with instanceData null is an entity with no per-instance
    state: for a cover that is correct and vanilla does it, and for a computer it
    means no ComputerControllerPS, so nothing holds isInteractive, nothing holds
    tweakDBRecord Devices.Computer, and what the player walks up to is scenery.
    That was OI-13's open question and the player answered it on 2026-09-09 -
    the probe node appears and cannot be touched.

    The buffer is copied out of vanilla rather than written here; see
    reference/device_computer.instancedata.json for which node it came from and
    why its CruidDict is left alone. Only the HandleIds are rewritten, because
    two props carrying the same buffer would otherwise define handle 24 twice in
    one file - and they are pure definitions, referenced by nothing, so
    renumbering them cannot change what the buffer means.
    """
    import copy
    if kind not in _DEVICES:
        f = ROOT / "reference" / f"device_{kind}.instancedata.json"
        if not f.is_file():
            sys.exit(f"{where} asks for device {kind!r}, but "
                     f"{f.relative_to(ROOT)} does not exist")
        _DEVICES[kind] = json.loads(f.read_text(encoding="utf-8"))["instanceData"]
    buf = copy.deepcopy(_DEVICES[kind])

    def renumber(o):
        if isinstance(o, dict):
            if "HandleId" in o:
                o["HandleId"] = str(next(_HANDLE))
            # BufferId lives in its own reference space and has to be unique the
            # same way. Missing this is not a subtle bug: WolvenKit's
            # ReferenceResolver throws on the second buffer that calls itself 1,
            # and the sector simply does not convert.
            if "BufferId" in o:
                o["BufferId"] = str(next(_BUFFER))
            for v in o.values():
                renumber(v)
        elif isinstance(o, list):
            for v in o:
                renumber(v)
    renumber(buf)
    return buf


def prop_node(p):
    # A VALUE, not a key: "device": null is the off switch. D69 turned both
    # clinic computers off after the first build that carried buffers crashed
    # the game on approach, and the two suspects added in that one deploy - this
    # buffer and the scene audio events - had to be told apart. Testing key
    # presence would have meant deleting the prose that says why the buffer is
    # there, which is the part worth keeping.
    if p.get("device"):
        return H({
            "$type": "worldEntityNode",
            "appearanceName": cname(p.get("appearance", "default")),
            "debugName": debug_name(p),
            "entityLod": 0,
            "entityTemplate": respath(p["template"], flags="Soft"),
            "instanceData": device_instance(p["device"], f"prop {p['id']!r}"),
            "ioPriority": "Immediate",
            "isHostOnly": 0,
            "isVisibleInGame": 1,
            "proxyScale": None,
            "sourcePrefabHash": "0",
            "tag": "None",
            "tagExt": "None",
        })
    return H({
        "$type": "worldEntityNode",
        # Which appearance out of the .ent's .app. "default" is safe for a prop;
        # a vanilla device usually wants a named one (the mq058 computer asks for
        # "computer_computer_2_angle_15").
        "appearanceName": cname(p.get("appearance", "default")),
        "debugName": debug_name(p),
        "entityLod": 0,
        "entityTemplate": respath(p["template"], flags="Soft"),
        # null, deliberately. instanceData is a RedPackage carrying the whole
        # per-instance controller state - two hundred fields of it - and it is what
        # makes placing an entity look expensive. base\entities\covers\
        # left_sided_low_cover.ent is placed by vanilla with instanceData null, so
        # the buffer is an override rather than a requirement, and a prop that
        # wants no overrides can go without it. Whether a DEVICE can also go
        # without one is the open question in OI-13.
        "instanceData": None,
        "ioPriority": "Immediate",
        "isHostOnly": 0,
        "isVisibleInGame": 1,
        "proxyScale": None,
        "sourcePrefabHash": "0",
        "tag": "None",
        "tagExt": "None",
    })


def mesh_node(p):
    """A static mesh: geometry the player can see and walk THROUGH.

    Collision is a separate node type in REDengine - 464 static meshes and 17
    collision nodes in the same Dogtown sector, and the collision ones carry no
    mesh at all. So a floor is two entries in source/world.json: the mesh that
    draws it and the box that holds the player up. Forgetting the second is not
    a subtle bug, it is a hole in the world.
    """
    return H({
        "$type": "worldStaticMeshNode",
        "castLocalShadows": "Always",
        "castRayTracedGlobalShadows": "Always",
        "castRayTracedLocalShadows": "Always",
        "castShadows": "Always",
        "debugName": debug_name(p),
        # Vanilla ties this to the object's size and nodeData.UkFloat1 repeats
        # it; node_instance keeps the two equal, which is what six of eight
        # measured rows do.
        "forceAutoHideDistance": float(p.get("autohide", MESH_AUTOHIDE)),
        "isHostOnly": 0,
        "isVisibleInGame": 1,
        "lodLevelScales": 4294967295,
        "mesh": respath(p["mesh"], flags="Soft"),
        "meshAppearance": cname(p.get("appearance", "default")),
        "occluderAutohideDistanceScale": 255,
        "occluderType": "None",
        "proxyScale": None,
        "removeFromRainMap": 0,
        "renderSceneLayerMask": "Default",
        # 0 = not part of a cooked prefab, same as every other node this
        # generator writes. Vanilla meshes carry a real hash because they came
        # out of one; ours did not.
        "sourcePrefabHash": "0",
        "tag": "None",
        "tagExt": "None",
        "version": 2,
        "windImpulseEnabled": 1,
    })


def fixed_point(v):
    return {"$type": "FixedPoint", "Bits": int(round(float(v) * FIXED_POINT))}


def world_position(x, y, z):
    return {"$type": "WorldPosition",
            "x": fixed_point(x), "y": fixed_point(y), "z": fixed_point(z)}


def rotate_xy(dx, dy, yaw):
    """Rotate a local offset into world space around Z, matching quaternion_yaw."""
    r = math.radians(yaw)
    return dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)


def collision_boxes(p):
    """('boxes' in world.json) -> one actor per box, positioned in world space.

    'half' is a HALF extent, because that is what the shipped Size vector is:
    the reference shape reads 0.105 x 0.025 x 0.119 for a deco object roughly
    21 cm wide. A 3 m wall is therefore half [1.5, 0.1, 2.0], not [3, 0.2, 4].
    """
    x, y, z = p["pos"]
    yaw = float(p.get("yaw", 0.0))
    actors = []
    for b in p["boxes"]:
        ox, oy, oz = b.get("offset", [0.0, 0.0, 0.0])
        wx, wy = rotate_xy(float(ox), float(oy), yaw)
        hx, hy, hz = b["half"]
        actors.append({
            "Position": world_position(x + wx, y + wy, z + float(oz)),
            "Orientation": quaternion_yaw(yaw),
            "Shapes": [{
                "ShapeType": "Box",
                "Size": vector3(float(hx), float(hy), float(hz)),
                # The shape sits at its actor's origin. Vanilla uses this to
                # hang several shapes off one actor; one box per actor is the
                # simplest thing that is still a shipped shape.
                "Position": vector3(),
                "Rotation": quaternion_yaw(0.0),
                "Preset": {"$type": "CName", "$storage": "uint64", "$value": COLLISION_PRESET},
                # Every one of the 184 shapes measured says CharacterObstacle,
                # including the two in nodes vanilla itself named "Critical".
                "ProxyType": "CharacterObstacle",
                "Materials": [{"$type": "CName", "$storage": "uint64",
                               "$value": COLLISION_MATERIAL}],
                "Uk1": 0, "Uk2": 0, "Uk3": 0,
            }],
            "Scale": vector3(1.0, 1.0, 1.0),
            "Uk1": 0,
            "Uk2": "0",
        })
    return actors


def collision_node(p):
    """Invisible box collision, stored inline in the node's own buffer.

    This is the finding that makes an underground location possible at all: the
    CollisionBuffer is not a reference into a baked physics cache, it is actors
    and shapes written out in full, and WolvenKit round-trips one of vanilla's
    back to byte-identical JSON. So collision can be AUTHORED - which is the
    difference between geometry the player looks at and geometry the player
    stands on.

    The num* fields are cooked counts over deduplicated arrays: vanilla's
    3-shape node says numShapeRotations 2 because two of its shapes share a
    rotation. They are computed here rather than guessed, because they are how
    the engine sizes what it reads.
    """
    actors = collision_boxes(p)
    shapes = [s for a in actors for s in a["Shapes"]]
    x, y, z = p["pos"]

    def spread(axis, key):
        far = 0.0
        for a, s in ((a, s) for a in actors for s in a["Shapes"]):
            centre = a["Position"][axis]["Bits"] / FIXED_POINT
            far = max(far, abs(centre - (x, y, z)["xyz".index(axis)]) + s["Size"][key])
        return far

    return H({
        "$type": "worldCollisionNode",
        "debugName": debug_name(p),
        # Half-extents of everything this node holds, measured from the node's
        # own position - the shipped one reads 0.87 x 0.45 x 0.26 around a
        # cloud of three actors about a metre across.
        "extents": vector4(spread("x", "X"), spread("y", "Y"), spread("z", "Z")),
        "isHostOnly": 0,
        "isVisibleInGame": 1,
        # 0, 1 and 2 all ship. Vanilla names its 0s "CriticalCollisionNode" and
        # its 2s "DecoCollisionNode", so 0 is the one that means "this is the
        # floor, never cull it".
        "lod": 0,
        "numActors": len(actors),
        "numMaterialIndices": len(shapes),
        "numMaterials": len({s["Materials"][0]["$value"] for s in shapes}),
        "numPresets": len({s["Preset"]["$value"] for s in shapes}),
        "numScales": sum(1 for a in actors if a["Scale"]["X"] != 1.0),
        "numShapeIndices": len(shapes),
        "numShapeInfos": len(shapes),
        # Only what the cooked arrays actually hold. A shape sitting at its
        # actor's origin stores no position and an unrotated shape stores no
        # rotation, so one box at the origin counts 0 and 0 - which is what
        # WolvenKit writes back after correcting an over-count, and why
        # vanilla's three-shape node says two rotations.
        "numShapePositions": sum(1 for s in shapes
                                 if any(s["Position"][k] for k in ("X", "Y", "Z"))),
        "numShapeRotations": len({json.dumps(s["Rotation"], sort_keys=True) for s in shapes
                                  if s["Rotation"]["r"] != 1.0}),
        "proxyScale": None,
        "resourceVersion": 2,
        # UNVERIFIED. Every collision node in the sampled sector carries the
        # same value, so it is per-sector, but it is not FNV1a64 of any of the
        # three depot paths that sector could have had, under any of seven
        # spellings. This is the one number here that is a guess, and the probe
        # exists to find out whether the engine reads it.
        "sectorHash": _SECTOR_HASH,
        "sourcePrefabHash": "0",
        # Null is attested: some shipped collision nodes carry categories, some
        # carry none, so none is a legal answer rather than an omission.
        "staticCollisionShapeCategories": None,
        "tag": "None",
        "tagExt": "None",
        "compiledData": {
            "BufferId": str(next(_BUFFER)),
            "Flags": BUFFER_FLAGS,
            "Type": COLLISION_BUFFER_TYPE,
            "Data": {"Actors": actors},
        },
    })


def fnv1a64(text):
    h = 0xCBF29CE484222325
    for byte in text.encode("utf-8"):
        h = ((h ^ byte) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


NODE = {"marker": marker_node, "trigger": trigger_node,
        "spawner": spawner_node, "prop": prop_node,
        "mesh": mesh_node, "collision": collision_node}

# Geometry is anonymous. A vanilla static mesh ships
# QuestPrefabRefHash 0 and the sector lists 114 nodeRefs for 1648 nodes, so
# a NodeRef is something a node opts into by being referenced. Giving a wall
# one would also file it under the quest-prefab machinery, which is the exact
# machinery D116 crashes in.
GEOMETRY = {"mesh", "collision"}


def node_instance(index, kind, p, world):
    x, y, z = p["pos"]
    # 'pos' is the FLOOR point - a coordinate somebody stood on, which is what
    # makes it verifiable and what the CET go button teleports to. An entity's
    # origin is not always at its feet: computer_1.ent carries its player
    # workspots at local z -1.40 to -1.52, so its origin belongs ~1.5 m up. Placed
    # at the floor point it renders half-sunk AND puts its interaction workspot
    # under the floor, where no prompt can be reached. 'zOffset' raises the node
    # without touching the recorded coordinate, so provenance and the go button
    # both keep meaning what they say. Props only - a marker is a point, and a
    # trigger volume is sized by 'size'.
    z += float(p.get("zOffset", 0.0)) if kind in ("prop", "mesh") else 0.0
    pos = vector4(x, y, z)
    uk10, uk11, max_dist, uk_float = COOKED[kind]
    uk13, uk14 = UK1314.get(kind, ("0", "0"))
    if kind == "mesh":
        # Kept equal to the node's own forceAutoHideDistance, which is what
        # six of the eight measured static-mesh rows do exactly.
        uk_float = float(p.get("autohide", MESH_AUTOHIDE))
    if kind == "marker":
        scale = vector3(MARKER_SCALE, MARKER_SCALE, MARKER_SCALE)
    elif kind == "trigger":
        # The outline is a unit quad, so this IS the trigger's half-extent in
        # metres: size [8, 8, 4] is a 16x16 box, 8 m tall once height 2 is scaled.
        sx, sy, sz = p["size"]
        scale = vector3(sx, sy, sz)
    elif kind == "mesh":
        # A real scale, unlike an entity: World Builder can stretch a mesh and
        # so can a sector, which is how one 3 m floor tile covers a 9 m room.
        sx, sy, sz = p.get("scale", [1.0, 1.0, 1.0])
        scale = vector3(float(sx), float(sy), float(sz))
    else:
        scale = vector3(1.0, 1.0, 1.0)
    return {
        # Undermine contradicts itself here - six nodes claim Id 0 while the last
        # three match their index - and every vanilla node says 0. So Id is not
        # load-bearing. Index keeps it self-consistent.
        "Id": str(index),
        "NodeIndex": index,
        "Position": pos,
        "Orientation": quaternion_yaw(p.get("yaw", 0.0)),
        "Scale": scale,
        "Pivot": vector3(),
        # Every sample collapses Bounds to the node's own position - min == max.
        # Real world geometry gets a real box; a placed quest node does not.
        "Bounds": box(pos, pos),
        "QuestPrefabRefHash": noderef("" if kind in GEOMETRY
                                      else full_ref(world, p["id"])),
        "UkHash1": noderef(""),
        "CookedPrefabData": respath("", flags="Default"),
        "MaxStreamingDistance": max_dist,
        "UkFloat1": uk_float,
        "Uk10": uk10,
        "Uk11": uk11,
        "Uk12": 0,
        "Uk13": uk13,
        "Uk14": uk14,
    }


# Handle ids for copied device buffers. Started high enough that it cannot walk
# into the ids the sector writes for itself (the clinic uses 0-9), and reset per
# sector so two builds of the same source produce the same bytes.
_HANDLE = None
_BUFFER = None
_SECTOR_HASH = None


def sector(spec, world):
    global _HANDLE, _BUFFER, _SECTOR_HASH
    _HANDLE = itertools.count(100)
    _BUFFER = itertools.count(100)
    _SECTOR_HASH = str(fnv1a64(f"{world['sectorDir']}\\{spec['id']}.streamingsector"))
    items = placements(spec)
    return {
        "$type": "worldStreamingSector",
        "category": spec.get("category", "AlwaysLoaded"),
        "cookingPlatform": "PLATFORM_PC",
        "externInplaceResource": respath_null(),
        "level": 0,
        "localInplaceResource": [],
        "nodeData": {
            "BufferId": "0",
            "Flags": BUFFER_FLAGS,
            "Type": BUFFER_TYPE,
            "Data": [node_instance(i, k, p, world) for i, (k, p) in enumerate(items)],
        },
        # A pool, not an index: vanilla quest_9694582f55685f39 lists its two refs in
        # the OPPOSITE order to its two nodes, so nothing reads this positionally.
        # Each node already carries its own name in nodeData.QuestPrefabRefHash.
        "nodeRefs": [noderef(full_ref(world, p["id"]))
                     for k, p in items if k not in GEOMETRY],
        "nodes": [NODE[k](p) for k, p in items],
        "persistentNodeIndex": 0,
        "persistentNodes": [],
        "variantIndices": [0],
        "variantNodes": [],
        "version": SECTOR_VERSION,
    }


def descriptor(spec, world):
    path = f"{world['sectorDir']}\\{spec['id']}.streamingsector"
    limit = vector4(FLT_MAX, FLT_MAX, FLT_MAX, FLT_MAX)
    neg = vector4(-FLT_MAX, -FLT_MAX, -FLT_MAX, -FLT_MAX)
    return {
        "$type": "worldStreamingSectorDescriptor",
        "blockIndex": {"$type": "worldStreamingBlockIndex", "oup": "Base", "rldGridCell": 0},
        # "Quest" + a questPrefabNodeRef: the sector is not streamed by distance
        # at all, only while an active phase lists that prefab (D133). Vanilla
        # quest_009c7e2341620c3d is the shape: same +/-FLT_MAX box, the ref names
        # a prefab, and its geometry nodes keep QuestPrefabRefHash 0.
        "category": spec.get("category", "AlwaysLoaded"),
        "data": respath(path),
        "level": 0,
        # 1 regardless of node count - Undermine's 9-node sector also says 1.
        "numNodeRanges": 1,
        "questPrefabNodeRef": noderef(full_ref(world, spec["questPrefab"])
                                      if spec.get("questPrefab") else ""),
        "streamingBox": box(neg, limit),
        "variants": [],
    }


def emitted(world):
    """The sectors that actually go into the archive.

    A sector carrying "disabled" is kept in source/world.json - with the reason
    written next to it - but is not built and gets no descriptor in the
    streaming block, so the game never sees it. This is how a suspect node is
    taken out of the world for one test without deleting the work that made it.
    """
    return [s for s in world["sectors"] if not s.get("disabled")]


def block(world):
    return {
        "$type": "worldStreamingBlock",
        "cookingPlatform": "PLATFORM_PC",
        "descriptors": [descriptor(s, world) for s in emitted(world)],
        "index": {"$type": "worldStreamingBlockIndex", "oup": "Base", "rldGridCell": 0},
    }


def write(obj, name):
    out = ROOT / "build" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope(obj, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return out


def main():
    world = load()
    tally = {k: 0 for k in KEY}
    # A sector deleted from world.json outright leaves its json behind too (the
    # D133 probe sector was packed once more after its removal). Same cure.
    live = {s["id"] for s in world["sectors"]}
    for old in (ROOT / "build").glob("*.streamingsector.json"):
        if old.name[:-len(".streamingsector.json")] not in live:
            old.unlink()
            print(f"REMOVED {old.name}  - no longer in world.json")
    for spec in world["sectors"]:
        if spec.get("disabled"):
            # build/*.json is not cleaned between runs (only build/tree is), so a
            # sector that stops being generated would otherwise keep being packed
            # from last run's leftover file. Drop it here or "disabled" is a lie.
            stale = ROOT / "build" / f"{spec['id']}.streamingsector.json"
            if stale.exists():
                stale.unlink()
            print(f"SKIPPED {spec['id']}  - disabled: {spec.get('disabled_why', 'no reason given')}")
            continue
        out = write(sector(spec, world), f"{spec['id']}.streamingsector.json")
        counts = {}
        for kind, _ in placements(spec):
            counts[kind] = counts.get(kind, 0) + 1
            tally[kind] += 1
        detail = ", ".join(f"{n} {k}(s)" for k, n in counts.items()) or "empty"
        print(f"wrote {out.relative_to(ROOT)}  ({detail})")
        # Loud, per node, for the same reason the sector-level skip is loud: a
        # node quietly missing from the world is indistinguishable from a node
        # that failed to build, and the whole point of the flag is that the
        # test knows exactly what was taken out.
        for kind in KEY:
            for p in spec.get(KEY[kind], []):
                if p.get("disabled"):
                    print(f"  SKIPPED {kind} {p['id']}  - disabled: "
                          f"{p.get('disabled_why', 'no reason given')}")
    out = write(block(world), "ash_cache.streamingblock.json")
    total = ", ".join(f"{n} {k}(s)" for k, n in tally.items() if n)
    live = len(emitted(world))
    off = len(world["sectors"]) - live
    print(f"wrote {out.relative_to(ROOT)}  "
          f"({live} sector(s){f', {off} disabled' if off else ''}, {total} total)")


if __name__ == "__main__":
    main()
