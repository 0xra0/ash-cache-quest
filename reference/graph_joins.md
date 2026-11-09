# Merging paths in a quest graph: what vanilla does

Measured 2026-09-03. Population scan over **all 2,860 vanilla `.questphase`
files**; shape and connection counts over a **seed-27 random sample of 150** of
them, deserialised with WolvenKit.CLI (3,524 nodes). Method and controls at the
bottom.

## Two ways to merge, and vanilla prefers the plain one

A quest graph can bring several paths together either by wiring them all into
one input socket, or by routing them through a dedicated join node.

In the 150-file sample, **238 input sockets carry more than one connection**.
Where they sit:

    44  questPauseConditionNodeDefinition
    38  questPhaseNodeDefinition
    36  questLogicalHubNodeDefinition
    21  questFactsDBManagerNodeDefinition
    18  questCutControlNodeDefinition
    17  questJournalNodeDefinition
    14  questOutputNodeDefinition
    11  questConditionNodeDefinition
     9  questRandomizerNodeDefinition
     8  questPhoneManagerNodeDefinition
     ... 22 more across 13 node types
     ------
     2  questLogicalXorNodeDefinition

**200 of 238 merges are a bare multi-connected input socket on an ordinary
node.** Only 38 go through a join node. So the plain form is not a shortcut this
project invented — it is what the game does.

How wide do they get? The full distribution of connections per input socket:

    0 connections   1076
    1                3320
    2                 196
    3                  36
    4                   3
    7                   1
    10                  1
    13                  1

## The join family

| class | files (of 2,860) | declared shape |
|---|---|---|
| `questLogicalHubNodeDefinition` | 1,230 | 73% are **1 in, 1 out** |
| `questLogicalXorNodeDefinition` | 1,003 | 78% are 2 in, 1 out; **never 1 in** |
| `questLogicalAndNodeDefinition` | 839 | 69% are 2 in, 1 out; never 1 in |
| `questFlowControlNodeDefinition` | 106 | `isOpen`, `opensAt`, `closesAt` |
| `questSwitchNodeDefinition` | 110 | — |

There is no OR node. `questLogicalOrNodeDefinition` is not a class — it is not
in the RTTI at all, so its zero count says nothing. Neither are
`questCombinedNodeDefinition` or `questCounterNodeDefinition`; all three were
guessed at while writing this census and checked against the SDK headers
afterwards, which is the only reason the zeros are not being read as evidence.

All three logical nodes derive from `questLogicalBaseNodeDefinition`, which
carries `inputSocketCount` and `outputSocketCount` as **declared uint32 fields**.
The socket count is data, not something inferred from how many connections a
socket happens to have — so a 4-input hub with one wire is legal and appears in
the sample.

**The hub is not the OR node.** Nearly three quarters of hubs are 1-in-1-out:
they are routing waypoints, there to keep a hand-authored graph readable, and a
further 5% are 1-in-*n*-out fan-out points. Only about a fifth are used as a
multi-input merge, and when they are, they run 2 to 6 inputs.

And there is no OR node to fall back on. Whatever OR-ing happens, happens on a
socket.

**XOR is the one purpose-built merge.** Every `questLogicalXorNodeDefinition` in
the sample has at least two inputs and exactly one output. Its name asserts that
a second arrival does not fire it again; that is the class the engine offers for
a merge which must resolve once. *The runtime behaviour has not been observed
here* — only the shape and the frequency. If you need fire-once semantics, this
is the node to reach for and to test.

## What this licenses in this project

`source/quest_graph.json` merges in exactly two places:

    quest_done.Succeeded      5 incoming    [journal_quest]
    obj_decide_on.Active      2 incoming    [journal_quest]

Both are bare multi-connected input sockets on a `questJournalNodeDefinition` —
the fifth most common place vanilla puts one (17 in the sample), and 5 incoming
is well inside the observed range, which reaches 13.

Both targets set a journal entry to a state. **Setting an entry Succeeded twice
is the same as setting it once**, so the open question of whether a merge
re-fires cannot produce a wrong outcome here even if it does. That is a stronger
guarantee than "nothing can deliver two activations", which was the previous
argument and depended on the branch conditions staying mutually exclusive.

The rule for anyone extending the graph: **merging on a bare input socket is
fine when the target is idempotent** — journal state, `questSetVar` to a fixed
value, a phase output. When it is not — a counter, a reward grant, an item
handout — route it through `questLogicalXorNodeDefinition` and verify in game.

## Method

    unbundle .*\.questphase from all 32 content archives     -> 2,860 files
    anchored name-table scan: b"\x00" + class + b"\x00"
    random.seed(27); random.sample(sorted(all), 150)          -> shape census
    handles resolved document-wide before counting connections, because a
    socket appears once as {"HandleId": n, "Data": {...}} and thereafter as
    {"HandleRefId": n}; counting only the inline form undercounts badly.

Per D27 the population scan shipped negative controls:
`questMultiplayerAIDirectorNodeDefinition`,
`questMultiplayerTeleportPuppetNodeDefinition` and
`questMultiplayerChoiceTokenNodeDefinition` — real RTTI classes left behind by
the cut multiplayer mode, which no shipped file can author. All three returned
**0**, so a non-zero count means the class was authored rather than merely
resolvable.

A control only controls if the class exists. Three of the names first put in
this scan — `questLogicalOrNodeDefinition`, `questCombinedNodeDefinition`,
`questCounterNodeDefinition` — are not in the RTTI, so their zeros were
indistinguishable from a broken scanner and were dropped. Check the SDK headers
before counting a name.
