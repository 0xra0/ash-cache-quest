# Streaming sectors: what a mod may put in the world

Everything here was measured off real files. Nothing is inferred from field names.
Re-deriving it costs an archive unbundle and a WolvenKit serialise per sample, so
this file exists to stop the next session paying that again.

## The samples

| file | source | category / level | nodes |
|---|---|---|---|
| `uqs_mappins.streamingsector` | Undermine (mod) | AlwaysLoaded / 0 | 9 markers |
| `uqs_airdrop_01.streamingsector` | Undermine (mod) | Quest / 255 | 2 entity, 2 device, 1 trigger |
| `hotfuzz.streamingsector` | Hot Fuzz (mod) | AlwaysLoaded / 255 | 1 trigger |
| `quest_9694582f55685f39` | vanilla | Quest / 255 | 1 trigger, 1 spawner |
| `quest_73110a178d6e7404` | vanilla EP1 | Quest / 255 | 20, incl. a computer and a cover |
| `quest_e495c59e9949e75b` | vanilla EP1 | Quest / 255 | 80, incl. 4 spawners |
| 18 `interior_-6*` sectors | vanilla EP1 | — | instanced meshes and collision only |

Extraction:

    A="/mnt/ssd/Cyberpunk 2077/.../archive/pc/ep1/ep1_1_nightcity.archive"
    dotnet WolvenKit.CLI.dll unbundle "$A" -o <dir> -r "quest_.*\.streamingsector"
    dotnet WolvenKit.CLI.dll convert serialize -p <dir> -o <dir>

698 quest sectors come out at 18 MB. **Grep the binaries before serialising** - node
class names are plain strings in the CR2W name pool:

    worldTriggerAreaNode         589 / 698    the overwhelmingly common quest node
    worldPopulationSpawnerNode   219 / 698
    worldEntityNode              148 / 698
    worldDeviceNode              133 / 698
    worldInteractiveDeviceNode     0 / 698    does not exist; devices are worldDeviceNode

## What each node type costs

| node | needs an `.ent`? | needs a TweakDB record? | `instanceData` |
|---|---|---|---|
| `worldStaticMarkerNode` | no | no | n/a - no such field |
| `worldTriggerAreaNode` | no | no | n/a - no such field |
| `worldPopulationSpawnerNode` | no | **yes**, `objectRecordId` | **null in all 5 samples** |
| `worldEntityNode` | yes | no | null in 1 of 3; a buffer in 2 |
| `worldDeviceNode` | yes | no | a buffer in **all 4** samples |

### The instanceData question

`instanceData` is an `entEntityInstanceData` wrapping a RedPackage buffer whose
chunk is the entity's whole per-instance controller state - roughly two hundred
fields (`ComputerControllerPS` alone carries `authorizationProperties`,
`backdoorBreachDifficulty`, `deviceOperationsSetup`, …). It is what makes placing
an object look expensive.

It is not always required. In `quest_73110a178d6e7404`:

    nodes[12]  worldEntityNode  base\gameplay\devices\masters\computers\computer_1.ent
               appearance computer_computer_2_angle_15      instanceData = a buffer
    nodes[13]  worldEntityNode  base\entities\covers\left_sided_low_cover.ent
               appearance default                           instanceData = NULL

So the buffer is an **override**, not a requirement, at least for a prop with
nothing to override. Whether a *device* can go without one is untested - see OI-13.
The probe sector (D15) is that test.

### The missing computer sample, found

OI-13 used to record "no vanilla computer-terminal `worldDeviceNode` sample". There
is none because a vanilla computer is **not a `worldDeviceNode`** - `mq058`'s is a
`worldEntityNode` pointing at `base\gameplay\devices\masters\computers\computer_1.ent`.
Sixteen EP1 interior sectors reference no device at all; interiors are geometry, and
every device in EP1 lives in a `quest_*` sector.

Device `.ent` paths actually referenced across the 698 quest sectors:

    115  security_systems\security_system.ent
     79  security_systems\security_area\security_area_1.ent
     53  empty_visible_object.ent
     15  masters\loot_container_access_point\loot_container_access_point_airdrop.ent
      1  masters\computers\computer_1.ent
      1  stash\invisiblescenestash.ent

## Field shapes

### worldTriggerAreaNode

No entity, no record, no redscript. `notifiers` carries a `questTriggerNotifier_Quest`
(`excludeChannels: 0`, `includeChannels: "TC_Default"`, `isEnabled: 1`), which is
what lets a `questTriggerCondition` in the `.questphase` wait on the volume.

