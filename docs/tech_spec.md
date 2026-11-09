# Ash Cache — technical architecture

## Principle

The engine's quest system runs the quest. We do not build a quest system.

Everything the player sees — journal entry, objective list, map markers, save
persistence, quest completion — comes from engine resources. Redscript is glue for
the things the graph cannot express: reacting to a shard being read, noticing the
player has arrived somewhere, deciding the quest may begin. That is exactly the
split used by Aldecaldos High Stakes, whose 5 redscript files contain zero quest
logic.

The test for whether something belongs in the glue is not "is it small" but
**"does deleting it lose the quest, or only stall it?"** `mod/r6/scripts/AshCache/`
writes five ints into the fact store and reads nothing back. Delete it and the
quest still has its journal entry, its objectives and its map pins; it simply
never advances. Anything that would fail that test — an objective raised from
script, a branch decided in script — belongs in the graph instead (D13).

Reward grants used to be on this list and no longer are: the engine has
`questItemManagerNodeDefinition` for that, so the graph does it (D12).

## Layer map

| Layer | Technology | Owns |
|---|---|---|
| Quest logic | `.questphase` graph | Act progression, conditions, spawns, facts |
| Quest UI | `.journal` + `LocKey` onscreens | Entry, phases, objectives, map pins |
| Injection | ArchiveXL `.xl` `quest: phases:` | Attaching the phase to the root graph |
| Items | TweakXL `.yaml` | The Splinter, Clean Slate, Predictive Echo, The Witness, keys |
| World | `.streamingsector` + `.streamingblock` | Props, the black box, the server rack |
| Glue | redscript | Setting the facts the graph waits on: quest start, arrival, shard reads |
| Debug | CET Lua | Jump-to-act, fact inspector, marker surveyor. Dev only, not shipped. |

## Build pipeline

    source/*.json                  hand-edited, the source of truth
        │  tools/gen_*.py          emit CR2W-shaped JSON
        ▼
    build/*.json
        │  WolvenKit.CLI convert deserialize
        ▼
    build/tree/**                  .questphase, .journal, onscreens
        │  WolvenKit.CLI pack
        ▼
    mod/archive/pc/mod/ashcache.archive  (+ .xl, + r6/)

`tools/build.sh` runs the whole chain. Nothing writes to the game directory.

## Deployment

**Never automatic.** The live install is only ever touched by an explicit,
confirmed step. Per standing rule: ask before every run against the live install,
develop and verify on scratchpad copies.

## Naming

Everything is prefixed `ashcache_` / `ash_cache`. Resource root is
`mod\ash_cache\` (ArchiveXL custom root — no vanilla path is shadowed).
Facts: `ashcache_<act>_<thing>`. LocKeys are allocated from one contiguous block
recorded in `source/lockeys.json` so they cannot collide with another mod.

## Localization

`en-us` and `ua-ua` are both first-class — `ua-ua` is a real translation, not an
alias, because it is the player's native language. All 19 locales are declared in
the `.xl`; unlisted ones fall back to the en-us resource path so no locale renders
a blank quest UI.

## OPEN DECISION — dialogue delivery

The design is dialogue-heavy. One vanilla-quality `.scene` conversation is ~1.3 MB
of graph JSON with performers, actor behaviors and animation references. That is a
GUI-editor artifact, not something to hand-generate.

Most of Ash Cache already avoids it by design — encrypted message, Mr. Blue Eyes
holocall, terminal logs, Mara's journal shard, epilogue messages. Those are cheap.

The exception is **Mara Voss**, who is a face-to-face conversation with a
three-way micro-choice. How that is delivered is the load-bearing decision and is
recorded in `docs/decisions.md` once made.
