# Decisions

## D1 — Mara's conversation: template a minimal `.scene`   (2026-09-01)

Copy `hot_fuzz.scene` as a structural template; strip custom animation and
cinematic camera work; keep the graph shape, sockets and the dialogue choice hub;
swap actors to Mara/V and replace the `locStore` with Ash Cache lines.

Rationale: gets the real vanilla dialogue UI (choice hub, subtitles, LocKey
pipeline) without authoring a performance graph from zero. Round-trip is proven
byte-exact, so a substituted scene can be validated by rebuilding it.

Accepted cost: Mara plays an idle loop rather than an authored performance.

### D1 revised — generate the scene, do not carve one down   (2026-09-01)

Superseded on contact with the material. `hot_fuzz.scene` is a *vanilla* scene
Deceptious edited (it is q003_08, the Stout scene) — 146 KB, 131 nodes, 83 of
them quest glue, and every section thick with animation, camera and audio events
anchored to vanilla NodeRefs that mean nothing here. Carving that down is a
subtraction problem with no way to tell a load-bearing field from a leftover.

Undermine Quest Series ships `mod/uqs/scene_template/dialog_only_template.scene`
instead: 13.7 KB, five nodes, **zero actors**, no animation events at all. That
is a positive existence proof for the minimal shape, so the scene is *generated*
from `source/scene_mara.json` by `tools/gen_scene.py`, matching how every other
resource in this mod is produced.

Confirmation that the template's own scaffolding is not load-bearing: its
`workspots`, `workspotInstances` and `ridResources` still point at sq031's
cinema, q203's wakeup and q304's Songbird escape — leftovers from whatever it was
cloned from, referenced by nothing in its five-node graph. The generator emits
none of them.

Accepted cost is unchanged and now literal: no performance at all. See D8.

## D2 — Voice: subtitles only for build 1   (2026-09-01)

Ship the first playable build with subtitles and no VO, as Undermine Quest Series
does. Wire `vomaps` and `.wem` after the quest is proven playable end to end.

Rationale: keeps the build loop fast and keeps the `.wem` encoder out of the
critical path. `WolvenKit.CLI wwise` is WEM->OGG only, so encoding *to* `.wem`
needs an external tool that is not yet identified.

## D3 — Ending availability: gate Hide only   (2026-09-01)

`ashcache_end_hide` requires `ashcache_mara_trusted`. Destroy, Absorb and Give-to-
Blue-Eyes are always offered.

Rationale: Hide is the one ending that structurally depends on Mara — she names the
off-grid Badlands cache and seals the case with her FIA lock. A player who
intimidated her has no reason to be handed that. The other three need nothing from
her, so gating them would punish without justifying.

Consequence to handle: the Hide script requires Mara alive. See open issue in
`docs/open_issues.md` — Mara must not be killable during the cleanup fight when
trusted, or the gate can be satisfied while the ending is unplayable.

## D4 — State Mara's survival as `ashcache_mara_dead`, not `_alive`   (2026-09-01)

The mara fact group had `ashcache_mara_alive` with `"default": 1`. Facts have no
default mechanism — the engine's fact store returns 0 for anything never written —
so that flag would read false for every player until something explicitly set it,
and the Hide gate would silently never open. Renamed to `ashcache_mara_dead` and
the gate tests `== 0`.

Rule this generalises to: **every fact must be correct when it is 0**, because 0
is what a fresh save reads. Phrase flags so that unset means the ordinary case.

## D5 — Build 1 resolves all four endings at the moment of the decision   (2026-09-01)

Each ending raises its own objective in `ac_ph5_resolution` and completes it
immediately, rather than waiting for the player to travel and act. Destroy and
Absorb genuinely resolve in the decision scene, so this is already correct for
two of the four. Blue Eyes (a handover) and Hide (a drive to the Badlands) each
want a travel leg; the wait node for those goes between their `_on` and `_done`
nodes when those locations become real content. Nothing else has to move.

Rationale: the quest is completable end to end now, and the journal still records
which ending the player took, which is the part that has to be right in the save.

## D6 — The Hide gate is enforced twice   (2026-09-01)

`gate_hide` runs before the choice is offered and writes `ashcache_hide_available`
for the choice hub to test; `br_hide` re-tests the same condition inside the ending
switch. The duplication is deliberate: the first is what greys the option out, the
second is what makes an unplayable ending unreachable even if the dialogue layer is
bugged, modded, or edited later by someone who does not know about D3.

`br_hide` is also checked **last** in the chained-false switch, and its own False
routes to `quest_done` rather than to an ending. So the failure mode for "no ending
fact was set at all" is a completed quest, not the gated ending and not a quest
stuck open forever.

## D7 — Subtitles ship as an external resource, not in the scene   (2026-09-01)

Spoken scene text has its own pipeline, entirely separate from the LocKeys that
carry journal and UI text:

    .scene line -> locstring ruid -> localizationPersistenceSubtitleEntries
                                  <- localizationPersistenceSubtitleMap (group "quest")
                                  <- .xl  localization.subtitles.<locale>

Both routes exist. Hot Fuzz embeds `en_us`/`pl_pl`/`db_db` text directly in the
scene's `locStore`; Undermine ships an empty `locStore` and an external subtitle
file per locale. This mod takes the external route: the text then lives in one
place per locale for the whole mod instead of once per scene, and adding the
eighteenth locale later touches no scene at all.

The ruids are arbitrary — Undermine ships a choice option keyed
`9999999999900000003`, a hand-picked number. So they get the same treatment as
LocKeys: a reserved block, allocated append-only by `tools/alloc_subtitle_ids.py`
into `source/subtitle_ids.json`, never renumbered. Block
**7731500000000000000-7731500000000000999**, carrying the same 77315 project
marker as the LocKey block so an id in a crash log is traceable to this mod.

## D8 — Mara speaks with no actor bound, for now   (2026-09-01)

**Superseded by D10 (2026-09-01).** Kept because the reasoning was right — it
just expired. One factual claim in it was also wrong and is corrected in D10:
Hot Fuzz does not leave *all* its lines unset.

The scene ships `actors: []` and every line carries `speaker: 0xFFFFFFFF`.

This is not a placeholder hack; it is the shape Hot Fuzz ships, where all 22
screenplay lines have the speaker unset. Giving Mara a body needs two things that
do not exist yet — a TweakDB character record and somewhere in the world to
stand — and a `spawnDespawn` actor pointing at a record that is not there is
exactly the hard-fail this project avoided by refusing to write a scene node
before the scene existed. The same reasoning, one level down.

Consequence: the choice hub uses `mode: attachToScreen` rather than
`attachToActor`, because with no actor there is nothing in the world to hang the
option list on. Both are one-field changes when the actor lands. See OI-6.

## D9 — World markers: generate empty sectors, always resident   (2026-09-01)

The quest's map pins and Mara's scene both point at NodeRefs (`#ac_mara` and
friends) that nothing defined. A NodeRef only resolves if some streaming sector
declares a node with that name, so the quest had eight names and no places.

`source/world.json` -> `tools/gen_sector.py` emits one `.streamingsector` per
location plus a single `.streamingblock`, registered by the `.xl`'s
`streaming: blocks:` key. That key is the mechanism verified in both reference
mods; without it the sectors are inert and every pin silently points at nothing.

Three choices, each taken from a shipped mod rather than reasoned from scratch:

- **`worldStaticMarkerNode` wrapping an empty `scnSceneMarker`.** A named point
  with no mesh, entity or collision — exactly what a pin points at and what a
  scene uses as its origin. Undermine ships seven.
- **`category: AlwaysLoaded` with a `streamingBox` of ±FLT_MAX.** The sector opts
  out of the world grid, so no cell index or bounds have to be computed. This is
  only legitimate because the payload is empty markers; a sector carrying meshes
  could not stay resident for the whole game.
- **`sourcePrefabHash: 0`.** Proven safe rather than assumed: Undermine's
  `uqs_mappin_penthouse` ships with `0` and is the marker its penthouse phase
  anchors a scene's `sceneLocation` to — the identical use.

### The NodeRef form is deliberately split

A `#` segment registers a globally addressable anchor, so
`$/03_night_city/ash_cache/#AshCache/#ac_mara` also answers to plain `#ac_mara`.
Undermine's own journal proves both resolve — it mixes the two forms in one file,
and all seven of its quest trigger areas are referenced short-form while declared
long-form.

So: **map pins keep the short form** (matches observed usage, and `journal.json`
already used it) and **`sceneLocation` uses the full path** (the only observed
sample does, and a scene anchored to nothing plays at the world origin instead of
erroring, which is a failure nothing would report). `validate.py` enforces both.

### Deferred markers are declared, not tolerated

`#ac_blueeyes_meet` and `#ac_badlands_cache` are referenced by the journal but
belong to locations that are not designed yet (D5). Listing them under
`deferred` in `world.json` is what lets the validator hard-fail on a misspelt
NodeRef without also blocking the build on known-missing content — the choice
would otherwise be between failing on work-in-progress and letting a typo ship
silently.


## D10 — Mara gets a body: cast a vanilla record, spawn her at her own marker   (2026-09-01)

Supersedes D8 and closes OI-6. D8 was correct that an actor pointing at a record
and a marker that do not exist is a hard-fail waiting to happen. Both now exist,
so the reason to wait is gone.

`source/characters.json` -> `tools/gen_tweak.py` emits a TweakXL record, and the
scene's `actors: ["mara"]` turns it into a `scnActorDef` that spawns her at
`#ac_mara` in `ash_cache_clinic.streamingsector`.

**Inherit a vanilla NPC; author no `.ent`.** The record is two meaningful lines —
`$base: Character.q306_fia_agent_corpo_scene_wa` plus overridden display names —
which is Hot Fuzz's entire mechanism. The alternative is authoring an entity
template, and a real one runs to ~100 components and 128 resolved dependencies
(measured on `judy_max.ent`). That is not a headless job. Every `base` and
`appearance` is verified against Appearance Menu Mod's `db.sqlite3`, so nothing
here is a record the game cannot spawn.

### Four things the references settled that assumption would have got wrong

- **`spawnMarkerNodeRef` takes the SHORT NodeRef form.** Hot Fuzz ships
  `#nq_judy_spawner`. The long `$/03_night_city/...` path belongs to a quest
  node's `sceneLocation` (D9) — so this mod deliberately references one marker
  two ways, in two fields, and `validate.py` enforces each separately.
- **The player takes the LAST actor id.** Hot Fuzz: judy_max 0, Nibbles 1,
  Johnny 2, Player 3. The Undermine template, with no NPCs, numbers its Player 0.
  An `actorId` is an index into a table read by position.
- **`mode` and `visualizerStyle` are independent.** Hot Fuzz's choice node is
  `attachToActor` *with* `visualizerStyle: onScreen`. So flipping the hub to
  `attachToActor` anchors it to Mara — whose nameplate it belongs to, where V
  looks — without changing how it draws. D8 read this as a visual change; it is
  not one.
- **Hot Fuzz does not leave every speaker unset** (D8 said it does). It sets a
  real speaker on 5 of 22 lines and pairs them: Judy speaks *to* the player, the
  player speaks *back to* Judy. That pairing is the shape copied here — hence the
  automatic addressee, and the `"to"` override for when it stops being a
  two-hander.

### `specCharacterRecordId` is written readable and ships hashed

The generator writes `Character.ashcache_mara`; the packed `.scene` comes back
holding `102920621884`. That is the correct cook, not a corruption: a TweakDBID is
`(len(name) << 32) | crc32(name)`, which computes to exactly that number, and the
same formula reproduces the `81306071356` Hot Fuzz ships for `Character.judy_max`.
The reference mods only *look* different because their editor cooked it earlier.
So the scene provably asks for the record `gen_tweak.py` writes.

### The marker reference now carries its `#`

`characters.json` originally wrote `"marker": "ac_mara"`. `validate.py` finds every
marker reference by scanning `source/*.json` for `#ac_*`, so the bare form was
invisible to it — a character pointing at an otherwise-unused marker would have
been reported as dead weight. Fixed at the source rather than in the checker,
because the project already had the convention: a marker *definition*
(`world.json`) is bare, a *reference* carries `#`. `characters.json` is a
reference. The existing typo and dead-weight checks then work unchanged.

### Where the TweakXL record lives

`build/tweaks/ash_cache.yaml`, deployed to `mod/r6/tweaks/` — a loose file, not
inside the `.archive`, and unmentioned by the `.xl`. It is generated in the same
build step as everything else so that renaming a character can never leave the
record and the scene that spawns it disagreeing.

## D11 — Verify every TweakDB id against the game's own TweakDB   (2026-09-02)

**Decision.** `tools/validate.py` now checks every TweakDB record id the mod
references against `/mnt/sata/cp2077-tweakdb/tweakdbstr.txt`, a dump of all
3,529,118 strings in the game's TweakDB, in both directions: ids the mod
*inherits* must exist, ids the mod *defines* must not.

**Why.** Rule 8 says do not invent engine APIs, and a TweakDB id is the easiest
kind to invent by accident. `Character.q306_fia_agent_corpo_scene_wa` is not
guessable, is not spell-checkable by eye, and is silent when wrong — Mara would
simply spawn as nothing. Until now these were verified by hand against AMM's
`db.sqlite3`, one at a time, at the moment of writing, with no way to notice a
later edit breaking one.

The proof that this matters was sitting in the reference material: Undermine ships
`districtID: District.Watson`. The real record is `Districts.Watson`. Undermine
ships, runs, and displays its journal entry regardless — so the engine tolerates a
dangling districtID completely silently, and *nothing short of a check like this
would ever surface it*. Ash Cache's own `Districts.Dogtown` turned out to be
correct, but it was correct by luck rather than by verification.

The reverse direction matters just as much and had no check at all. A record this
mod defines that collides with a vanilla one does not add a record, it *overwrites*
one — a mod that quietly replaces a base-game character. Rule 5's `ashcache_`
prefix exists to make that impossible, and this turns the convention into something
enforced rather than remembered.

**Cost.** Streaming 186 MB adds ~0.4 s to a validate run. If the dump is absent —
it lives outside the project and is not guaranteed to be on another machine — the
check prints how many ids went unverified and passes, because a missing dump means
"back to where this project already was", not "broken".

**What it verifies today:** Mara's `base`, both `_alternatives` bases, the player
puppet record, `districtID`, `recommendedLevelID`, `UINameplate.Always`, and that
`Character.ashcache_mara` does not already exist. Two negative tests cover both
directions.

## D12 — Items: inherit vanilla quest records, grant them from the graph   (2026-09-02)

**Decision.** Four items ship as TweakXL records in the same loose
`r6/tweaks/ash_cache.yaml` as Mara's character record, and the `.questphase` graph
hands them to the player with the engine's own `questItemManagerNodeDefinition`.
No redscript is involved, which keeps rule 1 intact.

    ashcache_splinter         the quest object      granted when the box is opened
    ashcache_mara_journal     readable shard        granted with the journal objective
    ashcache_courier_log      readable shard        granted with the room objective
    ashcache_fia_master_key   Hide ending only      granted behind br_hide

**Why inherit rather than author.** Same reasoning as D10 for characters, and the
bases were chosen by reading the *values* of the vanilla records out of the game's
own `tweakdb_ep1.bin`, not by copying a mod:

- `Items.q003_chip` — the Flathead from The Pickup — is the game's own plot
  MacGuffin: `Gen_Misc`, `ItemCategory.General`, `isSingleInstance`, tagged
  `Quest`, and its `objectActions` contain **neither Drop nor Disassemble**. The
  player cannot throw the plot away. Its one inherited action is a Flathead-
  specific `Crack` with an effector, so `objectActions` is cleared to `[]`.
- `Items.mq006_body_shard` is vanilla's own readable quest shard and brings
  `ItemType.Gen_Readable` plus the tag list
  `[Readable, Shard, SkipActivityLog, HideInBackpackUI, HideAtVendor]`. Its
  `_inline0` Read action is inherited too, so each shard's action overrides exactly
  one field: which journal onscreen it opens.

**Two things reading vanilla changed.** The first draft used
`Items.MilitechJunkItem3`, copied from the Lucy mod's own data item. That record is
`ItemType.Gen_Junk`, tagged `Junk`, and carries `ItemAction.JunkDisassemble` — one
"disassemble all junk" click and the quest object is gone. Fine for a collectible,
wrong for this. Second: Aldecaldos High Stakes writes
`hackCategory: HackCategory.DeviceHack` on its shard's read action where vanilla
writes `HackCategory.NotAHack`. Using `$base` inherits the correct value and the
question disappears.

**The grant node was the part most likely to be wrong.** No reference mod grants an
item to the player — Undermine uses `questInjectLoot` to fill containers instead —
so the shape was read off vanilla's `q003.questphase`, which contains three
`questAddRemoveItem` nodes (one of them granting `Items.RavenControlSplinter`).
Two fields are the opposite of a reasonable guess and all three vanilla instances
agree:

    isPlayer  = 0     NOT 1. The player is not addressed by this flag at all.
    entityRef = questUniversalRef with refLocalPlayer = 1    <- this is the player

Guessing `isPlayer: 1` would have produced a node that deserialises, packs, ships,
and gives the item to nobody. `tools/dump_graph.py` now prints the resolved item
name and whether the grant reaches `player` or `<<nobody>>`, so that specific
failure cannot hide.

**The readable-shard chain**, verified end to end from the packed resources:

    Items.ashcache_mara_journal          TweakXL, $base mq006_body_shard
      itemSecondaryAction ->
    Items.ashcache_mara_journal_inline0  TweakXL, $base mq006_body_shard_inline0
      journalEntry: onscreens/ash_cache/mara_journal
                                         ->
    .journal  FolderEntry 'onscreens' / OnscreenGroup 'ash_cache'
                                      / Onscreen 'mara_journal'
      title LocKey#77315027, description LocKey#77315028
                                         ->
    onscreens_{en-us,ua-ua}.json         both present, both real translations

**Not decided here:** what sets `ashcache_journal_read` and
`ashcache_courier_log_played` when a shard is actually read. That is a redscript
hook, it has no verified API yet, and it is OI-12.

## D13 — The glue layer: a generated redscript file, type-checked against the game   (2026-09-02)

The `.questphase` graph waits on ten facts it cannot set itself. Nothing set any
of them, so the mod installed cleanly and then did nothing: `await_start` blocked
on `ashcache_start` forever (OI-12). This is the layer that closes half of them.

**Decision.** `source/glue.json` declares, per fact, how the world sets it;
`tools/gen_glue.py` turns that into `mod/r6/scripts/AshCache/AshCacheGlue.reds`.
Five facts are now set:

    ashcache_start                a QuestsSystem listener on the vanilla q304_done
    ashcache_at_motel             proximity to a world.json marker, armed by act
    ashcache_at_clinic            same
    ashcache_courier_log_played   journal Visited callback on the shard's onscreen
    ashcache_journal_read         same

**Why this is not a quest state machine (rule 1).** It owns no objectives, no
journal entries, no markers and no branches. It writes five ints and the graph
reads them. Delete the file and the quest still has its journal entry, its
objectives and its map pins — it just never advances. That is the line the tech
spec draws around glue, and it is worth restating because "set the fact that
unblocks act 2" is one bad step from "run act 2".

**Generated, not hand-written, for the same reason everything else here is.** The
coordinates it triggers on come from `source/world.json`, so an OI-9 correction
moves the map pin and the arrival trigger together from one edit. The shard
journal paths come from `source/items.json`, so a shard's Read action and the
fact it sets cannot point at different entries.

### The verification, which is the actual news

There is a native `redscript-cli` at `/mnt/sata/redscript/target/release/`, and
the game ships its own compiled script bundle at `r6/cache/final.redscripts`.
Together they give a **type-check of mod redscript against the real game's RTTI**,
in under a second, with no game running and no Windows:

    redscript-cli lint -s build/scripts -b .../r6/cache/final.redscripts

`tools/lint_glue.sh` wraps it and `tools/build.sh` runs it at step 3b. Until now
"verified" under rule 8 meant *another mod does this and presumably ships*. It can
now mean *the compiler resolved this symbol against this exact game build*, which
is a strictly stronger claim.

It earned its place immediately. The installed, working mod SmugglersCache
declares `private func OnAttach()`; copied verbatim, that does not compile here —
redscript refuses to narrow an override's visibility. `OnAttach` is where the
listeners are registered, so the failure mode was a glue file that silently does
not compile, which is a quest that never starts. Decompiled vanilla also still
writes `new Vector4(x, y, z, w)`, which the current compiler rejects in favour of
`Vector4(x, y, z, w)`; the generated file sidesteps it with component arithmetic,
because the compiler that matters at runtime is the game's `scc.exe`, not this one.

The lint degrades to a printed note when the game or the compiler is missing, the
same way the TweakDB check does (D11), so the build still runs on a box without
the game.

### Design choices inside the file

**The watch is armed by act, not always on.** Each area names the value of
`ashcache_progress` during which its arrival can happen; outside that window
nothing is scheduled at all. This is both free and correct — the player who drives
past the clinic in act 1 must not pre-satisfy an act 2 gate. `validate.py` walks
the graph forward from `progress_N` and fails the build if the act it was armed
for is not the act the graph waits in, because the only symptom of getting that
wrong is a quest that stops advancing hours later.

**The sample rate follows the approach.** A fixed 1 Hz poll and a 25 m sphere can
be jumped clean through by a car at 60 m/s. The next sample is instead timed for
how long the remaining gap takes to close at that speed, clamped to [0.25 s, 5 s]:
one sample every five seconds when far away, four a second on the doorstep.

**`Visited`, not `State`.** `gameJournalListenerType.State` fires when an entry
becomes available, which for a shard is when it is picked up. `Visited` is the
game's own "the player opened this" signal — the one the Shards journal UI itself
listens to. The design says *read the journal*, not *carry it*.

**Everything is recomputed on load.** Facts persist in the save; the listeners and
the armed watch do not. `OnAttach` and `OnRestored` both re-register (idempotently)
and re-derive every fact this file owns from observable state, so a load lands
where a continuous session would have.

### What it deliberately does not do

Five facts stay unset and are listed under `blocked` in `glue.json` with what each
one needs. They are content gaps, not glue gaps: `world.json` generates marker
nodes only (D9) — empty named points, no geometry and no entity — so there is
nothing in the clinic to open, read, or fight. Tracked as OI-13. (Four, since D14
built the choice hub.)

A stubbed fact would be worse than an absent one. It advances the quest past a
beat that never happened, and it does it silently.

## D14 — The ending is a second scene, and its one gated option is a second entry
point   (2026-09-02)

`ashcache_decision_made` was the one of OI-13's five facts that needed no new
engine surface — a `.scene`, which this project already generates and has already
shipped once. `source/scene_decision.json` is that scene, and `decide_scene` in the
graph replaces the `await_decision` placeholder, the same move `await_box` made in
D1 once `scene_mara.json` existed.

Two things about it were decided rather than transcribed.

### The Hide option is gated by which door the scene is entered through

D3 says Hide is offered only when Mara is alive and trusted. The obvious way to
express that is a `questCondition` on the `scnChoiceNodeOption` — the option greys
out, the player sees a road not taken. `gate_hide` was even written for it: the
graph's own comment used to say it "leaves its answer in `ashcache_hide_available`,
which is what the choice hub tests to grey the option out."

> **2026-09-03 (D26):** the premise below — that no extracted scene ships a
> non-null option condition — was true of the three reference mods and false of
> the game; 1,177 vanilla scenes gate an option this way. The conclusion survives
> anyway: a failing `questCondition` removes the option rather than greying it.

Nothing tests it, because nothing can. `scnChoiceNodeOption` carries six condition
slots — `questCondition`, `emphasisCondition`, `bluelineCondition`,
`triggerCondition`, `timedCondition`, `iconCondition` — and across every extracted
scene, vanilla and mod, **every one of them is null in every sample**. The only
non-null scene conditions anywhere in the reference set are the
`scnCheckSpeakersDistance*` pair on interruption scenarios. Rule 8 does not have a
"but it obviously works" clause.

So the branch moved into the `.questphase`, where rule 1 wants quest logic anyway:

    obj_decide_on → route_hide  (If ashcache_hide_available == 1)
                      True  → decide_scene : decide_in_hide   (4 options)
                      False → decide_scene : decide_in        (3 options)

One scene, two entry points, two hubs, four shared destinations. `scnSceneGraph`
builds `startNodes` from the `entryPoints` list, so more than one is free; the
questphase node then exposes one input socket per name in its `entries` list.

Three things fall out of this that the `questCondition` version would not have
given:

  - `ashcache_hide_available` becomes load-bearing. Until now the graph set it and
    nothing ever read it — a fact whose entire job was to be tested by a test that
    was never written.
  - The hide path gets its own opening. It is not the same two lines with a fourth
    button underneath: Mara is alive and she named a place, and those are the lines
    that play. The option reads as a consequence rather than as an extra.
  - `br_hide` still re-tests the gate downstream (D6), so the enforcement is
    unchanged — two independent checks, neither trusting the hub.

The cost is the honest one: a greyed-out option teaches the player that something
was possible. Entering by another door does not. If a non-null `questCondition`
is ever observed in the wild, this is a small change — one hub, one entry point,
one condition — and OI-13's note says so.

### V is alone in it, and that is why the cast is empty

`actors: []`. Not an oversight and not laziness about writing Mara a farewell: a
`scnActorDef` is a **spawn instruction**, not a reference to someone already in the
room. Casting Mara would conjure her into the finale on exactly the branches where
`ashcache_mara_dead` or `ashcache_mara_hostile` is set — a corpse that walks in for
the last scene, or the agent V told to get lost delivering a warm goodbye.

A cast of nobody-but-V is a shipped shape, not an extrapolation. Undermine's
`dialog_only_template.scene` has **0 actors and 1 `scnPlayerActorDef`**, with a
section node, two `scnDialogLineEvent`s and two `scnQuestNode`s — the same parts
this file uses. The hub then falls back to `mode: attachToScreen`, which is what
Undermine's `template.scene` ships for its own hub. Both were checked in
`questmod-research/json_out/` rather than assumed from the generator tolerating it.

Anchored at `#ac_clinic_entrance`, one of the two coordinates D9 marks VERIFIED,
so the ending neither waits on OI-9 nor adds a sixth position to stand on.

That is deliberately *not* the marker the objective pins. `ac_obj_decide` sends the
player to `#ac_splinter_case`; the journal pin and the scene anchor are separate
things, and the anchor is very nearly inert here — a `sceneLocation` is the origin
everything in a scene is placed relative to, and this scene places nothing: no
spawned actor, no prop, a hub attached to the screen and a player acquired with
`findInContext` rather than moved. It still has to *resolve*, because a scene
anchored to nothing plays at the world origin rather than erroring. So the choice
is between two markers that both resolve, and the tiebreak is that one of them has
been stood on and the other is an offset guess that could be inside a wall.

## D15 — Placing world objects: three new node types, and a probe sector to prove
##       they work   (2026-09-02)

`gen_sector.py` wrote `worldStaticMarkerNode` and nothing else, so the four facts
left in OI-13 all shared one blocker: no way to put an object in the world. That is
now three more node types — `worldTriggerAreaNode`, `worldPopulationSpawnerNode`,
`worldEntityNode` — with every field measured off a real file. `reference/sectors.md`
holds the measurement table; this entry holds the calls that were judgement rather
than measurement.

### An entity is far cheaper than D10 made it look

D10 measured `judy_max.ent` at 100 components and 128 dependencies and concluded
that authoring an entity is a project. That figure is for a **character**. The
actual cost of *placing* one is a depot path and a transform, because
`instanceData` — the RedPackage carrying two hundred fields of per-instance
controller state, and the thing that makes an entity node look expensive — can be
**null**. Vanilla `quest_73110a178d6e7404` places `left_sided_low_cover.ent` that
way, two nodes after placing a computer that does carry a buffer.

So the buffer is an override, not a requirement. For a prop with nothing to
override, a mod can point at a vanilla `.ent` and write nothing else. Whether a
*device* can do the same is the one question left, and it cannot be answered
headless.

### So the probe sector is the answer to a question, not test scaffolding

`ash_cache_probe` holds one node of each new type, all at `#ac_clinic_entrance` —
one of the two coordinates D9 marks VERIFIED. That matters more than it sounds:
without it, "the object is not there" has three indistinguishable causes (wrong
coordinates from OI-9, a null `instanceData` the engine rejects, a wrong depot
path), and the whole point is to be able to tell them apart.

The prop is `base\gameplay\devices\masters\computers\computer_1.ent` with
appearance `computer_computer_2_angle_15` — the exact `.ent` and the exact
appearance vanilla places for mq058's computer, with the buffer removed. It is
also exactly the object `terminal_read` needs. One look answers it:

    appears, and can be used   -> terminal_read, box_opened and cabinet_opened
                                  are all cheap. Three of OI-13's four unblock.
    appears, but is inert      -> devices need the instanceData buffer. Expensive
                                  but bounded: it is transcription, not research.
    nothing appears            -> a mod-authored .ent is required after all.

It is a **separate sector** on purpose. A malformed node takes its own sector down
with it, and the two sectors carrying the real markers must not be in that blast
radius — every map pin and both scenes are anchored to them.

### The FIA cleanup crew is still not solved, and the reason is specific

The graph side is fully measured: `questSpawner_NodeType` is two fields, and its
target was verified rather than assumed — `#sa_ep1_37_car_01` in
`ep1_mq304_airdrops.questphase` resolves to a `worldPopulationSpawnerNode` of that
name in `quest_e495c59e9949e75b`. Spawn, wait for `questCharacterSpawned`, wait for
`questCharacterKilled` is a four-node vanilla phase.

What is missing is the enemies. **Every `objectRecordId` in every vanilla quest
sector is a `Vehicle.*`**; across 698 sectors not one mentions `Character.`, because
vanilla NPC groups come from communities, and a `.community` is a resource type no
mod in `questmod-research/` ships. Under rule 8 that makes "a spawner can carry a
Character record" a guess, so the probe ships the verified case — a vehicle record,
`spawnOnStart: 0`, activated by nothing — which tests only that a spawner node does
not break the sector it sits in. That is a smaller claim than the one needed, and
it is the one the evidence supports.

### Two checks that came out of this

A prop whose `entityTemplate` does not resolve **streams in as nothing at all** —
no log line, no placeholder mesh, no error. Since that is the same symptom as every
other way the probe can fail, `validate.py` now checks every depot path against
`/mnt/sata/Cyberpunk2077/depot_files.txt`, a listing of all 544,497 paths in the
game's archives. It is the resource-side twin of D11's TweakDB check and it
degrades the same way: no listing means a printed note, not a failure.

The same-point check had to become per-kind. Two markers at one point is a
copy-paste bug; a trigger centred on a marker, or a prop standing where a marker
points, is how these are meant to be used.

## D16 — The graph side of world content, and a probe that can actually answer

D15 gave `gen_sector.py` four node types, so the world can hold objects. Nothing
in the graph could talk to them. This is that half, plus a correction to D15's
own probe, which as shipped could not answer the question it was built to ask.

### The probe was inert

`spawnOnStart: 0` is what makes a `worldPopulationSpawnerNode` quest content: the
object does not exist until a graph node activates it. Every vanilla quest sample
ships 0, so D15 hardcoded 0 — and `ac_probe_spawner` therefore spawned nothing,
by design, with the CET panel dutifully explaining that it was inert on purpose.
That made it a test of "does this node break the sector", not of "does this node
work".

`spawnOnStart` is now a per-placement flag, defaulted to 0 and **rejected by
`validate.py` outside a probe sector** — quest content that ships with it set has
its ambush standing in the room hours before the quest starts, and nothing logs
that. The probes set it, so they appear on their own with no graph behind them.

### One probe became three, to make the spawner question answerable

The remaining unknown for `cleanup_done` is whether
`worldPopulationSpawnerNode.objectRecordId` accepts a `Character.*` record. It is
a guess because zero of 698 vanilla quest sectors do it — vanilla spawns NPC
groups from communities instead, and no reference mod here ships a `.community`.

One line of `world.json` asks the question, but only as a controlled pair:

    ash_cache_probe       trigger + computer   the instanceData question (D15)
    ash_cache_probe_car   Vehicle record       the control
    ash_cache_probe_npc   Character record     the variable

A Vehicle record is the only kind vanilla ever puts in a spawner, so if the car is
missing the NPC result means nothing — the location or the node is what failed.
Three sectors rather than one because a malformed node takes its own sector down
with it: a `Character` record loud enough to invalidate a sector must not be able
to take the control down with it and turn a clean "no" into "inconclusive".

`Character.q305_fia_agent` is a real Phantom Liberty FIA agent, checked against
the game's TweakDB by `validate.py` like every other record. It is who Hale's
cleanup crew would be, so a yes here is the content, not just the answer.

### Five graph pieces, measured then round-tripped

`gen_questphase.py` gained four condition terms and one node type. Every field and
both enums (`questObjectInteractionEventType`,
`populationSpawnerObjectCtrlAction`) came off real EP1 files — see
`reference/sectors.md`, which this work also corrected in two places.

    {"interaction": "#node"}                      the player used it
    {"device": "#node", "controller": "..."}      the device says so itself
    {"spawned": "#node"}                          they exist yet
    {"killed": "#node", "count": N}               N of them are down
    {"type": "spawn", "actions": [...]}           switch a spawner or community on

`count` has no default and the generator refuses to invent one. Both vanilla kill
conditions name an explicit number with `entireCommunity 0`; the `Greater 0,
entireCommunity 1` shape that the *spawned* condition uses would, on a kill
condition, go true on the first body and end the fight early. That is a bug you
would only find by playing it.

### Two ways to be sure the shapes are right

`tools/shapetest.py` builds a throwaway `.questphase` holding one of every new
piece, deserialises it to CR2W with WolvenKit, serialises it back, and reads the
fields out of what returned. WolvenKit refuses unknown field names and bad enum
values on the way in — verified by feeding it `objectRefX` and watching it produce
no file — and the assertions catch a wrong emitter default, verified by flipping
the interaction event to `Entered` and watching the test fail. Nothing it writes
is shipped; it lives in `build/shapetest/` and `build.sh` never looks there.

`validate.py` now walks the graph structurally for the world nodes it names, in
both the short `#ac_thing` form and a scene's long prefixed form. A condition
aimed at a node that was never placed never becomes true, and the quest stops
there with no error anywhere.

That check had to be made honest first. The old sweep was raw text over every
`source/*.json`, which cannot tell a use from a mention — so a NodeRef quoted
inside a `_comment` counted as a reference and could stand in for a real link.
`quest_graph.json` and `world.json` are now excluded from the sweep, because both
are walked structurally and `world.json` is where nodes are *defined*, not a place
that refers to them. `negtest.py` grew a third kind of case to hold that line: one
whose claim is that an edit is **legal** and the validator must stay quiet. A check
that fires on correct source costs more than one that misses, because the fix is
to weaken the check.

## D17 — The fourth micro-choice, and a check for one name spelled two ways   (2026-09-02)

Two things, and the second one found a bug in the first one's neighbourhood.

### The journal confrontation, as a second door

`source/facts.json` has declared `ashcache_mara_break` since the design was
written — "micro-choice C only (journal confrontation)" — and nothing set it. The
option needs to be offered only to a player who read Mara's journal shard, and the
obvious expression of that is a `questCondition` on a `scnChoiceNodeOption` so the
option greys out. No extracted scene, vanilla or mod, ships a non-null condition
there (OI-14), and rule 8 makes an unverified field a TODO rather than a design.
**Superseded in part by D26:** the field is real and now emittable, but it hides
rather than greys, so this branch stays.

So it is D14's move again, and for the same reason: the branch lives in the
`.questphase`, where rule 1 wants quest logic anyway.

    obj_mara_on → route_mara  (If ashcache_journal_read == 1)
                    True  → meet_mara : mara_meet_in_journal   4 options
                    False → meet_mara : mara_meet_in           3 options

Read back out of the cooked questphase:

    [30] If(ashcache_journal_read Equal 1)  True->[31]mara_meet_in_journal
                                            False->[31]mara_meet_in

The two openings are not the same three lines twice. On the journal path she can
*see* the shard in V's hands, so the beat `sec_open` spends establishing that she
is the one who hid the case is already spent — and what she buys with the saved
line is the admission that she left her own name lying on a desk. That is the
crack the fourth option widens.

`opt_break_j` is V quoting her back at herself: the journal says **she**, and out
loud Mara has said **it** three times. The section that follows ends where the
other two trust routes end — `fact_break` → `fact_trusted` → `fact_made` — because
breaking her is a *way* of earning her, not a fifth disposition. `facts.json` has
always read "micro-choice A, or C" for trusted, and now both bits are set, so
whatever eventually tells the routes apart has something to read.

Route evaluation is one-shot: a player who reads the shard *after* this node fires
gets the three-option hub. That is exactly `route_hide`'s behaviour and it is
correct — the conversation has already started.

### One character, one spelling

The clinic's antagonist shipped as **Hale** in seven spoken lines across two
scenes and as **Gale** in the journal shard — and, independently, as `Гейл`
against `Ґейла` in ua-ua. The same slip, made twice, in two alphabets.

Nothing downstream could catch it. Two spellings of one name are two valid
strings: they allocate LocKeys, they localise, they build, they ship. The player
just quietly meets two men.

`validate.py` now compares proper nouns across every `en-us` and `ua-ua` value in
`source/`. Getting it to zero false positives took two linguistic facts rather
than a tuned threshold:

- **A proper noun is a capital that is not sentence-initial.** A first draft
  compared every capitalised word and returned 12 hits, 11 of them grammar —
  `Burn`/`Bury`, `Then`/`They`, `Say`/`Day`. Dropping sentence openers dropped
  all 11.
- **Only same-length substitutions count.** An inserted or deleted letter is how
  Slavic case endings work: `Гейл`→`Гейла`→`Гейлом` is one name inflected, not
  two names. Counting those would bury the signal under correct grammar.

Strip the English possessive `'s` and `Gale's` versus `Hale` collapses to a clean
one-substitution pair. Both locales' bugs came out on the first run.

The check is an error, not a note, with a `NAME_TWINS` allowlist for pairs that
are genuinely both real. It is backed by two negtest cases, and the pair matters:
one asserts it fires on a mid-sentence misspelling, the other asserts it stays
quiet on `"Hate it or not, Hale is already moving."` — a sentence opener one
substitution from a real name, which is precisely what the naive version got
wrong.

### Not done, and now known to be blocked

`ashcache_terminal_full_read` was listed next to `mara_break` as authoring work
waiting on nobody. It is not. Pricing it out produced `reference/crafting.md`: the
recipe *record* shape is now fully measured off the shipped TweakDB, but what a
craft costs is not on the record and is unmeasured, there is no vanilla Neural
Dampener to craft, and — decisively — the fact is set by reading the clinic
terminal, which `glue.json` already lists as blocked world content. The
completionist read cannot exist before the required read does. The docs that said
otherwise are corrected.

## D18 — Six ways to fail, one symptom: the debug layer

Everything below is about what the mod can tell us when it is running, because
the next thing that happens to this quest is somebody testing it in game.

### The problem the panel actually solves

A quest mod can fail in six independent places, and from inside the game every
one of them looks identical — nothing happens:

1. `ashcache.archive` never mounted.
2. It mounted, but a file is missing from it.
3. `r6/tweaks/ash_cache.yaml` was not copied, so no item or character record
   exists.
4. `r6/scripts/AshCache/` was not copied, or failed to compile, so no trigger
   ever fires.
5. The localization tree did not merge, so every line renders as `LocKey#77315…`.
6. Everything loaded perfectly and the beat being waited on is one of the four
   OI-13 has no world content for.

Three of those six are *loose files that do not travel with the archive*. A
half-deploy is therefore the single most likely failure, and it produces a quest
that mounts, shows its journal entry, and cannot grant one item.

So the panel's first tab is not a cheat menu. It is a layer test: each row asks
the engine one question that only its own layer can answer.

| row | question | what only it can answer |
|---|---|---|
| archive | does `quests/main_quest/prologue/ash_cache` resolve? | the `.journal` exists only inside the archive |
| onscreens | do the two shard bodies resolve? | same archive, different file — separates "unmounted" from "file missing" |
| localization | does `LocKey#77315000` come back as text? | the locale jsons merged |
| tweaks | does `Items.ashcache_splinter` exist? | `r6/tweaks/`, a loose file |
| glue | is `AshCache.AshCacheGlue` attached? | `r6/scripts/`, a loose file |
| progress | where is the graph? | green stack + stuck quest ⇒ OI-13, not a build bug |

`Journal` then shows every objective's live `gameJournalEntryState`, because "no
map pin" and "the objective never activated" are one sentence to a player and two
different bugs. `Trace` polls every fact four times a second and logs
transitions, which turns *"I walked in and nothing happened"* into a timeline
naming the fact that did or did not flip. `Report` writes all of it to
`report.txt` next to `init.lua` and copies it to the clipboard.

### The build stamp

Both the panel and `tools/collect_logs.py` carry a SHA-1 of `source/*.json`.
Testing a stale deploy against fresh source produces bug reports for code that is
not running, and there is no cheaper way to find that out than being told.

### Reading the logs is not optional, and not doable by hand

The installed mod set produces **2,145 error lines in one TweakXL log** and 597
in one ArchiveXL log, none of them ours. Concluding the quest is broken because
somebody else's vehicle pack has an unknown property is a real hour to lose.

`tools/collect_logs.py` greps five log families for `ash_cache` only — and then
turns ArchiveXL's own vocabulary into a verdict, which is better evidence than
anything the in-game panel can infer, because it is the loader talking:

    [QuestPhase]     Merged phase "..." from "ashcache.archive.xl".
    [Journal]        Merging entries from "mod\ash_cache\journal\...".
    [Localization]   Merging entries from "...\localization\ua-ua\...".
    [WorldStreaming] Merging streaming block / Patching sector ...

A missing announcement is as informative as an error: no `[QuestPhase]` line for
us means the `.xl` never named the phase, not that the phase failed. The panel
says what the running game *believes*; the collector says what the loaders *did*.
When they disagree the loader is right and something is stale.

### tools/deploy.sh

Rule 2 says the game directory is touched only by an explicit, user-confirmed
deploy step. That step is now a script rather than five remembered `cp` lines,
because the failure it prevents — the half-deploy above — is the one the whole
diagnostics layer exists to diagnose. It is dry-run by default, needs `--yes`,
and `--remove` deletes only the five paths it created.

### One thing that got smaller

The journal root `quests/main_quest/prologue` existed in four places. The panel
now imports it from `gen_journal.py`, the generator that writes the resource: a
debug tool that disagrees with the thing it is debugging reports the archive as
unmounted forever and sends the tester to the wrong place, which is worse than
having no panel. `validate.py` keeps its own copy deliberately — the validator
has to be able to reject the source without any generator being importable.

## D19 — The clinic moves out of Cynosure and into a Dogtown shopfront   (2026-09-02)

Acts 2, 3 and 4 were anchored on AMM's "Cynosure Core" teleport preset,
(-2072.92, -2205.73, -194.78). The coordinate was never chosen for story reasons.
It was chosen because it was one of only two points in Dogtown this project could
prove were real geometry, and OI-9 said so plainly.

The cost only became visible when someone asked how to *walk* there. That point is
275m below the motel, inside the Phantom Liberty mission space V enters once during
*Somewhat Damaged* and does not return to. Reaching Act 2 meant an AMM teleport —
which works, and which reads as a bug to anyone playing.

### What "reachable" was made to mean

Not "the geometry exists" — that was the old standard, and it is what let a
275m-deep bunker pass. The new standard is that the engine's own navigation is
willing to route a player there:

    worldStaticGpsLocationEntranceMarkerNode

That node type exists so the GPS can plot a course to a building's door. There are
exactly **four** in the whole of Dogtown, harvested by unbundling all 273 EP1
level-0 exterior sectors from `ep1_1_nightcity.archive` and reading their node
data:

    {combat_zone_hillpark_gps}      -1764.12  -2639.38  45.00     485m from the motel
    {loc_q303_macs_clinic_gps}      -1891.75  -2486.90  28.00     358m
    {loc_q303_nighthawks_bar_gps}   -2423.12  -2669.31  28.01     223m
    {loc_q305_wtp_gps}              -2455.11  -2541.92  18.05     224m

One of the four is a clinic. The quest wanted a ripperdoc clinic in Dogtown, and
vanilla has exactly one with a registered pedestrian entrance, so the choice made
itself.

### What backs it up

    prefab            loc_q303_macs_clinic, dressed by q304 as Farida's
    interior volume   worldInteriorAreaNode {q304_Farida_interior_area}
    front door        base\gameplay\devices\doors\final\single_door.ent,
                      DoorController persistentState isLocked 0, isSealed 0
    furnishing        surgery benches, scalpel, anaesthetic, cyberdeck, four monitors
    sector category   Interior / Exterior, level 0 — ordinary streamed world,
                      not Quest-category, so it is present at any PL progress

The last line is the one that matters for a player who has barely started Phantom
Liberty. The room is permanent. Only the dressing is not: `q304_farida_shop_sign`
carries `isVisibleInGame: 0` and is switched on by that mission.

### What this cost

Four coordinates, four probe coordinates, and one player-facing string. The
objective read "Find the clinic beneath the stadium", which is no longer true, and
is now "Find the ripperdoc's clinic in Dogtown" in both locales. `docs/` prose that
described the clinic as being under the stadium was corrected with it. Nothing
structural moved — which is exactly what OI-9 predicted, and is the reason the
anchor was worth keeping in one file.

### What is still open

Whether that door opens outside q303/q304. Its authored state is unlocked, and a
runtime lock would be invisible in the files. That is now the single unverified
claim behind Act 2, down from "the whole act is behind a mission", and it is
answered by walking up to it.

## D20 — The phase entry socket is named `In1`, and that is not a style choice   (2026-09-03)

`source/quest_graph.json`'s input node had `"socket": "In"`. It now has `"In1"`,
and the output node `"Out1"`. `tools/gen_questphase.py` defaults to the same two,
`tools/validate.py` asserts them, and `tools/negtest.py` has a case for each.

### Why this was worth an evening

The in-game report from 2026-09-02 23:32 said all six layers `[ok]`, the quest
entry resolved, the journal merged, 35/35 LocKeys rendered, the glue was attached,
and `ashcache_start` had been 1 for fifteen minutes — while every one of the
fifteen objectives sat at `undefined` and every fact at 0. The player reported the
same thing from the other side: nothing happens when the quest is forced from CET.

That combination has exactly one shape: the phase was mounted and never entered.

### The mechanism

ArchiveXL does not merely register the phase resource. It synthesises a
`questPhaseNodeDefinition` inside the parent quest (`base\quest\cyberpunk2077.quest`
and the other four parents) that points at ours. The parent activates that node
**by socket name**, and the engine then enters the child graph at whichever
`questInputNodeDefinition` carries the matching `socketName`. No match, no entry —
and no diagnostic anywhere, because from the loader's point of view every resource
resolved perfectly.

The names ArchiveXL uses are hardcoded. `In1\0` and `Out1\0` sit in ArchiveXL.dll's
QuestPhase constant pool at offsets 1491924 and 1492252, wedged between
`"[{}] Patching phase \"{}\"..."` and `"[{}] Merged phase \"{}\" from \"{}\"."`.
(`strings` does not show `In1` — its default minimum length is 4. It took a raw
byte search to see it.)

### The evidence, in the order it was gathered

1. `ArchiveXL-2026-09-02-22-57-30.log:3798` —
   `[QuestPhase] Merged phase "mod\ash_cache\quest\ash_cache.questphase" from
   "ashcache.archive.xl".` So the merge itself succeeded; the fault is downstream.
2. The module's whole vocabulary, read out of the same constant pool:
   `quest / phases / path / parent / connection / input / output / intercept /
   node / socket`, plus the four failure messages (`parent phase is not loaded`,
   `input node doesn't exist`, `node with the same id already exists`,
   `output node doesn't exist`). None of those fired for us.
3. Every ArchiveXL-injected phase available on this machine, five from four
   unrelated mods, names its input node `In1`:

   | phase | shipped by | input | output |
   |---|---|---|---|
   | `mod\lifeswitch\quest\lifeswitch` | Prattler Prier | `In1` | (none) |
   | `mod\llquest\quest\llquest_root` | Longer Lockdown | `In1` | `None` |
   | `base\vendorsxl\phases\vendorsxl_1` | VendorsXL | `In1` | `Out1` |
   | `base\vendorsxl\phases\vendorsxl_limit_warning` | VendorsXL | `In1` | `Out1` |
   | `mod\uqs\launcher\uqs_launcher` | Undermine | `In1` | `Out1` |
   | **`mod\ash_cache\quest\ash_cache`** | **this mod** | **`In`** | **`Out`** |

4. The pairing is visible inside a working mod. `uqs_launcher`'s phase node for
   `uqs_alerts` has sockets `[CutDestination, In1(Input), Out1, Out2, Out3]`, and
   `uqs_alerts.questphase`'s input node is named `In1`. The phase node's socket
   name and the child's input node name are the same string, by construction.

### What made this expensive, and what stops it recurring

`_source: "verified"` was not the problem here; the problem was that *nothing in
the build knew this name mattered*. It read like a label. Six layer checks, 48
negative tests, a CR2W round-trip and a TweakDB cross-check all passed on a build
that could not run one node.

So the check is not "does the file parse" but "is the one string ArchiveXL will
look for actually present". `validate.py` fails the build on any other value, and
negtest case 49 restores `"In"` and asserts the build refuses it. Case 50 deletes
the input node entirely.

### What this does not explain

Nothing yet. If the quest still does not start with `In1` in place, the next
suspects in order are: whether the parent's input node re-fires on an existing
save (ArchiveXL's `connection:`/`intercept:` keys exist for exactly that kind of
control, and are unused here), and whether `await_start`'s pause condition
releases when the fact is already 1 at entry rather than only on a change.

### Postscript, same day: confirmed from source, and the first question answered

The user pointed out that ArchiveXL's source is checked out locally at
`/mnt/sata/cp2077-archive-xl`, which makes the whole byte-search above
unnecessary. It reads, in `src/App/Extensions/QuestPhase/Extension.cpp`:

```cpp
// PatchPhase(), the last thing it does before logging "Merged phase":
AddConnection(inputNode, aPhaseMod.input.socketName ? aPhaseMod.input.socketName : "Out",
              modPhaseNode, "In1");
```

`"In1"` is a literal in the argument list. It is never read from the child phase,
so there is nothing a phase can do to be entered under any other name. The
conclusion stands exactly as derived; the derivation was three steps longer than
it needed to be.

The same file answers the first of the two open questions, and the answer is not
the reassuring one — see **D21**. Read the source first next time. Reference
sources now checked out locally are listed in `CLAUDE.md`.

## D21 — The phase's depot path is an identity the save remembers, so it carries a revision   (2026-09-03)

`source/quest_graph.json` gained a `phase_revision`, and the phase now ships as
`ash_cache_r1.questphase` rather than `ash_cache.questphase`. That looks like
housekeeping. It is the difference between the D20 fix working on the user's save
and appearing to change nothing.

### The mechanism

All of this is in `cp2077-archive-xl/src/App/Extensions/QuestPhase/Extension.cpp`.

An injected phase is entered by two different routes, and which one runs depends
on whether the game is starting fresh or restoring a save.

**New game.** `PatchPhase` wires the parent's start node to the synthesised phase
node (`:228`), the root quest runs, the connection fires, the phase is entered
normally. `OnQuestStart` (`:143`) then writes a marker fact for the node (`:173`).

**Loading a save.** The parent's start node fired hours of playtime ago and will
not fire again — the graph is restored, not replayed. So a connection alone can
never start an injected phase on an existing save. `OnGameRestored` (`:97`) exists
precisely to cover that, and it is the *only* route:

```cpp
if (!factManager->GetFact(phaseFactId))                          // :132
{
    Red::DynArray<Red::CName> phaseNodeSockets{"In1"};           // :134
    Raw::QuestsSystem::ForceStartNode(aSystem, phaseNodeKey, phaseNodeSockets);
    factManager->SetFact(phaseFactId, 1);                        // :137
}
```

Read the order of those two statements. `ForceStartNode` returns `void` and is not
checked. The marker is written whether the phase ran or not.

The identity being marked is derived, not declared:

```cpp
auto phaseNodeKey = aPhaseMod.phasePath + ":" + std::to_string(aParentID);   // :357
auto phaseNodeId  = GeneratePhaseNodeID(...);                               // CRC16, :380
```

— then `QuestNodeKey{questNodeHash, phaseNodeId}` collapses to a `uint64`, and
`FactID` FNV1a32-hashes that to the fact key. Every input is deterministic, and
the only one under our control is **the depot path string**.

The store is `NamedFactStore` (`Red/QuestsSystem.hpp:104`, via the one-argument
`GetFact` at `:113`) — the same persistent, save-backed fact store that holds
`ashcache_start`. The marker survives the save.

### What that means for the save the user has been testing on

Last night's build merged (D20) and was force-started with `In1`, which matched no
input node, so nothing ran. Line 137 then executed anyway. That save now carries
"`mod\ash_cache\quest\ash_cache.questphase` has already started" as a permanent
fact. Deploying the D20 fix under the same path would hit line 132, read 1, and
skip the force-start entirely — the corrected phase would never be entered, and
the symptom would be identical to the bug it fixes.

Two consequences worth separating:

- Shipping the D20 fix alone would have looked like the diagnosis was wrong.
- Every future iteration tested on a save that already ran the phase has the same
  problem. This is not a one-off cleanup, it is a permanent property of injected
  phases, so it needs a permanent lever rather than a one-time rename.

### The fix

`phase_revision` in `source/quest_graph.json` names the resource:
`ash_cache_r{N}.questphase`. Bumping it changes the path, so the CRC16, the node
id and the fact id are all new, and `GetFact` reads 0 on any save. Checked
offline: the old and new paths give different node ids for **all 65536** possible
parent ids, so there is no parent quest for which the rename is a no-op.

- `tools/gen_xl.py` owns the name (`phase_resource_name`) and emits it.
- `tools/build.sh` stages the phase under it. The file is *built* as
  `ash_cache.questphase` and *packed* as `ash_cache_r1.questphase`, so no other
  tool needed to learn about the revision.
- `tools/validate.py` rejects a missing or non-integer revision; negtest 51/52.
- The CET panel prints the live resource name next to the build stamp, so which
  revision is actually mounted is readable in game instead of inferred.

### Why the revision is in the filename and not a YAML key

There is no ArchiveXL field for it. The path is the identity, so the version has
to be *in* the path — anything else would be a version number the engine never
sees. The cost is that `build/tree/` and the archive disagree on the filename,
which is why `build.sh` carries a comment saying so.

### What this still does not explain

Whether `await_start`'s pause condition releases when `ashcache_start` is already
1 on entry, rather than only on a 0→1 change. Untested, and now the only
remaining suspect if a clean force-start still produces no objectives. The glue's
`1 -> 0 -> 1` sequence in the 23:32 trace was the user working around exactly
this, and it should not be necessary.

---

## D22 — The journal was missing three whole entry classes, and one of them was a tree level

**2026-09-03.** The quest starts, the graph walks, and the player's report came
back with a different complaint: it does not look like a quest. No description,
no portraits, and messages from nobody.

Three reference journals were on disk the whole time. Counting entry classes in
them against ours:

| class | Hot Fuzz | High Stakes | Undermine | Ash Cache |
|---|---|---|---|---|
| `gameJournalQuestDescription` | 2 | 1 | 18 | **0** |
| `gameJournalQuestCodexLink` | 18 | 22 | 44 | **0** |
| `gameJournalContact` | – | – | 1 | **0** |

### What each one is

**`gameJournalQuestDescription`** is the paragraph the Journal shows above the
objective list — the thing that makes a vanilla quest read as a story rather than
a to-do list. It is a child of an *objective*, not of the quest, and always
carries the literal id `"description"`. `JournalQuestObjectiveBase` has a
`description` field of its own, which is the one-line objective text; these are
different things and both are needed. The engine returns them as an array
(`JournalQuestUtils.GetDescriptions` → `[wref<JournalQuestDescription>]`), so
writing one per objective makes the blurb grow as the player advances. Undermine
does exactly that. Ash Cache now ships twelve — one per spine objective and one
per ending, and none on the three optional objectives.

**`gameJournalQuestCodexLink`** holds a `gameJournalPath` into the game's own
codex tree, and is what puts the character portraits and location cards beside
the text. Vanilla repeats the *same set* on *every* objective of a quest — Hot
Fuzz carries three links on all three of its objectives. Linking is free: the art
comes from the codex entry named. Ash Cache links Dogtown, the Cynosure facility
and Pacifica, all three guaranteed unlocked because the quest requires
`q304_done`. Songbird's entry fits the premise and is deliberately not linked —
the player has not finished that storyline and it is theirs to reach.

Two spellings in that tree are wrong and must stay wrong:
`codex/locations/**distrcts**/…` (17 uses across four districts in the three
references) and `ep1/codex/quest/locations/**cyanosure**`. They are vanilla's own
typos in vanilla's own paths. Spelling either correctly produces a dead link.

**`gameJournalContact`** is the one that mattered most, because it is not
decoration — it is a level of the journal tree. The real shape is

```
PrimaryFolderEntry 'contacts'
  Contact 'uqs'                 <- avatarID, name, ContactType
    PhoneConversation 'alerts'
      PhoneMessage 'slot_1'
```

and the contact is what owns the avatar and the sender name. We emitted the
folder and then dropped conversations straight into it, which is neither shipped
shape: the messages arrived owned by nobody, so the phone had no name and no
portrait.

### The reversal

OI-2 closed on 2026-09-02 with the finding that Undermine files threads directly
under a bare `contacts` folder, and a comment in `gen_journal.py` recorded that
reasoning at length. That was wrong. Undermine's three thread ids *are* under
`contacts` — with a `Contact` in between that the earlier pass never descended
into. The mistake was reading a flat list of ids out of the file instead of
walking the tree and printing its depth. Fifteen lines of tree-walk found it.

Both shipped shapes are real, and the difference is only who owns the avatar:

- `contacts/<vanilla contact>` — appends to a real person's history and inherits
  their portrait. Hot Fuzz (`contacts/judy`), High Stakes (`contacts/panam`).
  No contact authored, because vanilla already has one.
- `contacts` + an authored `gameJournalContact` — a new contact carrying its own
  name, type and avatar. Undermine. **This is the correct one for Ash Cache**,
  whose senders are anonymous and belong to nobody vanilla.

Undermine leaves `avatarID` at 0 and gets the blank silhouette. There are 377
`PhoneAvatars.*` records in the game, including `Avatar_Unknown` — which is
exactly what an anonymous sender should look like — and `Avatar_Mr_blue_eyes`,
who is already a character in this quest's endings. Both now used, both checked
against the real TweakDB by `validate.py`.

### The cost of the tree level

Adding a level lengthened every message path by one segment:

```
contacts/ac_msg_unknown/ac_msg_unknown_01
contacts/ac_contact_unknown/ac_msg_unknown/ac_msg_unknown_01
```

The three `journal_entry` nodes in the graph address those paths. The old strings
stay perfectly valid strings — they resolve to nothing, the node loads, and the
SMS silently never arrives. `validate.py` cross-checks every graph journal path
against the journal tree and negtest covers the exact stale-path case.

### Order, not just content

The graph opened the journal entry first and delivered the two messages behind
it, so the quest announced itself and then explained why. Every vanilla side job
is the other way round: something buzzes, you read it, and only then does an
entry appear. The entry links are now
`await_start → sms_01 → sms_02 → quest_active → obj_dogtown_on`, and the messages
carry `delay` 0 and 3 — vanilla staggers a thread by 0 for the opener and 1–3 for
each follow-up (Hot Fuzz 0,2,2,1; High Stakes 3 throughout), so a conversation
reads as somebody typing rather than as a dump.

### What verifies it

A codex path that resolves to nothing does not draw and does not log. One
shipping reference mod carries `odex/glossary/world/militech` — a missing leading
`c` — and has presumably never once rendered that link. Faith is not a check, so
the CET panel gained two layer rows that resolve every codex path and every
contact in game, and the whole journal was read back out of the **packed
archive**: 12 descriptions, 45 codex links, 2 contacts with real avatars, delays
intact.

## D23 — The codex path was checked at the leaf and wrong at the stem, and voice needs no REDmod   (2026-09-03)

Two things came out of one question: whether the Cynosure codex entry can be
unlocked without finishing q304.

**It can, and the quest never had to unlock it.** `PopulateCodexLinks`
(`vanilla_scripts.reds:360616`) walks the codex links of the **tracked**
objective, resolves each target, and any target it finds `Inactive` it flips to
`Active` itself with `DoNotNotify`. The engine unlocks a linked codex entry on
sight. So the note in `journal.json` claiming these three were "guaranteed
unlocked because the quest requires `q304_done`" was true by accident and for the
wrong reason — the prerequisite has nothing to do with it, and a player who has
never set foot in Cynosure still gets the card.

Two consequences worth keeping. The unlock and the render are different branches
of the same `if`-chain, so the frame that unlocks does **not** draw the widget:
a freshly linked entry appears one objective update late, which looks like a bug
and is not. And only the first four links on an objective are ever spawned
(`codexLinksSpawned < 4`), so three is the ceiling worth authoring.

**The link was dead anyway.** The path shipped as
`ep1/codex/quest/locations/cyanosure`; the real one is
`ep1/codex/locations/quest/cyanosure` — the same two segments, the other way
round. The failure mode is the one this project keeps meeting: a codex link
whose `realPath` resolves to nothing is a valid string, the entry loads, the
objective loads, the journal renders, and the icon is absent with no log line.

What made it survive review is worth naming, because it will recur. Vanilla
misspells the leaf — `cyanosure`, not `cynosure` — and verifying that famous
typo *felt like* verifying the path. Checking the hard part of a string is not
checking the string. The two segments in front of it were never looked at.

So paths stopped being a matter of care. `reference/codex_paths.txt` is all 1013
`gameJournalCodex*` entries of the shipped game, walked out of
`base/journal/cooked_journal.journal` and `ep1/journal/cooked_journal.journal`
by joining each level's `id`, and `validate.py` checks every authored path
against it — class included, because Category, Group, Entry and Description are
four different classes at four valid paths, and a link pointing at the right
string on the wrong level fails identically. The check suggests the correction
when a leaf matches, which is how `cyanosure` gets found. Two negtest cases
freeze both halves.

That exposed a hole in the harness itself: `negtest.py` copied only `source/` and
`tools/`, so a check reading a file from `reference/` would have degraded to a
note and **passed**, in the one place whose entire job is proving checks fire.
`reference/` is copied now.

**Voice: no REDmod, and the ids already exist.** Custom VO is ordinary archive
content. `AldecaldosHighStakes` ships `.wem` files at
`mod\localization\en-us\vo\` plus a `locVoiceoverMap` of
`locVoLineEntry{stringId, femaleResPath, maleResPath}`, registered through
ArchiveXL's `localization.vomaps.<locale>` — the key confirmed in ArchiveXL's own
source (`Localization/Config.cpp:10`, `VoiceOverMapsNodeKey`), not inferred from
the file.

`stringId` is the locstring ruid, which `gen_scene.py` already bakes into the
scene from `source/subtitle_ids.json`. So text and audio are keyed identically
and cannot drift, and `gen_vomap.py` needed no new numbering at all — 43 lines
were already addressable.

The generator takes its manifest from the files on disk rather than a list,
because an entry whose `.wem` is absent from the archive is a dangling `raRef`:
the scene plays, the subtitle appears, there is no sound, nothing logs. Drop the
file, rebuild; delete the file and the map and its `.xl` entry go with it.
Untranslated locales inherit en-us **text** and never en-us **audio** — English
speech under Ukrainian subtitles is worse than silence.

`.wav -> .wem` is the one step that cannot be done here: nothing free encodes
Wwise Vorbis, and the pinned WolvenKit CLI's `wwise` subcommand is decode-only
and crashes on argument binding besides. Wwise **2023.1.14** exactly, Vorbis
Quality High, mono, 48000. `docs/voiceover.md` carries the whole procedure.

Decoding, on the other hand, is free — and that turns the game into a voice
corpus. Every VO file is named `<speaker>_<quest>_<f|m>_<ruid>.wem`, so a
speaker is a prefix match across 110,495 English lines: 2,714 Johnny, 1,863
Songbird, 1,926 Reed, 29,250 V. `tools/vo_rip.py` extracts and decodes them
through `vgmstream-cli` (rule 2: it only ever reads the game directory).

## D24 — Lipsync keys off the actor, not the line, and that was worth finding out before writing any of it   (2026-09-03)

The going-in assumption was that a lipsync entry keys off the same locstring ruid
`locVoLineEntry` uses, because everything else in the localization pipeline does.
It does not, and building on that would have produced a map that loads, merges,
logs `Lipsyncs merged` and animates nobody — this project's signature failure
mode, arrived at from a new direction.

**What it actually keys off.** The per-locale `.lipmap` (`animLipsyncMapping`)
holds two parallel arrays. `scenePaths[i]` is the FNV1a64 of a scene's depot path.
`sceneEntries[i]` holds `actorVoiceTags[]` — a **voicetag**, a third id namespace
that is neither the line id nor the character record — against `animSets[]`, one
`.anims` per actor. The line-level key is one level further down still: it is the
*name* of an animation inside that animset, `f_<ruid:016X>`.

Verified rather than reasoned. `FNV1a64("base\quest\minor_quests\mq029\scenes\
mq029_01a_garage.scene")` is `3647272176032198475`, which is `scenePaths[706]` of
the game's single `base\localization\en-us.lipmap`; entry 706's `actorVoiceTags`
is exactly the `voicetagId` that scene gives its `johnny` actor
(`1103967280742240508`); its `animSets[0]` is that scene's `johnny.anims`; and
that animset holds an animation named `f_194725D45D49D000`, whose hex **is** the
line's `locstringId.ruid`. Six values, four files, one chain.

**A voicetag is global to a character.** The Kidnap mod reuses Johnny's vanilla
number verbatim to give him custom lipsync in a mod scene. That makes
`source/voicetags.json` append-only by nature: renumbering one does not break one
scene, it unbinds that character from every scene at once. `alloc_voicetags.py`
reserves `7731600000000000000-7731600000000000099`, one digit off the subtitle
block so the two cannot be confused in a log.

**V gets nothing, on purpose.** The player keeps `voicetagId 0`. Zero of the 5688
shipped lipsync animsets name V — the game does not animate the player's mouth,
because V is normally seen from the inside. Allocating V a tag would have created
a key nothing can ever answer.

**The `f_`/`m_` prefix is the player's gender**, the same split the `.wem` pair
uses, not the speaker's. Vanilla writes both names on every line and ships only
the `f_` animation, so `gen_scene.py` writes both and an unresolved `m_` name is
demonstrably harmless rather than a crash.

**One loop, both arrays.** `LocalizationExtension::MergeLipsyncResource` opens
with `if (aSource->scenePaths.Size() != aSource->sceneEntries.Size()) return
false` — the *whole* resource is dropped, silently, not the odd entry. All 3495
vanilla entries satisfy it and so does the per-entry tags/animsets pairing. So
`gen_lipmap.py` never builds the two in separate passes; the invariant is
structural, not asserted. Ordering is not load-bearing: the merge does a
`lower_bound` over the **target's** sorted paths, and Kidnap ships an unsorted
array and works.

**The drop folder decides, twice.** `lipsync/<locale>/<character>.anims` is the
manifest exactly as `vo/<locale>/*.wem` is, and for a sharper reason: a lipmap
naming an animset that was not packed is a dangling `raRef` that merges cleanly
and moves no mouth. So the build ships no lipmap at all until an animset exists,
and removing the last one removes the map and its `.xl` entry with it.

**Verified from the packed archive**, not from the generator's own output: a test
build with a stand-in animset produced `mod\ash_cache\localization\en-us\
lipsync.lipmap` and `...\lipsync\mara.anims` at the depot paths the map names,
and reading the map back out gave scene voicetag `7731600000000000000` ==
`actorVoiceTags[0]`, `scenePaths[0]` == FNV1a64 of the packed scene's own depot
path, and `animSets[0]` == a path in the archive listing. The V-only scene
correctly got no entry at all.

**A postscript on OI-10.** Vanilla's `mq029_01a_garage.scene` points its
`resouresReferences.lipsyncAnimSets` at `base\quest\...\scenes\lipsync\johnny.anims`
and `...\v.anims`, and neither path ships — `scenes\lipsync` has zero hits in
every archive listing. That table is not the binding, and vanilla's own entries
dangle. OI-10's decision to point at arbitrary resolving paths was more correct
than the evidence available at the time could show.

**Still blocked (rule 8).** Authoring the `.anims` itself: `animAnimSet` with a
rig, opaque `animationDataChunks`, and an `animAnimationBufferCompressed` per take
at 344 joints / 414 tracks, `AdditiveFromRefPose`. No offline tool here, not
verified, marked TODO in `docs/voiceover.md` and tracked as OI-17. Two hard
blockers now stand between 43 written lines and a talking NPC, and they are the
same shape: both are encoders, and neither is a modding problem.

## D25 — The `.wem` wall was Vorbis, not `.wem`, and PCM walks around it (2026-09-03)

Every guide, this repo's own OI-16, and D23 said the same thing: `.wem` is
Wwise's container, only Wwise writes it, and it has to be **2023.1.14** exactly —
free, but behind an Audiokinetic account and a Windows GUI. That was accepted as
a hard blocker for two sessions.

It was the wrong statement of the problem. What nothing free writes is **Wwise
Vorbis** — a stripped Vorbis whose codebooks live outside the stream, which is
why `ww2ogg` only runs the decode direction. The **container** is a plain RIFF,
and Wwise plays uncompressed **PCM** as well as Vorbis. PCM has no encoder to
reimplement. It is 96 bytes of header in front of the samples.

**Checked before building anything.** A census of every `.wem` the game ships —
`audio_1_general` (4,434 files) and `audio_2_soundbanks` (4,796) — found **127
with `wFormatTag` `0xFFFE`**, uncompressed 16-bit PCM. Then the same census
across the 24 installed mods that declare a `vomap`: **LizziesBDs ships 116 PCM
files.** A codec the shipped data uses is a codec the shipped runtime has, and a
codec a published mod ships is one that survives contact with players.

The header was read off those files rather than off a spec, which mattered: the
only non-obvious field, `AkChannelConfig` at `0x28`, is packed
`(mask << 12) | (type << 8) | channels`, so mono is `0x4101` and not `0x1`. The
`junk` chunk is not filler either — it is what puts the sample payload at `0x60`,
16-byte aligned. Both are reproduced exactly.

`tools/wav_to_wem.py` writes it. Its header is **byte-identical** to a shipped
mono PCM `.wem` apart from the two size fields and the content hash. A vanilla
Vorbis line decoded with `vgmstream`, re-encoded by this tool and decoded again
comes back **sample-identical** to the reference downmix. Built, packed and read
back out of the archive: the `.wem` decodes as 48 kHz mono PCM, the vomap's
`stringId` matches `subtitle_ids.json`, and both `resPath`s name a depot path
that is in the archive.

**What is still not verified, and is stated as such (rule 8).** All 243 PCM
files — 127 vanilla, 116 from the mod — live under `base\sound\soundbanks\media`:
bank media, streamed by id. Every custom voice line in all 24 `vomap` mods (342
files) is Vorbis. So nothing shipped proves PCM through `locVoiceoverMap`'s
external-source path, which is the one this project uses. Both paths end in the
same Wwise source reader dispatching on the `fmt` tag, so it should hold. Only
the game can answer, and the failure mode if it does not is a subtitle with no
sound — exactly the status quo, so trying costs a rebuild.

The Wwise route stays documented, unchanged, as the fallback.

**The general lesson, which is why this is a decision and not a note.** "X is
impossible without tool Y" was inherited from documentation and never tested
against the game's own data. Ten minutes of counting bytes in files that were
already on this disk turned a hard blocker into a working tool. The other
inherited blocker, OI-17, deserves the same treatment before it is believed:
what does the shipped data actually contain, rather than what do the guides say
it takes to make it.

**Postscript, the same evening: the lesson paid off twice.** D25's closing line
said OI-17 deserved the same treatment before it was believed. It got it, and the
same shape of answer came back. `.anims` is not unwritable: the game's RTTI
carries four animation buffer classes, vanilla ships `animAnimationBufferSimd`
(13 of 208 sampled animations use it exclusively, 22 more alongside the
compressed one), and WolvenKit's `AnimationTools.ImportAnims` +
`AnimSIMDEncoder` write exactly that from glTF. Exporting a vanilla lipsync take
to `.glb` works headless here today. What is actually blocked is (a) the CLI's
`import` command, which declares no `--gamepath` and so cannot resolve the rig,
and (b) the viseme curves themselves — which is an animation problem, not a
format problem. OI-17 is rewritten around that. Both inherited "impossible"
claims turned out to be a true statement about one encoder mistaken for a
statement about the whole file.

---

## D26 — A choice option can be conditioned after all; it still cannot be greyed (2026-09-03)

D14 and D17 both routed around the same missing evidence: no extracted scene
shipped a non-null condition on a `scnChoiceNodeOption`, so under rule 8 the
construct was a TODO and the gate went into the `.questphase` as a second entry
point. Two scenes carry that workaround, and OI-14 has stood since as "find one
example in the wild and this closes."

The lesson at the bottom of D25 — that an inherited "no evidence" was never
tested against the game's own data — applies here word for word, so it was
tested. Every `.scene` in `basegame_4_gamedata.archive` was extracted, 7,067
files, and grepped. CR2W omits a property still holding its default and a null
`CHandle` is the default, so the *name* `questCondition` appears in a file only
when an option actually sets one — and only two classes in the entire RTTI have
a property by that name, one of which never lives in a `.scene`. The grep is
therefore exact *provided it is anchored on a null byte at both ends* — which the
first run of it was not:

    questCondition       1177 scenes   (17% of all scenes)
    bluelineCondition     764
    triggerCondition       65
    emphasisCondition       0
    iconCondition           0
    timedCondition          0

(That first column was wrong when D26 was written — it said 2,648, from an
unanchored search. Corrected the same day; see D27, which is about the mistake
rather than the finding.)

Three slots are genuinely dead. Three are not, and the busiest one is the one
both workarounds were written around.

`royce_default.scene` gates an option on
`questFactsDBCondition{questVarComparison_ConditionType q101_done Greater 0}` —
the exact structure `gen_questphase.build_condition` has emitted for the graph
all along. So `gen_scene.py` imports that function instead of growing a second
one, and `"condition": {...}` on an option now works in the same DSL as
everywhere else. Generated, it matches vanilla's structure; round-tripped through
CR2W it survives unchanged, and the packed `.scene` carries the same two class
names in its name table.

**And the workarounds stay.** The point of the greyed option was to let a player
see a road not taken, and a `questCondition` does not do that — it removes the
option. Three independent things say so:

  - `Inactive` and `CheckFailed` are bits in `scnChoiceNodeOption.type.properties`
    and the dialogue hub dims on them (`vanilla_scripts.reds:400227`), but across
    447 vanilla options that field is only ever 0, 1, 256 or 257. No author sets
    them; the runtime does, and `CheckFailed` arrives via `gameplayAction`, a
    TweakDBID naming an attribute-check record — a different mechanism entirely.
  - `scnChoiceNode.choiceFlags` has `IsValidInteractionFailsafeDisabled`. 360
    scenes set it; 343 of those — 95% — also carry a `questCondition`. A failsafe
    for "no interaction is valid" is only worth disabling if filtering can empty
    the hub.
  - There is no `inactiveCondition` slot. Every other `<x>Condition` names the
    flag it sets. `questCondition` names none, because it gates availability.

So D14's conclusion was right and its stated reason was wrong, which is a
different kind of error from D25's and worth naming: there, a claim was inherited
and never checked; here, a claim was checked, the check was sound, and the
*sample* was too small to carry the conclusion drawn from it. Three mods are not
the game. The fix is the same either way — count the shipped data before
believing a limit.

What changed on disk: `gen_scene.py` emits option conditions, `validate.py`
resolves their facts and refuses a hub whose every option is conditional (which
is how a hub opens empty and the conversation stops with nothing in any log),
three negtest cases hold both, and `reference/choice_conditions.md` records the
measurement. What did not change: `scene_mara.json` and `scene_decision.json`
still use two entry points, because the shape that works is not worth trading for
a shape whose runtime behaviour has never been seen in this mod. OI-14 carries
the one-line experiment and the three outcomes it can have.

## D27 — A name-table search needs a control, and mine did not have one (2026-09-03)

D26 measured the game by searching raw CR2W bytes for a property name, on the
sound principle that the format omits any property still holding its default —
so the name only appears when something wrote it. The principle is correct. The
search was not: it looked for `questCondition` anywhere in the file, and
`questCondition` is a substring of `questConditionNodeDefinition`, the quest
graph node class, which scenes embed. **1,177 scenes gate a dialogue option;
2,648 was reported.** Same error, same day, in `gameplayAction` inside
`gameplayActionData`: 46 reported as 257.

Anchoring the search on a null byte at each end fixes that failure and not the
other two. All three were hit while building one table:

  1. **Substring of a longer name** — fixed by anchoring.
  2. **A CName *value* equal to a property name.** The name table interns values
     and property names in the same list, so anchoring cannot separate them. In
     `.questphase`, 12 files contain `\x00optional\x00`; only 4 set the property.
     One of the others has a quest socket named, literally, `optional`.
  3. **Class names are decorated** as `handle:X` / `array:handle:X`, so an
     anchored search for a bare class name finds zero of thousands.

**What makes the D26 conclusion survive its own bad number** is a control that
was in the table by luck rather than design: `emphasisCondition`, `iconCondition`
and `timedCondition` are siblings of `questCondition` on the same class and come
back zero in *both* counting methods. Had name tables listed every property of
every class present, those would have matched wherever `questCondition` did. They
did not, so a hit means the property was written. The finding was never in
danger; only its size was.

**The rule this buys.** A cheap proxy measurement is worth running — grepping
7,067 files beats deserializing them by two orders of magnitude — but it must
ship with two things before its number is quotable: a **negative control** that
would have come out non-zero if the proxy were measuring the wrong thing, and a
**sample verified the expensive way**. OI-4 was then done in that order: 25
scenes deserialized out of the 1,177 (24 of 24 confirmed), and the questphase
census run by deserializing all 2,855 files rather than grepping any of them.

The lesson is not the same as D25's or D26's, and the three make a set. D25:
a claim inherited and never checked. D26: a claim checked soundly against a
sample too small to carry it. D27: a claim checked against the whole population,
with an instrument nobody had calibrated.

## D28 — Two open issues closed by measuring the game instead of arguing about it (2026-09-03)

OI-5 and OI-11 had the same shape as OI-4 did: a stated blocker of "assumed, not
observed". Both were settled against all 2,860 vanilla `.questphase` files,
using D27's discipline from the start rather than retrofitting it.

### OI-11 — the exit that does not exist

The issue asked for a distance-based exit or a timeout to stop Mara being left
paused mid-sentence when the player walks out, and noted that neither had a
worked example. **There is no worked example because the game does not do it.**

`questSceneInterrupt_ConditionType` and `questSceneReturn_ConditionType` are real
RTTI classes that look purpose-built for "wait until this scene is interrupted" —
they even carry their own `interruptConditions` arrays. Authored **zero times**
in 2,860 files. Two more dead classes for the list.

What vanilla does ship is on the scene node's `Default INT` / `Default RET`
outputs, and it is wired in only **13 of the 128 interruption-aware phases**. All
15 wired INT paths are the same four nodes: 500 ms `questRealtimeDelay`, then
`questSetTier_NodeType` to `Tier1_FullGameplay`. It is a **tier safety net**, not
an exit — nothing in the game routes an interruption to a cleanup, a despawn or a
cut. An indefinitely paused NPC is correct behaviour; Viktor Vector and Wakako
Okada do the same.

**No code changed.** Two things were recorded instead. First, a trap: this
project's scenes never leave `Tier1_FullGameplay`, so the safety net would be a
no-op — but anyone who adds a tier change must wire INT and RET at the same time
or an interrupted player can be left unable to move. Second, a reprieve: the 6 m
/ 5 m interruption distances inherited from the Undermine template turn out to be
the vanilla mode — `Greater 6` is the second most common interrupt distance in
the game and `Less 5` the most common return distance, out of 128 phases' worth
of literals.

### OI-5 — the plain shape is the idiomatic one

Over a seed-27 random sample of 150 phases (3,524 nodes): **238 input sockets
carry more than one connection, and 200 of them are bare sockets on ordinary
nodes.** Merging without a join node is what the game does, not a shortcut. One
socket in the sample takes 13 connections; this graph's widest takes 5.

Two things came out that were believed backwards. `questLogicalHubNodeDefinition`
is **not** the OR node — 73% of hubs are 1-in-1-out routing waypoints, and there
is no OR node class at all. `questLogicalXorNodeDefinition` is the one
purpose-built merge: always at least two inputs, always one output, never one-in.

The re-fire question is now moot for a better reason than before. Both merges in
this graph target a journal state change, and setting an entry Succeeded twice is
setting it once — true even if a merge *does* re-fire. The old argument ("nothing
can deliver two activations") depended on the branch conditions staying mutually
exclusive as the graph grew, and would have quietly stopped holding.

### The control caught something again, in the other direction

The join census originally ran with `questLogicalOrNodeDefinition`,
`questCombinedNodeDefinition` and `questCounterNodeDefinition` as negative
controls. All three returned 0 — and all three turn out **not to be RTTI classes
at all**. A zero from a name that does not exist is indistinguishable from a zero
produced by a broken scanner, so those were not controls, they were decoration.
They were replaced with the three `questMultiplayer*NodeDefinition` classes,
which are real, are left over from the cut multiplayer mode, and cannot appear in
a shipped file.

D27 said a proxy needs a negative control. D28 adds the obvious corollary nobody
states: **check that the control exists.** An instrument calibrated against
nothing reads zero very convincingly.

## D29 — Mara's protection, the tier that actually stops a player, and three coordinates nobody has stood on (2026-09-03)

Four things were settled here, all by counting the shipped game rather than
reasoning from the names of things.

**Tier2 does not stop anybody.** The brief was "movements are blocked … like
Vanilla", and the obvious reading of `GameplayTier` is that anything above
Tier1 restricts. It does not. From the game's own scripts, Tier3, Tier4 and
Tier5 each swap the player onto a dedicated locomotion state machine via
`PSMAddOnDemandStateMachine` (`LocomotionTier3/4/5`); Tier2 keeps ordinary
locomotion and only caps speed through `m_maxSpeedStat` / `Tier2WalkType`.
Tier2 is "walk slowly", not "stand still". So the first rung that delivers the
requirement is **Tier3_LimitedGameplay**, which also brings
`gameTier3CameraSettings` yaw/pitch limits — V is planted but can still look
around. Tier4 and Tier5 hand the camera to an authored cinematic camera, and
this project animates none, so choosing either would surrender the camera to
something that was never written.

**Census over all 7,825 vanilla `.scene` files (829 MB unbundled).**
`questSetTier_NodeType` appears in 985 of them (12.6%); `forceEmptyHands` in
189. By tier: Tier2 545, Tier3 215, Tier4 87, Tier5 54, **Tier1 zero**. Both
negative controls (`worldStaticMarkerNode`, `worldPopulationSpawnerNode`) read 0.

**Tier1's zero is a serialisation artefact, not a fact about the game.** mq029's
JSON plainly contains a `Tier1_FullGameplay` node, yet the string does not occur
in any of the 7,825 string tables. CR2W omits a field sitting at its declared
default, so the "restore to Tier1" half of every pair is invisible to a string
scan — as is `forceEmptyHands`, which only enters the table when something sets
it to 1. A string-table census therefore measures *which restrictive tier a
scene raises to*, and a zero from it must never be read as "never authored"
without first checking that field's default. The 204 tier-setting scenes that
name no tier at all are restore-only scenes.

**Every tier-setting scene uses a pair**: restrict + `forceEmptyHands 1` going
in, `Tier1_FullGameplay` + `forceEmptyHands 0` coming out. `forceEmptyHands` is
what satisfies "you can't use weapons" — it holsters and refuses the redraw.

**Mortality is a named claim, not a boolean.** 211 of the 7,825 scenes set
mortality through `questCharacterManagerParameters_SetMortality`. Vanilla's verb
is `Immortal` (104 files); `Invulnerable` occurs in exactly one file in the
whole game. `Mortal` occurs in all 211 — vanilla always releases the protection.
The worked example is `q001_00cd_boss_clean.scene`: `graph[32]` sets `Immortal`
and `graph[40]` sets `Mortal`, both with `source: q001_jackie_terminado` against
`#q001_scavengers_boss`. The on and off share one `source` string so two systems
can each hold a claim on the same NPC without clobbering each other, the way a
refcount beats a boolean. Mara's claim is `ash_cache_mara_protected`, and it is
**deliberately never released** — she has to survive past the end of the quest,
which is the one requirement that made this project depart from all 211.

That incidentally closes OI-1 by construction: the FIA cleanup runs after the
Mara scene in the graph, and she is already `Immortal` when it starts.

**`isPlayer` does not mean one thing.** On `SetMortality` the player is
`isPlayer: 1` with a `#player` NodeRef. On D12's `questAddRemoveItem` the player
is `isPlayer: 0` with `entityRef.refLocalPlayer = 1`. The flag is per-node-type
and carrying its meaning across node types produces a node that targets nobody,
silently. Both emitters record their own convention in their docstrings.

**D28's corollary fired on my own scanner.** An SDK grep for
`struct questSetTier_NodeType ` reported "NOT AN RTTI CLASS" for five classes
that are all real, because the SDK namespaces them (`quest::SetTier_NodeType`).
The controls were checked before any zero was believed, which is the only reason
this was a wasted minute rather than a wrong census.
`questMultiplayerNodeDefinition` genuinely does not exist and was dropped rather
than used as a control.

**Coordinates: derived positions are worthless and the build now says so.**
Seven of the ten world positions were captured by standing on them in game and
all seven are right. All three that were derived by offsetting from a captured
one are wrong: `ac_splinter_case` was inside solid rock (its capture is a 21 KB
all-black PNG where every other frame is 2-3 MB), `ac_motel_room7` was in a
parking garage under the motel, `ac_probe_car` was unreachable. Distance proves
nothing — the black-box guess sat 4.8 m from a verified point and was still
buried — because no data held here contains walls. So `check_verified` in
`validate.py` does not attempt a geometric test; it makes "never stood on"
countable, prints `7/10 position(s) stood on` in the build summary, and
hard-errors only where being wrong is both silent and unrecoverable: a scene
origin and a character spawn. `ac_motel_room7` is collapsed onto the verified
entrance and must declare `"collapsedOnto"`, so the one deliberate duplicate
cannot quietly cover for the copy-paste that check exists to catch.

A near-miss worth recording: `ac_splinter_case` was about to be placed at the
midpoint of the two deepest verified points. Reading the screenshots showed one
of them is outdoors on the plaza and the other indoors in the clinic, so that
segment crosses a wall. It was re-derived from two points that are both verified
*interior* instead.

**The trap D28 predicted is now live.** Raising the tier obliges wiring
`Default INT` and `Default RET`, or a player interrupted out of the conversation
is left unable to move with no error anywhere. Both scenes got the four-node net
(500 ms `questRealtimeDelay` → `questSetTier` Tier1), and `check_scene_tier`
now fails the build if a scene raises the tier without restoring it, or if the
graph node that plays it leaves either socket unwired. Three negative tests lock
it in; the suite is 84/84.

## D30 — The Cynosure lab is a quest sector, OI-14's refactor was disproved, and the voice pipeline had to be built rather than driven (2026-09-04)

### The Cynosure facility cannot be walked into, and the reason is structural

The question was whether the Cynosure laboratory can be reached without finishing
q305 — a real constraint, because that quest ends in a betrayal this playthrough
will not perform.

Every streaming sector in the game is compiled into one flat directory,
`base\worlds\03_night_city\_compiled\default\`, named by category and grid cell:
`exterior_-62_39_0_1.streamingsector`. The `loc_q305_bunker` folders hold only
lighting and envprobes, which is why searching for a sector by location name
finds nothing. The categories, from EP1's `all.streamingblock` (2,186
descriptors): Exterior 835, Interior 969, **Quest 381**, AlwaysLoaded 1.

`worldStreamingSectorDescriptor.questPrefabNodeRef` separates them perfectly:
non-zero on **381 of 381** Quest sectors and zero on all 1,805 others. A Quest
sector is not streamed by proximity — its `streamingBox` is ±FLT_MAX, which
disables distance streaming rather than making it infinite. It is loaded when the
quest prefab node it names is shown.

The Cynosure lab is two of them, and the metro chase a third:

    quest_c5762a0914e51033   #q305_pr_outer_bunker    4 variants
    quest_9ecf0f6eee9ee9de   #q305_pr_inner_bunker   11 variants
    quest_ec80f9c1c39f9ea0   #q305_pr_chase           1 variant

So the answer to "can I open the door without the quest" is that there is no door
to open. No amount of unlocking, teleporting or collision editing reaches it,
because the geometry is not loaded and nothing in the world will load it.

**What would work, unverified.** `questShowWorldNode_NodeType` takes an
`objectRef` NodeRef and a `show` bool, wrapped as
`questWorldDataManagerNodeDefinition → questShowWorldNode_NodeType`. The
installed mod Hot Fuzz uses it as a hide/show pair on `#q003_dildo_token`, with
`isPlayer 0` and `componentName None` — a worked example under rule 8. Pointing
one at `#q305_pr_inner_bunker` with `show: 1` is the shape that should load the
lab from a custom phase. It is **not verified**: that a quest prefab node
responds to this the way an ordinary world node does is inference from the
descriptor binding, not observation, and the 11 variants mean the state that
loads is whichever the prefab defaults to — an empty lab with none of q305's
scripting, NPCs or set dressing state.

Also settled while there: the quest's start prerequisite is **`q304_done`**
("Somewhat Damaged"), not anything from q305. q304 is where V is scanned inside
Cynosure, which is what this quest is about, and it happens before the
Songbird/Reed betrayal. Nothing needs changing — the earlier note that a
`q305_postcontent` prerequisite would have to be replaced was about an option
that was never taken.

### OI-14's remaining experiment is disproved, not deferred

The issue proposed collapsing each scene's two entry points into one hub with a
conditional option, described as "one line of JSON each". Measured against the
scenes: the two paths are **not** duplicates. `scene_mara.json`'s `sec_open` and
`sec_open_j` are different writing — the journal opening has Mara react to the
shard in the player's hand ("don't palm that shard, I can see the read light from
here") — and `scene_decision.json`'s `sec_open` and `sec_open_h` differ the same
way. Only `start`/`start_journal` are byte-identical.

So the refactor would delete four authored openings to save three mechanical
nodes per scene. The premise was that the second entry point exists only to add
an option; it exists because Mara says something different to a player who read
her journal. That is the feature.

The greying itself remains unauthorable — `Inactive` and `CheckFailed` are set at
runtime and no author sets them in 447 sampled options — so the issue closes at
"as far as it can go". A probe (one always-false conditional option in the base
hub, to observe whether the runtime removes, dims or ignores it) was specified
and deliberately **not shipped**: if the runtime ignores conditions, every player
on the untrusted path sees an option they did not earn, and trading a
guaranteed-correct hub for a cosmetic answer during someone's actual playthrough
is the wrong direction. The probe is recorded in OI-14 for a dedicated test pass.

### The voice datasets did not exist, so they were built

The brief was that character datasets and Applio settings were already prepared
and only needed a button pressed. Neither is on this machine, and no `.pth` or
`.index` for the two downloaded models is either. `tools/vo_dataset.py` and
`tools/rvc_train.sh` now build both from the game. Two settings are forced rather
than chosen: **48000 Hz**, because the game's lines decode at 48 kHz mono, and
**HiFi-GAN**, because it is the only vocoder with a 48000 pretrained pair present
(`f0G48k.pth` + `f0D48k.pth`) — RefineGAN ships 24k and 32k only, so selecting it
at 48000 silently trains from scratch and does not finish in a night.

Two silent dataset bugs were found and fixed, both of which train cleanly and
sound wrong:

  * `vo/` and `vo_holocall/` hold two mixes of one recording under the same file
    name. 8,332 names collide, `vo` sorts first, and the loop wrote both to the
    same `.wav` — so the band-limited holocall take always won. 451 of Songbird's
    1,863 lines have one, and a model trained on that learns the radio filter as
    part of the timbre. Johnny has 20 and V has none, which is why a smoke test
    on one speaker would not have caught it.
  * `_f_`/`_m_` is the player's gender (D24). For an NPC that means two takes of
    one actor — Rogue is 794 to 3 — and deduping is free. For V it means two
    different actors: 14,560 female, 14,690 male, 14,538 lines shipping both.
    `--gender` is now mandatory for any `v*` speaker, because the alternative is
    a model trained on the average of two people.

## D31 — Cynosure loads because a phase owns its prefab, and MIOpen was searching, not compiling (2026-09-04)

Two things were half-right yesterday and are now settled by reading the game and
measuring the machine instead of reasoning from a shape.

### The Cynosure mechanism, verified rather than inferred

D30 recorded that the lab lives in Quest-category streaming sectors with
`streamingBox` at ±FLT_MAX, and proposed `questShowWorldNode_NodeType` as the way
in — explicitly marked inference under rule 8. It was the wrong node.

`q305_06_outer_bunker.questphase` and `q305_07_inner_bunker.questphase`, pulled
out of `ep1_2_gamedata.archive` and serialised, carry the answer as a field on the
resource itself:

    questQuestPhaseResource.phasePrefabs = [
      questQuestPrefabEntry { prefabNodeRef "#q305_pr_outer_bunker" },   (q305_06)
      questQuestPrefabEntry { prefabNodeRef "#q305_pr_inner_bunker" } ]  (q305_07)

and the same list per-node as `questPhaseNodeDefinition.phaseInstancePrefabs`
(q305_07 node 128). **A quest sector is streamed for exactly as long as some
active phase names its prefab.** That is what the `questPrefabNodeRef` on all 381
Quest descriptors binds to, and it is why the ±FLT_MAX box is meaningless: there
is no proximity streaming to have a radius for. There was never a door to open.

`questShowWorldNode_NodeType` is real but is a second, finer step. q305_06 node
476 uses it on `#q305_pr_inner_bunker` with `show: 1` so the inner bunker is
visible through the airlock while the outer phase still owns the streaming. In
`mq305_03_bunker_exploration_setup` it appears only on props
(`#mq305_lab_footprints_01/02`), while that quest's *location* geometry is driven
by `questTogglePrefabVariant_NodeType` on `#loc_mq305_wanted_lab_lighting` and
`#loc_mq305_wanted_lab_env_int`. Showing a node no active phase owns loads
nothing. (mq305 is also not Cynosure — its lab is reached through the q302 subway
tunnel. That lead did not pan out, but it is what corrected the node type.)

### Why this ships as a second questphase resource

ArchiveXL attaches a phase to the **root** quest graph, so the phase runs from
game load until its output node fires — and `ash_cache`'s output node fires when
the quest ends. Anything that has to outlive the quest cannot live in that graph;
it would be cut at the moment the player finishes. So `source/cynosure_graph.json`
is built and injected as its own resource, `ash_cache_cynosure_r1.questphase`,
with its own `phase_revision`. `gen_questphase.py` now builds a list of graphs and
`gen_xl.py` emits a `quest.phases` entry per built phase.

The graph is three nodes: `input → pause(ashcache_cynosure_open == 1) →
prefab_phase → back to the pause`. It has **no output node**, deliberately — six
of the 61 q305/mq305 phases ship the same way (`q305_06_ob_lightning`,
`q305_06_ob_fx`, `q305_06_ob_devices`, `q305_07_ib_ui`, `q305_07_ib_sfx`,
`q305_outer_bunker_malfunctioning_doors`), and all six are ambient world-state
phases. A phase that holds a prefab is not supposed to finish. The loop back to
the pause is what makes it reversible: set the fact to 0 and the inner
`questPauseConditionNodeDefinition` releases, the phase exits, the sectors unload,
and the wait re-arms without reloading the save.

**Default off, and enforced.** Nothing in this mod sets `ashcache_cynosure_open`.
That is the entire safety argument for shipping a world change no one has tested,
so `validate.py` fails the build if the quest graph or the glue ever sets it, and
`negtest.py` holds both that and a mistyped prefab ref. The refs themselves are
checked against `reference/examples/quest_prefab_streaming.json`, which records
where each was read out of vanilla — the point being that the two names are
quoted, not remembered, and a third has to be quoted too. The CET panel picked the
fact up on its own, so the switch is a button rather than a console line.

**What is not verified:** that the bunker is walkable. Loading geometry is not
running q305 — the airlocks, the Cerberus, the lighting states and the set
dressing are graph nodes in phases that are not active. Expect an empty, dark
bunker with some doors shut. That needs a playthrough, and it is why this is
opt-in.

### MIOpen: the trap was exhaustive search, not first-run compilation

D30 told the user to expect "several minutes" of MIOpen kernel compilation on the
first run and not to kill it. Measured: **2 h 35 m elapsed, 2 h 09 m of it one CPU
core in the compiler, GPU at 0%, 144 MB of cached kernels, and step 1 of epoch 1
had still not run.** That is not a slow start, it is a run that never finishes,
and the advice to wait it out was wrong.

Cause, in two halves. MIOpen keys its tuning databases on `<arch>_<num_cu>`, and
on RDNA2 `num_cu` counts work-group processors, not compute units: 60 CU / 2 = 30,
so this card is `gfx1030_30`. ROCm 7.2 ships exactly one gfx1030 database,
`gfx1030_36` — the 72-CU RX 6800 **XT**. Every lookup misses. On its own that is
survivable; combined with Applio's `torch.backends.cudnn.benchmark = True`
(`rvc/train/train.py:121`), which on ROCm means MIOpen **exhaustive find**, each
miss becomes compile-and-time-every-candidate-solver, per unique tensor shape.

Three fixes, in `tools/rvc_train.sh`:

  * `MIOPEN_FIND_MODE=FAST` — immediate-mode heuristic instead of benchmarking.
    One kernel compiled per shape instead of every candidate. This is the big one.
  * `MIOPEN_SYSTEM_DB_PATH=/mnt/sata/Cyberpunk2077/miopen_db` — a directory of
    symlinks to the shipped database with `gfx1030_36` also exposed under this
    card's `gfx1030_30` key, so its 106,105 tuned entries are actually consulted.
    Same ISA, different WGP count: not optimally tuned, but valid, and "not
    optimal" beats "search from nothing" by orders of magnitude.
  * `APPLIO_CUDNN_BENCHMARK=0`, read by one patched line in Applio's `train.py`
    (original kept as `train.py.orig`). The default there is still `True`, so the
    GUI is unchanged.

Result on the same dataset, same card, same cache: **first step in 126 s, then
1.25 s/it and ~2.7 min/epoch, GPU at 99%.**

The remaining shape churn was left alone on purpose.
`data_utils.TextAudioCollateMultiNSFsid` pads each batch to the longest item *in
that batch* rather than to the bucket boundary, and the sampler reshuffles every
epoch, so new padded lengths keep arriving. Quantising the padding would cap the
distinct shapes at about ten — but the padded length is always the max of a real
sample, so the shape space is bounded by the slice count (~1k here) and saturates
after the first several epochs anyway. A bounded cost that disappears on its own
is not worth patching the tensor the model masks and slices against.

Two further bugs in `tools/rvc_train.sh`, both found by reading the queue log
rather than by anything failing:

  * It printed `=== mara done: .../mara.pth ===` for a run that never completed a
    single step. `core.py` is a wrapper; killing the inner `rvc/train/train.py`
    still lets the wrapper exit 0, so a zero status is not evidence a model
    exists. The queue would have walked on to the next model reporting success
    for a file that was never written. It now checks the artifact, not the status.
  * The header claimed a four-stage pipeline ending in `index`, and `run_one`
    never ran the index step. A `.pth` with no `.index` is a voice with no
    retrieval — Applio just runs at index-rate 0, which sounds like a worse model
    rather than a missing file. Added, and skipped when one is already there.

Operational note that cost a queue: **editing a running bash script corrupts it.**
Bash reads a script incrementally, so rewriting `rvc_train.sh` in place while the
detached queue was executing it produced `syntax error near unexpected token ')'`
at the exact byte offset the shell had reached, and the queue died after the first
model instead of continuing to the other two. Write to a temp file and `mv` it
over — rename leaves the running process on the old inode.

Epochs dropped 300 → 200 for the queue. With a pretrained base and ~35 minutes of
data an RVC model is converged well before 200, `save_every_epoch 10` with
`save_every_weights` means every tenth epoch is kept as its own candidate, and at
~2.7 min/epoch the difference is five hours — which is the difference between one
model finishing overnight and two.

### Correction, 2026-09-04, and the guard it produced

I reported that the queue restart "cost nothing" because Applio had resumed from
an epoch-8 checkpoint. The equation I based that on — `1310 = 10 × 131` against
`global_step = (epoch_str - 1) * len(train_loader)` at `rvc/train/train.py:467` —
was correct, and belonged to a different process.

`rvc_logs/mara.log` holds **two interleaved arithmetic sequences**, both at 131
steps per epoch:

    A   epoch  9 → 19    05:46:28 – 06:26:50    ~4.0 min/epoch
    B   epoch  1 → 20    05:54:12 – 07:02:28    ~4.0, then 2.8 from 06:28

Two trainers, one experiment directory, 43 minutes. A had genuinely resumed from
epoch 8; B — the survivor — started from scratch. B's per-epoch time falling from
4.0 to 2.8 the moment A stopped is the GPU-contention signature and is the clean
confirmation. So the restart cost a full restart *and* forty minutes of both runs
at half speed, and the first weights file was written by the lineage that died.

The reason it was invisible is structural, and worth remembering for anything
launched this way: **the trainer is a grandchild.**

    rvc_train.sh  ->  core.py train  ->  rvc/train/train.py

Killing the queue kills the shell and `core.py`. The trainer is reparented to
init, keeps its GPU context and its append-mode log handle, and `pgrep` on the
queue's own name finds nothing — so the machine looks idle while a full trainer
is still running and still writing checkpoints. Checking for the thing you
started is not the same as checking for the thing that is running.

Three fixes in `tools/rvc_train.sh`, all verified before install:

  * `run_one` refuses a model that already has a live `rvc/train/train.py <model>`
    process, naming the pid to kill. Matched on the trainer's argv, never on the
    caller's — a pattern that appears in the asking shell's command line matches
    the asking shell, which is how the process count was miscounted twice.
  * A queue-wide `flock` on `rvc_logs/queue.lock`, held on a descriptor so a kill,
    a crash or a power cut releases it with no cleanup step. That matters here:
    being killable at any moment is the whole design of this script.
  * `--status` printed `epoch 2620` for epoch 20 of 200, because `G_<n>.pth` is
    named for `global_step`. Against a 200-epoch target that reads as finished.
    The epoch is only spelled out in `<model>_<epoch>e_<step>s.pth`; it now reads
    the epoch from there and prints the step separately.

`mara_10e_1310s.pth`, lineage A's only surviving weights file, was moved to
`rvc_logs/orphaned/` with a README rather than deleted. It is a valid model, but
sitting beside `mara_20e_2620s.pth` it invites a comparison between two lineages
that share no weights.

## D32 — Three journal icons, three different mechanisms, and one of them was never broken   (2026-09-04)

OI-18 recorded two icon defects side by side, as if they shared a cause. They do
not share a mechanism, a data source, or even a widget, and one of them is not a
defect. All of this is read out of the game's own scripts and the ep1 journal;
`reference/examples/journal_icons.json` quotes the code.

**1. The linked-entry row is working.** `QuestCodexLinkController.SetupCodexLink`:

    if CodexUtils.IsImageValid(codexEntry.GetLinkImageID()) { RequestSetImage(...) }
    else { this.GetRootWidget().SetVisible(false); return; }

There is no generic card. An invalid link image hides the card outright, so three
cards visible *is* the evidence that three link images are valid. Both ep1 targets
carry real art (`UIJournalIcons.l_dogtown`, `UIJournalIcons.l_cynosure`).
`IsImageValid` also rejects an icon whose atlas part is `empty`/`empty2`/`c_empty`,
so a present-but-blank icon hides the card too — there is no path to a placeholder.

The difference from vanilla is that vanilla links character portraits and this mod
links three locations. `gameJournalQuestCodexLink` has exactly one field, `path`;
the art belongs to the target `gameJournalCodexEntry` (`linkImageId` for the row
thumbnail, `imageId` for the full entry). Adding a portrait is a content decision,
so it stays with the user rather than being "fixed" here.

**2. The journal list icon is derived from `type`, through two silent switches.**

    SimpleQuestListItemController -> QuestTypeIconUtils.GetIcon(questType)
    QuestsListController.GetDisplayedCategory(gameJournalQuest.type)

`gameJournalQuestType` has ten members. `GetDisplayedCategory` names nine. The
tenth, `VehicleQuest`, falls through to `QuestListItemType.Invalid`, and `GetIcon`'s
own fallthrough returns the atlas part `"invalid"` — the generic `(!)`. A quest
typed that way is a legal enum value, passes `check_enum`, serializes, loads and
works; the only symptom is a broken-looking icon. Vanilla itself ships one ep1
quest typed `VehicleQuest`.

**3. A third icon was being conflated with the second.** The tracked-quest HUD
widget, `QuestItemController.SetQuestData`, ends with

    RequestSetImage(this, m_QuestIcon, "UIIcon." + ToString(GetDistrict()))

— a TweakDBID built by string concatenation from `districtID`. Nothing about the
schema suggests this: `gameJournalQuest` has four fields (`title`, `type`,
`recommendedLevelID`, `districtID`) and none of them is named like an icon.

That one produced the sharpest lesson. **The icon is named for the `gamedataDistrict`
ENUM, and the enum name is not the record name.** `Districts.Akebono.enumName` is
`"Dogtown_Akebono"`; 105 of the game's 132 district records differ from their enum
that way. A first version of this check derived the icon id from the record name
and would have rejected four fifths of the game's districts — caught only by
computing the real mapping instead of assuming it. That mapping is now
`reference/district_icons.txt`, read out of `tweakdb_ep1.bin` flats. Twelve of the
132 have no `UIIcon` at all.

Both traps are build failures now (`check_journal_icon`, `check_district_icon`),
with three negative tests — 87 → 90. One of the three is a positive control that
keeps an empty `districtID` legal, because 16 of the 55 vanilla ep1 quests ship
without one; a check that forbade it would be wrong about the game rather than
strict about the mod.

This quest is `SideQuest` → `minor_quest` and `Districts.Dogtown` → `UIIcon.Dogtown`,
both valid. So **the `(!)` in the screenshot cannot come from the current build**,
and the likeliest explanation is that the screenshot predates those fields. That is
a claim about the game's code, not about the screen, so OI-18 keeps one user step:
take the shot again. If `(!)` survives, the next lead is not which icon was picked
but whether `QuestListItemData` is being fed the quest at all.

## D33 — Two of the three queued voices were already on disk, and one of them is better than what we would have trained   (2026-09-04)

The overnight queue was `mara v_male johnny`, 200 epochs each, about six GPU
hours apiece. The user then pointed at four files an earlier `find` had failed
to turn up:

    /mnt/sata/SoniTranslate/weights/JohnnySilverhand_365e_12410s.pth
    /mnt/sata/SoniTranslate/weights/MaleV-Cyberpunk2077.pth
    /mnt/sata/SoniTranslate/logs/JohnnySilverhand.index
    /mnt/sata/SoniTranslate/logs/added_IVF2918_Flat_nprobe_1_MaleV-Cyberpunk2077_v2.index

**The `find` had not failed to find them. It never finished.** It was
`find /mnt/sata -maxdepth 4 …`, it hit the 120 s timeout, went to the background,
and was killed. `/mnt/sata` is large and slow enough that a full-depth walk of it
is not a lookup, it is a job — and a killed job reports nothing, which reads
exactly like a negative result. Both paths above are three levels down, well
inside `-maxdepth 4`. The same thing happened twice; the rule now is that
anything rooted at `/mnt/sata` gets a specific subdirectory, never the mount.

### What the files actually are

Read out of the checkpoints, not out of the filenames:

|                      | MaleV                    | JohnnySilverhand         |
|----------------------|--------------------------|--------------------------|
| sample rate          | **48000**                | **32000**                |
| version / f0         | v2, pitch-guided         | v2, pitch-guided         |
| embedder             | contentvec, 768-dim      | contentvec, 768-dim      |
| vocoder              | absent → HiFi-GAN        | HiFi-GAN                 |
| epochs               | `info = '600epoch'`      | 365 (12410 steps)        |
| index                | 113805 × 768, IVFFlat    | 87222 × 768, IVFFlat     |
| training data        | ~38 min                  | `'00:28:09'`             |

MaleV is a pre-Applio RVC checkpoint — only `config/f0/info/sr/version`, and its
`sr` is the *string* `'48k'`. That is harmless, and the reason is worth writing
down because it is the kind of thing that gets "fixed" by mistake: Applio never
reads the `sr` key. `setup_network()` takes `tgt_sr = cpt["config"][-1]`, an int,
and `vocoder = cpt.get("vocoder", "HiFi-GAN")` — so an old checkpoint with no
vocoder key gets the right vocoder by default, because HiFi-GAN is what existed
when it was trained. `embedder_model` is likewise not in the checkpoint at all;
it is an argument to the inference call, defaulting to contentvec.

### Verified by conversion, on CPU, on purpose

`questmod-research/verify_downloaded_rvc.py` converts one Rogue clip through both
models. Both produced real audio at the right rate and sane levels
(`rvc_logs/downloaded_check/`, numbers in `reference/rvc_voices.json`).

It ran on CPU deliberately. `rocm-smi` showed 12.3 of 17.2 GB of VRAM held by the
trainer at epoch 70 of 200, and an inference wants roughly 2 GB more. It would
probably have fitted — and if it had not, the process that dies is the four-hour
run, not the check. Applio picks its device in `rvc/configs/config.py` with
`"cuda:0" if torch.cuda.is_available() else "cpu"`, so blanking
`CUDA_VISIBLE_DEVICES` / `HIP_VISIBLE_DEVICES` / `ROCR_VISIBLE_DEVICES` is the
whole switch — but it has to happen **before `import core`**, because `Config` is
a `@singleton` constructed at import time.

That gave an operationally useful number: CPU conversion runs at about 2×
realtime, 11 s for a 5.2 s clip. All 43 spoken lines is on the order of ten
minutes of CPU. **The voice pass never has to wait for the GPU.**

### The decision, and how it was applied without touching a running process

The quest's two scenes are spoken by exactly two actors — Mara 18 lines, V 11
lines — so a Johnny model is dub work, not quest work.

- **`v_male` dropped.** Same sample rate, same architecture, more data, three
  times the epochs. Six GPU hours to produce something behind what already
  exists is not a trade.
- **`johnny` kept.** 32 kHz is a 16 kHz Nyquist ceiling on lines that will sit
  next to full-band 48 kHz vanilla VO, and our dataset is 35 min against 28.
- **`mara` unaffected** — it is the only one with no alternative.

Re-ordering the queue by killing and restarting it was the wrong instinct, and
D31's correction is exactly why it was checked first: `run_one` runs the **index
step after training**, so killing the queue shell mid-`mara` would have finished
the `.pth` and never built the `.index`. Editing the script does not reach the
running shell either — a `mv` replaces the inode and the running bash keeps
reading the old one, which is the same property that makes editing it safe.

The lever that *does* reach a running queue is the dataset check. `run_one`
returns 1 on a missing dataset and the loop is
`run_one "$m" || echo "!! $m did not finish - the queue continues"`, so renaming
`rvc_datasets/v_male` to `v_male.SKIPPED-downloaded-model-is-better` makes the
queue step over it and go straight to johnny, with no signal sent to anything.
One `mv` undoes it. The reason is in `rvc_datasets/README.md`, and it was also
appended to `rvc_logs/v_male.log` so that it appears immediately above the
"no dataset" line it causes.

### What this does not fix

RVC converts audio; it does not synthesise it. There is still no source
recording for any of the 43 lines, so OI-16's gap is unchanged in kind — it has
just moved from "no voice model" to "no source audio". `edge-tts` 7.2.8 and
`gTTS` are installed in the SoniTranslate env, which makes TTS → RVC →
`tools/wav_to_wem.py` a complete path on paper. Both are network services and
neither has been run here, so that is marked UNVERIFIED and nothing was built
on top of it.

## D34 — I orphaned a trainer by editing a running script, and it took nine hours to kill the run   (2026-09-04)

The 200-epoch `mara` run died at ~epoch 118 with
`c10::AcceleratorError: CUDA error: an illegal memory access was encountered`,
raised out of `at::native::item` → `_local_scalar_dense`, and Applio then
cheerfully printed `Model mara trained successfully.` because its index step
runs after training and succeeded. `logs/mara/mara.pth` was never written.

The cause is mine, and it is in `rvc_logs/queue.log` in plain text:

```
=== mara : 626 clip(s) : 2026-09-04 02:19:26 ===
--- train (resumes from the newest checkpoint if there is one)
=== mara done: /mnt/sata/Applio/logs/mara/mara.pth ===
tools/rvc_train.sh: line 128: syntax error near unexpected token `)'
```

That syntax error is an in-place edit of `rvc_train.sh` while a shell was
running it. Bash reads a script lazily, by byte offset; rewriting the file under
a running shell makes it resume at an offset that is now the middle of a
different statement, and it dies. The wrapper died. **Its grandchild did not.**

### Why killing the wrapper does not kill the trainer

`tools/rvc_train.sh` → `core.py train` → `rvc/train/train.py`. The trainer is a
grandchild. When the wrapper dies the trainer is reparented to init and keeps
running, keeps its GPU context, and keeps `fd/1` and `fd/2` open on
`rvc_logs/mara.log`. Pid **1421600**, started 02:38:00, was still alive at
11:46 — **9 h 10 m** — holding **4.87 GB of VRAM**, with `cwd=/mnt/sata/Applio`.

The queue was then started twice more, at 05:16:20 and 05:44:01. Applio's own
bookkeeping recorded the result in `logs/mara/config.json`:

```json
"process_pids": [1421600, 1546772, 1584013]
```

Three trainers registered against one model directory. Applio writes that list
and never checks whether the older entries are still breathing.

### The evidence, in order

**06:31:55** — the allocator gives up, and says who is to blame:

```
HIPCachingAllocator.cpp:3934] memory allocation failed with OOM on device 0
while trying to allocate 1178599424 bytes (free: 0, total: 17163091968)
...
GPU 0 has a total capacity of 15.98 GiB of which 0 bytes is free.
Of the allocated memory 3.36 GiB is allocated by PyTorch, and 2.41 GiB is
reserved by PyTorch but unallocated.
```

Zero bytes free on a 16 GiB card while this PyTorch holds 5.77 GiB. PyTorch is
explicitly telling us that ~10 GiB belongs to somebody else. The 1.10 GiB
allocation that fails is `net_g.infer(*reference)` in `train_and_evaluate` —
the once-per-epoch reference render, a single large request that cannot be
satisfied out of fragments.

**11:30:44** — the kernel, via `dmesg`:

```
amdgpu 0000:0a:00.0: [gfxhub] page fault (src_id:0 ring:24 vmid:8 pasid:1022)
  Process python pid 1584013 thread python pid 1584013
  in page starting at address 0x00007f3b411a7000 from client 0x1b (UTCL2)
  GCVM_L2_PROTECTION_FAULT_STATUS:0x00801030
     Faulty UTCL2 client ID: TCP (0x8)
     MORE_FAULTS: 0x0   WALKER_ERROR: 0x0
     PERMISSION_FAULTS: 0x3   MAPPING_ERROR: 0x0   RW: 0x0
```

This is worth reading field by field, because it says something specific.
`WALKER_ERROR: 0x0` and `MAPPING_ERROR: 0x0` mean the page-table walk
**succeeded** — the address was mapped. `RW: 0x0` means it was a read.
`TCP` is the per-CU vector L1 cache, so the read came from a shader, not from a
copy engine. So: a shader read a mapped page it was not permitted to read.
That is not a wild pointer into nothing. It is the signature of a virtual
address whose backing was handed back to the driver while something still held
a descriptor to it.

`pasid:1022`, `pid 1584013` — the third trainer, the one the queue was actually
supervising. The orphan did not fault; it just sat there taking the memory.

### What is proven and what is inferred

Proven: three trainers ran concurrently; the orphan held 4.87 GB for nine
hours; the allocator reached `free: 0` with 10 GiB held by other processes; the
supervised trainer took a permission fault on a mapped page.

Inferred: that the OOM path is the *mechanism* joining the two. Under
`free: 0` the caching allocator's fallback is to release cached segments back
to the driver and retry, which unmaps VAs; a kernel still referencing one of
those VAs produces exactly the fault above. That chain is consistent with every
field in the fault status and with the timeline, but it was not observed
directly, so it is recorded as the best explanation rather than as fact.

### The run was salvaged, not lost

`--save-every-epoch 10` had already written
`logs/mara/mara_110e_14410s.pth`. That is not a resume-state file — it is the
same small inference checkpoint as the final `<model>.pth`, and literally the
same format as the downloaded `JohnnySilverhand_365e_12410s.pth`. And
`mara.index` is built by `core.py`'s post-train step from
`logs/<model>/extracted/*.npy` features, so it is independent of the weights
and a training crash cannot spoil it.

Both were copied to `/mnt/sata/Cyberpunk2077/rvc_voices/`, out of Applio's
volatile log tree, and then *proved* rather than assumed — `verify_mara_salvage.py`
loads the checkpoint and converts two clips with
`CUDA_VISIBLE_DEVICES`/`HIP_VISIBLE_DEVICES`/`ROCR_VISIBLE_DEVICES` blanked and
`assert not torch.cuda.is_available()`, so the live `johnny` run was never at
risk.

| | |
|---|---|
| epoch / step | 110 of 200 / 14410 |
| sample rate | 48000 (`cpt["config"][-1]`) |
| version / f0 / vocoder | v2 / true / HiFi-GAN |
| index | IndexIVFFlat, d=768, ntotal=105574 |
| conversion | 5.24 s out, 13.8 s CPU — in-domain and cross-voice both fine |

### `volume_envelope=1.0` does not mean "match the source"

The salvaged model came out at **−5.1 dBFS** from a **−21.6 dBFS** source, and
produced the same level from two inputs 5 dB apart. Level-invariant output is
what a generator that has not yet learned dynamics sounds like. But the setting
was also wrong. `rvc/infer/pipeline.py:545`:

```python
if volume_envelope != 1:
    audio_opt = change_rms(audio, self.sample_rate, audio_opt, self.tgt_sr, volume_envelope)
```

`1.0` is the sentinel for **do not touch** — it skips RMS matching entirely.
`0.0` fully matches the source envelope. Measured:

| volume_envelope | output |
|---|---|
| 1.0 (no correction) | −5.1 dBFS |
| 0.25 | −18.3 dBFS |
| **0.0** | **−22.4 dBFS**, 0.8 dB from the source |

**Settled: `volume_envelope=0.0` for mara.** It makes the line's level come from
the performance rather than from the model, which is what we want when these
sit next to vanilla VO.

> **Corrected by D36 (2026-09-04).** This is wrong, and the table above is worse
> than wrong: it is circular. `change_rms` rescales the output until its RMS
> matches the source's, so a level table measured after it can only ever report
> agreement. `0.0` was not preserving dynamics here — it was hiding a generator
> that emitted full-scale noise. Use `1.0` (leave the model's own output alone)
> and judge level separately. See D36.

### The class of bug is closed in the tool

`tools/rvc_train.sh` gained four functions and a three-way exit status. The
queue-wide `flock` was never the gap — it stops two *queue shells*, and a
trainer that outlives its shell holds no lock. So before training a model the
script now reads that model's `config.json` and reaps anything still alive:

- `is_descendant` walks `/proc/<pid>/status` up to init. Anything started by
  *this* queue is our own work and is never touched. `status` is used rather
  than `stat` because a `comm` containing a space shifts every field in `stat`.
- `looks_like_trainer` is the guard that matters for safety. A pid in
  `config.json` can be days old and Linux recycles pids, so `kill -0` proves
  only that *some* process holds that number. Before killing, the pid must also
  have `cwd == $APPLIO`, a trainer entry point in argv, and this model's name.
  Unreadable `/proc` — a different uid — fails closed.
- `kill_tree` kills children before parents: SIGTERMing a dataloader's parent
  leaves four `pt_data_worker`s behind, and those are what hold the GPU queues.
- The `multiprocessing.resource_tracker` is a *sibling* of the trainer, so
  `kill_tree` never reaches it. It is swept separately, and only when its ppid
  is 1 and its cwd is Applio's — a tracker that still has a parent belongs to
  somebody's live run.

And a partial run is now a result. `run_one` returns **2** for
"stopped early but left a usable checkpoint", builds the index for it anyway,
and names the file:

```
!! mara: training stopped before the end - mara.pth was never written.
   Newest usable checkpoint: .../mara_110e_14410s.pth
```

The candidate was built on a copy, `bash -n`-checked, exercised against a real
orphan tree plus a decoy with the wrong cwd, and installed with `mv` — never an
in-place edit, because the queue shell 1581375 is still running. `readlink
/proc/1581375/fd/255` reports the old inode as `(deleted)`, which is the proof
that worked.

### What this does not fix

Nothing about the source-audio gap. And `mara` is at 110 of 200 epochs: the
queue resumes from the newest checkpoint, so re-queueing it after `johnny`
finishes costs only the remaining 90 epochs. Whether that is worth it is a
listening decision, not a technical one.

## D35 — The last unverified link in the voice chain now runs end to end   (2026-09-04)

> **Partly retracted by D36 (2026-09-04).** The *chain* result stands: edge-tts
> runs, the `.wem` round trip is sample-identical, `uk-UA` voices synthesise.
> The *model* result does not. The mara checkpoint used below emits noise, and
> the level table used to verify it was measured downstream of the normaliser
> that guaranteed the result. Read the numbers here as evidence about the
> pipeline only, never about mara.

D33 left `edge-tts` marked UNVERIFIED: installed, plausible, never executed,
and nothing built on top of it. That was the right call at the time and it is
now closed. `questmod-research/verify_tts_chain.sh` runs the whole pipeline:

```
edge-tts (network)  ->  ffmpeg 48k mono s16  ->  RVC/mara on CPU  ->  wav_to_wem.py  ->  vgmstream
```

**The text sent to Microsoft was a pangram and a counting phrase.** None of the
quest's 43 lines left this machine. This tests plumbing, not content — the
lines themselves are the user's to release, and the point of a chain test is
that it works regardless of what goes through it.

### What came back

| stage | en-US-JennyNeural | uk-UA-PolinaNeural |
|---|---|---|
| TTS → 48 kHz mono | 6.58 s, −22.3 dBFS | 4.54 s, −22.9 dBFS |
| RVC → mara, `volume_envelope=0.0` | 6.56 s, −23.3 dBFS, 12.0 s CPU | 4.52 s, −24.2 dBFS, 7.4 s CPU |
| `wav_to_wem.py` | 629,856 B, 1ch 48000 PCM | 434,016 B, 1ch 48000 PCM |
| `vgmstream-cli` read-back | 314,880 samples, 16-bit LE PCM | 216,960 samples, 16-bit LE PCM |
| samples identical to RVC output | **yes** | **yes** |

Three things worth keeping.

**The `.wem` is lossless, not merely readable.** Step 7 compares the int16
samples before and after the container round trip and gets exact equality,
314,880 for 314,880. So if a line sounds wrong in game, the encoder is not a
suspect — that whole branch of the search tree is cut.

~~**`volume_envelope=0.0` holds on real material.** D34 settled it on one clip;
here it tracks two different sources to within 1.0 and 1.3 dB.~~ **Retracted by
D36.** Tracking to within 1 dB was not a finding, it was arithmetic: `change_rms`
sets the output RMS from the input RMS, so the two agreeing is the definition of
the setting, not evidence about the audio. The underlying output was railed noise.

**ua-ua has a source.** `uk-UA-PolinaNeural` and `uk-UA-OstapNeural` both
synthesise. Rule 7 says ua-ua is a real translation and not an en-us alias, and
until now that had no path to audio at all; it does now, through the same
pipeline, with no extra tooling.

CPU cost is ~1.8× realtime, so all 43 lines is well under ten minutes and never
needs the GPU — a training run and a voice pass can happen at the same time.

### What is still not verified

Two things, and they are different in kind.

1. **PCM on the voiceover path in game.** Unchanged from OI-16 — all 243 known
   PCM `.wem` files, vanilla and modded, are bank media, and no shipped example
   proves PCM through `locVoiceoverMap`'s external-source path. Only the game
   can answer that.
2. **Whether TTS-through-RVC is good enough to ship.** That is a listening
   judgement and nobody has listened yet. It is also not one question but two:
   Mara's 18 lines have no vanilla counterpart to be compared against, while
   V's 11 lines will play next to thousands of lines of real V performance in
   the same session. The second is a much harsher test than the first, and it
   may be that Mara passes and V does not. Worth deciding before generating 43
   lines, not after.

## D36 — The mara model was emitting noise, and my verification could not have caught it   (2026-09-04)

The report, verbatim: *"The sound is very bad, like some kind of sound eruptions.
The voice is not clearly audible, like some sound artifacts. There is a lot of
noise in the voice. ... In short, there is more noise than a clear voice."*

That is an accurate description of the measurement. `mara_110e_14410s.pth` — the
checkpoint D34 salvaged and D35 used, the one this file recorded as **"SALVAGED
FROM A CRASHED RUN, VERIFIED, USABLE"** — produces full-scale broadband noise.

### What the numbers say

Every run below uses the same code path, the same source clip and CPU inference.
`gap dB` is the level during the frames the *source* calls silence — a generator
that hallucinates noise fills the pauses between words; a good one leaves them
alone.

| model | clip% | p95 | gap dB | HF>8k |
|---|---|---|---|---|
| source (edge-tts) | 0.00% | −16.0 | −222.0 | 1.77% |
| **mara 110e, `volume_envelope=1.0`** | **100%** | **−0.1** | **−0.1** | 0.40% |
| mara 110e, `volume_envelope=0.0` (what shipped) | 0.00% | −17.3 | −60.1 | 1.27% |
| control: JohnnySilverhand 365e (downloaded) | 0.00% | −13.1 | −76.7 | 0.92% |
| control: MaleV (downloaded) | 0.00% | −13.9 | −95.8 | 0.75% |

Both controls run clean through the identical pipeline, so the encoder, the
container, the embedder and the settings are all exonerated. The fault is the
checkpoint.

### The verification was a tautology

Look at the two mara rows. At `volume_envelope=1.0` the output is railed at digital
full scale end to end. At `0.0` it looks *reasonable* — because `change_rms` rescales
the output until its RMS matches the source's.

D35 verified the chain with a **level table**: overall RMS at each stage. Overall RMS
is precisely the one statistic `change_rms` forces to agree. The check could not have
failed no matter how bad the audio was. It measured its own input.

This is the lesson worth keeping, and it is not really about audio: **a measurement
taken downstream of a normaliser measures the normaliser.** D34's `volume_envelope`
table has the same defect and is annotated accordingly.

### The model was broken before it sounded broken

Rendering every saved epoch against **mara's own training material** — audio the model
had already seen, which it must be able to reconstruct — locates the collapse:

| epoch | clip% | gap dB | HF>8k | |
|---|---|---|---|---|
| 20 | 0.01% | −73.5 | 1.12% | ok |
| 30 | 0.00% | −76.8 | 2.59% | ok |
| 40 | 0.38% | −66.9 | 3.46% | degrading |
| 50 | **100%** | **−0.1** | 0.00% | railed |
| 110 | 48.11% | −0.1 | 0.19% | railed |

Epoch 40 → 50 is 08:01:27 → 08:29:54, inside the run that shared the GPU with two
orphaned trainers. But the energy above 8 kHz was already climbing at epoch 20,
tripling by epoch 40 while the audio still sounded acceptable. **The rot preceded
the audible failure by 20+ epochs**, which is why no early checkpoint is a safe base
to resume from and the retrain starts from the pretrained models.

A model that cannot reconstruct its own training data is not undertrained. It is broken.

### Why it collapsed — and one theory killed on the spot

The training log says `Using Float16 for training.` (Applio's default,
`assets/config.json: "precision": "fp16"`), and mara's `lowest_value` never improved
after epoch 6 across 50 epochs. That looked conclusive.

It was wrong, and the live johnny run refuted it within minutes: johnny trains under
the **same fp16 default** and its `lowest_value` is **also** frozen (44.65 at epoch 16,
unchanged through 30) — and johnny is perfectly healthy at epochs 10/20/30, with its
HF share trending *down* (4.92 → 4.50 → 4.14%) where mara's trended up. So Applio's
overtrain counter plateaus as a matter of course and is not a health signal, and fp16
is not the cause.

The variable that does separate them is GPU state: mara trained 05:44→11:17 sharing
the card with two orphans, through an OOM and into a page fault (D34); johnny has the
card to itself. **That is the leading explanation, on a live control of n=1 per arm
with different datasets — not proof.** The retrain on a clean GPU is the test.

### What changed

**`tools/rvc_check_model.py`** — new. Renders a checkpoint against the model's own
training slices and measures clipping, the level in the source's silent frames, and
the share of energy above 8 kHz. Exits non-zero if a model is broken. It passes both
downloaded models and the live johnny checkpoints, and fails mara 110e. Thresholds are
deliberately loose: healthy models clear them by an order of magnitude and the broken
one misses by the same, so there is no grey zone to tune.

**`tools/rvc_train.sh`** — the queue now runs that check before calling any model done,
and returns 3 with "the result is NOISE - do not ship it" if it fails. A `.pth` existing
is no longer treated as evidence that training worked.

**`--wait`** — new, so a retrain can be queued behind a run with hours left.

**The broken files are quarantined** in `rvc_voices/BROKEN/` with a `WHY.md` holding the
tables, rather than deleted — D34 and this entry both cite them. `Applio/logs/mara` is
archived as `mara.railed-2026-09-04`. The 626-file dataset was never touched.

### The `--wait` bug, for the record

The first `--wait` waited on the queue's `flock`. It returned in the same second and
started mara's preprocess **while johnny was training** — recreating the exact fault
this entry is about. Cause: the running queue was started from a build of the script
that predates the flock, so it held no lock at all; `/proc/1581375/fd/9` did not exist,
and an uncontended lock is indistinguishable from a free one. Killed the process group
within three minutes, removed the partial `logs/mara`, johnny unharmed.

The fix is the same lesson as the reaper in D34: **the guard was one level away from the
hazard.** `flock` guards queue shells; the invariant that matters is one trainer on the
GPU. `--wait` now polls for a live `rvc/train/train.py` and only then takes the lock,
which additionally covers a hand-run `core.py`, the Applio web UI, and any older copy of
this script. Verified against the live johnny run: it waits and starts nothing.

### What is proven and what is inferred

**Proven by measurement here:** mara 110e emits full-scale noise; it fails on its own
training material; both downloaded models pass the same path; the collapse is between
epoch 40 and 50; HF energy was rising from epoch 20; `volume_envelope=0.0` masks the
defect; D35's level table could not have detected it; johnny is currently healthy.

**Inferred:** that GPU contention caused the collapse. Consistent with every timestamp
and with johnny as a live control, but not proven.

**Unchanged and still true:** the `.wem` round trip is sample-identical, `uk-UA` voices
synthesise, and none of the quest's 43 lines have been sent to any network service.
D35's *chain* result stands; its *model* result does not.

## D37 — Measure the model while it trains, not after   (2026-09-04)

D36 added a health gate to the end of `tools/rvc_train.sh`. That closes the
"shipped a noise generator" hole but not the one next to it: mara railed between
epoch 40 and 50 and then trained for **sixty more epochs**. An end-of-run gate
would have caught it at 08:29 the next morning, after the GPU had already been
spent. The signal was available at 08:01.

So `tools/rvc_watch_health.py` renders every checkpoint as it lands, against the
model's own training slices, and appends a row to `rvc_logs/<model>.health.tsv`.
`rvc_train.sh` starts one automatically before each `core.py train`.

It shouts in two situations:

- **BROKEN** — the checkpoint fails the absolute gate (clipping, or noise filling
  the frames the source calls silence). This is the failure that already happened.
- **ROT** — three consecutive checkpoints with a strictly rising share of energy
  above 8 kHz.

The second one is the whole point, and its design has one non-obvious property:
**there is no absolute HF threshold, because an absolute threshold cannot work.**

| model  | HF share over three checkpoints | healthy? |
|--------|---------------------------------|----------|
| mara   | 1.12 → 2.59 → 3.46 %            | no — railed 10 epochs later |
| johnny | 4.92 → 4.50 → 4.14 %            | yes |

Johnny's healthy HF share is **four times** mara's at the moment mara was dying.
Any level-based limit either fires on johnny or misses mara. Only the direction
separates them. So the rule is a ratio over three points, with two triggers: a
1.5x climb that has reached 2%, or a 2.5x climb from any base above 0.75%. The
second exists because a steep climb from a low base would otherwise not fire for
another ten epochs — and ten epochs was mara's entire remaining margin.

Both triggers and the six quiet cases are unit-tested against the two real
series before the watcher is trusted with a six-hour run.

Cost, measured: one checkpoint renders in **33 s** on two nice'd CPU threads,
against a checkpoint every ~19 min. It blanks `CUDA_VISIBLE_DEVICES`,
`HIP_VISIBLE_DEVICES` and `ROCR_VISIBLE_DEVICES` and refuses to start if the GPU
is still visible, so it cannot become the second job on the card — the fault that
destroyed mara in the first place, and the one my own first `--wait` recreated.

`trainer_alive()` reads `/proc/*/cmdline` and matches the model name as an exact
argv element rather than shelling out to `pgrep`, so the watcher's own command
line — which contains the model name — can never match itself. `--until-idle`
only arms once a trainer has actually been seen, so a watcher can be launched
while its model is still queued behind another.

Also added: `tools/rvc_status.sh`, one screenful of state. Applio interleaves its
per-epoch summary with tqdm's carriage-return progress bar in the same stream, so
a plain `tail` of a training log returns kilobytes of block characters per useful
line; everything in the status script filters on `| epoch=`.

## D38 — A line with a recording is not a line with a guess   (2026-09-04)

OI-8 timed every subtitle at 55 ms per character of the longest locale, because
D2 said there was no VO to time against. The RVC pipeline exists to end that, so
the formula now applies only where it is still true:

    "ms" on the line   ->  wins, always
    audio in vo/       ->  measured length + 250 ms tail
    neither            ->  55 ms/char, floor 1200 ms

Read straight off the RIFF header, no decoding and no dependencies. That covers
both formats this pipeline produces - the `.wav` RVC emits and the PCM `.wem`
`wav_to_wem.py` wraps around it, since a `.wem` **is** a RIFF, which is the whole
basis of the no-Wwise route. A 4.000 s test file measures 4000 ms through either.

With `vo/` empty the generated scenes are byte-identical, which is the property
that made this safe to land while the voices are still training.

**Three silent failures, one of which I wrote and caught in the same hour.**

1. The drop folder names files by the full subtitle key, `mara.mara_open_1`,
   while `line["id"]` inside the generator is the bare `mara_open_1`. My first
   version looked up the bare id. It matched nothing, raised nothing, and would
   have left every voiced line on its guess forever. `read_time` now takes the
   key as a **required** argument instead of deriving it, so the wrong one cannot
   be passed quietly. This is the same shape as D34's reaper and D36's `flock`:
   a guard positioned one level away from the thing it guards.

2. A Vorbis or Opus `.wem` is audio this reader cannot measure. Silently, that
   line keeps its guess while holding a recording of a different length. The
   build now names those lines.

3. An `"ms"` override and a recording are each legitimate alone. Together the
   override wins - that is what an override is for - so an `"ms"` set while a
   line was unvoiced silently truncates the voice dropped in later.
   `check_line_timing` in `validate.py` errors on the too-short direction only;
   erring long costs a beat of silence, erring short eats a spoken word.
   negtest covers both directions: 92/92.

**Not resolved:** whether `duration` governs display time at all when there is no
audio, and what the engine does with a `sectionDuration` shorter than its own
last line. Only the game can answer those, and they now matter only for the
unvoiced case.

## D39 — The privacy question about the voice lines was avoidable   (2026-09-04)

I had been treating "send the quest's 43 lines to a TTS service" as a decision
waiting on the user, and holding the pipeline there. That framing was wrong in a
useful way: it assumed the TTS stage had to be a network service, because the
chain verified in D35 used `edge-tts`.

It does not. `espeak-ng` is installed and speaks both `uk` and `en-us`, and
piper's catalogue - already on disk at `SoniTranslate/PIPER_MODELS/voices.json` -
lists `uk_UA-ukrainian_tts-medium` alongside a dozen high-quality `en_US` voices.

`tools/render_lines.py` runs the whole chain with the backend pluggable, and
`--tts edge` **exits rather than run** without `--allow-network`. The constraint
now lives in the tool instead of in my memory of it, which is the only place a
constraint survives being handed to someone else.

**Proven on real content, locally:** V's 11 English lines through
espeak -> MaleV -> PCM `.wem` in 1:48, plus one Ukrainian line. All 11 measure
inside the health gate - 0.00% clipping, gaps -87 to -240 dB, HF 0.29-1.76%.
They went to `rvc_logs/audition/`, not `vo/`: `--out` exists so a backend can be
auditioned without its output quietly becoming the shipped voice. Whether
espeak's delivery is *good* is a listening judgement and stays with the user.

**Two bugs found by running it, both in code written earlier today.**

- `render_lines.py` needs Applio's python for torch, and failed at `import torch`
  a full TTS pass into the job. It now re-execs itself under `APPLIO_PY`, because
  thirty seconds into a batch is a bad place to learn about an interpreter.
- **The health gate had a false-alarm bug**, which matters more: `measure()` took
  the noise floor as `db < np.percentile(db, 25)`. On a short clip whose frame
  levels tie, that strict comparison selects *nothing*, the mean of an empty
  slice is NaN, and `NaN <= SIL_MAX` is False - so a clean 2-second line was
  reported BROKEN. It now takes the quiet quarter **by rank**, which cannot
  return an empty set. The four known models measure exactly as before
  (-57.5/-57.7/-57.7/-57.7/-57.8), so the fix moved no established number.
  It failed safe - a false alarm, never a false pass - but a gate that cries
  wolf is a gate people stop reading.

**One measurement worth keeping:** the same line runs 7.80 s in Ukrainian against
5.28 s in English, 48% longer. D38 times subtitles off the longest locale; this
is the number behind that choice.

## D40 — "Clear, but a robot" is a TTS problem, and RVC cannot fix it   (2026-09-04)

The first local render went to the user, who listened and said: *the voice is clear,
but it sounds like a robot.* That is not a complaint about the voice conversion. It
is the correct diagnosis.

RVC converts **timbre**. It maps the spectral envelope onto the target speaker and
shifts F0 to the target's range. It does not touch rhythm, stress placement, or the
shape of the pitch contour — those come from the source recording and pass through
essentially unaltered. espeak-ng is a formant synthesiser: uniform phoneme durations,
a near-monotone contour, no phrase-level prosody at all. Feed that to RVC and you get
a robot with V's larynx. No inference setting reaches this. `protect`, `index_rate`,
`f0_method` and the rest all operate downstream of a delivery that was already flat.

So the fix is upstream, and the only lever upstream is which TTS produces the source.

### What was actually on this machine

D39 recorded that piper's catalogue was on disk and treated that as "piper is ready".
It was not. `/mnt/sata/SoniTranslate/PIPER_MODELS/` held **`voices.json` and nothing
else** — the 151-entry index of downloadable voices, no `.onnx` and no binary. The
only local TTS installed was espeak-ng. The correction matters because D39's claim
made piper sound like a flag away, and it was a 311 MB download away.

Installed into `/mnt/sata/Cyberpunk2077/tts_venv`, deliberately **not** into the
Applio environment: Applio is mid-training with a second run queued behind it, and
pip resolving a dependency could move torch under a job with hours invested in it.
The venv costs nothing and removes the whole class of accident.

Downloaded into `/mnt/sata/Cyberpunk2077/tts_models`:

| voice | role | size |
|---|---|---|
| `en_US-ryan-high` | male source, V | 121 MB |
| `en_US-lessac-high` | female source, Mara | 114 MB |
| `uk_UA-ukrainian_tts-medium` | both, 3 speakers | 77 MB |

This is network traffic, and it is a different kind from D39's. A model download
sends a filename. `edge-tts` sends the script. The `--allow-network` gate stays
exactly where it is.

`TTS_VOICE` gained a gender dimension for the same reason RVC has a pitch parameter:
the conversion shifts F0 further, and less convincingly, the bigger the gap. Mara
starts from a female read. The Ukrainian model is multi-speaker, so the voice string
carries the speaker after a `#` — `uk_UA-ukrainian_tts-medium#mykyta` for V,
`#tetiana` for Mara — resolved through the model's own `speaker_id_map` rather than a
hardcoded index.

### Three silent failures found by running it

**1. Uppercase Cyrillic was being deleted.** The first Ukrainian smoke test logged
`Missing phoneme from id map: Х`. The Ukrainian model is `phoneme_type: "text"` —
unlike the English models there is no espeak stage, characters go straight into the
id map, and its alphabet is **lowercase only**. Anything absent is dropped with a log
line and the rest is synthesised as if the sentence were complete. The real script
contains 22 distinct uppercase Ukrainian letters: every sentence-initial capital and
every proper noun would have vanished, fluently. `piper_text()` now lowercases for
text models, substitutes the punctuation no alphabet contains (`«` `»` `…`), and
raises naming any character it still cannot say rather than letting piper drop it.

**2. `render_lines.py` was rendering 29 of 43 lines.** `alloc_subtitle_ids.py`,
`gen_subtitles.py`, `validate.py`, `negtest.py` and `gen_scene.py` all walk
`nodes[].lines` **and** `nodes[].options` — that is where the project's count of 43
comes from. `render_lines.py`, written yesterday, read only `lines`. It would have
rendered 29 files and reported success. The 14 missing are choice options, and here
an option is not a wheel paraphrase with a spoken line behind it: the option text IS
V's line ("Then start talking. What's in the box?") and no other node carries it.
Whether the engine ever plays a choice option's audio is a separate and genuinely
open question — see OI-20 — but the renderer's job is to match what the other five
tools already allocate.

**3. Ukrainian was being synthesised with the wrong stress.** Ukrainian stress is
phonemic and not predictable from spelling, and this model was trained on stressed
text — its id map carries U+0301 COMBINING ACUTE. Unstressed input does not fail; it
stresses the wrong syllable, fluently. Proven rather than assumed: the same sentence
renders 2.496 s unstressed and 2.659 s stressed, so the mark reaches the model.
`ukrainian-word-stress` now runs over the batch in one subprocess in the venv
(loading its dictionary costs seconds, so once per run, not once per line), and a
missing package downgrades to unstressed with a loud warning rather than aborting.
Homographs stay a human's job: the stresser picks by part of speech and will still
choose `ні́чого` where `нічо́го` was meant. Both are real words.

### The health gate was measuring the wrong thing, again

D39 reported the espeak audition as "all 11 inside the health gate". That number was
wrong. It came from calling `measure(path)` with no source, which makes the function
compare a file against **itself** — its own quietest quarter. What it was reporting
was espeak's digitally silent padding, at -240 dB, not the health of the render.

Called correctly, with the source's frame levels, 22 of 25 English piper renders
"failed" the -40 dB gap threshold. They are not broken. The threshold assumes the
source contains silence, and a short choice line — *"What's your cut in this?"* —
contains none: its quietest quarter is ordinary consonants around -30 dB. The
statistic was measuring the TTS backend, not the model.

The measurement that survives is the **difference**. In the source's quiet frames,
how much louder is the output than the source was:

| | source quiet quarter | output there | delta |
|---|---|---|---|
| `dec_open_1`, piper en | -37.5 dB | -38.2 dB | **-1.1** |
| `dec_openh_2`, piper en | -35.3 dB | -38.2 dB | **-2.9** |
| `opt_destroy`, piper en | -29.1 dB | -32.4 dB | **-3.3** |
| railed mara (D36) | ~-60 dB | -0.1 dB | **~+60** |

RVC was *quieter* than its source in three of four. The two populations are separated
by sixty decibels, so the threshold is not delicate: `DELTA_MAX = +6.0`.

`measure()` now returns `sil_src` and `sil_delta` alongside `sil` — additive, so
`rvc_watch_health.py` and its live TSV are untouched, and its absolute threshold
stays correct for its own job, where the source is the model's training material and
does have real silence (johnny at epoch 70 measures a -57.8 dB gap). The new
`tools/rvc_audition.py` is the tool for the other job, and it says out loud how many
lines had any silence to judge, because a clean verdict on a statistic that had
nothing to measure is not a clean verdict.

**Result:** 50 lines (V, both locales), `clip 0.00%`, `hf 0.13-1.96%`, gap
`-35.2..+5.8 dB` against a `+6.0` limit. All 50 clean. 0 of 25 English lines contain
silence at all, which is stated in the output rather than hidden by it.

### What is still not decided here

Whether piper's delivery is good enough to ship. That is the same listening
judgement as before, now with a better candidate in
`/mnt/sata/Cyberpunk2077/rvc_logs/audition_piper/`. Nothing has been copied into
`vo/`. If piper is still not enough, the remaining lever is not another synthesiser:
it is a human reading the lines, which is the input RVC was designed for.

---

## D41 — The Ukrainian accent comes from the voice TARGET, not the synthesiser
*2026-09-04. Supersedes the "swap the TTS" half of D40 for ua-ua only.*

The verdict on the piper audition was split by language:

> "This sounds better than espeak-ng. It's less like a robot, but there's still a
> difference regarding the Ukrainian audio. As a native speaker, the Ukrainian
> text sounds awful. A short text sounds like English. A longer text or longer
> audio has Ukrainian, but it's broken with the use of English. It's like
> teaching a foreigner to speak Ukrainian."

English: acceptable. Ukrainian: a foreigner reading phonetically. D40 assumed one
knob — the synthesiser — and one direction to turn it. That was half right.

### The part D40 got right: piper's Ukrainian model was a bad choice on its own

`uk_UA-ukrainian_tts-medium` is `phoneme_type: "text"`. There is no phonemiser in
front of it: characters go straight into `phoneme_id_map`. A model like that can
only pronounce spellings it saw in training, and it has no way to be told that
`нічого` is two different words. Every other Ukrainian TTS worth using runs
**stress → IPA → tokens**, which is a model that can say a word it has never seen.
That difference is not a tuning parameter, it is a different front end.

### The part D40 missed: the accent is not in the synthesiser at all

RVC learns its phonetics from the target's recordings. `male_v` and `johnny` are
trained on Cyberpunk 2077 English VO and nothing else — the content encoder
(ContentVec) is English, the decoder has heard English and only English. Feeding
Ukrainian through it does not produce Ukrainian in V's voice; it produces the
nearest thing to Ukrainian that an English speaker's vocal apparatus was recorded
making. That is exactly what "like teaching a foreigner to speak Ukrainian"
describes, and no `protect`, `index_rate` or `f0_method` reaches it, because none
of them is a phonetic inventory.

This is not a theory about our pipeline. It is a measurement somebody else already
published, in the `Синтез мовлення` Telegram channel, testing FireRedTTS3 — a
cloning TTS, so the same question with the RVC step removed:

| reference speaker | synthesised Ukrainian | tester's verdict |
|---|---|---|
| Japanese | clean | "Схоже, що немає іноземного акценту" |
| Ukrainian | clean | "жодних проблем немає" |
| native English | **accented** | "Акцент також зберігається" |

Two out of three references produce clean Ukrainian and the English one does not,
which locates the accent in the *reference*, not in the model. Our RVC target is
an English voice actor. The conclusion transfers.

The corollary is the useful part: **there is no version of this pipeline where
English-only V speaks unaccented Ukrainian.** The only inputs that would fix it
are Ukrainian recordings of the target, and there are none — the game ships one
voice language (see OI-21).

### What replaces it, for ua-ua only

`StyleTTS2-Ukrainian` by Serhiy Stetskovych (`patriotyk`), which is what the
Ukrainian speech community actually uses — 80 mentions across the two channels
against piper's 11 — MIT licensed, and entirely local. Its pipeline is the one
described above:

    text → normalise → stressify → ipa() → tokenizer.encode → model → 24 kHz

Two checkpoints: `styletts2_ukrainian_single` (one voice, Filatov) and
`styletts2_ukrainian_multispeaker` (31 voices). Installed at
`/mnt/sata/Cyberpunk2077/styletts_venv` — a third venv, and CPU-only torch on
purpose, so `torch.cuda.is_available()` is False and it cannot contend with a
trainer no matter what it is asked to do. The reference app is cloned to
`/mnt/sata/styletts2-ukrainian` for its 31 style vectors and for the exact
preprocessing, which is copied rather than reinvented: deviating from it changes
the voice.

`--tts styletts2` deliberately has **no en-us entry**. Asking a Ukrainian model
for English gets Ukrainian phonetics wrapped around English words — the same
mistake in the other direction.

### And the RVC step is removed for ua-ua

`render_lines.py --no-rvc` ships the TTS voice as-is. This is what every dub does:
the Ukrainian V is a Ukrainian actor, not the English actor doing an impression.
Nobody expects a localised voice to match the original timbre, and the alternative
is not "V's voice in Ukrainian" — it is "V's voice failing at Ukrainian".

So the pipeline is now split by language, not uniform:

| locale | TTS | RVC | why |
|---|---|---|---|
| en-us | piper `ryan-high` / `lessac-high` | yes, `male_v` / `mara` | the target speaks this language |
| ua-ua | StyleTTS2 multispeaker | **no** | the target does not, and cannot be made to |

Which of the 31 voices plays V and which plays Mara is not decided here. Both
entries in `TTS_VOICE["styletts2"]["ua-ua"]` are `None`, and `tts_voice()` raises
naming `rvc_logs/styletts_voices/` rather than defaulting to something. Guessing a
voice from a name is not choosing a voice, and every one of the 31 is a real
person whose sound cannot be read off their spelling.

### Homographs are still a human's job

Automatic stress resolves by part of speech and will still pick `ні́чого` where
`нічо́го` was meant. StyleTTS2 takes `+` after a stressed vowel as a manual
override, and the fix belongs in `source/scene_*.json`, where it is reviewable,
not in the renderer. The channel's own summary of the state of the art:
"біда всіх українських tts наголоси, хоча таке ж саме і у Елевенлабс".

---

## D42 — Ukrainian ships as text, and the voice is English

**2026-09-04.** Owner's call, after listening to the StyleTTS2 and piper renders:

> "i'm already used to the English voiceover, so it's not a problem for me to
> listen to English, and English sounds better on the training data, so
> Ukrainian is not necessary."

This settles D40 and D41, and it retires OI-21 without needing the in-game test
that issue was waiting on.

**What changes.** `ua-ua` keeps everything it had except audio. Subtitles,
onscreens, journal entries, item names, shard bodies and codex links are all
still real Ukrainian, still authored in `source/scene_*.json` and
`source/lockeys.json`, still validated line for line. Rule 7 is untouched: the
player is Ukrainian and reads Ukrainian. They just hear the English take while
reading it — which is what vanilla Cyberpunk does for them today, because CDPR
shipped `lang_ua_text.archive` and never shipped a Ukrainian voice.

So the mod's Ukrainian player gets exactly the presentation they already know,
and nothing in the quest reads as a downgrade from the base game.

**Why this is the right answer and not a concession.** Three independent
findings all point the same way, and any one of them alone would be enough:

1. **The engine may not even offer the slot.** ArchiveXL's `OnLoadVoiceOvers`
   merges into voice languages the game already has; there is no
   `lang_ua_voice.archive` in either `content/` or `ep1/`, and an unmatched
   locale key fails silently (OI-21).
2. **The RVC targets cannot say Ukrainian.** `male_v`, `johnny` and `mara` learn
   phonetics from English-only Cyberpunk VO through an English content encoder.
   Ukrainian pushed through them comes out as the nearest sounds an English
   actor was recorded making — the owner's "like teaching a foreigner to speak
   Ukrainian" (D41).
3. **Dropping RVC to fix that costs the character.** A clean Ukrainian voice
   from StyleTTS2 is a *different person* — some Ukrainian actor, not V and not
   Mara. Trading V's voice for correct phonetics is a real trade, and the owner
   made it in the other direction.

**Encoded in the tools, not just written down here.** The text locale set and
the voice locale set were the same list copied into four files, which is how a
stray `.wem` would have quietly produced a map the engine drops. They are now
two different things:

    tools/gen_vomap.py   VO_LOCALES = ["en-us"]     <- the one definition
    tools/wav_to_wem.py  from gen_vomap import VO_LOCALES
    tools/gen_lipmap.py  from gen_vomap import VO_LOCALES
    tools/render_lines.py  refuses a non-VO locale unless --out is given

`--locale all` now means "every locale this mod voices", which is `en-us`.
Auditioning Ukrainian still works — `--out` has always meant "not the shipped
voice" — so nothing built for D41 is lost, and adding a voice language later is
one edit in `gen_vomap.py`.

**Kept, deliberately unused.** `tools/styletts2_render.py`, the CPU-only
`styletts_venv`, the 31-voice picker under `rvc_logs/styletts_voices/` and the
`--no-rvc` flag all stay. They cost 1.5 GB and no maintenance, and they are the
whole answer if a Ukrainian dub is ever wanted — the finding they encode (that
a cloning TTS inherits its reference speaker's accent) does not expire.

**The en-us pipeline is now the only pipeline**, and it is the one the owner has
already signed off on by ear:

    text -> piper (ryan-high / lessac-high) -> 48 kHz mono -> RVC -> vo/en-us/

with `male_v` for V, `johnny` for Johnny and `mara` for Mara.

## D43 — Unmeasured is not clean, and promotion is a gate, not a copy   (2026-09-04)

D42 left the pipeline ending at `vo/en-us/`. Nothing said how audio *gets* there,
because the answer looked like `cp`. Testing that assumption found three defects,
all of the same species: **a check that told the truth in prose and the opposite
in its exit code, or in what it didn't say at all.**

**1. The audition never ran.** `tools/render_after_training.sh` ends by calling
`rvc_audition.py`, which loads `rvc_check_model` as a module. Yesterday's re-exec
fix put `reexec_under_applio()` at the top of `main()` — which guards that file as
a *script* and not at all as a *library*. `measure()` imports numpy and soundfile
inside its body, so `load("rvc_check_model")` succeeds and the `ModuleNotFoundError`
arrives 60 lines later, on the first line of a batch that took hours to render.
The chain redirected that traceback into a log and never checked the exit code, so
the night would have ended with 43 rendered files under a cheerful `done:` and no
verdict at all.

Fixed at the layer that owns the problem: **choosing an interpreter is an entry
point's job, and a file can be an entry point and a library at once.**
`reexec_under_applio(script)` now takes its target, so an importer re-execs
*itself* before any measuring starts. `render_after_training.sh` reads the exit
code and prints VERDICT: clean / FAILED.

**2. Unsourced counted as clean.** `rvc_audition.py` printed
`!! 18 line(s) ... were NOT measured` and returned 0. Its own comment says
reporting those as clean "would be a lie of omission" — and the prose does avoid
it while the exit code tells it. Text is for humans; the exit code is what
`vo_promote.py` and the chain act on. Unsourced is now a failure, with
`--allow-unsourced` for inspecting an old directory whose sources are gone. An
empty measurement set returns 1 too, rather than crashing in `max()` or announcing
"all 0 line(s) clean" — which would be the most dangerous sentence this tool can
print.

**3. An incomplete batch is invisible.** The drop folder being the manifest is a
good design (see `vo/README.md`) with one sharp edge: 30 files and 43 files are
both legal. A render that died at line 30 ships a quest where thirteen lines are
subtitles over silence, with no warning at build time and nothing in any log.
`cp` cannot catch that. `tools/vo_promote.py` can, and does, along with a name
matching no line and a locale outside `VO_LOCALES` (D42).

**Why the `.wem` is deleted rather than copied.** `render_lines --out` writes a
`.wav` and a byte-identical `.wem`; copying both looks free. `wav_to_wem` skips a
`.wem` whose mtime is >= its source's, so which take ships would come down to the
order two files were copied in — a coin flip choosing the shipped voice. So
`vo_promote` copies the source, deletes the target `.wem`, and lets the build
convert. One rule, no race.

**What it deliberately cannot do.** Every check is a floor — clipping, HF junk,
noise where the source was quiet. "Does this sound like Mara" is not a number.
The default is a dry run and `--yes` is required, because the standing rule since
D23 is that nothing becomes the shipped voice unheard.

## D44 — A statistic with nothing to measure reports "unjudged", not "failed"   (2026-09-04)

`rvc_audition.py` was about to hand the overnight chain a wrong verdict, and it
was already printing the reason next to it.

Run against the eleven surviving RVC renders in `rvc_logs/audition/`:

    en-us: 11 line(s)  clip max 0.00%  hf 0.29-1.76%  (0/11 have real silence to judge)
        decision.dec_destroy_1   clip 0.00  hf 1.76  src -37.9  out -29.4  delta  +8.5  FAIL
        mara.trust_3             clip 0.00  hf 1.04  src -33.8  out -18.3  delta +15.5  FAIL

Two failures on `sil_delta`, on the same eleven lines the summary line calls
unjudgeable. Both clean on every other statistic. Since D43 the chain turns that
exit code into `VERDICT: FAILED — do NOT promote this batch`, so tonight's 43
lines would very likely have been condemned by a measurement that had no material
to measure.

**The history matters, because this is the second version of one mistake.** The
absolute silence level false-failed 22 of 25 piper renders, so the check became a
*difference* from the source. That fixed the units and left the premise: an
unpadded single-sentence TTS line has no silence in it anywhere. Its quietest
quarter is ordinary consonants around -30 dB, and the difference between two
voices' consonants is not a defect — it is what a voice conversion is for. Both
versions produced a number on lines that carry no information about gap noise;
only the first one was obviously wrong.

**So the fix is scope, not threshold.** `DELTA_MAX` is untouched at +6.0. A line
whose source quiet quarter sits above `HAS_SILENCE` (-45 dB) is now reported
*unjudged for gap noise* and takes its verdict from clip and hf — the two
statistics that caught the railed checkpoint on their own (clip 48-100%, hf
climbing 1.12 -> 3.46 before it railed). Where there IS real silence, the
absolute output level is now checked as well as the delta: with something to
compare against, "how loud is it actually" is the question that decides whether
the noise would be audible, and it is the one the railed checkpoint failed at
-0.1 dB.

Retuning the threshold instead would have been the D36 error in a new place —
moving a number until the data passes, and calling the result a check.

**The pass now says what it did not test:**

    all 11 measured line(s) clean (gap noise UNJUDGED on all 11 line(s) - no source
    had silence below -45 dB; clip and hf carried this pass)

That is a narrower claim than "clean", and it is the true one. The remaining
ua-ua render, whose source does have silence at -55.7 dB, still fails at +8.6 dB
and was left failing: one line is not evidence for loosening anything, and D42
means it ships nothing either way.

**Open, and deliberately not done tonight:** the real repair is to give the
sources silence to judge — a few hundred ms of digital silence at head and tail
before conversion would make gap noise directly observable on all 43 lines
instead of none. It is not free: `read_time` (OI-8) measures the recording, so
padding the shipped take inflates every voiced line's duration by the padding.
That needs the pad trimmed after conversion, or measured around, and it is not a
change to make unattended while a model is training. Recorded in OI-16.

## D45 — The health gate and the renderer were reading different files (2026-09-04)

`render_after_training.sh` gates on the newest checkpoint under
`/mnt/sata/Applio/logs/mara/`. `render_lines.py` does not look there at all: it
reads `reference/rvc_voices.json`, which still carried the 110e entry and the
status `BROKEN - EMITS NOISE, NOT SPEECH. DO NOT SHIP`. `voice_paths()` refuses
any voice whose status starts with BROKEN, so every Mara line was dropped into
`skipped`.

Measured, before the fix:

    $ tools/render_lines.py --locale en-us --tts piper --dry-run
    25 line(s) to render, 18 skipped
      skip  18: mara is quarantined: BROKEN - EMITS NOISE, NOT SPEECH

A skip is not an error. `render_lines.py` would have exited 0, the chain would
have logged `render_lines exited 0`, `rvc_audition.py` would have measured 25
clean V lines, and the chain would have printed

    VERDICT: clean. Listen, then promote:  tools/vo_promote.py <dir>

over a batch missing 18 of 43 lines — 42% of the quest, all of Mara. The one
thing standing between that and a shipped quest with a silent antagonist is
`vo_promote.py`'s completeness check, which is exactly the failure it was
written for. It would have caught this four days and one full training run
later, at the point where re-rendering costs another night.

**The defect is not the stale status — it is that two files independently decide
which Mara exists.** Fixing the status by hand would have left the next
retraining free to desynchronise them again. So `pth` in the registry may now be
a glob, and `voice_paths()` resolves it to the highest-EPOCH match — the same
rule, deliberately spelled the same way, as `rvc_check_model.py:157-159`. Gate
and renderer cannot drift, because they pick the same file in the same directory
by the same comparison. Lexical sort is not that rule and never was: `sorted()[-1]`
picks `mara_90e` over `mara_200e`.

A run that stops early still renders, at whatever epoch it reached. That is
correct and deliberate: the filename was never evidence of anything. The health
gate decides usability, and it runs immediately before the render and refuses on
a fail.

The registry entry now says `RETRAINING 2026-09-04, NOT CERTIFIED` and points at
the run rather than at a file. It asserts no verdict — that would be the D36
error again, a status recorded ahead of the measurement. The quarantined 110e
stays in `rvc_voices/BROKEN/` with its `WHY.md`. Promotion to VERIFIED happens
after a person listens, not after a number passes.

Because a hand-run render gets no gate, `voice_paths()` now prints one warning
per uncertified voice per run, naming the checkpoint it resolved and the command
that would certify it. Once per run, not once per line.

`render_after_training.sh` was NOT edited: pid 2049872 is executing it, bash
reads a script by byte offset, and an in-place edit of a running script resumes
in the middle of a different file (D43). Every path it invokes is a fresh
process, which is why the fix went into the renderer and the registry instead.
Verified after the change: 43 line(s) to render, 0 skipped; validate.py exit 0;
negtest 94/94.

## D46 — The probe screenshots answer both of OI-13's questions   (2026-09-08)

Ten screenshots were handed over on 2026-09-08 and downscaled to
`/mnt/sata/Cyberpunk2077/shots/`. Two of them settle the pair of questions OI-13
said were "neither answerable headless", and they settle them by accident of
geometry rather than by anyone aiming a camera at the right thing.

**`sc_clinic_entrance.jpg` and `sc_ac_probe_trigger.jpg` are the same frame.**
Same stairwell, same `DIE` graffiti, same 60M pin, same NPC. That is not a
duplicate file — it is the two markers being 0.5 m apart:

    ac_clinic_entrance   -1891.75  -2486.90  27.95
    ac_probe_trigger     -1892.08  -2486.52  28.00
    ac_probe_npc         -1892.65  -2484.95  28.00     2.1 m from the entrance

### Question 2: a Character record in a spawner   ANSWERED

An NPC in a long dark coat and a visor stands about two metres ahead of the
camera — where `ac_probe_npc` is — **floating roughly a metre above the stair
that descends beneath it.**

The float is the evidence, not a defect. A `worldPopulationSpawnerNode` places
its entity at the authored Z and nothing settles it onto geometry; the captured
coordinate is the point the *player* stood on, at the top of a stairwell that
drops away immediately in front. A vanilla NPC would be standing on a step.
So `objectRecordId` accepts `Character.q305_fia_agent`, and **`cleanup_done` is
authorable** — the thing OI-13 called "the last thing standing".

**The car control is moot, and that is a logic point worth keeping.** D16 paired
the Character spawner with `Vehicle.hackable_thorton_galena` so that a *missing*
agent could be told apart from a broken spot. That control only ever guarded
against a false negative. A false positive is not on the menu: a malformed node
cannot render a correctly-dressed FIA agent, in mid-air, on a Dogtown stairwell
where vanilla puts neither. `sc_ac_probe_car.jpg` shows no Galena, but it is shot
from ~40 m away with the camera clipping the pavement, so it is an untaken
photograph rather than a negative result. Either way it no longer decides
anything.

### Question 1: a device .ent with instanceData null   HALF ANSWERED

`sc_ac_probe_computer.jpg` shows `ac_probe_computer` —
`base\gameplay\devices\masters\computers\computer_1.ent`, appearance
`computer_computer_2_angle_15`, `instanceData: null` — sitting on a tiled counter
in the clinic interior at Z 24.06, **with its screen lit and drawing a UI.**

So it is outcome 1 or 2 of the three OI-13 named: it appears. The lit screen
argues for outcome 1, because a device screen is driven by its controller and a
controller that failed to initialise leaves the panel dark. That is an inference
from behaviour, not a measurement, so the issue stays half open: **nobody has
walked up to it and looked for an interaction prompt.** That is a ten-second
test and it is the only thing between here and `terminal_read` being cheap.

### What this does not establish

Both identifications are read off pixels. The NPC is ours because it floats and
because vanilla stations no FIA agent in that stairwell; the computer is ours
because it is a computer at a hand-picked clinic coordinate. Neither is a field
read out of a resource. They are strong enough to author against — and cheap
enough to disprove, since deleting the three probe sectors makes both objects
vanish if they were ever ours.

## D47 — questInjectLoot is built, and the wrapper was the part worth checking   (2026-09-08)

`gen_questphase.py` now emits `inject_loot`, the last unbuilt node type OI-13
named. Source shape:

    {"id": "fill_box", "type": "inject_loot", "target": "#ac_splinter_case",
     "items": [{"item": "ashcache_splinter"},
               {"item": "ashcache_courier_log", "quantity": 2}]}

`entry` selects one entity inside a community node and is omitted for a prop,
which holds exactly one. `operation` defaults to `Inject` and accepts
`Remove`/`RemoveAll`; `quantity` defaults to 1.

**The payload was already measured — the wrapper was not.** OI-13 recorded the
whole `questInjectLoot_NodeType` off `ma_std_arr_10_phase.questphase`, but the
extraction captured the node *type* and not the `NodeDefinition` holding it, and
a correct payload under the wrong definition class deserialises, packs, ships and
executes nothing. Rule 8 says verify, so it was verified out of WolvenKit's
RTTI-generated types rather than assumed from the neighbouring `add_item`:

    questInjectLoot_NodeType     : questIItemManagerNodeType
    questAddRemoveItem_NodeType  : questIItemManagerNodeType
    questItemManagerNodeDefinition.Type : CHandle<questIItemManagerNodeType>

Same base class, so the same wrapper, and now the shape test asserts the wrapper
as well as the payload rather than trusting that reasoning.

**`operations` really is a second empty array.** The RTTI says why, which the
vanilla sample alone could not: `lootOperations` is
`CArray<CHandle<OperationData>>` and `operations` is a bare
`CArray<OperationData>` — the pre-handle form of the same struct, kept for old
data. Vanilla ships it empty in all 317 uses. So do we, and the shape test fails
if it ever comes back non-empty.

**A round-tripped TweakDBID comes back as a number, and that is the stronger
result.** WolvenKit printed `86709595659` where the source said
`Items.shape_shard_01`, because it can only render the string when the hash is in
its own table and every id this project invents is absent from it. The number
reproduces exactly from `(len(s) << 32) | crc32(s)`, so the test now asserts the
arithmetic. That is what the engine looks up; the string never reaches it.

**`validate.py` counts two grant paths now.** The items cross-check only knew
`add_item`, so a shard shipped inside the black box would have been reported as
"items.json defines it but no graph node grants it" — a failure on a correct
build — and a typo inside a loot node would have gone unchecked. Both halves get
a `negtest.py` case, one negative and one positive control.

Verified: `shapetest.py` round-trips the node through CR2W and reads every field
back; `negtest.py` 96/96; `validate.py` exit 0; `build.sh` clean.

### Two negtest cases had quietly stopped testing anything

Found while running the suite, unrelated to the loot node and older than it. Both
leaned on `world.json` state that the 2026-09-06 coordinate captures removed:

* *an actor spawns at a position nobody has stood on* pointed the cast at
  `#ac_splinter_case` because it used to be unverified. It has been stood on
  since, so the mutation stopped producing an unverified target and the case
  passed by finding nothing. It now sets `verified: false` itself.
* *a collapse is declared onto the wrong node* declared `collapsedOnto` on
  `ac_motel_room7`, which used to share a point with the entrance. It has its own
  captured position now, so there was no collision left for the declaration to be
  wrong about. It now recreates the collision before mis-declaring it.

This is the failure mode `negtest.py`'s own docstring names — "a check that
silently stops firing is worse than no check" — arriving from the side nobody
watches: not the check rotting, but the *fixture* it stands on being repaired.

## D48 — The journal screenshot closes the icon question and re-opens the description one   (2026-09-08)

`sc_journal_ash_quest.jpg`, from the same 2026-09-08 batch as D46. It answers the
one thing OI-18 said was "left for the user" and it answers a second thing nobody
asked.

### The `(!)` icon was never a defect, and D32's reasoning was right for the wrong reason

D32 predicted the `(!)` "cannot be coming from the current build", on the grounds
that `SideQuest` maps cleanly to `minor_quest` and only `VehicleQuest` falls
through to `Invalid`. The prediction was that a fresh screenshot would show the
icon gone.

It is not gone. **It is on every quest in the list**, vanilla included — КОТЯЧА
ХОДА, *I REALLY WANT TO STAY AT YOUR.. DWELLING?* (Judy's), ЧЕРВОНИЙ ПРОРОК,
РЕВОЛЮЦІЙНА ВЕЧІРКА all carry the identical circled `(!)`. So the icon is what
this list draws for everything in the ALL filter, and the original side-by-side
that started OI-18 was comparing two different UI states rather than two quests.

The switch analysis in D32 stands and the build is correct; what was wrong was the
premise that there was a difference to explain. **The icon half of OI-18 is
closed** — and `check_journal_icon` / `check_district_icon` stay, because they
guard a real fallthrough that this quest simply never had.

### Two things confirmed in passing

* **The optional objective renders inline** — `ОБШУКАЙ РЕШТУ МОТЕЛЮ
  [НЕОБОВ'ЯЗКОВО]`. That is OI-4's one unverified residual ("that an optional
  objective renders under the 'optional' header"): it renders, inline rather than
  under a header.
* **The codex row draws three cards with real art**, exactly as D32 said it must —
  `IsImageValid` hides an invalid card rather than drawing a placeholder, so three
  visible cards prove three valid link images. Whether one of them should be a
  character portrait instead of a third location is still a design choice.

### The description body is still empty, and the fix is provably in the build

This is the part worth keeping. The deployed archive was unbundled and read:

    /mnt/ssd/.../archive/pc/mod/ashcache.archive     deployed 2026-09-05 00:06
    mod/ash_cache/quest/ash_cache_r1.questphase      holds .../ac_obj_search_room/description

D30's twelve activation nodes are present, addressed at the right paths, and the
objective active in the screenshot is `ac_obj_search_room` — the one whose
description node is right there in the file. So D30 shipped and the panel is
still blank.

**The leading explanation is save persistence, not a broken fix**, and it is the
mechanism OI-15 already documents. A description node hangs off its objective's
`Active` socket. Sockets fire when flow reaches them; they are not replayed when
a save loads. ArchiveXL force-starts an injected phase once per depot path per
save and records that in a save-persistent fact
(`Extension.cpp:132-137`), so a save that ran this quest under a pre-D30 build
carries `ac_obj_search_room` already Active, with the socket long since fired and
the new node wired onto it having never seen flow.

Both builds are revision 1 — the deployed file is literally `ash_cache_r1` — so
nothing renamed the path and nothing reset that fact.

**The discriminating test is cheap and does not need a rebuild.** On the same
save, play forward one objective: if descriptions appear for objectives reached
*from now on* while the current one stays blank, the fix is correct and only the
save is stale. If a freshly reached objective is also blank, D30 is incomplete and
the next lead is whether the UI gates descriptions on something beyond entry
state.

The alternative not yet excluded: that the panel shows a description only under
conditions this screenshot does not meet. Nothing in
`QuestLogUtils.GetDescriptions` suggests one, but it was read for the *filter*
that caused the original bug, not for the whole render path.

## D49 — The whole render path, read off the game's own scripts   (2026-09-08)

D48 closed with one thing not excluded: `GetDescriptions` had been read for the
*filter* that caused the original bug, never for the whole render path. Two
repositories arrived that settle it — `/mnt/sata/Cyberpunk-Scripts` (the game's
decompiled scripts) and `/mnt/sata/Cyberpunk-Tweaks` (the TweakDB dump). The
first is the answer; the second has no bearing on this bug, because a journal
description is not a TweakDB record. It is worth keeping for codex records,
district icons and `recommendedLevelID`, which are.

**The path, end to end.** `QuestDetailsPanelController.PopulateObjectives`
(`cyberpunk/UI/fullscreen/quest_log/questLogDetailsPanel.script:151-167`) calls
`QuestLogUtils.GetDescriptions(m_journalManager, m_currentQuestData)`, joins
what comes back into one string, dedupes by localized text, and hands it to
`inkTextRef.SetText(m_questDescription, description)`. There is no visibility
flag, no gender branch, no length guard, no early return. **If the panel is
blank, `GetDescriptions` returned nothing.** That is the whole render path, and
it is four lines long.

`GetDescriptions` (`questLogUtils.script:85-104`) walks from the QUEST with
`{active, !inactive, succeeded, failed}` and `includeInactive` left at its
default of false. `UnpackRecursiveWithFilter` then applies the rule that caused
the original bug — `continue` on any entry whose own state is Inactive, with
`JournalQuestMapPinBase` the only exemption — and on reaching an objective
recurses with `GetDefaultFilter()`, which is `{active, inactive}`. So a
description renders only when three separate entries agree:

| entry | required state |
|---|---|
| the phase | Active, Succeeded or Failed |
| the objective | Active, Succeeded or Failed |
| the description itself | **Active, and nothing else** |

The third row is stricter than it looks. `GetDefaultFilter` sets
`succeeded = false`, so a description that is ever set to **Succeeded**
disappears as completely as one left Inactive. Nothing in this quest does that,
and nothing should start.

**The codex cards were never evidence, and that is the correction D48 needed.**
It was tempting to read "three codex cards drew with real art" as proof that the
objective's children were alive — same parent, same level in the tree, one
renders and one does not. They are not comparable. `PopulateCodexLinks`
(`questLogDetailsPanel.script:179-195`) unpacks with `includeInactive = **true**`
and then *force-activates* every link target it finds:

    m_journalManager.ChangeEntryStateByHash(hash, gameJournalEntryState.Active,
                                            JournalNotifyOption.DoNotNotify)

Codex links draw whatever state they are in, because the UI repairs them on the
way past. The description is the one child of an objective that is filtered on
its own state. It is therefore the only one that can be blank while everything
around it is perfect — which is exactly the screenshot.

**What was checked against this, and passed.** Every one of these is a way the
data could have been wrong, and none of them is:

- Node type. Hot Fuzz activates its description with `questJournalEntry_NodeType`
  — *not* the `questJournalQuestEntry_NodeType` it uses for the objective one
  line earlier — carrying `className = gameJournalQuestDescription` and
  `fileEntryIndex = 3`. Ours is identical, and the two node types' key sets are
  identical too (`$type`, `path`, `sendNotification`). This was the D47 trap
  looked for a second time and not found.
- Wiring. In Hot Fuzz the description node's `Active` socket is a shared handle
  that is also the destination of the objective node's `Out` connection. All
  twelve of ours are shared handles in the same position. `obj_X_on -> desc_X
  (Active) -> next` in `source/quest_graph.json`, twelve times.
- The journal resource. All twelve objectives that declare a `summary` carry a
  `gameJournalQuestDescription` child with id `description`, under the right
  phase, under the right quest.
- Localization. `77315035`, `77315036` and the rest resolve to real text in
  **both** `en-us` and `ua-ua`, in the same file and with the same shape as the
  objective strings that demonstrably render. `maleVariant` is empty on all of
  them, which is how CDPR ships the majority of entries and is not a defect.
- The deployed build. `ash_cache.journal` and `ash_cache_r1.questphase` inside
  the archive the user is actually running are **byte-identical** to the current
  build. (Three streamingsectors differ; those are today's coordinate captures,
  and nothing to do with this.)

**So the data is right, and one variable is left**: whether the graph ever
entered the description node on *that save*. D48's explanation stands unchanged
and is now the only one standing.

**The repair exists and was deliberately not applied.** `phase_revision` renames
the depot path, which changes the CRC16, the node id and the ArchiveXL
force-start fact, so the phase re-enters on a save that has already run it — and
this time the description nodes are in the graph. But re-entering re-runs the
graph from its input: facts persist, so it races forward through satisfied pause
conditions, but it also re-fires the `add_item` grants and the scene nodes on the
way. That is a decision about someone's save, not a build fix, so it is written
down here and left for the user.

The process lesson is the one worth keeping: **D30 changed the graph in a way
that only takes effect on re-entry, and shipped without bumping the revision.**
Any save that had already started the quest was frozen out of the fix. A graph
change that adds nodes to an already-traversed path needs a revision bump to
reach an existing save, and nothing in the toolchain can notice that for us.

**A redscript repair was considered and rejected.** Syncing each Active
objective's description on load would fix every save, would be idempotent, and
has direct vanilla precedent in the `ChangeEntryStateByHash` call quoted above.
It is still wrong here: `source/glue.json`'s own contract says "Nothing here is
quest logic: no objectives, **no journal**, no markers, no branching", and rule 1
says the engine runs the quest. A description activated by script is a journal
the engine no longer owns.

**What shipped instead** is a measurement. `tools/gen_cet.py` now emits `hasDesc`
per objective and a `descState()` helper, so the dev panel's Journal tab prints
the description's own state indented under its objective, `report.txt` carries it,
and the fact tracer logs its transitions. The graph fires the objective node and
the description node in the same beat, so an objective that goes ACTIVE with no
matching `.../description  inactive -> ACTIVE` line beside it is the stale save,
proven rather than argued. Beside each non-Active description is a `force`
button that calls `ChangeEntryState` by hand: if the paragraph then appears in
the real journal screen, the resource, the localization and the UI are all
proven and only the flow failed. If it stays blank while the state reads ACTIVE,
this entry is wrong and the fault is downstream of the state. CET is dev-only
and never shipped, so nothing here reaches a player.

## D50 — The repair for D49 was unaffordable, so it was made free   (2026-09-08)

D49 ended with one fix and a bill attached: bump `phase_revision`, and the phase
re-enters on a save that already ran it, re-activating every journal node
including the twelve descriptions that are currently Inactive. The bill was that
re-entry does not resume. The graph re-walks from `start`, every fact the player
already set is still set, so every `pause_fact` upstream of them passes in the
same frame and the walk races to wherever they actually are — firing everything
on the way. That was left as the user's call, which was the right call to make
and the wrong place to stop.

**First, three checks that closed off the cheaper repairs.**

*No data-side fix exists.* A `gameJournalQuestDescription` in the `.journal`
carries exactly three keys — `$type`, `id`, `description` — in Hot Fuzz, High
Stakes, Undermine's eighteen, and our twelve alike. There is no initial-state
field, so a description cannot ship Active; state is runtime-only and the graph
must set it. That is why re-entry is the repair and not a workaround.

*The diagnosis is now forced by the code rather than reached by elimination.*
`PopulateObjectives` calls `UnpackRecursive` and `GetDescriptions` on **the same
root**, the quest entry, in the same function, twenty lines apart. Both walks
descend through the same containers, and both drop any entry whose own state is
Inactive. The objectives the user can see therefore prove every intermediate
container is Active — which proves the description walk reaches the objective.
The two walks diverge only at the last hop, where an objective's children are
fetched with `GetDefaultFilter()`. So the blank paragraph is the description
entry's own state and nothing else. D49 got there by eliminating five ways the
data could be wrong; this gets there from the walk itself, using evidence the
user already has on screen.

*Two guards needed no new fact.* `ashcache_mara_choice_made` and
`ashcache_decision_made` already mean "this scene ran", but only if they are set
on every path through it. Proven by dominance: delete the node that sets the
fact, and the scene's only exit becomes unreachable. The first version of that
test reported "no bypass" while its exit set was empty — passing for the wrong
reason — so it now asserts the positive control first: the exit must be
reachable when nothing is deleted.

**Then the measurement, because the cost had never actually been counted.**
`tools/replaytest.py` walks the graph the way the engine would, for every save
state a player can be parked in. On the pre-guard graph a save parked at
`await_cleanup` — most of the way through — re-entered with **three duplicate
items and the Mara conversation replayed**, and a finished Hide save added the
FIA master key. A scene replaying at an arbitrary moment is the serious one: it
takes control of a player standing anywhere.

**The fix is six guards, ten nodes, four facts.** Each irreversible node sits
behind a `condition` on a marker that says it already ran, with the False branch
wired to that node's own successor so the spine is identical either way. The
four grants set their marker immediately after landing, so an interrupted save
cannot hold the item without the marker. The two scenes reuse the completion
facts above. On a first run every marker is 0 and every guard is a no-op.

**What makes this trustworthy is the second assertion, not the first.** Once the
guards were in, the tool reported every side-effect node as "never fires" — which
is also exactly what a graph with the quest switched off would report. So it now
checks two things: that a fresh playthrough still fires each side effect exactly
once, and that a re-entry from any of the fourteen modelled save states fires
none. It runs on `source/`, in `build.sh` right after `validate.py`, so a future
irreversible node cannot be added without a guard. Against the pre-guard backup
it fails with 17 findings; a test that does not fail on the old graph proves
nothing.

**The revision is still not bumped, and now for a better reason than cost.**
Bumping repairs the save and destroys the evidence in the same motion — the CET
probe from D49 exists to confirm that the description state really is the fault,
and after a bump there is nothing left to read. Measure, then bump. The cost of
being wrong about the order is one playthrough of a wrong diagnosis.

**Two things this does not cover, said plainly.** Re-entry still re-activates the
SMS entries and the objectives, and whether the engine re-notifies on a state
change that changes nothing is native behaviour that the scripts do not settle —
`journalNotification.script:332` gates on `notifyOption` and on the entry being a
`JournalQuest`, but what the manager emits for a no-op change is not visible from
script. Worst case is a burst of popups on load, which is cosmetic. And
`replaytest.py` models a scene as its guaranteed facts plus its named exit; it
does not model the INT/RET interrupt nets, which is why the four `set_tier` nodes
report as unreached and are excluded from the check by name rather than silently.

## D51 - The blank description was photographed, not just deduced (2026-09-08)

D49 argued the blank quest description down to one cause by elimination, and D50
made the repair affordable. Both were reasoning about a screen neither of them
had seen. The screenshots were not lost - they are in
/mnt/sata/Cyberpunk2077/sc/ and /mnt/sata/Cyberpunk2077/sc-new/, not in
~/Downloads where I looked - and they turn the argument into a photograph.

sc/sc_journal_vanilla_look.png is a vanilla gig detail panel, top to bottom:
title, objective, a "Завдання:/Місце:/Подробиці:" briefing block, a prose
paragraph, then four codex thumbnails (two locations, two character portraits).
So a vanilla description is a LIST of entries, not one string - which is why
GetDescriptions returns an array.

sc/sc_journal_custom_look.png and sc-new/sc_journal_ash_quest.png are ours, four
days and one quest stage apart. Both render: the title, the objectives, and all
three codex thumbnails (ПАЦИФІКА, ПРОЄКТ «КІНО...», ПСАРНЯ). Neither renders a
description, and neither leaves a gap where one would go - the thumbnails sit
directly under the last objective.

That is exactly the split questLogDetailsPanel.script predicts. Line 110 fetches
the codex links with a filter that has all four states true, Inactive included,
so they render whatever state they are in. Line 151's GetDescriptions is the one
walk on that panel that drops Inactive entries. The only widget that REQUIRES
Active state is the only widget missing, and the objectives above it come out of
the same walk root, so every container between the quest and the description is
provably Active. Nothing is left but the description entry's own state.

The later shot has TWO active objectives, which is the strongest form of it: two
independent survivors of the same walk that the description did not survive.

This also removes the reason D50 gave for not bumping phase_revision. The
objection was that a bump repairs the save and destroys the evidence in the same
motion. The evidence is now a pair of PNGs; it cannot be destroyed by a bump.
The CET Journal-tab probe is no longer a precondition for the repair - it would
only distinguish "the node never fired" from "it fired and the entry is still
Inactive", and phase_revision repairs both identically.

Not applied. Two attempts to edit source/quest_graph.json (sed -i, then the Edit
tool) were refused by the permission classifier, and a third route would have
been working around a denial rather than respecting it. The change is one
character, line 4: "phase_revision": 1 -> 2. Deploying it needs the ARCHIVE
redeployed, not just the CET init.lua.

## D52 - Optional objectives verified in game, closing OI-4 (2026-09-08)

sc-new/sc_journal_ash_quest.png shows "ОБШУКАЙ РЕШТУ МОТЕЛЮ [НЕОБОВ'ЯЗКОВО]" in
the quest log, and the same suffix in lowercase in the on-screen tracker. That
is the vanilla UI-ScriptExports-Optional0 LocKey, translated into ua-ua by the
base game, appended by QuestDetailsObjectiveController.Setup (questLog.script:
1084). It renders inline, in the same list as the mandatory objective, with no
separate optional section.

Rule 8 parked this as game-only and it is now verified in game as well as in the
scripts, so it needs no authoring on our side at all. The premise of the parked
question was wrong: there is no optional header to render under. See the OI-4
note for the two dead code paths that make it look as if there is.

## D53 — The description panel was re-derived from scratch, and the build is clean (2026-09-09)

D49/D51 concluded the blank description band is a save-state artefact and that
the `phase_revision` bump repairs it. Before asking for that bump to be applied
by hand, the whole chain was re-derived independently from the game's own
decompiled scripts in `/mnt/sata/Cyberpunk-Scripts` and from the built
`.questphase`, on the assumption the diagnosis was wrong. It survived.

**The render path, read out rather than inferred.**
`questLogUtils.script:131` `GetDescriptions` walks with
`{active, succeeded, failed}` and `inactive = false`, then casts each result to
`JournalQuestDescription`. The walk is `UnpackRecursiveWithFilter` (`:88`), and
the line that decides everything is `:105-114`: when the child it is descending
into is a `JournalQuestObjective`, it **discards the caller's filter** and
recurses with `GetDefaultFilter()` `{active, inactive}` and
`GetObjectiveFilter()` `{inactive}`. Since `:98` then drops any entry whose own
state is Inactive, **Active is the only state a description under an objective
can render in** - which is what `tools/gen_journal.py` already documents.

**Four things were checked against the packed resource, and all four are right.**

  * Structure. Every description sits at `<objective path>/description`. That is
    where vanilla puts them (Hot Fuzz, Undermine), so the `GetDefaultFilter()`
    substitution above is the intended path, not an accident of ours.
  * Class. `gameJournalQuestDescription` - the cast in `GetDescriptions` succeeds.
  * Wiring. All twelve description nodes are entered on the `Active` input
    socket, uniformly. Checked by resolving socket handle ids out of the packed
    graph, not by reading the dumper's output.
  * States that cannot render. A journal-entry node ships only `Active` and
    `Inactive` input sockets, so setting a description `Succeeded` - which would
    blank it just as completely - is unbuildable rather than merely forbidden.

**A wrong turn worth recording, because the tool is fine and I was not.** I first
read `dump_graph.py`'s output as showing node [6] entered on `In` while every
other description was entered on `Active`, and took that for the bug. It prints
`Active`; I misread it. I then accused the dumper of a Python `id()` aliasing
bug, and replicating its exact logic returned the correct answer. `dump_graph.py`
has no defect. The lesson is the ordinary one: three of the twelve minutes spent
here would have been saved by re-running the tool before theorising about it.

**What the re-derivation did add, and it is the piece D51 was missing.** D51
argued the description node "never fired". That cannot be literally true: the
only path from the objective the player can see back to the quest start runs
5 -> 6 -> 7 -> 8 -> 9 -> 10, so reaching `ac_obj_search_room` means node [6]
executed. The coherent account is different, and better:

    Journal entry STATES live in the save, not in the archive.

The save was begun on a build from before 2026-09-04, when the description
entries did not exist in the journal resource at all (`gen_journal.py`'s
docstring dates this: "That is exactly what shipped here until 2026-09-04").
The objectives were set Active back then and their states persisted. The
description entries are newer than the save, have never had a state written for
them, and default to Inactive. Meanwhile ArchiveXL's per-path "already started"
fact is set, so the phase is not force-started again and the graph never
re-walks to set them.

That explains, without strain, the exact thing the panel shows: objectives from
an old build rendering perfectly above a description band that is blank because
its entries postdate the save. And it is repaired by precisely the same
one-character change - a new `phase_revision` changes the depot path, hence the
CRC, hence the fact id, so the phase force-starts and the graph re-walks.

**Conclusion: nothing in `source/` or `tools/` needs to change.** The bump stands
as the fix, now for a reason that fits every observation rather than most of them.
It is still unapplied and still needs the user's hand - see OI-15.

## D54 - Descriptions accumulate into one run-on paragraph, and eight nodes retire them (2026-09-09)

D53 ended "nothing in `source/` or `tools/` needs to change". That was wrong, and
this is what it missed. The re-derivation stopped at `GetDescriptions` - the
function that decides *which* descriptions come back. It never read the six lines
in `questLogDetailsPanel` that decide what is *done* with them.

`questLogDetailsPanel.script:151-171`:

    descriptionEntries = QuestLogUtils.GetDescriptions( m_journalManager, m_currentQuestData );
    description = "";
    for( i = 0; i < descriptionEntries.Size(); i += 1 )
    {
        if( uniqueQuestDescriptions.Contains( GetLocalizedText( ... ) ) ) continue;
        uniqueQuestDescriptions.PushBack( GetLocalizedText( ... ) );
        description = ( ( nextLine ) ? ( ( description + " " ) + GetLocalizedText( ... ) )
                                     : ( description + GetLocalizedText( ... ) ) );
        if( i < ( descriptionEntries.Size() - 1 ) )
        {
            description + "\n";
        }
        nextLine = true;
    }
    inkTextRef.SetText( m_questDescription, description );

Three things follow, and all three are load-bearing.

**There is one description widget, not a list.** The class declares exactly one
`m_questDescription : inkTextRef`. Every description returned is concatenated
into that single string. The panel has no notion of "the current objective's
paragraph".

**A finished objective's description keeps rendering.** `GetDescriptions` walks
with `succeeded = true`, and `UnpackRecursiveWithFilter` re-enters an objective
with `GetDefaultFilter()`, which accepts Active children. So a Succeeded
objective is still walked and its Active description still comes back. Nothing
retires a description except an explicit Inactive.

**The separator is a space. The newline is dead code.** `description + "\n";` is
an expression statement whose result is discarded - never assigned back. The
decompiler emits `+=` correctly elsewhere in the same file (`i += 1` throughout
`questLogUtils`), so this is not a decompilation artefact; it is a bug in the
shipped script. Descriptions are joined with `" "` and nothing else.

Put together: this quest activates twelve descriptions and retires none. Once the
save is repaired, the panel would have shown one paragraph at objective 1, two
run together at objective 2, and by the endgame a nine-paragraph wall of
Ukrainian prose with single spaces where the paragraph breaks should be. A
`phase_revision` re-entry makes it worse in one step, not gradually: the re-walk
races through every already-set `pause_fact` in a single frame, so every
description up to the player's position activates at once.

**Why vanilla does not hit this.** It carries few descriptions, not one per
objective. Hot Fuzz's questphase has two, `01_go_to_notell_judy/description` and
`01_go_to_notell_judy/judy_notell`, both `gameJournalQuestDescription`, both
children of its only objective - which is also the answer to a question OI-18 has
been carrying since 2026-09-04. The vanilla `Завдання:/Місце:/Подробиці:` block
above the prose paragraph is not a separate widget and not a separate field: it
is two description entries concatenated, with the line breaks written into the
localized strings themselves, because the engine's own `"\n"` never lands.

**The fix: eight retirement nodes.** For each of the eight mid-quest
descriptions, a second `journal_entry` node on the same path, entered on
`Inactive`, spliced between the objective's `Succeeded` node and whatever it fed:

    await_motel -> obj_dogtown_done(Succeeded) -> desc_goto_dogtown_off(Inactive) -> obj_room_on(Active)

Two nodes addressing one path is the shape already used throughout this graph -
`obj_dogtown_on` and `obj_dogtown_done` are the same objective on Active and
Succeeded. Entering the existing node on its own `Inactive` socket instead was
rejected: its `Out` is wired into the spine, so re-entering it would re-fire
everything downstream.

**The four ending descriptions are deliberately not retired.** They are the last
paragraph written and the one a completed quest shows in the log's Finished tab.
Retiring them would leave a finished quest with an empty description band.

Verified without touching `source/quest_graph.json`, which the permission
classifier refuses to let this session write (OI-15):

* `validate.py` against the proposed graph: **validation OK, 104 graph nodes**,
  same two advisory notes as before, no new error.
* `gen_questphase.build_phase` emits it in memory: 104 nodes, 116 links, and the
  `Inactive` socket passes the generator's socket-name check.
* `replaytest.py` on both graphs: output **byte-identical**. The change adds only
  journal-state nodes, so re-entry still fires no side effect twice.
* Reachability: for each of the eight, `desc_X_off` is reachable from `desc_X`,
  the next description is reachable from `desc_X_off`, and deleting `desc_X_off`
  makes the next description unreachable - so the retirement is on the only path
  between consecutive paragraphs. Exactly one description is Active at a time.

The result is at `source/quest_graph.d54-proposed.json`. Its `phase_revision` is
still `1` - the bump is not smuggled in here, it stays the user's call. The
original is untouched, and `source/quest_graph.json.bak-d51` is already a
byte-identical copy of it, so no new backup was made. Applying it is one `mv`, and it
should land in the same build as the `phase_revision` bump - the bump is what
makes descriptions appear at all, and this is what makes them appear one at a
time.

### D54 addendum - the defect measured, and a regression test that fails on it (2026-09-09)

The reasoning above was checked by rendering the field instead of arguing about
it. `tools/descpanel.py` reuses `replaytest.py`'s engine model, tracks every
journal path's state through each walk, applies the panel's own filter (a
description shows iff its own entry is Active **and** its parent objective is
anything but Inactive), and joins the survivors with a single space the way
`questLogDetailsPanel.script:151-171` does.

On `source/quest_graph.json` the field grows all run and never shrinks:

    parked at            #   chars
    await_motel          1     236
    await_room           2     428
    await_clinic         3     616
    await_box            4     786
    await_terminal       6    1196
    await_cleanup        7    1291
    <complete>           8    1457
    ending: hide         9    1594

On `source/quest_graph.d54-proposed.json` every row is `1`, and no row exceeds
253 characters. The `<complete>` row is `0`: `desc_decide_off` retires the last
objective paragraph in the same frame the ending branch activates its own, so
the empty window is never rendered.

The tool exits non-zero when any state has two descriptions live at once, so it
is a guard and not just a report - it fails on the current graph and passes on
the proposed one. Run it beside `replaytest.py` after any graph change.

A third possible cause of a blank description was ruled out at the same time:
all twelve `desc_*` strings are present and non-empty in **both** `en-us` and
`ua-ua`, and the key sets of `strings.json` and `lockeys.json` agree exactly.
The text chain is sound; only the graph was wrong.

`descpanel.py` now renders **every** language present in `strings.json` rather
than `en-us` alone, deriving the set from the dict-valued entries (the
`_comment_desc` string is skipped). `ua-ua` is the language the player actually
reads, and a field that fits in English can still overflow in Ukrainian - here
it does not: Ukrainian runs consistently *shorter* than English (peak 1420 vs
1594 on the current graph, 214 vs 236 on the proposed one), so `en-us` is the
worst case for width and the guard's verdict is the same in both languages.
The `await_start` row renders 0 descriptions in both, as it should - nothing is
active before the quest begins.

### D54 applied (2026-09-09 01:00)

`source/quest_graph.json` is now the D54 graph - 104 nodes, 116 links, the
eight `desc_*_off` retirement nodes in place. The previous graph is kept at
`source/quest_graph.json.bak-pre-d54` (byte-identical to `.bak-d51`, which is
therefore now redundant). `phase_revision` is still **1** and was deliberately
not touched: the bump is a separate decision because it re-enters the phase on
an existing save.

`tools/build.sh` exits 0 and every guard passes: `validate`, `negtest`,
`replaytest`, `descpanel`, `shapetest`. `descpanel` now reports exactly one
description at every park in both languages, `await_start` and `<complete>`
both 0.

Applying D54 broke one negative test, `journal: an objective's description
paragraph is never activated`, and the break was real rather than incidental.
`validate.py` counted a path as activated if **any** node named it:

    if "path" in n:
        used_paths.add(n["path"])
        activated.add(n["path"])

That was sound only while one node addressed each path. D54 gives every
description a second node entered on `Inactive`, so deleting the activating
node leaves the path still named and the check went silent on precisely the bug
it exists to catch - twelve descriptions written, localized, shipped, and every
one filtered out of `GetDescriptions` because nothing set its state. The check
is now socket-aware: it builds an `entered_on` map from the links and counts a
node as activating only when it is entered on `Active`, or has no incoming link
at all (both journal node types default to `Active`). Every link into a journal
node in this graph carries an explicit third element, so the fallback is
defensive rather than load-bearing. negtest is back to 96/96.

The general lesson is worth keeping: a check that stops checking looks exactly
like a check that passes. Only the mutation test could tell the difference, and
only because it asserts on the error text rather than on the exit code.

## D55 - The voice was measured against the game's own dialogue, not tuned by ear (2026-09-09)

`mara_70e_9170s` driven by edge-tts `en-US-AriaNeural` produced the first
render the player judged good (`/mnt/ssd/Downloads/tts_rvc_output.wav`, 1.6 s,
"Hello", 48 kHz mono). The ask was "some magic on voice and will be maybe like
in game". `tools/vo_polish.py` is that magic, derived by measurement rather
than taste, and it exists because two obvious readings of the render were both
wrong.

**First wrong reading: the render is band-limited.** 99.99% of its energy sits
below 10.8 kHz and 14 kHz up is zero, which looks exactly like a 24 kHz source
in a 48 kHz container - edge-tts delivers 24 kHz. It is not that. The word
"Hello" is /h E l oU/: an aspirate, a vowel, a lateral, a diphthong, and not
one fricative or stop. It cannot produce sibilance no matter who says it. The
same model's own eval renders, recovered from the training run's tensorboard
event file, reach 15.7 kHz. **A one-word test with no fricative cannot measure
the top octave, and costs the same VRAM as one that can.**

**Second wrong reading: the top end is 11 dB down.** That is what a plain LTAS
comparison against `rvc_datasets/mara/` says, but the corpus average includes
fricative frames and the render has none. Splitting both sides into sonorant
and fricative frames (>70% of frame energy below 1 kHz) and comparing like with
like drops the deficit to 3-5 dB and exposes what the biased comparison hid: a
**+3 to +4 dB bump at 500-2000 Hz**, the boxy/nasal "TTS honk", which is the
most audible difference from the game rips.

The chain that follows from the corrected measurement is four bells and a
highpass, no compression and no reverb. Compression because the render is
already flatter than the corpus over active speech (12.2 dB crest against 16.7,
IQR 15.2-17.8) so it would widen the gap; reverb because Wwise applies dialogue
space per bus at runtime and the shipped assets are dry, so baked reverb gets
applied twice. Level matches the corpus mean peak of -3.0 dBFS by peak, not by
`loudnorm`, for the reason already recorded in `vo_dataset.py`: R128 is a
dynamic normaliser and would flatten what is being preserved.

Measured after, at strength 1.0: the midrange bump falls from +3.1/+4.2 to
+1.2/+0.4, the 5-16 kHz deficit from -3.2/-4.2 to -1.8, peak lands on -3.0 dBFS.

Everything dynamic here is provisional. Crest, RMS and LRA taken from 1.6 s of
one word are not meaningful - a single syllable cannot show the stressed and
unstressed span of a sentence - and the docstring says so. The spectral finding
is frame-matched and stands; the dynamics finding needs a real line. The next
audition line should be short enough for the VRAM budget but phonetically
complete, carrying /s/, /S/, /t/ and /k/, so the top octave is actually
exercised.

`--measure` re-derives the whole table from the corpus, so none of the
constants are magic numbers. `--strength` defaults to 0.75 because full
EQ-matching normally overshoots; 0.5 / 0.75 / 1.0 renders were left beside the
input for the player to choose by ear. Nothing in the tool touches the network.

## D56 - The three-strength audition was not a test, and the user's ear was right (2026-09-09)

The user listened to `tts_rvc_polish_{0.5,0.75,1.0}.wav` and reported all three
sounded identical, wondering whether they lacked the ear for it. They did not.
The files are the same file everywhere the test word has energy, and measurement
says so three separate ways.

**1. The word has no content where the knob acts.** Energy distribution of
`tts_rvc_output.wav` over its loudest window:

    0-250 Hz    28.7 %        2000-5000 Hz    1.46 %
    250-500 Hz  26.9 %        5000-8000 Hz    0.20 %   (-27 dB)
    500-2000 Hz 42.7 %        8000-16000 Hz   0.07 %   (-31 dB)

98.3 % of "Hello" lives below 2 kHz. The band where the strength knob has its
largest effect - 5 kHz up, a 1.9 dB spread - carries 0.27 % of the signal.
Moving something 27 dB down by 2 dB changes the total by about 0.005 dB.

**2. Where the word does live, the knob was cancelled by the make-up gain.**
Measured 500-2000 Hz change from strength 0.5 to 1.0: **-0.09 dB**. The chain
cuts more midrange at higher strength, which lowers the peak, which makes
peak-matching to -3.0 dBFS hand back a larger make-up gain. The two effects
very nearly cancel in exactly the band the correction exists to fix.

**3. The nominal gains overstate the real curve.** White noise through each
chain, no make-up gain:

              0.5     0.75    1.0    spread
     350 Hz  +0.87   +1.31  +1.75    0.88
     900 Hz  -0.87   -1.29  -1.72    0.86
    1200 Hz  -1.37   -2.04  -2.73    1.36
    2600 Hz  +1.02   +1.53  +2.04    1.02
    9000 Hz  +1.92   +2.88  +3.85    1.92

At strength 1.0 the 1200 Hz bell is written as -3.5 dB and delivers -2.73: the
wide +2.0 bell at 350 and the +3.0 bell at 2600 overlap it and fill part of it
back. Adjacent bells do not add independently, so a chain's real curve is always
gentler than its parameter list. Read the sweep, never the parameters.

### What changed

`vo_polish.py` gained `--match {peak,rms}`. Peak-matching to -3.0 dBFS stays the
default and is correct for a delivered asset - every file in `rvc_datasets/mara`
is peak-normalised to exactly -3.0. It is wrong for an A/B, because the EQ moves
the peak and each variant is therefore re-gained by a different amount.
`--match rms` pins speech-only RMS to -20.75 dBFS instead (corpus mean -20.61,
median -20.75, IQR -21.60..-19.30 over 60 clips, silence stripped at -45 dBFS).

That fix helps and does not rescue the test: RMS-matched, the 0.5-to-1.0
midrange difference rises from -0.09 dB to -0.69 dB. Still under one JND. The
conclusion is that **the strength knob cannot be auditioned on a single sonorant
word at all**, at any level-matching. It needs real material.

### Three replacement files, each asking one question

Built RMS-matched to the game's own speech level so loudness cannot stand in for
the difference:

- `mara_ab_polish.wav` - raw, polished, raw, polished. Does the shipping chain
  do anything audible on this word? Expected answer: barely.
- `mara_vs_game.wav` - a real Rogue line, the polished render, a second real
  line chosen for sibilance (12 % of energy above 5 kHz against the corpus
  typical 2-4 %). This is the question the user actually asked: is it like the
  game.
- `mara_polish_exaggerated.wav` - the same axis at 4x, not for shipping. A
  direction-finder. If this one is also inaudible, the playback chain is what is
  hiding the difference, not the chain under test.

### The lesson

I shipped three variants of a correction and asked for a verdict without first
checking whether the difference was above threshold on the material being
judged. Two minutes of measurement would have shown it was not. An A/B whose
two sides are provably within a JND is not a test the listener can fail - it is
a test the author failed to design. Measure the difference before asking anyone
to hear it.

## D57 - descpanel.py is a build gate, and the mutation that proves it is not the obvious one (2026-09-09)

`descpanel.py` was held out of `build.sh` while it exited 1 on the shipped
graph. D54 fixed that, so it goes in - but D54's own lesson was that a check
which cannot fail is indistinguishable from one that passes, so it was mutation
tested first.

**The obvious mutation is wrong.** Deleting a `desc_*_off` node and its links
leaves the gate green, 8/8. That looked like proof the gate was hollow. It is
not: D54 did not *add* eight nodes, it **spliced** them into existing edges.

    before   obj_dogtown_done ----------------------> obj_room_on:Active
    after    obj_dogtown_done -> desc_goto_dogtown_off -> obj_room_on:Active
                                 (entered on Inactive)

Deleting one severs the quest. The playthrough dies at that objective, no later
description ever activates, and peak simultaneous descriptions is 1 because
nothing happens. A green result meaning "the quest is dead" reads exactly like
a green result meaning "the quest is correct".

**The mutation that tests D54** is to delete the node *and restore the edge it
was spliced into* - a true revert of one splice. That is caught 8/8, every one
of them putting a park back to 2 paragraphs. `desc_talk_mara_off` bypassed leaks
the Mara paragraph into 8 later parks including all four endings;
`desc_decide_off` leaks into all four endings. The pre-D54 graph run through the
same tool reports peak 9, rc=1. D54 is verified, and every one of its eight
nodes is load-bearing.

### What the severed-graph experiment exposed

Run standalone on a severed graph, `descpanel.py` prints "peak simultaneous
descriptions: 1" and exits 0. That is how D54 was verified last night, and it
would have said the same thing about a quest that could not be completed. Across
the suite the hole is covered - `replaytest.py` catches it (`decide_int_tier
NEVER FIRES`) while `validate.py` and `shapetest.py` also miss it - so
`descpanel.py` is wired in **after** `replaytest.py` and the ordering is now
load-bearing. Recorded in the build.sh comment so it is not reordered.

### Two descriptions render at no park, and that is not a bug in the graph

Every description defined must be visible somewhere, or it is authored text the
player never reads. Measured: 12 defined, 10 rendered, 2 never - `ac_obj_talk_mara`
and `ac_obj_decide`. Both activate immediately before a scene node and retire
when the scene ends, and the replay parks at waits, not inside scenes. So the
tool cannot see them either way, and the count is a property of where scenes sit
in the graph rather than of correctness.

It is therefore **reported and not asserted**. On the severed graph the same
number is 11, so the list is still a strong smell - but the gate for that is
replaytest, not this.

**Open question for the user, not a defect:** if those two paragraphs are only
ever on screen during a cutscene, when the journal is closed, they may be
unreadable in normal play. Worth deciding whether either objective should hold a
beat with the description up before it closes.

## D58 - The model's own eval renders settle what "Hello" could not, and correct D55 twice (2026-09-09)

D55 closed with an explicit caveat: every dynamics number came from 1.6 s of one
word and needed re-measuring on a full line. That did not need the GPU. Applio
logs its eval audio into the tensorboard event file, and by epoch 140 there are
**14 embedded WAVs, one per 10 epochs, 34.9 s each at 48 kHz** - continuous
speech with fricatives, extractable read-only by scanning for RIFF headers while
the trainer keeps appending. Free full-sentence material, and a free
epoch-by-epoch history.

**Method note that matters.** Raw band deltas against the corpus are not
level-matched, so a uniformly quieter render reads as deficient everywhere. Every
figure below has each row's own mean offset removed, leaving shape only.

### The midrange bump is the model's, not only the TTS source

Level-matched sonorant deltas vs `rvc_datasets/mara`, 500-2000 Hz:

    ep010 +2.9   ep050 +2.7   ep090 +1.8   ep130 +2.8
    ep020 +3.1   ep060 +2.8   ep100 +2.3   ep140 +2.4
    ep030 +4.4   ep070 +3.0   ep110 +2.8
    ep040 +3.3   ep080 +2.6   ep120 +2.5      tts_rvc_output +4.8

Present in **every** epoch at +2.4 to +3.1 dB. D55 attributed the bump to the
render and tuned for +3/+4; it is structural in the model, and edge-tts adds
roughly another +2.3 dB on top of it. Same story at the top: 5-16 kHz sits
-1.6 to -3.4 dB in every epoch, improving with training.

### Correction to D55: the crest reading flips a third time, and this one holds

Measured over active speech on 35 s of continuous sentences, ~500 frames per
render: **model 20.0-21.3 dB crest against the corpus 18.1 dB**. The model output
is about 2 dB *more* dynamic than the game, not 4.5 dB flatter as D55 recorded.
That earlier figure came from 12 frames of a single word.

Three readings, one right: whole-file (wrong - silence inflates it), 1.6 s word
(unreliable - no stressed/unstressed span), full sentences (trustworthy). The
absolute numbers are method-dependent - this measurement puts the corpus at
18.1 dB where D55's frame definition put it at 16.7 - so only compare within a
method. **No compression either way**, which is now the third distinct reason
that conclusion has survived.

### Training has plateaued, and this is the actionable part

RMS distance from the corpus shape, all four bands:

    ep010 2.14   ep050 1.88   ep090 1.23   ep130 1.76
    ep020 1.91   ep060 1.96   ep100 1.47   ep140 1.62
    ep030 2.81   ep070 1.89   ep110 1.69
    ep040 2.09   ep080 1.79   ep120 1.74

Falls sharply to ~epoch 90 then flattens into noise. `lowest_value` agrees on the
same region: 13.837 at epoch 120, unbeaten since. **Past roughly epoch 120-150
more training buys very little spectrally** - the script's 300-epoch default is
about twelve further hours of GPU for changes inside the run-to-run scatter. The
gap that remains is structural, which is exactly what `vo_polish.py` is for.

Also: the 70-epoch model the user auditioned is within 0.2-0.3 dB of epoch 140
on every band. A better checkpoint will not fix the voice character.

### Known limitation in vo_polish.py, not yet fixed

The chain's midrange cut and treble boost are in a 1:1 ratio (-3.5 / +3.5
nominal). The measured defect ratio is 2.5 : 2.2 for the model alone - near
enough - but **4.8 : 2.0 for the TTS-sourced render**, so on that pipeline no
single strength can correct both: midrange wants s~1.8, treble wants s~0.5.
Fixing this properly means having `--measure` emit recommended gains instead of
the table being hand-carried. Recorded, not done.

### Caveat on all of it

Eval renders are the model reconstructing its own training audio, not converting
a TTS voice. They show the model's ceiling and its spectral character; they are
not the user's actual pipeline. The +4.8 dB row is.

## D59 - vo_polish.py fits its own gains, and fitting revealed the model needs none (2026-09-09)

D58 recorded a flaw and did not fix it: the band gains were carried in a fixed
1:1 ratio, right for a direct RVC render (defect 2.5 : 2.2) and wrong for a
TTS-sourced one (4.8 : 2.0), where correcting the midrange overshoots the top by
three times. `--fit` removes the ratio from the author's hands.

### How: measure the filters, then solve

Each filter is probed alone with white noise at +6 dB, giving M[band][filter],
the dB it puts into each band per dB of its own gain:

                    350     1200     2600   5500sh
       250-500    0.924    0.095    0.033    0.037
      500-2000    0.215    0.702    0.303   -0.020
     2000-5000    0.013    0.147    0.673    0.020
    5000-16000    0.004    0.013    0.056    0.984

Not an identity matrix, which is the point. The 1200 bell delivers only 0.702 dB
into its own band per dB of gain, while the 350 and 2600 bells inject +0.215 and
+0.303 into it. Setting those to +2 and +3 pushes 1.34 dB *into* the midrange
that the cut must cancel before it removes anything - the entire gap between the
nominal -3.5 and the measured -2.73 from D56. Condition number 2.4, so the
least-squares solve for the wanted correction is stable. Measured at runtime, so
it stays true if the frequencies or widths are ever changed.

Residual RMS against the corpus shape, strength 0.75: TTS render 2.58 -> 0.79 dB,
epoch-140 eval take 1.44 -> 0.60 dB.

### What fitting then exposed, which matters more than the feature

**The target is a distribution, not a point.** Per-clip sonorant shape across 57
corpus clips:

         band      mean    sd    p10    p90   p90-p10
      250-500      16.3   2.4   13.2   19.1     5.9
     500-2000       7.1   3.5    3.2   11.1     7.9
    2000-5000      -4.3   2.1   -7.0   -1.8     5.1
    5000-16000    -19.1   2.6  -22.7  -15.6     7.1

Two real game lines differ from each other by more than any correction worth
applying. **And the render side is no steadier:** the same model on the same
passage, measured on different 10 s windows, gives 500-2000 Hz values of 11.2,
11.2, 9.2, 6.5, 7.3, 8.4 - a 4.7 dB spread. A 10 s excerpt estimates that band
to about +/-2 dB.

That is where a 2 dB disagreement with D58's numbers came from. It was *not* the
averaging method: pooling every corpus frame into one spectrum and averaging
per-clip shapes agree to within 0.5 dB in all four bands, which retroactively
makes D58's figures method-independent. It was excerpt sampling on the render.

So `fit` now prints the corpus sd beside every band, marks any correction
smaller than it `(inside corpus scatter)`, and warns below 300 frames.

### The conclusion that changes what the tool is for

Fitted on the full 34.9 s epoch-140 take, **all four bands come back inside the
corpus scatter**. Fitted on the TTS render, two do not - 500-2000 Hz at -4.3 dB
against a 2.9 dB sd, and 2000-5000 at +2.3 against 2.2.

The RVC model's own output is spectrally within the natural variation of real
Mara dialogue. The measurable defect belongs to the **TTS source**, not the
model. `vo_polish.py` is a correction for the edge-tts front end, and applying it
to direct RVC output is correcting noise.

**Confound, stated plainly.** Eval renders are the model reconstructing its own
training audio. Matching the corpus is partly circular - it shows the
reconstruction is faithful, not that conversion of arbitrary input would land in
the same place. The honest reading is narrower than it first looks: the model is
not *adding* a midrange bump of its own, and the TTS pipeline is.

Both pre-existing paths verified unchanged: the fixed table still produces
+3.40 dB make-up on the same input, and `--measure` is untouched.

## D60 - The pre-RVC TTS file existed, and it settles the attribution by measurement (2026-09-09)

D59 concluded the midrange bump belonged to the TTS front end rather than the
model, but inferred it from two unpaired comparisons. Applio keeps the
intermediate: `assets/audios/tts_output.wav`, 24 kHz, 1.608 s, written the same
minute as `tts_rvc_output.wav`. Same utterance, so this is a **paired**
comparison on identical words - no phonetic mismatch, which has confounded every
corpus comparison in D55 through D59.

All four rows on identical bands, level-matched, capped at 11 kHz because the
TTS source is 24 kHz and an uncapped top band would score the resampler's zeros
as a missing octave:

                          frames  250-500  500-2k   2k-5k  5k-11k
        edge-tts raw          10     -1.3    +4.3    +0.7    -3.8
        after RVC             12     -0.1    +4.4    -2.5    -1.8
        ep140 reconstruction 532     +0.9    +2.0    -0.9    -2.0
        ep070 reconstruction 509     +0.5    +2.6    -1.0    -2.1
        game corpus sd                2.3     3.5     2.2     2.6

### Three things this settles

**The midrange bump is entirely the TTS source.** +4.3 before conversion, +4.4
after: RVC moved it by 0.1 dB. Not inferred any more. It is also the only figure
in the table outside the corpus scatter, and only just - 1.26 sd.

**RVC costs presence, and that is the model's own defect.** 2-5 kHz goes +0.7 ->
-2.5, a 3.2 dB loss in a band edge-tts had almost exactly right. Reconstruction
loses only 0.9 dB there, so conversion of out-of-domain timbre is worse than
reconstruction of training audio - though 1.6 dB on 12 frames is not a claim to
lean on.

**RVC does add top end.** 5-11 kHz recovers from -3.8 to -1.8. Consistent with
the eval renders reaching 15.7 kHz, and the final disproof of the original
"band-limited by the 24 kHz source" reading from D55.

**And the plateau holds on a third independent measurement:** ep070 and ep140
differ by 0.6 dB in the midrange and 0.1 dB in presence. Both well inside
scatter. More epochs are not going to change the voice.

### What this means for the chain

The correction has two separate jobs with two separate owners: cut about 4.4 dB
of midrange that edge-tts puts in, and restore about 2.5 dB of presence that
conversion takes out. That is close to what `--fit` derives unaided (-6.5 at
1200, +4.0 at 2600 at strength 0.75, which after bell interaction lands near
those figures).

Because RVC passes the midrange through untouched, that half could equally be
fixed **before** conversion, or avoided entirely by choosing a TTS voice without
the bump. Cheaper than correcting it downstream, and it is the front end that
would need changing for release anyway - `en-US-AriaNeural` is a Microsoft
network voice, which is what `render_lines.py --allow-network` exists to gate.

**Caveat.** The two TTS rows rest on 10 and 12 sonorant frames. The *delta*
between them is trustworthy because the words are identical; their distance from
the corpus is not. Repeat on a full line before treating the absolute figures as
settled.

### The calming summary

Every number in the table is inside one corpus standard deviation except the
post-RVC midrange, which is 1.26 sd out. The pipeline is already close to real
game dialogue. The largest single improvement available is not more training and
not more EQ - it is a different TTS voice.

## D61 - The Sep 4 chain was measurably broken, and a local TTS beats the network one (2026-09-09)

Two results from trying to replicate D60 on a second voice pair.

### The replication failed, and failing was informative

`rvc_logs/tts_chain/` holds `en_jenny.wav` and `en_jenny_mara.wav` - a second
TTS-to-RVC pair, 6.6 s, 75 sonorant frames against D60's 12. It does not
replicate: RVC there moved 250-500 Hz by **-7.7 dB** and 5-11 kHz by **+8.4 dB**,
landing 3.3 and 2.5 sd outside the corpus, where the Aria pair moved the midrange
by 0.1 dB. Different behaviour entirely.

The files are dated 4 September, before the current fp32 run, and nothing in the
directory records which model made them. So this is not a second sample of the
same thing. Measuring the noise floor says what it is:

                                    speech  floor p90    SNR
        en_jenny raw TTS             -23.6      -60.3   36.8
        en_jenny after RVC (Sep 4)   -27.7      -45.8   18.1
        uk_polina after RVC (Sep 4)  -28.2      -47.4   19.2
        tts_rvc_output (Sep 9, 70e)  -20.9      -84.3   63.5
        ep140 eval (current)         -25.7      -54.1   28.4
        game corpus (20 clips)       -23.9      -60.7   36.8

**That generation destroyed 18.7 dB of SNR in conversion.** The raw TTS matched
the game's own 36.8 dB exactly; the conversion dropped it to 18.1. The user's
report at the time - "there is a lot of noise in the voice" - was accurate, and
this is the number behind it. The current model does not do this.

Two caveats on that table. `tts_rvc_output`'s 63.5 dB is flattered by true
digital silence padding a 1.6 s file, so it overstates. `ep140`'s 28.4 dB against
the corpus 36.8 is the honest figure for continuous speech: **the current model
still raises the noise floor about 8 dB**, an order of magnitude less than the
Sep 4 chain but not nothing.

**D60's central claim therefore remains unreplicated.** The only other pair
available is from a broken generation, so "RVC passes the midrange through
untouched" still rests on 12 frames of one word.

### piper is installed locally, and one of its voices beats edge-tts

`tts_venv/bin/piper` with `en_US-lessac-high` and `en_US-ryan-high` - CPU ONNX,
no GPU, **no network**, so outside what `render_lines.py --allow-network` gates.
Both synthesised the phonetically complete line recommended in D55 ("Six shells,
that is the price. Take it or walk.") in about a second.

Level-matched delta from Mara's dialogue, capped at 10 kHz because piper is
22.05 kHz and edge-tts 24 kHz:

                                    frames  250-500 500-2k  2k-5k 5k-10k   dist
        edge-tts en-US-AriaNeural       10     -1.3   +4.3*  +0.7   -3.7*   2.95
        piper en_US-lessac-high         38     +2.9*  +2.4   -2.1   -3.1*   2.68
        piper en_US-ryan-high           38     -0.5   +2.2   +0.4   -2.0    1.51
        en_jenny (network, Sep 4)       75     +0.1   +3.0   -1.3   -1.8    1.88
        game corpus sd                         2.3    3.5    2.2    2.6
        (* = outside one corpus sd)

**edge-tts Aria is the worst of the four**, and `en_US-ryan-high` is the only one
with every band inside the corpus scatter.

**Do not read that as a recommendation to switch to ryan.** It is a male voice
and Mara is female, so it would need roughly +12 semitones of pitch shift, a
degradation this measurement cannot see. `lessac` is the female local option and
still beats Aria overall. And Aria's row rests on 10 frames of "Hello" against
piper's 38 of a full sentence - the fairest comparison needs Aria re-rendered on
the same line, which needs network.

What the table does support: **the front end is worth changing, the change costs
nothing to try, and it can be done entirely locally.**

## D62 - Ninety epochs of training moved the voice less than one just-noticeable difference (2026-09-09)

The run has now logged eighteen eval renders, one per ten epochs, each the same
34.9 s passage at ~520 sonorant frames - well above the 300-frame floor D59 set
after excerpt sampling turned out to be worth 4.7 dB. Extracting all of them and
measuring level-matched band shape against a 40-clip corpus reference gives the
first picture of the whole run rather than of two endpoints.

              epoch  250-500  500-2k  2k-5k  5k-16k   dist   SNR
                010    +0.39   +2.44  -0.09   -2.74   1.84  23.7
                060    +1.09   +2.32  -1.10   -2.32   1.81  31.2
                090    +0.70   +1.29  -0.62   -1.36   1.05  27.2
                120    +0.61   +1.99  -0.47   -2.13   1.50  29.4
                140    +0.75   +1.88  -0.76   -1.87   1.43  29.3
                170    +0.80   +2.04  -1.05   -1.79   1.51  28.2
                180    -0.15   +3.14  -0.99   -2.01   1.93  25.9
       corpus sd        2.27    2.72   2.01    2.25         40.8

Two things fall out, and the second is the one that decides the run.

**The epoch-to-epoch jitter is the error bar, and it swallows the trend.** Every
adjacent pair differs by 0.35-1.10 dB. The best and worst distances across
epochs 090-180 are 1.05 and 1.93 - a spread no larger than the jitter between
two consecutive checkpoints. Differencing each epoch against ep090 directly,
after level-matching the pair, makes it plain:

              vs ep090  250-500  500-2k  2k-5k  5k-16k  max|d|
                 ep100    -0.27   +0.54  -0.21   -0.05    0.54
                 ep120    -0.09   +0.70  +0.15   -0.76    0.76
                 ep140    +0.05   +0.59  -0.14   -0.51    0.59
                 ep160    -0.38   +1.06  -0.15   -0.54    1.06
                 ep170    +0.10   +0.76  -0.43   -0.42    0.76
                 ep180    -0.85   +1.86  -0.36   -0.65    1.86

A broadband tilt needs roughly 1 dB to be heard and a single band in speech
closer to 1.5-2. Epochs 090 through 170 sit at or under that line against each
other. Ninety epochs - seven hours of GPU - produced changes at the threshold of
audibility. D56's rule applies to the training run itself: this is not an
audition, and building an A/B of ep120 against ep170 would repeat the mistake of
asking someone to hear something that is not there.

**Epoch 180 is the first to move meaningfully, and it moved the wrong way.**
+1.86 dB of midrange against ep090, landing at +3.14 against the corpus - the
worst midrange of the entire run bar ep030, with 3.5 dB less SNR than ep120.
One point is not a trend and the next few epochs may pull it back. But nothing
after ~090 has been better, the loss minimum has stood unbeaten since epoch 120,
and there is now no measurement pointing at a reason to continue.

The loss minimum (120) and the spectral minimum (090) disagree, which is itself
the finding: they are 0.76 dB apart, so they do not actually disagree about
anything audible. `mara_120e_15720s.pth` is on disk and is the defensible stop.

**A hazard found while checking that the checkpoints exist.** Weights are named
`mara_<epoch>e_<step>s.pth`, and step count is a deterministic function of epoch
at 131 steps/epoch, so the current run regenerates the *exact filenames* of the
broken fp16 run from 6 September. Two of that run's files still survived -
`mara_10e_1310s.pth` and `mara_200e_26200s.pth` - and the second is the model
the user actually listened to and approved ("on this damaged fp16 mara 200 epoch
model audio Okay, good"). Reaching epoch 200 would have silently overwritten the
only copy of the one checkpoint with a human verdict attached, and destroyed
half of the pending 10e-vs-200e A/B. Both are copied to
`old-fp16-2026-09-06_*.pth` (110 MB). Why the run's own epoch-10 save did not
already clobber the first one is unexplained; the copy does not depend on the
answer.

### D62 correction - the collision runs the other way, and it had already fired

The hazard above is stated backwards. `rvc/train/train.py:1123` guards every
weight write with `if not os.path.exists(m)`. **Applio never overwrites an
existing weights file - it silently skips the save.**

So `mara_200e_26200s.pth` was never at risk; the copy was harmless but the
reason given for it was wrong. The real problem is the one that explains the
loose end D62 admitted it could not account for. This run *did* reach epoch 10,
found 6 September's file sitting on the name, and skipped its own save. The
consequence is worse than an overwrite would have been:

- `mara_10e_1310s.pth` in `logs/mara/` was **not from this run**. It was the
  broken fp16 model wearing the fp32 run's naming, indistinguishable by name and
  distinguishable only by mtime. The pending 10e-vs-200e A/B would have compared
  two damaged checkpoints and been reported as old-versus-new.
- At epoch 200 the same thing would have happened again, and a later request for
  "the 200-epoch fp32 model" would have returned the fp16 one.

Both files are now moved to `old-fp16-2026-09-06_*.pth` with their original
mtimes intact, freeing the names. `logs/mara/` now holds exactly eighteen
checkpoints, all from this run.

The generalisable point: a silent skip is harder to detect than a clobber. An
overwrite leaves a file with a fresh mtime and consistent contents; a skip
leaves a stale file that is wrong in a way nothing in the filename records.
`ls` cannot show it. Only `ls --time-style` next to a known run-start time can.

### D62 addendum - epoch 190 partially reverts, but the drift is now two points

              epoch  250-500  500-2k  2k-5k  5k-16k   dist   SNR  vs ep090
                090    +0.70   +1.29  -0.62   -1.36   1.05  27.2     0.00
                170    +0.80   +2.04  -1.05   -1.79   1.51  28.2     0.76
                180    -0.15   +3.14  -0.99   -2.01   1.93  25.9     1.86
                190    +0.13   +2.72  -0.77   -2.08   1.76  28.0     1.44

SNR recovers (25.9 to 28.0), so ep180's noise-floor dip was jitter. The midrange
does not recover: ep180 and ep190 are the two largest departures from ep090 in
the whole run, both in the same direction and both away from the corpus, where
every epoch from 090 to 170 stayed at or under 1.06 dB. Two points is still not
a trend, but it is no longer a single outlier, and the direction is the wrong
one. Nothing here changes D62's conclusion; it removes the caveat that the
conclusion rested on one measurement.

### D62 addendum 2 - epoch 200 reverts too, so the "drift" was jitter after all (2026-09-09)

The run was stopped at epoch 200 on the user's instruction ("I don't see the
point in learning the model further"). It had been launched `--epochs 300`, so
this ended it 100 epochs early - about 7h42m of GPU.

Epoch 200's eval render measures dist 1.56, SNR 28.3, which puts it back beside
ep120 (1.50) and ep170 (1.51). Epochs 180 (1.93) and 190 (1.76) were the two
largest departures of the run and I called them "two points, not a trend but no
longer one outlier". Epoch 200 says they were jitter. **The addendum above
over-read them; there is no drift.** Adjacent-epoch jitter was already measured
at 0.35-1.10 dB, and 180/190 sit inside that once a third point exists.

Level-matched, ep200 vs ep120 is max 0.55 dB across all four bands and ep200 vs
ep090 is 0.89 dB - both under the ~1 dB JND for a broadband spectral tilt. So
every epoch from 090 to 200 is mutually indistinguishable, and the last 80
epochs bought nothing measurable.

Checkpoint to use: `mara_120e_15720s.pth`. It holds the loss minimum (13.837,
never beaten in the 80 epochs after it) and the best noise floor (SNR 29.4 vs
28.3). Both margins are at or under JND, so `mara_200e_26200s.pth` is an equally
defensible pick - this is a coin toss, not a quality gap.

Epoch 200 is also the save that would have been silently skipped: before the
files were renamed, 6 September's fp16 model occupied `mara_200e_26200s.pth`.
The new file is 57532660 bytes at 10:45:38, the same size as 190e and with a
fresh mtime, so it is genuinely this run's.

**Method caveat, disclosed late.** Corpus SNR is quoted as 36.8 dB in earlier
windows (20 clips, frames pooled across clips) and 40.8 dB here (40 clips, mean
of per-clip SNRs). That is a change of method, not of data. Compare figures only
within one method; the per-epoch SNR column is internally consistent throughout.

## D63 - The voice is signed off by ear, so the registry stops calling Mara a stand-in (2026-09-09)

**The decision:** `mara_200e_26200s.pth` is Mara's voice. Not provisionally, not as a
placeholder - `reference/rvc_voices.json` now says `VERIFIED` and the renderer stops
warning on every line.

**What actually decided it.** Not a number. At 10:52 the user loaded the checkpoint into
Applio's TTS tab, rendered a 12.4 s line through edge-tts, listened, and said the voice is
"normal and suitable". That file is `/mnt/ssd/Downloads/tts_rvc_output(1).wav`, byte-identical
to `/mnt/sata/Applio/assets/audios/tts_rvc_output.wav` (10:56:39), and the checkpoint's atime
(10:52:45, updated because the previous atime predated a mtime written eleven minutes earlier)
identifies which `.pth` was loaded. Every earlier attempt to settle this question by
measurement - D58, D60, D61, D62 and its two addenda - produced numbers under the JND and
therefore could not decide anything. One person listening for twelve seconds could.

**The measurement that was still worth having.** `tools/rvc_check_model.py mara` passes:
0.00% clipped, p95 -11.3 dB, silence floor -42.1 dB, hf8k 0.07%. Set against the fp16 model's
100% clipped and -0.1 dB in silent frames (D36), this is the opposite corner of the space. The
gate cannot tell a good voice from a bad one; it can only tell a working generator from a
railed one, and that is exactly what was in doubt after 6 September. It earned its place by
being cheap and by failing loudly the last time.

**Epoch 200 over epoch 120, and why not to revisit it.** 120 holds the loss minimum (13.837,
unbeaten across the 80 epochs that followed) and the better noise floor (SNR 29.4 vs 28.3).
D62 addendum 2 measured every pair from 090 to 200 as differing by at most ~1 dB of band shape,
at or under JND. The user listened to 200 and approved 200. A 0.55 dB argument does not
outrank that, and swapping the file now would mean shipping a checkpoint nobody has heard.

**Provenance, because the filename is not evidence.** `torch.load` reports
`creation_date = 2026-09-09T10:45:38.675607` from inside the checkpoint, `epoch = 200`,
`step = 26200`, `sr = 48000`, `version = v2`, `vocoder = HiFi-GAN`, `f0 = True`.
sha256 `b13ed637...cdc210`, 57,532,660 bytes. This matters because a file of the same name
existed from the failed 6 September fp16 run, and Applio's save is `if not os.path.exists(m)`
(`rvc/train/train.py:1123`) - it skips rather than overwrites. Had that file not been renamed
to `old-fp16-2026-09-06_*` first, this save would have been silently discarded and today's
listening test would have been run on the broken model. The rename also drops those files out
of the registry glob `mara_*e_*s.pth`; do not rename them back.

**Historical keys kept, renamed.** The fp16 post-mortem in the registry (`_broken_how`,
`_why_it_is_only_110_epochs`, `_open`, `_retrain`) is now prefixed `_history_2026_09_06_fp16_`.
It stays because the fp16 NaN root cause is genuinely reusable knowledge; it is renamed because
a reader skimming the entry must not mistake a post-mortem for the current state.

**Still open: which TTS front end ships.** The user approved a chain whose first stage is
edge-tts, a Microsoft network service. `render_lines.py` refuses `--tts edge` without
`--allow-network` (D61), and that gate is about where the quest's script goes, not about
audio quality - one line typed into a UI by the person who wrote it is a different act from
43 lines posted by a script. The local piper pass is rendered to
`rvc_logs/audition/piper-mara200e/` for comparison. The decision belongs to the user.

## D64 - The audition is the shipped voiceover, piper included, pitch collision and all (2026-09-09)

**The decision:** the 43-line piper render is now `vo/en-us/`. The user listened to it, said
"I like everything and it suits me", and that ends three questions at once: which checkpoint
(mara 200e, already settled in D63), which TTS front end (piper, local), and whether the
V/Rogue pitch overlap measured below is worth fixing (it is not).

**What moved.** 43 `.wav` copied from `rvc_logs/audition/piper-mara200e/en-us/` into
`vo/en-us/`. Nothing was renamed on the way in: every stem already matched a key in
`source/subtitle_ids.json`, 43 for 43, which is the check `validate.py` would have failed on
otherwise. `tools/build.sh` then did the rest by itself - `wav_to_wem.py` wrote 43 Wwise-PCM
`.wem` beside the sources, `gen_vomap.py` read the `.wem` (not the `.wav`, and not any list in
`source/`) and emitted a 43-entry `locVoiceoverMap`. The archive went from silent to
13,996,032 bytes. `validate.py` reports "43 voiced line file(s) (+43 awaiting conversion)" -
the second number is the `.wav` sources sitting next to their `.wem`, which is what the drop
folder is supposed to look like, not work outstanding. negtest 96/96.

**The network question is closed by not arising.** D63 left "which TTS front end ships" open
because the approved chain began with edge-tts, and `render_lines.py` refuses `--tts edge`
without `--allow-network`. The file the user approved today was rendered by piper, locally.
So no quest line has left this machine, the gate never had to be argued about, and `--tts edge`
stays behind its flag. If the user later prefers the edge read, that is a new decision and a
new consent, not a resumption of this one.

**The defect that was measured, reported, and knowingly accepted.** pYIN over all 43 renders:
Mara occupies 175-211 Hz (median 191, tight); V occupies 113-235 Hz (median 155) but the spread
is perfectly scene-correlated - V's 16 lines in `scene_decision.json` sit at 112-171 Hz, his 9
inside `scene_mara.json` at 154-235 Hz, i.e. on top of Mara's band. Measuring the TTS inputs
placed the cause upstream of RVC: piper's `en_US-ryan-high` lifts short interrogatives ("And
you?", "What's your cut in this?") by ~50 Hz, and RVC at `pitch=0` passes the contour through
faithfully. So in that one conversation the two speakers share a pitch and only timbre
separates them.

The fix was verified to exist before it was proposed: Applio's `proposed_pitch` computes
`up_key = clamp(round(12*log2(threshold/median_f0)), +-12)` per clip
(`rvc/infer/pipeline.py:250`), and the 155-male/255-female convention is its own docstring
(line 220). `render_lines.py` already passes `proposed_pitch_threshold=155.0` with
`proposed_pitch=False`, so the value has always been inert. A four-line test plus a control
(`wk_scratch/pitchfix.py`, output in `wk_scratch/pitchfix/`) gave: `mara.trust_3` 235->167,
`mara.opt_hostile` 182->161, `decision.opt_destroy` 156->154 (the control, correctly left
alone), but `mara.opt_level` 192->188 and `mara.opt_price` 205->195, both still inside Mara's
band. Applio takes its median over the f0 curve interpolated across unvoiced frames, which
drags the median down on clips that are mostly pause and under-reads how high the voiced parts
are. So the fix was partial, it was reported as partial, and the user accepted the audio as it
stands. `render_lines.py` is unmodified. If this is ever revisited, the flag must be per-voice:
Mara at threshold 255 would be shifted up ~5 semitones, changing the voice signed off in D63.

**Registry counts corrected while here.** `reference/rvc_voices.json` said `male_v` covers
"11 of the 29 scene lines" and `mara` "18 of the 29". Both predate `lines_of()` counting
`"options"` as well as `"lines"`. The true split is 25 and 18 of 43. The old numbers were the
reason the render looked wrong at first glance - that, and the filename prefix being the
scene stem rather than the speaker, so nine files named `mara.*` are V talking in Mara's scene.

**Addendum, same day: the promote checks were run after the copy, not before.** I copied the
43 files with `shutil.copyfile` and only then noticed `tools/vo_promote.py`, which exists
precisely to stop that. Running it `--dry-run` against the same batch afterwards gives the
verdict the copy should have had first: 43 files covering 43/43 lines, clip max 0.00%,
hf 0.13-2.04%, worst gap-vs-source +4.3 dB against a +6.0 limit over the 18 lines that have
real silence to judge. All 43 in `vo/en-us/` are byte-identical to the audition sources, and
every `.wem` is newer than its `.wav`, so the stale-`.wem` race the tool's header warns about
did not occur - the build wrote them after the copy, which is the order that tool enforces.
The result is right; the route to it was not. Use `vo_promote.py` next time.

## D65 — The quest was never empty; the rooms were   (2026-09-09)

Four screenshots from a real playthrough: the journal renders the vanilla way,
in Ukrainian, with title, description paragraph and objective list; the incognito
SMS arrives and reads correctly; the objectives advance from the motel to the
clinic on their own. And in room 7 there is a quest marker on the floor with
nothing under it, and at the clinic there is nothing to open. The player's words
were "the quest is like an empty quest".

That is an accurate report of what was authored. `source/world.json` gave both
quest sectors **markers only** — `worldStaticMarkerNode`, "no mesh, no entity",
by its own comment. The graph ran over an empty room and stopped at `await_box`,
a `pause_fact` on `ashcache_box_opened`, which `glue.json` had listed as blocked
since D9 because nothing in the world could set it. Every layer was working. The
world was the layer nobody had built.

### The mechanism was already there and had never been wired

`gen_questphase.build_condition` has accepted
`{"interaction": "#node", "event": "Executed"}` since the sector survey, emitting
`questInteraction_ConditionType` — "the player used a placed prop", the same two
fields vanilla writes. It had zero uses in the graph. `props` (`worldEntityNode`)
has been a supported world kind since D15 and had exactly one instance, a probe.
So the gap between "empty quest" and "playable quest" was not a capability and
not a design question. It was two entries in `world.json` and two nodes in the
graph.

    await_box       pause  any[ interaction #ac_splinter_box , fact box_opened ]
    box_opened_set  set_fact ashcache_box_opened = 1
    await_terminal  pause  any[ interaction #ac_terminal_pc  , fact terminal_read ]
    terminal_read_set  set_fact ashcache_terminal_read = 1

**Why the fact stays in the OR.** Two reasons, both real. The CET panel's Acts
tab sets these facts to skip a beat, and that has to keep working. And if the
prop turns out to offer no prompt, this node is the difference between a quest
that can be walked past and one that is stuck at act 3 with no way forward.
**Why the `set_fact` after it.** A `worldEntityNode` cannot write a quest fact.
The interaction released the pause; the fact is what records that it happened,
for the dev report, the glue's stage arming, and any later save that resumes
behind this point.

`ac_splinter_case` and `ac_clinic_terminal` stay markers, because the journal map
pins point at them (`ac_pin_splinter`, `ac_pin_terminal`, `ac_pin_decide`). The
props are separate nodes at the same coordinates: two ids, one point, one job
each — the pin's origin, and the thing the player touches. Neither position is a
new one to stand on; both are inherited from markers already verified in game.

### The model is a placeholder and the mechanism is not

Both props are `computer_1.ent` with appearance `computer_computer_2_angle_15`,
which is the one entity this project has watched render in this exact room
(D46, `sc_ac_probe_computer.jpg` — lit screen, drawing a UI). For the terminal
that is the right object outright; `glue.json` asked for "an interactable
computer at #ac_clinic_terminal" and this is it. For the black box it is
deliberately the *same* object, because the open half of OI-13 is a
single-variable question — does a device `.ent` placed as a `worldEntityNode`
with `instanceData: null` offer an interaction prompt, or only a lit screen —
and putting an unproven model at one of the two nodes would confound it. If a
prompt appears, the box's model is a one-line swap.

A real lootable container is a different and much larger thing, and it was worth
measuring before choosing not to build it. Vanilla makes one from a visible crate
entity **plus** a `worldDeviceNode` access point carrying a ~200-field
`instanceData` RedPackage and a `deviceConnections` entry naming
`LootContainerAccessPointControllerPS` (`quest_e495c59e9949e75b`, six such nodes).
Undermine does exactly the same with its own `.ent` files
(`uqs_airdrop_01.streamingsector`: one `worldEntityNode` for the crate, two
`worldDeviceNode` access points, all three with buffers). `gen_sector.py` emits
neither `worldDeviceNode` nor `instanceData`. That road is only worth paving if
these props turn out inert.

Depot paths checked against `depot_files.txt` rather than guessed by analogy:
`base\gameplay\devices\masters\loot_container_access_point\loot_container_access_point.ent`
and `..._airdrop.ent` both exist, and the *visible* airdrop crate is a separate
asset in `ep1\openworld\sandbox_activities\air_drop_assets\`. The access point is
the interaction, not the object.

### A validation gap the change walked straight into

`validate.py` collected the NodeRef namespace from markers only —
`if kind == "marker": defined[mid] = sid` — four lines under a comment saying all
four kinds share one namespace. So a condition pointing at a prop that really
exists failed as if the prop had been misspelt:

    graph node 'await_box' references NodeRef '#ac_splinter_box' that no world
    node defines

This was invisible while no graph node addressed anything but a marker, and it
would have hit the first `spawned`/`killed` condition on the cleanup crew too.
Fixed to record every kind. It needs no negtest case of its own: the build is the
positive control, because `validate.py` now exits non-zero the moment that line
regresses.

`replaytest.py` also could not evaluate the new condition and said so rather than
guessing. It now treats `interaction` the way it treats `delay` — the player
eventually presses it — with the limit written down: a prop that offers no prompt
at all is invisible to every headless check in this repo. That is precisely what
the fact in the OR is for.

One negtest case moved: "a blocked fact dropped from the list without being
implemented" popped `ashcache_box_opened`, which is no longer on the list. It
pops `ashcache_cabinet_opened` now, which the graph waits on and nothing sets.

### Where the quest stands

Blocked facts: four before, two now — `cabinet_opened` (optional, needs a lock)
and `cleanup_done` (needs the FIA encounter; the spawner half is answered, D46).
Verified: `validate.py` OK (106 graph nodes, 3 props), `negtest.py` 96/96,
`shapetest.py` 31 types round-tripped, `replaytest.py` clean, `build.sh` clean.
Nothing is deployed by this entry.

**The `phase_revision` bump stops being optional here.** The graph gained two
nodes and the generator numbers ids by position, so a save holding the old phase
holds ids that no longer mean the same thing. The four `guard_*` re-entry nodes
(D50) exist to make the bump safe; this is the change they were built for.


## D66 — Subtitles, no sound: everything on the voiceover path checks out except the codec (2026-09-09)

The player walked to the clinic door on the D65 build and Mara talked. Three
frames of her, in Ukrainian, correctly attributed, correctly timed, one after
the other — and *"i didn't hear any sound for the entire time i was standing by
the door."* The shard renders too (`sc_book.png`): "ЩОДЕННИК – М. ВОСС", five
paragraphs, vanilla shard chrome down to the **Toggle Audio** button.

So the scene runs. Only the voice is missing, which is the one thing OI-16 said
might be missing, in the one way it said it would fail.

### Every other link, checked rather than assumed

Silence is this project's signature failure — nothing logs it — so the whole
chain was walked before touching anything.

| Link | Evidence |
|---|---|
| The `.xl` declares the map | `localization.vomaps.en-us` → `mod\ash_cache\localization\en-us\vo\ash_cache_vo.json` |
| ArchiveXL merged it | `ArchiveXL-2026-09-09-12-26-49.log:1092` — *"Merging entries from …ash_cache_vo.json"*, no error beside it |
| It merged into the right language | `OnLoadVoiceOvers` walks `locVoLanguageDataMap` and matches `entry.languageCode` against our keys — only the `en-us` entry takes ours |
| The player is on that language | `UserSettings.json` `/language`: **VoiceOver `en-us`**, Subtitles `ua-ua`, OnScreen `ua-ua` — exactly D42's design |
| The keys match | all 43 `locVoLineEntry.stringId` are byte-equal to the `.scene`'s `scnscreenplayDialogLine.locstringId.ruid` (`7731500000000000000`…) |
| The same keys already work | those ruids are what the subtitle the player is reading resolves through |
| The audio is where the map says | all 43 `resPath`s resolve to files in the staging tree and the packed archive |
| The scene asks for voice | `scnDialogLineEvent.voParams`: `voContext Vo_Context_Quest`, `voExpression Vo_Expression_Spoken`, `customVoEvent None` |

Eight links, all sound. The ninth is the codec, and it is the one that was
never proven.

### What the codec census actually sampled

`tools/wav_to_wem.py` writes PCM because 127 shipped `.wem` files and 116 in
LizziesBDs are PCM — a real census, and a fair reason to try. But every one of
those lives under `base\sound\soundbanks\media`: **bank media, resident, loaded
as bank data**. The voiceover path is a different reader — external sources
streamed by resource path — and it has a different diet:

- vanilla `base\localization\en-us\vo\*.wem`: **110,495 lines, Custom Vorbis, zero PCM**
- 24 installed mods shipping a `vomap`: **342 lines, Vorbis, zero PCM**
- Kidnap's 23, measured here byte by byte: `fmt` tag `0xFFFF`, `fmt` size 0x42

A format tag the bank reader understands is not automatically one the
external-source reader accepts, and 110,837 examples now say which way this
goes. The tool's own header called this exactly: *"'should' is not 'does'"*.

### The control, because eight verified links do not add up to a proof

One line swapped to a known-good Vorbis `.wem` and nothing else touched:

    vo/en-us/mara.mara_open_1.wem     <- sq_kidnap_mitch_holo_mitch_phrase_1  (5.387 s vs 5.400 s)
    vo/en-us/decision.dec_open_1.wem  <- sq_kidnap_mitch_holo_mitch_phrase_5  (3.677 s vs 3.620 s)

Both borrowed from the installed Kidnap mod under **our** depot paths, so
nothing of Kidnap's is overwritten and no hash collides. The originals are in
`diag/d66_vo_control/` with the undo commands; this build must not ship.

Two lines rather than one, because they cost the player different things.
`mara.mara_open_1` needs the Mara scene replayed — clear
`ashcache_mara_choice_made` (the `guard_meet_mara` condition) and re-enter the
phase. `decision.dec_open_1` opens the scene the player has **not reached yet**,
so it answers the same question by just playing on. Whichever comes first wins.

    a voice, wrong words   -> the path is fine, PCM is the fault, and the fix is an encoder
    silence, as before     -> the fault is somewhere all eight checks missed

Deliberately NOT done: an encoder, a second delivery mechanism, or a rewrite of
`wav_to_wem.py`. Three fixes were available and plausible — Wwise 2023.1.14 by
the documented route, hand-built Wwise Vorbis with inline setup validated
against `vgmstream`, or Audioware (installed, working, 20,038 ids loaded, takes
`.wav` and `.mp3` outright, and ships a `voices:` manifest that carries its own
subtitle). Every one of them is expensive, and all three are wasted if the
cause is the ninth link rather than the eighth. Confirm first.

### The revision goes to 3

`phase_revision` was bumped 2 → 3. Not for the audio — a `.wem` swap changes no
node id — but because the Mara half of the control needs the phase to re-enter
on a save that has already walked past her. `replaytest.py` still reports the
re-entry as clean, which is what the D50 guards are for.

### Two things seen in passing and not acted on

**The terminal renders, and it renders badly.** `sc_ac_clinic_terminal_crap.png`
shows `computer_1.ent` at `#ac_terminal_pc` as a bare screen plane — yellow
bezel, three app cards, no computer body — standing on the clinic floor. It
resolves and it is in the right place, so the node and the coordinate are right;
the appearance is not. This is the cosmetic half of OI-13. The red `!` on it is
the objective marker, not an interaction prompt, so the interactivity half is
still open and still only the player can close it.

**The door the player called closed was not the clinic's.** They are inside the
clinic in the terminal frame, with the objective *"Отримай доступ до термінолу
клініки"* active. The green door with the red handle LED is where Mara talks
through it — that is the scene, working as authored.

Counts unchanged: 106 graph nodes, 43 voiced lines, 41 PCM + 2 borrowed Vorbis.
`validate.py` OK, `negtest.py` 96/96, `replaytest.py` clean, `shapetest.py` 31
types. Archive 13,574,144 bytes.

---

## D67 — The recordings reach the player as a scene AUDIO EVENT, not as a voiceover (2026-09-09)

D66 built a control to answer one question - is the codec why 43 lines are
silent - and told the player to walk back to Mara and listen. They came back
with: *"there's nothing to test."* They are right, and the control has been
reverted: `vo/en-us/mara.mara_open_1.wem` and `decision.dec_open_1.wem` are our
own recordings again, and nothing borrowed from Kidnap ships.

What replaced it is not another experiment. Two mods already installed on the
target machine turn out to answer the question the control was going to ask.

### The two mods

`r6/scripts/shardaudioframework/shardaudioframework.reds` is what puts the
**Toggle Audio** button on the shard the player photographed. To play a shard it
calls, in full:

```
GameInstance.GetAudioSystem(GetGameInstance()).Play(StringToName(this.m_data.text))
```

`m_data.text` is the shard's LocKey string, so that is `Play(n"LocKey#6139")` -
the *vanilla* audio system, nothing else. Its companion, `Shard Audio Pack -
Official - English`, ships no `.wem`, no `.bnk` and no archive at all. It is
1,095 `.mp3` files and one YAML under `r6/audioware/`:

```yaml
voices:
  LocKey#6139:
    en-us: ./6139.mp3
```

Two mods, two authors, one working feature. The only way that works is if
**Audioware hooks the vanilla `AudioSystem::Play(CName)`**. Nothing else in
either mod could.

### Why that matters more than a codec

It means the audio does not have to travel the voiceover path at all. Anything
that names a CName through the vanilla audio system plays our file - and a
`.scene` can do exactly that, without a line of script:

```
scnAudioEvent { audioEventName: <CName>, emitterName: "default",
                performer: <actor+1>, startTime: <same as the line> }
```

`scnAudioEvent` is verified vanilla, not invented (rule 8):
`mq029_01a_garage.scene` ships two of them, on a prop performer, and every field
below was copied from it including `duration: 0`, which is what vanilla sets on
a one-shot. Performer numbering comes from the same file - its `debugSymbols`
put johnny at `actorId 0`, `performerId 1` - so a line attaches to its own
speaker: Mara is performer 1, V is 2.

The scene still owns the line, its timing and its subtitle. Audioware only
supplies the sound. **Rule 1 is untouched**: no quest state moves into script,
because no script is involved.

### The manifest shape, and one deliberate omission

Both shapes were measured off installed mods, and this takes their intersection:
a plain CName key (TraumaTeam proves CName keys work) with `fem`/`male` pointing
at the same file, across all 18 locales the shard pack lists, and **no
`subtitle:` field**. That omission is the point. The shard pack has 1,099 voice
entries and not one `subtitle`, so it is optional - and the scene already renders
this line, in Ukrainian, from its own locstring. Declaring one here would make
the player read the beat twice.

One recording serves both brain genders: Mara does not change voice because V
does. All 18 locales point at the same en-us file, exactly as the shard pack
points 18 at one mp3 - D42 ships English audio under Ukrainian text on purpose,
so Audioware's locale pick can never be the thing that goes quiet.

### What is still unproven, and how it was made cheap to check

That a `scnAudioEvent`'s name reaches the same hooked `Play` a script call does.
The scene event is verified vanilla; the hook is verified by two shipped mods;
that the two meet is what this build tests. So the CET panel grew a **Voice**
tab: one button per line, calling `Game.GetAudioSystem():Play(name)` directly.
That splits the chain in half from anywhere in the game, with no save, no quest
state and no walk to a door:

  * a button speaks → the recording, the bank and the name are all good, and
    anything still silent in conversation is the scene event
  * no button speaks → Audioware, the deploy, or the manifest

### The `.wem` path is left in place

`locVoiceoverMap` still ships. It is inert - that is the whole finding - and
removing it would be a second change riding on the first. If it ever starts
working the two would double up, which is a note in OI-16, not a reason to pull
a verified-correct resource out of the build today.

### Files

`tools/gen_audioware.py` (new) owns the CName rule and the bank;
`tools/gen_scene.py` imports `event_name` rather than repeating it, because two
spellings of a name that only fails silently is how this whole issue started.
`build.sh` generates and mirrors the bank; `deploy.sh` learned to mirror a
DIRECTORY, and to delete before copying - a `.wav` left behind after its line is
cut is a file the mod ships and nothing plays. `validate.py` gained
`check_audioware`: two different line keys collapsing to one event name (dot
becomes underscore, so `mara.open_1` and `mara_open.1` would collide) is a bug
whose only symptom is one line playing another line's audio.

Counts: 43 audioware lines, 20 + 9 `scnAudioEvent` in the two scenes, 44 files
in the bank, 14 MB.

---

## D68 — The clinic terminal was inert because a device with no `instanceData` is scenery (2026-09-09)

The same message answered OI-13's other half: *"The same with the terminal.
There was no action with it at all."*

That is not a new mystery. `source/world.json` wrote the experiment down before
anyone could run it, on the probe node `ac_probe_computer`:

> Vanilla places this exact `.ent` with this exact appearance in
> `quest_73110a178d6e7404`, but WITH a 200-field `instanceData` buffer; the
> cover entity two nodes later has `instanceData` null. This is that `.ent` with
> a null buffer. If it appears AND can be interacted with, `terminal_read`,
> `box_opened` and `cabinet_opened` are all cheap. **If it appears but is inert,
> they need the buffer.**

It appears - drawn as a bare screen plane - and it is inert. So they need the
buffer, and reading vanilla's says why in one line: the buffer is what carries
`ComputerControllerPS`, and `ComputerControllerPS` is what holds
`isInteractive: 1` and `tweakDBRecord: Devices.Computer`. With `instanceData`
null there is no controller state at all - nothing to be interactive, and no
device record to build a body from. The bare screen plane and the missing
prompt are one defect, not two.

`reference/device_computer.instancedata.json` is that buffer, extracted verbatim
from node 12 of `quest_73110a178d6e7404.streamingsector` - the same `.ent`, the
same `worldEntityNode`, the same `computer_computer_2_angle_15` appearance this
quest already asks for. `ac_splinter_box` and `ac_terminal_pc` now carry it.

**`ac_probe_computer` keeps its null buffer on purpose.** It has stopped being a
probe and become the control: the difference between the two is now visible
standing in one room.

Two things had to be rewritten per node, and only two:

  * **HandleIds.** Vanilla numbered them 24-35 in a file that had 23 handles
    before them. Each appears exactly once and nothing references them, so they
    are definitions, not links - renumbering cannot change what the buffer
    means, and not renumbering means two props defining handle 24 in one file.
  * **BufferId.** Missed on the first attempt, and it is not subtle: WolvenKit's
    `ReferenceResolver` throws on the second buffer that calls itself `1`, and
    the sector does not convert. `System.Text.Json.JsonException ... Path: $`
    with a stack ending in `BufferHelper.ReadV2` is what that looks like.

**`CruidDict` is copied unchanged, deliberately.** It is tempting to read it as
a per-node unique id and generate one. It is not: nodes 79, 80 and 84 of
`quest_e495c59e9949e75b` all carry the same `3609005567401009152`, and
`1508365491801698304` appears in two different sectors. Vanilla duplicates it
across identical placements, so duplicating it is what matching vanilla means.

Verified: both buffers survive the pack - `ComputerControllerPS` x2,
`isInteractive: 1` x2, `Devices.Computer` x2, read back out of the staged
`.streamingsector` after conversion. Whether the prompt appears is the game's to
say; whether the state is in the archive is not a question any more.

`validate.py` OK, `negtest.py` 96/96, `replaytest.py` clean, `shapetest.py` 31
types. Archive 13,996,032 bytes, `.xl` names `ash_cache_r3.questphase`.

## D69 — Two new things went into one room, and the room crashed: the device buffer comes back out (2026-09-09)

The r3 build was deployed at 15:27. At 15:50 the game died. The player's whole
session, read off `CrashBreadcrumb/breadcrumb.log`, was: load at 15:44:56,
reload at 15:46:53, then a 700 m walk from `-2430,-2673` to `-1899,-2480,24`,
fifteen seconds standing still, two 400 ms hitches, and an access violation.

`-1899,-2480,24` is the clinic floor. `ac_splinter_box` is 12 m away and
`ac_terminal_pc` 20 m. They had just been given `instanceData` for the first
time, in that deploy.

    EXCEPTION
      Code:    0xC0000005 (ACCESS_VIOLATION)
      Thread:  508 "redDispatcher1" (not the main thread)
      Detail:  read at address 0xFFFFFFFFFFFFFFFF

A worker thread, not the game thread - so not the ImGui click that preceded it.
`0xFFFF...FFFF` is the shape of a failed 64-bit id lookup used as a pointer.
CrashLogger's own note - "No mod DLL on the stack" - clears nothing here:
`.archive` content cannot appear on a native stack by construction.

**The correlation is real and it is not proof.** This machine runs 3,081
archives and has 27 crash logs. Three crashes earlier the same day were the
known CET one (`cyber_engine_tweaks.asi+0xAC37`, main thread, signature
`134F61BD`) and had nothing to do with this quest. But the two crashes *after*
15:27 - `5F58BEDF` at 15:34 and `C0370605` at 15:50 - are signatures that appear
nowhere in the 27, and both read `0xFFFFFFFFFFFFFFFF` on a dispatcher thread.
The player has stood in that room before, on r2, and photographed the terminal.

**The problem with r3 is that it changed two things in one room.** The clinic
holds Mara's scene and both computers. r3 gave the computers a device buffer AND
gave the scenes 29 `scnAudioEvent`. Either could produce this fault:

- a device buffer whose controller resolves a component or a persistent-state
  slot it does not get; or
- a scene audio event whose CName the scene system resolves against Wwise
  directly rather than through the hooked `AudioSystem::Play`, gets no match,
  and uses the miss as a pointer. `0xFFFFFFFFFFFFFFFF` is exactly what a missed
  64-bit id lookup looks like, and D67 named that link as the one still unproven.

So this decision is a bisect, not a fix. **`"device"` in `world.json` is now a
value rather than a key** - `null` is off, `"computer"` is on - and both clinic
computers are off. The scene audio events stay. One walk into the clinic now
separates the two:

- **no crash** -> the buffer is the fault, and D68 gets rebuilt against a known
  target instead of a guess;
- **crash again** -> the buffer was never it, the scene event is, and the fix is
  in `gen_scene.py`.

Nothing about D68 is deleted. `reference/device_computer.instancedata.json`,
`device_instance()` and the renumbering all stay; `_device_status` in
`world.json` says why each node is off and what to type to re-arm it. Testing
key presence instead of value would have meant deleting the prose that explains
the buffer, which is the part worth keeping.

**Five hypotheses were killed with evidence before this one was written**, and
none of them changed a line of code:

- *The CruidDict is duplicated across the two props and collides in the
  persistency system.* No: `quest_e495c59e9949e75b` has **six**
  `worldDeviceNode`s carrying buffers that all share `3609005567401009152`, and
  three `worldEntityNode`s sharing `3790033641066651648`. Vanilla does this.
- *The HandleId renumbering broke a reference.* No: all 34 `HandleId` and 3
  `BufferId` in the packed sector are definitions. There is no `HandleRefId` in
  the file, so there is nothing to point at them.
- *The appearance name is wrong, which is also why it renders as a bare plane.*
  No: `computer_1.ent` declares 16 appearances and
  `computer_computer_2_angle_15` is one of them, extracted and read.
- *The buffer carries dangling links into the sector it came from.* No:
  `masters: []`, `mastersCached: 0`, and all three `entEntityID` are `hash: 0`.
  The `mq058_*` fact names in `filesStructure`/`mailsStructure` are inert data.
- *Memory exhaustion.* No: 11-12 GiB private on both the pre-deploy and
  post-deploy crashes. No cliff.

The node itself matches vanilla node 12 of `quest_73110a178d6e7404` field for
field except `sourcePrefabHash` (`0` vs a prefab hash), `CookedPrefabData`
(null vs a `.cookedprefab`), `Pivot`, and the nodeData `Id`. Two differences are
left that are ours and unexplained, and they are the first place to look if the
buffer turns out to be the fault: our sector is `category: "AlwaysLoaded"`,
`level: 0`, where vanilla's device sector is `category: "Quest"`, `level: 255` -
and an always-loaded sector survives the save reload the player did at 15:46:53,
which persistent device state may not be built to do.

### What the same crash hunt proved about the audio

`red4ext/logs/audioware-2026-09-09-15-44-01.log`:

    ids:
    - on-demand static audio    -> 1616
    ...
    no error reported!

The same line read `68` at 13:12, before the deploy. **+1548 exactly**, and
43 lines x 18 locales x 2 genders = 1548. Audioware parsed `ash_cache.yml`,
found all 43 `.wav`, registered every locale and both genders, and reported no
error. The bank half of D67 is not a hypothesis any more - it is live on the
player's machine and correct to the id.

That leaves exactly one link unproven, which is what the CET **Voice** tab is
for, and it needs no walk and no save state.

## D70 - Audioware said "requires gender", and the bisect came back

**2026-09-09, 16:31.** Two questions were open at 16:04: does anything play, and
did the device buffer crash the game. The player deployed at 16:14, played two
sessions, and both questions answered themselves in logs on their machine.

### The audio bug, in Audioware's own words

`red4ext/logs/audioware-2026-09-09-16-20-52.log`:

```
[16:20:52] initialization took 29.6552158s
ids:
- on-demand static audio    -> 1616
...
no error reported!
scene ids:
- on-demand static audio    -> 22
no scene error reported!

[16:27:40.868] [warning] cannot play sound: Registry error: requires gender: ash_cache_vo_decision_dec_absorb_1
[16:27:43.132] [warning] cannot play sound: Registry error: requires gender: ash_cache_vo_decision_dec_blueeyes_1
```

Two lines of warning close D67's last open link and open a new one in the same
breath. `Play()` **reaches Audioware**. The CName **resolves in the registry** -
you cannot be refused for the wrong gender on a key that does not exist. The
bank is loaded, the file is on disk, the hook is live. The sound does not come
out because the registry will not serve a *gendered* entry to a caller that
hands it no gender.

`r6/scripts/Audioware/Ext.reds` says where the gender would have come from:

```
import Codeware.Localization.PlayerGender
public final native func Play(eventName, entityID, emitterName, line, ext)
public final native func PlayOverThePhone(eventName, emitterName, gender)
public final func Play(eventName: CName) -> Void        // no gender anywhere
```

Every caller this quest has is the last one. The CET panel calls
`Game.GetAudioSystem():Play(name)`. `shardaudioframework` calls the same thing.
A `scnAudioEvent` names an audio event, not a speaker. None of them can satisfy
a gendered key.

### The shape was chosen for a good reason and it was still wrong

`gen_audioware.py`'s header wrote fem/male under each locale on purpose - the
same file twice, so that "V's brain gender must not change who Mara is". The
intent was right; the encoding of it was backwards. In Audioware, writing
fem/male does not mean *this line is gender-neutral*, it means **this key is
gendered** - and a gendered key is only playable by a caller that resolves one.

The fix was in the same header all along, in the shape it had already measured
off a shipped mod and then declined to copy:

```yaml
voices:
  LocKey#6139:
    en-us: ./6139.mp3      # shard_audio_pack_official_english
```

The shard pack is not just *a* precedent, it is *the* precedent: it is the one
installed bank driven by exactly the no-entity `Play(CName)` this quest uses,
and every entry in it is plain. A survey of the six installed banks that declare
`voices:` puts our old build alone at the far end of it -

| bank | gendered rows |
|---|---|
| shard_audio_pack_official_english | 0 |
| TraumaTeam | 6 |
| AntiTheftMeasures | 10 |
| Flushing Etiquette | 18 |
| DrugDealer | 34 |
| **ash_cache (old)** | **1548** |

`gen_audioware.py` now emits `    <locale>: <file>`. 43 keys x 18 locales = 774
plain rows, 0 gendered. Nothing else about the bank changes - same 43 wav, same
CNames, same absent `subtitle` field, same 18 locales pointing at the one English
take per D42.

**The number to check on the next launch** is the first block of the audioware
log. It read 68 before the bank existed and 1616 with the gendered bank. It
should now read **842** (68 + 774). If it reads 842 and no "requires gender"
warning follows a play, the audio chain is closed end to end.

### The bisect came back, and it did not convict the buffer

D69 turned both clinic device buffers off so that one walk would separate them
from the 29 `scnAudioEvent` added in the same deploy. The player ran that walk.
Today's ten crashes, in order:

| time | signature | thread | build |
|---|---|---|---|
| 11:33 | E4044E73 | redDispatcher10 | before the buffer existed |
| 11:34 | E4044E73 | redDispatcher8 | before |
| 11:39 | 960F5DA5 | redDispatcher14 | before |
| 11:55 | 134F61BD | GameThread (CET) | before |
| 12:45 | 134F61BD | GameThread (CET) | before |
| 13:18 | 134F61BD | GameThread (CET) | before |
| 15:34 | 5F58BEDF | redDispatcher13 | **buffer on** |
| 15:50 | C0370605 | redDispatcher1 | **buffer on** |
| 16:15 | E4044E73 | redDispatcher10 | **buffer off** |
| 16:29 | 134F61BD | GameThread (CET) | **buffer off** |

Two crashes in 25 minutes with the buffer. Two crashes in 15 minutes without it.
And the one dispatcher crash that happened with the buffer off carries
**E4044E73** - the signature this machine threw twice at 11:33 and 11:34, hours
before the buffer was ever built.

D69 leaned on the novelty of `5F58BEDF` and `C0370605` - signatures found in none
of the 27 older logs. That argument is now much weaker than it read at the time,
because the pre-deploy morning threw two *different* dispatcher signatures of its
own. On this install, a worker-thread access violation every ten to twenty
minutes is the baseline, not a symptom.

So the buffers come back on. The reasoning is not "it is proven safe" - it is
that the bisect ran, returned no separation, and an inert terminal blocks the
quest at its very first objective. Leaving a known-blocking change in place to
guard against an unproven risk is the worse of the two errors.

### One hypothesis killed on the way

Before re-arming, the obvious structural doubt: our computer sits on a
`worldEntityNode`, and the device system might require a `worldDeviceNode`. A
sweep of every extracted vanilla sector for nodes whose instanceData carries a
device controller state returns exactly one, and it is a **`worldEntityNode`** -
node 12 of `quest_73110a178d6e7404`, the same `computer_1.ent`, the same
`computer_computer_2_angle_15` appearance. Node type was never the problem, and
the two remaining field differences from vanilla stay what they were:
`sourcePrefabHash` ("0" vs a real hash) and `CookedPrefabData` (null vs a
`.cookedprefab`). That is the next thread to pull if the terminal is still inert
with the buffer back on.

## D71 - The scene needed a second registry, and Audioware's source named it
2026-09-09, after the user reported: "in cet working playing audio but if set
fact 3 from cet showing subtitles but not playing any sound and the same
terminal not working again".

D70's fix worked, exactly and measurably. The prediction was that
`on-demand static audio` would read 842. The 17:10 log reads:

    ids:
    - on-demand static audio    -> 842
    - on-demand streaming audio -> 19788
    - in-memory static audio    -> 182
    no error reported!

and there is no `requires gender` line anywhere in the file. The CET Voice
button speaks. The bank is closed.

The same log carried the next fault in the block underneath it, which had been
sitting there unread since D67:

    scene ids:
    - on-demand static audio    -> 22

TWO REGISTRIES, NOT ONE
Audioware keeps scene dialogue in a completely separate registry from `voices:`,
and prints the two separately. The 43 lines were all in the first. The 22 in the
second are not ours at all: the one other installed bank that ships a `dialogs:`
section is sonoraapex, whose manifest holds 2 keys x 11 locales = 22. Every
scene id in this install belonged to another mod.

THE SCENE AUDIO EVENT WAS NEVER THE DOOR
`tools/gen_scene.py` emits a `scnAudioEvent` beside each `scnDialogLineEvent`,
naming the CName from the `voices:` block, on the inference that a scene audio
event reaches `AudioSystem::Play` and therefore reaches Audioware. That
inference was wrong, and the source says so. From
`crates/audioware/src/hooks/audio.rs`, the hook is on the engine's
`PlayDialogLine`, and it keys on the dialogue line's CRUID:

    let modded = Engine::<CpalBackend>::exists_for_scene(&string_id);
    if modded {
        crate::engine::queue::send(Command::PlaySceneDialog { string_id, ... });
    }
    // still let the engine carry on, to handle subtitle
    let out = cb(a1, a2, a3, a4, a5, a6, a7, a8, a9);

That comment is the reported bug, written down in the mod's own source before we
hit it. The subtitle is drawn by the engine's path, which runs unconditionally.
The voice happens only when the CRUID is registered. Subtitles without sound is
not a partial failure - it is precisely what an unregistered line looks like.

`string_id` is field 0 of `audioDialogLineEventData`, a `Cruid`
(`types/vanilla/events/dialog_line.rs`). The manifest section that fills that
registry is `dialogs:`, a `HashMap<u64, SceneDialogs>` on the root Manifest
struct (`crates/manifest/src/de.rs:48`, serde-renamed from `scene_dialogs`).

THE KEY IS A NUMBER WE ALREADY HAD
From `book/pages/SCENE_DIALOG_LINES.md`, on the subtitle entries: "you can
notice the stringId ... is the same as the one defined for the Voice". The
`dialogs:` key IS the locstring ruid. This project allocates those in
`source/subtitle_ids.json` and already bakes each one into three places:
`scnscreenplayDialogLine.locstringId.ruid` in the .scene, the `stringId` of the
subtitle entry, and the `stringId` of the locVoiceoverMap entry. Nothing had to
be invented, allocated or renumbered - the fix is those 43 existing numbers
pointed at the 43 files the `voices:` block already copies.

SHAPE, VERIFIED TWICE
Single-inline: one plain path per locale, same as `voices:` after D70. Confirmed
against `crates/manifest/src/de/dialog.rs`'s own serde doc tests, and against
sonoraapex, the one installed bank that uses the section. The dual (fem/male)
form is legal here, unlike in `voices:`, because a scene line does carry a
speaker gender - but Mara is one voice, so single-inline is right.

A SIDE EFFECT WORTH NAMING: THE .WEM CODEC STOPS MATTERING
`tools/wav_to_wem.py` writes PCM .wem and says under rule 8, in its own header:
"NOT verified: that PCM is accepted on the VOICEOVER path specifically." That
was a live risk - a second, independent reason the scene could be silent, and
one we had no way to test apart from the first. Audioware decodes the source
file itself, so the .wem now only has to exist for the engine to raise the
dialogue line at all (and later, for lipsync - see the book's note that the RED
engine will not play a lipsync anim with no associated .wem). An unverifiable
assumption became a non-issue instead of a second experiment.

WHAT WAS NOT CHANGED, DELIBERATELY
The `scnAudioEvent`s stay in the scene for this build. They are proven inert -
this exact build had all 43 CNames registered and playing from the CET button
while the scene was silent - so they cannot double up, and changing two things
at once would spoil the reading. They come out once the scene is heard. See
OI-20, which this also resolves in principle: the 14 choice options have
subtitle ids like every other line, so they are registered here too and get
audio through the same door, which the scnAudioEvent path never gave them.

THE TERMINAL, AND WHAT WAS ELIMINATED THIS ROUND
The user's own reading - "this clinic needs to be unlocked ... no unlocked doors
and the premises themselves" - is the right shape of question, and it is now the
leading one, because the authoring has been cleared field by field.
`ac_terminal_pc` was diffed against vanilla node 12 of quest_73110a178d6e7404,
the mq058 computer, at every level:

  - node fields:      identical but for debugName and sourcePrefabHash
  - ComputerController + ComputerControllerPS: identical but for HandleIds
  - the PS says isInteractive 1, deviceState ON, tweakDBRecord Devices.Computer
  - worldNodeData:    identical but for Uk10, CookedPrefabData, QuestPrefabRefHash

Uk10 (vanilla 1312, ours 288 - one bit, 0x400) was killed by census: of the five
vanilla worldEntityNodes in the extracted corpus, four carry exactly our 288.
The remaining differences are sourcePrefabHash, CookedPrefabData and
QuestPrefabRefHash, all three of which are the marks of a node that came out of
a prefab - which is the thread to pull if the probe says the device exists.

Continuing to diff fields is the failure mode this project's debugging rules
name explicitly: fixes stacked on an unconfirmed cause. The data is right and
the device is dead, so the fault is in what the runtime makes of the node, and
only the running game can say which. `tools/gen_cet.py` gains a Devices tab that
asks it - a look-at probe over the vanilla
`GameInstance.GetTargetingSystem().GetLookAtObject()`
(core/systems/targetingSystem.script:93), reporting class, EntityID, whether
GetDevicePS() returns anything, and the device's state, power and action count.
Three answers, three different fixes, one button press and no save:

  nothing there        the entity never spawns - sector, .ent path or position,
                       and the "clinic is not really unlocked" reading gains.
  there, not a Device  instanceData is being dropped on load.
  there, IS a Device   inert at runtime: power, registration or persistency.

ALSO FOUND, NOT YET FIXED
ac_terminal_pc was cloned wholesale from the mq058 computer and still carries
mq058's content: filesStructure names mq058_file1, mailsStructure names
mq058_plex_newsletter, and their journalPaths point into mq058's journal. That is
what the terminal would show if it opened today. It does not affect whether the
device works, and it is not worth touching until it does.

### D71 postscript - the number came back right (2026-09-09 20:46)

Deployed 20:30, launched 20:43. `audioware-2026-09-09-20-46-27.log`:

    ids:                                  scene ids:
    - on-demand static audio    -> 842    - on-demand static audio    -> 796
    - on-demand streaming audio -> 19788  - on-demand streaming audio -> 0
    - in-memory static audio    -> 182    - in-memory static audio    -> 0
    for a total of: 20812 id(s)           for a total of: 796 scene id(s)
    no error reported!                    no scene error reported!

796 = 22 + 43 x 18. Both predictions held to the digit and nothing parsed
badly, so the `dialogs:` section is exactly the shape Audioware wanted and the
43 CRUIDs are now in the registry `hooks/audio.rs` consults. The remaining
unknown is playback, not registration: the session died at 20:50:50 at the
clinic door before the scene ran.

That crash is baseline, not ours. Signature `93CABB10`, thread
`redDispatcher12`, `ACCESS_VIOLATION` reading `0xFFFFFFFFFFFFFFFF` - a freed or
poisoned object dereferenced on a job thread. No mod DLL on the stack and
nothing audio-shaped anywhere in the 14 frames. Today this install produced six
`redDispatcher` access violations (`E4044E73` x3, `5F58BEDF`, `C0370605`,
`960F5DA5`) plus this one, most of them before the bank existed; the
CrashLogger trace shows the 17:01, 17:02 and 17:04 sessions each dying inside
two minutes at one repeated site, and the 20:40 session dying 73 seconds in,
nowhere near our content. The archive deployed at 20:30 is functionally the same
world data as the one that survived the same walk at 16:48 - this deploy's
changes were r6-side only (the YAML bank and the CET panel). Correlation with
the clinic arrival is noted and not claimed as cause.

### D72 - the Acts button was crashing the game, and D71's "baseline" call was wrong (2026-09-09 21:15)

**Retraction first.** The D71 postscript above concluded the 20:50 crash was this
install's baseline and flagged the clinic correlation as "noted and not claimed
as cause". That was wrong, and the next two crashes proved it. Keeping the
paragraph as written, with this correction under it, because the reasoning it
used - signature novelty is weak evidence, six redDispatcher AVs the same day -
was sound and still is. What defeated it was a repro, which no amount of census
arithmetic can substitute for.

Three fatal crashes, three signatures, one shape:

    20:50:50  93CABB10  redDispatcher12  read 0xFFFFFFFFFFFFFFFF  pos -1900,-2478,24
    21:03:12  CFBFFB1D  redDispatcher9   read 0xFFFFFFFFFFFFFFFF  cyber_engine_tweaks.asi
                                                                  + Codeware.dll on stack
    21:15:25  17370EC2  redDispatcher6   read 0xFFFFFFFFFFFFFFFF  pos -1899,-2479,24

The two with a position died **1.4 m apart**, at z=24 - the clinic interior
floor, about 10 m from `ac_mara` and the splinter case. The breadcrumb for the
last one shows the player walking in, stopping at 21:15:18, and standing still
until the fault at 21:15:21: the four seconds it takes to open the CET overlay
and click. The user reported both as "crashed when I click fact 3".

**Root cause: the panel wrote facts from the wrong thread.** `Acts` ->
"Act 3 - at the clinic, box found" ran, inside one ImGui button callback:

    setFact(ashcache_start, 1)          setFact(ashcache_at_clinic, 1)
    setFact(ashcache_at_motel, 1)       setFact(ashcache_box_opened, 1)
    setFact(ashcache_courier_log_played, 1)
    setFact(ashcache_progress, 2)

Six `questsSystem:SetFactStr` calls with no frame boundary between them. CET
dispatches ImGui callbacks from its D3D12 present hook - the render thread, mid
frame - not from the game tick. The engine only ever changes facts from a quest
node on the main thread, one edge at a time. Six mutations re-entered from a
foreign thread means the graph is re-entered while its listener list is being
walked, and every edge that fires kicks a spawn or a scene start onto the
`redDispatcher*` job pool at once. A job thread then reads a listener that the
previous edge already freed: `0xFFFFFFFFFFFFFFFF`. The 21:03 stack keeps
`cyber_engine_tweaks.asi` and `Codeware.dll` in frame, which is that path.

It crashes *at the clinic* because act 3 is the clinic act - that is where the
edges land. Nothing is wrong with the archive; the same world data survived this
walk at 16:48. The bug was in `tools/gen_cet.py`, dev-only, never shipped.

**Fix.** `setFact` no longer writes. It appends to `factQueue`, capped at 64.
`drainFactQueue()` is called at the top of `onUpdate` - CET's main-thread tick -
and applies exactly one write per frame, preserving order so gates still land
before `progress`. At the observed 22 fps an act jump takes ~0.3 s and the full
reset ~1.2 s. The Acts tab shows the pending count and disables its buttons
while the queue drains, so presses cannot stack. The per-fact `set`/`clear`
buttons in the Facts tab route through the same `setFact` and are fixed with it.

This is also the honest answer to "the debug button speaks but the scene is
silent" being tested at all: every fact the panel has ever set went in through
this path, so any beat driven from the panel has been arriving in a burst rather
than as separate edges. Beats tested that way before today were tested wrong.

### D73 - the clinic crash is a world node, not the CET panel, and the launch failures were never crashes (2026-09-10 01:00)

**Correction to D72.** D72 said the Acts button "was crashing the game". The
queue fix in it was deployed at 21:29 and the game crashed at the clinic again
at 21:43, on a walk in from the street with the overlay never opened. So the
fix was necessary - writing six facts from CET's present hook is genuinely the
wrong thread, and the Facts tab did it too - but it was not the cause of these
crashes. What made me point at the button was that clicking it required standing
in the clinic, which is where the real trigger lives.

**The census that settles it.** 241 crash logs on this install, back to
2026-08-06. Signature `93CABB10` appears in exactly two of them:

    20:50:50  93CABB10  redDispatcher12  read 0xFFFFFFFFFFFFFFFF  pos -1900,-2478,24
    21:43:06  93CABB10  redDispatcher14  read 0xFFFFFFFFFFFFFFFF  pos -1899,-2479,24

Both today, both after the 20:30 archive deploy, both on the clinic floor, 1.4 m
apart. In the 237 crashes before them it does not occur once. The third fatal,
`17370EC2` at 21:15:25, is also a first-ever signature and also died at
-1899,-2479,24. Meanwhile `CFBFFB1D` at 21:03 has eight prior occurrences going
back to 2026-08-07 - that one really is baseline, and it is the only one of the
four that is.

**The 21:43 breadcrumb removes the panel from the story.** A continuous walk:
-1980,-2543,32 at 21:42:38 through the entrance at -1889,-2487,28 at 21:42:57,
down to -1899,-2480,24 at 21:42:59, stationary for three seconds, first-chance
at 21:43:03, fatal at 21:43:06. No pause anywhere on the approach - the overlay
was never open.

**Prime suspect: `ac_probe_npc`.** It sits at -1892.65,-2484.95,28, three metres
from the door that walk went through, with `spawnOnStart: true` and
`objectRecordId = Character.q305_fia_agent`. Its own `_about` says why it is the
suspect: every `objectRecordId` in all 698 vanilla quest sectors is a `Vehicle.*`
and not one is a `Character.*`, so whether a `worldPopulationSpawnerNode` accepts
a Character record was always a guess. A spawn that resolves to a bad record is
exactly the shape of the fault - a `redDispatcher` job dereferencing a sentinel.
It is also the only node in the project doing something vanilla never does.

Disabled for one test, one variable: `ash_cache_probe_car` (the Vehicle control,
55 m away and nowhere near the crash site) and `ash_cache_probe` (a trigger and
a prop, no spawn) both stay in. If the clinic stops killing the game, OI-13 is
answered - no, a spawner node will not take a Character record - and that answer
is worth more than the probe was.

`gen_sector.py` grew a `disabled` flag for this: the sector stays in
`source/world.json` with its reason written next to it, gets no descriptor in
the streaming block, and is not packed. It also deletes the sector's leftover
`build/*.json`, because `build/tree` is cleaned every build but `build/*.json`
never was - without that, a sector that stops being generated keeps shipping
from the previous run's file, and "disabled" would have been a lie. The first
build after the flag went in proved it: the archive still contained
`ash_cache_probe_npc.streamingsector`.

**The launch failures are not crashes.** `crashlogs/session_*.log` decides it,
because the tee block writes `=== wine exited rc=N ===` after wine returns.
Every session with a crash log has that line. Not one of the seventeen "the game
didn't start" launches has it - the shell pipeline died with the game still
running, which is a Ctrl+C or a closed terminal, not a game failure. The trace
log agrees: the 21:31 launch was executing at +73s, seconds before it ended.

Every one of them stops producing output at +68 to +79s - the same stage every
time, right after the Streamline DLL signature block and before
`Loading input configs from r6/input`. In the 21:08 launch that gap was 12s and
the menu followed. Silence before the kill, oldest to newest: 7s, 7s, 25s, 30s,
36s, 39s, 57s, 66s, 66s, 82s, 92s, 99s, 108s, 145s, 158s, 284s, 631s. Two were
abandoned after seven seconds of quiet. One sat there for ten minutes and was a
real hang. Nothing on screen distinguished them, which is the actual defect.

So `start` got two changes. `DXVK_LOG_LEVEL` and `VKD3D_DEBUG` are no longer
hard-set to `none` - they default to `info`/`warn` and take `CP_DXVK_LOG` /
`CP_VKD3D_LOG`, mirroring how `CP_FPS_CAP` overrides `DXVK_FRAME_RATE`. Both
already fed the stream the script tees, so silencing them was throwing away the
only evidence the graphics layer ever produces. And the launch block now prints
a heartbeat every 15s with the game's cpu and rss, so a slow load and a hung one
are finally different things on screen.

### D74 - "the game doesn't start" is a real fault with a name, and it is not ours (2026-09-10 01:40)

D73 said the failed launches "were never crashes" because none of them wrote
`=== wine exited rc=N ===`. That inference was sound and the conclusion drawn
from it was wrong. The missing line proves the *shell pipeline* was killed with
the game still executing. It says nothing about whether the game was healthy,
and it was not.

`bin/x64/CrashLogger/CrashLogger_trace.log` had the answer the whole time. Every
one of the five launches the user abandoned tonight looks like this:

    01:22:17  session start
    01:22:35  deferred init complete - game running      (+18s)
    01:23:31  first-chance ACCESS_VIOLATION at
              0x00006FFFF9456814 faultaddr=0x0           (+74s)

That +74s is exactly the point where every failed launch goes quiet - the stage
D73 described as "the same place every time" and mistook for a slow load. It is
not a stage. It is the crash.

**The fault.** `Cyberpunk2077.exe+0x216814`, signature `E4044E73`, a null read
through RCX on a `redDispatcher*` job thread, ~74s in, while CET is still
loading its Lua mods (`scripting.log` ends mid-line two seconds before it).

**It is baseline, and this time that is established rather than assumed.**
25 of the 242 fatal crash logs carry `E4044E73`, and they start on **2026-08-06**
- five on the earliest day in the census, a month before this quest had a single
sector - recurring on 11 separate days since. The trace log adds 38 first-chance
occurrences across 294 sessions. A load-order race in a 3000-archive install.

**Why it reads as "nothing starts".** The fault escalates to FATAL only about
half the time (20 of 38). When it does, wine exits rc=5 and there is a crash log.
When it does not, the job thread is lost, the loader never completes, and the
process SURVIVES: 74 threads asleep, RSS frozen at 5089 MiB, no window, forever.
One such process was still alive an hour later holding 5 GiB, because Ctrl+C
killed the pipeline and not the game.

**Two things I built on 2026-09-09 were wrong and are replaced.**

1. The heartbeat printed `ps -o %cpu`, which is the average over the process
   lifetime, not current load. A process that burns 65s of CPU and then dies
   still prints a slowly decaying percentage - the user watched 82% decay to 16%
   and read it as work finishing. The honest signal sat next to it and was
   ignored: RSS pinned at exactly 5089 MiB for nine consecutive samples. The
   watchdog now computes instantaneous cpu from `/proc/PID/stat` utime+stime
   deltas.
2. `DXVK_LOG_PATH` was set to a unix path. DXVK is a PE dll inside wine, so it
   resolved as `C:\mnt\ssd\...` and wrote nothing. Set to `none`; stderr is
   already teed.

**What now happens instead.** `start` runs a watchdog for the first five minutes
of each launch. It declares the launch dead on either (a) that exact fault
appearing in CrashLogger's trace - verdict at ~74s, or (b) RSS frozen with cpu
under 5% for 60s - the generic net for a startup fault this pattern does not
know. Then it kills the game and relaunches, up to `CP_MAX_TRIES` (default 4).
It disarms permanently once RSS passes 7 GiB, so it can never touch a session
that reached the menu, and a normal quit is never retried. Ctrl+C now takes the
game down with it.

**Honest caveat on the retry.** Retrying only helps because the fault is a race:
21:08 and 21:33 yesterday started fine on the same mod set. Tonight went 5 for 5,
which against 4 of 6 earlier is not a distinguishable rate (p ~ 0.45), so there
is no evidence the archive deployed at 01:21 made it worse - but neither is there
proof retrying will always win. If a night ever goes 4 for 4 through the retries,
that is the signal the race has become deterministic and the mod list, not the
launcher, is what changed.

**What this does not touch.** The clinic crash is a separate signature
(`93CABB10`, 0xFFFFFFFFFFFFFFFF, at the clinic, twice, never before) and the
`ac_probe_npc` test from D73 is still the open question. Startup and clinic are
two different bugs; conflating them is what produced D72.

### D75 - the watchdog worked, and the three ways it still lost (2026-09-10 02:05)

First live run of D74's watchdog, session log `session_2026-09-10_01-48-52.log`.
It relaunched twice on its own, correctly, and then quit one attempt short:

	01:48:52  launch      -> STALLED at +186s, killed, relaunch
	01:52:02  relaunch 2  -> STALLED at +141s, killed, relaunch
	01:54:27  relaunch 3  -> wine exited rc=5 at +132s, loop stopped

The user saw only the tail of that third attempt and reported "the same, nothing
starts". The first two relaunches were invisible to them - which is the intended
behaviour, but it means the report "nothing starts" no longer distinguishes one
failure from four. Three defects, in increasing order of how much they cost:

**1. The fast detector was never armed.** `GAME_FOLDER` is already
`$WINEPREFIX/drive_c/game/bin/x64/`, and D74 wrote
`TRACE_LOG="$GAME_FOLDER/bin/x64/CrashLogger/..."`, doubling the segment. The
path does not exist, `[ -r "$TRACE_LOG" ]` returned false every sample, and the
trace check silently never ran. Only the slow RSS/cpu stall detector fired,
which is why both kills took 140-190s instead of ~80s. This is the same mistake
as the `DXVK_LOG_PATH` one corrected in D74, one day apart: **a wrong path does
not fail loudly, it makes a feature quietly do nothing.** Both were guarded by a
test that only proves the code parses. Fixed, and verified by resolving the
variable and stat-ing the file rather than by reading the line back.

**2. The fault pattern matched an address that moves.** D74 matched
`first-chance.*9456814`. The module base is randomised per launch: the same
fault is logged at `0x00006FFFF9426814` at 01:50 and `0x00006FFFF9456814` at
01:55. Roughly half of all occurrences would have been missed even with the path
fixed. Now matched on `first-chance.*faultaddr=0x0000000000000000` - the null
read itself, which is base-independent.

That pattern is broader: 76 of 297 trace sessions contain one, against 38 for
the address form. Of those 76, exactly one went on to live more than fifteen
minutes without going FATAL - and that session's "life" is measured by the gap
to the next launch, which is also what a hang looks like from outside. So the
false-positive rate is at most ~1%, and probably zero. It is still cheap to
remove: **a null read is now an accusation, confirmed on the next sample.** A
load that is still working grows RSS by hundreds of MiB between samples (2.2 ->
5.1 GiB across a normal load); a dead one sits still. Only growth counts as
life, because RSS also *falls* ~300 MiB during teardown. Costs 15s of detection
time, buys immunity to a pattern that is deliberately loose.

**3. A crash exit was read as a normal exit - this is the one that mattered.**
The retry condition was "the watchdog killed it", nothing else. But the fault
escalates to FATAL about half the time (20 of 38 in D74's census), and then the
game dies on its own: null read at ~74s, crash handler spends ~50s writing the
dump, wine returns 5 at ~132s - before the stall counter, which needs four
consecutive frozen samples, can reach four. `[ -e "$RELAUNCH_MARK" ] || break`
then treated it as a clean quit. The retry loop stopped on exactly the failure
it exists to handle.

The fix needs to separate "died while loading" from "died after being alive",
and the watchdog is the only thing that knows which. It now touches
`REACHED_MARK` when it disarms - past the stall point, or out of arming window.
The loop retries when the watchdog killed it, **or** when wine returned non-zero
with no `REACHED_MARK` and the attempt lasted at least 30s. That last clause
keeps a wine that fails instantly from burning all four attempts, and the
`REACHED_MARK` requirement means a crash hours into play is never silently
restarted - that one is the player's to see.

Verified by driving the real code, not by reading it. The watchdog function was
extracted from `start` with its sleeps shortened and run against stub processes:
a flat-RSS stub with an injected fault line confirms and kills, a stub growing
200 MiB every 2s stands down and runs on. The retry block was extracted
verbatim and driven through six cases: watchdog kill -> retry; rc=5 during load
-> retry (the 01:56 case); rc=5 after the menu -> stop; rc=0 clean quit -> stop;
rc=0 during load -> stop; rc=2 after 5s -> stop. All six correct.

What is still not verified: the whole thing against a real launch that actually
reaches the menu. `MENU_RSS` is 7 GiB and no successful launch has ever been
recorded by a heartbeat, so the disarm threshold is a guess. The real protection
against killing a live session is the `cpu < 5%` clause - a game rendering a
menu is nowhere near idle - not the RSS number. If a future session is killed at
the menu, lower `MENU_RSS`, do not widen the cpu threshold.

### D76 - "the sound has completely disappeared" was PulseAudio routing, not the mod (2026-09-10 02:40)

The 20-attempt launch marathon finally produced a playable session (02:15:21 ->
02:23:45) and the player reported total silence - not "the quest lines are
silent", *everything*. The obvious suspect was our 01:21 archive deploy, the only
content change in the whole game tree since the last session that had sound.
It was not the archive.

**What the evidence said.** While a later session was alive I read the OS side
directly instead of theorising:

- The game had 3-4 PulseAudio streams open (`Cyberpunk 2077`, float32le 2ch
  48000Hz, via `wine64-preloader`), all `Corked: no`, `Mute: no`, `Volume: 100%`.
  Three streams because three separate audio engines live in this process: the
  game's own, Audioware (kira/cpal) and RadioExt (FMOD).
- `winepulse.drv` loaded, `libpulse` mapped, `/memfd:pulseaudio` segments open,
  registry `Software\Wine\Drivers` `"Audio"="pulse"`, cookie in the game's
  remapped `HOME` identical to the real one.
- `UserSettings.json` has not been written since 2026-09-04, so no in-game
  setting can have changed. Master/Sfx/Dialogue are 100. (Music, CarRadio and
  Radioport are 0 - a deliberate, long-standing choice, not the fault.)
- Audioware registered 20812 ids + 796 scene ids with "no error reported!";
  RadioExt's FMOD init was clean.
- The played session took no first-chance exception during load, so this was
  not the startup fault silently killing an audio init job.

**The actual cause.** `module-switch-on-connect` is **not loaded** on this box
(`/etc/pulse/default.pa` loads `switch-on-port-available` and
`default-device-restore`, not `switch-on-connect`). PulseAudio therefore binds a
stream to whatever sink was default at creation time and never moves it again.
The default sink here is a Bluetooth headset - `HOCO W35 Air`,
`bluez_sink.A4_DB_BB_C8_79_F6.a2dp_sink` - which idle-disconnects on its own; I
watched it vanish mid-investigation, the default flip to
`alsa_output.pci-0000_0c_00.4.iec958-stereo` (S/PDIF), and `pactl info` change
under me between two commands minutes apart.

The asymmetry is the whole bug: when a sink is **removed** PulseAudio migrates
its streams to the new default, but when a sink **appears** nothing moves back.
A 40-minute crash marathon is more than enough for the headset to idle out. The
launch that finally survived opened its audio on S/PDIF; the headset reconnected
afterwards; every application started later went to the headphones and the game
did not. Unmuted, full volume, perfectly healthy - and inaudible.

**Why this was worth chasing rather than guessing.** From inside the game this
is indistinguishable from "the mod broke the audio", and the mod was the only
thing that had changed. One more deploy-and-pray cycle would have cost the
player another twenty launches and proved nothing.

**What was built.**

1. `start` grew `audio_snapshot`, called at the watchdog's disarm point (the
   moment the load is known to be alive). It logs the default sink and every
   Cyberpunk stream's sink/mute/volume, and moves any stream that is not on the
   default sink, announcing the move. Every future session now records its own
   audio routing, so this question is never open again.
2. `/mnt/sata/Cyberpunk2077/audio-doctor.sh` for the live case - the headset
   reconnecting *after* the one-shot snapshot has run:
   - no flag: report routing, flag anything misrouted or muted;
   - `--fix`: move streams to the current default sink and unmute;
   - `--level`: measure each stream's real PCM peak via
     `parec --monitor-stream=INDEX`, which separates "PulseAudio is sending it
     somewhere else" from "the engine is emitting silence".

**Verified by execution, not inspection** (the D75 lesson). Both the extracted
`audio_snapshot` and the doctor were driven against a real misrouted stream -
`pacat --property=application.name="Cyberpunk 2077"` pinned to the HDMI sink -
and each detected it, moved it, and was a no-op on the second run. The doctor's
report-only path was also run with no game present.

**The real fix is one line the player has to choose to take:**
`pactl load-module module-switch-on-connect` - after which streams follow the
headset when it reconnects, for every application, not just this game. That is a
system-wide behaviour change, so it is offered, not applied.

**Caveat.** I never observed the silent session itself; it had already crashed
when the report arrived. The reconstruction rests on the routing mechanism, the
confirmed absence of `switch-on-connect`, and the headset disconnecting under
observation - not on a captured `sink-input` on the wrong sink at the time. If
the next silent session's `[start] audio:` lines show every stream already on
the default sink, this explanation is wrong and `--level` is the next probe.

### D77 - the clinic crash is not the spawner; the three device props are the only suspects left (2026-09-10 03:05)

**D73's test ran and returned an answer: no.** `ash_cache_probe_npc` was
disabled for the 01:21 archive and the game died on the clinic floor again at
02:32:37. Verified rather than assumed - `build/tree` holds four sectors and
`build/ash_cache_probe_npc.streamingsector.json` is gone, and the deployed
archive md5 `bb58a308f307bd846ee8125d76a30432` is byte-identical to the repo one
built with the flag on. So a `worldPopulationSpawnerNode` carrying a
`Character.*` record in `objectRecordId` is **not** what kills the clinic.
Whether the engine accepts such a record at all is still unanswered - the node
never shipped, so nothing was learned about the API. That half of OI-13 stays
open; only the crash accusation is withdrawn.

**Four crashes, one square metre, three signatures.**

    2026-09-09 20:50:50  93CABB10  redDispatcher12  read 0xFFFFFFFFFFFFFFFF  -1900,-2478,24
    2026-09-09 21:15:25  17370EC2  -                -                       -1899,-2479,24
    2026-09-09 21:43:06  93CABB10  redDispatcher14  read 0xFFFFFFFFFFFFFFFF  -1899,-2479,24
    2026-09-10 02:32:37  E815263E  redDispatcher7   read 0x0000000700000001  -1899,-2479,24

`E815263E` is a first-ever signature in 248 crash logs, and its stack shares
nothing with `93CABB10` except the three-frame job-worker tail every
`redDispatcher` crash ends with. Its fault address is not a sentinel: RDI holds
`0x0000000700000001` in a region that is `MEM_RESERVE` and was never committed -
a garbage pointer, not a freed one. **Three unrelated code paths dying in the
same square metre is the signature of corrupted state, not of one bad call.**
The crash surfaces on whichever job touches the wreckage next, which is exactly
why the signature census kept saying "new bug" while D72's position rule kept
saying "same bug". Position wins again.

**The panel is clear a second time.** `report.txt` is still 2026-09-09 17:15 -
the CET overlay was never opened in the 02:26 session. A continuous walk in,
nine seconds standing still, two hitches (452 ms then 335 ms) on arrival, fault
seven seconds later. The player also heard a voice line speak one word before
the freeze, which is the first evidence in this project that the scene audio
path reaches the speakers at all.

**What is left, and why it is one thing.** `ac_splinter_box`, `ac_terminal_pc`
and `ac_probe_computer` are the only `worldEntityNode`s in the project. All
three are the same device master, `base\gameplay\devices\masters\computers\
computer_1.ent`, placed with `instanceData` null. The player has confirmed all
three times over that they are inert scenery with no interaction prompt - a
device master with no `ComputerControllerPS` behind it. That is a
half-constructed object, and a half-constructed object is the right shape for a
job thread reading `0x0000000700000001`.

The control was already in the data and I had not read it that way: **the motel
sector is markers-only and has never crashed, the probe car is a spawner 55 m
from anything and has never crashed, and the only sector carrying props is the
only sector that has ever killed the game.**

**The test.** `gen_sector.py` grew a node-level `disabled` flag, filtering in
`placements()` and nowhere else - that list is what ids, positions, nodeData and
nodeRefs are all built from in lockstep, so a node leaving it leaves the sector
completely while the survivors keep their numbering and `meet_mara`'s
`sceneLocation` still points at the marker it always did. The skip prints per
node for the same reason the sector-level skip does: a node quietly absent is
indistinguishable from a node that failed to build. `validate.py` reads
`source/world.json`, not `build/`, so `"interaction": "#ac_splinter_box"` in the
graph stays legal and the quest is unchanged - only the world differs. All four
suites pass (`96/96` negtest, replaytest and shapetest clean).

Archive `6e9ccc7bb6846ee8c62cb4a888aea3bf`, 4 KiB smaller than
`bb58a308...` - three device nodes' worth. Built, not deployed.

`await_box` waits on `interaction: #ac_splinter_box`, which can no longer fire,
so the run past that point needs the CET panel's `ashcache_box_opened` - the OR
branch that node has carried since D1 for exactly this case.

**If the clinic stops crashing**, the null-`instanceData` device master is the
answer to both the crash and the missing interaction prompt, and OI-13's
remaining half is answered too: a device `.ent` needs its buffer. **If it still
crashes**, the props are cleared and the suspects are the markers, the trigger
at the entrance, or the streaming block itself - and the next cut is the whole
clinic sector.

### D78 - the props are cleared too, and the three 93CABB10 crashes are one deterministic bug (2026-09-10 11:45)

D77's test ran. The player deployed `6e9ccc7bb6846ee8c62cb4a888aea3bf` at 11:28 (md5
verified against the repo build, not assumed), launched at 11:28:09, and the game
died at 11:36:12 in the same square metre. **The three device masters are not the
cause.** D77's hypothesis is withdrawn in full.

The run itself was clean in every other respect, which is what makes the result
worth something:

- The CET dev panel is **not deployed at all** on this install -
  `bin/x64/plugins/cyber_engine_tweaks/mods/ash_cache_dev` does not exist. So the
  panel is not merely unopened, it is absent. CET is out permanently, not "out
  again".
- Audio routed correctly for the first time: `[start] audio:` shows the default
  sink as the Bluetooth headset and all three game streams on sink 16, unmuted at
  100%. The player connected the headphones before launching, which is the fix
  D76 predicted.
- Audioware: "no error reported!", "no scene error reported!".
- The 11:26:10 crash in the same window is `E4044E73`, the known D74 startup race
  (33 occurrences since 2026-08-06). Unrelated.

**The new fact, and it is the important one: the three `93CABB10` crashes are
frame-for-frame identical.** All 14 frames, same IDs, same offsets, and even the
stack scan matches at nearly every slot:

```
[ 0] ID 1912746313+0x1E    <- faults, read at 0xFFFFFFFFFFFFFFFF, RDI = 1
[ 1] ID 3539880448+0xD0    \
[ 2] ID 3759548164+0x70     |  one subsystem, exe+0x544xxx..0x545xxx
[ 3] ID  686117276+0x55    /
[ 4] ID 3491828114+0x65    \
[ 5] ID 1344613639+0x752    |  one subsystem, exe+0x74Bxxx..0x74Dxxx
[ 6] ID 2380012562+0xDF    /
[ 7] ID 2241008910+0xF8
[ 8] ID 3270714933+0x44
[ 9..11]                      redDispatcher job-worker tail
```

D77 read the *variety* of signatures at this coordinate as evidence of corrupted
state surfacing on random threads. That reading was half wrong. Three of the five
crashes are not random at all - they are one deterministic code path, reproduced
exactly, twice on 2026-09-09 and again today. Only `17370EC2` and `E815263E` are
different, and those are one occurrence each. The corrupted-state story may still
explain those two; it does not explain `93CABB10`, which needs a cause that
produces the *same* call every time.

`read at 0xFFFFFFFFFFFFFFFF` with `RDI = 1` and `R13 = 1` is the shape of a lookup
that returned -1 for "not found" and was used without checking - a hash miss
dereferenced as a pointer. That is a mod-flavoured failure: hashed depot paths,
CNames and NodeRefs are exactly what a mod can get wrong.

**`93CABB10` has never appeared outside the clinic.** Full census over all 249
`crash_*.log`, 2026-08-06 to today: 3 occurrences, all of them 2026-09-09 20:50 or
later, all at `-1899,-2479,24`. Five weeks and 240-odd crashes on this install
before that, and not one. The signature is not baseline.

**What the position evidence now rules out, using the motel as the control.** The
shipped world is down to 4 markers (clinic), 2 markers (motel), 1 trigger (probe),
1 spawner (probe_car). The motel sector is markers-only, `AlwaysLoaded` like every
other, and has never crashed in any session. So "a marker node in a mod sector"
is cleared by a control that has been running the whole time. What is left that is
different about the clinic is not its node types - it is that the clinic is *where
the quest's next beat lives*: `await_clinic`, then `await_box`'s
`interaction: #ac_splinter_box`, then `meet_mara` anchored to
`$/03_night_city/ash_cache/#AshCache/#ac_mara`.

**The 25 m sphere is not the trigger.** `AshCacheGlue.reds` sets
`ashcache_at_clinic` inside a 25 m radius of `ac_clinic_entrance`
(-1891.75, -2486.90, 27.95). Computed against the breadcrumb, the player was
inside that sphere from 11:34:21, left at 11:35:02, re-entered at 11:35:17, and
did not die until 11:36:12 - nearly two minutes inside it, including a save. The
fatal step is the descent from z=28 to z=24 at that XY, not the area entry.

**Next test, and it is a control rather than another guess.** Three hypotheses
have now failed (the CET thread, D73's spawner, D77's device props). Systematic
debugging says that is the point to stop bisecting inside the suspect and ask
whether the suspect is the right one at all. `tools/modoff.sh` takes every
deployed piece of ash-cache out of the game tree by `mv` - archive, `.xl` and
`r6/scripts/AshCache` - into `/mnt/ssd/Cyberpunk 2077/ashcache-off/`, and `on`
puts them back byte-identical. One run, walk to the same spot:

- **Still crashes** -> the mod is cleared entirely, `93CABB10` belongs to the
  install or to that interior, and every bisect planned inside this repo is wasted
  work. The census makes this the less likely outcome, which is exactly why it is
  worth ruling out before spending more runs.
- **Does not crash** -> it is ours, and the next cut is the quest half against the
  world half, because the motel control has already cleared the world half's node
  types.

The archive is unchanged by this - `6e9ccc7bb6846ee8c62cb4a888aea3bf` stays
deployed and the props stay disabled until there is a reason to bring them back.

### D79 - the control ran, my piece list was short, and the clinic bug is one instruction (2026-09-10 12:20)

**modoff.sh as first written was not a control.** Its PIECES list had three of
the six paths `deploy.sh` installs. The 11:54 run therefore left `r6/tweaks/ash_cache.yaml`,
the Audioware bank `r6/audioware/ash_cache` and the CET panel `ash_cache_debug`
installed. The user spotted this and started moving pieces out by hand into
`/mnt/ssd/Cyberpunk 2077/copy` at 12:12-12:16. `tools/modoff.sh` now carries the
full six-path list and a `check` subcommand that diffs it against `deploy.sh`
and refuses to be trusted if the two drift.

**Related and worse: I said the CET panel was not deployed.** It is - the
directory is `ash_cache_debug`, not `ash_cache_dev`. `init.lua` (55 KB) is
rewritten by every deploy, last at 11:53:05. D78's "CET is out permanently"
is withdrawn. `deploy.sh`'s PAIRS/DIRS list is the inventory; guessing path
names is not.

**What the 11:54 run still proves.** `crash_20260910_120127.log`'s mod inventory
contains zero `ashcache` entries - no archive, no archiveXL, no reds - so the
world data, the quest phase and the scene were genuinely absent. That session
ran 11:54:06 -> 12:01:13 (`OnWorldDetached`), then CET faulted on the main
thread at `cyber_engine_tweaks.asi+0xAC37`, signature `134F61BD`: the most
common crash on this install, 84 of 255 logs, on the way out of the world.
Not the clinic bug. The mod went back in at 11:59 and the very next session
(12:05:06 -> 12:10:42) died at `-1899,-2479,24` again.

**Signatures were hiding that two crashes are one.** `417F3DF0` (12:10:42) is
a new signature but the same instruction as `93CABB10`:

```
        sig        fault                          instruction
  93CABB10   read  at 0xFFFFFFFFFFFFFFFF   Cyberpunk2077.exe+0x1D173BE  ID 1912746313+0x1E
  417F3DF0   write at 0x0000000000000001   Cyberpunk2077.exe+0x1D173BE  ID 1912746313+0x1E
  top four IDs identical: 1912746313 | 3539880448 | 3759548164 | 686117276
  registers: RAX/RDI/R13 = 1 in the write case, RDI/R13 = 1 in the reads
```

The signature folds in the access type, so a read-modify-write instruction
hashes two ways. **Census by instruction ID, not signature.** Done over all 255
logs, ID `1912746313+0x1E` appears 4 times: 09-09 20:50, 09-09 21:43, 09-10
11:36, 09-10 12:10. Zero before 09-09 20:50, across five weeks.

**And it cuts the other way: `E815263E` is baseline.** Its instruction is ID
`3858698886+0x20`, the same as `5F58BEDF` at 09-09 15:34, hours before and
nowhere near the clinic. So the clinic does not have "three unrelated stacks
dying in one spot" - it has one recurring bug plus the machine's normal noise.
D77's corrupted-state reading is withdrawn in full.

**Shape of the fault, restated.** The pointer being dereferenced holds `1` or
`-1` - sentinels, not addresses, and both appear at the same instruction with
a `1` sitting in RDI/R13. That is a handle or token used without checking
whether it resolved. The player was standing still at `-1899,-2479,24` for
seven seconds before the first-chance (12:10:29 arrival, 12:10:36.615 fault),
so it is not entry, not the 25 m area sphere, and not an interaction - it is
something completing a load while the player stands there.

**Next cut, and it is inside the archive, not around it.** The two archive files
are the only pieces that carry world data, the quest phase and the scene. Cut
those two alone and leave the loose files installed; that isolates the half
that can produce a resource-handle fault.

### D80 - the user ran the only control that counts, and it is our archive (2026-09-10 12:37)

At 12:12-12:18 the player moved **every** mod on the install out of the game tree
into `/mnt/ssd/Cyberpunk 2077/copy`, then at 12:21 put back **only ours**. The
12:21:19 session therefore ran with two archives in `archive/pc/mod` - both
`ashcache` - one CET mod (`ash_cache_debug`), our tweak record, our redscript and
our voice bank, and nothing else. Their report: the game started on the first
attempt, loaded fast and the frame rate went up. Then, 50 s after
`OnWorldAttached`, `crash_20260910_122313.log`:

    93CABB10   read at 0xFFFFFFFFFFFFFFFF
    Cyberpunk2077.exe+0x1D173BE   ID 1912746313+0x1E   thread 500 "redDispatcher1"
    RDI = 1, R13 = 1;  top four IDs identical to the other four

That is the fifth hit of the clinic instruction and the first with a clean
install underneath it. **The bisect is over: the fault is in our archive.** Every
"it crashes here too" argument from the baseline crash rate is now irrelevant -
the baseline was 3,081 archives and is currently 2.

Two side findings from the same run. The startup fault (`E4044E73`, D74) did not
fire once with the mod list emptied, which is consistent with it being a
third-party load-order race and not ours - but it is one observation, not a
census. And the frame rate rising is not evidence about us either way; 3,079
archives came out at the same time.

**What is left in the archive, and what changed when the crash started.** The
live world content, after D77 turned the three props off, is six
`worldStaticMarkerNode`s, one `worldTriggerAreaNode` and one
`worldPopulationSpawnerNode`. Lining the sources up against the census:

| candidate | status |
|---|---|
| `ac_probe_npc` (`Character.*` spawner, D73) | off since before crash #2; crash continued |
| the three props (`worldEntityNode`, D77) | off since the 02:54 build; crashes #3 #4 #5 |
| six markers | all-zero nodeData, unchanged for weeks, motel sector has never crashed |
| `ac_probe_trigger` | unchanged since it was authored |
| **`ac_probe_car`** | **moved -1916.6,-2467.91,24.06 -> -1953.87,-2479.25,28.62 on 2026-09-09** |

The old coordinate is the one D-coords called *unreachable* - a derived point,
buried, where the spawner had nothing to stand on and (`sc_ac_probe_car.jpg`)
never produced a car. The new one is a verified square of street outside the
clinic. The instruction's first fatal is 2026-09-09 20:50 and there is none in
the 251 logs before it. That is the only structural change inside the window.

Two independent reasons to distrust the node beyond the timing:

- `spawnOnStart: 1`. `reference/sectors.md` records `spawnOnStart: 0` in **every**
  vanilla quest-content spawner sampled; ours fires itself at stream-in, on a job
  thread, which is where the fault lands.
- `appearanceName: "default"`. That is the `worldEntityNode` prop convention
  (`gen_sector.py` defaults all three node kinds to it). A Galena's appearances
  are `thorton_galena__basic_*`; `Vehicle.hackable_thorton_galena` resolves to
  `v_standard2_thorton_galena` -> `base\vehicles\standard\v_standard2_thorton_galena_01__basic_01.ent`,
  and nothing in a vehicle `.app` is called `default`. A CName that resolves to
  nothing is exactly the `-1` this instruction dereferences.

**The cut.** `ash_cache_probe` and `ash_cache_probe_car` are both disabled at the
sector level - neither is quest content, and the control the car existed to
provide is already moot (the FIA agent rendered, D73 follow-up). The archive now
contains **six inert marker nodes and no other world node at all**. Built
13,987,840 B, md5 `0ebdad641923df831c4aeb3ee3dcf140`; validate / negtest 96/96 /
replaytest / shapetest all pass.

This is deliberately not a one-variable step. One variable was the right shape
for crash #3; it is the wrong shape for crash #5, because the question is no
longer "which node" but "is it a node at all". If the clinic still dies with this
archive, no world node can be the cause and the search moves to the questphase,
the journal and the ArchiveXL block. If it lives, the two probes come back one at
a time and the car is the first suspect.

### D81 - a shipping voiced quest mod read field for field, and 20 dead audio events removed (2026-09-10 13:00)

The player supplied `AldecaldosHighStakes 1.3.4` and asked how a working mod
does audio. It was unpacked to `wk_scratch/aldecaldos/` and compared against our
build resource by resource. **It uses no Audioware at all** - pure engine path:
23 `.wem` in the archive, a `locVoiceoverMap`, subtitles, a `.lipmap` per
locale, all registered in the `.xl`.

WHAT MATCHES, AND THEREFORE IS NOT THE BUG

  - `scnscreenplayDialogLine`: same fields, same shape. Their
    `locstringId.ruid` 159050490332091896 is `0x02350f94099895f8`, and their
    lipsync names are `f_02350f94099895f8` / `m_02350f94099895f8` - the ruid in
    hex. Ours is `0x6B4BCE4968EEC000` = 7731500000000000000 with
    `f_6B4BCE4968EEC000`. Identical convention, arrived at independently.
  - stringIds agree across all three of our files: 43 subtitle entries, 43
    vomap entries, 27 + 16 scene events.
  - `locStore` empty in both. `voInfo` empty in both. Same 27 top-level keys.
  - `scnSceneEventId` may be huge: theirs runs 0 .. 9223372036854775807. Our
    19-digit ids are legal, and that suspicion is dead.
  - Our `.wem` is a valid Wwise RIFF. `vgmstream-cli` reads it as "Audiokinetic
    Wwise RIFF header", 16-bit LE PCM, 48 kHz, mask 0x4 FC.
  - VoiceOver language in `UserSettings.json` is `en-us`, so the en-us-only
    vomap in our `.xl` is the right one. (Aldecaldos maps all 19 locales to its
    one file; cheap insurance we do not currently need.)

WHAT DIFFERS

  1. **20 dead `scnAudioEvent`s.** We emitted one per voiced line naming
     `ash_cache_vo_<line>` with `emitterName` = "default". Neither CName is
     defined anywhere. Aldecaldos carries ONE in the scene read here and it
     names `mus_q114_saul_briefing_02_STOP`, a vanilla bank event; none of its
     dialogue lines has one. Audioware never reads a scnAudioEvent: its only
     scene path is the `AUDIO_PLAY_DIALOG_LINE` detour keyed on the line's
     `string_id`, and its `AudioInterface::PostEvent` hook only logs and calls
     on. **Removed.** Two unresolvable hashes per line, on the audio thread, at
     line start, is also the exact shape of the faults this quest keeps logging.
  2. **`alwaysUseBrainGender` 1 -> 0.** Theirs is 0, Hot Fuzz's is 0; 1 is what
     a scene with no recordings sets. We have 43.
  3. **Codec.** Theirs is Wwise Vorbis (`fmt` tag 0xFFFF, 66-byte fmt, stereo,
     with `cue `/`LIST`); ours is PCM (0xFFFE, 24-byte fmt, mono). This is the
     link `tools/wav_to_wem.py` has flagged as unverified from the start.
     Aldecaldos is the 25th mod checked and still zero PCM examples on the
     voiceover path.
  4. **No `stringidvariantlengthsreport` entries.** Audioware's own
     `book/pages/SCENE_DIALOG_LINES.md` documents this as required and says
     ArchiveXL cannot make one - the only route is a Codeware
     `Resource/PostLoad` callback pushing `locVoLengthEntry` per line. We ship
     none. This is now the leading explanation for "subtitle shows, no sound"
     and for "the voice said one word and then stopped".
  5. They ship `.anims` + 19 `.lipmap`s; we ship none. That is OI-17, separate.

Also recorded, from their `tweaks.yaml`: `Vehicle.sq_hs_behemoth` sets
`appearanceName: militech_behemoth_basic_arasaka` - a real named appearance.
Independent confirmation that "default" is not a vehicle appearance.

Build after the cut: `ashcache.archive` 13,987,840 B, md5
`0da018da384d11ac4e8e3ba2aa54a909`. Zero `scnAudioEvent` in either scene.
validate OK, negtest 96/96, replaytest OK, shapetest OK.

### D82 - the sound was never ours: Audioware's redscript half is not installed (2026-09-10 13:15)

`audioware-2026-09-10-13-07-53.log`, the session the user tested at 13:07:

```
for a total of: 774 scene id(s)
no scene error reported!
[13:09:22.798] [warning] [456] scene is not available, and therefore dialogs aren't either
[13:09:27.989] [warning] [456] scene is not available, and therefore dialogs aren't either
```

Two lines asked for, two lines refused, then a fatal access violation at
13:09:28.348 (first chance) / 13:09:33.853.

THE CHAIN, ALL FOUR LINKS READ IN SOURCE

1. `crates/audioware/src/engine/mod.rs:252` - `play_scene_dialog()` opens with
   `let Some(ref mut scene) = self.scene else { warns!("scene is not available,
   and therefore dialogs aren't either"); return; }`. That is the exact string
   in the log, and it returns BEFORE touching the bank.
2. `engine/queue.rs:276` - the only thing that ever fills `self.scene` is
   `Lifecycle::Session(Session::Ready) => engine.try_new_scene()`.
3. `abi/mod.rs:328` - `Session::Ready` is queued by the native function
   registered as `Audioware.OnGameSessionReady`, i.e. it is called FROM
   redscript, not from a native game-state hook.
4. `r6/scripts/Audioware/Service.reds:31` - the one caller: a Codeware
   `Session/Ready` callback whose case arm calls `OnGameSessionReady()`.

And `r6/scripts/` on this install (mtime 12:21, when the user cleared the mod
tree) contains exactly one directory: `AshCache`. The redscript compile log for
this very session lists 44 source files and not one of them is Audioware's -
ArchiveXL, Codeware, TweakXL, NewGamePlus, mod_settings and the rest all ship
their reds under `red4ext/plugins/<name>/`, which survived; Audioware is the one
that ships its half under `r6/scripts/Audioware/`, which did not.

So `engine.scene` was `None` for the whole session and EVERY scene dialogue line
was dropped at the guard. Not some. Not ours in particular. All of them.

WHAT THIS RETROSPECTIVELY EXPLAINS

- "in cet working playing audio but if set fact 3 from cet showing subtitles but
  not playing any sound" - the CET button plays through `AudioSystem::Play(CName)`,
  the `voices:` registry, which needs no scene. The scene path needs the scene.
- "the voice said one word, and it crashed" (2026-09-09, before the tree was
  cleared) - that was Audioware working.
- The 774 scene ids and "no scene error reported!" every session since: the bank
  loads perfectly. Loading and playing are different subsystems, and only one of
  them was broken.

WHAT IT DOES NOT EXPLAIN, AND I AM NOT CLAIMING IT DOES

The crash. `crash_20260910_130933.log` is instruction `766120943+0x6`, signature
`0DC18D53`, thread 508 `redDispatcher4`, read at `0xFFFFFFFFFFFFFFFF` with
RDX = 1 - the third first-ever signature in three tests. It landed 0.36 s after
the second refused line, which is suggestive and nothing more.

THE FIX, WHICH IS NOT A CODE CHANGE

Restore the 18 files. `/mnt/ssd/Cyberpunk 2077/copy/r6/scripts/Audioware/` holds
them and `diff -r` says they are byte-identical to
`/mnt/sata/audioware-wakeup-only/crates/audioware/reds/` minus the Debug/ folder -
and `audioware-wakeup-only` is the build actually installed (md5
`6ffd5141609dfcaf9de3a8d74d503e12` on both the game's dll and that target dir).
So the scripts match the binary exactly. `module Audioware` namespaces all of it,
its only external import is `Codeware.Localization.*` (installed and compiling),
and its one `@if(ModuleExists("ModSettingsModule"))` guard is satisfied. Nothing
can collide.

CORRECTION TO D81

D81 said the `stringidvariantlengthsreport` work was blocked because Codeware's
redscript declarations were absent from `r6/scripts/`. That was wrong: Codeware
ships its reds under `red4ext/plugins/Codeware/Scripts/`, all five files compiled
at 13:09:54 in the same log. The length report is unblocked. It is being held
back deliberately anyway - one change at a time, and a redscript file that fails
to compile takes the game's boot with it.

### D83 - the crash is older than this mod: 214 of 259 crash logs have no ashcache in them (2026-09-10 13:30)

The user restored `r6/scripts/Audioware/` at 13:20 (D82's one action), launched
13:21:24, and the game crashed at 13:23:14. Reported as "the same crash", with a
pointer at two wiki guides.

**D82's fix landed.** The 13:21 session compiled all 18 Audioware `.reds`
(`session_2026-09-10_13-21-24.log:72-89`), and `audioware-2026-09-10-13-21-53.log`
is 443 bytes containing the id banks and **not one** `scene is not available`
warning - where the 13:07 log had two. `engine.scene` is now populated. Whether a
line is audible is still unproven; the crash arrived first.

**The crash is not ours, and this is now measured rather than argued.**

  crash_20260910_132314.log
    signature 88087014, EXCEPTION 0xC0000005 at Cyberpunk2077.exe+0x53F9D4
    ID: 3858698886+0x20, thread 516 "redDispatcher5", read at 0x1 (RDI = 1)
    Region: not mapped - MEM_FREE, never allocated (wild or stale pointer)

  crash_20260829_013339.log
    signature 88087014, same instruction, thread 512 "redDispatcher2"
    frames [0]-[3] byte-identical: 3858698886+0x20 <- 23729818+0x112
                                   <- 3907986206+0x4B <- 4117243690+0xCF
    `grep -ci ashcache` on that log returns 0 - the mod was not installed.

That instruction has faulted **14 times since 2026-08-06**, always on a
`redDispatcher*` job worker, always a near-null read of a freed region, reached
from at least two different job types. Our first `.wem` was written
2026-09-09 11:25. The stack that crashed today crashed eleven days before this
project had a single voice file.

The wider census over 259 logs in `bin/x64/CrashLogger/`:

  logs where ashcache.archive was installed  ......  45
  logs where it was NOT                       ...... 214   (83%)

  faulting-module culprits named by the logger:
    cyber_engine_tweaks.asi  127     Codeware.dll  93
    ArchiveXL.dll             46     NewGamePlus.dll 22
    let_there_be_flight.dll    4     TweakXL.dll      3

  top two signatures, both predating this mod's VO work by a month:
    134F61BD x84  cyber_engine_tweaks.asi+0xAC37 on the GameThread, Aug 7 -> today
    E4044E73 x33  redDispatcher, null deref, Codeware/NewGamePlus/ArchiveXL, Aug 6 -> today

An `.archive` is data, never a DLL, so ours can never appear on a native stack -
that cuts both ways and is why the count above, not the stack, is the evidence.

**What the two guides the user pointed at actually add.**
`adding-a-custom-voiceline-to-a-scene.md` is already the cited source of
`docs/voiceover.md:143`. Checked line by line against the build:

  locVoiceoverMap / locVoLineEntry / femaleResPath+maleResPath+stringId  - done
  stringId == the scene line's scnlocLocstringId.ruid                     - done
    build/vomap_en-us.json.json entry 0 stringId 7731500000000000000
    == build/ash_cache_mara.scene.json screenplayStore lines[0].locstringId
  registered under `vomaps: en-us:` in the .archive.xl                    - done
  .wem living in localization/en-us/vo/ inside the archive                - done

`how-to-edit-voiceover-and-subtitles-in-a-quest..md` supplies the `m_<hex>` /
`f_<hex>` CName convention on `scnscreenplayDialogLine`. Also already correct:
ours reads `m_6B4BCE4968EEC000` for ruid 7731500000000000000, and
0x6B4BCE4968EEC000 is that number.

**The single divergence is the one we chose knowingly** (`docs/voiceover.md:94-121`).
Byte-level, against the Aldecaldos mod's files, which were made by following this
exact guide:

  theirs  fmt chunk 0x42 (66 B)   wFormatTag 0xFFFF   2ch  48000  40789 B/s
  ours    fmt chunk 0x18 (24 B)   wFormatTag 0xFFFE   1ch  48000  96000 B/s
          + `hash` and `junk` chunks, then raw 16-bit PCM

Ours were never produced by Wwise. The bet - 243 shipped PCM `.wem` prove the
engine decodes PCM - still stands for bank media and is still unproven through
`locVoiceoverMap`'s external-source path, which is the path this project uses.
That gap explains a silent vanilla path. It does not explain a job-system fault
that predates the files.

**Not changed, deliberately.** Audioware's bank is 43 `.wav` and never touches a
`.wem`, so the encoding question does not gate the next test. Nothing was rebuilt
or redeployed for this entry.

### D84 - D83 censused the wrong signature; the clinic instruction is ours, and the vomap is the last thing standing (2026-09-10 16:15)

**D83 is withdrawn in its central claim.** It counted signature `88087014` /
instruction `3858698886+0x20`, found 214 of 259 logs with no `ashcache` in them,
and concluded the crash predates the mod. That census is correct and it is about
the wrong crash. `3858698886+0x20` is the machine's background noise - D79
already said so ("`E815263E` is baseline"). The clinic bug was isolated in
D78-D80 as a different instruction entirely, and D83 walked past it.

    baseline noise   3858698886+0x20   14 hits since 2026-08-06, one of them with
                                       zero ashcache in the log - genuinely not ours
    the clinic bug   1912746313+0x1E   6 hits, ALL with ashcache, none before
                                       2026-09-09 20:50 in 251 prior logs

The 13:23 crash the user reported was the first kind. The 13:39 crash is the
second, and it is the one that matters.

**Crash #6, and it settles D80's open question.** `crash_20260910_133921.log`:

    93CABB10   read at 0xFFFFFFFFFFFFFFFF
    Cyberpunk2077.exe+0x1D173BE   ID 1912746313+0x1E   thread 548 "redDispatcher13"
    RDI = 1, R13 = 1
    14 frames, byte-identical to crash #4 (417F3DF0, 12:10) for the whole walk

That session ran on the archive deployed at 13:07 - the D80 build, six inert
marker nodes and **no other world node at all**. D80 wrote: "If the clinic still
dies with this archive, no world node can be the cause." It died. **No world
node is the cause.** `ac_probe_car`, the prime suspect there, is cleared with the
rest of them.

**The user handed over the reproducer.** Their words: *"in cet audio is playing
but when click fact 3 game crashing"*, and earlier *"if set fact 3 from cet
showing subtitles but not playing any sound"*. "fact 3" is the Acts tab, button
`Act 3 - at the clinic, box found` (`build/cet/init.lua:48`), which queues
`ashcache_start`, `ashcache_at_motel`, `ashcache_courier_log_played`,
`ashcache_at_clinic`, `ashcache_box_opened` and sets `ashcache_progress = 2`.
So the sequence is: Audioware's own playback works, the graph advances, the scene
runs, **the subtitle renders, the voice line does not sound, and a job worker
faults.** That is not a world node streaming in. That is a line of dialogue
failing to resolve its audio.

**Two things changed on 2026-09-09; one is now eliminated.** D80 named the window
correctly - the instruction's first fatal is 20:50 and there is nothing before it
in five weeks of logs. Inside that window:

| change on 2026-09-09 | status |
|---|---|
| `ac_probe_car` moved to a reachable street square | out since the D80 build; crash #6 followed |
| **43 `.wem` + `vomap_en-us.json` first packed** (build at 20:21, first fatal 20:50) | **untested** |

The vomap is the only structural change left in the window that produced the bug.

**And it is the one place the build knowingly diverges from every shipping mod.**
`docs/voiceover.md:94-121` chose raw PCM with its evidence and its rule-8 caveat,
and D81's read of AldecaldosHighStakes measured the difference:

    theirs  fmt chunk 0x42 (66 B)  wFormatTag 0xFFFF  2ch  48000  40789 B/s   Wwise Vorbis
    ours    fmt chunk 0x18 (24 B)  wFormatTag 0xFFFE  1ch  48000  96000 B/s   raw 16-bit PCM

D79 described the fault's shape as "a handle or token used without checking
whether it resolved" - the dereferenced pointer holds `1` or `-1`. A voice line
whose media the decoder refuses is exactly that: the scene asks for a sound, gets
a sentinel back instead of a handle, renders its subtitle anyway because
subtitles come from a different resource, and something downstream on the job
thread dereferences the sentinel. The user's report of subtitles-without-sound
immediately before the crash is that story told from inside the game.

**The cut, and it is one file.** `gen_xl.py` gains `ASHCACHE_NO_VOMAP=1`, which
suppresses the `vomaps:` block only. The `.wem` files stay packed; nothing in the
engine resolves them, so the vanilla voiceover path is never entered. Audioware
reads its own `.wav` bank and is untouched - which is why the CET audio test must
keep working through this control. Diff against the deployed manifest:

    51,52d50
    <   vomaps:
    <     en-us: mod\ash_cache\localization\en-us\vo\ash_cache_vo.json

**`deploy.sh` gains `--only SUBSTR`, because D79 was wrong for want of it.** A
full deploy moves six paths, one of which is an archive rebuilt from unchanged
inputs - the same build, not the same bytes (13,987,840 B either way, md5
`0da018da...` deployed vs `31e8daf3...` rebuilt; the packer is not
deterministic). `tools/deploy.sh --only .archive.xl --yes` copies exactly one
file and leaves the archive in the game untouched, so the control has one
variable and it is the right one. An `--only` matching nothing exits 1 rather
than reporting a successful deploy of zero files.

**Wwise on Linux started.** The user supplied the Audiokinetic-Launcher-on-Linux
guide and `/mnt/ssd/Downloads/AudiokineticLauncher-2026.1.1.6296.exe`.
`/mnt/sata/wwise/setup-prefix.sh` builds a prefix at `/mnt/sata/wwise/prefix` -
deliberately **not** the game's prefix, because `dotnet48` and `vcrun2022`
rewrite system DLLs and the game's prefix is the one install that currently
boots. Wine 11.7 Staging, winetricks 20250102, both already present.
`docs/voiceover.md:143` marked headless `WwiseConsole.exe` as TODO under rule 8;
this is the first move on it. The modding guide pins **2023.1.14**, not the
launcher's own 2026.1.1 - the version is chosen inside the launcher, and the
login step needs a human and an Audiokinetic account.

**Prediction, written before the test.** If the clinic survives with the vomap
withheld, the `.wem` encoding is the bug and Wwise is the fix. If it still dies,
the vomap is cleared too, and what remains inside the archive is the questphase,
the journal and the scene resource itself.

### D85 - winetricks' `wininet` verb poisons the prefix for every installer after it (2026-09-10 16:28)

The Audiokinetic Launcher guide says to run
`winetricks winhttp wininet xaudio29 vcrun2022 dotnet48`, and capitalises the
warning that **vcrun2022 is mandatory or every install inside the launcher
fails**. On wine 11.7 Staging in new-wow64 mode that command cannot succeed as
written, and the reason is worth writing down because both failures look like
wine bugs and neither is.

**Two aborts, one cause.**

    wineboot   unimplemented function iertutil.dll.650
               wineboot.c:1051 initialize_internet -> wininet -> iertutil
    vcrun2022  unimplemented function urlmon.dll.CreateUri
               wine vc_redist.x86.exe /q -> urlmon -> iertutil

`winetricks wininet` installs Microsoft's Win7 `wininet.dll` and, knowing it
needs company, pulls `iertutil` in behind it - setting BOTH to
`native,builtin` at prefix scope. Measured with `winedump -j export`:

    wine builtin urlmon.dll     CreateUri (-> iertutil.CreateUri)   forwards BY NAME
    wine builtin iertutil.dll   9 exports, all named, CreateUri = ordinal 2
    Win7 native iertutil.dll    2,444,288 B, exports BY ORDINAL ONLY - no names
    Win7 native wininet.dll     imports iertutil ORDINAL 650

So the override is a scissors:

    native wininet   NEEDS native iertutil    (ordinal 650; builtin stops at 9)
    builtin urlmon   NEEDS builtin iertutil   (name forward; native has no names)

Whichever way iertutil is set at prefix scope, one of the two breaks. Native
breaks `urlmon.CreateUri` for everything in the prefix, which is what killed
`vc_redist.x86.exe`. Builtin breaks native wininet, which is the wineboot
abort. There is no prefix-scope setting that satisfies both.

**Resolution: scope them differently.** The prefix goes builtin, because that
is what the *installers* need and they are the long, expensive part.
`/mnt/sata/wwise/run-launcher.sh` hands the launcher the native pair together
through `WINEDLLOVERRIDES="wininet,iertutil=n,b"`, which lives for one process
tree and is invisible to the rest of the prefix. That is the only combination
that is internally consistent: inside the launcher, native wininet resolves
ordinal 650 against native iertutil; outside it, builtin urlmon still finds a
named CreateUri.

If the launcher's login turns out to work on builtin, drop the override
entirely - wine 11.7's own wininet is capable and the guide's advice to force
native predates it. The override is there to honour the guide, not because we
have evidence the launcher needs it.

**Method note.** `fix-and-resume.sh` runs `wineboot -u` and greps its output
for the two abort strings *before* starting the twenty-minute
vcrun2022+dotnet48 leg. Cheap gate, expensive thing behind it. The grep is
against a file, not a pipe: under `set -o pipefail` a `wineboot | grep`
conflates "wineboot failed" with "the abort message is absent", and those are
opposite verdicts.

**Prefix isolation held.** Everything above happened in
`/mnt/sata/wwise/prefix`. The game's prefix was not touched - dotnet48 and
vcrun2022 rewrite system DLLs, and the install that boots is not a thing to
experiment on. Process accounting after the failed run: zero wine processes
left alive under the Wwise prefix, the game's own tree untouched.

**Meanwhile the D84 control went in.** `ashcache.archive.xl` deployed 16:22:18
at 3,739 B with zero `vomaps:` lines; `ashcache.archive` still 13:07:13 /
13,987,840 B, byte-identical to the one crash #6 ran on. Exactly one thing
moved. `Cyberpunk2077.exe` came up at 16:22:43 and no crash log has been
written since 13:39. The result of that test is the next thing this file
should record.

### D86 - the vomap control cleared the .wem, and the register file named the next suspect (2026-09-10 16:50)

The D84 control ran: `.archive.xl` deployed 16:22:18 at 3,739 B with zero
`vomaps:` lines, `ashcache.archive` untouched at 13:07:13. The game crashed
anyway at 16:24:54.

**Same instruction, not merely the same signature.** `crash_20260910_162454.log`
and `crash_20260910_133921.log` are both `1912746313+0x1E`, both `93CABB10`, both
`read at 0xFFFFFFFFFFFFFFFF`, and a full diff of the two 21,772-byte logs differs
only in timestamp, thread id, memory figures, ASLR bases and the register file.
All 14 frames identical. That is one deterministic code path, reproduced with the
voiceover map removed.

**So the archive's .wem cannot be the cause.** With no `vomaps:` block the game
never resolves a single one of our .wem files, and the crash is byte-identical.
Whatever the raw-PCM encoding does or does not break, it does not do this.

**But the control did not clear "audio" - only that path.** Audioware was fully
live at the crash: `audioware-2026-09-10-16-23-33.log` reports 774 ids AND 774
scene ids, "no error reported", and `redscript_r2026-09-10_16-22-59.log` lists all
18 `Audioware\*.reds` plus `AshCache\AshCacheGlue.reds` with zero errors. Scene
dialogue reaches Audioware through the `AUDIO_PLAY_DIALOG_LINE` detour, not
through the vomap, so removing the vomap removed a path the scene lines were
probably never using. D84 was a control of the wrong half.

**What the register file says.** The new crash carries `RAX 6568636163687361`.
Little-endian, that is the eight bytes `a s h c a c h e` - our own prefix, live in
a register at the faulting instruction. The 13:39 crash had float garbage there.
Per the standing rule, `read at 0xFFFFFFFFFFFFFFFF` with a small integer in an
index register (`RDI = 1`) is a hash lookup that returned -1 and was used
unchecked, and CNames, NodeRefs and TweakDBIDs are all hashed - so an
`ashcache`-prefixed name failing to resolve is exactly the shape on screen.

**Act 3 reaches the scene.** The CET Acts tab queues six fact writes; the graph
runs `box_opened_set -> obj_box_done -> desc_find_box_off -> guard_splinter ->
give_splinter -> mark_splinter -> progress_4 -> obj_mara_on -> desc_talk_mara ->
guard_meet_mara -> route_mara -> meet_mara`. `meet_mara` plays
`ash_cache_mara.scene`. So "the game crashes when I press fact 3" is "the game
crashes in the Mara scene", and the crash lands 42 s after ArchiveXL merged the
phase - not at load, at use.

**Cleared on the way past:** the built scene holds **0** `scnAudioEvent`, so the
unresolvable `ash_cache_vo_<line>` CName is gone and shipped - `gen_scene.py` is
dated 13:00:09 and the deployed archive was packed at 13:07:13. ArchiveXL merged
every block with no error; TweakXL read `ash_cache.yaml` with no error naming any
record of ours; `UINameplate.Always` is real (2 vanilla uses);
`Character.q306_fia_agent_corpo_scene_wa` is real (ep1 q306.tweak:613); `#ac_mara`
is a real marker in an enabled sector. None of those is the fault.

**What is left.** Grepping the built scene for our prefix returns three values and
no others: `specCharacterRecordId = Character.ashcache_mara`,
`dynamicEntityUniqueName = ashcache_mara`, and four `factName` fields. The bare
`ashcache_mara` is an exact match for the eight bytes in RAX. The scene does two
things that resolve a name: it spawns that actor, and it plays lines.

**Diffed against the one shipping voiced quest mod we have.**
`AldecaldosHighStakes`' `sq_high_stakes_regina_brief.scene` spawns two actors.
Field for field against ours:

| field | Aldecaldos (ships, works) | ours |
|---|---|---|
| `alwaysSpawned` | 0 | **1** |
| `prefetchAppearance` | 0 | **1** |
| `spawnMarkerNodeRef` | uint64 0 (none) | **"#ac_mara"** |

It places actors from the scene's own origin instead, which our `meet_mara` node
already sets to `$/03_night_city/ash_cache/#AshCache/#ac_mara` - the same marker,
in its long form. `alwaysSpawned` is the interesting one: it moves the spawn
earlier than scene playback, and the note from 2026-09-09 already reads "the code
path that faults only runs when the spawn actually proceeds".

**Decision: bisect, do not patch three fields at once.** `AC_ACTOR_SPAWN=0` in
`tools/gen_scene.py` builds a scene whose actors are never spawned -
`alwaysSpawned`, `isEnabled`, `spawnOnStart` and `prefetchAppearance` all 0 - while
the resource still carries `Character.ashcache_mara`, `#ac_mara` and every line
and embedded quest node. One variable.

  - survives -> the actor spawn is the fault; match Aldecaldos on the three
    fields above and re-enable.
  - crashes  -> the actor is cleared, and the remaining suspect is the dialogue
    path itself, which is where a real Wwise-encoded .wem finally becomes
    testable rather than assumed.

Built and staged: `ASHCACHE_NO_VOMAP=1 AC_ACTOR_SPAWN=0 tools/build.sh`. The
manifest it produced is **byte-identical** to the one already installed (3,739 B,
no vomaps), so a full `tools/deploy.sh --yes` moves the archive and nothing else.
validate OK, negtest 96/96, replaytest OK, shapetest OK.

Restore afterwards with a plain `tools/build.sh` - the control is not a shippable
state and the build prints a banner saying so.

### D87 - the actor spawn was the crash, and the record was in the wrong field (2026-09-10 17:20)

The D86 control came back on the survives branch. Deployed 16:56, session 17:00,
Act 3 pressed, **no crash** - the same click that had produced
`1912746313+0x1E` twice ran the whole graph without faulting. The only crash log
written afterwards is `crash_20260910_170347.log`, which is a different bug
entirely: `cyber_engine_tweaks.asi+0xAC37`, signature `134F61BD`, main
GameThread, a stale pointer in CET's own ASI. Not ours, not the same instruction,
not the same thread.

What the user saw alongside that is the control working as designed rather than a
second problem: no subtitles, no audio, silence. With `AC_ACTOR_SPAWN=0` Mara is
never spawned, so the scene has no one to speak, and the section that carries
every line has no performer to attach them to. Silence is what "the actor is
gone" looks like from inside the game. The result to read is the one that did not
happen.

So: **the fault is in the spawn**, and D86's branch says match the reference.

Diffing our actor against `AldecaldosHighStakes`' `regina_fake` - the one actor on
this machine that demonstrably spawns *and* speaks - turned up more than the three
fields D86 predicted, and the extra one is the interesting one:

| field (`spawnDespawnParams`) | regina_fake | ours | now |
|---|---|---|---|
| `specRecordId`      | `Character.reggie` | **empty (0)** | `Character.ashcache_mara` |
| `alwaysSpawned`     | 0 | 1 | 0 |
| `prefetchAppearance`| 0 | 1 | 0 |
| `spawnMarkerNodeRef`| 0 | `#ac_mara` | 0 |
| `validateSpawnPostion` | 0 | 1 | 0 |

We had the character record only in the actor-level `specCharacterRecordId`. The
reference puts it in `spawnDespawnParams.specRecordId` - the field the
spawnDespawn plan itself reads - and leaves the actor-level one at 0. Ours ships
both now, carrying the same TweakDBID, so neither convention comes up empty.

That single emptiness explains the shape of the crash better than anything else
found so far. `prefetchAppearance: 1` asks the engine to preload the appearance
*of a record*; with `specRecordId` at 0 there is no record to resolve it through.
`alwaysSpawned: 1` moves that work to resource-prepare time, off the game thread -
and the crash landed on `redDispatcher14`, a job thread, at
`read 0xFFFFFFFFFFFFFFFF`, the shape a hash lookup takes when it returns -1 and
nobody checks. `RAX` held `6568636163687361` = `ashcache`, and
`dynamicEntityUniqueName` is `ashcache_mara`: the name being registered for a
dynamic entity that had no record behind it.

`spawnMarkerNodeRef` goes to 0 because it was never load-bearing. The quest node
already carries `sceneLocation: scnWorldMarker ->
$/03_night_city/ash_cache/#AshCache/#ac_mara`, so the scene's own origin *is* the
marker; a `Local` marker of 0 with a zero `spawnOffset` puts her on the same spot
with one less name to resolve. The short-NodeRef finding from Hot Fuzz is still
true, it is just a second reference to a position we already have.

Cleared on the way, so they are not candidates any more: the lipsync index is not
dangling (`resouresReferences.lipsyncAnimSets` has one entry per actor and Mara's
id 0 resolves to `civ_prst_f_01_enus_30.anims`, exactly as OI-10 records), and
`AC_ACTOR_SPAWN` is kept rather than deleted - it is the one-variable way back to
"is it the actor again?" if this instruction ever returns.

Built with `ASHCACHE_NO_VOMAP=1` so the manifest stays byte-identical (`cmp`) to
the installed 3,739 B file: this test still moves one thing. validate OK,
negtest 96/96, replaytest OK, shapetest OK.

    tools/deploy.sh --yes      # only the archive can differ
    # launch, CET -> Acts -> 3

  - Mara appears and the scene runs -> the spawn was it; the remaining question is
    audio, and that is D88's territory.
  - it crashes again on `1912746313+0x1E` -> re-run with `AC_ACTOR_SPAWN=0` to
    confirm the control still holds, then the fault is elsewhere in the actor
    setup and the next field to move is `appearance`.

### D88 - the Wwise Launcher runs on Wine once powershell stops lying (2026-09-10 17:40)

The installer worked; the launcher did not. It drew no window and quit, and the
log had one cause in it:

    message: 'Failed to retrieve running processes',
    i18nMessage: { key: 'system:process.failedToRetrieveProcess' }
    at async gwe.initCoreServices

Extracting `resources/app.asar` and reading the function that throws it
(`getRunningProcesses`, in `.vite/main/zip-task-*.js`) gives the whole story:

    e = await exec('echo ""; ps | % {$_.Path}', { shell: "powershell" })
    const t = e.split("\n").slice(1).map(i => i.trim()).filter(i => i)
    if (!Array.from(new Set(t)).length)
        throw N({ key: "system:process.failedToRetrieveProcess" })

Wine ships a `powershell.exe` that prints nothing and **exits 0**. So the list is
empty, the app throws before it draws anything - and because the exit code is 0
the launcher's own `catch` never fires, so it never reaches the
`wmic process get ExecutablePath` fallback, which works fine in this prefix.

`shim/powershell_shim.c` answers that one command from
`CreateToolhelp32Snapshot`, plus the format-list `Win32_Process` query that
`systeminformation` sends over **stdin** to a long-lived
`powershell -NoExit -Command -` (its `--###START###--/--##ID##--/--###ENDCMD###--`
protocol is implemented too). Everything else answers empty, exactly as Wine's
stub did - the launcher already survived empty BIOS, baseboard and OS answers.

Two things cost a round each and are worth writing down:

  - **argv was the wrong place to look.** The first version only inspected the
    command line and changed nothing, because Node passes these as `-c <command>`
    for one call and over stdin for the other.
  - **A file in `system32` does not win.** Wine prefers its builtin exe unless
    the name is overridden explicitly, so `run-installed.sh` ships
    `WINEDLLOVERRIDES="wininet,iertutil=n,b;powershell.exe=n"`.

Result: `initCoreServices` completes, every module loads (`wwise`, `Strata`,
`auto-update`), and it reaches `blob-api.gowwise.com` and checks for updates.

    /mnt/sata/wwise/run-installed.sh     # the app
    /mnt/sata/wwise/run-launcher.sh      # the installer, only needed once

`run-launcher.sh` runs the downloaded `.exe`, which only ever installs; that is
why it looked like "the app will not start" - it was starting the wrong binary.
To undo the shim, delete `prefix/drive_c/windows/system32/powershell.exe`; the
Wine builtin comes back and the launcher stops opening again.

Still human-only: signing in with an Audiokinetic account, and installing
**Wwise 2023.1.14** - the version the modding guide pins, not the launcher's own
2026.1.1.

### D89 - Sign In needed a URL round trip Wine could not close on its own (2026-09-10 21:00)

Clicking Sign In did nothing and printed a Wine crash while the window stayed
alive. The log said exactly where:

    [auth.service] Requesting sign in - Opening browser, waiting for answer...
    err:module:find_forwarded_export function not found for forward
      'iertutil.CreateUri' used by L"C:\windows\system32\urlmon.dll"
    wine: Call ... to unimplemented function urlmon.dll.CreateUri, aborting

The window survives because what aborts is the helper thread doing
`shell.openExternal`, not the app.

**Cause.** winetricks had left a NATIVE `iertutil.dll` (Win7, 2010) in system32,
and D88's runner forced it with `WINEDLLOVERRIDES=wininet,iertutil=n,b`. That
DLL exports **681 functions under 10 names** - `CreateUri` is reachable by
ordinal only. Wine's builtin `urlmon` forwards `CreateUri` to iertutil BY NAME,
so the forward misses. Wine's own iertutil exports it by name at ordinal 2. The
two builtins are a matched pair; the native pair would need a native urlmon too.
The prefix registry already said `"*iertutil"="builtin"` - the env var was the
only thing forcing native, and it had been copied in from the *installer*
runner, where it was never needed either.

Proved one-variable with `shim/uritest.exe`, which does nothing but
GetProcAddress:

    iertutil=n,b   -> RESULT: FAIL - CreateUri unresolved (err 127)
    builtin        -> RESULT: OK - hr=0x00000000, real URI object

Fix: drop `wininet,iertutil=n,b` from `run-installed.sh`, leaving
`powershell.exe=n`. Native wininet is unwanted anyway - it imports iertutil by
ordinal, which is the "iertutil.dll.650" wineboot crash, and Chromium does its
own networking.

**The other half.** Login answers come back as `ak-launcher://signIn?code=...`.
The launcher registers that scheme *inside* the prefix on first run
(`user.reg: [Software\Classes\ak-launcher\shell\open\command]`), but the browser
doing the redirect is a Linux program and cannot read the Wine registry, so the
redirect dead-ended. Added `/mnt/sata/wwise/wwise-url.sh` plus
`~/.local/share/applications/wwise-launcher-url.desktop`, registered with
`xdg-mime` for `wwise-launcher`, `ak-launcher` and `ak-bug-reporter`. Electron's
`handleArgs()` takes the first argv matching `/.*:\/\/.*/`, and the app's
single-instance lock forwards it to the running window.

Verified live before asking for a real login, with a probe scheme:

    app.handleSecondInstance() argv:...,wwise-launcher://selftest?token=probe

and then for real:

    ak-launcher://signIn?code=5706f9e6-... -> [auth.service] Sign in completion...
    -> launcher/signin/success

Outbound chain confirmed intact: winebrowser -> xdg-open -> exo-open ->
`/usr/bin/zen` (Xfce's helpers.rc names a custom WebBrowser helper; the
`custom-WebBrowser.desktop` that `xdg-settings` reports does not exist as a file
and is a red herring).

### D90 - the Wwise install failed on a race, not on a missing prerequisite (2026-09-10 21:25)

Installing 2023.1.14 died in 410 ms with "An unexpected error has occurred.
Unable to start the installation process." The prerequisite step's own output
was still sitting on disk:

    Starting prerequisites installation...
    Creating directory: C:\Audiokinetic\Wwise_2023.1.14.8770
    Prerequisites installation complete in 1542ms

It **succeeded** - in 1542 ms, against a parent that gave up after 410.

**Cause.** `Oee()` (the Windows elevation) writes `runAsAdmin.lnk` targeting the
launcher's own exe with `--installPrerequisites=<json> --stdoutFile=<f>`, sets
the RunAsAdmin bit, and `exec`s the shortcut. Windows' cmd blocks until the
elevated child exits. Wine's shell32 resolves the link and launches the target
DETACHED, so `runSelfAsAdmin` reads `stdout.txt` while it is still the empty
file it wrote a moment earlier, `if(!n) throw` fires, and its `finally` deletes
the files the child is about to write.

Measured, not assumed - a shortcut to a 3-second batch file:

    cmd /c slow.bat   8.6s     (the target, waited for)
    cmd /c slow.lnk   0.29s    (same target, detached)

and the target's own trace showed it running to completion afterwards.

No setting avoids the elevated path: `Dhe()` marks `targetDir` `sudo:true` for
every install type except CreateStandalone, and `Fhe()` sets `envVariables` for
Wwise on Windows regardless, so `OI()`'s early `return []` is unreachable.
Neither lever on the launch worked either, both tested:

    lnkfile\shell\open\command handler   ignored - the TARGET ran, not the handler
    .LNK added to PATHEXT               ignored - still 0.29s

**Fix.** node's `child_process.exec` spawns `process.env.comspec`, so
`shim/cmdwait.c` -> `system32/cmdwait.exe` becomes ComSpec. It rebuilds the
command line with the real cmd as argv[0], waits for it, propagates the exit
code - and *only* when the command mentions a `.lnk`, then waits for
`%TEMP%\WwiseLauncher\stdout.txt` to appear and stop growing before returning.
The parent then reads the real output the real child really wrote. It fabricates
nothing: a genuine prerequisite failure leaves the file empty, the wait times out
at 240 s, and the launcher reports the same error Windows would.

Wine takes ComSpec from the registry and ignores the environment variable, so it
is set at
`HKLM\System\CurrentControlSet\Control\Session Manager\Environment\ComSpec` =
`%SystemRoot%\system32\cmdwait.exe` (REG_EXPAND_SZ, matching how it shipped).
To revert, put back `%SystemRoot%\system32\cmd.exe`.

Verified: `exit /b 7` propagates as 7, output passes through, and the .lnk branch
waited 2.44 s for a write delayed by 2 s instead of returning at 0.29 s.

### D91 - the ComSpec wrapper broke every exec() because of its filename (2026-09-10 22:00)

D90's `cmdwait.exe` fixed the .lnk race and broke everything else. The symptom the
user saw was the install page's **Next** button permanently greyed out - not
clickable, no error text, no tooltip, nothing in the log.

Reading the renderer bundle (`.vite/renderer/assets/launcher-icon-DcPLLWE8.js`,
misnamed - it is the app, not an icon) the button is

    disabled: !he || !b || !!Le

`b` is react-hook-form's `isValid`, which starts **false** and only flips once
every async field validator RESOLVES. A validator that never settles disables the
button and renders no error, because there is no error - only an unfinished
promise.

The launcher exposes `require` in the renderer (nodeIntegration on), so with
`--remote-debugging-port=9222` the RPCs can be called directly. That is the proof:

    system:checkDisksSpace    -> ok, 73 ms
    system:validateDirectory  -> still pending at 20 s

and one level down:

    cp.execFile("C:\\windows\\system32\\cmd.exe", ["/d","/s","/c","net use C:"])  -> 330 ms
    cp.exec("net use C:")            (i.e. via ComSpec)                          -> pending at 25 s
    cp.exec("echo hello")            (i.e. via ComSpec)                          -> pending too

But `spawn("C:\\windows\\system32\\cmdwait.exe", ["/d","/s","/c","echo hello"])`
returned in 711 ms. So the wrapper works; `exec` through it does not. `ps` said
why - the hung processes read

    C:\windows\system32\cmdwait.exe -c net use C:
    C:\windows\system32\cmd.exe     -c net use C:

`-c`, not `/d /s /c`. node picks the argument style from the shell's NAME:

    if (/^(?:.*\\)?cmd(?:\.exe)?$/i.test(file)) args = ['/d','/s','/c', `"${command}"`];
    else                                        args = ['-c', command];

`cmdwait.exe` fails that regex, so node addressed it as a POSIX shell. cmd has no
`-c`, ignores it, and opens an INTERACTIVE session on a stdin nobody will ever
write to. Every single `execCommand` in the launcher hung forever. Two dozen
`cmdwait.exe`/`cmd.exe` pairs were still sitting in `ps` from the probes.

Fix: the same binary, installed under the name node insists on, in a directory of
its own so it does not shadow the real one -
`C:\windows\cmdwait\cmd.exe`, with ComSpec pointing there. `REAL_CMD` still names
`C:\windows\system32\cmd.exe`, a different path, so there is no recursion.
`posix_to_cmd()` in cmdwait.c translates a leading `-c` anyway, as a second line
of defence rather than the fix.

Verified after the change, live in the running app:

    process.env.ComSpec      C:\windows\cmdwait\cmd.exe
    exec("echo hello")       1502 ms, stdout "hello"
    exec("net use C:")       1878 ms, fails as it should (C: is not a mapped drive)
    system:validateDirectory 1767 ms, {"errors":[],"warnings":[]}

and the install the user could not start ran to
`Install operation completed successfully.` - 202 MB at
`prefix/drive_c/Audiokinetic/Wwise_2023.1.14.8770`, with `Wwise.exe` and
`WwiseConsole.exe` under `Authoring/x64/Release/bin`.

Note for the .wem work: `bin/Plugins/DefaultConversions.xml` declares Vorbis,
Opus, PCM and ADPCM with `Platform Name="Any"`, so the Authoring-only install
converts for Windows. The unchecked Deployment Platforms are SDK libraries for
building a game, not codecs.

To revert everything: ComSpec back to `%SystemRoot%\system32\cmd.exe`.

Method note: the useful move was not reading more minified JS, it was
`--remote-debugging-port` plus `require("electron")` in the renderer - one probe
turned "the button is greyed out" into "this named promise never resolves".

### D92 - the .wem are real Wwise Vorbis now, made headlessly (2026-09-10 22:20)

Wwise 2023.1.14.8770 installed (D91), so the hole wav_to_wem.py's header has
been honest about since it was written is closed. That hole: PCM .wem is proven
on the soundbank-media path (127 vanilla files, 116 in LizziesBDs) and NOT on
the locVoiceoverMap path, where all 342 custom voice lines across the 24
installed mods that ship a vomap are Wwise Vorbis. Our 43 were PCM.

**The GUI route in the guide is not needed.** `WwiseConsole.exe` ships in the
same Authoring tree and runs under Wine unmodified:

    $ /mnt/sata/wwise/wc.sh --help
    Wwise | v2023.1.14 | Build no.8770
    Operations: convert-external-source  create-new-project  ... waapi-server

Two commands do the whole of "new project -> Source Settings -> Vorbis Quality
High -> Import as Sound SFX -> ShareSets -> Convert":

    create-new-project      C:\wwproj\ashcache\ashcache.wproj --platform Windows
    convert-external-source C:\wwproj\ashcache\ashcache.wproj
        --source-file <list.wsources> --output Windows <dir>
        --platform Windows --no-wwise-dat

EXTERNAL SOURCES is the right primitive and not a workaround. It is Wwise's own
batch route for audio a game provides at runtime, which is exactly what a vomap
entry is: a .wem named by path that no project object references. The Import
route in the guide builds Sound SFX objects in the Actor-Mixer hierarchy that
this project would never look at again.

`--no-wwise-dat` matters: without it Wwise drops a `Wwise.dat` dependency file
in the output directory, and the output directory here is vo/<locale>/, which
is a manifest that must hold audio and nothing else.

The ShareSet is the factory `Vorbis Quality High` the guide names. Read out of
`Conversion Settings/Factory Conversion Settings.wwu`, its Channels and
SampleRate are both "as input" - the guide has you set Mono / 48000 by hand
because a hand-recorded line is usually 44.1k stereo. Ours come out of RVC at
48 kHz mono already (ffprobe: pcm_s16le,48000,1,16 on every one), so "as input"
lands on the guide's numbers without touching anything.

Result, all 43 lines, 2.5 s wall:

    fmt tag  0xFFFF   1 ch   48000 Hz   fmt chunk 66 bytes    x43, no exceptions

which is byte-shape identical to the reference, Aldecaldos'
`sq_hs_aldo_intro_m_72c02868d4f11070.wem` (0xFFFF, 48000, fmt 66; stereo and
carrying extra cue/LIST chunks from its authoring, neither of which is
required). vo/en-us/ .wem went 14 MiB -> 1.5 MiB, ~10-13% of source per file,
and the packed archive 13.99 MB -> 1.70 MB.

`mara.trust_3.wem` is 3 KiB, still the truncated 0.22 s render. The encoder is
not the problem there; the render is.

**tools/wwise_wem.py** does this and runs BEFORE wav_to_wem.py in build.sh.
Wwise wins where Wwise is installed; wav_to_wem.py then finds every .wem newer
than its .wav and skips all 43, and on a machine with no Wwise it still does the
whole job in PCM. That fallback is why it stays. `--check` says which one will
run without converting anything.

Gates after the rebuild: validation OK (43 voiced line files, 43 audioware
lines), negtest 96/96, replaytest OK, shapetest OK. validate.py needed no change
- its CODECS whitelist already had 0xFFFF, because it was written from a census
of what the game and the installed mods actually ship.

The vomaps block is back in the manifest (a plain build.sh; the D87 control was
built with ASHCACHE_NO_VOMAP=1). So the next deploy re-arms the vanilla
voiceover path, this time with the codec every working example uses. Audioware
is unchanged and still plays the .wav directly - two paths, same recordings,
still generated from the same folder.

Not yet deployed: rule 2 wants the deploy said out loud.

### D93 - the echo was both paths playing, and the engine's path wins (2026-09-10 22:35)

The quest has sound. Reported the same hour D92 deployed: "the sound problem is
officially fixed ... it sounds really cool, just like Vanilla, and you can
hardly tell the difference from the in-game voice", with one defect - "there's a
lot of echo in Rogue's voice".

Not the recordings. vo_polish.py ships every render dry on purpose and its
header says why: "Wwise applies dialogue reverb per space at runtime from its
own buses; the shipped assets are dry and these must stay dry, or the space gets
applied twice." Nothing in tools/ adds reverb, delay or echo - grepped.

It was two copies. Audioware's dialogue detour does not replace the engine's
playback, it adds to it. crates/audioware/src/hooks/audio.rs:

    let modded = Engine::<CpalBackend>::exists_for_scene(&string_id);
    if modded {
        crate::engine::queue::send(Command::PlaySceneDialog { string_id, .. });
    }
    // still let the engine carry on, to handle subtitle
    let out = cb(a1, a2, a3, a4, a5, a6, a7, a8, a9);

That is correct for the mod's ordinary user, whose modded line has no
locVoiceoverMap entry at all: the call-through finds no audio and only fetches
the subtitle. We became the exception at D92. The vomap entry now resolves to
real Wwise Vorbis, so the call-through plays it too - one copy through
Audioware's own mixer, dry, and one through the dialogue bus with the room's
reverb on it, a few milliseconds apart. That is the echo, and it is also the
proof that the vomap path plays: it could not double a line it was not carrying.
Which retires the D67 gamble entirely - the route that "has been silent since
the day it shipped" is the one working, and the workaround is the one to remove.

Kept the engine's. It places the voice on the speaker in 3D, applies the space's
reverb once, ducks music and ambience under it, and is the only path lipsync
(OI-17) can hang off; the player's "hardly tell the difference from the in-game
voice" is a description of that processing. Audioware's route has none of it and
existed only because wav_to_wem.py could not write Vorbis.

Kept it as the FALLBACK, not deleted. gen_audioware.wanted() writes a bank only
when the engine cannot carry the line, and each way it cannot is checked, never
assumed: ASHCACHE_NO_VOMAP=1 (no vomaps block), no .wem in vo/ at all, or a .wem
whose fmt tag is not 0xFFFF - which is exactly the state of a machine with no
Wwise, where wav_to_wem.py wrote PCM. Same primary/fallback shape as
wwise_wem.py -> wav_to_wem.py, one layer up. ASHCACHE_AUDIOWARE=1 forces the
bank back, so a one-thing-moved A/B between the two routes is still buildable.

deploy.sh had a matching hole: its DIRS loop did `[ -d "$src" ] || continue`, so
a bank that stopped being built would have been left installed in the game and
gone on doubling every line - a fix that changes nothing on the machine it was
written for. Mirroring has two directions; it now removes the destination when
the source is gone, and says so in the dry run.

Also corrected, same pass: validate.py counted every source file with no .wem as
"awaiting conversion" including the ones that had one, and printed "(+43
awaiting conversion)" on a run where all 43 were converted. That is the single
number a reader checks to see whether the audio built.

Sizes unchanged in the archive; the game loses 13.7 MB of loose .wav from
r6/audioware/. Gates: validation OK (43 voiced line files, 43 audioware names,
bank off), negtest 96/96, replaytest OK, shapetest OK.

Not yet deployed: rule 2 wants the deploy said out loud.

### D94 - the two crashes are not one bug, and eight identical stacks say which one to chase (2026-09-11 02:20)

The player, after the D93 deploy: "the problem with the echo has been fixed...
The game crashed on the last line, and when i logged back in, I couldn't click
on facts 3 because it crashed."

D93 is confirmed from the game side, not just from the build: the Audioware log
for the 22:43 and 22:45 sessions reports **0 ids and 0 scene ids**, where the
22:25 session (the echo) reported 774 and 774. The bank is out of the tree,
`r6/audioware/ash_cache` no longer exists in the game, and the doubling is
therefore gone by construction.

**Two crashes in that window, and they are different bugs.**

  22:45:13  sig DE41E2DF  ID 766120943+0x6     redDispatcher11  - "the last line"
  22:47:01  sig 93CABB10  ID 1912746313+0x1E   redDispatcher8   - "clicking fact 3"

Both are `read at 0xFFFFFFFFFFFFFFFF`, which is the shape of a hash lookup that
returned -1 for "not found" and was used unchecked - the shape a mod's
unresolvable reference takes. That is where the resemblance ends.

**The fact-3 crash is old and deterministic.** Censused by faulting instruction
rather than by signature (the hash folds in the access type, so one instruction
can produce several signatures - see the note in the crash-evidence memory), ID
`1912746313+0x1E` appears in 8 of 265 crash logs: 2026-09-09 20:50 and 21:43,
2026-09-10 11:36, 12:10, 12:23, 13:39, 16:24, and 22:47. **All eight stack
traces are byte-identical**, all 14 frames, same address-library ids, same
offsets. That is one code path reproduced eight times across two days - through
the props-on build and the props-off build, through the Audioware-bank build and
the vomap build, before the `.wem` existed and after. Nothing done to the audio
this week touches it, and it is the crash that is actually blocking testing.

It also retires D73's suspect. That entry blamed a `worldPopulationSpawnerNode`
carrying a `Character.*` record in `objectRecordId`. The clinic sector in the
current build contains **four nodes, all `worldStaticMarkerNode`** - the spawners
and props have been off since 2026-09-10 12:36 - and the 16:24 and 22:47 crashes
reproduced the same stack anyway. A suspect that is not in the build cannot be
the cause.

**The last-line crash is new.** Every one of its 17 frames appears in exactly
one of the 265 crash logs: this one. The instruction itself, `766120943+0x6`,
appears once more (13:09:34) under a completely different stack, so it is a
shared helper, not a location. A code path never walked before on this machine
is what you would expect from D92: the engine's own voiceover route is now
decoding real Wwise Vorbis for this quest for the first time.

**Ruled out before instrumenting.** All 43 `.wem` were re-read offline with
`vgmstream-cli -m`: 43/43 parse as Audiokinetic Wwise RIFF, Custom Vorbis,
48 kHz. Nothing is malformed or truncated mid-stream. `mara.trust_3` is short
(10,560 samples, 0.22 s) but structurally valid, so it is a bad render, not a
decoder hazard. The codec is not the crash.

**What was built instead of a guess.** Both crashes are a job thread faulting
milliseconds after the main thread did something, and there is no record of what
that something was: the panel's trace lives in memory and dies with the process,
and CrashBreadcrumb - the only source of position - was uninstalled. So
`tools/gen_cet.py` gained a trail file:

  - `trail.log` in the panel's own folder, appended and **flushed per line**. A
    buffered write that never reaches disk is not evidence.
  - every `note()` goes to it, so fact edges and objective transitions are on
    disk as they happen.
  - fact writes are **bracketed**: a `wr->` line before `SetFactStr` and the
    ordinary `write` line after it. A trail ending on `wr->` blames that write;
    a trail ending on `write` says the main thread survived it and the fault came
    out of what it set in motion. Those are different bugs and the log now tells
    them apart.
  - a `pos` line once a second, which is the half of CrashBreadcrumb worth
    keeping. Position beats signature census (D72, D77).

**And a control, not just a meter.** An Acts press queues six fact edges, drained
one per frame - 16 ms apart, a cadence no quest node produces. That is a standing
suspect for a crash that has followed the Acts buttons since 2026-09-09, and it
is also why the trail alone cannot name the guilty edge: all six land inside one
second. Step mode (a checkbox in the Acts tab) drains the queue by hand, one
write per press. It makes each edge a separate, timestamped event - and if the
burst is the cause, it stops crashing. Off by default, because a diagnostic has
to be able to reproduce the crash before it can explain it.

`dev/cet/ash_cache_debug/init.lua` is generated (rule 4) - `tools/gen_cet.py` is
the file that was edited. Gates: validation OK, negtest 96/96, replaytest OK,
shapetest OK (31 types), generated Lua parses. Archive unchanged at 1,695,744 B;
the only deploy difference that matters is the panel.

### D95 - Mara's record goes in one selector, and the game tree had been rolled back (2026-09-15 17:35)

**What the D94 trail said.** The 2026-09-11 10:38 session ran the 02:21 panel in
step mode. Five queued writes landed seconds apart, not 16 ms, and it still
crashed on `1912746313+0x1E` (9th occurrence, byte-identical stack). The trail
ends on `write box_opened = 1`, not on `wr->`, so the main thread survived
`SetFactStr` and a job thread faulted on what the edge released. The first four
writes re-set values the save already held; `box_opened` was the only real 0 -> 1.
**The burst theory is dead.**

**The game tree is not the build.** Checked on 2026-09-15 with size and sha256:
`ashcache.archive` in the game is 13,991,936 B dated 2026-09-10 11:53, and the CET
`init.lua` there carries `BUILD_STAMP 2026-09-10 02:54` and no trail code. The
trail itself proves the 02:21 set was installed at 10:38 on the 11th. So the tree
was rolled back to the pre-D86 set afterwards (panel folder mtime 2026-09-12
18:08), Audioware bank directory included. The 16 crashes on 2026-09-12 21:44-23:34
are all `283315594+0x20` / `E4044E73`, the D74 startup race, not the quest.

**The change.** A second agent's census (`diag/actor_census/`), re-run here:
every `spawnDespawn` actor in the extracted references names its record in
`spawnDespawnParams.specRecordId` and leaves the actor-level
`specCharacterRecordId` at 0. Vanilla Johnny (q103, sq026, sq028) and T-Bug (q004)
do this, and so does Undermine's TweakXL-defined Songbird. D87 set both. Ours is the
only actor of the six that does. `tools/gen_scene.py` now writes 0 there. Built
scene diff before/after: exactly that one field. `.xl`, TweakXL yaml and reds are
byte-identical to the 02:21 set; archive 1,695,744 B as before. validate OK,
replaytest OK, negtest 96/96, shapetest OK, glue lint 0/0, Lua parses.

**Why this is a test and not a fix yet.** At 22:43-22:45 on 2026-09-10 the D93
build, with both selectors set, spawned Mara and played to the last line. At
22:47 the same build crashed on Act 3 from a loaded save. So both selectors do
not crash every spawn; if they are the cause, they crash only the path a restored
quest phase takes. That is consistent with every log so far, and it means the
test has to run from the same save that crashes (progress 3, box not opened).

    tools/deploy.sh --yes      # all five paths plus removal of r6/audioware/ash_cache
    # load the crashing save, CET -> Acts -> 3 (step mode optional), send trail.log

  - survives and Mara speaks: the duplicate selector was it. Then watch the last line
    (OI-22): its stack shares the ~+0x747000-+0x74E000 region with this one.
  - crashes on `1912746313+0x1E` again: the selector is cleared. Next is the
    save-restore path itself. Load that save with `ashcache_mara_choice_made=1` set
    first (the graph skips the scene), which isolates spawn from graph.

### D96 - V's scene voicetag is vanilla's, not 0 (2026-09-15 22:40)

The note at decisions.md:1357 gave the player `voicetagId 0`, on the reasoning that no V lipsync animset ships. That reasoning holds for the lipmap and is wrong for the scene. Every census scene with a player actor except one empty test scene writes V's tag `1103967280742240864`, 16 of 17 in all: 12 vanilla, Hot Fuzz, Regina, and both WolvenKit templates. That includes Regina, which gives the player no lipsync set. Ours was the only scene pairing `0` with a lipsync set.

`tools/gen_scene.py` now writes the vanilla number. Nothing allocates V a tag in `source/voicetags.json`, and V gets no lipmap entry, as before. `validate.py`'s voicetag-0 rule covers NPC characters only, so it is unaffected.

This was made as the one-variable test in OI-21 (2026-09-15 22:40), after Test A cleared the character and every other scene-only difference was ruled out offline. It is not yet shown to fix the crash; OI-21 holds the test and the next suspect.

### D96 update (2026-09-15 23:10) - it fixed the crash

The player deployed D96, released the scene from the CET menu, and got no crash, with subtitles and voices playing. Every earlier scene start on that save had faulted. This took one variable, and it closes OI-21.

### D97 - the OI-21 debug gate is removed and the phase revision is 4 (2026-09-15 23:10)

The `dbg_scene_gate` pause and its `ashcache_dbg_scene_go` fact existed only to separate the pin from the scene start while OI-21 was open. The cause turned out to be D96, so they were removed from `quest_graph.json`, `facts.json`, `glue.json` and `validate.py`, and the CET menu was regenerated without them.

Removing a node forced a `phase_revision` bump, 3 to 4. `gen_questphase.py` numbers nodes by their position in the list. Deleting one mid-graph renumbers everything after it, so a save that is already running the phase would point at different nodes. The rule is to bump whenever a node is removed or inserted ahead of nodes a save may be inside, not only when re-entering the quest start (OI-15 assumed ids are stable).

### D98 - the box and the terminal were never switched back on after D78 (2026-09-15 23:32)

**Symptom (player, 23:26):** the Mara scene does not start by itself; it only works when started from CET. The natural run stops at "Find the black box".

**Evidence, from trail.log:**
- 23:16:43 - the CET Acts button "Act 3 - box found" writes `box_opened = 1`.
- 23:16:44 - `ac_obj_talk_mara` goes ACTIVE.
- 23:16:55 - `mara_choice_made` is set by the scene, with no further input.
- So the scene start itself works. What blocks the natural flow is `await_box`.
- 23:24:05 - the natural run reaches `ac_obj_find_box`.
- 23:24:26-29 - the player stands at -1906.7,-2472.8, less than 2 m from the box position, and nothing happens.
- The built clinic sector held 0 worldEntityNodes.

**Cause:** D77 set `disabled` on `ac_splinter_box` and `ac_terminal_pc` for the clinic bisect. D78 withdrew that hypothesis the same day, because the clinic still crashed without the props, but the flags stayed on. Both `await_box` and `await_terminal` accept the CET fact as an OR branch by design. That kept the quest passable from the debug menu and hid the missing props.

**Change:**
- Removed both `disabled` flags. The backup is `source/world.json.bak-2026-09-15-props-off`.
- No graph change and no phase_revision bump: only the sector changed, so the questphase node ids are untouched.
- The build at 23:30:06 exits 0. Both props ship with their D70 device buffer.

**Still open (OI-13):** on 2026-09-09 the terminal was inert even with the buffer. That test ran while the scene's heap corruption (D96) was still live, so it is weak evidence either way. The CET Devices tab, a look-at probe, answers the question in one look.

### D99 - the clinic doors are opened by the quest; the computers are still silent (2026-09-16 01:30)

**Report (2026-09-15 23:43, two Devices-tab screenshots).** With D98 deployed, both props
load: class `Computer`, `ComputerControllerPS`, state ON, interactive true. Neither offers
the player anything. The clinic door is shut. The trail confirms it: at 23:41:55 the player
stands at -1900.2 -2478.2 24.1, just outside the entrance at -1899.80 -2477.14, and at
23:42:07 they are at the exact coordinates of `ac_terminal_pc`. That is the Devices tab's
**go** button, not a walk.

**The doors.** `wk_scratch/gps/exterior_-30_-39_0_0.streamingsector.json` gives both clinic
doors with a quest ref in `nodeData.QuestPrefabRefHash`, inside prefab `loc_q303_macs_clinic`:

    idx 969  {single_door}  -1899.80 -2477.14 24.06  #q303_dvc_door_clinic_entrance
    idx 968  {double_door}  -1903.74 -2473.97 24.06  #q303_dvc_door_clinic

Both are authored unlocked (D19). So the shut door is runtime state from q303/q304, which
no file shows.

**Change.** A new graph node type, `device_action`, emits
`questInteractiveObjectManagerNodeDefinition` wrapping `questDeviceManager_NodeType`.
- **Shape:** measured off `ep1_mq304_airdrops` (`ForceDetonate`). Hot Fuzz, a shipped mod,
  uses the same node to `ForceUnlock` a vanilla door by its short `#` ref.
- **Silent-typo guard:** the controller class and the action are CNames resolved at runtime,
  so a typo does nothing and logs nothing. The generator therefore checks door actions
  against `DoorControllerPS.GetQuestActionByName` (vanilla_scripts.reds:135033).
- **Placement:** two `ForceOpen` nodes sit after `await_clinic`. `ac_clinic_entrance` is on
  the street 13 m away, so the doors' sector is streamed when they run.
- **Why ForceOpen:** it sets opened, unlocked and unsealed in one call and does not gate on
  power (`OnQuestForceOpen`, :135528).
- **Revision:** `phase_revision` 4 -> 5, so a save parked at `await_box` re-enters the phase
  and passes the doors.

Backup: `source/quest_graph.json.bak-2026-09-16-doors`. Build 01:26:26 green: 108 nodes,
replaytest clean, 0 WolvenKit errors.

**The probe was lying.** Its `hasActions` line passed an EntityID where `GetActions` wants a
`GetActionsContext` struct, so it could only ever print `?`. It now reads the gates
`GetActions` walks, one by one: `IsPowered`, `HasUICameraZoom`,
`ShouldShowExamineIntaraction`, `IsPersonalLinkConnecting` and the computer animation state.
For doors it reads `IsOpen` / `IsLocked` / `IsSealed`.

**Not fixed: the computers.** Our instanceData carries `hasUICameraZoom 1`. By the script,
that is enough for `GetActions` to offer `ToggleZoomInteraction`, unless an earlier
else-if branch wins or the device's Direct context never activates. The new probe lines say
which. Opening the door is not claimed to fix them.

---

## D100 — both clinic props were placed 1.48 m too low: buried mesh, unreachable interaction (2026-09-16)

The player deployed D99 and reported: *"doors are now opened but other stuff
broken … this stuff are undergrown and not look beatiful so need to be fix"*,
with `sc_problem_look.png` and `sc_problem_look_2.png`. Both show a
`computer_1.ent` prop as a flat slab sunk through the clinic floor at an angle —
the top edge and three app cards above the tiles, the body below them.

### The entity says where its floor is

`computer_1.ent` carries three player workspot components, and a workspot anchor
is where the player *stands*:

    personalLinkPlayerWorkspot   local z  -1.52
    ToggleZoomInteraction        local z  -1.40
    personalLinkComponent        local z  -1.40

So this entity expects its origin ~1.5 m above the floor. It is a mounted screen,
not a floor-standing box; that is also why the visible mesh is a bare panel.

Vanilla agrees, measured independently. In `quest_73110a178d6e7404` the computer
is `nodes[12]` at Z **8.705**. The AI spots at Z 6.01–6.06 are a *different*
level — `nodes[4]` at Z **7.221** is the only floor node on the computer's side
of the building (X −587.7 vs the computer's −579.8; the rest cluster at −588…−606).
8.705 − 7.221 = **1.484 m**, which is the workspot number again.

Its orientation is pure yaw (`i=0, j=0, k=0.0436, r=0.9990` — 5°), so the 15° tilt
is baked into the appearance and `quaternion_yaw` was never the problem. The
player's own screenshots show both slabs facing the camera, so yaw is already right.

### This is very likely the missing interaction too

`gameinteractionsComponent` and `ToggleZoomInteraction` are children of the entity
origin. With the origin at floor level, the interaction workspot sits at
floor − 1.40 m — **inside the floor**. That fits every symptom at once: the CET
probe finds the device by look-at raycast (the slab pokes through), reports
`ComputerControllerPS`, state ON, `isInteractive` true — and the player still gets
no prompt, because the place you must stand to use it is underground. Not yet
confirmed in game; the D99 probe lines still decide it.

### `pos` is not the thing that moved

`pos` is the FLOOR point: a coordinate somebody stood on, which is what makes it
verifiable, what the COORDINATE PROVENANCE block promises, and what the CET go
button teleports to. Folding 1.48 into it would have destroyed all three and left
the go button dropping the player into the air. Instead `gen_sector.py` gained a
prop-only `zOffset` applied when the node is emitted, and `validate.py` type-checks
it beside `yaw` and `height`. Recorded coordinates unchanged: 24.06 / 24.08.
Emitted nodes: **25.540** and **25.560**.

### No `phase_revision` bump

D99 needed one because graph node ids are positional and the save was parked mid-phase.
This changes a streaming sector only — the graph is untouched at 108 nodes, and sectors
stream fresh from the archive on every load. Bumping would restart the quest for nothing.

Build green: `validation OK` (27 facts, 108 graph nodes, 5 sectors, 3 props, 12/12
positions stood on), replaytest `OK: every side effect happens exactly once`,
`Completed with 0 warnings and 0 errors`. Backup: `source/world.json.bak-2026-09-16-zoffset`.

### Still open

The box's model remains a placeholder and is now a screen floating at chest height
rather than a screen in the floor. A real floor-standing container is a
`worldDeviceNode` + `LootContainerAccessPointControllerPS` buffer, which
`gen_sector.py` does not emit — unchanged from D98, and deliberately not bundled here.

### D100 confirmed in game (2026-09-16 11:34)

The 1.48 m lift was the whole cause. User screenshots after deploy:

- `sc_terminal_box.png` — the clinic terminal's computer UI is **open and in use**:
  the FILES tab is selected and a shard is being read. The interaction prompt
  exists, the device responds, the buffer works. OI-13's device half closes.
- The journal objective advanced from "Отримай доступ до термінала клініки"
  (get access to the clinic terminal) to "Переживи зачистку ФІА" (survive the
  FIA sweep). The quest is running past the point it was stuck on.
- User reports the Mara scene now starts automatically, no CET nudge.

So the missing prompt was never the instancedata buffer, never the appearance,
never the yaw. The interaction workspot sat 1.40 m below the entity origin and
the origin sat on the floor, which put the spot the player must stand in inside
the floor collision. Nothing else had to change.

**What is still wrong is cosmetic and was predicted here.** Both props now float
with nothing underneath them - `computer_1.ent` is a screen on an arm whose
stand and desk are separate world geometry in vanilla, so lifting it to its
correct mount height in open floor space leaves a screen hanging in the air.
`sc_splinter_case_box.png` shows this clearly at the box. The terminal reads
acceptably because there is a bench roughly under it; the box does not.

The box's model remains the placeholder noted above: it is a computer screen
standing in for a container. That is now the only open item on these two props.

## D101 — clinic props moved onto real furniture, measured by live raycast (2026-09-16)

D100 fixed the height; the panels still hung in open floor. Measured with cp77wb
`raycast_scene` (needed a bridge fix: CET's per-mod require cache hides World
Builder's editor, reached instead through `GetMod("entSpawner").editor`):

- Floor under both old spots 24.056, nothing raised within 1 m - no bench under either.
- Panel from horizontal rays: 1.5 m wide (local Y ±0.75), bottom at origin −0.28,
  top +0.32, tilted back 15°. The screen faces local −X, where the workspots are
  (−0.49…−0.74), so the stand spot is heading `yaw+180`, 0.58 m out.
- Box → workbench top 24.856 (0.80 m), front edge faces 39.8°: pos (−1908.62,
  −2472.35), yaw −140.2. The stand spot lands 0.09 m from the stood-on case marker.
- Terminal → NE wall counter ~25.08 (1.0 m), front edge faces 225°: pos (−1909.67,
  −2463.40), yaw 45.0, on the clear stretch past the items in the corner.

zOffset 1.48 unchanged (interaction depends on it). `collapsedOnto` dropped, and
`verified` set to false: these points were measured, not stood on. Markers, pins
and graph untouched, so no `phase_revision` bump. Backup: `source/world.json.bak-2026-09-16-mount`.
Build green, 0 warnings / 0 errors. Not yet seen in game.

**Terminal confirmed in game (2026-09-16):** standing at the counter and aiming at the screen shows the
"Use" prompt (Використати), and the UI tabs render. At 3.1 m there was no prompt, which is normal for the
range. `ac_terminal_pc` is now `verified: true`. The splinter box was confirmed the same day: the Use prompt shows on its screen, and `ac_splinter_box` is now `verified: true` too.

## D102 — the splinter box becomes the prologue's Relic case, usable through a scene hub (2026-09-16)

The placeholder `computer_1.ent` on the workbench is gone. `ac_splinter_box` is now
`base\quest\main_quests\prologue\q005\entities\q005_biochip_suitcase.ent` at
(-1908.897, -2472.03, 24.87), yaw -50.2, which is the open notebook in the middle of the bench, with the latches toward the player.
That pose was measured with a cp77wb camera raycast, previewed live with a Codeware
`DynamicEntitySpec`, and approved by the player (sc_better.png). The .ent has no
interaction, so the prop is `scenery` (new validate.py exemption, which needs a written reason).

The prompt now comes from the prologue's own mechanism: `q005_07_vip_apartment.scene` hub 4162,
an `attachToWorld` scnChoiceNode captioned 'użyj' (extracted to
`questmod-research/vanilla_ex/q005_json/`). gen_scene.py takes `attachToWorld: {offset, range}`
on a choice node, which gives mode attachToWorld, entityPosition = offset relative to the scene location,
the Interaction/SceneDialogObjectSettings mappin, a 2 m range and yaw limit 200.
The new `source/scene_box.json` is one hub, "Use" / "Використати", at `#ac_box_origin`, a new marker on the case.

Graph: `await_box` (interaction OR fact) is replaced by `guard_box` (fact == 0), then `open_box`
(the scene, which blocks until the option is picked), then `box_opened_set`. What was lost: the CET Acts tab setting
`ashcache_box_opened` no longer releases a scene that is already waiting; it still skips the box
on a fresh entry through guard_box.

Build green. Not yet seen in game.

**2026-09-16 15:07, first in-game test: no prompt.** The loaded save was made at the box step under the
pre-D102 build (trail.log 15:07:20: progress 3, box_opened 0, ac_obj_find_box ACTIVE). D102 put two
nodes (guard_box, open_box) where await_box had been, and gen_questphase numbers nodes by list
position, so every later id moved and the save's running node pointed at another node. open_box
never started. This is the D97 rule, which I missed: `phase_revision` is now 5 → 6.

## D103 — Mara faced away from V: the marker yaw was the player's camera, not a facing (2026-09-16)

First in-game run of the r6 build (sc_mara_not_correctly.png): the Relic case prompt shows, but Mara talks with her back to V. The scene spawns her with an identity `spawnOffset` at `#ac_mara`, so she takes the marker's orientation. That yaw (-111.9) came from the 2026-09-03 Surveyor capture, which records where the PLAYER was looking while standing on the spot. Its forward vector (-sin, cos) points 0.81 away from V's talk position. Fix: yaw 32.1, aimed at V's live position during the conversation (wb_live_player, 2.35 m away). The choice hubs attach to the actor, not the world, so no other scene offset rotates with it. No questphase node change, so no phase_revision bump (D97 does not apply).

## D104 — Choice options left from reserved sockets: overlapping sections, crash on options 2+ (2026-09-16)

In-game (sc_mara_dialog_collapse_screen.png): option 1 played `trust_1` and `deal_2` at once, and options 2 and 3 crashed the game (the earlier FIA crash, CrashLogger 15:49:28, null read on redDispatcher). Cause: `gen_scene.py` put option *i* on output stamp `{name i, ordinal 0}`, which I inferred from single-option samples that can't distinguish the two layouts. `royce_default.scene` (2 options) shows the real layout: options on `{name 0, ordinal i}`, then six reserved sockets `name 1..6`. So option 0 also fired reserved socket 2, which ran sec_deal in parallel. Options 1 and 2 had no `(0,i)` socket at all, which gave the null read. Fixed in the generator (`CHOICE_RESERVED_SOCKETS = 6`). All four hubs (mara ×2, decision ×2) are rebuilt; box has 1 option and was unaffected. Build green. This touches scene files only, with no questphase node change, so no phase_revision bump. Not yet seen in game.

## D105 — Mara gets facial emotions, and stays when the scene ends (2026-09-16)

**Emotion.** Lines in `source/scene_*.json` take an optional `"emotion": "<base>[/<variant>]"`.
`gen_scene.py` turns a change of emotion into the vanilla facial event: a `scnChangeIdleAnimEvent`
on component `head`, `bakedFacialTransition.toIdle{Female,Male} = idle__<base>__<g>`,
`facialKey_* = idle__<base>__<g>__<variant>`, Fast / 2.73 s / 2730 ms, starting with the line.
Copied field for field from `mq029_01a_garage.scene` (Johnny: spawnDespawn, `facialAnimSets []`,
the same shape as Mara) and checked against the 68 events in `q005_07_vip_apartment`. Performer is
`(actorId << 8) | 1` (q005_07: actor 1 → 257). Names are limited to the female idles that occur in
the 73 extracted vanilla scenes. Event ids are `2e9 + ruid`. Mara's 18 lines are tagged.

**Disappearance.** `keepAlive: 0` despawns a spawnDespawn actor the moment the scene ends, which
is the vanishing the user saw. Mara now ships `keepAlive: 1`, opted in through `characters.json`.
UNVERIFIED (rule 8): none of the extracted scenes sets it, so this is an in-game experiment. The
failure modes are that she still vanishes, or that she is gone after a save load, because dynamic
entities are not saved. Walking her out needs move/AI nodes and was not attempted.

**Lipsync is unchanged.** OI-17 still stands: the lipmap chain is built, but no Mara `.anims` exists.

## D106 — Scene sections list their cast in `actorBehaviors` (2026-09-16)

D105's emotions did nothing in game, though keepAlive worked. The events matched Hot
Fuzz's field for field, and Mara's appearance (`ep1\characters\appearances\corpo\corpo__nusa_wa.app`,
`_q306__fia_undercover_01`) has a real `face_rig` and loads
`generic_average_female_facial_idle.anims`. The one difference left was every section's
`actorBehaviors`: ours was `[]`, copied from `template.scene.json`. Across the 11
extracted scenes, 63 of 65 sections with performer events list those actors
(`scnSectionInternalsActorBehavior`, `OnlyIfAlive`). The two that don't are q005 props
(drones, AV) and the template. `gen_scene.py` now lists the whole cast in every section.
UNVERIFIED in game until the next test.

## D107 — Mara gets a lipmap entry, with a borrowed vendor animset as a stand-in (2026-09-16)
D106 (cast in `actorBehaviors`) did not bring back emotions: her face stayed the
same the whole scene. By then the emotion event matched q005's field for field,
the deployed archive was the D106 build, ACM had no global hooks, and her `.app`
has the face rig and every female facial set. One thing was still different from
vanilla: every vanilla actor's voice tag has a `.lipmap` entry for its scene, and
Mara's custom tag 7731600000000000000 had none. So nothing bound a facial
controller to her. `lipsync/en-us/mara.anims` is now a copy of vanilla
`civ_prst_f_01_enus_30.anims` (the set the scene already fell back to), which makes
gen_lipmap emit the entry and gen_xl emit `localization.lipmaps.en-us`. Its takes
are not named after our lines, so the mouth is not expected to move (OI-17).
**Hypothesis, UNVERIFIED in game.** If emotions still don't show, revert by
deleting `lipsync/en-us/mara.anims`.

**D107 outcome (2026-09-16): disproven in game.** Face still static with the lipmap binding. Stand-in `lipsync/en-us/mara.anims` removed and rebuilt, per OI-17 (no lipmap until real animsets). Also ruled out: vanilla q005 Jackie/Tbug/Iguana get 27/14/2 emotion changes with zero facial/anim sets on the actor, so scene-side anim-set references are not required; all of Mara's idle events sit inside their section durations. Next discriminator: AMM facial expression on Mara in game (rig vs scene).

**Emotion check result (2026-09-16): no bug.** In game, AMM Tools → Facial Expression changes Mara's face with every expression (19 tried, screenshots from the user), and she blinks normally. Her face rig and emotion layer work. The scene's emotion changes use calm keys (cautious, suspicious, defensive, focused, contempt, confident, sceptical, pleased) that are hard to see on a face whose mouth doesn't move. The D106 actorBehaviors change is still in place but did not fix anything. The face looks frozen because of the missing lipsync (OI-17), not missing emotions.

**D108 (2026-09-16): stronger Mara emotions.** The user asked for more visible faces before lipsync. Ten lines in `source/scene_mara.json` moved from calm keys to strong ones: opening warnings use anger/defensive; "Hale's already moving" lines (open_3, openj_3, deal_3) use fear/worried; break_4 uses anger/full; trust_2 uses disgust; hostile_1 uses joy/fake_smile; hostile_2 uses anger; deal_1 uses joy. All come from the vanilla FACIAL_EMOTIONS set. Build is green. Verified in game 2026-09-16 (user: "emotion work").

## D109 — Mara lipsync generated from her audio (2026-09-16)

OI-17 had two blockers; both are closed.

**Headless import.** `/mnt/sata/WolvenKit/WolvenKit.CLI/Commands/ImportCommand.cs` is patched locally with `--gamepath/-gp`, which loads the game archives before import (same call ExportTask makes). The original is at `questmod-research/lipsync/ImportCommand.cs.orig`. Anims routing uses the env var `GltfImportArgs__ImportFormat=Anims`, so `appsettings.json` stays untouched. Round trip checked: vanilla `civ_high_f_24_nat_30.anims` → glb → import, 16/16 rebuilt.

**Animation data.** Vanilla lipsync is JALI float tracks: 4662 track keys against 56 joint keys, on Neck, Neck1 and Head only. WolvenKit carries those tracks as glTF `extras.trackKeys`. `tools/gen_lipsync.py` decodes each `vo/en-us/mara.<line>.wem` and computes a 30 fps loudness envelope. For every frame it copies the vanilla frame (16 female takes, same 414-track wa rig) whose `jaw_mid_openLipsyncPoseOutput` matches, and it prefers to keep playing the current take. Eye, brow and upper-face tracks are dropped, so the emotion idle keeps the upper face. The mouth syncs to syllables. Shapes are not tied to phonemes; that would need an aligner.

**Output.** `lipsync/en-us/mara.anims` has rig `h0_009_wa_c__young_skeleton.rig` and 18 takes `f_<subtitle id hex>` whose lengths match the audio. It also carries the 16 unused vanilla takes, because import keeps the originals. The build is green and packs the lipmap plus animset. There is no ua-ua lipsync, because there is no ua-ua voice. Verified in game 2026-09-16: the mouth opens on her speech and the scene reads correctly.

## D110 — The courier's shard lies on the room 7 table (2026-09-16)

**Problem.** The motel beat blocked on `await_room` (`ashcache_courier_log_played`), but room 7 held nothing to find. `give_courier_log` put the log in V's inventory silently the moment the objective started, so the player had no cue to read it and the quest looked stuck.

**Decision.** The same mechanism as the Relic case (D102):
- `ac_courier_shard`: scenery prop `q004_data_shard.ent`, the prologue's own quest shard. It has no interaction or device components.
- `ash_cache_courier_shard.scene` (`source/scene_courier_shard.json`): one `attachToWorld` choice hub, "Take shard" / "Взяти скіпку", at marker `ac_shard_origin` on the same point, 10 cm above it.
- Graph: `guard_courier_log` → `take_courier_log` (blocks until taken) → `mark_courier_shard_taken` → `guard_courier_log_given` → `give_courier_log` (now `notify: true`) → `mark_courier_log` → objective. Reading the shard sets `played` through the existing journal Visited glue.
- Placement: a cp77wb camera raycast with the player's crosshair on the table. The visual hit is at z 81.120 with the normal up, confirmed by a downward physical ray, and the prop sits 1 cm above that. Yaw -58.5 turns it toward where the player stood.

**Guards.** `phase_revision` 6 → 7, because node ids moved (D97).
- The shard is offered unless `ashcache_courier_shard_taken` or `courier_log_played` is set. It is deliberately not keyed on `courier_log_given`: a pre-D110 save holds the log silently (given=1, played=0) and never saw a shard, so it still gets the prompt.
- `guard_courier_log_given` stops such a save from receiving a second copy.
- A first attempt keyed only on `played` failed `replaytest.py`: a D110 save that took the shard but hasn't read it has the same facts, so a later re-walk would offer the shard again. The new replay guard `ashcache_courier_shard_taken` (facts.json) tells the two apart.
- Build is green and replaytest is OK. Pending an in-game test.

### D110b — Taking the shard always grants the log (2026-09-16)

In-game test on a pre-D110 save (given=1, played=0): the prompt worked (trail 21:21:30
`courier_shard_taken 0 -> 1`), but `guard_courier_log_given` took False, so nothing was
granted, no notification showed and there was nothing to read. The guard's premise was
wrong: the ash_cache_debug trail shows `courier_log` count 0 after every load, even on
saves where the log was read, so no copy is ever held to duplicate. Removed the guard;
`mark_courier_shard_taken` now links straight to `give_courier_log`. Replay safety is
unchanged (`guard_courier_log` still requires shard_taken=0 and played=0). phase_revision
7→8. Build green, replaytest OK. Test from a save before the shard was taken.

## D111 — The FIA cleanup crew: spawner car + 3 hostile agents + ShootAt (2026-09-16)

**Built, packed, NOT yet seen in game.** After the terminal (`desc_survive`), phase r9 runs
`guard_cleanup (cleanup_done==0) -> spawn_fia -> await_fia_spawned (all 3 spawned) ->
fia_attack_1..3 (ShootAt #player) -> await_fia_dead (all 3 killed, count 1 each) ->
cleanup_set -> await_cleanup`. Verified from the packed resource with `tools/dump_graph.py`.

- **Enemies.** Every vanilla FIA record is friendly/neutral with no weapon, so
  `characters.json enemies` inherits `Character.mws_se5_06_netwatch_{rifle,handgun}_ma`
  (suits, full archetypeData and loadout) and overrides one flat,
  `baseAttitudeGroup: hostile`. `Attitudes.Group_Hostile` is Hostile to `Group_Player` and
  Friendly by default to everyone else; 168 vanilla Character records ship it.
- **Combat node.** New `shoot_at` node type = `questCombatNodeDefinition` +
  `questCombatNodeParams_ShootAt`, copied from q304_transmitter_tower_04 node 20. All 21
  vanilla combat nodes in `vanilla_ex/combat_json` are this function with sockets In/Success.
- **Car.** `Vehicle.cs_savable_chevalier_thrax`, parked, on the same spawner shape vanilla
  uses (appearanceName `default`, as all 5 vanilla spawners in the extracts).
- **Positions.** cp77wb live raycast straight down from Z 35 on the street west of the
  clinic entrance: open ground at Z 28.43-28.44 for all four.

**Unverified (rule 8):** vanilla drives fights through communities. A Character on a
`worldPopulationSpawnerNode` resolving as the EntityRef of ShootAt and of
questCharacterKilled has no vanilla instance. D46 only showed that such a spawner renders the
NPC. If the crew spawns but stands idle, the ShootAt ref is the suspect. If they die and the
objective does not close, the killed ref is. The car arrives parked; nothing drives it in.

## D112 — FIA crew stood still: ShootAt payload is AIInjectCombatThreat (2026-09-17)

In game (r9) the car and all 3 agents spawned, but none came for V inside the clinic.
Cause: D111 copied `questCombatNodeParams_CombatTarget` (q304_transmitter_tower_04
node 20). That payload retargets an NPC that is already in combat. An agent on the
street has no perception of V indoors, so it never entered combat. Vanilla's own
"send enemies at a target" is the other payload under the same function name:
`AIInjectCombatThreatCommandParams {dontForceHostileAttitude 0, duration 0,
isPersistent 1, targetPuppetRef}`. That is 17 of 19 combat nodes in ep1_mq304_airdrops.
It writes the target into the threat list, so the NPC fights and paths to it.
tools/gen_questphase.py `shoot_at` now emits that payload, verified from the packed
file (build/verify): 3× InjectCombatThreat, persistent, target #player.
phase_revision 9→10: a save made after the idle crew spawned re-enters the phase,
and `guard_cleanup` (cleanup_done==0) re-runs the spawn and the threat.
UNVERIFIED: vanilla's targetPuppetRef always names a community member. `#player`
there is the same gameEntityReference form CombatTarget accepted. Whether the
agents can path INTO the clinic depends on its navmesh. If they fight but hold at
the door, that is navmesh, not the quest.

## D113 — Reloaded FIA crew idles: re-send the threat on a loop (2026-09-18)

In-game report (D111 build): the crew did move and fought Barghest on the street, but after a
reload they fired into the air and stood together until they saw V. Spawner NPCs come back from
a save with no AI state, and the quest nodes that sent the order have already run, so nothing
sends it again. The graph now forks after `await_fia_spawned`: `await_fia_dead` (unchanged, one
uninterrupted pause) plus one loop per agent, `fia_attack_k -> fia_tick_k (5 s) ->
fia_fighting_k (cleanup_done==0) -> fia_attack_k`. One loop per agent, so a combat node that
never completes on a dead agent stops only that agent's loop. phase_revision 10 -> 11.
Verified: build 0/0, replaytest OK, dump-d113.txt nodes 63-74. Still open: the spawn spot is
~58 m from the clinic door with Barghest in between (the fight they got into), so the next step
moves the spawners to the street at `ac_clinic_entrance` once physics there can be raycast.

## D114 — FIA crew spawns at the clinic door, not 58 m west (2026-09-18)

**Symptom (in game, r10):** the crew spawned, fought Barghest on the way, and never reached V.
**Cause:** the spawners stood ~58 m west of `ac_clinic_entrance`, and the route to the door crosses
Barghest ground. Hostile-to-player agents and kurtz_army soldiers do engage each other in practice,
whatever the attitude flats suggest.
**Fix:** `ac_fia_car` and `ac_fia_agent_1..3` moved onto the street in front of the door and measured with
cp77wb while V stood on the entrance marker (raycasts only hit where physics is streamed, so they must
be taken on site):
- ground: straight down from Z 30, flat at Z 28.0 at all four points
- clearance: rays at Z 28.3 run clear ~29 m south-west along the door line and a lane 3 m out;
  the lane 5 m out has street furniture 6-9 m from the door, which I avoided
- agents 11-15 m from the door, the car 20 m out, all yaw -50.5 (facing the door)
World change only; the questphase stays at r11 (D113). Build 0/0; the packed sector contains the new position.

## D115 — The Splinter perk tree (Relic-style chip upgrades)

**Ask:** the splinter did nothing once the quest ended; the user wanted a Phantom Liberty-style upgrade
tree that makes V stronger. Chosen: our own tree; unlocked by every ending except Burn; points from quest
milestones plus echo fragments hidden in Dogtown.
**Why not a native tab:** the game's trees are bound to native enums (`gamedataNewPerkType`,
`gamedataAttributeDataType`); script cannot add one. Relic itself is only gated by fact `ep1_tree_unlocked`.
**How:** the installed CustomPerkFramework (Character -> "Additional Perk Trees") hosts trees that draw
their own ink content; MonowirePerkTree is a working example. Ours:
- `source/chip_tree.json` -> `gen_chip.py` (parallel-array table `AshCacheChipData.reds`) and
  `gen_tweak.py` (one `BaseStatusEffect.ashcache_chip_<id>`, InfiniteDuration, savable false).
- `source/scripts/AshCacheChipTree.reds`: rules, a 3 s ScriptableSystem tick (re-applies bought perks
  after load, registers the tree once `ashcache_splinter_given`, shows a one-time Relic-type message),
  and the menu, all framework code behind `@if(ModuleExists("CustomPerkFramework"))`.
- State is facts only: bought = `ashcache_chip_<id>`; points = sum of 0/1 source facts (never
  incremented, so no double award on reload). Absorb = full (level 2); Blue Eyes/Hide = tiers 1-2 only;
  Burn = none. Not quest logic: the graph neither reads nor waits on any of it (rule 1).
- Stat units read from vanilla TweakDB (`dev/chip/stat_units.py`), not guessed.
- `lint_glue.sh` gained a second pass with the framework + Codeware sources in scope, because the
  vanilla-only bundle made the guarded menu code invisible to the first pass (proved by a planted error).
**Open (closed by D117):** the 6 echo fragments (`ashcache_chip_frag_1..6`) had facts and points but no world objects.
In game 2026-09-17 (user report): the tree menu and the perks work, buying a perk spends points, and the message shows after the quest ends. The stats screen changes too: the user checked the RAM and HP perks; the others were not checked one by one.

## D116 — The Cynosure phase is no longer injected (2026-09-17)

Every save crashed at world load with `resourceToken.cpp:128 "WaitUntilLoaded can only be
called on main thread."` on a loader thread, before ArchiveXL patched any phase into the root
quest. Manifest bisect, with the same archive each time:
no `quest:` block → clean; r11 only → clean across repeated loads; both phases → crash.
`ash_cache_cynosure_r1.questphase` is byte-for-byte what D31 built on 09-04, so the change that
exposed it is not in this resource. The exact mechanism is **not established**. The suspect is
the node-level `phaseInstancePrefabs` (q305 bunker prefabs) being resolved while the root quest
is restored.
`gen_xl.PHASES` drops the entry, so it is neither staged nor listed. `source/cynosure_graph.json`
and `ashcache_cynosure_open` stay; nothing in the quest used them.
**Open:** confirm with a Cynosure-only manifest before redesigning access to the lab.

## D117 — Echo fragments: six shards placed by script, taken by walking onto them (2026-09-17)

**Ask:** place the 6 echo fragments from D115. The user stood on each spot in game and gave the player
position + camera yaw; those are `chip_tree.json` `fragments` verbatim (feet z, no offset).
**Why not the graph or a sector:** a fragment must stay collectable after the quest ends, but a phase
stops when its output node fires, and a second long-lived phase is exactly what crashed every load in
D116. A sector prop would stay visible after pickup. So this is tree glue, like the rest of D115; the
graph never reads these facts (rule 1).
**How:** `AshCacheChipSystem.Tick` -> `UpdateFragments`. While `UnlockLevel > 0` and a fragment's fact
is 0, Codeware `DynamicEntitySystem` places `q004_data_shard.ent` there (tag = the fact name,
`persistSpawn` false, so the save never carries one and each load re-creates what the facts allow).
Within `fragment_radius` (2.0 m) the fact is set, the entity deleted and a Relic message shows
`chip_frag_msg N/6` (LocKey 77315081, en-us + ua-ua). Within 30 m of any fragment the poll drops from
3 s to 0.5 s so a walking V can't cross the radius between ticks. Burn (level 0): no fragments.
`IsPopulated` counts registered entities, not only streamed-in ones (Codeware
`DynamicEntitySystem.cpp:491`), so the per-tick spawn call never duplicates.
**Lint:** `lint_glue.sh` pointed at the pre-move `/mnt/sata/redscript` and silently skipped
type-checking; repointed to `everything/redscript`. A planted `CreateEntityNope` is now reported
from the Codeware-guarded code. The check caught `EulerAngles(0, 0, yaw)` (native struct, argument
constructor is undefined behaviour); it now sets `.Yaw` on a default value.
**Verified in game (2026-09-17):** walking onto a fragment awards its 2 points, they land in the
tree's balance and can be spent. Uncollected fragments still trigger after a reload.

**Invisible shard (2026-09-18).** Fragment 1 was walked onto with no shard ever seen. The two
halves are independent: the fact fires on distance to `pos` alone, so a template that never
loads and a shard that is merely unseen look identical in game - points arrive either way. Two
changes, because the first is right regardless of which it was:
  - `pos` is where V's FEET were, and the template's mesh is `q003__splinter.mesh`, a few
    centimetres of splinter. Drawn at `pos` it lies on the floor, outside the standing view
    cone. New `fragment_z_offset` (0.9) lifts the SHARD ONLY - the trigger still measures from
    `pos`, the geometry already verified to fire. Codeware's `DynamicEntitySpec` has no scale
    field, so height is the only lever short of a different template.
  - `des.CreateEntity` returns an `EntityID` that was being discarded. It is now checked, and a
    refused spawn writes one `FTLogWarning`. That distinguishes the two causes without a
    third launch.
The template itself is real - `questmod-research/vanilla_ex/shard_ent/` holds it, extracted by
that exact path - and it carries a `gameScanningComponent`, so the shard should answer the scanner.

**Also fixed:** `tools/validate.py` still pointed `TWEAKDB` at `/mnt/sata/cp2077-tweakdb/`, stale
since the move to `everything/`. It had been printing "17 TweakDB record(s) unverified" as a note
and passing. Same class of silent verification loss as the `lint_glue.sh` path above; validation
now checks 24 records and 3 depot paths again.

**Open:** whether the raised shard is visible, and whether fragment 6 (z=19) is standable.

## D118 — The case opens, and the splinter is taken out of it (2026-09-18)

**The complaint.** "What we have now is not beautiful." It was one prompt captioned `Use` on a
case that never changed, and the splinter arrived as an inventory popup. The beat the quest is
named after was invisible: nothing on screen said the case had been opened, and nothing said the
thing inside had been picked up.

**Why a prop swap and not an animation.** `q005_biochip_suitcase.ent` is an animated entity -
`entAnimationControllerComponent`, rig `base\items\quest\q005__biochip_case_a\q005__biochip_case_a.rig`,
graph `base\gameplay\anim_graphs\cinematics_props.animgraph`, with the lid, bottom and handle as
separate mesh components. Vanilla opens it with a cinematic animation, and it has NO appearances
(`appearances: []`), so there is nothing to switch. Driving that animation would need
`questUseWorkspotNode` or a scene anim event, neither of which `gen_questphase` or `gen_scene`
emits. The asset that solves it is vanilla's own opened case,
`base\quest\main_quests\prologue\q005\entities\devices\q005_broken_suitcase.ent`: an opened
military case mesh plus `base\items\quest\q003__splinter_case\q003__splinter.mesh` - the splinter
lying in it - plus an `entLightComponent` that lights the thing the player is asked to take. It
lives under `entities\devices\` but its entity class is a plain `gameObject`, with no
`instanceData` buffer, which is what made `computer_1.ent` a crash suspect from D65 to D101.

**Two prompts on one marker.** `scene_chip.json` is a second `attachToWorld` choice hub at
`#ac_box_origin`, the same shape and the same vanilla model as the box hub
(`q005_07_vip_apartment.scene`, hub 4162). `scene_box.json`'s caption changed from `Use` to
`Open the case` / `Відкрити скриньку`; the new one is `Take the splinter` / `Взяти осколок`,
matching the existing strings' terminology (`чорна скринька`, `осколок`). No LocKeys were needed
- scene captions are inline locstrings - and no new facts: the two the graph already has are
exactly the two states.

**Where the node went, and why it matters.** `take_chip` sits INSIDE `guard_splinter`'s True
branch, not before it. That guard exists because a `phase_revision` bump re-walks the graph from
`start` with every already-set fact still set (D50), so the prompt and the grant it releases now
share one guard: a re-entry walk finds `ashcache_splinter_given` at 1, takes the False branch, and
can never offer an item the player is already carrying. `replaytest.py` still reports every side
effect exactly once on a fresh run and none repeated on re-entry.

**The objective now closes on the grab, not on the lid.** `ac_obj_find_box` owns the map pin at
the case (`ac_pin_splinter`), so completing it when `ashcache_box_opened` was set would have left
a player who opens the case and walks away with no active objective and no pin leading back to the
splinter still lying in it. `box_opened_set` now runs into `guard_splinter`, and both routes out of
it converge on `obj_box_done` - two connections on one input socket, the OR-join the format allows.

**Who draws it.** A sector node, once emitted, cannot be taken out of the world at runtime, so a
prop with two looks cannot be a sector node: `ac_splinter_box` is now `disabled` in
`source/world.json`, kept there because that entry is the measured, in-game-approved pose
(sc_better.png) and `glue.json` reads its `pos` and `yaw`, so a correction still happens in one
place. New `glue.json` block `props`: each entry names a world.json prop and lists states, first
match wins, each with a tag, a template and `z_offset`/`yaw_offset` - the D117 lesson, keep the
nudge in data. `gen_glue.py` emits `SyncProps()` as an if/else chain, despawn-then-spawn inside
each branch so two looks cannot overlap for even a frame with the player a metre away.

**Mechanism is the fragments', deliberately.** Codeware `DynamicEntitySpec`, `persistSpawn false`,
one tag per state, `IsPopulated` as the no-op guard. A save therefore never carries a case in the
wrong state; `SyncProps` runs from `OnAttach`, `OnRestored` and every watched fact, with a 2 s
retry while `GetDynamicEntitySystem` is not ready yet - and returns ready=true without Codeware so
the retry cannot loop forever. That is a real cost worth stating: on an install without Codeware
the case is not drawn at all, where before D118 the static node still appeared. The prompts and
the grant are unaffected - they are scene and graph - and Codeware is already required for the
echo fragments (D117), so this adds no new dependency, only a second thing that needs it.
`spawnInView` is true here for a different reason than the shards:
the player is looking straight at the case when it changes.

**Rule 1 is intact.** Nothing here decides anything. The graph blocks on two scenes, writes two
facts and closes one objective; the glue only asks which look the object on the bench should be
wearing. Take the glue away and the quest still advances - the case just stops changing.

**Checks:** `validation OK` (126 nodes, 5 scenes), `scene take_chip ok`, redscript lint 0 errors
with CustomPerkFramework + Codeware in scope (which is what type-checks `DynamicEntitySpec`,
`IsPopulated`, `DeleteTagged` and the `ResRef` parameter against this game build - rule 8),
`replaytest` clean. `phase_revision` 11 -> 12, because inserting `take_chip` renumbered every node
after it (D97); the phase is now `ash_cache_r12.questphase`.

**Open:** not yet seen in game. Two things to look at: whether the opened case sits at the right
height on the bench (the two templates are different meshes - `z_offset` is the lever, currently
0), and whether the splinter reads clearly enough inside it to be worth walking over to.

## D119 — The terminal gets a menu, a download bar, and something to carry away (2026-09-18)

**Complaint:** "you just click the terminal and the quest progresses, which isn't very engaging."
Accurate. `await_terminal` waited on `questInteraction_ConditionType` `Executed` against
`#ac_terminal_pc`, so the entire Act 4 beat was one press of the computer's own Use prompt. The
objective said *Voss kept records the Agency believes it destroyed* and the player never saw one.

**What the engine already has.** The Konpeki suite in `q005_07_vip_apartment.scene` — V copying the
Relic — is the same beat, and it is built out of two `questUIManagerNodeDefinition` types this
project had never used: `questProgressBar_NodeType` (top text, bottom text, duration: the download
bar) and `questWarningMessage_NodeType` (the big centre-screen line, vanilla's "WARNING:
UNAUTHORIZED SCANNING"). Both are engine nodes, so the menu is still the engine running the quest
(rule 1) and no part of this is a redscript UI. Hardcoded `type: "Undefined"` on both: it is the
only value the game ships, and inventing the rest of an enum off its name would be guessing at an
engine API (rule 8).

**Why not the vanilla computer screen.** The terminal was a real device — `device: "computer"`,
the D101 `instanceData` buffer carrying `ComputerControllerPS` — so the "proper" UI would be files
and mail authored inside that buffer. Rejected: it is 200 fields of CR2W the project has scar
tissue around (D65–D101), and vanilla's own answer to *download data at a terminal* is not a
computer screen. It is a scene with a progress bar. So the prop is now `"device": null` — the
documented off switch (D69), and OI-13 answered in game on 2026-09-09 what it leaves: the entity
still appears and cannot be interacted with at all. The model stays, the prompt comes from the
scene, and there is no second Use prompt leading to an empty screen. `scenery:` carries the reason.

**The beat.** `source/scene_terminal.json`, hub at the new `#ac_terminal_origin` marker (the prop's
own floor point, offset 1.4 m = screen height):

  - **"Download Voss's archive"** -> the bar fills for 6 s -> "TRANSFER COMPLETE" -> the scene exits
    and `give_archive` grants `ashcache_clinic_archive`, a readable shard: Voss's own record of
    admission 0-1140, the courier signing for the splinter eleven minutes after intake, and the
    index of the 212 files that are not in it. The download now leaves something behind.
  - **"Check the audit trail"** -> sets `ashcache_terminal_full_read` and prints the purge line,
    then loops back to the hub. That fact was declared at D12, documented as the completionist
    read, and had no setter anywhere for six days; it is now worth a chip point.

Only the download leaves the scene, so the hub cannot be dismissed into a half-finished objective —
walking away leaves the prompt standing, exactly like the case's.

**The one non-obvious mechanism:** `questProgressBar` does NOT block. It starts the bar and returns.
Wired straight to the exit, the bar would animate over a quest that had already granted the archive
and closed the objective — the instant version of the beat, which is the complaint again. The wait
is an eventless `section` of 6.4 s inside the scene (`"seconds"` on a section is new in
`gen_scene.py`). Precedent for an eventless section is Hot Fuzz, the one reference scene that ships
one; `stu` is milliseconds.

**Guarded like the case.** `guard_terminal` reads `ashcache_terminal_read == 0`; True runs the menu
and the grant, False skips both. A `phase_revision` re-walk therefore cannot offer an archive the
player is already carrying. Same caveat as `take_chip`: CET can skip the beat only from in front of
it, because the guard is read on the way in.

**Ukrainian declension met the proper-noun check.** `validate.py` flags two names one letter apart,
and `Агенція` (nominative) / `Агенції` (genitive) are both required Ukrainian. `NAME_TWINS` had been
empty since the check was written; this is its first entry, and the reason is on the line. The
English pair it caught in the same pass — `NODE` / `CODE` in two all-caps HUD lines — was a real
find and got rephrased.

**Checks:** `validation OK` (128 nodes, 6 scenes, 5 items, 90 lockeys, 20/20 stood on), `scene
terminal_menu ok`, `8 nodes / 2 options` emitted with both LocKeys and `stu 6400`, `128 nodes, 146
links`, redscript `0 warnings and 0 errors` + `chip tree: 0 errors`, `cet init.lua parses`,
`replaytest` clean, no leaked processes. `phase_revision` 12 -> 13 (`ash_cache_r13.questphase`):
`await_terminal` was removed, which renumbers every node after it (D97).

**Open:** not yet seen in game. The hub's 1.4 m offset is a guess off `computer_1.ent`'s 1.48 m
`zOffset` and wants one look to confirm the prompt sits on the screen rather than above it; and the
6 s bar is a feel number, trivially changed in `source/scene_terminal.json`.

## D120 — The endings get the beat they were describing (2026-09-18)

**The complaint, in the player's words:** after the shootout with the agents "almost nothing
happens" — no V slotting the chip into her own head, no handing it to the man with blue eyes for a
price, no burning it.

He is describing a real defect and not a missing cutscene. The ending ran like this: the decision
hub set one `ashcache_end_*` fact, the `br_*` chain read it, and the matching objective was raised
with `notify: false` and completed *in the same frame*. The objective said **"Destroy the
splinter"**; nothing destroyed anything; the splinter was still in the backpack when the quest
finished. Three of the four endings were a journal entry describing an act the game never performed.
The build-1 note on `end_destroy_on` admitted as much — "when the Blue Eyes handover and the
Badlands drive become real content, the wait for the travel leg goes between the `_on` and `_done`
node" — and that is exactly where this went.

### What now happens between `_on` and `_done`

`source/scene_epilogue.json`, one entry and one exit point per ending:

  **Burn** — a burn barrel out back, the chip goes in "like a cigarette butt", the splinter's last
  transmission hits V's optics (`fast_travel_glitch` on the player) under a centre-screen
  **SIGNAL LOST — 0-1140**, and one closing line. The item is then removed.

  **Jack in** — "personal link, straight into the socket behind my ear", the engine's own progress
  bar reads **NEURAL LINK — SPLINTER 0-1140** for 5 s, the glitch fires as it lands,
  **ECHO INTEGRATED**, and V hears what nine years sounds like. The item is spent.

  **Blue Eyes** — no meet and no face, because a man who has stayed anonymous through two
  conversations does not turn up in person for the third: a drop box, a number that will not ring
  twice, and a price he named himself. Out of the scene the splinter is removed, 15,000 eddies land
  with the engine's own notification, and the receipt arrives on the same anonymous thread that
  pushed V at the courier in Act 1.

**Hide keeps the build-1 treatment.** It is a drive into the Badlands and a place to bury a case —
content, not a flourish — and faking it with three lines would be worse than leaving it plain.

### Engine nodes, not a cutscene (rule 1)

Two new node types in `tools/gen_questphase.py`, both usable from a scene or the graph:

  `play_fx`      `questFXManagerNodeDefinition` / `questPlayFX_NodeType`. Two shipped instances were
                 read for the field shape: q005_07_vip_apartment drives the Konpeki safe's hacking
                 light through three of them (`play` 1 then `play` 0), and Undermine's
                 `template.scene` plays `fast_travel_glitch` **on the player** — `isPlayer: 1` with
                 the nodeRef left as uint64 0, the opposite convention to `add_item`, where
                 `isPlayer` is 0 and a `questUniversalRef` carries `refLocalPlayer`. `effectName` is
                 resolved against the target entity's own effect list, so a name that entity does not
                 define plays nothing and still completes the node; `fast_travel_glitch` is the one
                 player-side name with a shipped precedent, which is why both beats that glitch use
                 it.
  `remove_item`  the same node and the same params block as `add_item`, one enum apart
                 (`questEAddRemoveItemType`: AddItem 0, **RemoveByItemID 1**, RemoveByTag 2,
                 RemoveAll 3). No reference quest removes an item, so the remove side rests on the
                 RTTI-generated struct rather than a shipped instance; every other field keeps the
                 value three vanilla AddItem nodes agree on.

One serialisation trap, caught by WolvenKit refusing the file outright:
`questPlayFX_NodeTypeParams` is a **plain struct** and must be written inline, where
`questAddRemoveItem_NodeTypeParams` derives from `ISerializable` and is a handle. Same word
"params", opposite encoding.

### The payout is a vanilla item, and the validator had to learn that

`Items.money` is the game's own currency record — the id vanilla loot and every eddies mod moves —
so granting 15,000 of it through the ordinary `add_item` node raises the engine's normal eddies
notification and needs no HUD node. `tools/validate.py` used to fail any granted item `items.json`
does not define. It now splits the case: an id prefixed `ashcache_` must be ours (rule 5) and stays
a hard error, anything else is a borrowed vanilla record and is verified against the game's TweakDB
name dump. `remove_item` is checked the same way — a typo there is the quietest failure of the
three, since the node completes, the object stays in the backpack, and the ending that just said it
was burned is contradicted by the inventory screen.

### What `replaytest` caught, and it was not cosmetic

The first wiring used ONE scene node with three entry points, the shape `decide_scene` uses. The
replay simulator reported `epilogue_scene: fires 3x` and, worse, `pay_blueeyes: fires 3x` on a
single fresh run — a scene node with three exits hands the walk three live output sockets, so every
ending's tail ran on every playthrough. Split into three nodes, one per ending, each with one door
in and one out.

It then caught the second hole: a `phase_revision` bump re-walks a **finished** save from `start`,
every fact it reads is still set, and the walk arrives back at its own ending — replaying the beat,
removing an item the player no longer has, and paying the Blue Eyes fee a second time. Hence
`ashcache_epilogue_played`, one fact, read by a guard in front of each of the three chains and set
last in each of them, so a save taken mid-beat replays it rather than skipping it. Same shape as
`guard_splinter`; the run is now clean both ways.

The chip tree does not notice the splinter leaving: its visibility is keyed on the fact
`ashcache_splinter_given`, not on holding the item, so the perks bought with it survive the object.

### Checks

`validation OK` (45 facts, 142 graph nodes, 7 scenes, 95 lockeys, 20/20 stood on), `negtest 96/96`
(the two item cases held after the validator split above — they had briefly stopped firing, which is
the only reason that split is written the way it is), `replaytest` "every side effect happens exactly
once on a fresh run, and a re-entry repeats none of them", redscript 0 errors, `cet init.lua parses`,
all seven scenes and both questphases deserialise. `phase_revision` 13 -> 14
(`ash_cache_r14.questphase`), since eleven new nodes renumber everything after them (D97).
`tools/dump_graph.py` now prints a borrowed vanilla item by name instead of `<<no item hashes to>>`,
which is not a miss.

**Open:** not yet seen in game. Three things want a look. Whether `fast_travel_glitch` reads as "a
chip dying in my optics" or as an obvious fast-travel transition — it is one CName in
`source/scene_epilogue.json` if it is wrong. Whether 15,000 is the right number for a man who names
his own price. And the nine new lines are subtitle-only while the 43 around them are voiced: they
want `vo/en-us/epilogue.<line id>.wav` (stems `epilogue.epi_burn_1`..`epi_sell_3`) dropped in, at
which point the build voices them with no further edit.

## D121 — Mara stops being scenery (2026-09-18)

**The complaint.** "Mara feels like a 'wooden' (flat) character in the plot; she should play a role
at the quests."

**The defect, which is structural and not a writing problem.** Mara existed for exactly one
conversation. She told V that Hale's crew was twenty minutes out — and then stood in the clinic,
immortal and `keepAlive`, while the firefight she had just predicted, the decision and all four
endings happened around her. Nothing she said had a consequence. Nothing V chose *about* her
changed anything: `ashcache_mara_hostile` was set by the intimidate branch and read by nothing at
all, and `ashcache_mara_break` — the payoff for the hardest option in the scene, the one that quotes
her own journal back at her — was set alongside trust and likewise read by nothing. The one ending
gated on her trust, the Badlands, was also the one ending D120 left with no beat, so she was absent
from the ending that exists because of her.

Three places, three additions, and the through-line is that she is an **analyst**, not a gunfighter.
Everything below is machinery this project has already shipped and the user has already played.

**1. She hands over her sidearm, and says why.** `sec_gift` closes the three routes where V did not
tell her to get lost: *"I'm no good in a firefight and I'm not going to stand here pretending
otherwise. What I'm good at is that clinic's node. By the time Hale's people file a report, you were
never in this building."* This is the load-bearing line of the whole decision. Her character record
is `q306_fia_agent_corpo_scene_wa`, a non-combat scene NPC with no weapon and no `archetypeData`
(see `_enemies` in `characters.json`) — she *cannot* fight, and the alternative was either a
different casting or an unattested combat record. Saying it out loud converts an engine limitation
into the most in-character moment she has. The gun is `ashcache_mara_liberty`, `$base
Items.Preset_Liberty_Default`: Militech's federal sidearm, which is the joke — nine years undercover
carrying the one object that would have identified her instantly. Granted by the **graph**, not the
scene, for D120's reason: every grant in this quest lives on the other side of a scene exit where
the guards can see it. The intimidate branch gets `sec_cold` instead — no gun, and she still takes
V's name off the clinic's sign-in on the way out. The help is not a reward for being nice to her.

**2. She works the fight.** *"Keep your phone on. I'll count them for you"* is the last thing she
says, and six seconds into Act 4 she keeps the promise: `ac_msg_mara_01`, the count and which one is
the netrunner, fired off `await_fia_spawned` so the numbers are true at the moment they are sent. The
intimidate route gets `ac_msg_mara_02` — the same count, from someone who ends it with *"Don't write
back."* It needs no guard of its own: the whole cleanup already sits behind `guard_cleanup`.

**3. She has a verdict.** One phone thread, one message per ending, wired at the point all four
endings already converge and chained on False exactly like the ending switch above it, reading the
same `ashcache_end_*` facts so the two switches cannot disagree. Burn is relief; absorb is the only
one where she is frightened rather than pleased, and the only one that asks V for something back;
Blue Eyes is disappointment with no lecture, because *"I had nine years and I did nothing"*; the
Badlands is the closest she comes to thanks. On the intimidate route the chain short-circuits to one
message, the same four lines whatever V chose — the sameness *is* the characterisation. And
`route_break` last in the chain finally gives `opt_break_j` its payoff: *"I've started saying person.
Out loud, to people. It's worse, and it's right."*

**The Badlands ending gets its beat** (`h_*` in `scene_epilogue.json`), which D120 deferred as "real
content, not a flourish". That was the wrong call for one reason: it is the only ending with another
person in it, so leaving it empty left the ending gated on Mara's trust as the ending she does not
appear in. It is deliberately the quietest of the four — no glitch, no progress bar, two people, a
hole and no ceremony, because nothing happening is the thing she wanted for nine years. It also fixes
a defect D120 left behind: `hide_splinter`, because "bury the case where the FIA does not look"
ticked with the splinter still in V's pocket.

**Mara is not cast in that scene, on purpose.** A `scnActorDef` *spawns* — it is an instruction to
put a character at the scene's anchor, not a reference to one already standing there — and she is
already standing in the clinic with `keepAlive: 1` from her own scene. Casting her would either
duplicate her or despawn the original, and neither has been measured. `findInWorld: 1` would be the
obvious expression and is attested **nowhere**: all 55 instances in the references are 0, so rule 8
forbids it. The measured route, if she ever needs a body in a later scene, is to move her onto a
world spawner and acquire her with `acquisitionPlan: "spawner"` (3 shipped instances) — that is the
refactor to do first, and it is deliberately not being done in the same change as the writing.

**What the tools caught.**

`validate.py` failed on `"I'd"` vs `"I'm"` differing by one letter — the proper-noun twin check
firing on an English contraction of a pronoun, because D121 is the first line in the project to put
"I'm" anywhere but the start of a sentence. Fixed at the root with `PRONOUN_I` rather than as a
`NAME_TWINS` exception: an exception would have recorded a false pair as if both halves were real
people, and it would have been luck rather than correctness that `"I'll"`/`"I've"` (two letters
apart) never fired.

`replaytest.py` reported `give_liberty: fires 0x, want 1`. Not a graph bug — the simulator only
credits facts that *dominate* a scene's exit, and `mara_trusted`/`mara_hostile` are set on opposite
branches of her hub, so it is right to withhold both. Same problem the ending facts have and now the
same answer: a `dispositions()` helper beside `endings()`. Getting there means re-opening
`guard_meet_mara` (on a finished save the scene is skipped and everything downstream of its exit is
unreachable), which made `meet_mara` count 3x — so the disposition walks credit only what the
ordinary playthrough could not reach.

**Checks.** `validation OK` (46 facts, 46 journal paths, 106 lockeys, 165 graph nodes, 7 scenes, 69
spoken lines, 6 items, 28 TweakDB records, 82 proper nouns); `negtest 96/96`; `replaytest` clean both
ways, now including `mara: trusted` and `mara: hostile`; redscript 0 warnings 0 errors; CET parses;
every resource deserializes; 0 leaked processes. `phase_revision` 14 → **15**
(`ash_cache_r15.questphase`). Nothing deployed.

**Open, and all of it wants the game running.** Whether `item_mara_liberty_name` survives a weapon
record's own name resolution — this is the first item in the file that is a weapon rather than a
quest object, and if the override does not stick it degrades to an ordinary Liberty, a working pistol
with the wrong name. Whether her SMS during the fight arrives while the shooting is still going on
(delay 6) or after it is over. And the one place the fiction still outruns the world: on the
intimidate route she says she will be in the back room, and the NPC stays standing exactly where she
was — the line was rewritten to claim the back room rather than to claim she leaves the building,
but she does not walk anywhere, and she will not until she is on a spawner.

---

## D122 — Mara at the landfill (2026-09-18)

**The ask.** "Mara could be found dead at a Night City landfill, with visible bullet or knife wounds,
depending on V's choices."

**The rule, and it is never stated in the text.** She turns up dead in exactly the two endings that
leave the cache ALIVE in the world — `absorb`, where it is in V's head and she is the only other
person who can say what was on it, and `blueeyes`, where V sold the trail along with the data. Burn
it or bury it and nobody has a reason to go looking for her. Nothing in the quest says this; it is
meant to be found by comparing two saves. `mara_dead == 1` short-circuits everything — if she died in
the clinic there is no landfill beat, and the Hide ending was locked out for the same reason.

**The wound is D121's sidearm coming back.** `ashcache_mara_liberty_given` decides which coroner's
note is granted, and it is the only read of that fact outside its own replay guard. Gave her the
Liberty: three gunshot wounds grouped on the torso, two more rounds in the ground beside her because
the shooters were behind cover, and the gun recovered under the body with the slide locked back and
the magazine empty. Told her to get lost: sharp-force trauma to the neck and forearms, the forearm
wounds defensive, nothing in her hands, no casings within thirty metres — "whoever did this stood
close enough to be recognised and did not care." Two records sharing one display name, one
description and one shard title, so the ONLY thing that differs between two playthroughs is the
paragraph that says how she died.

**Four things were measured rather than guessed, and two of them killed the obvious design.**

1. *A `Character.*` record in a `worldPopulationSpawnerNode` works.* OI-13 has been open since D73 as
   an explicit guess; the FIA cleanup crew shipped on it and the player confirmed the fight in game
   today. Closed, yes.
2. *There is no such thing as a record that spawns dead.* Read out of the real TweakDB with
   `reference/tools/tweakdb_read.py`: `Character.q001_scavenger_dead_man`,
   `Character.q105_jigjig_prostitute_dead` and Mara's own living base record carry **identical**
   `statPools`, `visualTags`, `appearanceName` and `reactionPreset`. A spawner pointed at a vanilla
   "dead" record would have put a living, standing woman in a landfill. This is the single most
   valuable thing the session found and it was one command away from being shipped wrong.
3. *The corpse is in the entity template.* What differs between those records is
   `entityTemplatePath`, and resolving the three raRef hashes against `depot_files.txt` by FNV1a64
   gives `q001_scavenger_dead_man.ent`, `q105_jigjig_prostitute_dead.ent` and Mara's own
   `q306_fia_undercover_wa.ent`. q105's is the female one, so that is the body — drawn through the
   same Codeware `DynamicEntitySystem` the D118 case already uses, not through a spawner.
4. *A second injected phase is not available here.* The obvious home for a beat that outlives the
   quest is a separate `.questphase`, the way `cynosure_graph.json` is built — and D116 already
   found that with that phase attached **every save crashed at world load**, which is why
   `gen_xl.py` still has it commented out. So the aftermath lives in the main graph, parked on a
   `pause_fact` between the ending messages and `quest_done`. The quest stays open until V drives out
   there, possibly forever, which is both engine-legal (six vanilla q305 phases ship with no output
   node at all) and a fair description of the ending.

**Two tool defects, both found by the tools themselves on a correct graph.**

`validate.py:87` keyed the stage-window walk on the raw link source, so an edge written
`route_wound:True` was filed under a name no walk ever pops and the walk stopped dead at the first
condition node — for act 7, a window of exactly one node. Invisible until now because the only two
proximity watches that existed sat in acts with no branch between the progress node and the pause.
Fixed at the root by stripping the socket, which only ever widens a window.

`descpanel.py` reported **peak simultaneous descriptions: 2** on absorb and blueeyes. An ending's
description is never switched off anywhere in this graph — it stays Active until the quest closes,
which was invisible while it was the only live paragraph. D54's invariant is that the log panel
concatenates every still-Active description into one field, so absorb plus landfill would have
rendered as a single run-on block. Fixed with `route_body_absorb` and two Inactive nodes. The cost,
recorded deliberately: on those two endings the ending's own flavour paragraph is now retired rather
than left up at quest end, because the live objective is the landfill.

`replaytest.py` needed a third helper, `aftermath()`, for the same reason `endings()` and
`dispositions()` exist — the two grants sit behind an ending, an arrival fact the simulator has no
model of, and a disposition, and exactly one of them is reachable per walk by construction. Adding it
exposed that each extra walk replays the quest from the root, so a `covered` set now stops later
walks re-crediting earlier ones' side effects.

**Checks.** `validation OK` (50 facts, 49 journal paths, 114 lockeys, 184 graph nodes, 6 sectors,
10 markers, 8 items, 30 TweakDB records, 89 proper nouns); `negtest 96/96`; `replaytest` clean both
ways including `landfill: shot` and `landfill: cut`; `descpanel` peak 1; redscript 0 warnings 0
errors; chip tree 0 errors; 0 leaked processes. `phase_revision` 15 → **16**
(`ash_cache_r16.questphase`). Nothing deployed.

**Open — and the first one blocks everything else.**

*The landfill has no coordinate.* It is the one value in D122 that cannot be derived from the game
files: "landfill" appears in TweakDB only as the attitude group `_Landfill_Guards` and in the depot
only as terrain prefabs under `base\prefabs\environment\terrain\landfill`, neither of which carries a
world position. `ac_landfill_body` ships at `0,0,0` with `verified: false` — deliberately absurd so
it can never be mistaken for a measurement. It has to be stood on and captured the way the six echo
fragments were (D117), position plus yaw; yaw aims the body. Everything else in D122 is finished and
keyed to that marker.

*The body template has not been seen draw.* `q105_jigjig_prostitute_dead.ent` is a real depot path
carrying a real quest corpse, but whether it renders as a body lying on the ground rather than a
standing T-pose has not been observed. Three fallbacks are listed in `world.json` under
`_alternatives`, including `base\characters\base_entities\corpse\corpse.ent` and, as the last resort,
Mara's own entity — right face, standing up, worse writing but unambiguously her.

*The dropped Liberty is a placeholder asset.* `ac_mara_liberty_drop` points at the D118 suitcase,
which is a known-good prop through the same glue system, so a failure to appear means the glue or
the coordinate rather than the asset. No weapon entity has been placed as a world prop in this
project yet.

*`ashcache_mara_autopsy_read` is set and read by nothing.* Declared anyway and flagged by
`validate.py` as such. Every other shard here sets a fact something can look at, and a shard whose
read is the one player action the mod does not notice is the exact defect D121 was opened to fix.

### D122a — the landfill was stood on (2026-09-18, same day)

`x=1544.9994, y=-1981.8353, z=73.3839, yaw=21.8821`, captured the D117 way. The first open item
above is closed; the paragraph stays as written because the *reason* it could not be derived is the
part worth keeping.

One measurement moved three nodes, which is the point of naming a marker rather than repeating a
coordinate: `ac_landfill_body` carries the map pin on `ac_obj_landfill` and the 12 m arrival watch in
`glue.json`, and `ac_mara_body` sits on the same point because she *is* the marker. No `z_offset` —
the captured z is where the player's feet were, which is exactly where a body on the ground belongs.
That is not true of `ac_splinter_box`, which sits on a bench and may still need its nudge (D118).

`ac_mara_liberty_drop` is the one node that is **derived rather than measured**, so `collapsedOnto`
came out and `verified` stayed `false`. It is 0.6 m along the right-hand vector of the body's own
yaw — `right = (cos yaw, sin yaw)` = `(0.9280, 0.3726)`, so `(1545.5562, -1981.6118, 73.3839)` — with
its own yaw at body+90 so the gun lies across her rather than in line with her, which reads as
dropped rather than placed. Deriving it from the yaw rather than picking an axis means it lands
beside her hand whichever way she ends up facing. `validate.py` now reports 22/23 positions stood on
and names that node as the one exception, which is the correct amount of noise for a coordinate that
is defensible but unobserved.

Re-verified after the edit: `validation OK`, `negtest 96/96`, `replaytest` clean, `descpanel` peak 1,
build `EXIT=0`, `lint_glue.sh` 0 warnings 0 errors, chip tree 0 errors. The coordinate is in the
generated glue at `AshCacheGlue.reds:140-141` (the area watch, X/Y only — proximity is 2D) and at
`:392` / `:399` (the two prop spawns). Still nothing deployed.

### D123 — Mara walks out (2026-09-18)

*"After the shootout, she should emerge from the clinic for a short dialogue, the purpose of which
would be to hint at the quest's continuation."*

Until now Mara existed for one conversation in Act 3 and a handful of SMS. The fight ended, the
street went quiet, and the next thing that happened was a choice hub with V standing alone. She had
promised to count the agents ("Keep your phone on. I'll count them for you.", D121) and she kept it
by text. D123 is her keeping it in person.

**Where the beat sits.** Between `progress_6` and `gate_hide` — so she speaks *before* the decision,
not after it. That ordering is the beat: what she says reframes the choice V is about to make, and
placing it after the hub would have made it an epilogue to a decision it is supposed to inform.
`source/scene_aftertalk.json`, 12 scene nodes, 13 spoken ids (`aftertalk.*`, ruids ...069–...081).

**How she "emerges from the clinic" without a new coordinate.** Since D87 this project ships no
`spawnMarkerNodeRef` on an actor: an actor spawns at the scene node's own `sceneLocation` with a
zero offset. Anchoring the scene at `#ac_clinic_entrance` — verified back in D9, and already the
decision scene's anchor — therefore puts her in the doorway as a *consequence of one line of the
graph node*. No animation, no walk path, and nothing new for the user to stand on and measure. OI-9
did not grow by one.

**The known risk, written down before testing rather than after.** She was already cast once, in
`ash_cache_mara.scene`, with `keepAlive 1` (D105), so an entity carrying the unique name
`ashcache_mara` may still be standing inside the clinic when this scene opens. Either the spawn plan
reuses her where she stands — lines play, nobody at the door — or it places her at this scene's
location, which is what we want. Only a playthrough decides. The **same** character record is used
deliberately: it cannot produce two Maras, which is the failure that would look unfixable. If she
does not appear, the fix is one edit — her own record in `characters.json` (same base, same
appearance, new `record` name) so the unique name differs and the spawn is unconditional.

**What she actually says**, and why it is the continuation hint: the splinter is a *cutting*. The
scan it grew from is still under **Cynosure**. That is not a promise this mod cannot keep —
`source/cynosure_graph.json` already streams those sectors on `ashcache_cynosure_open`, and Act 3
has said since D14 that the splinter "grew off your own Cynosure scan". The line was sitting there
the whole time; nobody had ever spoken it out loud. It also makes every ending provisional, which is
what a hint at a continuation is for: burn the case and Hale grows another one by spring.

**Two entry points, one exit**, the third use of the idiom after `scene_mara` (D14) and
`scene_decision`. The warm route opens with three lines, one two-option hub — both options reach the
same answer, because a branch twenty seconds before the real ending switch would be a second ending
switch — and closes on her going back inside to delete nine years of paperwork. The intimidate route
gets four lines and **no hub at all**: V is given nothing to say, which is the point of it. It still
delivers Cynosure. A sequel hook gated behind having been polite in Act 3 is a hook half the players
never hear.

`ashcache_mara_warned` is set inside the scene on both routes and filed under `discoveries`, not
under `mara` — it is not her disposition, it is something the player now knows. The graph reads it
only as `guard_aftertalk`'s re-entry guard (same shape as `guard_meet_mara` on
`ashcache_mara_choice_made`), so a `phase_revision` bump cannot drag the player back into a Tier3
conversation. What it is really for is a continuation opening on a save where it is 1.

`guard_aftertalk` also tests `ashcache_mara_dead == 0`. That is 0 on every route the graph can
currently produce, because `protect_mara` makes her Immortal and never releases it — written anyway,
for the same reason `gate_hide` writes it.

No new INT/RET pair: the scene raises the tier, so it needs the interruption net, and it reuses
`decide_int_wait` / `decide_ret_wait` the way the four epilogue scenes already do. The net is
nothing but "500 ms, then Tier1".

**A negtest that had quietly stopped testing anything.** `negtest.py` reported **95/96** with
`checks that did not fire: cast: character nobody casts`. The case emptied `scene_mara.json`'s cast
and expected validate's "no scene casts them" — but with a second scene casting Mara, emptying one
cast list no longer leaves her uncast. The case now *appends* a character nobody casts, which tests
the invariant head-on and cannot rot again as scenes are added. This is exactly what the "checks
that did not fire" line exists to catch, and it is the only reason the regression was visible.

Verified: `validation OK` (51 facts, 187 graph nodes, 8 scenes, 82 spoken lines, 22/23 positions
stood on), `negtest 96/96`, `replaytest` — `aftertalk_scene` fires exactly once on a fresh run and
zero times on re-entry — `descpanel` peak 1, build green with `ash_cache_r17.questphase` and
`mod\ash_cache\quest\ash_cache_aftertalk.scene` in the archive, `lint_glue.sh` 0 warnings 0 errors.
Both locales reached the cooked subtitle resources. `phase_revision` 16 → **17**. Nothing deployed.

### D124 — Mara calls (2026-09-18)

"Receiving only text messages is a bit boring." Fair. Eleven SMS nodes and no voice on any of
them. This is the quest's first holocall, and the first thing the investigation settled is that a
holocall is not a kind of message at all.

**The engine ships no scene-side phone event.** `strings -a Cyberpunk2077.exe` matches nothing for
`^scn.*(Phone|Call|Holo).*$`. The phone UI has exactly one door, `questCallContact_NodeType` under
`questPhoneManagerNodeDefinition`, and it is a QUEST node. So a holocall is two graph nodes with a
scene between them: the graph opens and closes the call, the scene is only the conversation inside
it. That is rule 1 not as house style but as the only available shape — a redscript holocall would
have to counterfeit a UI the game already owns. `HolocallStartEvent` is `importonly`, dispatched
from C++, and `questTriggerCallRequest` is an `import class`: nothing on the script side originates
a call.

The node's fields came out of vanilla, not out of a guess. `questCallContact_NodeType` does not
appear in any of the 80 EP1 phases already extracted, so 439 base-game `main_quests` phases were
unbundled (`phonecall_ex/`, read-only on the install) and three serialised. What they show:

    q112_03_infiltration   Takemura -> V, twice      StartCall then EndCall
    q104_gas_station       Panam -> V                StartCall then EndCall
    q105_lizzy             V -> Evelyn, V -> Judy    StartCall then EndCall

Three things worth writing down, because all three are counter-intuitive:

  * **Nobody uses `IncomingCall`.** Not once in six instances. The call simply starts. The obvious
    design — ring, wait on `questPhonePickUp_ConditionType`, then connect — is a graph that hangs
    forever on a player who does not answer. Vanilla does not take that risk and neither does this.
  * **`applyPhoneRestriction` reads backwards from its name.** `phoneSystem.script`'s `TriggerCall`
    only touches the restriction when the flag is 1, and on the `EndCall` branch it calls
    `ApplyPhoneCallRestriction(FALSE)`. So 1 on `EndCall` is what RELEASES the phone. Vanilla ships
    0 on start and 1 on end, and so do we. Copying the name instead of the behaviour would have
    locked the phone for the rest of the save.
  * **`showAvatar` is 0 in all six**, including calls that visibly show a portrait in game. The
    portrait comes from the contact's `avatarID`, which `ac_contact_mara` already has.

`mode` is `Audio`. `Video` is a real option and a real holocall in the strict sense, but it renders
the caller to a texture from a **holocall prefab** — q104 names one, `prefabNodeRef
#holocalls_studio` — and we have no such prefab and no puppet to put in it. Audio is what Takemura,
Panam, Judy and Evelyn all are.

**Two things this beat cost nothing to place.** The scene anchors with `type: Tag`, `tag:
around_player` rather than a NodeRef. The evidence is unusually clean: of the 15 scene nodes in
q112_03_infiltration exactly one uses a Tag, and it is the one called `q112_01b_market_phonecall`. A
call pinned to a marker is a call that stops working once the player drives away from it. And the
cast is acquired as a VOICE — `findInContext`, `contextualName: Voice`, field for field with
q005_07's penthouse Siri — so there is no entity, nothing to spawn, and no position to stand on and
measure. That also means the keepAlive question hanging over D123 cannot arise here: a voice actor
is never spawned, so a Mara left standing in the clinic is irrelevant to it.

No `set_tier` anywhere. q112_03 brackets two calls and contains one tier node in the whole phase,
`Tier1_FullGameplay`. V keeps walking. The one thing to watch in game is whether the choice hub
still draws while they do — every other hub in this quest has had Tier3 under it.

**Where it sits, and why.** Between the ending messages and the D122 landfill aftermath. After the
endings because what she is calling about is what V just did with the splinter; before the
aftermath because on absorb and blueeyes that is where she turns up dead, and a call from a woman
whose body the player has already found is a bug that reads as a ghost story. The gate is
`mara_dead == 0 AND mara_warned == 1 AND mara_called == 0`. Reading `mara_warned` rather than
`mara_trusted` is deliberate: the intimidate route gets the call too, because on that route she
gave V the address as well, just with worse grace.

What she says is the payoff for the last line of D123 — "Keep the phone on. One day you'll want the
address." She gives the address: Cynosure, the dig under the Badlands, and whatever the splinter
was cut from still on a rack down there. One version, no warm/cold split: she is not calling as a
friend on either route, she is closing a file, and that is as true after the intimidate route as
after the others.

**`replaytest` found a real hole in itself.** It reported `holo_scene: fires 4x`. The four ending
walks are four counterfactuals of ONE save — the player takes exactly one — so any node downstream
of where the four endings converge is reached by all four and summed. Nothing had ever run on every
ending from below that convergence before, so the flaw had never been visible.

The tempting fix was to credit those walks once each, the way the disposition and aftermath loops
already do. That is wrong: it would equally silence a guard that is SUPPOSED to read the ending and
has quietly stopped, which is the exact defect the loop exists to find. So the graph declares it
instead — `"every_ending": true` on `holo_scene`, read by `replaytest.py` and nothing else — and
only declared nodes are exempt. Checked both directions: remove the declaration and it reports
`fires 4x` again; break `guard_epi_destroy` and it still fails. An exemption that cannot be shown to
be load-bearing is an exemption that is hiding something.

New fact `ashcache_mara_called`, filed with the replay guards and set AFTER the hang-up, not before
the ring, so a save interrupted mid-call rings again rather than losing the address forever.

`questPhoneCallPhase`, `questPhoneCallMode`, `questPhoneCallVisuals` and `scnContextualActorName`
were added to `refresh_enums.py` rather than written as bare strings — WolvenKit's failure mode for
a bad enum is a `CEnum.Parse` stack naming neither field nor value.

Verified: `validation OK` (52 facts, 192 graph nodes, 9 scenes, 91 spoken lines), `negtest 96/96`,
`replaytest` — `holo_scene` fires exactly once on a fresh run and zero times on re-entry —
`descpanel` peak 1, build green with `ash_cache_r18.questphase` and
`mod\ash_cache\quest\ash_cache_holocall.scene` in the archive, `lint_glue.sh` 0 warnings 0 errors.
The built questphase carries `StartCall` restrict=0 and `EndCall` restrict=1 with caller
`contacts/ac_contact_mara` and addressee `contacts/player`; the built scene carries one actor,
`findInContext`/`Voice`, and `isHolocallSpeaker: 1` on all 7 of its spoken lines. 9 new subtitle
ids (`holocall.*`, 82 → 91), both locales in the cooked resources. `phase_revision` 17 → **18**.
Nothing deployed.

Open: no delay node exists in the engine (`^quest.*(Delay|Wait)NodeDefinition$` matches nothing), so
the call rings the moment the ending SMS is dispatched. If that reads as noisy, the fix is a
`questTimeManagerNodeDefinition` countdown, which is a new node type and was not worth one on
spec. Also open: the call gives the Cynosure address but does not set `ashcache_cynosure_open`, so
the bunker the address points at still only streams on the deliberate opt-in. Making the call open
it is one link — and a decision about holding two vanilla sectors loaded on every finished save,
which is a different conversation.

### D125 — The notes read themselves (2026-09-18)

"Modify the Toggle Audio feature so that while reading notes, V's voice reads them aloud." The
first thing to settle was whose feature Toggle Audio is, because it is not ours and it is not
vanilla's either.

**It belongs to an installed mod, and it was already pointing at our shards.** Nothing in
`Cyberpunk-Scripts` draws a Toggle Audio hint anywhere — the Shards codex and the shard popup
both ship `Close` and, for an encrypted one, `Crack`. The button comes from **Shard Audio
Framework**, `r6/scripts/shardaudioframework/shardaudioframework.reds`, which `@replaceMethod`s
`ShardNotificationController.SetButtonHints` and adds `ShardAudioFrameworkToggle` to **every**
uncrypted shard. So the button has been drawn on all five of this quest's notes since the day it
was installed, and pressing it has done nothing. The request is not to build a feature; it is to
answer one that is already asking.

**What it asks for is a CName, and the CName is a LocKey we already own.** SAF plays a shard with
nothing but the vanilla API:

    let text = StringToName(this.m_data.text);
    GameInstance.GetAudioSystem(GetGameInstance()).Play(text);

and `m_data.text` is filled by vanilla's own `ReadAction` (`readAction.script:18`):

    shardUIevent.text = entry.GetDescription();

`GetDescription()` returns the onscreen entry's RAW description string, not the localised prose —
which is why the framework's companion pack is keyed `LocKey#6139`. Our five `gameJournalOnscreen`
entries carry `LocKey#77315028 / 32 / 89 / 112 / 113`, so those five names are exactly what the
game will ask the audio system for. Audioware hooks `AudioSystem::Play(CName)` — that is the
inference D67 already banked, and the one that makes two mods by two authors into one working
feature — so answering them is a bank entry and nothing else. **Zero new redscript.** Writing our
own `@wrapMethod(ShardNotificationController)` would have collided head-on with SAF's
`@replaceMethod` of the same handler.

`tools/gen_audioware.py` derives the key from `source/items.json` + `source/lockeys.json`, the same
two files `gen_journal.py` builds the entry from, so it cannot drift from the note. Verified against
the built artefact rather than the intention: the five descriptions in `build/ash_cache.journal.json`
and the five `voices:` keys in the bank are the same set.

**The switch had to be taught the difference.** `wanted()` deletes the whole bank once the `.wem`
are real Wwise Vorbis, because then the engine plays the scene lines itself and the bank would
double them. That reasoning does not reach a shard: the engine has no voiceover path to a journal
entry at all — no scene is playing, and a `gameJournalOnscreen` has nowhere to hang a sound. This
mattered immediately, not theoretically: the 43 `.wem` in `vo/en-us/` ARE Vorbis now, so the bank
is currently off, and without splitting the two the notes would have shipped into a folder that
gets deleted. Spoken lines now drop out of the bank and notes stay in, and a notes-only build omits
the `dialogs:` key entirely rather than emit a bare one, which is YAML null and would fail to parse.

**What is read is the note.** Not a script written for the voice — the shard body itself, the same
string the journal draws. That is the beat ("as if he is reading them himself to find out what
happened"), and it also means a sixth note is voiced by writing nothing new. `narration_text()`
flattens it first, and the reason is a silent failure, not tidiness: **piper's CLI treats one line
as one utterance** and writes each to the file named by `-f`, so a five-paragraph shard would have
come out as its own closing sentence — well-formed audio of the wrong text, with nothing in any
log. Newlines are collapsed before any backend sees them. Brackets around a header go while the
words stay (a reader says "VOSS slash private", not "open square bracket"); a dangling dash becomes
an ellipsis, because "Take the—" is a man being cut off and "Take the." is a man finishing his
sentence. Durations were then checked against word counts — 150-205 wpm across all five, where a
truncated `mara_journal` would have been five seconds instead of twenty-nine.

`narration/<locale>/<onscreen entry>.wav`, a sibling of `vo/` and deliberately not a folder inside
it: nothing downstream is shared (no `.wem`, nothing in the archive, no `locVoiceoverMap`), and
`validate.py`'s rule that every directory under `vo/` is a locale that must ship voiceover is a
guard worth keeping rather than carving an exception into. It gets its own check on the same terms
as `vo/` — a recording naming no shard fails the build — which matters more here, because SAF draws
the button whether or not anything answers it, so the failure mode is a button that does nothing
and a build that says nothing. Three negtest cases cover it.

**The voice is a placeholder and must not be mistaken for shipped.** `male_v` is gone from this
machine. `reference/rvc_voices.json` pointed at `/mnt/sata/SoniTranslate/weights/MaleV-Cyberpunk2077.pth`,
and `/mnt/sata/SoniTranslate` no longer exists — it went when everything was moved under
`/mnt/sata/Cyberpunk2077/everything/`. `/mnt/sata`, `/mnt/ssd`, `/mnt/data` and `$HOME` have no
`*MaleV*`, no `*male_v*` and no `SoniTranslate*` anywhere. This is not a D125 problem and it is
bigger than D125: the 25 V lines already in `vo/en-us/` were rendered with it and are safe, but no
NEW audio in V's voice can be made until the file is back, and `render_lines.py` now refuses and
says so rather than substituting something. The five notes were rendered `--no-rvc` in piper's
`en_US-ryan-high` so the button can be tested at all; they are a stand-in, recorded as one in the
registry and in `narration/README.md`, and one `--force` re-render replaces them.

One content call worth naming: the courier log is an audio recording, and V reads its transcript
rather than the courier speaking. V's voice throughout was what was asked for, a courier model does
not exist, and a second voice for one note would be the only place in the quest where the narrator
changes. Open if it reads wrong.

Verified: `validation OK` (52 facts, 192 graph nodes, 9 scenes, 91 spoken lines, **5/5 notes read
aloud**), `negtest 99/99` (90 silent failures caught, 9 legal edits left alone — 96/96 before, three
new narration cases), build green, bank written with five `voices:` keys and no `dialogs:` section,
every key cross-checked against `build/ash_cache.journal.json`. `phase_revision` unchanged at 18:
nothing in the graph, the journal or any scene moved. Nothing deployed.

Open: the voice, above. Whether 150-205 wpm is the right pace for a man reading to find something
out — `NARRATION_LENGTH` is one number. Whether an autopsy report should be read aloud at all, or
only the three notes that are somebody's own words. And SAF's second entry point, the Shards codex
screen, plays from `m_selectedData.m_description`, which the non-crypted path sets to the same raw
LocKey — so it should work there too, and has not been looked at in game.

### D125a — V's voice came back (2026-09-22)

D125 shipped five shard narrations in piper's `en_US-ryan-high` because the `male_v` checkpoint
could not be found on any mount. It had not been lost. It is at

    /mnt/sata/Cyberpunk2077/rvc_voices/Male V cyberpunk2077/MaleV-Cyberpunk2077.pth
    /mnt/sata/Cyberpunk2077/rvc_voices/Male V cyberpunk2077/added_IVF2918_Flat_nprobe_1_MaleV-Cyberpunk2077_v2.index

and `reference/rvc_voices.json` now points there.

**It was re-verified rather than re-pointed.** The whole discipline of that file is that nothing in
it is inferred from a filename, and a file that has been away for four days and come back from a
zip is exactly the case that discipline exists for. `torch.load(map_location="cpu")` and
`faiss.read_index` on the restored pair return, field for field, what was recorded on 2026-09-04:
keys `config/f0/info/sr/version` (the pre-Applio shape, no `vocoder` key, which is correct for its
age), `sr='48k'` as a string against `config[-1] = 48000`, `version v2`, `f0 1`, `info '600epoch'`,
`enc_p.emb_phone.weight` of `(192, 768)` for contentvec, and an `IndexIVFFlat` of 113805 × 768.
Same model. The sha256 and both byte counts are now written down, so the next time this moves it is
one command rather than a re-derivation.

The five notes were re-rendered with `--shards --force`. Measured after, because a railed RVC model
produces plausible files and the mara collapse (D36) was caught exactly this way: durations land
within a few hundredths of the piper versions, so nothing truncated; levels are mean −19 dB with
peaks between −0.9 and −2.2 dB, which is real dynamic range rather than the −0.1 dB-in-silence
signature of a model that has railed.

What this unblocks is larger than the five notes. 25 V lines were already rendered before the file
went missing, but everything written since — the D120 epilogue, D121, D122, D123, D124, and D126
below — had no way to be voiced at all.

Open: none. The `johnny` entry still names two paths on the deleted `/mnt/sata/SoniTranslate` and
nothing matching survived the move; it is marked as a record of what the file was rather than a
path to read, and nothing depends on it (`role_in_quest: none`, and ua-ua ships subtitles only,
D42).

### D126 — the quest opens with a call (2026-09-22)

The prologue used to open with two SMS from an unknown number: the hook, and then a second message
carrying an attachment it could only describe — *"[attachment: audio, 2s] It is your voice.
Distorted. Saying words you never said. 'Don't let them delete me.'"* That is now a holocall from
the same number, in the same slot in the graph, between `await_start` and `quest_active`, so the
phone still leads and the journal still follows.

**The reason a call is better here and not merely different is that second message.** A text can
only tell the player about a recording. A call can play it. So the beat the SMS narrated is the one
beat this scene performs, and it is why the scene has a second speaker: `Echo`, whose single line is
rendered through `male_v` — not as a substitution, but because the echo was grown off V's scan, so
V's model *is* its voice. It is the one line in this quest that could not have been made at all
three days ago, and it is the reason D125a came first.

**Who is calling is still not established.** `docs/quest_design.md` gives the hook to "an unknown
number" and gives Mr. Blue Eyes his own contact and his own SMS later. Nothing in the new scene
hints, and the caller never answers `opt_who`. That is not an oversight left for later — after
"Who is this?", *"It was."* reads as a refusal, and after "That's my voice." the same two words are
an answer. One line, both jobs.

**Two bodiless cast members, and the honest way to declare them.** `characters.json` grew a
`"voice": true` flag. A voice is cast only in holocall scenes, where `gen_scene.py` builds it with
`voice_actor_def()` — `findInContext`, contextualName `Voice` — so there is no entity to place. Three
tools read the flag: `validate.py` stops demanding a `marker` (there is no spawn for a missing marker
to send to the world origin), `gen_tweak.py` stops writing `uiNameplate` (a nameplate is drawn over a
head), and `validate.py` refuses to let a voice be cast in a scene that is *not* a holocall — the one
way the flag could go wrong quietly, since `actor_def()` would then want the marker that is no longer
required. Both inherit `Character.q005_penthouse_siri`, which is not a stand-in: it is the penthouse
AI in `q005_07_vip_apartment`, the one vanilla actor on this machine that speaks without a body, and
the same scene `voice_actor_def()` was built field-for-field from in D124.

**The caller has no RVC model on purpose.** `VOICE_OF["Unknown"]` is `None`, which the renderer now
reads as "TTS, no conversion" — distinct from an actor being *absent* from that table, which is a bug
and still gets skipped loudly. Somebody masking their voice should not come out sounding like a
specific human being. The check that decides this moved from being a property of the run (`--no-rvc`)
to a property of the line, so one unconverted speaker does not turn conversion off for the rest of
the cast sharing the render.

**The guard is the part that was not obvious.** Two `journal_entry` nodes needed none: re-activating
a message already in the thread shows the player nothing. A call is not idempotent. A
`phase_revision` bump re-walks a finished save from the top, and without `ashcache_hook_called` the
opening hook rings again hours into the quest, explaining a burn order the player has already beaten.
It is set *after* the hang-up, never before the ring, so a save interrupted mid-call rings again
rather than losing the address — and at that point the address is the whole quest, because no
objective has been raised yet.

**The contact stayed; the thread went.** `ac_contact_unknown` is what the `questCallContact` node
names and what supplies the name and avatar the phone draws while it rings, so it had to survive. Its
two messages did not. `gen_journal.py` now reads an empty `messages` list as "a contact who calls and
never texts" and emits the `gameJournalContact` with no `gameJournalPhoneConversation` under it —
without that, the one visible scar of this change would have been a blank thread sitting in the
player's messages app under a name, with nothing in it to open. `type` is `Caller` now rather than
`Texter`, and the strings went with the messages rather than being left unreferenced, because a
string nothing names still ships in all 18 locale files and still reads as live content. Their
LocKeys stay allocated and are never reused.

`phase_revision` is deliberately NOT bumped, and this is the one decision here that costs the user
something. Bumping is how an existing save is made to re-enter the phase — but re-entry on a save
that is already past this point would walk through `guard_hook` with `ashcache_hook_called` still 0
and ring the opening hook in the middle of act 4. Leaving it at 18 means the change reaches a fresh
run of the quest only. Testing this beat needs a save from before `q304_done` completes, or the CET
force-start hook on `ashcache_start`.

Open: whether the phone UI actually opens, which is still D124's unanswered question and now has a
second data point — `ac_contact_mara` is a `Texter` and this one is a `Caller`, so if one draws right
and the other does not, that field is the difference. Whether a call landing 30 real seconds after
Somewhat Damaged ends collides with anything (the scene is anchored `around_player` precisely because
V could be anywhere). Whether the hub draws with no Tier3 under it — the same question D124 left, and
it matters more here, because this fires at a moment the player did not choose. And whether the
masked caller reads as deliberate or as a voice nobody got round to finishing.

### D126a — the renderer was quietly shipping PCM (2026-09-22)

Found while building D126, not looked for. Rendering the 56 outstanding lines flipped
`gen_audioware.wanted()` from "bank off, the engine plays them" to "bank on" — and the reason it
gave was the point: *"37/80 .wem are not Wwise Vorbis"*.

Measured rather than reasoned about: the 43 lines already in `vo/en-us/` carry `fmt` tag `0xFFFF`,
and every newly rendered one carried `0xFFFE`. Two writers, two formats. `tools/wwise_wem.py` makes
real Wwise Vorbis through the Wine Wwise (D89-D91); `tools/wav_to_wem.py` is the no-Wwise fallback
and writes PCM, which is proven on the soundbank-media path and **not** on `locVoiceoverMap`, where
all 342 custom voice lines across the installed mods are Vorbis.

`build.sh` already runs them in the right order — Wwise first, the fallback second, so Wwise wins
wherever it is installed. What defeated that is `render_lines.py`, which wrote the `.wem` itself
immediately after the `.wav`. Both converters skip a `.wem` newer than its source, so the PCM file
was already "current" by the time the build looked, and Wwise never touched it. The line then ships
PCM on the voiceover path, which is silence.

`vo_promote.py` has always deleted the `.wem` on the way in and its header says exactly why — "let
the build convert. One rule, no race". A render written straight into `vo/` simply never went
through it, and that path did not exist when the rule was written.

Fixed at the source: `render_lines.py` still writes a `.wem` for an audition (`--out`), where it is
the point, and into `vo/` now removes any stale one instead. The 56 were deleted and re-encoded with
Wwise; all 99 read `0xFFFF` now, and the bank has gone back to carrying the five notes and nothing
else.

Worth noting what saved it. Nothing failed, nothing warned, and the build stayed green throughout —
the only visible symptom was an `ASHCACHE_AUDIOWARE` switch changing its mind, and it changed its
mind *correctly*, because it is a measurement rather than a flag. Had the bank not existed, 56 lines
would have shipped as subtitles over silence.

### D127 — three bugs from the first real playthrough of the ending (2026-09-22)

All three came back from one session in game, and they are worth writing down together because two of
them share a cause and the third is the reason nobody had seen the first two before.

**The woman standing on the landfill.** D122 put Mara's body at the junkyard using
`q105_jigjig_prostitute_dead.ent`. In game that draws a living, undamaged sex worker standing
upright, and shooting her crashes the process.

The D122 reasoning is preserved in `source/world.json` because half of it was right and that half is
still useful: character records named `*_dead` really are ordinary living NPCs —
`q001_scavenger_dead_man`, `q105_jigjig_prostitute_dead` and Mara's own base record carry identical
`statPools`, `visualTags`, `appearanceName` and `reactionPreset`. The conclusion drawn from that was
that the deadness must live one level down, in the entity template, and the `raRef` hashes were
resolved against `depot_files.txt` to find it.

It is not there either, and the file says so plainly the moment it is opened.
`q105_jigjig_prostitute_dead.ent` has **110 components** — `gameAttitudeAgent`,
`gameSquadMemberComponent`, `gameInventory`, `StimBroadcasterComponent` — and its eight appearances
are every one `service__sexworker_wa_prostitute_poor_0N`. It is a complete NPC puppet with a full AI
stack. The deadness was never in a resource at all: q105 spawns her alive and kills her from quest
script, and `_dead` is a note the author left for themselves about which beat the file belongs to.

That also explains the crash. `AshCachePropSpawn` builds a `DynamicEntitySpec` with
`persistState: false` and `persistSpawn: false`; killing an NPC runs the game's whole death pipeline
— loot, death signal, persistent body registration — against an entity that was never registered for
any of it.

The right object was one directory over, in `entities/` rather than `characters/`, and CDPR's own
word for it is *fluff* — set dressing. `q105_fluff_dead_body_01.ent` is eight components headed by
**`entCorpseComponent`**, one appearance, `wa_q105_fluff_01_corpse`. `wa` is woman-average, so it is
a female body. No attitude agent, no squad, no inventory, no health: nothing to anger, nothing to
loot, nothing to kill. Its two siblings `_02` and `_03` are recorded as swaps in `world.json`.

The same pass retired the D118 placeholder beside her, which was drawing *a biochip suitcase* on the
ground in place of her Liberty. `int_weapons_002__constitutional_liberty__base1.ent` is **one**
component, `entAnimationControllerComponent` — a weapon-shaped mesh with no item record and no pickup
logic, safe for exactly the reason the corpse is. It ships ten appearances and defaults to Rogue's
engraved one, so `tools/gen_glue.py` grew an optional `appearance` on a prop state and passes it
through `DynamicEntitySpec.appearanceName`.

**The rule, stated once so it does not cost a third time.** A filename is a label its author chose.
The only thing that says what a resource *is* is the resource. Extract it and read it —
`reference/rvc_voices.json` has said the same about checkpoints since the mara collapse, and this is
the same mistake in a different file format.

**The choices that vanish and the quest that waits.** Reported as "when you do everything too
quickly, or when Barghest coincide with the choices, the choices disappear and the quest waits for
something."

`reference/interruption.md` — measured over all 2,860 shipped `.questphase` files — records that a
scene interruption **pauses and resumes a conversation and never ends one**. That is the mechanism,
and the consequence nobody had drawn from it is that a scene only pauses for reasons it has
*declared*. Every scene here declared exactly one: the speakers walking apart, `Greater 6` / `Less
5`, inherited from the Undermine template.

Combat was not on that list, so when Barghest open fire mid-hub the engine does nothing at all. The
game hides the dialogue HUD in combat — that is the choices disappearing — while the scene stays
parked on its choice node waiting for a selection the player can no longer make, and the graph waits
on an exit that can never fire. On the four scenes that raise the tier (mara, aftertalk, decision,
epilogue) V is also pinned at `Tier3_LimitedGameplay` with `emptyHands` while being shot at: frozen,
unarmed, and unable to end the conversation that is freezing them.

The fix is to declare it. `interruption_scenario()` now carries
`scnCheckPlayerCombatInterruptCondition { isInCombat: true }` and
`scnCheckPlayerCombatReturnCondition { isInCombat: false }` alongside the distance pair. Both types
are in the RTTI with a single `bool`, five shipped files author the interrupt half, and the wrapper
shape is the one already proven by the condition sitting next to it in the same array. Combat now
becomes the engine's own pause/resume: `Default INT` fires, the wired net hands back Tier1 after
500 ms so the player can fight, and when combat ends `Default RET` fires and the conversation resumes.
It is added to every scene including the holocalls — a call that keeps talking over a firefight is the
same bug with a smaller blast radius, and vanilla holocalls pause for combat too.

**Mara dying whichever way the chip goes.** On the graph as written she dies in exactly two endings,
absorb and Blue Eyes — the two that leave the cache alive in the world — and burning it should leave
her alone. Tracing the chain, `route_body_destroy` does take its False socket to `quest_done`, so
burn really does skip the aftermath.

What the trace did turn up is that **Blue Eyes was reached by elimination**: not hide, not destroy,
not absorb, therefore Blue Eyes, therefore a body. "She is dead" was the default outcome of the whole
chain, so any state in which no ending fact is set at all reads as the one ending that kills her, and
the player is shown a corpse for a choice they did not make. `route_body_blueeyes` now tests
`ashcache_end_blueeyes == 1` and its False socket goes to `quest_done`. One node, and the class is
gone.

It is **appended at the end of the nodes array**, not written beside its siblings, and that is not
cosmetic: `gen_questphase` numbers nodes by their position in that list (`enumerate(specs)`), so
inserting one in the middle renumbers every node after it and a save parked mid-phase resumes against
the wrong ids. Position in the array carries no meaning; the links do the wiring.

### D127a — the build that was reported green and was not (2026-09-22)

Found while fixing the above, and the most expensive thing in this entry.

**D126 never built.** `build/ash_cache.questphase.json` on disk contained zero occurrences of
`ashcache_hook_called`: the opening holocall, the whole feature, had never reached an archive.
`gen_questphase` had been exiting on three links left over from the two SMS nodes the hook replaced —
a condition entered on `Active` (which had been `sms_hook_01`'s socket), and two links into
`quest_active` naming none of its four inputs. A fourth defect sat behind them, a one-term `"all"`
condition, which `build_condition` rejects because a logical operator needs two operands.

`build.sh` is `set -euo pipefail` and failed honestly with exit 1. Nothing was wrong with the
tooling. The failure was in the reporting: the scene files are written *before* the questphase, they
all succeeded, and a glance at the tail of a long build read as success. The build was called green
in a hand-off message and it was not.

Two things changed so that it cannot repeat quietly.

`tools/validate.py` grew `check_graph_sockets()`, which resolves every link against
`gen_questphase.inputs_of` / `outputs_of` — imported, not copied, so a node type that grows a socket
cannot make the two drift. `validation OK` and "the build works" had become two different claims
about the same file, and this closes the gap: the cheap tool now fails first. Three `negtest` cases
pin the three live shapes (101 → 104).

**`phase_revision` 18 → 19.** D126 inserted five nodes near the top of the array, so every id after
them moved. A save parked mid-phase against r18's numbering would resume against the wrong nodes. A
bump is safe here because every side effect sits behind a guard that reads a fact the player already
has — `tools/replaytest.py` proves a re-entry fires none of them — and `guard_hook` now also tests
`ashcache_progress == 0`, so the re-walk rings the opening call only for a player who had not started
the quest yet. That second term is what makes the bump free: D126 declined to bump precisely because
it feared re-ringing the hook hours into a playthrough, and testing one fact removes the fear.

### D128 — the quest borrows Farida's doors instead of keeping them (2026-09-22)

**Report.** *"After this quest, the clinic becomes fully accessible. However, to avoid
conflicts with the Phantom Liberty quest (where Farida installs a facial implant for V),
this quest should close the doors when it starts to prevent any bugs; otherwise, the
location can be freely entered before that."*

The clinic is not ours. It is `loc_q303_macs_clinic`, dressed by q304 as Farida's, chosen
in D19 because it is the only ripperdoc clinic in Dogtown with a registered pedestrian
entrance. D99 added two `ForceOpen` nodes after `await_clinic` to get the player in. What
D99 never added was the other half: nothing ever closed them again, so from the first visit
onward Farida's front door stood open for the rest of the save — for her mission too.

### An action on a door is an action on the save, not on the door

`DoorControllerPS` is a *persistent state*, and all three handlers end the same way:

    OnQuestForceClose  :135551   SetIsOpened(false)                  SetIsSealed(false)
    OnQuestForceLock   :135640                      SetIsLocked(true) SetIsSealed(false)
    OnQuestForceOpen   :135528   SetIsOpened(true)  SetIsLocked(false) SetIsSealed(false)
                                 -> EntityNotificationType.SendPSChangedEventToEntity

The state changes first; the entity is told afterwards, *if one is streamed in*. That is
why these nodes can run at the opening holocall with the player anywhere in Night City, and
it is the answer to the caution D99 wrote into `open_clinic_entrance`'s comment — that node
was placed after `await_clinic` to be safe, not because it had to be.

Two consequences follow directly from the table:

- **Close does not lock.** `ForceClose` leaves `isLocked` untouched, and an unlocked vanilla
  door opens on approach. A close on its own would have shut the door and changed nothing
  about who can walk through it, which is exactly the "freely entered" being reported.
  Hence a `ForceLock` behind each close.
- **One node undoes both.** `ForceOpen` sets opened, unlocked and unsealed together, so the
  act 2 pair that already exists reverses the new pair exactly. No third node type, and no
  way for the quest to leave a door locked behind it.

### Shape

Four nodes, appended to the end of `nodes` — never inserted, because `gen_questphase`
numbers nodes by position and an insertion renumbers every node after it (D127):

    quest_active -> close_clinic_entrance -> lock_clinic_entrance
                 -> close_clinic_inner    -> lock_clinic_inner -> obj_dogtown_on (Active)

`quest_active` is the journal entry going Active, i.e. the moment the quest exists at all.
Both doors are treated identically so the invariant is one sentence: whatever this quest
shuts, the same two `ForceOpen` nodes reopen. Afterwards the doors stay open, which is the
"fully accessible" the report asks for and the behaviour that already shipped.

**No `phase_revision` bump.** It is still 19 from D127, which is enough: appended nodes
leave every existing id where it was, and the r19 re-walk is self-healing for a save parked
mid-quest — it passes the new close/lock pair, then reaches `await_clinic`, whose fact
`ashcache_at_clinic` is already 1 for anyone who got that far, and the `ForceOpen` pair
fires again in the same walk.

### The risk this carries

A player who starts Ash Cache *while q303/q304 is in progress* gets Farida's door locked
under them. q304's own quest nodes should take the door back the moment its objective
needs it — quest device actions are last-write-wins on the same persistent state — but
nothing here proves that. The clean fix is a condition on the new pair testing a vanilla
q304 fact, which needs a fact name measured out of the shipped questphases rather than
guessed. Not built; recorded here and reported.

Backup: `source/quest_graph.json.bak-2026-09-22-d128`. Build green: `validation OK`
(200 graph nodes), replaytest clean, `ash_cache_r19.questphase`, 0 redscript warnings.

### D129 — Cynosure is under the motel, and the way in is now an experiment rather than a theory (2026-09-22)

**Ask:** "Something needs to be implemented regarding the Cynosure location."

Cynosure was named in the prologue call, in Mara's two clinic lines, in the
splinter's own description and in the ending holocall that hands V the address —
and there was nothing there. The way in had been built (D31) and then pulled
(D116) after every save crashed at world load. So the request split in two, and
the user chose both halves: content that ships, and the measurement that D116
left undone.

#### What the geometry actually says

`quest_c5762a0914e51033.streamingsector` — the outer bunker — unbundled out of
`ep1_1_nightcity.archive` and serialised: 469 nodes, and their transforms run

    X  -2411.5 .. -2074.3      Y  -2598.4 .. -2166.3      Z  -208.4 .. -57.1

Cynosure is not under the Badlands. It is directly under Dogtown, and the motel
at (-2240, -2553) sits **inside** that horizontal footprint, roughly 250 m above
it. The clinic at (-1900, -2477) does not — it is 26 m east of the bunker's
eastern edge. The prefab path had been saying so since D30 and nobody read it:
`$/03_night_city/c_pacifica/...`.

That is a gift, not a problem. The courier hid the box in a motel wall directly
over the hole it came out of; he never got off the site. It is also the one
thing in this quest the player can verify by looking at a map.

#### The beat

A second optional objective in `ac_ph6_aftermath`, `ac_obj_cynosure`, hung off
`quest_done` — the shape D122 established for the landfill: the journal already
reads complete, the phase quietly waits, and never going is a legitimate way to
finish. One link replaced, eight nodes **appended** (D127's positional-id rule),
200 -> 208 nodes, 252 -> 261 links.

    quest_done -> obj_cynosure_on -> desc_cynosure -> wait_cynosure
               -> guard_cynosure_seal -> give_cynosure_seal -> mark_cynosure_seal
               -> obj_cynosure_done -> desc_cynosure_off -> phase_out

`ashcache_at_cynosure` comes from the glue's 12 m watch at stage 7 — the
landfill's radius and the landfill's reasoning, because the shaft head is a
piece of Dogtown the player already walked past in act 1. The payload is one
shard, `ashcache_cynosure_seal`: an FIA closure order welded to the shaft head.
No prop and no interaction, because the fiction is that the way down is already
shut, and because an unverified coordinate can hold a map pin but must not hold
an object.

The shard also does the reconciling. Mara says on the phone that the dig runs
under the Badlands; the geometry says Dogtown. The plate says the Badlands
portal is the **listed** approach and has been nine kilometres of collapsed
tunnel since '69, so every survey goes down Shaft 14 and gets filed as a
Badlands entry. The contradiction becomes the reason nobody has looked at the
archive in four years, and no voiced line has to be re-cut.

**Not built:** the marker `ac_cynosure_shaft` is PROVISIONAL. It carries
`ac_motel_entrance`'s verified coordinate with `collapsedOnto` declared, so the
pin, the GPS route and the trigger all work on the first test — but the real
shaft head wants to be off the lot, not at the front door. `glue.json` names the
marker and not a coordinate, so one stood-on capture moves all three at once.
The shard is also the sixth note and the only one not read aloud (5/6) — V's
narration needs a render, which is a GPU job and a separate round.

#### The experiment D116 never ran

D116's table has three filled cells and one empty one:

| injected phases         | result                               |
|-------------------------|--------------------------------------|
| none                    | clean                                |
| quest phase alone (r11) | clean across repeated loads          |
| quest + Cynosure        | every save crashed at world load     |
| **Cynosure alone**      | **never measured**                   |

Until that cell is filled, "two injected phases" and "the bunker prefab refs
resolve while the save is being restored" are both standing explanations, and
the second one has a mechanism worth stating: a vanilla phase is reached through
a `phaseResource` DepotPath on a parent node, so its `phaseInstancePrefabs`
resolve when the player enters it. ArchiveXL injects ours into the **root** quest
graph, so the resource is loaded while the save is restored — on a loader
thread, which is exactly where `WaitUntilLoaded` asserts. That would fire with
the fact at 0, because resolution happens at load, not at entry.

`gen_xl.PHASES` is now a mode rather than a list: `ASHCACHE_CYNOSURE=only`
injects the Cynosure phase and not the quest, `=both` reproduces the fatal
pairing, unset ships the quest alone. The mode also decides what `build.sh`
packs, so the experiment is two files and nothing else moves. Built and stashed
in `mod/bisect/` with its own README; `tools/deploy.sh` has never heard of that
directory, so it cannot ship by accident.

**`cynosure_graph.json` phase_revision 1 -> 2.** Not because the graph changed —
it is what D31 built. Because ArchiveXL force-starts an injected phase node only
while its derived fact is 0 and sets that fact to 1 immediately, whether or not
the phase ran, and the D116 crash happened *at world load, before it ran*. Every
save that loaded a build between 09-04 and 09-17 is therefore marked as having
already started r1. Re-testing r1 on those saves would have measured nothing at
all. D21 and OI-15 say this; it needed saying again for a resource that never
executed.

**No `phase_revision` bump on the quest graph** — still 19 from D127. Appended
nodes leave every existing id where it was, and r19's re-walk already reaches
the new chain: it passes `quest_done`, hits `wait_cynosure`, and parks there for
a save that has not been to the shaft, which is the correct place for it to park.

**Verified:** validation OK (208 graph nodes, 121 lockeys, 9 items, 11 markers,
22/24 stood on), replaytest clean, descpanel peak 1, redscript 0 warnings 0
errors, shipping archive carries `ash_cache_r19.questphase` and no Cynosure
phase, experiment archive carries `ash_cache_cynosure_r2.questphase` and no
quest phase. Nothing deployed.

### D130 — The meeting with Mr. Blue Eyes (2026-09-22)

**The gap.** He has been in this quest since D5 and has never been in a room. Two
SMS, one ending, one phone avatar. The ending named after him does not even meet
him: D120 made it a drop box at the clinic, thirty seconds after the decision,
and the objective's map pin pointed at `ac_blueeyes_meet` — a *deferred* marker
that resolves to nothing, so it has been drawing no pin at all since D5.

**What ships.** A third optional beat in `ac_ph6_aftermath`, `ac_obj_meet`, in
D122's shape: parked between the quest being logged complete and `phase_out`, so
never going is still a legitimate way to finish. It opens when the shaft-head
beat closes, runs on **every ending**, and is one conversation with no item,
no money and no fight in it.

**He is vanilla, and he is verifiable.** `Character.q203_mr_x` is his own record:
its `entityTemplatePath` is the raRef hash 2012867658149774415, which is FNV1a64
of `base\quest\main_quests\epilogue\q203\characters\q203_mr_x.ent`, and AMM's db
lists that record as *Mr. Blue Eyes (G-Man)* with exactly one appearance,
`corporat_ma__q003_gman`. The record's own `appearanceName` flat is empty, so
naming that appearance in `characters.json` supplies what `gen_scene.py` needs
rather than overriding a choice. His nameplate reuses `sms_blueeyes_title` — NO
CALLER ID — the way the unknown caller reuses `sms_unknown_title` (D126): V never
gets another handle for him, and eighteen locales get the right one for free.

**He has no voice, and that is a measurement.** A scan of all 110,495 English VO
files finds no line for him under any of his names: `blue_moon` (the singer) is
the only `blue` speaker in the game, and `base\quest\holocalls\mr_blue_eyes`
ships a scene with no audio behind it. There is nothing to clone and nothing to
train on, so `render_lines.py` maps `BlueEyes` to `None` — the TTS front end
*is* his voice, `en_US-ryan-high`, flat and unhurried. Same value as `Unknown`,
different reason: that one is masking a voice, this one is a man nobody has ever
heard.

**Four doors, one exit, one node.** The scene has four entry points — sell,
absorb, destroy, hide — chosen by four *positive* conditions on the same
`ashcache_end_*` facts the ending switch reads, and a fifth outcome (no ending
fact set at all) that reaches no door rather than the last one. That is D127's
bill being paid: reaching an outcome by "not the other three" is how the landfill
once showed a body for a choice the player never made. The four doors converge
after two lines each, because what he has come to say does not depend on the
answer — only his opinion of the person he is saying it to.

One quest node with four entries and one exit, not four nodes. D120 needed four
for the epilogue because a shared node there would have had four live *exit*
sockets; `scene_aftertalk.json` already ships two entries into one. `replaytest`
still reported it twice, which is what `every_ending` exists for (D124): the four
ending walks are four counterfactuals of one save, and the flag credits the node
once. The claim is true by construction here and the replay guard above it is
still counted separately.

**Stage 8.** `ashcache_progress` ran 0→7; the aftermath's second leg makes it 8.
Without it the arrival watch on the meeting and the arrival watch on the shaft
head would both be armed on stage 7 **at the same point** — the meeting would
start on the step that grants the closure order, before the message that asks
for it. `validate.py` checks a glue stage against the window the graph opens for
it, so this is a claim the build re-checks.

**Where he stands, and why it is not where I wanted him.** The first cut put him
on a new marker, `ac_blueeyes_meet`, carrying the motel entrance's coordinate
with `collapsedOnto` declared — the D129 shape. `validate.py` refused it twice:
a scene origin and a spawned actor may not sit on a position nobody has stood on.
That rule is right and it is the rule D129 wrote down, so the meeting is anchored
on `#ac_motel_entrance` itself, a verified coordinate, and `ac_blueeyes_meet` is
retired rather than left deferred. The lot is the argument anyway: D129 measured
the outer bunker at X −2411..−2074, Y −2598..−2166, so the motel forecourt is the
roof of Cynosure, and the first place the quest ever sent V is the last place it
leaves them.

**He despawns.** No `keepAlive` (D105), so the engine takes him the frame the
scene ends, and the last line is written to be delivered on the way out. It is
also the only way not to leave a shootable Character record standing on a Dogtown
pavement — D127 is the invoice for the other choice.

**The payload is a fact, not an item.** `ashcache_blueeyes_offer`, set by the
scene's last beat and read by nothing in this build: the save-game record that
the offer on whatever is still under Shaft 14 is open. Same job
`ashcache_mara_warned` does for D123. Three shards in three consecutive beats
would have been a shop, and what this beat has to give is a sentence about why
somebody welds a door in a hurry.

**Cost:** 14 graph nodes appended (208 → 222) and one link replaced,
`phase_revision` deliberately still **19** — appending keeps every existing node
id stable, and no save has ever loaded the D129 beat that this one hangs off.
17 new spoken lines plus 2 options, rendered in en-us, subtitled in both locales.

**Known gap:** no lipsync take. `gen_lipsync.py` is Mara-specific — a female
basis take on a female rig, hard-coded output path — so he speaks with a still
mouth while the scene's emotion idles animate the rest of his face. Tracked as
OI-25.

**Verified:** validation OK (222 graph nodes, 124 lockeys, 11 scenes, 118 spoken
lines, 118 voiced line files, 4 characters, 22/24 stood on), replaytest clean,
descpanel peak 1, shapetest OK, redscript 0 warnings 0 errors, build exit 0,
quest block `ash_cache_r19.questphase`, both locales carry the new UI text.
Nothing deployed.

**Addendum — the no-RVC path ships unmixed.** The 17 lines came out of piper at
full scale, peaking 32767 against a median of 22182 across the 99 lines already
in the quest: about 3.4 dB louder than V and Mara, in a conversation with V. The
cause is structural rather than a bad render — every other voice in this mod goes
through RVC, which normalises on the way out, and he is the first character whose
audio is the TTS front end itself. Only a handful of isolated samples touched
0 dBFS, so nothing was actually distorted; the fix was a flat 0.677 gain to the
family level and a re-encode (`wwise: 17 encoded`). Anything else mapped to
`None` in `VOICE_OF` will arrive the same way and needs the same pass.

### D131 — Shaft 14 becomes a site you work (2026-09-22)

**Ask:** "some implementation of Cynosure location is needed because, according
to the quest, this location is very poorly explored and leaves one in a stupor."

Fair. D129 gave Cynosure an objective and a shard: walk to a pin on a parking
lot, take a silent grant, objective closes. The place the whole plot is named
after — the prologue call, both of Mara's clinic lines, the splinter's own
description, the holocall that hands over the address — was a map marker and a
notification toast.

#### What ships

`source/scene_cynosure.json`, `scene_terminal.json`'s shape exactly: `actors []`,
a world-attached prompt on the pad, and options that set a fact and **loop back
to the hub**. A failing condition removes an option rather than greying it out
(OI-14), so the menu shrinks as the site is worked, in whatever order the player
likes, and stops when they leave.

| option | costs | pays |
|---|---|---|
| pull the closure plate | 4 s bar | the FIA closure order (D129's shard) |
| jack the maintenance port | 6 s bar | the survey abstract — **new** |
| put a hand on the weld | nothing | no item at all |

The survey abstract is the round's payload and the first description of Cynosure
as a place: nine levels, minus one the landing, minus three the cold store, minus
seven the archive, four through six flooded since '71, minus eight a containment
bay sealed from the inside and "not ours". V's scan is on minus seven, Tier 3,
originals included. And the cold store is short exactly one item — **0-1140**,
the number already stencilled on the splinter in the player's own inventory
(`hud_absorb_top`) — signed out nine years ago on a Tier 3 badge that resolves to
nobody, by a carrier who never signed out at grade. He got as far as a motel wall
250 m straight up, which is where act 1 begins.

The weld is worth no item and is the best beat on the site. The plate is warm,
the air moves *outward* through the seam, and the pumps on the landing log a
maintenance cycle every eleven days on a facility that has been shut for four
years. `ashcache_cynosure_alive` is read by nothing, like `ashcache_blueeyes_offer`
— it is the save-game record that V felt it.

#### Three things the tools decided, not me

**An all-conditional hub is a softlock, and validate.py knows it.** The first cut
had five options, every one of them fact-gated — including two mutually exclusive
"head out" variants, which I could prove always leave exactly one available. The
validator refused it anyway, and it is right: "I can prove one is always visible"
is exactly the argument that is wrong once a fact misfires, and the failure mode
is a tier-raised scene the player cannot leave. The informed sign-off moved onto
the discovery that earns it — `seam_4`, "it's under my feet, and it's running" —
and the way out is now unconditional.

**A scene sets facts; the graph hands out objects.** Both grants sit behind the
scene, on the facts it set, which is also why both shards arrive as ordinary
notifications after V steps back rather than mid-conversation.

**`replaytest.py` learned what optional means.** Its invariant A is "every
side-effect node fires exactly once in a fresh playthrough", and zero is an alarm:
a guard stuck shut. Both new grants hang off hub options, so `scene_facts()` is
right to withhold their facts (it credits only facts whose node *dominates* the
scene's exit) and both reported 0x. The blanket fix — a node-level "optional"
flag — would have silenced the alarm for good. Instead the tool got a `site()`
counterfactual walk, the same shape as `dispositions()` and `aftermath()`: drop
the site marker to re-open the scene guard, set both option facts, credit only
what nothing else reached. It proves the grants are *reachable*. Checked by
breaking it: with `guard_cynosure_survey` inverted, the walk still reports
`give_cynosure_survey: fires 0x`.

#### Audio, and a confirmation of D130's addendum

20 spoken lines (V, piper `en_US-ryan-high` → `male_v` RVC, CPU, 3m25s) and the
two shard narrations — `cynosure_seal`, which D129 left as the one note not read
aloud, and the new `cynosure_survey`. **7/7 notes read aloud** now.

Levels came out in family with no gain pass: new lines peak at a median 23585
against the shipped 22182, narrations at 28136 and 29401 against an existing
25322–29437. That is the other half of D130's addendum measured from the other
side — RVC normalises on the way out, so a line that goes through it needs
nothing, and the 3.4 dB the Blue Eyes lines arrived hot was the no-RVC path and
only the no-RVC path.

#### Graph

Eight nodes **appended** (222 → 230), 14 links added and 3 rewired (282 → 296),
`phase_revision` deliberately still **19**: appended nodes leave every existing
id where it was, and r19's re-walk reaches the new chain and parks at
`wait_cynosure` for a save that has not been to the shaft.

    wait_cynosure -> guard_shaft_site -> shaft_scene -> mark_shaft_site
                  -> check_plate -> [guard/give/mark closure order]
                  -> check_port  -> [guard/give/mark survey abstract]
                  -> obj_cynosure_done

`guard_shaft_site` is the beat's replay guard and is set the moment the scene
exits, whatever the player did on the site; `guard_cynosure_seal` keeps the job
it has had since D129 and `guard_cynosure_survey` is its twin (D50: one guard per
irreversible node). The scene raises the tier, so `Default INT` / `Default RET`
are wired to the shared `decide_int_wait` / `decide_ret_wait` pair.

**Still not built.** The scene is anchored on `#ac_motel_entrance` because
`validate.py` refuses a scene origin on a position nobody has stood on — D129's
own rule, D130's bill. `ac_cynosure_shaft` carries that same coordinate today, so
the pin, the 12 m arrival watch and the prompt are one point; a stood-on capture
at the real shaft head moves all three together and lets a hatch prop stand there
at last. And the way *down* is still one save load away: `mod/bisect/`, unrun.

**Verified:** validation OK (230 graph nodes, 135 lockeys, 12 scenes, 138 spoken
lines, 138 voiced line files, 10 items, 7/7 notes read aloud), replaytest clean
and still failing on a broken guard, descpanel peak 1, negtest 104/104, shapes OK
(31 types), redscript 0 warnings 0 errors, `BUILD_EXIT=0`, quest block
`ash_cache_r19.questphase`, both locales carry the new UI text, `ps` clean.
Nothing deployed.

### D132 — A mod sector can carry its own geometry, and collision is authorable (2026-09-22)

The user built LocationStudio (`/mnt/sata/Cyberpunk2077/LocationStudio`), a CET
location editor with room kits, placed objects, volumes and declarative
authoring plans, and chose the **archive route**: author there, ship here. That
forced the question this entry answers, which is a bigger one than it looks.

**The reframe.** Every attempt at "go down into Cynosure" so far has meant
re-enabling CDPR's bunker — 381 quest-category sectors, `streamingBox ±FLT_MAX`,
each carrying a `questPrefabNodeRef`, and D116's crash is a main-thread
`WaitUntilLoaded` at world load. That fight may not be winnable at all. But this
mod already ships three of its own streaming sectors that have never crashed.
Nothing says one of them has to be above ground. The interior does not have to be
*theirs*.

**The finding that makes it possible.** `worldCollisionNode.compiledData` is not
a reference into a baked physics cache. It is a `CollisionBuffer` holding actors
and shapes in full: `WorldPosition` as `FixedPoint` (Bits / 131072 = metres,
checked — Bits -247428704 reads -1887.731, which lands in the Dogtown sector it
came from), a quaternion, and a list of `Box`/`Capsule`/`TriangleMesh`/
`ConvexMesh` shapes with half-extents, a preset and materials. WolvenKit
round-trips a vanilla one to **byte-identical JSON** (`json equal: True`). So
collision can be written, not just copied — which is the whole difference
between geometry the player looks at and geometry the player stands on.

**Two node kinds, and they are separate on purpose.** One Dogtown exterior sector
holds 464 static meshes and 17 collision nodes, and the collision ones carry no
mesh at all. A floor is therefore two entries in `source/world.json`: `meshes`
draws it, `collisions` holds the player up. Forgetting the second is not a subtle
bug, it is a hole in the world, so `validate.py` checks both halves and
`negtest.py` gained six cases (110/110).

**Every constant measured, none guessed.** `worldStaticMeshNode` ships Uk10 1040
/ Uk11 20610 in 226 of one sector's 406 static meshes — among them
`int_ent_industrial_a` trusses, the same kit this mod now builds with. `UkFloat1`
is not constant for a mesh: in six of eight distinct rows it equals the node's own
`forceAutoHideDistance` to the last decimal, so `node_instance` keeps the two
equal per node. `Uk14` is 1 on 464 of 464 meshes and 0 on every other kind
measured, which is why `UK1314` exists. Collision ships 1024/512 with
`MaxStreamingDistance` FLT_MAX across all 17 samples and all three LOD values;
ours writes `lod` 0, the value vanilla names `CriticalCollisionNode`. The shape
preset resolves exactly: FNV1a64("World Static") is 11199900243055890879.

**Geometry is anonymous, by construction.** A vanilla static mesh ships
`QuestPrefabRefHash` 0 and one sector pools 114 nodeRefs for 1648 nodes, so a
NodeRef is something a node opts into by being referenced. `gen_sector` gives a
mesh or a box none, which also keeps a wall out of the quest-prefab machinery —
the exact machinery D116 dies inside. That broke `dump_sectors.py`, which had
assumed `nodeRefs[i]` for every node; it now counts named nodes and checks
membership rather than position, which is what `gen_sector`'s own comment said
the pool was all along.

**Two things the tools corrected.** WolvenKit recomputes the cooked `num*` counts
on write: a single box at its actor's origin came back `numShapePositions` 0 and
`numShapeRotations` 0, not 1 and 1, because the format stores only non-default
positions and non-identity rotations — which is also why vanilla's three-shape
node says two rotations. The generator now emits what the format actually holds.
And `sectorHash` is the one number here that is a **guess**: it is per-sector
(identical across all 17 samples) but it is not FNV1a64 of any of the three depot
paths that sector could have had, under any of seven spellings.

**The probe.** `ac_probe_geometry` — a 4 m x 3 m industrial wall panel with a
matching box — stands at the landfill on `ac_landfill_body`'s coordinate, the one
point there anybody has stood on, so "nothing rendered" cannot be confused with
"it rendered inside a junk pile". Panel visible: meshes ship, and the whole
`int_ent_industrial_a` kit is available. Panel solid: collision ships and
Cynosure can be walked. Visible but walk-through: `sectorHash` is the first
suspect. Nothing at all: a mod sector will not carry geometry and the runtime
route is the only route. It comes out the moment it has answered.

**Verified:** validation OK (230 graph nodes, 6 sectors, 1 mesh, 1 collision,
24/26 positions stood on, 6 depot paths — the mesh path resolved against the
game's own archives), negtest 110/110, shapes OK, replaytest clean, `BUILD_EXIT=0`,
redscript 0 warnings 0 errors, `sectors OK (17 nodes defined, 0 problems)`, and
the PACKED sector reads back actor (1544.9994, -1981.8353, 75.3839) with half
extents 1.5 / 0.15 / 2.0. Nothing deployed.

## D133 — Farida's clinic dressing is baked, so the swap has to go through a Quest sector   (2026-09-24)

**Ask.** Replace the clinic's vanilla furniture with the FIA-aftermath dressing, but only
while this quest owns the room: Phantom Liberty's q304/q305 use the same room (D128).

**What the room is made of.** The clinic lives in `ep1\...\interior_-60_-78_0_0` and
`interior_-60_-77_0_0` (32 m interior grid, found through the ep1 `all.streamingblock`).
399 nodes sit inside the room box and about 385 are dressing, all from
`loc_q303_macs_clinic_deco_prefab`. Cooking flattened that prefab: **only 12 nodes keep a
NodeRef** (the `#q304_farida_*` props, `#q304_cyberdeck`, a few monitors). The
sector has no `variantNodes`. So neither `questTogglePrefabVariant` nor `questShowWorldNode`
can reach the other ~373 nodes. Vanilla has no switch for this dressing.

**Design.**
1. The 12 referenced nodes stay in place, so PL can still find them. Our graph hides
   them with `questShowWorldNode` during Act 2 and shows them again afterwards.
2. The rest move out. ArchiveXL `nodeDeletions` removes them, and the build writes copies into
   our own Quest-category sector. A phase holds that sector everywhere except the Act 2 window.
3. The FIA dressing is a second Quest sector, held only during Act 2.

**Probe first.** Every sector this mod has shipped is AlwaysLoaded. Nobody has shown that a
*mod-authored* Quest sector obeys a phase. `ash_cache_probe_qsector`:
- It holds one `delivery_crate_a` where V stood in the clinic.
- It carries `category: Quest` and `questPrefab: ac_pr_probe`, the same shape as vanilla
  `quest_009c7e2341620c3d`: a ±FLT_MAX box, and geometry keeps QuestPrefabRefHash 0.
- `probe_prefab_wait` → `probe_prefab_hold` (a `prefab_phase` node) is a looping branch
  off `start`, driven by the fact `ashcache_probe_prefab` that the tester types into CET.

    crate appears at 1, vanishes at 0   -> the design stands; build the swap
    crate never appears                 -> a mod Quest sector is not phase-streamed;
                                           fall back to runtime hiding
    crate is there before the fact is set -> category/ref ignored, sector streamed anyway

`gen_sector.py` now reads `category`/`questPrefab` per sector. `validate.py` treats a
`questPrefab` as a defined NodeRef and rejects it on anything other than a Quest sector.

**Result (2026-09-24).** Negative. With the player inside the room and
`GetFactStr("ashcache_probe_prefab")` printing 1, no crate. The probe branch hangs off `start`, and
`start` was shown to fire on that save, so a mod-authored Quest sector is simply not streamed by
our `prefab_phase`. The swap is dropped, and D134 takes over.

## D134 — the clinic furniture is hidden at runtime, by refs we give it   (2026-09-24)

**Mechanism.** It uses two Codeware pieces, both of which are already used in the game's installed mods.
- `worldStreamingSector.GetNodeSetup(i).SetNodeRef(...)` in a `Resource/Ready` callback gives
  the flattened dressing NodeRefs of ours as each sector loads. DeceptiousBugFixes does exactly this.
- `WorldStateSystem.ToggleNode(ref, bool)` then hides and shows those setups. The 12 nodes that
  vanilla already references (`#q304_*`, the monitors) are toggled by their own vanilla paths
  and are never re-tagged.

**What is hidden.** `tools/clinic_hide_scan.py` writes `reference/clinic_hide.json`: 347 node
*setups* (312 in `-78`, 35 in `-77`) inside D133's room box. Architecture, lights, decals,
occluders and the ambient sound stay.
- Indexes are **setup** indexes, the unit `GetNodeSetup` takes. The old `wk_scratch/clinic/nodes.tsv`
  was in node space and would have tagged the wrong setups.
- Instanced meshes have one setup per copy, so a copy standing outside the room is never touched.
- At runtime a sector is refused whole, with an `FTLogWarning` naming it, if its setup count
  or any setup's class differs from the scan.

**Window.** `glue.json` `hide.ac_clinic` sets it to `ashcache_progress` 2..6. The room is
already stripped the first time V walks in, and `progress_7` (which every ending passes)
gives it back.
- A persistent `m_hidden_ac_clinic` means the glue only ever re-shows what it hid.
- All of it sits behind `@if(ModuleExists("Codeware"))`. Without Codeware the room simply stays vanilla.
- `lint_glue.sh` pass 2 type-checks that branch; a planted `ToggleNodeX` fails it.

**Probe removed.** Gone: the D133 sector, `probe_prefab_wait/hold` and `ashcache_probe_prefab`.
`phase_revision` 19 → 20, because saves that ran r19 hold `probe_prefab_wait` active.
`gen_sector.py` now also deletes build JSON for sectors that world.json no longer names. The
probe sector had been packed once more after its removal.

**Open.** It is not yet known whether a `ToggleNode` state survives the sector streaming out and back in.
The in-game test is to leave the clinic for more than 200 m during the window and come back.
The FIA dressing itself is still only the LocationStudio plan
(`research/locationstudio/clinic_dressing.plan.json`); it will ship as glue props gated on the same window.

## D135 — ToggleNode is never called from a fact listener (2026-09-24)

**Symptom.** The game froze at the step to "courier room searched" (progress 2), the
moment the D134 hide window opens. The engine watchdog killed it 120 s later
(`red4ext` log: `engineWatchdog.cpp:198 Watchdog timeout`).

**Evidence.** The CrashLogger minidump, read with `diag/dmp_scan.py`: the main thread
sits in a message wait. Worker thread 524 shows the script VM, then Codeware.dll+0xE9800
(a native wrapper taking `(NodeRef, Bool)`, i.e. `WorldStateSystem.ToggleNode`), then a
kernel wait. Quest-fact listeners run on the quest system's job thread, and ToggleNode
called there deadlocks against the main thread.

**Fix.** `SyncHide_*` only schedules an `AshCacheHideCallback` (DelaySystem, 0.1 s). The
toggle happens in `OnHideApply` → `ApplyHide_*`, the way INCF-CORE defers its own
ToggleNode. The logic is unchanged: the same window, and the same persistent `m_hidden_*`.

## D136 — clinic hide missed every worldInstancedMeshNode (2026-09-24)

In game after D135 the clinic was only partly empty. Live raycast + player pos (cp77wb) put the
player inside BOX looking at dressing that was not in the list: `worldInstancedMeshNode` setups have
Position 0,0,0 (copies live in a shared transform buffer), so the BOX test dropped all of them.
`clinic_hide_scan.py` now tests those by `buffer.Unknown1[0]` (the bbox of all copies) against BOX
+1.5 m, since hiding the setup hides every copy. Also: surgery/lab lamp meshes hidden (no lights in
them), ducts/wall vents kept. 78: 312 -> 382, 77: 35 -> 63.

## D137 — Clinic dressing deleted for good by ArchiveXL (2026-09-24)

In game after D136: `ToggleNode` hid plain meshes but left their collision (you
walk into an invisible surgical chair), and `worldInstancedMeshNode` setups ignored
it entirely (office chair, tables, shelves stayed). User chose a permanent empty
room: the clinic is only a shell, and Cynosure's interior is built from scratch.

- `tools/gen_xl.py` emits `streaming: sectors: nodeDeletions` from the scan's
  `delete` lists (-78: 415, -77: 63). ArchiveXL (src/App/Extensions/WorldStreaming/
  Extension.cpp) checks `expectedNodes` = setup count and each node's type, and skips
  the whole sector on any mismatch, so a stale scan leaves the room vanilla. `index`
  is the SETUP index. Static meshes are scaled to 0, instanced mesh copies scaled to
  0, other nodes moved to Z -2000 and swapped for a dummy node; the setup count is
  unchanged, so the Codeware tag check (570/80) still holds.
- Setups with `QuestPrefabRefHash != 0` (q304: Farida's tools, the cyberdeck and
  monitors, 12) are NOT deleted, since q304 may still need them. They stay on the D134
  runtime hide during progress 2–6.
- BOX west edge -1916.5 → -1919.5: the sink, IV stand, fridges and medical rack were past it.
- No `worldCollisionNode` exists in any EP1 sector covering the clinic (checked all
  167 non-quest sectors whose streaming box contains it). Whether scale-0 deletion
  removes these meshes' collision is **unverified until tested in game**.

## D138 — Clinic collision deleted separately (2026-09-24)

In game after D137, the dressing was gone but still solid. Collision lives in `worldCollisionNode`
actors in the sectors Phantom Liberty overrides at the BASE path `_compiled\default\`
(not `ep1\`): `interior_-15_-20_0_2` (almost all of it) and `exterior_-15_-20_0_1`.
D137's "no collision node in EP1" was wrong: I had searched the `ep1\` copies only.
- `tools/clinic_collision_scan.py` matches each actor inside BOX, by position (< 0.3 m),
  to the nearest clinic setup or instanced copy. Instance transforms: `worldTransformsBuffer` =
  world translation; destructible `cookedInstanceTransforms` = local offset rotated by the setup.
  Only actors whose owner is deleted go: 404 + 2. Floor, walls and vents (139 + 22) stay.
- gen_xl emits them as `nodeDeletions` of type `worldCollisionNode` with `expectedActors` +
  `actorDeletions` (ArchiveXL Config.cpp:144).
- The desk lamps were added to HIDE_ANYWAY: they were kept as "lighting".
- The ArchiveXL log of 2026-09-24 19:01 confirms D137 applied to -78 and -77 ("All patches
  have been applied").

## D139 — q304's props are deleted too (2026-09-24)

In game after D138 the furniture and its collision were gone, but the 12 setups kept
for q304 (`QuestPrefabRefHash != 0`: wall monitors, Farida's tools, the cyberdeck)
were still drawn while this quest owned the room, the tools floating where their
tables had been: the D134 runtime hide did not hide them. The user chose an empty
room (D137), so `clinic_hide_scan.py` now sends them to `delete` as well; the `hide`
lists are empty and the runtime hide toggles nothing. Cost: Phantom Liberty's
q304/q305 lose that dressing in this room, and a q304 scene that uses one of the
tools may play without it. The -78 sector now deletes 429 setups (was 417).

## D140 — the CAUTION signs go too; the other leftovers are not vanilla dressing (2026-09-24)
After D139 the user still saw signs, a laptop, a shard and a camo case. Every setup of the
two clinic sectors inside the box is now either deleted or architecture, so of those only
the signs came from them: `industrial_lettering_caution` decals, kept by the decal rule.
They are now deleted via `HIDE_ANYWAY` (431 deletions in -78). The laptop is our own
`ac_terminal_pc` (computer_1, z 25.56), which floats because its workbench is gone; it
is repositioned when the interior is rebuilt. The shard and the case are in neither
sector and still need a RedHotTools inspection to find their source.

## D141 — Farida's laptop, faceplate shard case and shop sign go too (2026-09-24)

Both are q303/q304 entities in `ep1\exterior_-30_-39_0_0` (setups 1065, 1069), a sector
the box scan never read. They floated on the wall once their tables were deleted. That
sector also holds the clinic's lights, fog, doors and intercom, so it is not box-scanned:
`clinic_hide_scan.py` deletes only the names in `NAMED` from it. The sector was extracted
to `/mnt/sata/Cyberpunk2077/game_extract/` (json in `game_extract/json/`).

## D142 — the blank CAUTION plates go too (2026-09-24)

With the CAUTION decals gone (D140), their backing plates showed as two dark squares by
the entrance: `int_common_techpanel_a_floor_l200_w200_a`, instanced setup 499 of
`interior_-60_-78_0_0`, exactly two copies. It lives under `\architecture\`, so the scan
keeps it; `FORCE` deletes that one setup. The floor walkway techpanels are untouched.

## D143 — empty clinic for the redesign (2026-09-24)

The user is redesigning the clinic, so the mod's own dressing is off too: `ac_terminal_pc`
is `disabled` in world.json and the glue's `ac_case` is moved to `glue.json`
`_parked_props`. Both are scenery; the Use prompts sit on the `#ac_terminal_origin` and
`#ac_box_origin` markers, which stay. The LocationStudio scene "Ash Cache Clinic - FIA
aftermath" is deactivated, not deleted. Restore: drop the `disabled` key, move `ac_case`
back into `props`, re-activate the scene. Backups `*.bak-2026-09-24-cleanroom`.

## D144 — Faceplate jar removed (2026-09-24)
The lit jar on the clinic wall (`faceplate_tank`, exterior_-30_-39_0_0 setup 1229) plus its five
`{L_Face_Jar_*}` lights (94-98) and nitrogen fog particles (1032, 1034) join the D141 NAMED list.
Its collision, exterior_-15_-20_0_1 node 94 actor 10 (RHT: NormalCollisionNode_376), was added by hand
to clinic_collision.json: a full rescan would drop node 96 [26,30], because the exterior sector's kept
setups now count as nearer owners.

## D145 — Clinic redesign keeps the bench and the terminal counter (2026-09-25)

The GPT 5.6 clinic design (wk_scratch/clinic_design) builds the procedure island around the
verified ac_case pose. The hide pass had removed the bench that pose was measured on
(interior_-60_-78 setup 531: two instanced industrial_table_f, top z 24.856) and the counter
under ac_terminal_pc (interior_-60_-77 setup 22: industrial_table_i). Both are now kept
(clinic_hide_scan.py KEEP_I), along with their three collision actors
(interior_-15_-20_0_2 node 43 actors 22, 23; node 59 actor 48). The collision list was
edited by hand, not rescanned: a full rescan still drops exterior_-15_-20_0_1 node 96 [26,30] (D144).

## D146 — One central procedure table instead of Farida's bench (2026-09-25)

User: the kept bench (D145, two industrial_table_f) is wrong; one big table in the centre, as in the
GPT 5.6 design. Setup 531 is hidden again (the terminal counter, 22, stays kept). The table is vanilla
morgue_table_a.mesh wrapped in mod\ash_cache\props\clinic\ac_procedure_table.ent by the new
tools/gen_mesh_ent.py (mesh + one box collider from the mesh bounds, from the q005 case template).
Pose in world.json ac_procedure_table (disabled; pose authority), drawn by glue prop ac_clinic_table
while ashcache_progress is 2..6. Yaw -50.2 (the case's), centre shifted 0.45 m away from ac_mara:
nearest corner 1.57 m from her. Top 24.849 under the case at 24.87. Not yet seen in game.

## D147 — Table and case moved to the clinic centre, under the big ceiling lamp (2026-09-25)

User: move table and case to the centre. The first try used the room centre from 16 wall raycasts
(-1909.00, -2468.71); the user corrected it: the centre is where the big lamp hangs. That lamp is
exterior_-30_-39 node 1213 (entropy_ceiling_bar_lamp, light {L_Chair_Ceiling}) at -1910.87 -2466.22,
over where Farida's chair stood, and it is also the centre of the round floor grate (edge 2.0-2.1 m
all round by live raycasts). ac_splinter_box / ac_box_origin now there at z 24.898, yaw -135 (latches
toward the entrance); ac_splinter_case 1.2 m in front; ac_procedure_table under them, long side across
the room. Confirmed by screenshot (shots/ls/20260925-013357-lamp1.png). ac_mara is unchanged and now
7.4 m from the table - her scene needs a replay in the new room.

## D148 — Solid mesh props; Mara beside the table (2026-09-25)

The table was walk-through: gen_mesh_ent.py had kept the case template's "Interaction Object"
colliders, which only answer interaction rays. Colliders now get vanilla's "Device solid visible"
filter (copied from ma_wbr_hil_05_fluff_dead_body_01.ent); a live ray stops at the table face in the
PlayerBlocker group. ac_mara moved next to the table as in the design (-1909.49 -2465.12, yaw 164.8,
facing V's case spot); old pose kept as _previous. User confirmed in game after a save/load: table
solid, case "open" prompt back. A running quest scene keeps the origin it started with, so moving
its marker needs a save/load before the prompt follows. Mara's new spot not yet seen in her scene.

## D149 / D150 — Case faces the entrance; foam insert with a cradle for the splinter (2026-09-25)

D149: at yaw -135 the case's lid opened on the entrance side and hid the tray; ac_splinter_box and
ac_box_origin are now yaw 45 (lid opens away from V).
D150: user - too much empty space in the opened case; the Relic (q005) case holds its chip in a
place made for it. tools/ash_case/bl_insert.py builds ash_case_insert.mesh from boxes in the case
frame: dark foam bed (ash_case_interior, already shipped) filling the tray 3.2 cm below the rim, a
raised gunmetal cradle (new ash_case_cradle, flat 64px textures) in the centre with a
splinter-shaped pocket; gen_case_ent.py <dims> <out> <insert.json> adds it to the opened .ent and
rests the splinter in the pocket (z = pocket floor + 0.5 mm). Screenshot shots/ls/20260925-015831-insert1.png.
D150b-d (same day): cradle textures brushed steel (168,172,178 / r 80 / m 240); a 3 mm emissive
strip (ash_case_glow, cyan 90,225,255 EV 3 on metal_base, as vanilla military_case_k) rims the
pocket (mkmesh.py EMISSIVE); the opened case's light softened from 55 lm pure red 8 cm over the
tray to 18 lm (255,60,45) 15 cm over it (gen_case_ent.py LIGHT_*). shots/ls/light1_crop.png.
D150e: glow edge base colour (0,110,130), emission (0,200,255) EV 5 - reads cyan (shots/ls/cyan1_crop.png).

## D151–D154 — Clinic dressing pipeline and the design's room (2026-09-25, overnight, autonomous)

D151: dressing is data - source/clinic_dressing.json -> tools/clinic_dressing.py. Each item names a
vanilla mesh (+ extra meshes sharing its pivot), the surface it stands on, x/y (or a footprint
centre with "center": true) and yaw; the tool extracts the mesh, wraps it solid (gen_mesh_ent.py),
lifts it by its own bounds onto the surface, and writes a disabled world.json pose + a glue prop
drawn while ashcache_progress is 2..6. Entries it owns carry "_dressing": true. dev/hotcycle.py
runs one hot deploy + respawn + screenshot cycle against the running game.
D152: the terminal's visible part is now the dressing prop ac_dress_monitor (PL old_monitor_4_3 +
its lit display, on the counter, screen to the room). computer_1.ent (ac_terminal_pc) is disabled
again: its angle_15 look is a stand-less panel that floated 0.4 m over the counter, screen to the
wall. The terminal prompt is the scene hub on #ac_terminal_origin and never depended on it.
D153: room frame for placement (u toward the terminal wall, v door -> far wall, origin -1908.0
-2469.5) from a 0.25 m grid of live downward raycasts. Dressing: diagnostic unit + folder on the
counter, stool, two military instrument trolleys in the left lane, military supply cart back-left,
low lab cabinet on the right wall (1.7 m from ac_mara), IV stand at the table's left end, bin past
the counter. Walkway door -> table, Mara's bubble, case approach and terminal spot kept clear.
D154: two accent lights (tools/gen_light_ent.py, the case template's light alone): terminal cyan
90 lm 0.7 m in front of the monitor; Mara face fill warm-neutral 70 lm 0.9 m in front of her.
Screenshots: shots/ls/20260925-025956-lights_entry.png (from the inner door),
20260925-025339-room_back2.png, 20260925-025944-lights_term.png.
D155: the clinic was still near-empty (10 props in a 7.3 x 14.6 m room; user feedback 2026-09-25).
Room re-measured with horizontal live raycasts (dev/roommap.py): walls run 2.4 deg off the D153
frame; left wall past v 1.2 is Farida's recessed sink unit (kept), right wall has pillars at v -2.5
and 3.5. clinic_dressing.py gained room placement: "room" [u,v], "face", "front" (mesh-local front
axis), "against" (back flush to a fitted wall line), "on" (stack on an earlier item), and a
one-regex-per-archive mesh prefetch (was minutes per mesh). Added 20 items: tall military lab
cabinet + open empty wall medkit + utility box (left wall), wheelchair (left lane), packed boxes and
a crate in the door-left corner, scrub sink and an unbolted ripperdoc-chair base by the entry
(right), stripped recovery bed (right wall), far wall: bench with tray + small unit, half-empty
shelf with a foam box, open empty implant freezer, unplugged medical unit, cold 160 lm practical
over them; folded sterile cloth at the procedure table's left end; standing exam lamp. 33 dressing
items total. Screenshots: shots/ls/20260925-130809-d6_dl.png, 130833-d6_fr.png, 130757-d6_far.png.

## D156 — Mara's room, the entry hall, the walkway fix (2026-09-25 afternoon)

User feedback (16:05): a prop at the entrance blocks the walk, Mara needs her room, the entry hall
past the white street door needs clothes storage, the clinic still reads empty, the case's map pin
sits in the wrong place, no terminal prompt.
- Chair base (ac_dress_chair_base) stood at u 1.15 in the walkway: now against the right wall, v -3.05.
- Map pin: live `GetQuestMappinPositionsByObjective` returns -1908.11 -2471.92 - the PRE-D148 marker.
  The built sector is right (dump_sectors: #ac_splinter_case -1910.02 -2467.07); the session loaded
  the clinic sector before the case moved and hot archive reload does not re-read it. Fix = save/load.
  The white "?" pin 35-70 m off along +v is not ours.
- Terminal prompt: by design only in ac_ph3_truth (after the case and Mara); not a bug.
- Side room left of the table (u -6.5..-3.6, v 1.3..8.9, door gap v 3.9..6.0 in its inner wall) is
  Mara's room: mattress + duvet + pillow, dropped jacket, duffel, locker + folded clothes, table with
  laptop / desk lamp / mug / noodle cup / can, office chair, towel by the tap, 260 lm warm light.
- Entry hall (u -2.4..2.1, v -6.3..-10.9): four steel lockers on the right wall with clothes on top,
  three hanging garments + a bag on the left wall, 90 lm cold light. Path street door -> glass door kept.
- Main room: lane cart, far cart, second IV stand, device on the bed, second lab cabinet, floor
  dressing packages, instrument tray, bench lamp + trauma pack. 72 dressing items total.
- Walls measured with dev/roommap/walls.py (horizontal static rays); WALLS gained mara_* / hall_*.
- clinic_dressing.py: an .ent is only rebuilt when its generator args change (stamps in
  game_extract/dress_stamps) - a full rebuild was ~20 min; lights may be placed by "room".

## D157 — Tidy clinic pass; world prompts need V to face the prop (2026-09-25)
User feedback: floating coats/towel, packages standing upright, "too chaotic", Mara's room dark,
case prompt showing while facing away. Removed pkg_1..4, box_c, Mara's towel/jacket/can, the three
hanging coats (no hook mesh; clothes_hanging_* hang from their own origin in mid-air). All yaw_add
zeroed except Mara's chair, so every prop sits square to its wall. Added low industrial_shelf_h
units with folded clothes on top: two on the entry-hall left wall, one in Mara's room where the
towel was. A shelf by the glass door was dropped: the sink runs to the door wall there. Mara's room
light 260 -> 700 lm, radius 6. Lower shelf levels stay empty: the prop collider is a box, so their
heights can't be raycast. gen_scene.py: attachToWorld hubs now use activationYawLimit 60 (was vanilla
4162's 200, which let the list pop up 1.8 m from the case while V faced the far bench); box/chip
range 2 -> 1.5. Scene changes apply when the scene node restarts (load a save).

## D158 — Hub approach wedge, terminal in parallel, wall dressing (2026-09-25)

- `activationYawLimit` is a wedge of APPROACH directions around the hub entity's forward (+Y), not
  V's view cone. With identity `entityOrientation` the hub inherits the scene marker's yaw 45, whose
  forward is +v (the far wall), so the case prompt fired only from BEHIND the case. `attachToWorld`
  now takes `yaw` (relative to the marker): box/chip 180 (door side), terminal 90 (-u, the room);
  wedge 120°. gen_scene.py `_yaw_quat`.
- Terminal no longer waits for Mara: `desc_find_box` forks `obj_terminal_on` (Active socket), the
  main walk joins at the new `wait_terminal` (pause_fact ashcache_terminal_read) before progress_5.
  Node appended at the array end; phase_revision 21 so a save parked at take_chip re-walks and
  starts the terminal branch. replaytest OK.
- Dressing: removed floor tray, foam box (clipped the shelf leg), unbolted chair base, bench drawer
  unit; trauma pack moved off the shelf upright. Added wall shelf over the bench (+3 containers),
  hook rail with two aprons on the left wall, wall shelf over the recovery bed (+3 items), glove
  dispenser. 78 items.

## D159 — stale .xl hid the whole phase; bench/apron/shelf fixes (2026-09-25)
- After the r21 reload every prompt of the phase was gone (journal: ac_obj_terminal Inactive, splinter not given).
  Cause: hotcycle hot-loaded only ashcache.archive; the game folder kept the r20 .xl, which names
  `ash_cache_r20.questphase` - a file the new archive no longer holds, so ArchiveXL injected nothing.
  hotcycle.push_archive now deploys (with backup) and hot-loads the .xl whenever it differs. The phase
  injection still only happens on a save load.
- lab_table_c's bounds top is 25.336 but its raycast top is 25.24: bench items use surface 25.24; the trauma
  pack's bounds reach a strap 0.096 below its base, so its surface is 25.144.
- Aprons: bounds centre u -3.21, top at rack-local z ~1.6 (hook tips). industrial_shelf_c moved to u -2.6
  (it touched the left glass). medical_cart_c (cart_far) removed: it blocked the table -> left-wall lane.

## D160 — Clinic collisions found by footprint check, not by eye (2026-09-25 evening)

`dev/roommap/overlap.py` intersects the rotated bounds footprint of every generated prop, reading the
positions from the gen log. Static raycasts measured the vanilla geometry the props must clear.
- Supply cart (medical_cart_d) stood in Mara's side-room doorway (gap v 3.9..6.0). Removed.
- lab_set_a_locker_b overlapped lab_set_a_locker_a by 0.74 m on the right wall. Removed.
- Shelf and bench overlapped by 5 cm. The glass is at u -3.33, so the bench and everything on it moved
  +0.12 u, and the shelf moved to u -2.64.
- The right wall has a pillar at v -3.45..-2.46 whose face is at u 2.84. The sink ended 0.38 m inside
  it; the sink is now centred at v -4.75, spanning -5.98..-3.52. The glove dispenser was on the wall
  behind the pillar, so it now sits on the pillar face (room 2.77, -2.95).
- Freezer door mesh dropped: gen_mesh_ent puts "extra" meshes on the body's pivot, so the door stood
  half in the floor beside the freezer. Any hinged extra needs its own offset; there is none yet.
Respawn tags are `ashcache_<id>`, not the bare id. A bare tag deletes nothing, and the old prop stays.
Verified live: shots/ls/20260925-1949*-v86/v88/v89, 20260925-195021-v87.

## D161 — bench items on the real (stepped) top; Mara's lipsync rebuilt (2026-09-25)
- lab_table_c's collision is one flat box at 25.24, but its visible top is stepped (mesh raster:
  u<-1.225 at 1.18, u -1.225..-0.525 at 1.10, u>-0.525 at 1.12 above the 24.056 floor). The tray
  straddled the 8 cm step and hung in the air: moved to u -1.56 on the high block. The lamp sat 14 cm
  past the bench's end: now u 0.22, surface 25.176. The pack's base now sits at 25.176.
  Raycasts see the collision box, not the mesh. For surfaces, rasterise the uncooked glb
  (`uncook --mesh-export-type MeshOnly`).
- Mara lost lipsync after the first choice: `lipsync/en-us/mara.anims` dated from 2026-09-16 and was
  never regenerated after the D121 scene rewrite. 17 current ids had no take, including every
  post-choice Mara reply. Reran `tools/gen_lipsync.py`: 25 takes, which is every Mara line. The other
  10 `mara.*` ids are V's lines. gen_lipsync is not part of build.sh, so rerun it after any
  change to Mara's lines.

## D162 — trauma pack clear of the bench step (2026-09-25)
The pack is 0.445 m long along u. At u -0.38 it hung 8 cm over the step down to the lower diamond-plate block (u -0.525). Moved to u -0.26, 4 cm clear; verified `shots/ls/20260925-204056-v91.png`. Rule: check a prop's full footprint (bounds) against the D161 step lines, not just its centre. D161 lipsync rebuild confirmed by the user in game.
- Correction, same day: the pack was never floating; it sat 10 cm *inside* the bench. The D159 note said a "strap" hung 0.096 below the base. That was wrong: 773 vertices across the full 44x34 cm footprint make up the case floor itself. New `dev/roommap/benchfit.py` places the uncooked glbs at the gen-log poses, fills in the bench's top triangles and reports each prop's gap and unsupported contact points. Now: pack +0.002, tray +0.001, lamp +0.001, 0 unsupported points each. Surfaces are 25.18 / 25.241 / 25.18. Verified in `shots/ls/20260925-205327-v92.png` and `-205357-v92tray.png`. Rule: never read a surface offset off the bounds box and a guess; run benchfit.py after moving any bench prop.

## D163 — every raised prop checked against real surfaces (2026-09-25)
- New `dev/roommap/fitcheck.py` generalises benchfit.py. It places every dressing glb, plus the glue-drawn procedure table (morgue_table_a + _top_a), at the newest gen-log pose and rasterises all near-horizontal faces. For each raised prop it reports the supporting item, the gap range and the unsupported contact points. `--live id,...` despawns those props, raycasts collision under their corners and centre, then respawns them.
- Collision often differs from the mesh: the bed is a box at its head-section height, and the cardboard boxes are bounds boxes. Trust the mesh check; use `--live` only where no mesh is available (vanilla terminal counter; poor_wall_shelf_01_a, whose uncook fails in DirectXTexNet).
- Fixed:
  - bed device: hung 25 cm past the bed's edge and sat 5 cm up, at the head-section height. Now centred on the pad at room (2.875, -1.05), dz -0.048.
  - box_b: B is 2 cm larger than A and was off-centre. Now centred, dz -0.012.
  - pillow: dz -0.019.
  - mara_top_1: dz -0.013.
  - far-shelf items: dz -0.007.
  - table cloth: floated 2.5 cm; surface now 24.875.
  - folder: moved 5 cm clear of the monitor's foot, which stood 1 cm inside it.
- Now all within about 4 mm. Still flagged: wall-hung items (by design); terminal-counter and bed-shelf items (flush by live raycast); box_b and duvet (they touch at their lowest point on uneven cardboard or mattress tops).
- clinic_dressing.py: new optional `"dz"` item key, added to the surface.
- Shots: `shots/ls/20260925-211054-d163bed.png`, `-211244-d163folder2.png`.

## D164 — wall-hung props set against the real walls (2026-09-25)
- `fitcheck.py --wall id,...` casts Static-only rays (walls; the Dynamic glue props are ignored) from the prop's centre in the four room directions at 25/50/75 % of its height. It reports the gap between the prop's mesh extent and the nearest wall. With no glb available it uses the bounds box.
- The "against" wall lines (roommap) were off by up to 3.4 cm. Before → after:

  | Prop | Before | After |
  |---|---|---|
  | sink | 3.4 cm inside the wall | +2 mm |
  | far shelf | 2.7 cm inside | +3 mm |
  | apron rail | 4 mm inside | +4 mm |
  | first-aid box | 9 mm off | +2 mm |
  | fuse box | 7 mm off | +2 mm |
  | glove dispenser | 2.1 cm off (moved 1.9 cm) | +3 mm |
  | bed shelf | already -4 mm | unchanged |

- New optional item key `"wall_gap"` (default 0.015) in clinic_dressing.py.
- The far-shelf items are still supported (+1 mm).
- overlap.py (gen11) leaves only expected bounds overlaps:
  - bed/device, bench/lamp/pack: the mesh check shows these seated correctly.
  - aprons on the rail: they hang from it.
  - Mara's chair tucked under her desk: no clipping.
- Shots: `shots/ls/20260925-212145-d164chair.png`, `-212157-d164apron.png`.

## D165 — Aprons hang on the rack's J-hooks (2026-09-25)
The aprons (D158) hung in the air: between hooks, 3–5 cm proud of them and 14 cm too high. wall_rack_a has two hook rows: upper diagonal rods (x = 0, ±0.15 … ±0.6) and lower J-hooks (x = ±0.075 … ±0.525, bar top z 1.459, trough at y 0.10). wall_rack_apron_a's origin is its strap-loop top. Both aprons now use `pos`/`yaw` (rack yaw −47.4) at rack-local (±0.375, 0.10) with origin z = rack z + 1.455 (`surface` 24.162). Checked in game: `shots/ls/20260925-213553-d165apron.png`.

## D166 — the "glove dispenser" was a loose hanging glove (2026-09-25)
`wall_rack_glove_a` is a single glove draped over a hook, made for `wall_rack_a`, not a dispenser. On the pillar (D158/D160/D164) it read as a severed hand sticking out of the wall. It is now on the apron rack's free lower J-hook: rack-local x +0.075, y 0.095. The glove origin sits inside the fold, so it goes at the bar centre (1.452 above the rack origin) → pos -1915.345 -2466.769, z 25.506, yaw -47.4 (the rack's). Verified in game: `shots/ls/20260925-214831-d166glove3.png`.
Gotcha: a pose change lives in AshCacheGlue.reds, so `hotcycle.py --no-script` respawns the OLD pose.

## D167 — floor props vs furniture and walls (2026-09-25)
New `dev/roommap/clipcheck.py` samples every placed glb at 2 cm and flags pairs (at least one on the floor) whose per-cell z intervals overlap by more than 2 cm. Result: 0 pairs among the dressing props and the procedure table. At a 3 mm threshold it catches only the known cases (bed device 4 mm into the mattress, box_b 1.2 cm into box_a), which shows it is sensitive.
Against static collision (`fitcheck.py --wall` on the 31 floor props), everything was within ±1.1 cm except Mara's table (back 2.7 cm inside the wall) and Mara's shelf (2.0 cm). Their `against` placement uses the bounds box, which underestimates the back. Fixed with `wall_gap` 0.047 and 0.040; both are now 5 and 4 mm off the wall, and their items are still supported (+0..1 mm).

## D168 — Mara's room clipping (2026-09-25)
- **Props vs props:** clipcheck over every pair of Mara's-room props at a 1 cm threshold found 0 overlaps.
- **Props vs walls:** the mattress was 0.6 cm and the duvet 1.1 cm inside the outer wall; every other prop is 4 mm to 45 cm clear.
- **Missed by rays:** the screenshot showed what rays missed. A vanilla wall pipe stub (face u -6.04, v 6.63-6.78) came down through the foot of the duvet. Its collision ends at z 24.55, but the visible mesh reaches lower.
- **Fix:** sliding the bed along the wall had only 19 cm and was not enough. So the mattress and duvet now have `wall_gap` 0.421 (the bed stands 40 cm off the wall), room v 7.77, and the pillow u -5.36. The pipe is now beside the foot of the bed (`shots/ls/20260925-221601-d168mara4.png`). Duvet and pillow support are unchanged; clipcheck is still clean.
- **Lesson:** Static-ray wall checks from a prop's centre cannot see thin vanilla fixtures such as pipes, conduits or ledges. Check the screenshot.

## D169 — thin vanilla fixtures vs props, all rooms (2026-09-25)
New `dev/roommap/fixturecheck.py`, which is live. Every 5 cm cell of each prop's real footprint gets a Static-only down ray and an up ray (props are Dynamic, so the prop never hits itself). A Static hit between the prop bottom and top + MARGIN is a fixture in the prop.
MARGIN is 0.25. Fixture meshes reach past their collision: the D168 pipe's collision bottom (24.545, a round 6 cm radius cap at u -6.11 v 6.71) sat 10-20 cm over the sagging duvet edge the pipe visibly entered.
Calibration: at the D168 pose it flags the duvet (u -6.15 v 6.72); at the current pose it reports clear.
Result: all 70 props clear (`dev/roommap/fixture1.log`). Limit: a fixture with no collision at all is invisible to rays, so screenshots are still the backstop.

## D170 — screenshot pass, all rooms (2026-09-25)
This is the visual backstop to D169, for fixtures with no collision. Views were taken with `hotcycle.py --no-script --no-archive --view=...`, and nothing was changed.
- **Clinic** (`s_c_*`): four corners, the entry and the back view, plus two retakes of the door corner (`s_c_dl2` -1908.21 -2471.83 yaw -148, `s_c_dl3` -1904.82 -2471.97 yaw 144).
- **Hall** (`s_h_*`): four views.
- **Mara's room** (`s_m_*`): `s_m_1`, `s_m_bed`, `s_m_chair` and `s_m_door`, plus two shots along the room's long v axis: `s_m_far` (-1915.78 -2468.09 yaw -135) and `s_m_diag` (-1912.95 -2470.21 yaw 63.4).
- **Result:** no prop clips into a fixture or another prop. The bed is clear of the D168 pipe. Shots are in `shots/ls/20260925-2309*` through `-2316*`.
- **Gotchas:**
  - `view` teleports to z 24.1 and settles on whatever is there. At `d4_dl` (-1906.59 -2475.16) the player landed on solid geometry 0.87 m up (u < -2.5 is solid there), so the shot was useless. Probe the floor first with a Static+Dynamic down ray; a hit of 26.5 means the spot is inside a solid.
  - Mara's room is long and narrow along v, so views aimed along ±u hit a wall 1.5 m away (`s_m_3`) or look out into the clinic (`s_m_3r`).

## D171 — Mara idles in a vanilla workspot instead of standing like a statue (2026-09-25)
- **Problem:** the scene spawns Mara from `q306_fia_agent_corpo_scene_wa` and only drives her face (emotions, lipsync). Nothing drives her body, so she stood in a bind pose, arms straight down, for the whole meeting (`shots/ls/20260925-234556-mara_anim_0_static.png`).
- **Picked in game:** a stand-in from `Character.ashcache_mara` was spawned at `#ac_mara` and candidates were played on her with LocationStudio's new `npc_play_animation`, which uses AMM's catalog and AMM's own WorkspotSystem calls.
  - Tablet idles were rejected, because AMM attaches no prop and the empty hand reads as rubbing her face.
  - Arms crossed was chosen: guarded and watchful, right for an ex-FIA agent (`…234704-mara_anim_2_arms.png`).
- **Shipped without AMM:** the vanilla `base\workspots\common\ground\generic__stand_ground_arms_crossed__stand_around__02.workspot`, a stand-around loop with its own variations.
- **Mechanism:** `gen_scene.py` has a new scene node type, `workspot` (`actor`, `workspot`), copied from q005_07 (Jackie, node 2603):
  - a `scnWorkspotData_ExternalWorkspotResource`;
  - a `scnWorkspotInstance`, with id equal to the node id, a Global marker at the actor's `characters.json` marker (long NodeRef form) and an identity transform;
  - a `scnQuestNode` wrapping `questUseWorkspotNodeDefinition` with `scnUseSceneWorkspotParamsV1`, infinite and instant, with no output links. The actor is addressed by `entityReference.names = [actorName]`, as q001_00cd does for its community-spawned `boss`; our actor has no world NodeRef.
- **Wiring:** `scene_mara.json` and `scene_aftertalk.json` each gain a `mara_idle` node, linked from every start node. The holocall is voice-only, so gen_scene refuses a workspot node there. Scenes only; no questphase change, so no phase_revision bump.
- **Status:** build green (build19), archive hot-loaded. **Not yet seen in a running meeting.** The open question is whether `names` alone resolves a scene-spawned actor. If it doesn't, fall back to `playAtActorLocation`, or to a performer-bound reference.
- **Tooling:** LocationStudio (source tree, installed with `.bak-2026-09-25-lsinstall` backups) gained `modules/live_tools.lua` and these tools:
  - `npc_animations_search`, `npc_play_animation`, `npc_stop_animation`, `npc_animation_status`, `npc_list_nearby`, `npc_spawn_record`, `npc_despawn_tag`;
  - `capture_views` (with a floor probe), `floor_probe`, `raycast_batch`, `respawn_tagged`.
  - They replace `dev/hotcycle.py --view/--respawn` and the ad-hoc raycast Lua.
- **Fixed on the way:** `runtime_state.lua` used `_G`, which CET's sandbox does not have. LocationStudio init failed until it fell back to the chunk environment.

### D171 update (2026-09-26): the scene workspot node crashed; the idle now comes from the glue
- **First try:** the scene node with `EntityRef` + `names=["Mara"]` did nothing in game (`IsActorInWorkspot` false). `names` holds community/spawner entry names.
- **Second try:** the live RTTI enum `gameEntityReferenceType` is `0 EntityRef, 1 Tag, 2 SlotID, 3 SceneActorContextName`, so the node was switched to `type SceneActorContextName` with `sceneActorContextName "Mara"`. The game then crashed about 20 s after load, when the replayed meeting started: a null read at +0x10 on `redDispatcher11` (`crash_20260926_002515`, frames unnamed). The node was removed from both scenes, which are back to byte-identical with pre-D171. gen_scene keeps the `workspot` node type, unused, with this warning.
- **What held:** `WorkspotSystem.PlayInDeviceSimple` on the real, scene-spawned Mara, the way AMM does it, held through the rest of the meeting. The scene does not override it.
- **Shipped now:**
  - `tools/gen_workspot_ent.py` builds `mod\ash_cache\workspots\mara_idle.ent` (prebuilt into `assets/mod`). It is a plain gameObject from the suitcase template plus AMM's `workWorkspotResourceComponent` and its compiledData chunk, renamed `ashcache_idle` and pointed at the vanilla arms-crossed `stand_around__02.workspot`.
  - `source/scripts/AshCacheIdle.reds` is a separate ScriptableSystem, so the generated glue is untouched. A 1 s DelayCallback tick finds `Character.ashcache_mara` within 30 m of V. If she is not in a workspot, it spawns the device on her (Codeware, tag `ashcache_idle_device`, yaw + 180 because the component is turned 180) and calls `PlayInDeviceSimple(device, mara, false, n"ashcache_idle", n"ashcache_idle")`. If she is gone, it despawns the device.
  - The signature was checked with `redscript-cli lint` against `final.redscripts`, and both lint passes are clean.
- **Status:** built (build24) and copied into the game with `.bak-2026-09-26-idle2` backups. Not yet seen in game.

### D171 update 2 (2026-09-26): verified in game — trimmed workspot, AMM argument set, AI hold
- **Device:** a bare gameObject spawned but never took her. `mara_idle.ent` is now AMM's whole ArcadeMachine device (`workspot_anim.ent`) with only its `amm_workspot_base` component kept, renamed `ashcache_idle`.
- **Call:** AMM's argument set, `PlayInDeviceSimple(device, mara, false, n"ashcache_idle", n"AMM_WORKSPOT", n"None", 0.0, DontPlayAtResourcePosition)`. With the defaults the call was accepted every tick and she never entered.
- **Late arms, "wants to leave but can't":** both came from the vanilla `stand_around__02.workspot` itself, a street idle rather than a pose. It enters from hands-at-sides, turns her ±120° after the look-at target (`workLookAtDrivenTurn`), shuffles her feet (`*__shuffle__*` clips) and has random walk exits. `tools/gen_idle_workspot.py` writes `mod\ash_cache\workspots\mara_arms_crossed.workspot` from it without entry/exit anims, turns, reactions or shuffles. What remains is the `stand__arms_crossed_front__01` loop with `look_around__01` (random list 1/1, no repeat limit, sequence loops forever). The user confirmed in game: arms cross at once and she stands still.
- **Glue (`AshCacheIdle.reds`):**
  - It plays once per Mara entity and replays only if she has dropped out of every workspot. `IsActorInWorkspot` alone reads true while a scene drives her, so it is not a "we played" signal.
  - It re-sends `AIHoldPositionCommand` (99999 s, as AMM's `Util:HoldPosition`) whenever `IsCommandActive(n"AIHoldPositionCommand")` is false.
  - It polls every 0.2 s while waiting and every 1 s otherwise, and logs each state change to CET's `gamelog.log` (buffered, so it appears late).
- **Open:** in two sessions Mara was gone a few minutes after the aftertalk, with V standing still (`no mara`). This is unexplained and not investigated.

### D172 (2026-09-26): ash case re-bake — box UV charts, pocket faces, red light dropped

In game the case read as a red camouflage mosaic. Three separate causes, none of them the texture file
(a decoded ash_case_d01.xbm matches its PNG):
1. **UV atlas** — `smart_project` on the decimated Trellis mesh cut thousands of few-pixel islands;
   16-bit UVs + BC7 blocks + mips smeared them. `bl_game.py` now groups faces by dominant axis
   (smoothed, patches < 40 faces merged) and unwraps each group as one chart.
2. **Pocket faces inverted** — `recalc_face_normals` turned every pocket floor and wall (234 faces
   per half) away from the opening. Blender's preview draws back faces, the game culls them, so the
   open lid showed the shell through its pocket. `half()` now faces them into the cavity after the
   recalc. Found with the lid's `chunkMask = 2` live (only the interior chunk drawn: it vanished).
3. **Red light** — D150d's 18 lm point light 15 cm over the tray lit every surface red on the
   brighter re-bake. Removed from `ash_case_open.ent` (`gen_case_ent.py LIGHT = False`). Live, only
   toggling a light takes effect; SetIntensity does not.
Shots: shots/ls/20260926-112740-case_now.png (before), -112918-case_off2.png (light off),
-114430-case_pocket2.png (fixed). finish.sh no longer wipes the insert/cradle/glow files.

### D173 (2026-09-26): ash case modelled procedurally, Trellis mesh retired
After D172 the case still read as crumpled foil in game: the Trellis2 surface itself is lumpy, and
no re-bake fixes geometry. `_ashcase/bl_proc.py` now builds the case in Blender: a lofted shell with
bumper rib, seam lip and groove, lid rib, ribs and label on top, latches and catches, rubber handle,
purge valve, hinges, and metal corner caps. It uses one procedural material keyed by a face attribute
`part`, with grime and edge wear pre-baked from AO on a throwaway UV. It writes a `.blend`, which
`bl_game.py` now accepts:
- it opens the file instead of importing a glb;
- the seam comes from scene prop `case_seam`, so the cut runs in the groove;
- roughness and metal are baked from linked sockets when there is no packed ORM image;
- UVs come from smart_project for this source.

The interior BSDF is now looked up by type: with user prefs loaded, the node name is translated.
Run: `blender -b -P bl_proc.py -- proc/case_proc.blend && ./finish.sh proc/case_proc.blend`.
Backups: `game_final.bak-2026-09-26-proc`, `dev/bak/ash_case.bak-2026-09-26-proc`, `bl_game.py.bak-2026-09-26-proc`.

## D174 (2026-09-26): ash case atlases flipped vertically before xbm
In game the D173 case showed the atlas upside down (label bands on the lid ribs, dilate fill as blotches); a Blender preview with V flipped reproduced it exactly, and the raw bake was clean. So the glb -> WolvenKit .mesh / png -> xbm path loses a V flip. finish.sh now writes flipped copies to game_final/xbm_src (n01 green inverted too) and cooks those; the pngs next to the glbs stay unflipped for bl_prev.py (`bl_prev.py <dir> tex flipv` shows the game's view). Probably also why the Trellis case looked like crumpled foil.

### D175 — Mara's body is Mara (2026-09-26)

**The ask.** "ac_mara need to make extract full character model to make dead model with bullets or
knife wounds." Since D127 the landfill body was q105_fluff_dead_body_01 - a corpse, but a stranger.

**How the game draws a corpse.** An entCorpseComponent plus a generated .app whose skinned meshes
bind to it, posed by `entCorpseParameter.bakedPose`: one MODEL-space QsTransform per bone name
(verified: Hips at z 0.19, the body lying along X). Nothing is animated and nothing is re-skinned,
so no model export is needed - `tools/gen_mara_corpse.py` builds such an .app out of Mara's own
appearance (corpo__nusa_wa.app/_q306__fia_undercover_01) and a vanilla corpse pose:

    mara_shot   pose wa_generic_valentinos_01   3 x corpse_dec_006_gunshot_blood on the left chest + a splatter
    mara_cut    pose wa_generic_citizen_01      corpse_dec_007_incised_blood across the neck and on both
                                                forearms (defensive), a splatter below the neck

glue.json `ac_body` picks by `ashcache_mara_liberty_given`, the fact the coroner's note reads.

**Three things that were not obvious.**
- *The pose is exact only for the corpse it came from.* Bones outside the rig (face joints, hair,
  garment dangles) were baked for THAT corpse's meshes. Each bone is re-seated as
  pose * inv(their bind) * her bind (binds = inverse of the transposed `boneRigMatrices`, rows
  X Y Z W - matches the glb exactly); identity where the meshes agree, a fix where they do not.
  Face joints her head has and theirs did not ride rigidly on Head.
- *A corpse wound decal is a 3 cm box.* Its helper cube's local Z is the projection axis (read off
  the vanilla ground-side splatters). `tools/posed_skin.py` skins the body glb (WolvenKit `uncook
  --mesh-export-type MeshOnly`; plain `export` wants a material depot) into the pose so each
  wound sits on posed skin. Forearm targets are 3D points on the bone axis - an (x, z) target
  below the wrist put the first draft's "forearm" cuts on her thigh.
- *The q105 template is a braindance prop.* Its scanner carries scanning.q105_bd_dead_* clue
  records; cleared in the components and in the .ent's compiledData copy (asserted).

Also: her proxy mesh is a standing woman, so it is dropped and her meshes are AlwaysVisible; an
.app's compiledData is refilled from components by WolvenKit's writer (the CRUID dict is not
read); the two appearances are copies of one, so BufferIds are renumbered per file like handles.

**Not verified in game yet.** Decal size/orientation on her clothes is the open risk. Corpse
decals project on the character only (ROT_Character) - there is no blood on the ground.

### D176 — crash on taking the splinter: the idle glue waits 3 s for a new Mara (2026-09-26)
- **Symptom:** the game crashed 2–6 s after `ashcache_splinter_given` 0→1 (the case closing), twice: `crash_20260926_123320` and `_132623`. Both are a null read at +0xF8 on a `redDispatcher` worker thread, with unnamed frames.
- **Why not the case:** the case .ent/.mesh files only changed in sizes since the last close that didn't crash (10:51), and the quest steps logged around the 10:51 and 12:33 closes are identical.
- **Why the idle glue:** the splinter grant starts `talk_mara`, which spawns Mara beside V. `gamelog.log` breaks off mid-line at `ashcache i` at 13:26:17, the same second as the first-chance AV (13:26:17.787). At that moment AshCacheIdle had just sent the AI hold, spawned the device and called PlayInDeviceSimple on a Mara less than a second old. The D171 workspot crash was the same kind of worker-thread null read.
- **Change:** `source/scripts/AshCacheIdle.reds` leaves each new Mara entity alone for 3 slow ticks (3 s), logging `mara settling`. Backup: `.bak-2026-09-26-settle`. Built and deployed (`dev/build_idle_settle.log`).
- **Status:** the cause is inferred, not proven. It needs one more take of the splinter in game. If that still crashes, the next test is disabling AshCacheIdle entirely.

### D177 — aftertalk never offered its choice: the idle glue keeps off a Mara in a scene (2026-09-26)
- **Symptom:** after the FIA fight Mara's aftertalk plays its opening lines, then no choice appears and the splinter decision never starts.
- **Evidence (trail.log):** three runs today (13:50, 13:55, 13:58) reach `progress 6` and stop. `ashcache_mara_warned` (set by the aftertalk's `fact_warned`, after the hub) was never set today; the last time was before D171. So the aftertalk stalls at `hub`, and `gate_hide`/`obj_decide_on`/`decide_scene` never run. The graph links are intact. D171's open issue ("Mara gone minutes after the aftertalk, V standing still") is the same stall.
- **Cause (inferred):** AshCacheIdle sends `AIHoldPositionCommand` and `PlayInDeviceSimple` to Mara while the aftertalk holds her. The meeting survived this; the aftertalk did not.
- **Change:** `AshCacheIdle.reds` returns with `mara in scene` while `SceneSystem.GetScriptInterface().IsEntityInScene(mara)` is true. She crosses her arms once a scene lets her go, no longer mid-dialog. Lint clean (build_inscene.log).
- **Deploy gap found:** `tools/deploy.sh` never listed `AshCacheIdle.reds`; every change since D171 update 2 (including D176's settle) reached the game only by hand-copying, and D176 had not reached it at all. The D176 crash not recurring is therefore not evidence for D176. The line was added (backup `deploy.sh.bak-2026-09-26-idle`); deploy_inscene2.log shows the copy.
- **Status:** deployed, not seen in game.

### D178 — crash as talk_mara ends, and no idle through it: settle after release, hands off the aftertalk only (2026-09-26)
Run 14:16-14:17 with D176/D177 deployed. Spawn settle worked ("mara settling" 14:17:16, no crash at spawn). D177 then kept the glue off Mara for all of talk_mara, so she stood in a bind pose through it (user: "mara animation dissapear"). Choice made 14:17:42.6; first-chance AV 14:17:43.9 on redDispatcher14, null +0xF8, crash_20260926_141749 (signature 1A79772A, new stack; same null +0xF8 shape as 12:33/13:26). The first idle tick after the scene released her sends the hold and spawns/plays the device - same "act within a second of a Mara transition" pattern as D176.
Change (AshCacheIdle.reds): the tick a scene releases her resets the 3 s settle; the D177 hands-off now applies only while ashcache_progress >= 6 and ashcache_mara_warned == 0 (the aftertalk), so the mid-dialog play returns for talk_mara. Built lint clean, deployed. Not yet seen in game; D177's aftertalk fix is still unverified (this run crashed before the FIA fight).

### D179 — aftertalk stall, real cause: Mara still locked by the idle glue when it opens (2026-09-26)
- **Run 14:32-14:38 (D178 deployed):** talk_mara ended 14:34:35; the glue's hold + workspot followed after the 3 s settle. Terminal read 14:34:55 (progress 5), fight over 14:35:10 (progress 6). The aftertalk played `sec_open` and stalled at `hub`: `mara_warned` 0, V still in a scene, and the idle status "no mara" at 14:38.
- **Cause:** D177's hands-off only stopped NEW commands. The aftertalk reuses the keepAlive Mara (D123's known risk), and she was still in the device workspot under a 99999 s `AIHoldPositionCommand`. The scene could not take her. Before D171 (no glue), `mara_warned` was set.
- **Change (AshCacheIdle.reds):** from progress >= 5 until `mara_warned` is set, `Release()` stops her workspot (`StopNpcInWorkspot`), cancels the stored hold (`AIComponent.CancelCommand`), despawns the device, and does nothing else. That runs 15+ s after talk_mara releases her, clear of D176/D178's transition window. The D177/D178 in-scene aftertalk check is removed. Build lint clean, deployed (`.bak-2026-09-26-release`). Not yet seen in game.

### D180 — D179's release never ran: FindMara is blind in a scene; release by entity ID (2026-09-26)
- **Run 15:13-15:18 (D179 deployed):** talk_mara 15:14:25, terminal 15:14:41, fight over 15:16:02. The aftertalk stalled again with `mara_warned` 0; idle status "no mara".
- **Live evidence (15:20):**
  - Targeting (`TSQ_NPC` and `TSQ_ALL`, `TargetingSet.Complete`, 50-300 m) returned 0 parts while V was in the scene. `npc_list_nearby` uses the same query.
  - FindMara is therefore blind in a scene and flickers through walls. It flickered "settling"/"no mara" at 15:12. D179's release sat after FindMara, so it never ran.
  - On a stand-in `Character.ashcache_mara`, deleting the idle device, with or without `StopNpcInWorkspot`, did not remove her. Deleting it alone left her in its workspot (`IsActorInWorkspot` true). The "no mara" branch does exactly that.
- **Change (AshCacheIdle.reds):**
  - The progress >= 5 / `mara_warned == 0` check now runs before FindMara.
  - `Release()` finds her by the stored `m_npc` (workspot) and `m_holdNpc` (hold) with `GameInstance.FindEntityByID`. It stops the workspot, cancels the hold and despawns the device. It retries each tick until she resolves.
  - Build lint clean, deployed (`.bak-2026-09-26-byid`). Not yet seen in game.
- **Still unproven:** that the lock is what stalls the aftertalk. If it still stalls, the next thing to check is whether the aftertalk's `ashcache_mara` actor (same unique name + keepAlive as the meeting's) spawns at all. Try giving it its own record (D123's fallback).

### D181 — aftertalk hub was waiting on distance, not on Mara's workspot
Live at the stall (2026-09-26 15:47): progress 6, mara_warned 0, idle already "released for aftertalk", V frozen by Tier3 at (-1897.5,-2494.0), 9.1 m from #ac_clinic_entrance, with no Mara in view. The compiled hub was mode attachToActor with customActivationRange 3.3, so it only displays when V is within 3.3 m of actor 0. The lines are subtitles plus VO and play regardless, which is why the scene "stalls after the opening lines". D177–D180 (idle release) addressed the wrong layer.
Fix: gen_scene.py honours `"attachToScreen": true` on a choice node, and scene_aftertalk's hub sets it. That is the same mode scene_decision already ships. Mara not appearing at the door (D123 known risk) is separate and cosmetic; it no longer blocks progress.

### D182 — Mara's corpse mesh flung to a far point: baked bone order (2026-09-26)
- **Symptom (in game, 16:15):** at the landfill, part of Mara's body mesh stretched into a long sheet heading off into the distance. Seen from above it looked like a pillar; seen close up it was a torn brown band. Her face and body pose were otherwise right.
- **What checked clean:** every bone her meshes use has a pose, with sane positions and unit scale. Her 18 meshes agree on every bind.
- **The one difference from vanilla:** `bakedBoneNames` was sorted alphabetically. Vanilla lists bones in rig order (Hips, Spine, LeftUpLeg, ...), with extras after.
- **Change:** `tools/gen_mara_corpse.py` now keeps the vanilla order and appends the extra face bones sorted. Backup: `dev/bak/gen_mara_corpse.py.bak-2026-09-26-order`, plus the old `ash_mara_corpse.{app,ent}` in `dev/bak`.
- **Build:** regenerated, built and deployed (`dev/build_d182.log`). The game archive is backed up as `.bak-2026-09-26-d182`.
- **Status:** the cause is inferred, not verified in game.

### D183 — Mara's corpse streaks at the camera up close: LODMode

**Symptom (after D182):** the band stayed. Live test with a DES-spawned copy: clean at 3, 6 and 12 m. Inside ~2 m every mesh streaks toward the camera: skin, dress, jacket, and head and hair (seen with the head hidden).
**Ruled out, one hot-reloaded build each:** empty `forceLOD0Components`; vanilla-only bone list (drops the 30 eye and tongue joints); no `entGarmentParameter`. The vanilla `q105_fluff_dead_body_01.ent` renders clean from the same spot.
**Cause:** our mesh components had `LODMode: AlwaysVisible` (set by the generator); vanilla corpses use `Appearance`. With `Appearance` the 1.5 m shot is clean and she still shows at 12 m.
**Change:** `tools/gen_mara_corpse.py` sets `LODMode = "Appearance"`; regenerated, built, deployed. Backup `dev/bak/gen_mara_corpse.py.bak-2026-09-26-lodexp`. The D182 rig-order change stays in, since it matches vanilla, but it was not the cause.
**Status:** verified live (hot-reloaded build, test spawn). Not yet seen at the landfill.

### D184 — Landfill: probe wall removed, dropped Liberty laid flat

- **Wall.** The D132 geometry probe (a 4 m industrial wall panel `ac_probe_geometry` plus its collision box `ac_probe_geometry_col`) was still standing on Mara's body marker long after it had answered its question. Both are removed from `source/world.json`, sector 2, and the rebuilt landfill sector has no static mesh or collision nodes.
- **Pistol.** At roll 0, `int_weapons_002__constitutional_liberty__base1.ent` stands upright on its grip, which is its in-hand pose. I tested live at the landfill: roll 90 lays it on its side; pitch 90 still stands. `world.json` props now take an optional `roll`, which `gen_glue.py` passes to a new `roll` parameter on `AshCachePropSpawn`. The gun's z is raised 3 cm, to 73.41.
- **Status.** Built and deployed. Not yet seen in game: the game crashed while hot-reloading the scripts, so it needs a normal restart.
- **Warning.** RedHotTools' `.hot-scripts` crashed the game (write access violation in "Translating bytecode") after a global function's signature changed. Restart the game for signature changes; hot reload only body-only edits.

### D185 — Landfill arrival never fired; quest never closed

- **Arrival.** Two watches share stage 7: `ashcache_at_landfill` and `ashcache_at_cynosure`. `ArmWatch` kept only the last match, so it watched the shaft head and V could stand on Mara's body forever without firing the landfill watch. `gen_glue.py` now stores the armed stage (`m_watchStage`, formerly `m_watchIndex`). Each tick checks every unfired area at that stage and times the next sample off the nearest one.
- **Close.** `quest_done` (Succeeded) is followed by `obj_cynosure_on`, and activating a child objective puts the quest back to Active; nothing succeeded it again afterwards. The new `quest_final` node (appended, so no renumbering and no revision bump) sits between `desc_meet_off` and `phase_out`.
- **Verified.** Live in game, setting `ashcache_at_landfill` completed the landfill objective, granted the autopsy note and activated the Cynosure objective. `replaytest.py` passes. The watch change needs a game restart because a class field was renamed. Not yet played through: arriving at the shaft, then the meeting, then the quest reading Succeeded.

### D186 — Mara's gun is a pickable trophy: the Last Word

The Liberty beside her body was `int_weapons_002__*`, a mesh with no item, so it could not be picked up. It is now a real loot drop of a new record, `Items.ashcache_mara_trophy`, named "Last Word" / «Останнє слово».

- **Record** (items.json, gen_tweak.py: new `keep_actions`, `tweak`, `stats` fields). Built like Dex's Plan B (`Preset_Liberty_Dex`, read live): the iconic blueprint, the `IconicWeapon` tag, `IconicQualityRandomization` instead of the random-quality and random-mod groups, and `Quality.IconicItem`. It keeps the Default visualTags, so it looks like the gun that was lying there. Stats: +15 CritChance, +35 CritDamage, +0.5 HeadshotDamageMultiplier and +4 MagazineCapacityBase, all Additive. The same numbers are in `item_mara_trophy_desc`.
- **Drop** (source/scripts/AshCacheTrophy.reds). Condition: body placed, liberty_given set, `ashcache_mara_trophy_dropped` == 0, and V within 25 m of the prop spot. Action: GiveItem to V, then `LootManager.SpawnItemDrop(V, item, pos, identity)`, then set the fact.
  - SpawnItemDrop MOVES an item out of the owner's inventory. Checked live: dropping an item V did not hold returned true and spawned nothing. Dropping a held one removed it from V and put a lootable drop on the ground.
- **Glue**: ac_body_gun has an extra `when` condition, trophy_dropped max 0, so the look-alike prop goes when the real drop appears.
- **Validator**: an item may name `granted_by` (a script that must mention the record) in place of a graph grant.

Not yet verified in game: the record's name, stats and quality after TweakXL loads it, and the script's drop firing on its own. Both need a restart. Risk: if V leaves before picking it up and the drop is streamed out, it is not dropped again.

### D187 — Last Word invisible in the inventory: `!append` replaced, not appended

After the pickup, the trophy was in V's inventory (checked with TransactionSystem) but did not show in the UI. Its stats read EffectiveDamagePerHit 0, MagazineCapacity 0, Quality 0 and ItemLevel 0, and `statModifiers` held 5 entries where the base has 151. On a record defined with `$base` in the same block, TweakXL's `statModifiers: !append` REPLACED the inherited list. Without the Base_Weapon_inline* modifiers no derived weapon stat is computed.

Fix: `statModifiers` stays inherited. gen_tweak.py now emits the custom stats and Quality.IconicItem as their own `Items.ashcache_mara_trophy_stats` StatModifierGroup (flats copied from Base_Liberty_Constant_Stats, read live). items.json lists that group in the record's full `statModifierGroups`. Not yet re-checked in game; needs a restart.

## D188 — trophy tags written in full (2026-09-26)
Live read after D187: the trophy was in V's inventory with correct stats (25.4 dmg, mag 16) but its
tags were only [IconicWeapon]. `tags: !append-once` on a new $base record REPLACES the inherited list,
exactly like statModifiers in D187, so the Weapon/Handgun tags the inventory filters on were gone.
items.json now writes the Liberty's full tag list (read live from ashcache_mara_liberty) plus IconicWeapon.
Rule: never use !append / !append-once on a record defined with $base in the same file.
D188b: the trophy showed as Tier 1 (GiveItem = Common), 25 dmg vs the Boss Liberty's 29. Added
`quality: Quality.Legendary` (gen_tweak puts it in the _stats group) and DamagePerHit AdditiveMultiplier
+0.3 (the form Dex's Liberty uses for its +1%). Description text updated en+ua.

## D189 — trophy tier via the record's `quality` field
D188b put `Quality.Legendary` in the trophy's StatModifierGroup. It is a Quality record, not a stat modifier, so it did nothing: new drops were still Tier 1 (seen in game). It is now written as `quality: Quality.Legendary` on the item record. A live test with SetFlat and then GiveItem gave Quality 4 and EffectiveDamagePerHit 73; the Tier 1 copy had 33. Copies already created keep their saved tier.

## D190 — trophy is Tier 5++
Changed `quality` to `Quality.LegendaryPlusPlus` so the trophy matches the look of vanilla top-tier iconics. Live test with SetFlat and then GiveItem: Quality 4, IsItemPlus 2, EffectiveDamagePerHit 85 (was 73 at plain Tier 5).

## D191 — V and Mara are FireRedTTS3 clones, not TTS -> RVC
`render_lines.py --tts firered` clones each voice from one vanilla game clip plus that clip's own en-us subtitle as the transcript (`reference/firered_voices.json`). There is no RVC stage: the clone ships as it is. The batch runs through `tools/firered_render.py` in the `fireredtts3` conda env, loading the model directly with no Gradio server, at 10 flow steps and cfg 2.0.
- **References (chosen by ear 2026-09-26):**
  - Mara: Rogue, `rogue_q103_f_1700d0ee0529f000`.
  - V (and Echo): male V, `v_mq001_m_19db828fbb44d000`.
- **Audition:** 5 Mara and 4 V references were tried, two lines each. 6 of the 18 renders ran to the 64 s cap because the stop token never fired, and they clustered on particular references. The likeliest cause is a subtitle that doesn't match what the actor says in the clip.
- **Runaway guard:** the renderer re-rolls the seed when a render runs over 3× the length its word count predicts, and fails after 4 tries.
- **Scope:** Unknown and BlueEyes keep their existing voices, and are skipped with a reason. Ukrainian stays subtitle-only (D42).
- **Backups:** the RVC renders are in `vo.en-us.bak-2026-09-26-rvc/` and `narration.en-us.bak-2026-09-26-rvc/`.

**Verified in game (2026-09-26):** the user played the full quests with the FireRed voices - "much better than RVC". Accepted.

## D192 — Cynosure M1 greybox: a custom sector 300 m under the clinic   (2026-09-29)

The facility is its own streaming sector, built entirely by Location Studio from
`source/cynosure/cynosure_m1.edl.yaml`. It ships as `archive/pc/mod/ash_cache_cynosure.archive` + `.xl`.
The frame CYN has its origin at (-1908, -2470, -300), under the Dogtown clinic, and +Y runs along the canonical route. Shaft 14 is a remote surface access point: its head is by the motel (-2240, -2553), ~340 m away, and the descent abstracts the buried service route between the two (D193). That is about 100 m
below and 330 m away from the vanilla PL Cynosure bunker (-2072.9, -2205.7, -194.8), so nothing collides with
Phantom Liberty. D19's reason for leaving the vanilla bunker still stands.

It has all 21 canonical rooms (CYN_ROOM_01..16 plus the A side rooms), with sizes taken from the eight concept images:
610 nodes (421 meshes, 145 collisions, 44 static lights), 8 cameras and 21 navigation nodes.

**Verified in game:** V stands in Entry and in the Predictive Core, the walls and floors line up, and the Entry doorway
opens onto Checkpoint.

**Not built yet:**
- door frames (LS skips its door pieces, so doorways are open gaps);
- the Shaft 14 trigger/teleport from `ac_cynosure_shaft`;
- M2 custom meshes (core column, coffins, archive tubes, pump) and vanilla stand-ins for them;
- a round core hall (the M1 core is square);
- the anchors in CYNOSURE_ANCHORS_AND_TRANSFORMS.md are still UNMEASURED.

Rebuild: `edl_apply` the yaml, then `build_mod_from_project(name=ash_cache_cynosure, premise_id=<new>,
allow_skipped=true, streaming_x=260, streaming_y=260, streaming_z=120, cli=tools/wkcli.sh)`, then hot-reload the
archive (the block is already registered).

## D193 — Shaft 14: the descent is a quest teleport, not an elevator   (2026-09-29)

The shaft-head scene gets two hub options: "[Cut the seal] Climb down Shaft 14" / «[Зрізати пломбу] Спуститися в шахту 14".
It is offered only once the weld beat has been done (`ashcache_cynosure_alive` = 1) and `ashcache_cyn_descended` is still 0.
After the first descent it becomes a plain "Climb down Shaft 14" / «Спуститися в шахту 14».
Both leave through a new scene exit, `shaft_descend`.

The graph then runs, in order:
- `tp_cyn_down`, a new generator node type `teleport`: `questTeleportPuppetNodeDefinition`, copied field for field from the 24 vanilla ones, with destination `#ac_cyn_entry_tp`;
- `ashcache_cyn_descended` = 1, written AFTER the teleport, so no save says V is down while V still stands at the shaft;
- `ashcache_cyn_phase` = 20 (ENTRY);
- `ashcache_cyn_escaped` = 0;
- a pause until `ashcache_cyn_escaped` = 1;
- `tp_cyn_up` to `#ac_cyn_shaft_return_tp`, then back into the shaft scene.

**Why a teleport and not an elevator:** the facility is ~380 m down AND ~340 m sideways from the shaft head. An elevator only moves vertically inside one shaft, and a 380 m cabin would be its own streaming problem. Vanilla's long elevators are themselves a cabin plus a fade plus a quest teleport. An elevator cabin at the shaft head is the M2 dressing, and its "ride" is this node.

**Why dedicated markers and offset 0:** the landing point is data rather than a vector hidden in a node, and the `destinationOffset` rotation semantics never matter. All three markers are in `ash_cache_motel`, which is AlwaysLoaded, so they resolve from 300 m underground.

**The return is M1 scaffolding:** a glue area on `ac_cyn_escape` (radius 4, stage 7). The M4 ending flow replaces it.
- New glue flag `rearm`: the glue listens to the area's fact, and the graph's reset to 0 re-arms the watch. Without it, a second descent would park V underground until a reload.

**Tooling:** `validate.py` now counts glue area markers as references, and lets the graph use facts that the Cynosure contract declares (`ashcache_cyn_phase`).

**Not verified in game yet:** the teleport node itself; the fade (`healAtTeleport` 1 as vanilla); landing on `ac_cyn_entry_tp`; the return.

## D194 — Shaft hub runs at full gameplay; D193 descent verified (2026-09-30)

**Bug:** the Shaft 14 scene (D131) had never been run in game. Its `tier_on` node raised the scene to Tier3_LimitedGameplay with empty hands before the world-attached hub. In game that locked walking, and the hub showed only its collapsed speech-bubble icon: it never expanded, even with V 1.8 m away and looking at it. The scene started from the 12 m arrival watch and was then stuck with no choice reachable, holding V in tier 3.

**Fix:** removed `tier_on`; `start` now links straight to `sec_arrive`. This is the shape of `scene_terminal.json`, `scene_box.json` and `scene_courier_shard.json`, all proven in game, none of which raise the tier before a world-attached hub. The `tier_off` / `tier_off_d` nodes stay; setting Tier1 at full gameplay does nothing.

**Rule:** do not raise the tier in front of a world-attached choice hub. Tier3 is for an actor conversation, not for a prompt the player has to walk up to and look at.

**Verified in game 2026-09-30:** the hub expands; "Put a hand on the weld" sets `cynosure_alive`; "[Cut the seal] Climb down Shaft 14" teleports V to `ac_cyn_entry_tp` (landed at -1907.6, -2468.1, -300.0) and sets `cyn_descended`. The return leg (the `ac_cyn_escape` watch → `tp_cyn_up`) is still unverified.

**Addendum, same day: return entry.** The return leg works: the `ac_cyn_escape` watch fired and `tp_cyn_up` put V back at the shaft head. But the scene re-entered at `shaft_in`, so the arrival lines replayed every time V climbed back up. Fix: the scene got a second entry, `shaft_return` → `start_return` → `hub` (node appended, not inserted), and `tp_cyn_up` now targets it. `shaft_in` stays the first-visit entry.
Verified in game 2026-09-30: the full round trip works (descent, the Escape watch, the return teleport, then straight to the hub with no replayed arrival lines).

## D195 — Cynosure M2: procedural door frames and round core, anchors measured   (2026-09-30)

M2 is generated, not hand-written: `tools/gen_cyn_m2.py` reads `source/cynosure/cynosure_m1.edl.yaml` and writes
`cynosure_m2.edl.yaml` (the EDL id stays `cynosure_m1`, so applying it replaces the M1 build in place) and
`cynosure_anchors_measured.yaml`. Edit M1, then rerun the script.

- **Door frames.** The kit's door pieces never export, so every M1 doorway was a full-height 2 m slot, 30 m tall in the core.
  Each of the 20 shared slots now gets an LS procedural `wall` filler with a 1.6 x 2.4 m opening, plus a `door_frame`.
- **Round core hall.** A 32-segment ring of tangent walls (apothem 19 m, 30 m tall) inside the 40 x 40 core. It has openings
  at the south and east doors, and boxed passages (two sides and a roof) join each opening to the square door, so the
  corner voids cannot be reached. The core's corner work lights and `cyn_cam_core` moved inside the ring.
- **Anchors.** 64 structural anchors are MEASURED from the same EDL numbers: world origin, forward reference, 21 room origins,
  the main-route `X_TO_Y` door slots, and room ENTRY/EXIT 1 m inside those doors. Prop, device, light, SFX and surface
  anchors stay UNMEASURED until those objects exist.
- **Pivot and sectorCategory:** both were already fixed on 09-29 (`pivot='max'` in the kit, and the exportUI lazy init) and survived the LS update.

**Verified in game.** The sector was hot-reloaded and checked with raycasts taken with V standing in each area:
- the doorway opening is clear, and its jambs and header block;
- the ring wall blocks at r = 18.8 m, and the core's south and east openings are clear;
- the passage sides and roof block.
Screenshots show the curved hall and the framed doorways.

**What it took (LS 0.93.0).** Memory `ls-093-procedural-pitfalls` has the details.
- **Apply crash:** CET has no `package` global, so `init.lua` got a shim.
- **Broken native writers:** the native .mesh/.mi writers emit JSON that WolvenKit 9.0.1 rejects, so M2 uses the template
  backend (a glb imported over `int_common_a_wall_h400_l200_a.mesh`, which is extracted into LS `mod_sources/`).
- **No tangents:** the glb writer emitted none, and WolvenKit refuses such geometry, so `procedural.py` was patched.
- **Doorway collision cut:** the `doorways: auto` collision rule removed the jambs' collision, so all M2 geometry uses `doorways: keep`.
- **Kit fix reverted:** the update undid the `bunker_large` entry in `edl.py`, so it was re-applied.

**Open:**
- the archive also carries a byte-identical copy of the vanilla template mesh, which should be excluded;
- the elevator cabin waits on a stood-on capture of the real shaft head;
- M2 props (core column, coffins, archive tubes, pump) are not made yet.

## D196 — M2 visible pieces are vanilla kit meshes, not procedural geometry   (2026-09-30)

Supersedes D195's door fillers, door frames and ring walls. In game (user screenshot, 2026-09-30) the procedural
pieces looked broken: LS box-projects their UVs, and the int_common_a multilayer masks are laid out for the kit's
own UVs, so trims and paint landed at random. `tools/gen_cyn_m2.py` now builds the same things from the kit itself:

- every doorway is the vanilla `int_common_a_wall_door_single_h400_l200_a.mesh` (framed 1.48 x 2.49 m opening),
  plus `int_common_a_wall_h400_l200_a` pieces above it in rooms taller than 3.8 m;
- the core ring is 32 wall pieces (door pieces at 0 and 270 degrees), the passages are wall pieces with a
  `int_common_a_ceiling_tiles_b` roof;
- collision is 102 plain boxes (`col_*`), independent of the visuals.

No procedural stage is left: the archive dropped from ~1 MB to 73 KB and a rebuild takes about a minute, not 20.
Verified: the Checkpoint -> Entry doorway is open (aim ray 14.4 m through it) and textured like the walls.
Open: one unexplained second door frame about 2 m west of the ring's south opening; it may be a stale
leftover in the running game. Check after a restart.

## D197 — Starfield props for Cynosure dressing (M3), personal build only   (2026-10-01)

The core column, coffins, archive tubes and pump had no source. Starfield (installed at
`/mnt/data/Games/Starfield...`) has a large lab, bunker and industrial set, so `/mnt/sata/Cyberpunk2077/starfield_kit/`
now converts its props straight from the BA2 archives: NIF + `.mesh` geometry, `.mat` materials resolved through
`materialsbeta.cdb`, one baked atlas per prop, and the ash_case `mkxbm` / mkmesh route to CR2W.
See its README. 51 props are cooked at depot `mod\ash_cache\sf\<name>\`.

**Licence:** these meshes are Bethesda's. They are fine for the user's own game but must never be in a published
build. Anything that ships needs its own models; the ComfyUI SDXL + Trellis2 route is in `starfield_kit/gen/`.

M3 dressing is declarative: `source/cynosure/cynosure_m3_dressing.yaml`, read by `tools/gen_cyn_m3.py`, together with
`cynosure_m2.edl.yaml`, produces `cynosure_m3.edl.yaml` (still EDL id `cynosure_m1`) and `cynosure_m3_plan.png`.
It has wall rows (doors are skipped with 0.8 m clearance), lines, stacks, rings, wall mounts and free placements.
Every prop gets an oriented box collision from its cooked bounds. Overlaps and door-approach blockages are reported,
not silently fixed. First pass: 231 props of 38 kinds, 218 boxes, 0 warnings. Stand-ins until real models exist:
- the core column is a stacked 12 m containment tank;
- the archive tubes are specimen tanks;
- the coffins are creature-cage pods;
- the pump is `genericmachines_a01`.

**Not applied yet** (the game was not running). To apply:
1. `edl_apply` `cynosure_m3.edl.yaml`.
2. `dependency_stage(workspace_name=ash_cache_cynosure, premise_id=<new>,
   sources=["/mnt/sata/Cyberpunk2077/starfield_kit/depot"])`. This copies only the referenced props into the build
   workspace, so no game-folder write is needed.
3. `build_mod_from_project` as in D192, then hot-reload.

Then check in game:
- that the prop fronts face the room (default −Y, `fronts:` overrides);
- the 12 m core column inside the ring;
- the body scanner's hang height.

D197 addendum (same night):
- **Branch coffin is real now:** `cyn_branch_coffin` is built procedurally (`starfield_kit/gen/bl_coffin.py`):
  2.2 x 0.9 x 0.82 m, about 2.7k tris, Starfield tiling PBR baked to one atlas, and a glass window chunk.
  The Branch Coffins room has two columns of four, with the aisle kept clear. It replaces the creature-cage stand-ins.
- **Glass:** Starfield `*EffectGlass` parts are kept as a trailing submesh with a second material instance on
  vanilla `base\materials\glass.mt`, default parameters. Unverified in game. This applies to the specimen tank
  (the archive tubes), the security camera and the UV irradiator.
- **Tint:** `BSMaterial::Color.w` is the override amount; `Multiply` mode multiplies, any other mode lerps.
  The first cook ignored w and over-darkened trims.
- **Bake sentinel:** island-edge texels that sampled the magenta sentinel were spread by the dilation.
  The mask now takes near-magenta plus a 2 px grow. All 51 props were re-cooked.
- **GPU routes tried for custom models (ComfyUI):**
  - SDXL concept images work only with MIOpen off (`gen/comfy_nomiopen.py`).
  - Trellis2 image-to-3D shape works, but the ROCm safe decoder emits CPU tensors that CuMesh rejects,
    which breaks every o_voxel/CuMesh post node and poisons the HIP context until a restart.
  - The raw shape is 5 M faces of face soup (31k fragments).
  - Single-view texturing fails in the patched projection code.
  - Verdict: for hard-surface props, procedural Blender + Starfield textures beats Trellis here.
- **3D Gen Studio** was not usable tonight: its backend is not running, and port 3001, where its MCP looks,
  belongs to the Invidious container, so every call returns `{}`.
- **Emissive:** `ColorEmissive` materials bake into a 5th atlas, `e01`; the mesh gets metal_base `Emissive` +
  `EmissiveEV` 4 + white `EmissiveColor` (the ash case's D150c parameter set). It is on the specimen tank's cyan
  glow, the mega-screen, the body scanner lights, the UV lamp, the coffin's amber lamp and the core pillar.
  The EV is a first guess.
- **Core insert:** `cyn_core_insert` (`gen/bl_core.py`) is a 5.9 m-radius glass tube with a cyan emissive pillar,
  collars and conduits, sitting inside the stacked containment column. It has no collision of its own; the tank
  stack collides.
- **Verification:** `starfield_kit/sf_verify.py` reads every cooked mesh back through WolvenKit and checks
  chunks, materials, texture files and bbox. 53/53 pass. The M3 regeneration: +237 props, 39 kinds,
  223 boxes, 0 warnings.
- **Archive size:** the 39 kinds used are about 122 MB raw, mostly BC7 textures; the large tanks and servers are 2048.
  Drop those to 1024 if the archive needs to shrink.