`outline` is an `AreaShapeOutline` with **both** a `points` array and a cooked
`buffer`, and they must agree. Every sample's outline is the same unit quad; the
real size is the node's `Scale` in `nodeData`, so `Scale [8,8,4]` with `height 2`
is a 16×16 box, 8 m tall.

The buffer layout, decoded from Hot Fuzz and re-encoded to the same bytes:

    <uint32 count> then count × <4×float32 x,y,z,1.0> then <float32 height>

72 bytes for a quad, little-endian. Hot Fuzz's shipped buffer differs from its own
`points` array only by editor float noise on one corner (-0.99904 vs -1).

### worldPopulationSpawnerNode

    objectRecordId   TweakDBID, e.g. Vehicle.hackable_thorton_galena
    spawnOnStart     0 in every quest-content sample
    instanceData     null in every sample
    alwaysSpawned    "default__false_"      spawnInView "default__true_"

`spawnOnStart: 0` is what makes it quest content rather than set dressing: the
object is inert until the graph activates it.

**Every vanilla `objectRecordId` is a `Vehicle.*`.** Zero quest sectors mention
`Character.`, because vanilla NPC groups come from communities
(`questCommunityTemplate_NodeType`, 40 uses in q304) rather than from spawner nodes.
That gap is why the FIA cleanup crew is not a solved problem - see OI-13.

### worldEntityNode

    entityTemplate   {DepotPath, Flags: "Soft"}
    appearanceName   which appearance out of the .ent's .app; "default" for a prop
    entityLod 0      ioPriority "Immediate"      sourcePrefabHash "0" is fine

## nodeData, and the two undecoded flag words

Each node has one entry in the `worldNodeDataBuffer`, carrying its transform and
six fields nobody has decoded. They are **not** the same per node type, so they are
values to copy, not to derive:

| kind | Uk10 | Uk11 | MaxStreamingDistance | UkFloat1 | copied from |
|---|---|---|---|---|---|
| marker | 0 | 0 | 0 | 0 | uqs_mappins, all 9 |
| trigger | 288 | 65280 | FLT_MAX | 29.8995686 | hotfuzz |
| trigger | 288 | 65024 | FLT_MAX | 66.639 | uqs_airdrop, and vanilla |
| spawner | 288 | 512 | 9520.28 | 150 | two vanilla sectors agree |
| entity | 288 | 10762 | 1745.70 | 53.70 | uqs_airdrop |
| entity | 1312 | 10762 | 9513.76 | 53.70 | vanilla mq058 |

`Uk11 = 10762` (0x2A0A) for an entity node in **both** vanilla and Undermine - two
independent authors, same constant. The trigger's 0xFF00 vs 0xFE00 disagreement is
one bit and unexplained. `Bounds` collapses to `min == max == Position` on every
placed quest node.

`nodeRefs` is a **pool, not an index**: vanilla `quest_9694582f55685f39` lists its
two refs in the opposite order to its two nodes. Each node carries its own name in
`nodeData[i].QuestPrefabRefHash`.

## The graph side

Measured across the 80 extracted q304 questphases. These are the pieces that turn a
placed node into a quest beat:

| you want | graph node / condition | payload |
|---|---|---|
| switch a spawner on | `questSpawner_NodeType` | `{action: "Activate", spawnerReference: NodeRef}` — **two fields** |
| switch a community on | `questCommunityTemplate_NodeType` | `action`, `communityEntryName`, `communityEntryPhaseName`, `spawnerReference` |
| wait until they exist | `questCharacterSpawned_ConditionType` | `questComparisonParam{Greater, 0, entireCommunity 1}` + `gameEntityReference` |
| wait until N are down | `questCharacterKilled_ConditionType` | `questComparisonParam{GreaterOrEqual, N, entireCommunity 0}` + `killed`/`defeated`/`unconscious` all 1 |
| wait until a thing is used | `questInteraction_ConditionType` | `{eventType: "Executed", objectRef: NodeRef}` — **two fields** |
| wait until a device changes | `questDevice_ConditionType` | `deviceConditionFunction` (e.g. `IsOpen`), `deviceControllerClass` (e.g. `DoorControllerPS`), `objectRef` |
| put loot in a container | `questInjectLoot_NodeType` | per-item `{itemTDBID, operationType: "Inject", quantity}`, wrapped in `questItemManagerNodeDefinition` — same base class as `add_item` (D47) |

