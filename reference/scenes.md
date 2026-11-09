# What the reference `.scene` files actually contain

Three `.scene` resources have been extracted and serialised to JSON under
`/mnt/sata/Cyberpunk2077/questmod-research/json_out/`. They are the entire
evidence base for `tools/gen_scene.py` under rule 8, and every session so far has
re-derived the same measurements off them by hand. This file caches them.

    dialog_only_template.scene   Undermine Quest Series
    template.scene               Undermine Quest Series
    hot_fuzz.scene               Hot Fuzz (a complete 11-file quest)

Re-measure with:

    python3 - <<'PY'
    import json, glob, collections
    for f in sorted(glob.glob("/mnt/sata/Cyberpunk2077/questmod-research/"
                              "json_out/*.scene.json")):
        r = json.load(open(f))["Data"]["RootChunk"]
        ...
    PY

(the full script is in the session that wrote this file; the numbers below are
what it printed on 2026-09-02.)

## The measurements

| | dialog_only_template | template | hot_fuzz |
|---|---|---|---|
| NPC actors (`actors`) | **0** | 1 | 3 |
| player actors | 1 | 1 | 1 |
| `lipsyncAnimSets` entries | 1 | 2 | 4 |
| entry points | 1 | 1 | **11** |
| exit points | 1 | 3 | **11** |
| `locStore` | empty | empty | en_us + pl_pl embedded |
| choice nodes | 0 | 1 | 1 |
| section nodes | 1 | 4 | 23 |
| quest nodes | 2 | 34 | 83 |

## What each number licenses

**A scene may have no NPC cast at all.** `dialog_only_template` ships 0 `actors`
and 1 `scnPlayerActorDef`, with a section node, two `scnDialogLineEvent`s and two
`scnQuestNode`s. So a solo-V scene that speaks and sets facts is a shipped shape,
not an extrapolation from the generator tolerating an empty list. This is what
`source/scene_decision.json` relies on (D14).

**A scene may have many entry and exit points.** Hot Fuzz has 11 of each. The
`sceneGraph`'s `startNodes` is built from the `entryPoints` list and `endNodes`
from `exitPoints`, and the questphase node that plays the scene exposes one input
socket per name in its own `entries` list. Two entry points is unremarkable.

**A choice node has SEVEN output sockets, whatever its option count.**

    hot_fuzz    1 option   7 sockets   connected [0]   mode attachToActor
    template    1 option   7 sockets   connected [0]   mode attachToScreen

Two mods, two authors, the same 7, with sockets 1..6 carrying zero destinations in
both. That is the editor's fixed shape rather than litter one of them left behind.
`CHOICE_SOCKETS = 7` in `gen_scene.py`; OI-7 records how this was settled.

**Both hub modes ship.** `attachToActor` when there is an NPC to hang the hub on,
`attachToScreen` when there is not. `mode` and `visualizerStyle` are independent —
Hot Fuzz ships `attachToActor` *with* `visualizerStyle: onScreen`.

**Every `scnChoiceNodeOption` condition slot is null in every sample *here*.**
All six — `questCondition`, `emphasisCondition`, `bluelineCondition`,
`triggerCondition`, `timedCondition`, `iconCondition` — across every option of
both choice nodes of the three reference mods. The only non-null scene conditions
in these three files are the `scnCheckSpeakersDistanceInterruptCondition` /
`...ReturnCondition` pair on interruption scenarios.

**That was mistaken for a fact about the game until 2026-09-03.** It is a fact
about three mods. All 7,067 vanilla scenes were then counted: `questCondition` is
non-null in **1,177 of them** (17%), and the shape is the ordinary quest
condition DSL.
`reference/choice_conditions.md` has the measurement, the worked example and the
one thing it still does not settle — a failing condition removes the option
rather than greying it, so D14's workaround stands for a different reason than
the one it was written for. See OI-14 and D26.

**One lipsync entry per actor, indexed by actor id, no exceptions.** Seven actors
across the three scenes; in all seven, actor N carries `lipsyncAnimSet.id == N`
and the table is exactly as long as the cast. That includes Hot Fuzz's Nibbles and
Johnny, who ship `animSets: []` *and* a valid lipsync id — which is what separates
"no animation of its own" (observed, fine) from "indexes nothing" (observed
nowhere). OI-10 has the full argument.

**Wrong-but-resolving references are tolerated.** `template.scene` is a Songbird
conversation whose two lipsync paths belong to a Japantown vendor and whose
`cinematicAnimSets` point at `sq031_07_cinema`, an unrelated quest it was cloned
from. It ships and works. So a reference that resolves is worth more here than one
that is thematically correct, which is why this mod's lipsync entries are that
same vendor's.

**`locStore` may be empty.** Hot Fuzz embeds `en_us`/`pl_pl` in its own `locStore`;
both Undermine scenes ship it empty and carry the text in an external subtitle
resource. This mod takes the external route (D7) — one file per locale for the
whole mod rather than one per scene, and `ua-ua` is a locale the base game has no
scene pipeline for anyway.
