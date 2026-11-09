# The Cynosure-only experiment   (D129, answers D116 / OI-19)

**This is not the mod.** It is the third cell of D116's bisect table, which was
never measured:

| injected phases                  | result                                  |
|----------------------------------|-----------------------------------------|
| none                             | clean                                   |
| quest phase alone (r11)          | clean across repeated loads             |
| quest + Cynosure                 | **every save crashed at world load**    |
| **Cynosure alone**               | **what these two files measure**        |

The crash was `resourceToken.cpp:128 "WaitUntilLoaded can only be called on
main thread."`, on a loader thread, before ArchiveXL patched any phase in.
Until this cell is filled, "two injected phases" and "the bunker prefab refs"
are both still live explanations, and neither can be designed around.

The phase is `phase_revision 2`, not 1. Any save that loaded a build between
2026-09-04 and D116 on 09-17 is permanently marked as having already started
r1 - ArchiveXL sets that fact whether or not the phase ran, and the crash
happened before it ran - so r1 would have measured nothing on those saves.

## Run it

    GAME="/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/archive/pc/mod"
    cp mod/bisect/ashcache.archive    "$GAME/ashcache.archive"
    cp mod/bisect/ashcache.archive.xl "$GAME/ashcache.archive.xl"

Load a save. That is the whole test. The quest phase is NOT injected in this
build, so the quest itself cannot run and nothing about it is being measured.

* **Crash at world load** -> the prefab refs are the cause, not the pairing.
  The fix to try next is vanilla's shape: the prefab-holding phase as its own
  resource behind a `phaseResource` DepotPath, so the refs resolve when the
  player enters the node instead of while the save is being restored.
* **Loads clean** -> D116 was about having two injected phases, the refs are
  innocent, and the Cynosure phase can come back inside the quest's own graph.

If it loads, the rest of OI-19 is reachable from the CET panel: set
`world_state` -> `ashcache_cynosure_open` -> 1 and answer the three questions
in that issue, in order (does the outer bunker appear / can it be entered /
does the inner bunker appear and connect). Expect a dark, half-sealed bunker:
q305's airlocks, lighting and Cerberus are graph nodes in phases that are not
running. Setting the fact back to 0 unloads the sectors again.

## Put the mod back

    tools/deploy.sh --yes

A normal build overwrites `mod/archive/pc/mod/` with the shipping archive and
manifest, and the deploy copies both. Nothing here is ever deployed by
`tools/deploy.sh` - `mod/bisect/` is not in its PAIRS list.