`questSpawner_NodeType`'s target was checked rather than assumed:
`#sa_ep1_37_car_01` in `ep1_mq304_airdrops.questphase` resolves to a
`worldPopulationSpawnerNode` of that name in `quest_e495c59e9949e75b`, shipping
`spawnOnStart: 0`. That is the complete verified chain — graph node → sector node →
TweakDB record.

### Two corrections to an earlier reading of this file

An earlier revision said the minimal encounter is spawn -> spawned -> killed, and
that the killed condition takes the same comparison params as the spawned one.
Both were wrong, and both were checked properly afterwards.

`q304_transmitter_tower_02` is 4 nodes and there is **no kill condition in it**:

    In -> questSpawnManagerNodeDefinition   (questCommunityTemplate, Activate)
       -> questPauseConditionNodeDefinition (questCharacterSpawned, Greater 0,
                                             entireCommunity 1)
       -> questConditionNodeDefinition      (questFactsDBCondition)

Vanilla waits on a **fact** for "the encounter is over", not on a body count. And
`questCharacterKilled` is genuinely rare - **2 instances** across every extracted
EP1 questphase, and both are `GreaterOrEqual N` with `entireCommunity 0`:

    GreaterOrEqual 2  #q304_transmitter_com_gangers_01
    GreaterOrEqual 1  (mq304_cleanup)

There is no measured "the whole community is dead" form. `Greater 0` with
`entireCommunity 1` - the shape the spawned condition uses - would go true on the
FIRST body. That is why `gen_questphase.py` refuses to default the count.

Full tally of `questComparisonParam` across the extracted phases:

    39  spawned  Greater 0          entireCommunity 1
    10  spawned  Greater 0          entireCommunity 0
     2  spawned  Greater 1          entireCommunity 0
     2  spawned  Less 1             entireCommunity 0
     1  spawned  GreaterOrEqual 4   entireCommunity 1
     1  killed   GreaterOrEqual 2   entireCommunity 0
     1  killed   GreaterOrEqual 1   entireCommunity 0

### Wrappers, and the two kinds of reference

A condition type is never emitted bare. It sits inside a wrapper whose class says
which subsystem answers the question:

    questObjectCondition     <- questInteraction, questDevice, questInventory
    questCharacterCondition  <- questCharacterSpawned, questCharacterKilled, Hit, Mount
    questFactsDBCondition    <- questVarComparison
    questJournalCondition    <- questJournalEntryState

The two families also address the world differently, and they are not
interchangeable. `questInteraction` / `questDevice` / `questSpawner` take a **bare
`NodeRef`**. The character conditions wrap the same name in a
**`gameEntityReference`**, whose `names` array can then pick one entry out of the
community the node spawns - vanilla's `#sa_ep1_31_av_com` + `"av"`.

### The spawn node

`questSpawnManagerNodeDefinition` holds `actions[]`, each a
`questSpawnManagerNodeActionEntry` wrapping one `questSpawner_NodeType` or
`questCommunityTemplate_NodeType`. 140 of the 178 vanilla instances carry a single
action; the rest carry 2, 3, 4, 5 or 8, so it is a list and not a field.

`action` is a `populationSpawnerObjectCtrlAction`, and its values are aliased in
pairs - `Activate == Spawn == 1`, `Deactivate == Despawn == 2`,
`Reactivate == Respawn == 3`. Vanilla writes the `Activate` spelling.

### spawnOnStart is the quest/set-dressing switch

`spawnOnStart: 0` is what makes a spawner quest content: the object does not exist
until a graph node activates it. The consequence for testing is that a spawner
placed with no graph behind it shows you nothing at all, whether the mechanism
works or not - which is why the D15 probe sectors, and only those, set it to 1.

## The depot listing

`/mnt/sata/Cyberpunk2077/depot_files.txt` - 544,497 unique depot paths, 47 MB, the
resource-side twin of `tweakdbstr.txt`. `tools/validate.py` checks every `.ent` a
prop points at against it, because an unresolvable `entityTemplate` streams in as
nothing at all with no log line anywhere. Rebuild it with:

    G="/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc"
    dotnet WolvenKit.CLI.dll archive "$G/content" "$G/ep1" -l -v Quiet \
      | tail -n +2 | sed '/^[0-9%]*$/d' | LC_ALL=C sort -u > depot_files.txt
