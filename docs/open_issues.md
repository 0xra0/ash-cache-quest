# Open issues

## OI-1 — Mara must survive the cleanup fight when trusted   (from D3)   **RESOLVED (2026-09-03, D29)**

The Hide ending is gated on `ashcache_mara_trusted`, but its script needs Mara
alive: she names the Badlands cache, hands V the FIA Master Key, and seals the
case. The design also says she "may be caught in crossfire" during the FIA cleanup.

So the gate can pass while the ending is unplayable.

**Proposed fix (no extra gate condition needed):** make Mara invulnerable for the
duration of the cleanup fight whenever she is fighting alongside V. This is the
standard vanilla pattern for quest companions and keeps D3 exactly as decided.
When hostile she is not in the fight at all, so she needs no protection — and Hide
is already gated off in that branch.

**Partly handled in the graph (2026-09-01).** Both `gate_hide` and `br_hide` now
test `ashcache_mara_dead == 0` as well as `ashcache_mara_trusted == 1`, so a dead
Mara closes the Hide ending cleanly instead of opening an unplayable one. That is
the safety net, not the fix — the fix is still to keep her alive, because a player
who earned Hide and then lost it to a stray grenade has been robbed of an ending
with no explanation. Whoever builds the cleanup encounter owns this.


**Resolved as a side effect, which is the right way for this one.** (2026-09-03)
The Mara scene now sets `questCharacterManagerParameters_SetMortality` to
`Immortal` on `#ac_mara` with the claim `ash_cache_mara_protected`, and the FIA
cleanup runs after that scene in the graph. She is already protected when the
fight starts, so there is nothing left to special-case in the encounter.

The protection is deliberately never released. All 211 vanilla scenes that set
mortality also set `Mortal` again; this one does not, because the requirement is
that she cannot be killed *after* the quest either. The absence of a matching
`Mortal` node is the feature, and both the node's `_comment` and D29 say so, so
that a later reader does not "fix" the asymmetry.

## OI-2 — SMS threads were filed under an invented contact   **RESOLVED WRONGLY 2026-09-02, RE-RESOLVED 2026-09-03 (D22)**

`tools/gen_journal.py` defaulted every thread to `contacts/unknown`. The worry was
that an invented contact folder may not surface the thread. It was the right worry,
and the references settle it without needing the game.

Two shapes are observed, and only one of them is ours:

- `contacts/<character>` — the thread joins somebody's existing message history.
  High Stakes ships `contacts/panam` and `contacts/reginald_reggie_jones`; both are
  real vanilla contacts. Hot Fuzz's `contacts/stout` and Deceptious's
  `contacts/judy` are the same idea from the other side — those two only *point at*
  vanilla entries from a questphase node, they do not author a folder at all.
  Nothing in any reference authors a contact that does not already exist.
- `contacts` — the thread stands alone, titled by the conversation's own `title`
  LocKey. Undermine ships three like this (`alerts`, `ooc_notifications`,
  `uqs_gender`) as a `gameJournalPrimaryFolderEntry`.

Ash Cache's senders are anonymous by design — the threads are titled UNKNOWN and
NO CALLER ID — so there is no character to file them under and the second shape is
both the correct one and the observed one. `title` already carries the thread name,
so nothing is lost by not having a contact.

The folder *type* follows from the id's depth, which explains all four samples:
`contacts` is a top-level section and gets `PrimaryFolderEntry`, while
`contacts/panam` and `quests/main_quest/prologue` sit inside one and get
`FolderEntry`. (Undermine also uses Primary for its quests path, so the engine
tolerates the wider type up there; two mods to one say plain.)

Verified from the packed `.journal`:

    RootFolderEntry ''
      FolderEntry 'quests/main_quest/prologue'  -> Quest 'ash_cache'
      PrimaryFolderEntry 'contacts'
        PhoneConversation 'ac_msg_unknown'    -> 2 messages
        PhoneConversation 'ac_msg_blueeyes'   -> 1 message

`source/quest_graph.json`'s three journal paths moved with it, `validate.py` now
rejects a thread filed anywhere but a contact folder, and that check has a negative
test. Setting `"contact": "contacts/judy"` on a thread still works if a future
thread should come from a named character.

### Correction, 2026-09-03

Everything above about *which* shape Ash Cache wants is right. The reading of
Undermine that justified it is not.

Undermine's three threads do not sit directly under `contacts`. They sit under a
`gameJournalContact` with id `uqs`, which sits under `contacts`. The earlier pass
listed entry ids out of the file and never walked the tree, so it saw three
conversation ids at what it assumed was the top level and concluded the contact
layer was optional. It is not optional — it is the entry that carries the avatar
and the sender name, which is why the messages arrived from nobody and with no
portrait, and why the player asked for "icons of npc".

Fixed by authoring one contact per anonymous sender, with a real
`PhoneAvatars.*` id on each. Every message path gained a segment, the graph's
three `journal_entry` nodes moved with it, `validate.py` now requires a contact
block and cross-checks the depth, and negtest covers both the missing contact and
a stale three-segment graph path. Full reasoning in D22.

The lesson is narrow and worth keeping: **print the tree, not the ids.** A flat
list of entry ids from a nested resource cannot tell you what nests inside what,
and that is exactly the question a shape decision turns on.

## OI-3 — Quest folder path is inherited, not reasoned   **RESOLVED (2026-09-02)**

The worry was that Ash Cache is a `SideQuest` sitting in `quests/main_quest/prologue`
because that is the only path proven to work, and might therefore land in the wrong
journal tab. It will not, because the folder is not what decides the tab.

The quest entry carries its own `type` enum, and all three reference mods set
`type: MinorQuest` *while* sitting under `quests/main_quest/prologue`:

    hot_fuzz      quests/main_quest/prologue/nq_ncpd_judy      type MinorQuest
    high_stakes   quests/main_quest/prologue/sq_high_stakes    type MinorQuest
    undermine     quests/main_quest/prologue/nq_uqs            type MinorQuest

Meanwhile vanilla's own minor quests live somewhere else entirely — the Lucy mod
reads `quests/minor_quest/mq049_edgerunners` and `quests/minor_quest/lost_on_you`,
which are real vanilla entries. So the same quest *type* appears under two
different folders and both display correctly. The folder is a merge point in the
journal tree, not a category.

Ash Cache keeps `quests/main_quest/prologue` — three independent mods prove it
merges — and keeps `type: SideQuest`, which is a real value of
`gameJournalQuestType` (the enum is extracted from the game by
`tools/refresh_enums.py`, not hand-written). No reference uses `SideQuest`
specifically, so if the entry lands in an odd tab, `MinorQuest` is the value with
three working samples behind it and the one-word change to try.

One thing this turned up that was worth more than the issue itself:
`journal.json`'s `districtID` is `Districts.Dogtown`, and it is **correct** —
confirmed against the game's TweakDB. Undermine ships `District.Watson`, which
does not exist (the real record is `Districts.Watson`), and works anyway. So a
bad TweakDB id here is silent, which is why `validate.py` now checks all of them
against the real TweakDB. See D11.

## OI-4 — `version: OptionalProperty` on optional objectives is inferred
**RESOLVED (2026-09-03, D27). Right output, wrong reason.**

`questJournalQuestEntry_NodeType` carries a `version` enum whose only two values
are `Initial` and `OptionalProperty`. No reference mod sets `optional` at all, so
there was no worked example, and `gen_questphase.py` emitted `OptionalProperty`
when `optional` was set and `Initial` otherwise, on the reasoning that *the enum
exists precisely to say whether that property is present*.

**Measured against every quest phase the game ships** — all 2,860 `.questphase`
files from `basegame_4_gamedata.archive`, deserialized in full rather than
grepped, holding **11,794** quest-entry nodes:

    optional   version             count
    0          Initial              9502
    0          OptionalProperty     2281
    1          OptionalProperty       11
    1          Initial                 0     <- never, not once

**The generator is right.** `optional = 1` implies `version = OptionalProperty`
in 11 cases out of 11, with zero counterexamples in the shipped game. Nothing
needs to change.

**The reasoning was wrong**, and it matters for anyone extending this. If the
enum meant "the optional property is present", it would never appear on a node
with `optional = 0` — and it appears on 2,281 of them. It is a **format stamp**:
nodes written by the newer editor carry it whether or not they use the feature,
which is what a node-version enum is for in a data-driven engine. So the
implication runs one way only. Do not read `version` to decide anything.

**Two things worth knowing that fell out of the same census:**

  - **The state is the socket, not a field.** A `questJournalNodeDefinition` has
    four input sockets — `Active`, `Inactive`, `Succeeded`, `Failed` — and which
    one you wire into is what sets the objective's state. There is no state
    property to get wrong. `gen_questphase.py` already models exactly this
    (`INPUTS["journal_quest"]`), and the graph's `_on` / `_done` node pairs wire
    `Active` and `Succeeded` respectively, which is q001's shape node for node.
  - **`questJournalQuestSetObjectiveOptional_NodeType` is dead.** Zero instances
    in 2,860 phases. It is the obvious-looking class for this job and the game
    never uses it; the flag on the entry node is the live mechanism.

**A design observation, not a defect.** The entire base game plus Phantom Liberty
marks an objective optional this way **11 times, in 4 files**
(`q001_ride_to_mb`, `q101_p2_meet_takemura`, `mq058_mint_hideout`,
`mq059_chase`). This mod does it 3 times, across two phases - `ac_obj_search_motel`
in `ac_ph1_signal`, `ac_obj_read_journal` and `ac_obj_open_cabinet` in
`ac_ph2_clinic`. (Corrected 2026-09-09: this said "5 times in one phase", which
counted graph NODES, not declarations - each optional objective has both an
activate and a succeed node, and `ac_obj_search_motel` has only the activate.
`source/journal.json` declares three.) That is not wrong - the
two optional clinic discoveries are the design — but it is worth knowing that
optional objectives are a rare construct in shipped content, so they are a thin
path and correspondingly less proven. Of vanilla's 11, seven pair `optional` with
`trackQuest: 0` and four with `trackQuest: 1`; this mod uses `track: false`
throughout, which is the majority shape.

**Still not verified in game (rule 8):** that an optional objective renders under
the "optional" header in the quest log. The UI reads
`JournalManager.GetIsObjectiveOptional()` — a native call, so the redscript dump
cannot say what backs it — and repaints on an `OnObjectiveIsOptionalChanged`
event, which confirms optionality is runtime-mutable state rather than a static
read of the `.journal`. Both halves are set here (the `.journal` marks the
objective optional and the node sets it again on activation), which is q001's
belt-and-braces shape too.

**The last open half is now answered, and the answer is "no header" (2026-09-08,
D50).** Rule 8 parked "does an optional objective render under the optional
header" as game-only. The game's own scripts settle it, and the premise was
wrong: there is no optional header.

  - `QuestDetailsObjectiveController.Setup` (`questLog.script:1084`) appends the
    localized `UI-ScriptExports-Optional0` in square brackets to the objective's
    title when `GetIsObjectiveOptional` returns true. That suffix is the entire
    visual treatment, and it is a vanilla LocKey, so `ua-ua` gets it translated
    for free.
  - `m_questDetailsPanel`'s `m_optionalObjectives` container is declared and
    cleared on every repopulate and **never filled** - every objective is spawned
    into `m_activeObjectives` (`questLogDetailsPanel.script:132`).
  - `questLogv2.script:186-198` looks like it sorts them: a three-way branch on
    `IsActive()` and `GetIsObjectiveOptional()`. All three arms assign the same
    `targetParent`, `m_ObjectivesListRef`.

So the three optional objectives here need no extra authoring and will read
`<title> [Optional]` in the same list as the rest. Worth recording as a general
warning too: two separate places in this UI look like they implement optional
sectioning and neither does. A container that exists is not evidence that
anything fills it.

**Fully closed in game (2026-09-08, D52).** `sc-new/sc_journal_ash_quest.png`
shows `ОБШУКАЙ РЕШТУ МОТЕЛЮ [НЕОБОВ'ЯЗКОВО]` in the quest log and the same
suffix in the on-screen tracker. Vanilla's `UI-ScriptExports-Optional0`, already
translated into `ua-ua` by the base game, appended inline by
`QuestDetailsObjectiveController.Setup`. Rendered in the same list as the
mandatory objective, no separate section. Nothing to author.

## OI-5 — Multi-connection socket semantics are assumed, not observed   **RESOLVED (2026-09-03, D28)**

The graph relies on two behaviours: an output socket with several connections
activates all of them (fan-out, used for the optional-discovery branches), and an
input socket with several connections fires on any one of them (OR-join, used
where the four endings converge and where the Hide gate's two paths rejoin). Both
shapes are present in the reference mods, so the format allows them. What was not
verified is the runtime semantics, specifically whether an OR-join re-fires its
node if a second connection arrives later.

**Measured** over a seed-27 random sample of 150 of the 2,860 vanilla
questphases, 3,524 nodes (`reference/graph_joins.md`):

- **238 input sockets carry more than one connection**, and only 38 of those are
  on a join node. **200 of 238 merges are a bare multi-connected input socket on
  an ordinary node** — the plain shape is the dominant vanilla idiom, not a
  shortcut this project invented.
- `questJournalNodeDefinition` is the fifth most common host for one (17 in the
  sample), which is exactly where both of this graph's merges land.
- Connections per socket reach **13**. This graph's widest is 5.
- `questLogicalHubNodeDefinition` is **not** the OR node: 73% of the 1,230 files'
  hubs are 1-in-1-out routing waypoints. There is no OR node class at all.
- `questLogicalXorNodeDefinition` (1,003 files) is the one purpose-built merge —
  always ≥2 inputs, always 1 output, never 1-in.

**The re-fire question is moot here, for a better reason than the old one.** Both
merges — `quest_done.Succeeded` (5 incoming) and `obj_decide_on.Active` (2) —
target a journal state change, and setting an entry Succeeded twice is the same
as setting it once. That holds even if a merge does re-fire, which the previous
argument ("nothing can deliver two activations") did not: it depended on the
branch conditions staying mutually exclusive as the graph grew.

Still unobserved, and now labelled rather than assumed: **whether XOR's name
matches its runtime behaviour.** Only its shape and frequency were measured. The
rule for extenders is in `reference/graph_joins.md` — merge on a bare socket when
the target is idempotent; route through XOR and test in game when it is not (a
counter, a reward grant, an item handout).

## OI-6 — Mara has no body   **RESOLVED (2026-09-01)**

Both halves are closed. `#ac_mara` is a real `worldStaticMarkerNode` in
`ash_cache_clinic.streamingsector` (D9), and she now has a record to be and an
actor to spawn her (D10):

    Character.ashcache_mara   $base Character.q306_fia_agent_corpo_scene_wa
    scnActorDef 0  spawnDespawn  ->  #ac_mara   appearance fia_undercover_01
    scnPlayerActorDef 1
    12 lines: Mara speaks 11 to V, V speaks 1 to Mara
    choice hub: attachToActor -> Mara

Verified from the PACKED resource, not the generator's intermediate: run
`python3 tools/dump_scene.py`, which joins line -> speaker -> actor and
line -> ruid -> subtitle text in one pass. `specCharacterRecordId` cooks to
`102920621884`, which is exactly `(len << 32) | crc32` of
`Character.ashcache_mara` — so the scene provably asks for the record
`gen_tweak.py` writes. Ten negative tests cover the new `validate.py` checks.

**What is still not verified is in-game behaviour, and it belongs to OI-10 and
the list below** — this issue was about the resources existing, and they do.

Two things to look at the first time the scene is played:

- Whether the appearance reads as Mara. `corpo__nusa_wa__q306__fia_undercover_01`
  is verified spawnable via AMM's database but has never been looked at in this
  context. `source/characters.json` carries three costed alternatives under
  `_alternatives`; swapping is a two-field edit and a rebuild.
- Which way she faces. The `yaw` on `#ac_mara` in `source/world.json` orients the
  scene, and that coordinate is one of the four unverified ones (OI-9).

## OI-7 — A choice node's output socket count is inferred   **RESOLVED (2026-09-02)**

`tools/gen_scene.py` emitted exactly one output socket per option, on the reading
that option *i* leaves by the socket whose `stamp.name` is *i*. Hot Fuzz's single
choice node has 1 option and 7 output sockets with only socket 0 connected, and
one sample could not say whether 7 is required or just what its author's editor
left behind.

Counting the other reference scene settles it:

    hot_fuzz.scene     1 option    7 output sockets    connected: [0]
    template.scene     1 option    7 output sockets    connected: [0]

Two mods, two authors, the same 7 — and in both, sockets 1..6 carry zero
destinations. That is the shape the editor emits, not litter one person left
behind. Padding was also always the safer direction: six unconnected sockets are
demonstrably tolerated, because both samples ship them; a *missing* socket has no
evidence either way.

Found while shipping D14, which was about to add two hubs with 3 and 4 options —
exactly the case this issue warned about. `CHOICE_SOCKETS = 7` had been sitting in
`gen_scene.py` since the file was written, with the reasoning above already in its
comment, and **was never read by any code**. Applying it is three lines. Every hub
now emits 7 sockets, carrying destinations on 0..N-1, which is a strict superset of
what shipped before; `gen_scene.py` refuses more than 7 options rather than
emitting an option that has nowhere to leave from.

Verified from the packed archive:

    ash_cache_decision.scene   options 3  sockets 7  connected [0, 1, 2]
    ash_cache_decision.scene   options 4  sockets 7  connected [0, 1, 2, 3]
    ash_cache_mara.scene       options 3  sockets 7  connected [0, 1, 2]

## OI-8 — Subtitle timing is a reading-speed guess
**HALF RESOLVED (2026-09-04). The guess now only applies to lines that have no audio.**

The premise of this issue was "with no VO, nothing anchors how long a line stays
up". That premise expires the moment a line HAS audio, and the RVC pipeline is
what produces it. So `gen_scene.py` now takes a line's duration from its
recording when one exists:

    "ms" on the line   ->  wins, always. The manual escape hatch.
    audio in vo/       ->  measured length + 250 ms tail
    neither            ->  55 ms/char of the longest locale, floor 1200 ms

The measured length is read straight off the RIFF header — no decoding, no
dependencies — which covers exactly the two formats this pipeline produces: the
`.wav` RVC emits, and the PCM `.wem` that `wav_to_wem.py` wraps around it. Both
measure a 4.000 s test file as 4000 ms. A compressed drop falls back to `ffprobe`
if it happens to be installed.

The longest recording across locales and both voice tags wins, for the same
reason the longest locale sets the reading pace: whichever one runs longest is
the one that would be cut off.

**Two silent failures were closed on the way, and they are the interesting part.**

  - The vo drop folder names files by the FULL subtitle key, `mara.mara_open_1`,
    while `line["id"]` inside the generator is the bare `mara_open_1`. The first
    version looked up the bare id, matched nothing, and would have left every
    voiced line on its guess **with no error anywhere**. `read_time` now takes
    the key as a required argument rather than deriving it, so a caller cannot
    quietly pass the wrong one.
  - A Vorbis or Opus `.wem` is audio this reader cannot measure. Left unsaid,
    such a line keeps its reading-speed guess while having a recording of a
    different length — and a subtitle two seconds short of its audio truncates
    the line. The build now says so by name.

**Still open:** the original two questions, which only the game can answer — whether
`duration` governs display time at all when there is no audio to match, and what
the engine does with the Undermine template's `sectionDuration` of 2501 against a
last line ending at 3500. Both now matter only for the unvoiced case.

**Checked and clear (2026-09-04): D42 does not under-time the Ukrainian subtitle.**
The worry was structural. OI-8's original design timed a line off the *longest*
locale precisely so "Ukrainian sets the pace"; D42 then took Ukrainian audio away
while keeping Ukrainian text, and `read_time` returns `max(MIN_LINE_MS, audio +
VO_TAIL_MS)` with the character count no longer in the expression at all. So every
voiced line's duration now comes from the English take, and if a ua-ua subtitle
needed longer than its English audio it would be cut — the exact failure OI-8 says
it errs against ("erring long costs a beat of silence, erring short eats a
subtitle"). Measured instead of argued, against the 11 real en-us renders still in
`rvc_logs/audition/en-us/`:

  - English speech runs **70-120 ms/char** (mean 78.6). Subtitle reading speed is
    `MS_PER_CHAR = 55`. Speech is slower than reading by construction — 55 ms/char
    is ~200 wpm, ordinary delivery is ~150 — so the audio a line sits over
    generally outlasts the time its subtitle needs to be read.
  - Extrapolating the **fastest** measured rate (70 ms/char, the worst case for a
    long subtitle) over all 43 lines: **0** lines where the longest locale needs
    more time than its English audio will occupy.
  - The premise itself does not hold for this script. The ua-ua/en-us character
    ratio across the 43 lines is **median 1.00, mean 0.97**, range 0.62-1.32.
    Ukrainian is not systematically longer here; English carries more short
    function words and it comes out even. (The 48%-longer figure recorded under
    OI-16 is ua-ua *audio* against en-us audio — an espeak delivery rate, not a
    text length, and irrelevant now that ua-ua audio is not used.)

**The margin is thin, though, and that is the part to remember.** Per line it is
not the aggregate rate that decides, it is that line's own ua/en ratio:

    ratio  line                    audio~   needs   en   ua
     1.05  mara.opt_break_j        3400ms  3245ms   45   59
     1.05  mara.hostile_1          2840ms  2695ms   37   49
     1.10  mara.deal_3             7530ms  6875ms  104  125

`mara.opt_break_j` clears its Ukrainian subtitle by **155 ms**. So the correct
statement is not "safe by construction" but "safe on this text, measured, with
about 5% to spare on the tightest line". Two things would break it: a ua-ua line
rewritten appreciably longer than its English, or a delivery faster than the 70
ms/char floor seen here. Both are visible — `tools/gen_scene.py` prints `N of M
line(s) timed from real audio`, and any such line can be pinned with `"ms"`.
Adding the reading-speed floor back as a third `max()` term in `read_time` would
close it permanently, at the cost of a beat of silence after the English take on
those three lines; not done, because on measured data it would change nothing
today and OI-8's escape hatch already covers the case that it would.

The original text follows.

With no VO (D2), nothing anchors how long a line stays up, so `gen_scene.py`
computes it: 55 ms per character of the longest locale, floor 1200 ms, 250 ms
between lines, and a `sectionDuration` long enough for the last line to finish.

Two things are unverified. First, whether `duration` even governs display time
when there is no audio to match. Second, the Undermine template ships a
`sectionDuration` of 2501 with a line that starts at 2500 and runs 1000 — the
section ends a thousand milliseconds before its own last line — which suggests
the engine either extends the section or truncates the line, and which of those
it does matters. This generator errs the other way on purpose: erring long costs
a beat of silence, erring short eats a subtitle.

Timing off the *longest* locale means Ukrainian sets the pace and English lines
sit on screen longer than an English reader needs. That is deliberate, and any
line can override it with `"ms": <n>`.

**Half of the first open question is answered (2026-09-08, D50).** "Does
`duration` govern display time at all?" — not in the UI layer, and that was
checkable without the game. `scnDialogLineData.duration` exists, and its only
consumer in the entire script tree is `SetupAnimation`, which sets the length and
delay of the Kiroshi text-reveal animation (`baseSubtitlesControllers.script:643-
686`). Nothing in the subtitle controllers holds a timer: a line appears on a
`ShowDialogLine` blackboard push and leaves on a `HideDialogLine` push, both from
the scene system. So a subtitle's lifetime is the scene section's event schedule,
which is what this generator computes — the value is not ignored, it just is not
read where it looked like it would be. The remaining unknown is unchanged and
still native: what the section does with a last line that outruns
`sectionDuration`.

## OI-9 — Half the marker coordinates are hand-derived offsets

`source/world.json` anchors each sector on a position vanilla itself vouches for,
so those two are known-standable points in the real geometry:

    ac_motel_entrance    AMM "Dogtown Apartment"            (-2240.04, -2553.28,  80.30)
    ac_clinic_entrance   vanilla {loc_q303_macs_clinic_gps} (-1891.75, -2486.90,  28.00)

The other four (`ac_motel_room7`, `ac_clinic_terminal`, `ac_splinter_case`,
`ac_mara`) are offsets of a few metres from those anchors, chosen on paper. None
of them has been stood on. They are quite possibly inside geometry, and the motel
room is a guess at "one floor up and inside" with no floor plan behind it.

Nothing here is structural — every coordinate is one number in one JSON file and
`tools/build.sh` regenerates the sectors — so this is a content pass, not a
rework.

**The clinic anchor moved on 2026-09-02 (D19).** It used to be AMM's "Cynosure
Core" at (-2072.92, -2205.73, -194.78). That was real geometry, but it is 275m
underground inside the Phantom Liberty mission space, so the only way into Act 2
was a teleport. It is now vanilla's own ripperdoc shopfront in Dogtown, which the
player walks into off the street.

**What is known about that room** — all read out of the shipped sectors, none of
it stood on:

    GPS entrance marker      -1891.75  -2486.90  28.00   {loc_q303_macs_clinic_gps}
    front door               -1899.80  -2477.14  24.06   DoorController isLocked 0, isSealed 0
    door intercom            -1900.80  -2478.65  25.58   {q303_dvc_farida_door_intercom}
    interior volume          -1901.54  -2476.47  23.60   {q304_Farida_interior_area}
    surgery benches/monitors  x -1907..-1917  y -2465..-2473   z 24.9..26.6
    floor-level geometry      x -1919.5..-1899.5   y -2478.1..-2465.0   floor z ~24.1

So: a room roughly 20m x 13m, entered at its south-east corner four metres below
street level, with the surgery in the north-west half. Our four markers are laid
out to keep at least 3m clear of every vanilla prop, which is a paper clearance —
props have volume and a position is a point.

**How to correct them:** in game with AMM open, walk in off the street, stand
where the marker belongs and read the player position off AMM's teleport panel,
then paste it into `source/world.json` and rebuild. Do the clinic first: four of
the six markers are there, and it carries the scene origin, whose `yaw` also
decides which way Mara's conversation faces.

**One thing is still unverified, and it is the only one that matters:** whether
that front door opens outside q303/q304. Its authored state is unlocked and
unsealed, and it lives in an ordinary streamed sector rather than a Quest-category
one — but a quest can lock a door at runtime and nothing in the files rules that
out. Walking up to it settles it in ten seconds. If it turns out shut, the anchor
moves again and nothing else in the project does.

**Do the OI-13 probes on the same trip.** Three probe sectors put a trigger, a
computer, a car and an FIA agent on the clinic anchor — the VERIFIED one, and now
also an outdoor one, which is what a car spawner needs — precisely so that a
missing object is not confused with a bad coordinate (D15, D16). All of it is
answered standing in the same spot, and the CET Surveyor tab teleports to each
node and says what each outcome would mean.

**Before doing any of it, read the Status tab** (D18). Four of the six markers
being wrong and the archive never having mounted look the same from the clinic
floor - an empty room either way. The Status tab separates them in one glance,
and `python3 tools/collect_logs.py` says the same thing from the loaders' side
without the game needing to be running.

### 2026-09-03 — confirmed wrong in game, and the fix is now mechanical

The player teleported to each marker and reported what was there: `ac_motel_room7`
lands in the `ac_clinic_entrance` texture, `ac_clinic_terminal` puts you down the
stairs by the core, `ac_splinter_case` is inside a wall, `ac_mara` is in a pipe.
So the four derived offsets are all wrong, not merely unverified, and this now
**blocks OI-13**: authoring the black box prop against a coordinate that is inside
a wall would waste the authoring.

The Surveyor tab used to hand back one coordinate at a time as a text block to
paste into `source/world.json` by hand. It now has, per marker, a **go** button
(teleport to where the marker currently thinks it is) and a **set** button
(overwrite it with where the player is standing), plus **write markers.txt**,
which emits the exact JSON each `world.json` entry needs, for every marker that
was actually captured. Markers nobody stood on are omitted rather than written at
their current value — a coordinate nobody stood on must never come back labelled
`verified`.

So the whole of OI-9 is now: walk to each of the four places, press set, press
write, send back one file. No JSON edited by hand and nothing transcribed.


**Seven of ten captured, three still outstanding.** (2026-09-03) A CET surveyor
capture (`markers.txt`) supplied real stood-on positions for
`ac_motel_entrance`, `ac_clinic_entrance`, `ac_clinic_terminal`, `ac_mara`,
`ac_probe_trigger`, `ac_probe_computer` and `ac_probe_npc`. Every one of them is
right. Every one of the three derived by offsetting is wrong: `ac_splinter_case`
was inside solid rock, `ac_motel_room7` inside a parking garage under the motel,
`ac_probe_car` unreachable. That is a clean 7/0 against 0/3, which is why
`validate.py` now records provenance rather than trying to test geometry.

The screenshots also settled the clinic's real shape: street level is Z≈28, a
stairwell drops to Z≈24, and *both* the ripperdoc interior and an outdoor plaza
sit at Z≈24 on opposite sides of one wall. `loc_q303_macs_clinic` is genuinely
enterable with no q303/q304 progress.

**What is still needed, and only you can do it.** Teleport to
`ac_motel_entrance` (verified), walk to room 7 on foot, press **set**. Same for
`ac_splinter_case` (walk in from `ac_clinic_terminal`, which is verified) and
`ac_probe_car`. Until then the build prints `7/10 position(s) stood on` and
`check_verified` errors on any scene origin or character spawn that is not
verified — because those two fail silently and unrecoverably, while a marker in
a wall merely puts a map pin somewhere stupid.

### 2026-09-09 - CLOSED. All ten positions stood on.

`source/world.json` now carries `"verified": true` on every one of the ten
markers, and three of them (`ac_motel_room7`, `ac_splinter_case`,
`ac_probe_car` - exactly the three this issue said were outstanding) carry
`"stood on in game 2026-09-06, CET Surveyor capture (ash_cache_debug/markers.txt).
Replaces a DERIVED value."` `tools/validate.py` confirms it independently:

    10/10 position(s) stood on

So the paragraphs above that say "Seven of ten captured, three still outstanding"
and "the build prints `7/10 position(s) stood on`" are history, not status. They
are left in place because the 7/0-against-0/3 result is the reason `validate.py`
records provenance instead of trying to test geometry, and that reasoning is
still load-bearing.

**This also re-reads a screenshot.** `sc/ac_splinter_case_under_texture_sc.png`
shows V under the world with the whole city rendered inverted overhead and the
objective marker 325 m off. That is not an open bug: the filename names
`ac_splinter_case`, this issue records that marker as having been "inside solid
rock" before the 2026-09-06 capture, and teleporting into solid collision is
precisely how CP2077 ejects the player downward. The photograph documents the
defect that capture already fixed. Nothing to do.

**What this unblocks.** OI-9 was blocking OI-13 - authoring a prop against a
coordinate inside a wall would waste the authoring. That block is gone. OI-13 is
now gated only on its own question (does an interactable prompt appear at
`#ac_probe_computer`), and a missing prompt there can no longer be blamed on the
coordinate.

## OI-10 — Lipsync index dangled into an empty table   **RESOLVED (2026-09-02)**

`tools/gen_scene.py` used to emit `lipsyncAnimSet: 0xFFFFFFFF` against an empty
`resouresReferences.lipsyncAnimSets`, on the reasoning that `0xFFFFFFFF` is the
sentinel every other unset id in this format uses. It is — for `scnActorId`,
`scnPropId` and `scnReferencePointId`. An `SRRefId` is an array index, and whether
the engine sentinel-checks one before dereferencing was a claim about code nobody
here has read. With no VO (D2) nothing drives lipsync, so the risk was never "her
mouth does not move", it was "the engine dereferences the id while setting the
actor up" — a crash on spawn, at the exact moment the scene opens.

Re-reading the references settled it, and the invariant is sharper than this issue
originally recorded:

    dialog_only_template   1 actor  (player 0)                      1 entry
    template.scene         2 actors (songbird 0, player 1)          2 entries
    hot_fuzz               4 actors (judy 0, Nibbles 1, Johnny 2,   4 entries
                                     player 3)

Seven actors across three independent scenes, and in every single case the table
is exactly as long as the cast and actor N carries `lipsyncAnimSet.id == N`. That
includes Nibbles and Johnny, who ship `animSets: []` *and* a valid lipsync id at
the same time — which is what separates the two claims this issue used to conflate.
An actor carrying no animation of its own is observed and fine. An actor indexing
nothing is observed nowhere.

**What ships now:** one entry per actor, indexed by actor id. The paths are
`template.scene`'s own two, in its own order, because its cast is exactly this
mod's — one NPC at 0, the player last. They point at a Japantown vendor's lipsync
anims, which is not a mistake being copied: that template is a *songbird*
conversation, so those paths do not match its actor either, in the same way its
`cinematicAnimSets` point at the unrelated quest it was cloned from. Wrong-but-
resolving references are demonstrably tolerated here; absent ones had no evidence.
The refs are `Soft`, so they are load-if-present, not packing dependencies, and
they name base-game paths that are present anyway.

Verified from the packed resource: `python3 tools/dump_scene.py` now resolves each
actor's lipsync index to a filename and prints `<<lipsync N of M>>` if it ever
points past the end of the table.

    actor 0  Mara     lipsync civ_prst_f_01_enus_30.anims
    actor 1  Player   lipsync v.anims

**Still not verified:** `animSets: []` on Mara. That one *is* observed (Nibbles,
Johnny), so it is not carrying the same risk — but neither of those two is the
actor a scene attaches its choice hub to. If Mara T-poses rather than crashing,
this is where to look, and the fix is the same shape: copy a vanilla
`cinematicAnimSets` entry and index it.

**Postscript (2026-09-03) — this table is not the lipsync binding at all.**
Investigating OI-17 turned up the actual chain, and it does not run through
`resouresReferences.lipsyncAnimSets`. The engine finds an actor's mouth animation
through the per-locale `.lipmap`, keyed on the actor's `voicetagId` and the FNV1a64
of the scene's depot path. Better still, it retro-justifies the decision above:
vanilla's own `mq029_01a_garage.scene` points its lipsync table at
`base\quest\minor_quests\mq029\scenes\lipsync\...\johnny.anims` and
`...\v.anims`, and **neither path ships** — `scenes\lipsync` returns zero hits
across every archive listing. Vanilla's entries dangle too. Pointing at arbitrary
resolving paths was not merely tolerated; it is what the shipped game does.

## OI-11 — Nothing despawns Mara if the player walks out mid-scene   **RESOLVED (2026-09-03, D28). The premise was wrong.**

The actor is `alwaysSpawned: 1` + `spawnOnStart: 1`, so she is standing in the
clinic the moment the scene starts, and the scene takes her away when it ends.
That is the right shape for a confrontation the player walks into.

The worry was the exit: `interruption_scenario()` pauses the conversation when
the speakers get more than 6 m apart and resumes under 5 m, but nothing ends the
scene if the player simply leaves. The interruption pause is indefinite, so a
player who walks away leaves Mara paused mid-sentence in an underground clinic
until they come back. This issue asked for a distance-based exit or a timeout,
and noted that neither had a worked example.

**There is no worked example because the game does not do it.** Measured across
all 2,860 vanilla `.questphase` files (`reference/interruption.md` has the method
and the negative controls):

- `questSceneInterrupt_ConditionType` and `questSceneReturn_ConditionType` — the
  two RTTI classes that look purpose-built for "wait until this scene is
  interrupted" — are authored **zero times**. Dead classes.
- A scene node's `Default INT` / `Default RET` outputs are wired in **13 of the
  128 interruption-aware phases**, 15 connections each way, and every one of them
  is the same four nodes: a 500 ms `questRealtimeDelay_ConditionType`, then
  `questSetTier_NodeType` to `Tier1_FullGameplay`.
- Nothing in the game routes an interruption to a cleanup, a despawn or a cut.

So the indefinite pause is vanilla behaviour, not a defect of this graph. Any
vendor, Viktor Vector, or Wakako Okada behaves the same way. **No change made.**

**One thing did come out of it, and it is a trap for later.** The INT wiring
vanilla does ship is a *tier safety net*: a player interrupted out of a
constrained-movement conversation is handed back full gameplay control after half
a second. `tools/gen_scene.py` never changes tier — both scenes run at
`Tier1_FullGameplay` throughout — so that net would be a no-op here and is
deliberately not built. **If anyone adds a tier change to a scene, they must wire
`Default INT` and `Default RET` to the four-node pattern at the same time**, or an
interrupted player can be left unable to move. The generator already emits both
sockets, unconnected, so this is wiring and not new node types.

Also confirmed while measuring: the inherited 6 m / 5 m distances are not a
guess that happened to survive. Across the 128 phases, `Greater 6` is the second
most common interrupt distance in the game and `Less 5` is the most common return
distance. The hysteresis gap is universal — no sampled scene uses one number for
both.

## OI-12 — Ten facts gate the graph and nothing in this repo sets them   **HALF RESOLVED (2026-09-02)**

The difference between "the quest's resources exist" and "the quest can be played".
Ten facts were declared under `world_triggers` and `discoveries` — which is exactly
right, the graph is supposed to wait and something outside it is supposed to set —
and nothing set any of them, so a player who installed the mod got a quest that
never started: `await_start` blocked on `ashcache_start` forever.

Five are now set, by the glue layer described in D13. `source/glue.json` declares
them and `tools/gen_glue.py` generates
`mod/r6/scripts/AshCache/AshCacheGlue.reds`:

    start               a QuestsSystem listener on the vanilla fact q304_done
    at_motel            proximity to a world.json marker, armed only during act 1
    at_clinic           the same, act 2
    courier_log_played  journal Visited callback on the shard's onscreen entry
    journal_read        the same

Every engine API in that file is type-checked against the game's own compiled
script bundle by `tools/lint_glue.sh`, which `build.sh` runs. That is a stronger
guarantee than this project could previously make about a script API, and it paid
for itself on the first run — see D13 for the two constructs it rejected that a
shipping reference mod and decompiled vanilla respectively still use.

The prerequisite fact `q304_done` was not guessed. `reference/facts.md` records
both confirmations: the game's own `mq304.questphase` waits on it with a
`questVarComparison_ConditionType`, and an installed mod gates on it independently.

**What is left is not glue.** The remaining five need a thing in the world that
nobody has authored — a prop to open, a terminal to read, a locked cabinet, an
encounter to survive, a choice hub. `world.json` generates marker nodes only (D9):
empty named points, no geometry and no entity. That is now OI-13.

`validate.py` prints the remaining five on every run, each with what it needs, and
fails the build if `glue.json`'s own list of them stops matching what is actually
left over — so the file cannot quietly stop describing reality.

## OI-13 — Four facts need world content that does not exist yet

**Half of this is answered, and the answer was pre-registered. (2026-09-09, D68)**

The player: *"The same with the terminal. There was no action with it at all,
and the same with the textures."* `world.json` had already written down what
that would mean, on `ac_probe_computer`: *"If it appears but is inert, they need
the buffer."*

They need the buffer. A `worldEntityNode` with `instanceData` null has no
`ComputerControllerPS`, so nothing holds `isInteractive` and nothing holds
`tweakDBRecord: Devices.Computer` - the device has no device in it. That is one
defect, not two: the bare screen plane with no computer body and the missing
interaction prompt are both "there is no controller state here".

`reference/device_computer.instancedata.json` is vanilla's buffer for this exact
`.ent`, appearance and node type, extracted verbatim from
`quest_73110a178d6e7404`. `ac_splinter_box` and `ac_terminal_pc` carry it now;
`ac_probe_computer` keeps its null one and has become the control.

What is NOT answered: whether the prompt now appears, and whether the model
still draws as a bare plane once the device record is there. Those are one walk
across the clinic. `terminal_read`, `box_opened` and `cabinet_opened` are the
three facts riding on it.

**UNBLOCKED (2026-09-08, D46/D47). Both probe questions answered off the
screenshots, all ten coordinates stood on, and the last unbuilt node type is
built. What is left is authoring, not research.**

### Status, 2026-09-08

| | was blocked on | now |
|---|---|---|
| `cleanup_done` | does a spawner take a `Character.*` record | **yes** — the probe agent is standing (floating) at the clinic entrance, D46 |
| `terminal_read` | does a device `.ent` with `instanceData: null` appear | **yes, and its screen is live** — the interaction prompt is the only untested half, D46 |
| `box_opened` | a verified coordinate + a container + its contents | coordinate stood on 2026-09-06; `questInjectLoot_NodeType` built and round-tripped, D47 |
| `cabinet_opened` | same as `box_opened`, plus whatever unlocks it | same |

**Both anchors sit inside dressed, populated vanilla interiors** (screenshots
`sc_ac_mara`, `sc_ac_motel_room7`, `sc_splinter_case`, 2026-09-08). The clinic at
Z 24.06 is real tiled geometry with glass partitions, and `#ac_mara` is 1.9 m from
`#ac_splinter_case` — so Mara standing at the desk the box is on is coherent, but
the space is tight enough that the scene's actor placement is worth eyeballing
before it is called done. The motel anchor is a dressed squat with **vanilla NPCs
seated ~20 m away**. That is a live constraint on `cleanup_done`: an FIA firefight
authored into a room that already holds civilian population is a design problem
before it is a technical one, and it is the reason to pick the encounter's spot
deliberately rather than reusing an existing marker.

The one remaining measurement is ten seconds of play: **walk up to the computer
at `#ac_probe_computer` and see whether an interaction prompt appears.** If it
does, all three device-shaped facts are a depot path and a transform each. If it
does not, they need the `instanceData` buffer transcribed from a vanilla sample —
expensive but bounded, and nothing about the placement changes either way.

The historical blocker note is kept below because the reasoning that produced the
probes is what made them decisive.

> **Blocked by OI-9 as of 2026-09-03.** The player went looking for the black box
> and found nothing, which is correct: `world.json` generates marker nodes only,
> so there is no prop at `#ac_splinter_case` to find. But `#ac_splinter_case` is
> also one of the four coordinates confirmed wrong that day — it is inside a wall.
> Authoring the prop first would place it inside that wall. Capture the four
> coordinates (OI-9 is now a four-button job in the Surveyor tab), then author.

Carved out of OI-12. These are the beats of the quest that have a journal
objective, a map marker and a graph node waiting for them, and no object in the
world to make them happen:

    box_opened       an interactable prop at #ac_splinter_case - the black box V opens
    terminal_read    an interactable computer at #ac_clinic_terminal, plus its log text
    cabinet_opened   the optional FIA-locked cabinet, plus whatever unlocks it
    cleanup_done     the FIA cleanup encounter: spawn nodes, an enemy group, an end condition
    decision_made    DONE (D14) - source/scene_decision.json

Three of them are on the main spine (`box_opened`, `terminal_read`, `cleanup_done`),
so each is a hard stop rather than a missed optional beat. `cabinet_opened` costs
content rather than progress.

**None of them should be faked in the glue layer.** A stubbed fact advances the
quest past a beat that never happened, silently, and the player has no way to tell
that is what occurred. They are listed under `blocked` in `source/glue.json` with
what each needs, and `validate.py` fails the build if that list and the real
leftovers ever disagree.

**`decision_made` is done.** It was the one that needed no new engine surface: a
second `.scene`, which this project already generates. See D14.

### What is no longer blocking (D15)

`gen_sector.py` used to write `worldStaticMarkerNode` and nothing else, so all four
shared one blocker: no way to put an object in the world. It now writes four node
types, every field measured off a real file. `reference/sectors.md` is the table.

The measurement that mattered most: **`instanceData` can be null.** It is the
RedPackage carrying ~200 fields of per-instance controller state and it is what made
placing an entity look expensive. Vanilla `quest_73110a178d6e7404` places
`base\entities\covers\left_sided_low_cover.ent` with `instanceData: null`, two
nodes after placing a computer that does carry a buffer. So the buffer is an
override, not a requirement — for a prop with nothing to override, placing an
object is a depot path and a transform.

This also corrects an earlier note in this issue. It used to say "no vanilla
computer-terminal `worldDeviceNode` sample". There is none because a vanilla
computer **is not a `worldDeviceNode`** — mq058's is a `worldEntityNode` pointing at
`base\gameplay\devices\masters\computers\computer_1.ent`, appearance
`computer_computer_2_angle_15`. Sixteen EP1 *interior* sectors reference no device at
all; interiors are geometry, and every device in EP1 lives in a `quest_*` sector.
698 of those were extracted, and they hold 133 `worldDeviceNode`s.

### The questions left, and neither is answerable headless

**1. A vanilla device `.ent` placed with `instanceData: null` — does it appear, and
can it be used?** Three outcomes, and they decide the cost of three of the four facts:

    appears, and can be used   -> terminal_read, box_opened and cabinet_opened are
                                  all cheap: a depot path and a transform each.
    appears, but is inert      -> devices need the buffer. Expensive but bounded -
                                  transcription from a sample, not research.
    nothing appears            -> a mod-authored .ent is required after all.

**2. Does `worldPopulationSpawnerNode.objectRecordId` accept a `Character.*`
record?** This is the last thing standing between `cleanup_done` and being
authorable, and it is asked as a controlled pair rather than on its own:

    car appears, agent appears   -> cleanup_done is authorable today
    car appears, agent does not  -> the crew needs a .community; nothing here has one
    car does not appear          -> ignore the agent result: the spot or the node
                                    failed, and this says nothing about records

**Three probe sectors ask these**, shipped and waiting, all standing on
`#ac_clinic_entrance` — a VERIFIED coordinate, so a node that is missing failed for
its own reasons rather than because it was placed inside a wall:

    ash_cache_probe       a trigger and a computer .ent with instanceData null
    ash_cache_probe_car   a Vehicle spawner - the control for question 2
    ash_cache_probe_npc   a Character spawner - Character.q305_fia_agent

Three sectors rather than one because a malformed node takes its own sector down
with it, and a `Character` record loud enough to invalidate a sector must not be
able to take the control down with it. All of them set `spawnOnStart` so they
appear on their own with no graph behind them — D15's single probe did not, which
made it a test of "does this break the sector" rather than of "does this work".
See D16.

Teleport to each from the CET Surveyor tab; the panel names the three outcomes at
each one. Delete all three sectors once this issue closes.

### The graph side is built

Counted across the extracted q304 questphases, read field by field, and now emitted
by `gen_questphase.py`:

| you want | source | emits |
|---|---|---|
| the player used it | `{"interaction": "#node"}` | `questObjectCondition` / `questInteraction_ConditionType` |
| a device says so itself | `{"device": "#node", "controller": "DoorControllerPS"}` | `questObjectCondition` / `questDevice_ConditionType` |
| they exist yet | `{"spawned": "#node"}` | `questCharacterCondition` / `questCharacterSpawned_ConditionType` |
| N of them are down | `{"killed": "#node", "count": N}` | `questCharacterCondition` / `questCharacterKilled_ConditionType` |
| switch a spawner or community on | `{"type": "spawn", "actions": [...]}` | `questSpawnManagerNodeDefinition` |

`count` is required and has no default: both vanilla kill conditions name an
explicit number, and the `Greater 0, entireCommunity 1` shape used by the *spawned*
condition would, on a kill condition, end the fight on the first body.

`tools/shapetest.py` round-trips one of each through WolvenKit to CR2W and back and
reads the fields out of what returned, because a node whose payload is subtly wrong
deserialises fine, packs fine, ships, and then does nothing.

`validate.py` walks the graph for the world nodes it names and fails the build on
one that no sector places — a condition aimed at a node that was never placed never
becomes true, and the quest stops there in silence.

**Built on 2026-09-08 (D47)** — `inject_loot` in `gen_questphase.py`, round-tripped
through CR2W by `shapetest.py`, with both halves of the items cross-check held by
`negtest.py`. The paragraph below is the measurement it was built from and is kept
as the record of where the shape came from.

`questInjectLoot_NodeType` is what puts the shards inside a
container rather than straight into the player's inventory. Not needed until
there is a container — but **it no longer needs to be guessed** (2026-09-03). The
game uses it 317 times across 177 quest phases, and a complete deserialized node
is kept at `reference/examples/questInjectLoot_node.json`, taken from
`ma_std_arr_10_phase.questphase`. The shape:

    questInjectLoot_NodeType
      params[] -> questInjectLoot_NodeTypeParams
                    lootOperations[] -> questInjectLoot_NodeTypeParams_OperationData
                                          itemTDBID      Items.<id>
                                          operationType  Inject
                                          quantity       1
                    objectRef -> questUniversalRef
                                   entityReference.names[0]   ganger_001
                                   entityReference.reference  #ma_std_arr_10_com
                                   refLocalPlayer             0
                    operations[]                              (empty, legacy)

Two things in there are worth reading twice, both of them the same class of trap
as `questAddRemoveItem`'s `isPlayer` (D12). `refLocalPlayer` is **0** here — the
opposite of the add-item node — because loot goes into a *world object*, not the
player. And the target is addressed twice over: a `NodeRef` to the sector node
(`#...`), plus a `names[]` entry selecting the entity within it. `operations` is
a second, empty array beside `lootOperations`; vanilla leaves it empty and so
should we.

### Why `cleanup_done` is still stuck, specifically

The chain is verified end to end except for one link. `questSpawner_NodeType`'s
target was checked rather than assumed: `#sa_ep1_37_car_01` in
`ep1_mq304_airdrops.questphase` resolves to a `worldPopulationSpawnerNode` of that
name in `quest_e495c59e9949e75b`, shipping `spawnOnStart: 0`.

What is missing is the enemies. **Every `objectRecordId` in every vanilla quest
sector is a `Vehicle.*`** — across 698 sectors, not one mentions `Character.`, because
vanilla NPC groups come from communities (`questCommunityTemplate_NodeType`, 40 uses
in q304) and a `.community` is a resource type no mod in `questmod-research/` ships.
Under rule 8 that stays a guess until `ash_cache_probe_npc` is looked at.

Also worth knowing before designing the encounter: vanilla does **not** end a fight
on a kill condition. `q304_transmitter_tower_02` is spawn -> spawned -> **fact**, and
`questCharacterKilled` appears exactly twice in everything extracted, both times as
`GreaterOrEqual N` against a named community. So `cleanup_done` needs either a known
enemy count or something else to signal the end.

### A fifth fact rides on the terminal   (added 2026-09-02, D17)

`ashcache_terminal_full_read` is not one of the four — the graph never waits on it,
so it does not stall anything — but it is blocked by the same missing object. The
completionist read of the clinic terminal cannot exist before the required read
does, and `ashcache_terminal_read` is item two on the list above.

This was previously written up, here and in `docs/quest_design.md`, as authoring
work waiting on nobody. It is not, and the recipe it unlocks turned out to have two
unmeasured pieces of its own — see `reference/crafting.md`, which does record the
recipe *record* shape in full, measured off the shipped TweakDB, so that when the
terminal is real the remaining work is small and known.

### The Character-in-a-spawner question may already be answered   (2026-09-03)

The player, testing the **pre-relocation** build, teleported to each probe marker
and reported what they found. Two of the ten lines matter:

    ac_probe_car   "teleports to the car inside the lab where the [Blackwall] core is"
    ac_probe_npc   "teleports to the annoying npc at the desk with computers"

`ac_probe_car` is `Vehicle.hackable_thorton_galena` — the control. `ac_probe_npc`
is `Character.q305_fia_agent` — the variable, and an FIA agent at a desk in the
Blackwall control room is exactly what it would look like if it worked. If both
of those were ours, a `worldPopulationSpawnerNode` accepts a `Character` record
and `cleanup_done` becomes authorable.

**Not banked.** The player flagged the report as possibly stale themselves, and the
old anchor sat inside Cynosure, which has its own vehicles and its own hostile
NPCs — a coincidence is entirely possible at that spot.

The relocation makes the test decisive for free. The probes are now outdoors on a
Dogtown street at the clinic entrance, where no vanilla Galena and no vanilla FIA
agent stand. Walk to `#ac_clinic_entrance` in the current build: a sedan six metres
to one side and an FIA agent four metres ahead are ours or they are nothing.

### Ordering against OI-9

Three of the four hang off markers OI-9 has not verified (`#ac_splinter_case`,
`#ac_clinic_terminal`, and wherever the cleanup happens). So the *placement* waits on
OI-9 — but the node shapes, the graph shapes and the generator do not, and those were
the bulk of the work. D14, D15 and D16 are all proof of that split: each was carved
out of this issue and finished headless.

### 2026-09-09, later the same day: the buffer went in, the game crashed, the buffer came back out

The answer above is still the answer — a device with no `instanceData` is
scenery, and vanilla's buffer is what makes it a device. What is now in doubt is
whether *that* buffer, copied into *this* sector, is safe.

Twenty-three minutes after the build carrying it was deployed, the player
crashed standing 12 m from `ac_splinter_box`: `0xC0000005`, read at
`0xFFFFFFFFFFFFFFFF`, on `redDispatcher1` — a worker thread, so not the CET
click that preceded it. Two crash signatures that appear nowhere in the 27 crash
logs on that machine showed up in the two sessions after the deploy, and in
neither of the three before it.

That is a correlation on a machine with 3,081 archives, not a proof, and the
same deploy also put 29 `scnAudioEvent` into the two scenes in that same room.
**Both computers are off** (`"device": null`) so the next walk says which of the
two it was. D69 has the full evidence, including the five hypotheses killed on
the way — the CruidDict, the HandleId renumbering, the appearance name, dangling
links in the buffer, and memory.

If the buffer turns out to be the fault, the first thing to look at is not the
buffer at all: our sector is `category: "AlwaysLoaded"`, `level: 0`, and
vanilla's device sector is `category: "Quest"`, `level: 255`. An always-loaded
sector is not torn down when the player reloads a save inside one session — and
the player did exactly that, at 15:46:53, four minutes before the crash.

`ac_probe_computer` stays. It was the null-buffer control and it now has nothing
to be a control *against*, but deleting it would cost the one node in this
project that has been watched rendering in that room.

### 2026-09-09 16:31 - the bisect ran and the buffers are back on

D69's walk happened. With both device buffers OFF the game still crashed twice
in 15 minutes (16:15 redDispatcher10, 16:29 the CET GameThread one), and the
16:15 signature E4044E73 is the same one this install threw at 11:33 and 11:34 -
hours before the buffer existed. Crash rate: 2-in-25-min with it, 2-in-15-min
without. No separation. On this machine a worker-thread AV every 10-20 minutes is
the baseline.

Both switches in world.json are back to "computer". Also cleared on the way: the
doubt that a device needs a `worldDeviceNode`. The only vanilla node in the whole
extracted corpus that carries a device controller state is a **worldEntityNode**
(quest_73110a178d6e7404 node 12). Node type is right.

If the terminal is still inert with the buffer on, the next two differences from
that vanilla node are `sourcePrefabHash` ("0" vs 751022378267559076) and
`CookedPrefabData` (null vs a real .cookedprefab). See D70.

### 2026-09-09, second test: the authoring is cleared, the runtime is not

Both device buffers went back on in D70 and the terminal is still inert. This
round eliminated the authoring as a cause rather than guessing at it again:
`ac_terminal_pc` is field-for-field the vanilla mq058 computer (node 12 of
quest_73110a178d6e7404) apart from its debugName, its HandleIds, and the three
prefab marks - `sourcePrefabHash`, `CookedPrefabData`, `QuestPrefabRefHash`. Its
`ComputerControllerPS` reports `isInteractive 1`, `deviceState ON`,
`tweakDBRecord Devices.Computer`. `Uk10` differed by one bit (1312 vs 288) and
was killed by census: four of the five vanilla worldEntityNodes in the corpus
carry exactly our 288.

So the fault is in what the runtime makes of a correctly authored node, which no
offline diff can see. `tools/gen_cet.py` gains a **Devices** tab: a look-at probe
over vanilla `GetLookAtObject` reporting class, EntityID, whether `GetDevicePS()`
returns anything, and the device's state/power/actions. It changes nothing and
needs no save. Its three outcomes point at three different fixes - see D71.

The user's own hypothesis ("this clinic needs to be unlocked ... no unlocked
doors and the premises themselves") is now the leading one and the probe tests it
directly: a look-at that returns NOTHING means the entity never spawned, which is
a sector/streaming question and not a device question.

Separately found: the terminal still carries mq058's own content - filesStructure
`mq058_file1`, mailsStructure `mq058_plex_newsletter`, journalPaths into mq058.
That is what it would display if it opened today. Not blocking, not yet fixed.

## OI-14 — A gated choice option cannot be shown greyed out   (from D14)
**CLOSED as far as it can go (2026-09-04, D30). The greying is not authorable and the proposed refactor was disproved.**

The original claim was that every condition slot on `scnChoiceNodeOption` is null
in every extracted sample, so under rule 8 an option cannot be gated at all. That
was true of the sample and false of the game. The sample was mods plus a handful
of vanilla scenes.

**Measured against all 7,067 scenes in `basegame_4_gamedata.archive`:**

    questCondition       1177 scenes   (17%)
    bluelineCondition     764
    triggerCondition       65
    emphasisCondition       0
    iconCondition           0
    timedCondition          0

**Corrected 2026-09-03, later the same day.** This table first read 2,648 (37%).
That was a naive substring search: `questCondition` is also a substring of
`questConditionNodeDefinition`, the graph node class, and scenes embed quest
graphs. Searching for the name with a null byte on both sides gives 1,177, and a
random sample of 25 of those scenes was deserialized to check it — 24 of 24 that
loaded carry a genuinely non-null option condition, no false positives. The
conclusion is untouched and the number is 2.25x smaller.

So three slots really are unused by the game and three are not. The worked
example is `base/quest/tertiary_characters/default_dialogues/royce_default.scene`,
which gates one option of a two-option hub on
`questFactsDBCondition{questVarComparison_ConditionType q101_done Greater 0}` —
byte-for-byte the shape `gen_questphase.build_condition` already emits.
`reference/choice_conditions.md` has the full measurement and how to redo it.

**Built and verified (2026-09-03).** `gen_scene.py` takes `"condition": {...}` on
an option in the same DSL the graph uses, importing the graph's builder rather
than growing a second one. Generated against `ashcache_journal_read`, the
structure is identical to the vanilla one; through CR2W and back, the condition
survives unchanged and the packed `.scene` carries `questCondition` and
`questFactsDBCondition` in its name table exactly as vanilla does. `validate.py`
resolves the fact against `facts.json`, and refuses a hub whose *every* option is
conditional. Three negtest cases hold it.

### What stays open: it hides the option, it does not grey it

The greyed-out rendering is real — `DialogHubLogicController`
(`vanilla_scripts.reds:400227`) dims a dialogue list item on
`gameinteractionsChoiceType.Inactive` or `.CheckFailed`, and
`interactionItemLogicController:392669` does the same for world interactions.
Those are bits in `scnChoiceNodeOption.type.properties`, a `CUInt32` bitfield.

**But no author ever sets them.** Across 447 options in a 40-scene sample,
`type.properties` takes four values only: `0` (88), `1` QuestImportant (340),
`256` Blueline (4), `257` (15). Never `4` Inactive, never `16` CheckFailed. Those
are set at runtime; `CheckFailed` comes from the attribute-check system, which
enters through `gameplayAction` (a TweakDBID naming a check record), not through
any condition slot.

And the format carries a tell that conditions *remove*:
`scnChoiceNode.choiceFlags` has `IsValidInteractionFailsafeDisabled`. 360 scenes
set it and **343 of them — 95% — also carry a `questCondition`**. A failsafe for
"no interaction is valid" is only worth disabling if filtering can empty the hub.

So D14's *conclusion* was right and its *reason* was wrong. It routed around the
greying because no evidence existed for the condition; the truth is that the
condition exists and would not have greyed anything. Two entry points remain the
only proven way to show a player an option they did not earn — because they never
see it.

### The experiment this leaves on the table

Switching `scene_mara.json`'s journal gate and `scene_decision.json`'s hide gate
from two hubs to one conditional hub is now one line of JSON each, and would
delete `route_hide`, `route_mara` and two entry points. It is **not done**, on
purpose: the current shape works, and what is verified here is the *file*, not
how the runtime treats a failed condition inside an ArchiveXL-injected scene.
Three outcomes, and all three are survivable, which is why it is worth trying:

  - **removed** (expected) — identical to today, two nodes lighter.
  - **dimmed** — better than today, and closes this issue outright.
  - **ignored** — the option is offered unearned; `br_hide` re-tests the gate
    downstream (D6), so the ending stays correct and only the hub reads wrong.

To close this issue for real, someone has to look at a hub in game.

### Both halves resolved (2026-09-04, D30)

**The refactor is disproved, not deferred.** It was described above as "one line
of JSON each", on the premise that the second entry point exists only to add an
option. It does not. `scene_mara.json`'s two openings are different writing — the
journal one has Mara react to the shard in the player's hand, "don't palm that
shard, I can see the read light from here" — and `scene_decision.json`'s two
differ the same way. Only `start`/`start_journal` are byte-identical. Collapsing
the hubs would delete four authored openings to save three mechanical nodes per
scene. The duplication that remains is the price of the second opening, and the
second opening is the feature.

**The probe, specified and deliberately not shipped.** Nothing in this quest uses
a conditional option, so the runtime question — removed, dimmed or ignored —
cannot be answered by playing it. The cheapest probe is one always-false
conditional option in `scene_decision.json`'s base `hub`:

```json
{"id": "opt_hide_probe", "goto": "sec_hide",
 "condition": {"fact": "ashcache_mara_trusted", "value": 1, "compare": "Equal"},
 "en-us": "Bury it where the FIA stopped looking.", "ua-ua": "..."}
```

The base hub is only entered when Mara is *not* trusted, so the condition is
always false and the three outcomes are directly observable. It is not in the
build on purpose: if the runtime ignores conditions, every player on the
untrusted path is offered an ending they did not earn, and `br_hide`'s downstream
re-test (D6) keeps the *ending* correct while the hub still reads wrong. Trading
a guaranteed-correct hub for a cosmetic answer during a real playthrough is the
wrong direction. Add it for a dedicated test pass, look at the hub, delete it.

Until someone does, the answer is that two entry points remain the only proven
way to withhold an option, and this quest already uses them correctly.

## OI-15 — Retesting on the same save needs a `phase_revision` bump   (from D21)

ArchiveXL force-starts an injected phase on a loaded save exactly once per depot
path, and records that in a save-persistent fact keyed by CRC16 of the path —
setting it whether or not the phase actually ran
(`cp2077-archive-xl/src/App/Extensions/QuestPhase/Extension.cpp:132-137`). So a
save that has run the quest once will not run it again, however much the graph
changes underneath.

The lever is `phase_revision` in `source/quest_graph.json`. Bumping it renames the
resource, which changes the node id and therefore the fact, and the phase enters
cleanly.

**What this costs during development.** Any test that must start the quest from
the beginning on a save that already started it needs a bump before the build.
Three ways to avoid the bookkeeping, in preference order:

1. Keep a dedicated **pre-mod save** for quest-start testing and always load that.
   It never acquires the marker, so no bump is ever needed.
2. Test the start on a new game.
3. Bump the revision. Correct, but it litters the depot with dead resource names
   and every bump is one more path a future save may carry a marker for.

**What it does not cost.** Iterating on anything *downstream* of the start — a
scene, an objective, an item, a marker position — is unaffected. The phase is
already running on that save; only re-*entering* it is gated.

**Unverified.** That the marker actually survives a save/load cycle is inferred
from the fact store it is written to (`NamedFactStore`, the same persistent store
as `ashcache_start`) and from ArchiveXL's guard being pointless otherwise. It is
not directly observed, because the fact key is a raw hash with no name behind it
and nothing in CET or redscript can read a fact by hash. The `phase_revision`
mechanism is correct either way, which is why this was not worth chasing further:
if the marker does not persist, a bump is a harmless no-op.

**The bump is now free (2026-09-08, D50).** The reason to avoid it was never the
dead depot names, it was what re-entry does: the graph re-walks from `start`,
every fact the player set is still set, so it races past every satisfied
`pause_fact` to wherever they are and fires everything on the way. Measured, a
save parked at `await_cleanup` re-entered with three duplicate items and the Mara
conversation replayed. Every irreversible node now sits behind a marker guard,
and `tools/replaytest.py` — wired into `build.sh` after `validate.py` — asserts
both halves: a fresh playthrough still fires each side effect exactly once, and a
re-entry from any of fourteen modelled save states fires none. So option 3 above
is no longer the last resort; it is the ordinary way to repair a save. Options 1
and 2 remain cheaper for routine iteration because they need no rebuild.

**What a bump still costs.** It renames the depot path, so the *archive* must be
redeployed, not just the CET file. And it re-activates the SMS and objective
entries along with the descriptions; whether the engine re-notifies for a state
change that changes nothing is native and unsettled (D50), so expect the
possibility of a burst of popups on the load that repairs the save.

**The bump is now unblocked, and it is not applied (2026-09-08, D51).**
D50 made a re-entry provably harmless. The remaining objection was that bumping
repairs the save and destroys the evidence in one motion - and that objection is
gone, because the evidence is now two screenshots
(`/mnt/sata/Cyberpunk2077/sc/sc_journal_custom_look.png`,
`sc-new/sc_journal_ash_quest.png`) that a bump cannot touch.

The change is one character on line 4 of `source/quest_graph.json`:
`"phase_revision": 1` -> `2`. I could not make it: two edit attempts on that
file were refused by the permission classifier, and a third route would have
been circumvention rather than a different tool. It needs the user's hand or an
explicit approval.

Deploying it redeploys the **archive**, not just `dev/cet/init.lua`. Expect the
SMS and objective entries to re-activate, possibly as a notification burst -
that path is native and still unsettled.


## OI-16 — The quest has 43 spoken lines and no voice for any of them   (from D23)

**A second route, and this one does not need Wwise. (2026-09-09, D67)**

D66 left this waiting on a control the player declined to run - *"there's
nothing to test."* The control is reverted; nothing borrowed ships. What
replaced it came out of two mods already installed on their machine:
`shardaudioframework` plays a shard with the plain vanilla call
`GameInstance.GetAudioSystem().Play(StringToName(m_data.text))`, and its
companion pack answers that call with an `r6/audioware/` YAML and an `.mp3`.
**Audioware hooks the vanilla `AudioSystem::Play(CName)`**, which means the
recordings never have to be Vorbis, or `.wem`, or ride `locVoiceoverMap` at all.

The scene now carries a `scnAudioEvent` beside every `scnDialogLineEvent`
(20 in Mara, 9 in the decision scene), naming a CName that `tools/gen_audioware.py`
registers against the `.wav` we already have. The scene keeps the line, the
timing and the subtitle; Audioware only makes the sound. No script.

Still open until the game says so: that a scene's audio event reaches the same
hooked `Play` a script call does. The CET **Voice** tab splits that in half -
a button there enters the chain at the vanilla call, from anywhere, with no save
and no quest state. Button speaks but Mara does not = the scene event is the
gap. No button speaks = Audioware, the deploy, or the bank.

`locVoiceoverMap` still ships and is still inert. If it is ever fixed the two
routes would double up - that is a note for whoever fixes it, not a reason to
pull a correct resource today.


**The game answered, and the answer is probably no. (2026-09-09, D66)** The
player walked to the clinic door on the voiced build: Mara's lines appeared as
subtitles, correctly timed and attributed, and *"i didn't hear any sound for the
entire time i was standing by the door."*

Eight of the nine links were then checked rather than assumed and all eight hold
— the `.xl` entry, ArchiveXL's merge (logged, no error), the language it merged
into, `VoiceOver = en-us` in `UserSettings.json`, the 43 `stringId`s matching the
scene's `locstringId.ruid`s byte for byte, those same ruids already resolving the
subtitle the player is reading, every `resPath` present in the archive, and
`voParams` asking for `Vo_Context_Quest` / `Vo_Expression_Spoken`. The ninth is
the codec, and it is the one this issue always said was unproven.

The census that justified PCM sampled the wrong reader: all 243 PCM examples are
bank media under `base\sound\soundbanks\media`. The voiceover path is external
sources streamed by resource path, and there it is **110,495 vanilla lines and
342 modded lines, every one of them Vorbis, no PCM anywhere**.

A control is built and waiting for one walk: `mara.mara_open_1` and
`decision.dec_open_1` carry a borrowed Wwise Vorbis line each (Kidnap's, under
our own depot paths, originals in `diag/d66_vo_control/`). A voice saying the
wrong words closes this issue; continued silence reopens all eight links.

If it closes as expected, three routes to real Vorbis are open and none is
started: Wwise 2023.1.14 by the route already documented in `docs/voiceover.md`;
a hand-built Wwise Vorbis writer with inline setup, checkable locally against
`vgmstream-cli` without the game; or **Audioware**, which is already installed
and running here (20,038 ids loaded this session), takes `.wav` and `.mp3`
outright, and ships a `voices:` manifest that carries its own subtitle — at the
cost of driving playback from glue instead of from the scene.


**The promote path is built and gated 2026-09-04 (D43).** `tools/vo_promote.py`
is what moves a measured batch into `vo/`; it refuses an incomplete one, an
unmeasured one, a stray name and a locale outside `VO_LOCALES`. Getting audio
from an audition directory to the shipped voice is no longer a `cp` that nobody
checks. What is still open here is unchanged: whether PCM plays on the voiceover
path at all, which only the game can answer.

**Scope narrowed 2026-09-04 (D42): en-us only.** The 43 lines still need audio,
but only in English. `ua-ua` ships subtitles over the English take, as vanilla
does for a Ukrainian player. See OI-21, resolved as moot.

Everything on this side of the `.wem` is built and proven: `gen_vomap.py`,
`build.sh` copying the map and its audio together, the `localization.vomaps`
entry in the `.xl`, and a packed-archive read-back showing the map and the files
side by side. Drop `vo/en-us/<scene>.<line>.wem` and rebuild — that is the whole
workflow, and it needs no REDmod.

**No longer blocked on Wwise — probably.** (2026-09-03) The premise was that
`.wem` means Wwise Vorbis, and nothing free writes that. True of Vorbis; not
true of the container. A census of every `.wem` the game ships —
`audio_1_general` (4,434) and `audio_2_soundbanks` (4,796) — found **127 files
with `wFormatTag` `0xFFFE`, uncompressed 16-bit PCM**, and the installed mod
**LizziesBDs ships 116 more**. A codec the shipped data uses is a codec the
shipped runtime has, and PCM needs no encoder at all: 96 bytes of header in
front of the samples.

`tools/wav_to_wem.py` writes those 96 bytes. Its header is **byte-identical** to
a shipped mono PCM `.wem` apart from the two size fields and the content hash,
and a full round trip — vanilla Vorbis line → `vgmstream` → `.wav` → this tool →
`vgmstream` — comes back **sample-identical** to the reference downmix. Built,
packed and read back out of the archive: the `.wem` decodes as 48 kHz mono PCM,
the vomap's `stringId` matches `subtitle_ids.json`, and both `resPath`s name a
depot path that is in the archive.

**The one thing not verified (rule 8):** that PCM is accepted on the *voiceover*
path specifically. All 127 vanilla PCM files and all 116 of the mod's live under
`base\sound\soundbanks\media` — bank media, streamed by id. Every custom voice
line in all 24 installed mods that ship a `vomap` (342 files) is Vorbis. So no
shipped example proves PCM through `locVoiceoverMap`'s external-source path.
Both paths end in the same Wwise source reader dispatching on the `fmt` tag, so
it should hold — but "should" is not "does", and only the game can answer.

Trying costs nothing: the failure mode is a subtitle with no sound, which is
exactly the status quo. If it does fail, the Wwise route is unchanged and still
documented — Wwise **2023.1.14** exactly, Vorbis Quality High, mono, 48000, in
`docs/voiceover.md`.

Cost of PCM: 96 KB/s. Roughly 17 MB per locale for 43 lines, lossless.
`--rate 24000` halves it, and the game itself ships 24 kHz voice (every
holocall) if that ever matters more than fidelity.

Training material is not blocked either. `tools/vo_rip.py` pulls any of the
game's own speakers out as `.wav`; the corpora are large (Johnny 2,714 lines,
Songbird 1,863, Reed 1,926, V 29,250). With the encoder in place the whole chain
is now local: rip a corpus → train or fetch an RVC voice → generate a `.wav` →
drop it in `vo/en-us/` → `tools/build.sh`.

Downstream: **lipsync**, now investigated in full and split out as its own
issue — see OI-17. The map, the ids, the `.xl` block and the build wiring are all
done and verified from the packed archive; only the `.anims` itself is blocked,
by a second encoder problem of exactly the same shape as this one.


**The voice-model side is now built, and the premise changed.** (2026-09-04)
The brief was that the character datasets and Applio settings already existed
and only needed a button pressed. No dataset folders or `.txt` settings sheets
were on this machine, so both were built here instead.

> **Corrected 2026-09-04 (D33).** The half of that sentence which said there
> were no `.pth`/`.index` files for Male V and Johnny Silverhand was wrong. They
> are at `/mnt/sata/SoniTranslate/weights/` and `/mnt/sata/SoniTranslate/logs/`,
> and they have been there the whole time. The search that "found" nothing was a
> `find` rooted at `/mnt/sata` which hit the 120 s timeout and was killed — it
> reported nothing because it never finished, not because there was nothing.
> Both paths are three levels deep, inside the `-maxdepth 4` it was given.

`tools/vo_dataset.py <speaker> --as <model>` turns a game character into a
training set: rip, drop clips outside 1.2-12 s, seeded-shuffle so the sample
spans the whole performance instead of one quest's recording session, peak
normalise to -3 dBFS, cap at 35 minutes, and write `SETTINGS.txt` (the settings
sheet) plus `manifest.json` (which lines, reproducibly). `tools/rvc_train.sh`
runs preprocess → extract → train → index headless, skips stages already done,
resumes from the newest checkpoint, and `--detach` survives a closed terminal.

Two settings are forced rather than chosen. **48000 Hz**, because the game's
lines decode at 48 kHz mono and anything else resamples the training data for
nothing. **HiFi-GAN**, because it is the only vocoder with a 48000 pretrained
pair present (`f0G48k.pth` + `f0D48k.pth`); RefineGAN ships 24k and 32k only, so
selecting it at 48000 quietly means training from scratch. Process Effects and
Noise Reduction are both **off**: this audio was recorded in a booth and already
mastered, and a second denoise pass eats the breath and sibilance that make a
voice recognisable.

Two silent dataset bugs were found and fixed on the way, both of which produce a
model that trains cleanly and sounds wrong:

* `vo/` and `vo_holocall/` hold two different mixes of one recording under the
  same filename, 8,332 names collide, and `vo` sorts first so the band-limited
  holocall take always overwrote the clean one. 451 of Songbird's 1,863 lines
  have one. `vo_rip.py` now excludes them unless `--include-holocall`.
* `_f_`/`_m_` is the *player's* gender (D24), which for an NPC means two takes of
  one actor and for V means two different actors — 14,560 female to 14,690 male,
  with 14,538 lines shipping both. `--gender` is now mandatory for any `v*`
  speaker, because mixing them yields a model that sounds like neither.

**Still yours to decide: who Mara sounds like.** She is a custom character, so
unlike Johnny or V there is no voice to download — a donor has to be picked from
the game and converted. The first overnight run uses **Rogue** (797 clean lines,
626 usable, 35.0 min): weathered, guarded, and old enough to have buried
something nine years ago. Judy, Songbird, Panam, Myers, Claire and T-Bug all
have enough data too, and switching is one command
(`tools/vo_dataset.py judy --as mara && tools/rvc_train.sh --fresh mara`). The
real cost of any of them is recognisability — every donor is a character the
player has already met.

**Which voices this quest actually needs, and which are already done.**
(2026-09-04, D33) The two scenes are spoken by exactly two actors: **Mara, 18
lines** and **V, 11 lines**. Johnny does not appear — that model is for the
ua-ua dub.

| voice | state |
|-------|-------|
| **mara**   | **BROKEN — emits noise, not speech.** Quarantined in `rvc_voices/BROKEN/`; a clean retrain is queued. See the 2026-09-04 D36 update below. |
| **male_v** | **done.** The downloaded `MaleV-Cyberpunk2077.pth` is 48 kHz RVC v2, ~38 min of data, 600 epochs — ahead of the 200-epoch run on 35 min that was queued, so `v_male` was dropped from the queue. Verified by conversion. |
| **johnny** | still queued. The downloaded one is 32 kHz, a 16 kHz ceiling next to full-band vanilla VO, and its dataset was 28 min against our 35. |

Full inventory, with every field read out of the checkpoints rather than the
filenames, in `reference/rvc_voices.json`.

**The remaining gap is source audio, not models.** RVC converts a performance,
it does not invent one, and there is no recording of any of the 43 lines.
`edge-tts` and `gTTS` are installed in the SoniTranslate env, so TTS → RVC →
`tools/wav_to_wem.py` closes the chain on paper; both are network services and
neither has been run here. UNVERIFIED — nothing is built on top of it.

One useful measurement while deciding: conversion on **CPU** runs at about 2×
realtime (11 s for a 5.2 s clip), so all 43 lines is roughly ten minutes without
the GPU. The voice pass never has to wait for training to end.


**mara is done enough to use, and the crash that stopped it was self-inflicted.**
(2026-09-04, D34)

The 200-epoch `mara` run died at ~epoch 118 with an amdgpu page fault. The cause
was an orphaned trainer from an earlier queue run — I had edited
`tools/rvc_train.sh` in place while a shell was running it, which killed the
wrapper and left its grandchild `rvc/train/train.py` alive, reparented to init,
holding 4.87 GB of VRAM for nine hours. Applio's own
`logs/mara/config.json` had recorded all three trainers in `process_pids` and
never checked whether the older two were alive.

It cost epochs, not the model. `--save-every-epoch 10` had already written
`mara_110e_14410s.pth`, which is the same small inference checkpoint format as
the final `<model>.pth`, and `mara.index` is built from the extracted features
rather than from the weights, so the crash could not spoil it. Both are now in
`/mnt/sata/Cyberpunk2077/rvc_voices/` with a README, verified on CPU by two real
conversions, and recorded field-by-field in `reference/rvc_voices.json`.

One settled inference argument came out of it: **`volume_envelope=0.0` for
mara**. `rvc/infer/pipeline.py:545` reads `if volume_envelope != 1:`, so `1.0`
means *do not touch the level* — at `1.0` this model emits −5.1 dBFS from a
−21.6 dBFS source and is invariant to input level; at `0.0` it lands at
−22.4 dBFS. Measured, not assumed.

`tools/rvc_train.sh` now reaps stale trainers for a model before training it,
and treats a periodic checkpoint as a usable result (exit 2) instead of a
failure. That closes the class of bug, not just this instance.

**Still open on this issue:** whether to spend the remaining 90 epochs. Resuming
costs 90, not 200, because the queue resumes from the newest checkpoint. That is
a listening decision and needs a listen. **And the real blocker is unchanged —
there is still no source audio for any of the 43 lines.**


**The TTS half is no longer UNVERIFIED.** (2026-09-04, D35)
`questmod-research/verify_tts_chain.sh` ran the whole pipeline end to end —
`edge-tts` → `ffmpeg` 48 kHz mono → RVC/mara on CPU at `volume_envelope=0.0` →
`tools/wav_to_wem.py` → `vgmstream-cli`. The container round trip returns
**sample-identical int16** (314,880 for 314,880), so the encoder is no longer a
suspect for anything that sounds wrong later. CPU cost is ~1.8× realtime, so 43
lines is under ten minutes and never needs the GPU.

The text sent to the endpoint was a pangram and a counting phrase. No quest line
left this machine — that is a release decision, not a plumbing one.

`uk-UA-PolinaNeural` and `uk-UA-OstapNeural` also synthesise, so the ua-ua track
(rule 7) has a source through the same pipeline with no extra tooling.

**What is left on this issue is now two questions, both needing the user:**
1. PCM on the *voiceover* path in game — unchanged, only the game can answer.
2. Whether TTS-through-RVC is good enough to ship. Mara's 18 lines have no
   vanilla counterpart; V's 11 will play next to thousands of lines of real V
   performance in the same session. That is a much harsher test, and it may be
   that Mara passes and V does not. Worth deciding before generating 43 lines.
   Sample audio to judge from: `rvc_logs/tts_chain/`.


**The salvaged mara model emits noise and has been thrown away.** (2026-09-04, D36)

The user, on listening: *"more noise than a clear voice"*, *"sound eruptions"*.
Measured, that is exactly right — `mara_110e_14410s.pth` renders at 100% of samples
at full scale, and puts −0.1 dB of noise into frames the source calls silence, where
a healthy model gives −57 to −96 dB. It fails on its **own training material**. Both
downloaded models pass the identical pipeline, so the chain, the container and the
settings are all exonerated; the checkpoint is the fault.

Two things this closes, and one it opens:

- **The `volume_envelope=0.0` recommendation is withdrawn.** Use `1.0`. The level
  table that justified `0.0` was measured downstream of `change_rms`, which rescales
  the output until its RMS matches the source — so the check could not have failed.
  The "verified" status this issue carried was never evidence.
- **Nothing may be called usable because the file exists.** `tools/rvc_check_model.py`
  now measures clipping, the noise floor in the source's silent frames, and the share
  of energy above 8 kHz, and `tools/rvc_train.sh` runs it before declaring any model
  done, returning 3 with "the result is NOISE" if it fails.
- **Still open:** the retrain is queued behind johnny via `--wait` and starts from the
  pretrained models, because the high-frequency share was already climbing at epoch 20
  — no early checkpoint is a safe base. Whether TTS-through-RVC is good enough to ship
  cannot be judged until a working mara exists.

### 2026-09-04 — the TTS stage does not have to leave this machine

Everything in this issue so far assumed the TTS stage was `edge-tts`, which is
Microsoft's network service. That is why none of the 43 lines have been sent
anywhere: doing so is a decision for whoever owns the text, and nobody has taken
it. **It turns out the decision may not be needed at all.**

Two local backends are available on this machine right now:

  - **espeak-ng**, installed, speaks `uk` and `en-us`. Robotic prosody, and RVC
    carries prosody through - it replaces timbre, not delivery.
  - **piper**, whose catalogue is already at `SoniTranslate/PIPER_MODELS/voices.json`
    and lists `uk_UA-ukrainian_tts-medium` (3 speakers) plus a dozen high-quality
    `en_US` voices. Much better, but the `.onnx` files are not downloaded and the
    `piper` binary is not installed. Downloading a voice model sends a model name,
    not a line of the quest.

`tools/render_lines.py` does the whole chain - text -> TTS -> 48 kHz mono -> RVC
-> `vo/<locale>/<key>.wav` + `.wem` - with the backend pluggable. `--tts edge`
**refuses to run without `--allow-network`**, so the constraint is enforced by the
tool rather than remembered by whoever runs it.

**Proven end to end on real quest content, entirely locally:** all 11 of V's
English lines through espeak -> MaleV -> PCM `.wem`, in 1:48 wall clock, plus one
Ukrainian line. Measured output, 11/11 inside the health gate: 0.00% clipping,
gaps at -87 to -240 dB, HF share 0.29-1.76%. Written to
`rvc_logs/audition/`, **not** to `vo/` - `--out` exists precisely so a backend
can be auditioned without its result quietly becoming the shipped voice.

So the pipeline is no longer the unknown. What is unknown is whether espeak's
delivery is acceptable once it wears V's voice, and that is a listening
judgement. Mara's 18 lines still wait on a working model.

One measured detail worth keeping: the same line runs **7.80 s in Ukrainian
against 5.28 s in English**, 48% longer. That is the reason OI-8 times subtitles
off the longest locale, now with a number behind it.

### 2026-09-04 (later) — piper is installed, and the delivery is still the open question

The user listened to the espeak audition: *"the voice is clear, but it sounds like a
robot."* Correct, and not fixable in RVC — RVC converts timbre, not delivery (D40).

Corrected from the entry above: `/mnt/sata/SoniTranslate/PIPER_MODELS/` held only
`voices.json`, the download index. No models, no binary. piper now lives in
`/mnt/sata/Cyberpunk2077/tts_venv` (deliberately not in the Applio env, which is
training) with three voices in `/mnt/sata/Cyberpunk2077/tts_models`:
`en_US-ryan-high` for V, `en_US-lessac-high` for Mara, and the 3-speaker
`uk_UA-ukrainian_tts-medium` (`#mykyta` for V, `#tetiana` for Mara).

All 25 of V's lines are rendered in both locales, Ukrainian with automatic stress
marks, and measure clean against the source (`tools/rvc_audition.py`: clip 0.00%,
hf 0.13-1.96%, gap -35.2..+5.8 dB against a +6.0 limit):

    /mnt/sata/Cyberpunk2077/rvc_logs/audition_piper/{en-us,ua-ua}/

**Still a listening judgement, and still not made.** Nothing is in `vo/`. Two things
a listener should check that no measurement here can:

- Whether piper's prosody is acceptable once it wears V's voice. If it is not, the
  next lever is not another synthesiser - it is a human reading the lines, which is
  what RVC was built to convert.
- Whether the Ukrainian stress is right. The stresser disambiguates homographs by
  part of speech and will sometimes pick the wrong one (`ні́чого` vs `нічо́го`).
  Only a Ukrainian speaker can hear that, and the player is one.

Mara's 18 lines still wait on a mara model that passes its health check.

### 2026-09-04 (later still) — the audition can only judge gap noise on padded sources

`rvc_audition.py` measures whether the model hallucinated noise into the source's
silence. A piper line is one sentence with no padding, so it contains no silence:
across the eleven surviving RVC renders, **0 of 11** had a source quiet quarter
below -45 dB, and the two lines the tool failed on that statistic were clean on
every other one. D44 scopes the test rather than retuning it — those lines are now
reported unjudged and carry their verdict on clip and hf.

That is correct but narrow. The repair that would make the statistic work is to
give it silence to measure: a few hundred ms of digital silence at head and tail
of each source before conversion, which would make gap noise observable on all 43
lines instead of none.

**Why it was not done tonight.** `read_time` (OI-8) takes a voiced line's duration
from the measured recording, so padding that survives into the shipped take
inflates every line's duration by the padding — and the OI-8 margin is already
down to 155 ms on `mara.opt_break_j`. It needs the pad trimmed after conversion,
or `vo_lengths()` taught to measure around it, and neither is a change to make
unattended with a model mid-training. Decide it before the next render batch, not
after.

### 2026-09-09: Audioware answered, and it answered exactly

The bank is not a hypothesis any more. `audioware-2026-09-09-15-44-01.log`, from
the player's own machine, after the deploy:

    ids:
    - on-demand static audio    -> 1616
    ...
    no error reported!

The same counter read **68** in the 13:12 log, before the deploy. The difference
is **1548**, and 43 lines x 18 locales x 2 genders is 1548 — every line, every
locale, both genders, nothing dropped and nothing rejected. Audioware found
`r6/audioware/ash_cache/ash_cache.yml`, parsed it, resolved all 43 `.wav`, and
reported no error.

So of the chain in D67 — recordings exist, the manifest is right, the names are
right, Audioware registers them, a `Play(CName)` reaches them, a `scnAudioEvent`
counts as that call — the first four links are now evidence rather than
inference. The fifth is what the CET **Voice** tab tests in five seconds from
anywhere. The sixth is what a conversation tests.

The sixth link also has a new reason to be watched: a scene audio event whose
CName the scene system resolves against Wwise *directly*, rather than through
the hooked `AudioSystem::Play`, would get no match — and a missed 64-bit id
lookup used as a pointer is `0xFFFFFFFFFFFFFFFF`, which is the exact fault
address of the crash in D69. That is a coincidence worth naming out loud, not a
finding. If the clinic still crashes with both device buffers off, it stops
being a coincidence.

### 2026-09-09 16:31 - the cause was in the manifest, and Audioware named it

Two warnings on the player's machine, after they pressed the CET Voice tab:

    cannot play sound: Registry error: requires gender: ash_cache_vo_decision_dec_absorb_1
    cannot play sound: Registry error: requires gender: ash_cache_vo_decision_dec_blueeyes_1

This is not a miss. The key resolved; the registry refused to serve it. Our bank
wrote `fem:`/`male:` under every locale (the same file twice, to keep Mara's voice
independent of V's), and in Audioware that does not mean "gender-neutral" - it
means "this key IS gendered", playable only by a caller that supplies a gender.
`Play(CName)` with no entity - the CET panel, shardaudioframework, and a
scnAudioEvent - supplies none.

`gen_audioware.py` now emits the plain per-locale shape the shard pack uses:
43 keys x 18 locales = 774 rows, 0 gendered. Expect `on-demand static audio` to
read **842** (68 + 774) on the next launch instead of 1616. See D70.

Still open on this issue: whether a scnAudioEvent reaches the hook the same way
the CET button does. The button is now the control - if it speaks and Mara does
not, the remaining fault is in gen_scene.py.


### 2026-09-09, after the second in-game test: half closed, and the other half named

D70's manifest fix is confirmed on the user's machine. `on-demand static audio`
reads **842**, the predicted number to the digit, there is no `requires gender`
line anywhere in the log, and the CET Voice button speaks. `voices:` is done.

The scene was still silent, with subtitles showing - and that combination is a
diagnosis, not a mystery. Audioware hooks the engine's `PlayDialogLine` and keys
on the line's CRUID, letting the engine's own path run regardless so the subtitle
still appears (`hooks/audio.rs`, and its own comment says so). Scene dialogue
lives in a **second registry**, reported separately in the same log:
`scene ids -> 22`, all 22 of them another mod's. The `scnAudioEvent` this build
emits was never able to reach it.

Fixed by adding a `dialogs:` section keyed by the locstring ruids already in
`source/subtitle_ids.json` - 43 keys x 18 locales, the same files.

**CONFIRMED on the user's machine, 2026-09-09 20:46** (deploy 20:30, launch
20:43, `red4ext/logs/audioware-2026-09-09-20-46-27.log`):

    ids:                                  scene ids:
    - on-demand static audio    -> 842    - on-demand static audio    -> 796
    for a total of: 20812 id(s)           for a total of: 796 scene id(s)
    no error reported!                    no scene error reported!

796 = sonoraapex's 22 + our 774 (43 x 18) exactly, with the main block holding
at 842 and neither registry reporting an error. The registration half of OI-16
is closed by number. What is NOT yet confirmed is playback: the session crashed
at 20:50:50 on arrival at the clinic door, before the scene ran, so no one has
heard a line through the scene path yet. See D71.

Remaining for this issue after that: the shard's Toggle Audio button is still
silent (needs a courier recording for LocKey#77315032), and `mara.trust_3.wav`
is 0.22 s, which looks like a truncated render.

## OI-17 — CLOSED 2026-09-16 (D109, verified in game). Was: the lipsync map is built and there is no way to author an `.anims`   (from D24)

A voiced line with no lipsync plays over a face frozen in its idle, which reads
as a broken NPC rather than as a missing feature. So this had to be understood
before the first `.wem`, not after.

**The chain, verified end to end on one vanilla line.** Four resources and three
different keys have to agree:

    .scene   scnActorDef.voicetagId.id                     = 1103967280742240508
    .lipmap  scenePaths[i]      = FNV1a64(scene depot path)
    .lipmap  sceneEntries[i].actorVoiceTags[j]             = the same number
    .lipmap  sceneEntries[i].animSets[j]  -> that actor's .anims
    .scene   screenplayDialogLine.femaleLipsyncAnimationName = f_<ruid:016X>
    .anims   animations[k].name                            = f_194725D45D49D000

Proven against `base\quest\minor_quests\mq029\scenes\mq029_01a_garage.scene`:
its FNV1a64 is `3647272176032198475`, which is `scenePaths[706]` of the game's one
and only `base\localization\en-us.lipmap`; entry 706's `actorVoiceTags` is
exactly the `voicetagId` that scene gives its `johnny` actor; its `animSets[0]` is
that scene's `johnny.anims`; and that animset holds an animation named
`f_194725D45D49D000`, whose hex **is** the line's `locstringId.ruid`.

The key is the **voicetag**, one level above the line — not the locstring id the
voiceover map uses. Getting that wrong would have produced a map that loads,
merges, logs success and animates nobody. The line-level key lives inside the
animset, as the animation's name.

**What ships now, all verified from the packed archive:**

- `tools/alloc_voicetags.py` + `source/voicetags.json` — block
  `7731600000000000000-7731600000000000099`, append-only. V is deliberately not
  allocated one: 0 of the 5688 shipped lipsync animsets name the player, because
  V is normally seen from the inside.
- `tools/gen_scene.py` — Mara carries a real voicetag, and all 43 lines name
  `f_<ruid>` / `m_<ruid>`. Only `f_` animations ship in vanilla, yet vanilla sets
  both fields on every line, so an `m_` name that resolves to nothing is
  demonstrably harmless.
- `tools/gen_lipmap.py` — `lipsync/<locale>/<character>.anims` is the manifest,
  the same drop-folder rule `gen_vomap.py` uses. Round-trips byte-identical
  through WolvenKit.
- `tools/build.sh`, `tools/gen_xl.py` — map and animsets copied together, and a
  `localization.lipmaps` block emitted only for locales that have one.
- `tools/validate.py::check_lipsync` + 8 negtest cases.

A test build with a stand-in animset packed correctly and read back with every
link matching: scene voicetag `7731600000000000000` == the map's
`actorVoiceTags[0]`; `scenePaths[0]` == FNV1a64 of the packed scene's depot path;
`animSets[0]` == a path that is actually in the archive.

**The blocker, restated after actually looking (2026-09-03).** "Nothing free
writes an `.anims`" was wrong, in the same way OI-16's premise was wrong. What
follows replaces it.

*The format is writable.* A lipsync take is a normal skeletal animation on the
character's own face rig, not an opaque viseme stream — the smallest shipped one
(`q108_14b_lift/johnny.anims`, 8 KB) is `animAnimSet { rig -> Johnny's
`_skeleton.rig`, animations: [ animAnimation { animationType
AdditiveFromRefPose, name `f_18D51C305D4EA000`, duration 1.833, animBuffer:
animAnimationBufferCompressed { numFrames 56, numJoints 344, numTracks 414,
numAnimKeys **51**, numConstAnimKeys 1024 } } ] }`. Only ~51 of the 344 joints
actually move; the rest are constant.

*And there are two buffer types, not one.* The game's RTTI carries
`animAnimationBufferCompressed`, `animAnimationBufferSimd`,
`animCAnimationBufferUncompressed` and `animCAnimationBufferBitwiseCompressed`
(confirmed by `strings` on `Cyberpunk2077.exe`). A census of 208 sampled vanilla
animations from `basegame_4_animation` found **13 using `animAnimationBufferSimd`
exclusively and 22 using it alongside the compressed one** — so the runtime plays
SIMD buffers, exactly the way it plays PCM `.wem` in OI-16.

*WolvenKit writes SIMD buffers.* `WolvenKit.Modkit/RED4/Tools/AnimationTools.cs`
has `ImportAnims(gltfFile, animStream, args)` and
`Tools/Animation/AnimSIMDEncoder.cs`. glTF in, `.anims` out. It needs an existing
`.anims` as the target, for its `rig` reference — and any vanilla lipsync animset
for a compatible character is one.

*Export already works headless here.* Verified this session:

    WolvenKit.CLI export <vanilla lipsync>.anims -o out -gp "<game>"
      -> johnny.anims.glb   (1 animation, on Johnny's face rig)

*Import does not, and that is a CLI gap rather than an engine limit.*
`WolvenKit.CLI/Commands/ImportCommand.cs` declares only `path`, `--outpath` and
`--keep` — there is **no `--gamepath`**, so the archive manager is never loaded
and the rig lookup fails with *"No rig found for ...\_skeleton.rig"*. Routing to
the anim importer itself does work: add `"GltfImportArgs": {"ImportFormat":
"Anims"}` to the CLI's `appsettings.json` and it reports *"Failed to rebuild with
buffers: johnny.anims (as Anims)"* — the right code path, missing only the rig.
(That setting sends **every** `.glb` import to `.anims`, so it was reverted here
rather than left on.) Three ways round it: the WolvenKit **GUI** under wine,
which has a project and therefore a game path; patching `ImportCommand.cs` to
pass `gamepath` the way `ExportCommand.cs` does; or a `.cpmodproj` and
`WolvenKit.CLI build`.

*So the real blocker is not the file format — it is the animation.* Something has
to produce face-rig curves that match the audio. Nothing here does. Options, none
built or verified:

  - **Transplant.** Export a vanilla lipsync take of similar duration to glTF,
    rename the animation to this line's `f_<ruid:016X>`, re-import. The mouth
    moves plausibly and matches nothing. Cheap; possibly worse than a still face.
  - **Generate.** Rhubarb Lip Sync (free) turns audio + transcript into viseme
    timings, but mapping its six visemes onto the ~51 joints this rig animates is
    unmapped work, and the mapping would have to be read out of vanilla takes.
  - **Author.** Blender on the exported rig. Real, and 43 lines of it is a lot.

**TODO, unverified (rule 8).** The claim that has changed is only this: the
`.anims` container is no longer the obstacle. The obstacle is viseme data and a
CLI that cannot import headless.

Until then the build ships no lipmap at all — deliberately. A map naming animsets
that were not packed merges cleanly, logs success and moves no mouth, which is the
worse failure.

**Reference that proves the path is reachable from a mod archive:** the Kidnap
mod ships 3 custom animsets and 20 per-locale lipmaps, and reuses Johnny's vanilla
voicetag `1103967280742240508` verbatim — which also proves a voicetag is global
to a character rather than local to a scene.

## OI-18 — The journal entry has no description body and generic icons   (2026-09-03)
**ICONS CLOSED (2026-09-08, D48) - the `(!)` is on every vanilla quest in the same
list, so there was never a difference to explain. DESCRIPTION: the data is now
proven correct end to end and the only surviving explanation is a stale save
(2026-09-08, D49).**

The game's decompiled scripts arrived at `/mnt/sata/Cyberpunk-Scripts`, and the
render path turns out to be four lines with no branch in it: whatever
`QuestLogUtils.GetDescriptions` returns is what the panel prints. Checked against
it and passed: the node type and its key set match Hot Fuzz exactly, all twelve
`Active` sockets are connection destinations, all twelve description entries are
in the `.journal` under the right objective, both `en-us` and `ua-ua` carry the
LocKeys with real text, and the `.journal` and `.questphase` inside the archive
the user is running are byte-identical to the current build. One correction to
D48: the three codex cards drawing was never evidence about the description,
because `PopulateCodexLinks` unpacks with `includeInactive = true` and
force-activates its targets - the description is the only child of an objective
filtered on its own state.

**Next measurement, and it is now one glance rather than one objective of play:**
the dev panel's Journal tab prints each description's own state indented under
its objective, and `report.txt` carries it. An objective reading ACTIVE over a
desc that is not is the stale save, confirmed. The `force` button beside it sets
the state by hand - if the paragraph appears, everything but the graph flow was
fine. Requires redeploying `dev/cet/init.lua` only; the archive is unchanged.

**The repair, when the user wants it:** bump `phase_revision` in
`source/quest_graph.json` from 1 to 2. That renames the depot path, so ArchiveXL
force-starts the phase again on a save that already ran it. The cost is that the
graph re-runs from its input - facts persist so it races forward, but it re-fires
the `add_item` grants and the scene nodes on the way. Left for the user; it is a
decision about their save, not a build fix. See also OI-15.

**DESCRIPTION HALF FIXED (2026-09-04, D30). ICONS DIAGNOSED (2026-09-04, D32) - one half was never a defect; both traps are now build failures. One screenshot left for the user.**

Side-by-side screenshots of a vanilla quest and this one show three differences,
none of which is a crash and all of which read as unfinished:

* Vanilla's journal screen carries a description body — `Завдання:` / `Місце:` /
  `Подробиці:` with briefing text under each. This quest's entry has none.
* Vanilla's linked-entry row renders four portrait/location thumbnails. This one
  renders three generic codex cards.
* The left-hand quest list shows a character icon for vanilla and a generic `(!)`
  for this one.

Everything else renders correctly, in Ukrainian, including `[необов'язково]`
inline on the optional objective. So this is missing content in the journal
resource, not a broken pipeline. Not yet diagnosed: which field carries the
description body, and whether the thumbnail row keys off the codex link's own
image or off a separate field on the journal entry.

### The description body: found, diagnosed, fixed

It was never missing content. All 12 description paragraphs were written,
translated into Ukrainian, allocated LocKeys 77315035-77315046 and shipped inside
the `.journal` as `gameJournalQuestDescription` entries hanging off their
objectives — exactly where vanilla puts them. The panel was empty because
**nothing ever activated them.**

`QuestLogUtils.GetDescriptions` collects through
`UnpackRecursiveWithFilter`, which tests every entry individually:

    if !includeInactive && (GetEntryState(currentEntry) == Inactive
                            && currentEntry as JournalQuestMapPinBase == null) {
      // skipped
    }

A description is not a map pin, so an Inactive one is dropped. State does not
cascade from the objective — each entry is its own claim. And the single carve-out
in that condition is what hid the bug for weeks: **map pins render while
Inactive**, so this quest's pins worked perfectly on the same code path that was
silently discarding every description.

The fix is 12 `journal_entry` nodes, `class: gameJournalQuestDescription`, path
`<objective>/description`, each chained onto its objective's `Active` node so the
paragraph appears the moment the objective does. The shape is confirmed against a
working reference: Hot Fuzz's questphase addresses
`quests/main_quest/prologue/nq_ncpd_judy/ncpd_judy/01_go_to_notell_judy/description`
identically, and the emitted nodes match it field for field
(`className gameJournalQuestDescription`, `fileEntryIndex 3`,
`sendNotification 1`).

Made unrepeatable rather than merely fixed: `journal_paths` in `validate.py` now
treats an objective's description as an addressable path, so one that nothing
activates is reported as dead UI and fails the build; `negtest.py` holds it (85/85);
and `gen_journal.quest_description`'s docstring, which asserted the engine hands
the UI every description "whose objective has been reached", is corrected — that
belief is what produced the bug.

### The icons: both halves diagnosed (2026-09-04, D32)

Read out of the game's own scripts (`questmod-research/vanilla_scripts.reds`) and
the ep1 journal. Quoted in `reference/examples/journal_icons.json`.

**The codex row is not a defect.** `QuestCodexLinkController.SetupCodexLink` has
no generic card to fall back to:

    if CodexUtils.IsImageValid(codexEntry.GetLinkImageID()) { RequestSetImage(...) }
    else { this.GetRootWidget().SetVisible(false); return; }

An invalid link image **hides** the card. Three cards visible therefore means
three valid link images drawing their real art, and both ep1 targets check out —
`ep1/codex/locations/subdistricts/dogtown` carries `UIJournalIcons.l_dogtown`,
`.../quest/cyanosure` carries `UIJournalIcons.l_cynosure`. `IsImageValid` is
stricter still: it rejects an icon whose atlas part is `empty`/`empty2`/`c_empty`,
so even a blank icon hides the card rather than drawing a placeholder.

What differs from vanilla is content, not pipeline: this mod links three
**location** entries and vanilla links **character portraits** alongside them.
`gameJournalQuestCodexLink` has exactly one field, `path` — the art is entirely
the target entry's business. A portrait means linking a vanilla character's codex
entry, or authoring an entry with its own `linkImageId`. **That is a design
choice, not a fix, and it is the user's to make.**

**The list icon comes from `type`, and there is exactly one bad value.**

    SimpleQuestListItemController -> QuestTypeIconUtils.GetIcon(questType)
    QuestsListController.GetDisplayedCategory(gameJournalQuest.type)

Both are switches with silent fallthroughs, and they compose:
`gameJournalQuestType` has ten members, `GetDisplayedCategory` names nine, and the
tenth — `VehicleQuest` — falls through to `QuestListItemType.Invalid`, whose icon
is the atlas part `"invalid"`: the generic `(!)`. This quest is `SideQuest`, which
maps to `minor_quest` and is fine. So **the `(!)` in the screenshot cannot be
coming from the current build**, and the likeliest explanation is that the shot
predates `type`/`districtID` being set.

A third icon exists and was being conflated with this one: the tracked-quest HUD
widget, `QuestItemController.SetQuestData`, whose last line builds
`"UIIcon." + ToString(GetDistrict())` by string concatenation from
`districtID`. That one is also fine here — `Districts.Dogtown` → `UIIcon.Dogtown`.

Both traps are now build failures rather than screenshots:
`check_journal_icon` rejects a quest type the list cannot draw, and
`check_district_icon` rejects a district with no icon behind it. Three negative
tests hold them, one of which is a positive control keeping an empty `districtID`
legal, because 16 of the 55 vanilla ep1 quests ship without one.

**What is left for the user:** confirm on a fresh screenshot whether the `(!)` is
still there. If it is, the reading above is wrong somewhere and the next lead is
`QuestListItemData.m_questType` — whether the list is being fed the quest at all,
rather than which icon it picked. If it is gone, the only remaining item is the
design question of whether to link a character portrait.

**The repair is now cheap, and the order matters (2026-09-08, D50).** Bumping
`phase_revision` re-enters the phase and re-activates the twelve description
entries, and re-entry no longer duplicates items or replays scenes. Two things
were also settled on the way. There is no data-side alternative: a
`gameJournalQuestDescription` carries only `$type`, `id` and `description` in
Hot Fuzz, High Stakes, Undermine and ours alike, with no initial-state field, so
the graph is the only thing that can make one Active. And the diagnosis is now
forced rather than inferred — `PopulateObjectives` runs both walks from the same
quest entry, so the objectives the user can see prove every container above the
description is Active, leaving the description's own state as the only variable.

**Measure before repairing.** A bump fixes the save and erases the evidence in
the same motion. Read the CET panel's `desc` states first; an objective reading
ACTIVE over a description that is not is the confirmation, and it takes one
glance. Then bump.

**Confirmed by photograph, not by elimination (2026-09-08, D51).** The
screenshots were never lost; they are in `/mnt/sata/Cyberpunk2077/sc/` and
`sc-new/`, not `~/Downloads`. `sc/sc_journal_vanilla_look.png` shows a vanilla
gig panel: title, objective, a `Завдання:/Місце:/Подробиці:` block, a prose
paragraph, four codex thumbnails. Ours (`sc/sc_journal_custom_look.png` and the
later `sc-new/sc_journal_ash_quest.png`) render the title, the objectives and
all three codex thumbnails - and no description, with no gap where one would be.

That is the exact split `questLogDetailsPanel.script` predicts. Line 110 fetches
the codex links with all four states enabled, Inactive included, so they render
regardless of state. Line 151's `GetDescriptions` is the only walk on that panel
that drops Inactive entries. The one widget requiring Active state is the one
widget missing, and the objectives above it share its walk root, so every
container between the quest and the description is provably Active. The later
shot has two active objectives - two survivors of the walk the description did
not survive.

The CET Journal-tab probe is therefore no longer a precondition for repair. It
would only separate "the node never fired" from "it fired and the entry is still
Inactive", and a `phase_revision` bump repairs both identically. See OI-15.

### 2026-09-09 - the briefing block is answered, and a second defect found (D54)

Two of this issue's three original bullets are now closed for real reasons rather
than by elimination.

**`Завдання:/Місце:/Подробиці:` is not a missing field.** The details panel has
exactly one description widget, `m_questDescription`, and everything
`GetDescriptions` returns is concatenated into it. Vanilla's briefing block plus
prose paragraph is two `gameJournalQuestDescription` entries on one objective -
Hot Fuzz ships exactly that, `01_go_to_notell_judy/description` and
`01_go_to_notell_judy/judy_notell` - and the line breaks inside the block are
written into the localized strings, because the engine's own separator is a
single space. `description + "\n";` in `questLogDetailsPanel` discards its
result and never runs. So adding a briefing header here is a text change on a
LocKey plus one extra description entry, not a new mechanism. Still unrequested,
now cheap and understood.

**And the same six lines expose a defect this quest does have.** All twelve
descriptions are activated and none is ever retired, while a Succeeded
objective's Active description keeps being returned. The panel would therefore
have grown from one paragraph to nine run together with single spaces, and a
`phase_revision` re-entry produces the whole pile in one frame rather than
gradually. Eight retirement nodes fix it; they are built and verified in
`source/quest_graph.d54-proposed.json` and cannot be applied from this session -
`source/quest_graph.json` is refused by the permission classifier. See D54 and
OI-15.

## OI-19 — Cynosure loads, and nobody knows whether it can be walked   (2026-09-04, D31)

**The way in is built and verified; the thing on the other side is not.**

`source/cynosure_graph.json` ships as its own injected phase and holds
`#q305_pr_outer_bunker` and `#q305_pr_inner_bunker` streamed while
`ashcache_cynosure_open` is 1. The mechanism is verified against vanilla — that is
exactly how `q305_06_outer_bunker` and `q305_07_inner_bunker` load their own
sectors, and `reference/examples/quest_prefab_streaming.json` records where each
ref was read. The resource round-trips through WolvenKit with both refs and the
release condition intact.

What is **not** verified is everything after the geometry arrives. Loading a
sector is not running the quest that owns it: the airlocks, the Cerberus, the
lighting states, the devices and the set dressing are all graph nodes inside
q305_06/q305_07, and those phases are not active. The honest prediction is an
empty, dark bunker with some doors shut, and possibly no legitimate way from the
outer bunker to the inner one.

That is why the fact defaults to 0 and why nothing in this mod sets it —
`validate.py` fails the build if anything ever does, and `negtest.py` holds it.

**UPDATE 2026-09-22 (D129).** This is no longer blocked on a decision, it is
blocked on one save load. D116 pulled the phase after every save crashed at
world load, and its bisect table still has an empty cell — the Cynosure phase
*alone*, never measured. That build now exists: `mod/bisect/`, two files, its
own README, `phase_revision 2` so the marked saves from 09-04..09-17 can still
answer. Fill that cell before any of the three questions below are worth
asking. Also measured, and it changes where the lab is: the outer bunker's node
transforms put Cynosure at X -2411..-2074, Y -2598..-2166, Z -208..-57 — under
Dogtown, with the motel inside its footprint, not under the Badlands.

**UPDATE 2026-09-22 (D131).** The *surface* is no longer waiting on this. The
shaft head is now a site the player works — three things to do, two documents,
and a facility that describes itself floor by floor from its own maintenance
port (see D131). That is deliberately everything that can be done without the
geometry: what remains behind this issue is walking down there, and that is
still one save load away. `mod/bisect/` is built and has not been run.

**To test:** CET panel → `world_state` → `ashcache_cynosure_open` → 1, then
travel to Cynosure on foot and look. Three questions, in order:

1. Does the exterior/outer bunker geometry appear at all?
2. Can the outer bunker be entered without q305's airlock scripting?
3. Does the inner bunker appear, and can it be reached from the outer one?

If (1) fails, the phase is not running — bump `phase_revision` in
`source/cynosure_graph.json` (OI-15: a save that once loaded a build is
permanently marked as having run that phase node). If (1) works and (2) fails, the
next lead is `q305_bunker_airlocks_controller.questphase` and
`q305_outer_bunker_malfunctioning_doors.questphase`, both kept at `/mnt/sata/Cyberpunk2077/questmod-research/q305_keep/`; the second is
one of the six output-less ambient phases and may be copyable wholesale. If (3)
fails, q305_06 node 476 is the shape to copy — `questShowWorldNode_NodeType` with
`show: 1` on `#q305_pr_inner_bunker`, which is what vanilla uses to reveal the
inner bunker early, and the generator does not emit that node type yet.

**Do not add scripting speculatively.** Every one of those is cheap to add once a
playthrough says which of the three failed, and expensive to debug all at once.

**UPDATE 2026-09-22 (D132).** The question may no longer need answering. This
issue has always assumed that walking Cynosure means walking CDPR's Cynosure —
the 381 quest-category sectors behind D116's load-time crash. It does not.
`worldCollisionNode` stores its actors and box shapes inline rather than
referencing a baked physics cache, WolvenKit round-trips a vanilla one to
byte-identical JSON, and `gen_sector.py` can now emit both halves of a piece of
geometry: `meshes` for what is drawn, `collisions` for what holds the player up.
An interior built that way lives in one of this mod's own sectors, which have
never crashed, at any depth we choose. The bisect still decides the fate of the
injected phase and of the vanilla bunker; it no longer decides whether there is
a Cynosure to walk. `ac_probe_geometry` at the landfill is the one test that
gates it - see D132 for how to read it.


## OI-20 — Nothing proves a choice option's voiceover is ever played   (2026-09-04, D40)

`alloc_subtitle_ids.py`, `gen_subtitles.py`, `validate.py`, `negtest.py` and
`gen_scene.py` all walk `nodes[].lines` **and** `nodes[].options`. That is where the
project's count of 43 spoken lines comes from: 29 lines plus 14 choice options. Every
one of the 43 has a reserved LocKey, a ruid, and a slot `gen_vomap.py` will fill the
moment a matching `.wem` appears in `vo/<locale>/`.

What is not established is whether the engine ever *plays* the 14. A line is spoken
because a `scnSectionNode` carries a `scndialogLineEvent` for it with a start time and
a duration. A choice option has no such event: it lives in a `scnChoiceNode`, which
hangs waiting for the player, and `gen_scene.py` correctly gives it no duration —
there is nothing to time. So the option's audio has a voiceover-map entry pointing at
it and, as far as anything here can tell, no trigger.

Three possibilities, and this machine can distinguish none of them:

1. The engine plays a choice option's VO when the option is highlighted or selected,
   driven off the `locstringId` rather than off a dialog event. Then all 43 are
   voiced and nothing needs to change.
2. Vanilla scenes never voice the wheel text — the wheel is a paraphrase, and V's
   spoken version is a separate line in the section node that the choice leads to.
   Then this quest is missing 14 section-node lines, and the option `.wem` files are
   dead weight the packer still ships.
3. It depends on the option's `usage`/`type`, which is where a vanilla scene with
   voiced choices would show its hand.

Reading a shipped `.scene` cannot settle it either, because the question is about
runtime behaviour, not the file format.

**What decides it:** put a `.wem` on one option key (`mara.opt_level`), leave its
neighbours silent, run the scene, and listen at the wheel. If option audio plays, (1)
holds. If it does not, the fix is structural — every choice needs a following section
node carrying V's spoken line — and that is a graph change, not an audio one.

**Meanwhile:** `render_lines.py` renders all 43, because that is what the other five
tools already assume and 14 unused `.wem` files cost 3 MB, while 14 silently
unrendered lines cost a third of the quest's voice. Do not read the presence of those
files as evidence that they are heard.

---

## OI-21 — Nothing proves the game can play a `ua-ua` voiceover at all   (2026-09-04, D41)   **RESOLVED AS MOOT (2026-09-04, D42)**

Before any more effort goes into Ukrainian VO, this has to be answered, because
if the answer is no then `vo/ua-ua/` is 43 files the engine never opens.

**What is on disk.** The install has exactly two voice archives, and they are the
same language:

    game/archive/pc/content/lang_en_voice.archive
    game/archive/pc/ep1/lang_en_voice.archive

Twenty-two `lang_*_text.archive` files sit beside them, `lang_ua_text.archive`
among them — Ukrainian is an official **text** localisation and has been since
2.0. There is no `lang_ua_voice.archive`, in `content/` or `ep1/`, and CDPR has
never shipped one.

**What ArchiveXL does with our vomap.** From source, not from the DLL —
`src/App/Extensions/Localization/Extension.cpp:341`:

```cpp
for (auto& entry : map->entries)          // the game's locVoLanguageDataMap
{
    for (const auto& unit : m_configs)
    {
        auto paths = unit.vomaps.find(entry.languageCode);
        if (paths != unit.vomaps.end())   // only if the game ALREADY has it
            ...  entry.voMapChunks.PushBack(ref);
```

It iterates the languages the game already knows and merges into the ones it
finds. It cannot add a language. A `vomaps` key naming a language the map does
not contain matches nothing, pushes nothing, and logs nothing about that specific
key — if no key matched at all the log says only `No voiceover maps to merge`,
and if *another* locale matched it says `All voiceover maps merged` and the
unmatched one is invisible. Either way the failure is silent, which is why this
is written down rather than assumed.

**What is not known.** Whether `ua-ua` is an entry in `locVoLanguageDataMap` at
all. The string `ua-ua` does occur in the executable, but as the text locale
code — that says nothing about the voice map. Three possibilities:

1. `ua-ua` is not in the map. Our vomap is inert; `vo/ua-ua/` is dead weight.
2. `ua-ua` is in the map but has no audio, and the Voice Language selector is
   built from installed `lang_*_voice` archives. It would still be unreachable.
3. `ua-ua` is in the map and the selector offers it once *any* source supplies
   audio for it — in which case our mod could be that source.

**The test, in game.** Settings → Audio (or Language) → **Voice Language**. If the
dropdown offers only English, it is 1 or 2 and Ukrainian voiceover cannot ship
regardless of how good the synthesis gets. If Ukrainian appears after the mod is
deployed, it is 3. The `red4ext` log will also say `Merging entries from ...` once
per vomap it accepted; two lines means both locales took, one means only en-us.

**What this does not block.** `vo/en-us/` is unaffected — English is the one voice
language present, and the English chain is the one the player judged acceptable.
The Ukrainian *subtitles* are unaffected too: those go through
`localization.subtitles.ua-ua`, which is a text language the game demonstrably
has. Nothing here changes what a Ukrainian player reads; it only decides what
they hear while reading it, which in vanilla is English.

Related: OI-16 (voice pipeline), OI-20 (whether option audio is ever played),
D41 (why the Ukrainian is synthesised natively instead of converted).

**RESOLVED AS MOOT — 2026-09-04, D42.** The in-game check this issue was waiting
on is no longer worth making, because the answer stopped mattering. The owner
decided Ukrainian ships as text with English audio:

> "i'm already used to the English voiceover, so it's not a problem for me to
> listen to English, and English sounds better on the training data, so
> Ukrainian is not necessary."

`vo/ua-ua/` will never be populated, so whether the engine could open it is a
question about a directory that stays empty. `VO_LOCALES = ["en-us"]` in
`tools/gen_vomap.py` is now the single place that decides this, and
`render_lines.py` refuses to render a non-VO locale into `vo/` at all — so the
43 files this issue warned about cannot be created by accident.

The finding itself is still true and still worth keeping: **ArchiveXL cannot add
a voice language, only merge into one the game already has.** If a Ukrainian dub
is ever wanted, this issue reopens as the *first* thing to test, before any
audio is made. Nothing else in the mod is affected — the Ukrainian subtitles
travel via `localization.subtitles.ua-ua`, which is a different merge point with
a different hook and is already proven working in the packed archive.

### 2026-09-09 - resolved in principle by D71

The premise of this issue was that a choice option gets no `scnAudioEvent`, so
nothing plays its recording. That framing died with the discovery that
`scnAudioEvent` was never the path to scene audio at all. `dialogs:` is keyed by
the locstring ruid, and every choice option has one - they are allocated in
`source/subtitle_ids.json` exactly like spoken lines. All 43 voiced keys are now
registered, options included, through the same door. Whether the engine actually
raises a dialogue line for a hovered or selected option is still unobserved, so
this stays open until the scene is heard once.


## OI-22 — The game needs 3-4 `./start` attempts before a session survives   (2026-09-09)

The user cannot test: "it's not possible to test normally with these stupid
crashes". Eight launches between 20:40 and 21:15 produced three usable sessions.

The fact-3 half is fixed - see D72, it was our CET panel writing facts from the
render thread. This issue is only the *other* half: launches that reach the main
menu and then end with **no crash log at all**.

From `CrashLogger_trace.log` and the CET/RED4ext logs, the failed attempts
(20:55:52, 20:57:08, 21:03:28, 21:05:47) all:

- reached `deferred init complete - game running` ~18 s in,
- compiled redscript to completion (~61 s in, 158 KB of warnings, no errors),
- loaded `ash_cache_debug` at ~65 s, so CET and the main menu were up,
- then ended within 10-90 s with **no `crash_*.log` and no FATAL trace line**,
- and wrote **no audioware log**, so the world was never entered.

Ruled out already:

- **OOM** - nothing in the kernel log, 28 GiB of swap free, peak process private
  12.2 GiB against 31 GiB physical.
- **Leaked wineserver** - none alive after the crash, and `start` already clears
  stale servers for this prefix (lines ~140-222) before launching.
- **A mod failing to load** - the RED4ext logs for a failed and a successful
  launch are byte-identical, 7130 B / 58 lines, zero errors.

No SEH exception means CrashLogger cannot see it: the process is aborting or
being terminated below the exception path. The two candidates that behave this
way are a DXVK/VKD3D device loss (`VK_ERROR_DEVICE_LOST` -> abort) and an
amdgpu ring reset. **Both are currently invisible**, because `start` line 45
hard-sets `export DXVK_LOG_LEVEL=none`, and `dmesg` on this machine is
restricted (`kernel.dmesg_restrict=1`), so the kernel log cannot be read
unprivileged.

Next step is evidence, not a fix: make `DXVK_LOG_LEVEL` overridable the way
`DXVK_FRAME_RATE` already is via `CP_FPS_CAP`, and capture `sudo dmesg -w` for
amdgpu resets across one failed launch. Note this machine has a history of
amdgpu page faults under ROCm load (see the fp16 training work), so the GPU is a
live suspect rather than a guess.

The ~62 s redscript recompile before every attempt is inherent - redscript
rebuilds `final.redscripts.modded` from 113,841 source refs each boot - and is
not a fault, but it is what makes four attempts cost eight minutes.

### OI-22 update (2026-09-10 01:00) - answered, and it was not a crash

Resolved by `crashlogs/session_*.log`, which the `start` script has been writing
all along and which OI-22 was opened without reading. The tee block appends
`=== wine exited rc=N ===` after wine returns; every session with a crash log
has that line and not one of the seventeen "didn't start" launches does. The
pipeline was killed with the game still executing - the trace log shows the
21:31 launch alive at +73s - so these were abandoned launches, not failures.

They all go quiet at the same point, +68 to +79s, between the Streamline DLL
signature block and `Loading input configs from r6/input`; in a launch that
went on to reach the menu, that gap was 12 seconds. Silence tolerated before
each kill: 7s, 7s, 25s, 30s, 36s, 39s, 57s, 66s, 66s, 82s, 92s, 99s, 108s,
145s, 158s, 284s, 631s. The 631s one was a genuine hang. Nothing on screen ever
distinguished it from the 7s ones, which is what actually needed fixing.

Fixed in `start`: a heartbeat line every 15s carrying the game's cpu and rss
during the quiet window, and `DXVK_LOG_LEVEL`/`VKD3D_DEBUG` no longer pinned to
`none` (defaults `info`/`warn`, overridable with `CP_DXVK_LOG`/`CP_VKD3D_LOG`).
Backup of the pre-change launcher: `start.bak-2026-09-09-dxvklog`.

Ruled out earlier and still ruled out: OOM, leaked wineservers, plugin load
failure. Also ruled out now: the GPU. The user's `dmesg` across the whole
evening carries no amdgpu line at all - only USB and bluetooth - so the ring
reset theory in the original OI-22 entry is dead. The ~61s redscript recompile
per boot is real and inherent, and it is most of the quiet window.

Open only as: does the game ever hang there for good, or does it always recover
if left alone? The heartbeat answers that on the next occurrence.

### OI-22 reopened and re-answered (2026-09-10 01:40) - it WAS a fault, just not a fatal one

The previous entry closed this as "not a crash, the pipeline was killed". Half
right. The pipeline was killed, but only because the game had already faulted:
signature `E4044E73`, a null deref on a `redDispatcher*` job thread at
`Cyberpunk2077.exe+0x216814`, ~74s into the launch. See D74.

Established, not assumed: 25 fatal crash logs carry it, starting 2026-08-06 -
before this quest existed - across 11 days; plus 38 first-chance hits in 294
trace sessions. Baseline, third-party, load-order race.

Answered: the launches were failing for a real reason, at a fixed point, and
`start` now detects it in ~74s and relaunches automatically (`CP_MAX_TRIES`,
default 4). The 5 GiB zombie process left behind by Ctrl+C is also fixed.

Still open, and only worth chasing if the retry stops winning:
- which archive or plugin loses the race. Codeware.dll, NewGamePlus.dll and
  ArchiveXL.dll appear in the stack scan, but as scan hits, not real frames.
- whether the fault rate tracks archive count.

### OI-22 update (2026-09-10 02:05) - the watchdog is live and has run

First real run: two automatic relaunches, then a stop one attempt short because
a FATAL crash exit was read as a normal quit. All three defects fixed and
tested against stub processes; see D75. Still open:

- No launch has yet reached the menu with the watchdog running, so `MENU_RSS`
  (7 GiB) is an untested guess. The `cpu < 5%` clause is the real guard.
- Which archive or plugin loses the load-order race is still unknown, and the
  retry loop deliberately does not answer it - it treats the symptom.
- Watch for a night that burns all four attempts. That is the signal the race
  has gone deterministic, and at that point the mod list is what to look at.

### OI-22 update (2026-09-10 02:40) - the corrected watchdog worked on a real launch

First real-world run of the D75 fixes, session `02-24-40`:

```
[start] STARTUP FAULT confirmed: null deref, load frozen at 5081 MiB. This launch is dead.
=== wine exited rc=1 at 2026-09-10 02:26:16 ===
=== relaunch 2 of 4  2026-09-10 02:26:19 ===
[start] +111s  past the stall point at 7753 MiB - watchdog off
```

The trace confirms the fault at 02:25:53, +73s after launch - so the fast
detector armed (it never did before, the path was wrong), confirmed on the next
sample, killed at +96s instead of +190s, and the relaunch loaded clean. The
session then died at 02:32:37 to a *different* crash (`E815263E`,
`Cyberpunk2077.exe+0x53F9D4`, faultaddr `0x700000001`) and the loop correctly
did **not** retry, because `REACHED_MARK` was set. Both halves of D75 behaved.

`MENU_RSS = 7 GiB` is no longer a pure guess: the healthy load passed it at
7753 MiB while stalled loads park at ~5.0-5.1 GiB. Comfortable margin.

### OI-23 - game audio can land on the wrong PulseAudio sink (2026-09-10 02:40)

Open. `module-switch-on-connect` is not loaded, so a stream never follows a sink
that appears after it. The Bluetooth headset (`HOCO W35 Air`) idle-disconnects,
so a game launched while it is away plays into S/PDIF forever - which reads in
game as "all sound is gone". See D76.

Mitigated, not closed:
- `start` now logs `[start] audio: ...` lines at the watchdog disarm point and
  moves misrouted streams once.
- `/mnt/sata/Cyberpunk2077/audio-doctor.sh` handles the reconnect-later case
  (`--fix`), and `--level` measures whether a stream carries PCM at all.

Closes when a silent session's `[start] audio:` lines are seen. If they show the
streams already on the default sink, D76 is wrong and the search moves inside
the engine. The permanent fix, if the player wants it, is
`pactl load-module module-switch-on-connect`.

### OI-13 update (2026-09-10 03:05) - the spawner half is answered "not the crash", the device half is now under test

The `worldPopulationSpawnerNode` accusation is withdrawn. `ash_cache_probe_npc`
did not ship in the 01:21 archive and the clinic killed the game anyway at
02:32:37 (signature `E815263E`, `-1899,-2479,24`). Whether that node type accepts
a `Character.*` record is still unknown - it never ran - so **keep the sector,
keep the flag, and do not delete `ac_probe_npc`.**

The device half is now the live test. All three `worldEntityNode`s
(`ac_splinter_box`, `ac_terminal_pc`, `ac_probe_computer`) are flagged
`disabled` in `source/world.json` and are absent from archive
`6e9ccc7bb6846ee8c62cb4a888aea3bf`. See D77 for the argument and for what each
outcome means. Not deployed - needs the user's word.

### OI-24 - the clinic floor at -1899,-2479,24 corrupts something (2026-09-10 03:05)

**Open.** Four fatal crashes there, three distinct signatures, one square metre.
Not the CET panel (`report.txt` untouched in the fatal session), not the spawner
probe (absent from the build), not the in-game settings. The current suspect is
the three null-`instanceData` device masters; the bisect archive is built and
waiting.

Closes when one launch reaches that spot and stands there without dying, with
the `[start] audio:` lines and `breadcrumb.log` both captured. Reopen the moment
a fifth crash lands within 2 m of it.

### OI-23 update (2026-09-10 03:05) - the routing explanation is confirmed by the player

"The sound in the game appeared after I logged in again" - a fresh login
recreated the streams while the headset was the default sink, which is exactly
what D76 predicts and is the second half of the evidence that was missing. The
open question it answers: connecting the headset **while the game is running**
does not move the game's audio, because `module-switch-on-connect` is not loaded.
`audio-doctor.sh --fix` is the live workaround; the module is the permanent fix
and is the user's call.

### OI-24 update (2026-09-10 11:45) - fifth crash, props cleared

Fifth fatal at `-1899,-2479,24`, with the props-disabled archive verified running
(`6e9ccc7bb6846ee8c62cb4a888aea3bf`, deployed 11:28, session started 11:28:11,
fault 11:36:12). D77's device-master hypothesis is dead.

Sharper than before:

- The three `93CABB10` crashes have **identical 14-frame stacks**. This is one
  deterministic bug, not three threads tripping over debris. Only `17370EC2` and
  `E815263E` remain unexplained singletons.
- `93CABB10` appears in 3 of 249 crash logs, all at this coordinate, none before
  2026-09-09 20:50. Not baseline.
- Fault shape: `read at 0xFFFFFFFFFFFFFFFF`, `RDI = 1` - a lookup that returned
  -1 and was dereferenced. Hash miss, not a freed object.
- The CET dev panel is **not installed** on this machine at all
  (`mods/ash_cache_dev` does not exist), so it can never have been involved.
- The glue's 25 m sphere is not the trigger: the player stood inside it for ~2
  minutes, saved twice, and only died on descending z=28 -> z=24.
- The motel sector - markers-only, `AlwaysLoaded`, 340 m away - has never
  crashed. That control clears "marker node in a mod sector" on its own.

**Closes when:** one launch reaches `-1899,-2479,24`, stands there 30 s and does
not die, with `breadcrumb.log` and the `[start] audio:` lines captured.
**Reopen on:** a sixth crash within 2 m.

**Next action (needs a run, not a build):** `tools/modoff.sh off`, launch, walk to
the spot. This is the control that has never been run - is the crash ours at all?
`tools/modoff.sh on` restores everything byte-identical. See D78 for what each
outcome means.

### OI-23 update (2026-09-10 11:45) - closed in practice

The 11:28 session routed correctly: default sink was
`bluez_sink.A4_DB_BB_C8_79_F6.a2dp_sink` and all three game streams were on
sink 16, unmuted, 100%. The player connected the headset before launching, which
is the workflow D76 prescribed. The permanent fix
(`pactl load-module module-switch-on-connect`) is still offered, not applied -
it changes routing behaviour for every application on the box, so it is the
player's call.

### OI-24 update (2026-09-10 12:37) - it is our archive, and the probe car is the suspect

The player emptied the whole mod tree and put back only ours. The 12:21 session
ran on two archives, both `ashcache`, and reproduced the clinic instruction
(`crash_20260910_122313.log`, ID `1912746313+0x1E`, fifth hit, 50 s after
`OnWorldAttached`). Nothing else was installed, so the baseline-crash-rate
argument is dead and the fault is ours. Full reasoning and the census in **D80**.

Both probe sectors are now off. The archive ships six inert `worldStaticMarkerNode`s
and no other world node: no spawner, no trigger, no prop. md5
`0ebdad641923df831c4aeb3ee3dcf140`, built 2026-09-10 12:37, all four test suites
pass. Needs deploying and one launch to the clinic.

- **lives** -> put the two probes back one at a time; `ac_probe_car` first, and
  fix `spawnOnStart: 1` -> 0 and `appearanceName: "default"` before believing any
  result from it.
- **dies** -> no world node can be the cause. Next surfaces are the questphase
  (two phases, five parents each in the `.xl`), the journal, and the ArchiveXL
  streaming block itself.

Not yet checked, and the cheapest remaining offline work: whether
`appearanceName: "default"` is legal on a `worldPopulationSpawnerNode` at all.
`gen_sector.py` defaults every node kind to it, which is right for a
`worldEntityNode` prop and unevidenced for a spawner - `reference/sectors.md`
does not record the field for the five vanilla spawner samples it read.

### OI-20 update (2026-09-10 13:00) - the scene audio path, measured against a working mod

Everything on our side that CAN be checked offline now checks out: 43 dialogs
registered in Audioware's scene registry (774 = 43 x 18 locales, "no scene error
reported"), keys equal to the scene's locstring ruids, bank deployed and md5
-identical to the build, vomap/subtitles/scene stringIds all in agreement, the
`.wem` readable as a Wwise RIFF by `vgmstream-cli`, and VoiceOver set to en-us
so the en-us-only vomap is the right one. See D81 for the full comparison.

Two candidates remain, both offline-fixable, ranked:

  1. **No `stringidvariantlengthsreport` entry per line.** Audioware's own
     documentation lists this as required for scene dialogue and gives the only
     known route - a Codeware `Resource/PostLoad` callback on
     `base\localization\en-us\stringidvariantlengthsreport.json` pushing a
     `locVoLengthEntry` with femaleLength/maleLength per stringId. We have the
     durations already: `gen_scene.py:vo_lengths()` measures every recording.
     BLOCKED right now only by tooling: this needs Codeware's redscript
     declarations, and `r6/scripts/` currently holds `AshCache` alone because
     the player emptied the tree for the crash bisect. `tools/lint_glue.sh`
     cannot type-check a Codeware symbol until those are back.
  2. **PCM `.wem` on the voiceover path.** Never verified, and the 25th shipping
     mod is still Vorbis. If (1) does not fix it, this is next, and the answer
     is the Wwise route in `docs/voiceover.md`.

### OI-24 update (2026-09-10 13:00) - the clinic instruction did not fire

`crash_20260910_124402.log` is NOT the clinic bug. Faulting instruction
`4266871082+0x30`, signature `8403A30D`, thread 532 `redDispatcher9`, read at
`0x2C84` via `RDX+0x2163` with `RDX = 0xB21` - a small integer used as a struct
pointer. First and only occurrence in 257 crash logs. The clinic instruction
`1912746313+0x1E` stays at 5 hits, none since 12:23.

So the markers-only archive did not reproduce the world-node fault. What it did
do is die during load: `[start] died during load with rc=5`, at +122s, 64s after
the save's `OnWorldAttached` at 12:42:58 - the same shape of timing as the 12:23
death (50s after attach) but a different instruction.

Next surfaces, now that the world is six inert markers: the two `.questphase`
files (5 parents each in the `.xl`), the `.journal`, and the ArchiveXL streaming
block. The 20 dead `scnAudioEvent`s removed under D81 are also gone from this
build - two unresolvable CNames per line was the same fault shape, though they
only fire when a scene plays.

### OI-20 update (2026-09-10 13:15) - found, and it was never in our archive

Root cause proven in D82: Audioware's redscript half (`r6/scripts/Audioware/`,
18 files) is not installed, so `Audioware.OnGameSessionReady()` is never called,
so `engine.scene` stays `None`, so `play_scene_dialog()` returns at its first
guard for every line. The log says so in words:
`scene is not available, and therefore dialogs aren't either`, twice, at the two
lines the user tried.

Blocked on ONE user action - restoring 18 files into the game tree:

    cp -r "/mnt/ssd/Cyberpunk 2077/copy/r6/scripts/Audioware" \
          "/mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game/r6/scripts/"

Verified before proposing: byte-identical to the source of the exact dll build
installed; namespaced `module Audioware`; only external import is Codeware, which
is installed and compiling.

Ranked remainder, unchanged in order but now behind a proven cause:
1. `stringidvariantlengthsreport` entries - UNBLOCKED (Codeware's reds live in
   `red4ext/plugins/Codeware/Scripts/`, not `r6/scripts/`; D81 was wrong about
   this). Held deliberately: one change at a time, and a bad .reds costs a boot.
2. PCM vs Wwise Vorbis `.wem` - only matters for the vanilla vomap path, which
   runs in parallel; Audioware's detour always calls through
   (`hooks/audio.rs:95`, "still let the engine carry on, to handle subtitle").

### OI-20 update (2026-09-10 13:30) - the reds restore took; the crash is a separate, older problem

D82's restore is confirmed in the log: 18 Audioware `.reds` compiled at 13:21,
zero `scene is not available` warnings (two in the 13:07 session). Audio still
unheard - the 13:23:14 crash landed before a line could be tried.

That crash is signature 88087014, instruction 3858698886+0x20, on a
`redDispatcher` worker. Its twin from 2026-08-29 has frames [0]-[3] identical and
`grep -ci ashcache` = 0. Across 259 crash logs, 214 (83%) were recorded with our
archive not installed. Full numbers in D83.

Both wiki guides the user cited were checked against the build line by line;
everything in them is already implemented except the `.wem` encoding, which
`docs/voiceover.md:94-121` chose deliberately. Ranked remainder, unchanged:

  1. `.wem` is raw PCM (fmt 0x18, tag 0xFFFE, 1ch) where every working custom-VO
     mod on this machine ships Wwise Vorbis (fmt 0x42, tag 0xFFFF). Only affects
     the vanilla vomap path. Fixing it needs Wwise 2023.1.14, which is not
     installed here. Audioware's bank is `.wav` and is unaffected.
  2. `stringidvariantlengthsreport` via a Codeware Resource/PostLoad service -
     unblocked (Codeware compiles), still held until a line is heard.

Next test is cheap and needs no rebuild: reach a Mara line with the restored reds
in place and say whether anything is audible.

### OI-20 / OI-24 update (2026-09-10 16:15) - the crash is ours, the cut is built, one command runs it

D83's "the crash predates this mod" is withdrawn: it censused the baseline
instruction, not the clinic one. See D84. The clinic instruction
`1912746313+0x1E` has 6 hits, every one with `ashcache` in the log, none in the
251 logs before 2026-09-09 20:50.

Crash #6 (13:39 today) ran on the D80 probe-free archive, so **no world node is
the cause** and `ac_probe_car` is cleared. The user's reproducer is the CET Acts
tab, `Act 3 - at the clinic, box found`: subtitle renders, voice line does not
sound, job worker faults. Audioware's own playback works throughout.

**Next test - built, not yet deployed, needs the user to run two commands.**

    cd /mnt/sata/Cyberpunk2077/ash-cache-quest
    tools/deploy.sh --only .archive.xl --yes

That replaces one file and removes two lines from it (the `vomaps:` block). The
archive already in the game is not touched. Then launch, CET -> Acts ->
`Act 3 - at the clinic, box found`.

  - survives  -> the `.wem` encoding is the bug. Wwise is the fix; the prefix
                 build is already running at /mnt/sata/wwise/.
  - still dies -> the vomap is cleared as well. What is left inside the archive
                 is the questphase, the journal and the scene resource.

To put the voiceover back: `tools/build.sh && tools/deploy.sh --only .archive.xl --yes`
(without `ASHCACHE_NO_VOMAP=1` the block returns).

**Wwise on Linux (was: blocked, no Wwise installed).** Now in progress.
`/mnt/sata/wwise/setup-prefix.sh` -> log at `/mnt/sata/wwise/setup.log`. The
winetricks stage downloads the Win7 SP1 package for `wininet` and is slow. When
it finishes, the launcher install and login need a human:

    WINEPREFIX=/mnt/sata/wwise/prefix wine /mnt/ssd/Downloads/AudiokineticLauncher-2026.1.1.6296.exe

then the xdg-scheme steps from the user's guide so the browser login can hand
back to the launcher, then install Wwise **2023.1.14** (the version the modding
guide pins - not the launcher's own 2026.1.1).

### OI-20 update (2026-09-10 22:35) - RESOLVED. The lines play; the echo was the other route

Player, on the first test after D92 deployed: "the sound problem is officially
fixed ... it sounds really cool, just like Vanilla, and you can hardly tell the
difference from the in-game voice." OI-20 asked whether a quest line is ever
heard. It is. Closed.

One defect came with it - "there's a lot of echo in Rogue's voice" - and it is
not the recordings (nothing in tools/ adds reverb; vo_polish.py ships them dry
deliberately). Audioware's AUDIO_PLAY_DIALOG_LINE detour plays its copy and then
calls the engine unconditionally ("still let the engine carry on, to handle
subtitle"), which is harmless for a modded line with no locVoiceoverMap entry
and is not harmless for ours, which now has one that resolves. Two copies, one
dry through Audioware, one wet through the dialogue bus. D93 makes the two
routes mutually exclusive with the engine's as primary and the bank as the
fallback for a machine with no Wwise.

Note what the echo proves: the vomap path is carrying the line. It cannot double
what it is not playing. So removing the Audioware copy cannot return this quest
to silence - which is the one risk worth checking before removing it.

Still open, and now testable for the first time: OI-17 (lipsync) hangs off the
engine's voiceover path, which is the path that works. V's lines are unheard -
the player tested Mara's only.

### OI-21 (2026-09-11 02:20) - clicking Acts 3 crashes the game, and has since 2026-09-09

**Status: OPEN, reproducible, instrumented, blocking testing.**

Player: "when i logged back in, I couldn't click on facts 3 because it crashed".

Faulting instruction `1912746313+0x1E` (`Cyberpunk2077.exe+0x1D173BE`), read at
`0xFFFFFFFFFFFFFFFF` with `RDI = 1` - an unchecked -1 out of a hash lookup, on a
`redDispatcher` job thread. **8 occurrences in 265 crash logs, all eight stacks
byte-identical:** 2026-09-09 20:50, 21:43; 2026-09-10 11:36, 12:10, 12:23,
13:39, 16:24, 22:47. Signatures `93CABB10` and `417F3DF0` are the same
instruction (the signature hash folds in read-vs-write), which is why counting by
signature undercounted it.

Independent of everything changed this week: it reproduces with props on and
props off, with the Audioware bank and without it, before the `.wem` existed and
after. D73's spawner-node suspect is retired - the clinic sector in the current
build holds four `worldStaticMarkerNode` and nothing else.

Next test round should answer it. The panel now writes `trail.log` (flushed per
line) next to `init.lua`, and the Acts tab has a **step** checkbox that applies
one queued fact write per press. What to do, once:

  1. Load, open CET, Acts tab, tick **step**.
  2. Press an Acts button - it queues six writes and applies none.
  3. Press **apply next** repeatedly, one press per second or so.

Then either it never crashes - the burst cadence is the cause, and the fix is to
slow the drain - or it crashes on one specific press, and the last `wr->` line in
`trail.log` names the exact fact. Send `trail.log`.

### OI-22 (2026-09-11 02:20) - a new crash on the last dialogue line

**Status: OPEN, seen once.**

Player: "The game crashed on the last line".

22:45:13, signature `DE41E2DF`, instruction `766120943+0x6`, `redDispatcher11`,
read at `0xFFFFFFFFFFFFFFFF`. **Every frame of its 17-frame stack appears in
exactly one of 265 crash logs - this one.** A path never walked here before,
which is what D92 would produce: the engine's voiceover route is decoding this
quest's Vorbis for the first time.

Not the assets. All 43 `.wem` re-read with `vgmstream-cli -m`: 43/43 parse as
Wwise RIFF / Custom Vorbis / 48 kHz, none truncated mid-stream.

The mara scene's tail is section 12/13/14 (the last spoken lines) ->
`questFactsDBManagerNode` (`mara_trusted` / `mara_hostile` / `mara_break`) ->
`mara_choice_made` -> `questSceneManagerNode` back to `Tier1_FullGameplay` ->
end. `trail.log` distinguishes those from each other: if the trail carries
`mara_choice_made` the scene finished and the fault is on the exit path; if it
stops at the last `fact` line the scene died mid-section.

Seen once. Do not chase it until the trail says which half it is - and note that
OI-21 fires on the way in, so OI-21 has to be got past first.

### OI-21 update (2026-09-15) - not the burst; one selector cleared; the game tree was stale

Step mode reproduced the crash with writes seconds apart, and the trail ends
after `box_opened`'s write returned. The trigger is that single edge's downstream
work: the Mara spawn (D86 control). D95 clears the actor-level
`specCharacterRecordId`, which no reference actor populates. The game directory
had been rolled back to the 2026-09-10 11:53 set, so it needs a full
`deploy.sh --yes` before the test means anything. Test from the save that crashes.

### OI-21 update (2026-09-15 18:00) - D95 did not move it; the crash window is three nodes wide

D95 deployed and verified, and Acts 3 still crashed (`crash_20260915_175232`, same
`1912746313+0x1E`). Two new facts. This time the fault is a **write into the exe's
read-only image data** (exe+0x2B2B060, ID 1413875527); the nine earlier crashes in
this function read 0xFFFFFFFFFFFFFFFF and one wrote 0x1, so the function is handed a
dangling or wrong-type pointer, not one fixed bad value. And the trail saw
`splinter_given` go to 1 in the same 0.25 s poll as the writes, first-chance fault
at 17:52:28.503. The graph between those points is `give_splinter` (the only grant
so far with `sendNotification=1`) -> `mark_splinter` -> `progress_4` ->
`obj_mara_on` (notifying objective) -> `meet_mara` (scene start). D95 changed only
the last one. The Acts 3 preset also writes `progress=2` after `box_opened`, which
can overwrite the graph's `progress_4` before a poll sees it.

The panel now stamps trail lines `HH:MM:SS.mmm fN`, and for 6 s after any write or
edge polls facts, the four quest items and objectives every frame with a `tick`
line per frame. The last `tick` before the crash is the last completed frame; lines
after it happened in the faulting frame. Needs only the CET init.lua deployed.

### OI-21 update (2026-09-15 18:35) - ManualSave-492 freezes on load, and the hang detector cannot see it

- **What happened:** two sessions (18:07 and 18:15) froze 13-21 s after V attached from ManualSave-492. That save was made at 17:51:40 at (-1895, -2489, 28), the spot of the Acts-3 crash. No exception and no dump. The trail and CrashBreadcrumb both stop on the same frame (18:12:32 and 18:24:33), after 0.3-0.9 s hitches, so the frame loop stalled.
- **What did not change:** the deployed archive is sha 8c73f8d8, byte-identical to the 17:34 build. With that build the 17:47 run loaded AutoSave-3 and walked to the same spot without trouble. The clinic sector holds 4 static markers, and every probe sector is disabled. The only other change is the CET trail's hot window, which had ended 7-15 s before each freeze.
- **Why no report:** CrashLogger's HangDetector was armed in both sessions and never fired, because the window kept answering WM_NULL. `cp2077-crash-logger/src/HangDetector.cpp` now also treats a `CrashBreadcrumb/breadcrumb.log` untouched for 10 s as a hang, and samples the main thread 3 times.
- **Next:** deploy the rebuilt .asi, load ManualSave-492, wait at least 20 s after the freeze, then read `bin/x64/CrashLogger/hang_*.log`. Its VERDICT line decides between blocked and spinning.

### OI-21 update (2026-09-15 18:52) - the load failures follow the 18:02 panel, not the save

A third load failed: `crash_20260915_184657`, signature 5C4457AE, an execute of heap
memory (0x1B9FA74C0, PAGE_READWRITE) on `redDispatcher5`, called from exe+0x14324C
(ID 2246119540+0x1EC). A job ran a dangling function pointer. Freeze session 2's
18:26:12 first-chance AV was the same shape (fault address = instruction address).
This save put V at (-2115, -2268, 18), 290 m from the clinic, so the spot is out.

The trail shows every session restoring progress 0 -> 3 on load, the good 17:47 run
included, so the quest state is out too. The one difference between the load that
worked (17:47, CET build 17:34) and the three that did not (18:07, 18:15, 18:40, CET
build 18:02) is the hot window's per-frame polling. A load opens that window by
itself (items 0 -> -1 at detach, -1 -> 0 at attach), so the panel called
`GetFactStr` on a `qs` cached in onInit, `GetEntryState` on cached journal entries,
and `GetItemQuantity`, every frame through teardown and attach. In the crash session
per-frame ticks ran up to the faulting frame.

Change (build 18:52, init.lua ab684f45): the hot window still writes a `tick` line
every frame, but polling is back to 0.25 s for facts and 1 s for items and
objectives. One variable. Test: load the same save; a minute of play past attach
confirms it. If it still fails, the panel is cleared and CrashLogger ce0cb012's
frame-stall report is the next evidence.

### OI-21 update (2026-09-15 20:40) - the crashing job was loading Mara's lipsync animset, and that path never shipped

- **The instruction, disassembled.** `1912746313` is `out = entries[*idx]` (16-byte handles, array at container+0x70) with no bounds check, then `lock inc` on the handle's refcount. The minidump of `crash_20260915_190752` (11th hit, stack identical to 17:52) gives idx = 1. The refcount pointer was -1 there and a pointer into `.rdata` at 17:52, so slot 1 is garbage: the array is shorter than 2 or already freed.
- **The thread named the job.** RedHotTools, installed 18:30, logged on thread 556 at 19:07:46.144. That is the faulting `redDispatcher8`, in the millisecond of the first-chance AV: `Resource not found: base\open_world\vendors\westbrook\japantown\wbr_jpn_prostitute_female\lipsync\en\wbr_jpn_prostitute_female\civ_prst_f_01_enus_30.anims`. The path appears once across six RedHotTools session logs.
- **That path is ours.** It is `LIPSYNC_NPC` in `tools/gen_scene.py`, Mara's entry `resouresReferences.lipsyncAnimSets[0]`. **OI-10's "they name base-game paths that are present anyway" was never checked, and is wrong.** `lang_en_voice.list` ships that set only at `base\localization\en-us\lipsync\...\wbr_jpn_prostitute_female\wbr_jpn_prostitute_female\civ_prst_f_01_enus_30.anims`. Vanilla tables dangle too (mq029), so the miss alone is normal; about 46 per session are harmless. But every vanilla NPC line is backed by a lipmap entry, and Mara's are not, because `lipsync/` is empty.
- **Not established.** The container type: `animAnimSet.animations` is at 0x40, not 0x70. Also why fresh runs survived.
- **Change.** `LIPSYNC_NPC` now points at the shipped en-us path (the VO language is en-us). The player path is unchanged. The built scene differs from the previous build in exactly that string. validate OK, negtest 96/96, replaytest OK, shapetest OK, glue lint 0/0. `ashcache.archive` sha256 353ace265b33…, `.archive.xl` 0374c39a37df….
- **Freezes.** Every hang report since 18:40 has RedHotTools on the main-thread stack, with CET in three of four and Codeware in two, reached through CET Lua. That includes the 20:03 session, which had no Ash Cache installed. The 18:07 and 18:15 freezes predate RedHotTools, and the 18:52 panel loaded a save and ran for 5 min.
- **Test.** The game currently has no Ash Cache files, so run `tools/deploy.sh --yes`, load the crashing save, then CET -> Acts -> 3. If it survives, OI-21 closes. If it crashes, send the crash log and the RedHotTools session log, and check whether a not-found line still sits on the faulting thread.

### OI-21 update (2026-09-15 21:45) - the pin is cleared; the fault is Mara's spawn loading her appearance, from an entity another mod patches

- **Gate test.** Debug build af27baaa299c holds `meet_mara` behind `ashcache_dbg_scene_go`. The `ac_pin_mara` pin was live 21:17:59-21:21:11 with no fault. The fact went to 1 at 21:21:11.049, and redDispatcher3 (t508) faulted at 21:21:11.326 (`crash_20260915_212116`, 0AFF1DC3). The pin is out; the scene start is the trigger. The silence while held is the gate working, not a bug.
- **The fault.** `3858698886+0x20` is `mov rdi,[r8]` with `r8 = [rcx+0x298]`. rcx is a static in the exe's .bss (ID 458427884+0xD00), and r8 = `A7CC66F800000001` is non-canonical, which Windows reports as a read of 0xFFFF...FFFF - so every "sentinel" read in this issue is a garbage pointer. Frame 7 is `ResourceSerializer_Deserialize` (2901686778, `cp2077-archive-xl/src/Red/Addresses/Library.hpp:174`). Frame 4 is 2057311186 (`dynamicBuffer.cpp`), which is also on the 20:55 stack. That is an already-corrupted engine allocator, hit by a loader job.
- **What the job was loading.** `diag/oi21_rtti/vanilla_scan.py` matches every archive-index hash (597k, vanilla + ep1 + mods) against dump memory. t508's stack holds `basegame_4_appearance` resources, including `base\characters\common\dismemberment\common\blood_dynamic_radial.mi`: character appearance materials, i.e. Mara's spawn, as D86 found. The 17:52 and 19:07 faulting stacks hold `ash_cache_mara.scene` itself.
- **Lipsync is not the lead, and the 20:40 reasoning was wrong.** Every lipsync path in all 8 census scenes (40 entries, NPCs and V) is a non-shipping `lipsync\en\` editor path. Hot Fuzz ships the same shape with no lipmap entry. Pointing `LIPSYNC_NPC` at a shipped file is not a vanilla pattern; it coincides with the signature moving from 1912746313 to the allocator, and it did not remove the fault. Revert candidate once the cause is known - not before (one variable).
- **Spawn fields are not the lead.** They have matched AldecaldosHighStakes' `regina_fake` since D87. What still differs is the character. `Character.q306_fia_agent_corpo_scene_wa.entityTemplatePath` = 3765170606357371005 = FNV1a64(`ep1\quest\main_quests\q306\characters\q306_fia_undercover_wa.ent`), and the installed `citizen_breast_physics.archive.xl` (2025-12-03) resource-patches `base\characters\entities\citizen_physics.ent` into that entity and about 500 others. No other installed mod references it.
- **Not established.** Whether this character faults without our scene. Whether the patch matters: it predates OI-21 by nine months, and hundreds of patched NPCs spawn normally.
- **Test.** A: CET console spawn of `Character.ashcache_mara` with her appearance through Codeware's `DynamicEntitySystem`, no scene. B, only if A faults: move `citizen_breast_physics.archive.xl` out of `archive/pc/mod`, relaunch, repeat A.

### OI-21 update (2026-09-15 22:05) - today's freezes are RedHotTools, not the quest; Test A has not run yet

- **Freezes.** 9 freeze detections today: 18:54, 19:07, 19:48, 19:49, 19:58, 20:11, 20:45, 21:32 and 21:55. Six have a report; the game was killed before sampling finished for 20:11, 20:45 and 21:55. Every sampled main thread shows the same stack: CET Lua → script call → `codeware+0xAEA34` → `redhottools+0x81xxx/0x82xxx` → ntdll lock wait. All of them came after RedHotTools was installed (~18:40); the August and early-September freezes have neither module on the stack.
- **The 21:47 session was not Test A.** It froze at 21:55:18 with no console command typed. CET's Console.cpp logs every command to scripting.log as `] > <cmd>`, and the newest such line is from 09-12. So Mara's spawn was not involved in that freeze.
- **RedHotTools removed.** The user removed RedHotTools.dll at 21:55:21. The 21:57:14 session loads 21 RED4ext plugins without it.
- **21:55:35 session died during startup, unrelated to the quest.** First-chance AV (null read) at `Cyberpunk2077.exe+0x216814` at 21:56:41, while CET was still loading Lua mods. The same address crashed three times on 09-12; frames 4-5 there are `ResourceSerializer_ExecutePostLoad` (1350901460) and `ResourceSerializer_OnDependenciesReady` (1185093671).
- **Naming crash frames.** Crash Logger prints game frames as RED4ext reloc hash IDs, and `cp2077-archive-xl/src/Red/Addresses/Library.hpp` names some of them. In the 21:21 crash, frame 7 is `ResourceSerializer_Deserialize` (2901686778). Frames 10-13 are the same job-worker chain as the `+0x216814` crash. Frame 0 (3858698886) is in no source table.
- **Still open.** Run Test A (spawn `Character.ashcache_mara` away from the scene) in a session without RedHotTools.

### OI-21 update (2026-09-15 22:40) - Test A is clean, so the scene is the trigger; V's voicetag was the one field no shipping scene shares

- **Test A ran and passed.** `scripting.log` 22:06:00 shows the `DynamicEntitySpec` spawn of `Character.ashcache_mara` with `corpo__nusa_wa__q306__fia_undercover_01`, with no fault (player screenshots `sc_mara_are_spawning.png`, `sc_cet_command_userdata.png`). The character, its appearance and the `citizen_breast_physics` patch all load outside the scene, so Test B is dropped.
- **The 22:08:29 crash is not OI-21.** `crash_20260915_220829` is CET (`cyber_engine_tweaks.asi+0xAC37`) on GameThread under `CShutdownState_OnTick` (4069332669, `CyberEngineTweaks/src/reverse/Addresses.h:59`), a teardown crash on quit.
- **Only the `.scene` runs in the crash window.**
  - In the built phase the path is gate -> guard (42) -> scene 43. INT and RET lead to 500 ms pauses, longer than the 277 ms to the 21:21 fault.
  - The panel trail shows the write at f12961, the fact seen at f12962, and normal 48 ms ticks up to the fault.
  - The 17:52 and 19:07 faulting stacks hold the scene path, so memory was already bad while the scene loaded.
- **Ruled out offline:**
  - *Handles:* 96, all inline, no duplicates, no cross-references.
  - *Packing:* the verify JSON equals the build JSON apart from TweakDBID storage.
  - *Audioware:* today's logs register 22 scene ids, all from sonoraapex, and nothing of ours is in `r6/audioware`.
  - *A 09-09 environment change:* the only game files changed 11:00-20:51 are other mods' session saves.
  - *`.wem`:* the files are real Wwise 2023.1.14 output (D89-D91), and the old signature predates them.
  - *`SetMortality`:* not in the 09-10 generator backup.
  - *Choice sockets:* same 7-socket layout as vanilla.
  - *`A7CC66F800000001`:* a stack local on t508, sitting beside a pointer into the exe. It is an engine tag written into freed memory, not our data.
- **The anomaly is `playerActors[0].voicetagId`.**
  - 16 of the 17 census scenes with a player actor use `1103967280742240864`: 12 vanilla, Hot Fuzz, Regina, and both WolvenKit templates.
  - The only other `0` is `q108_00_chicken_test`, an empty test scene with lipsyncAnimSet -1.
  - Ours had `0` with lipsyncAnimSet 1 (`v.anims`), a pair nothing that ships uses. `voiceVagId` is `0` in every scene, so it stays.
  - The `0` came from decisions.md:1357. That reasoning, "no V lipsync ships", is true of the lipmap and says nothing about this field.
- **Change (D96).** `tools/gen_scene.py` now writes `1103967280742240864`, and the `alloc_voicetags.py` docstring is corrected. One variable. **This is not proven to be the cause**: it is the last field unique to our scene. D65 played once with `0`, but heap corruption does not fault on every run.
- **Next suspect if this fails.** Mara's own new voicetag `7731600000000000000`. The mods' actor tags are also absent from the 14-scene vanilla sample, which is too small to call ours unique.
- **Test.** Run `tools/deploy.sh --yes`, load, then CET -> set `ashcache_dbg_scene_go`.
  - If it crashes, keep this change and bisect the scene (dialogue lines, voice-over and lipsync against the actor).
  - If it doesn't, repeat twice more before closing, then remove the debug gate.

### OI-21 update (2026-09-15 23:10) - RESOLVED by D96; the debug gate is removed (D97)

- **Player test after deploying D96.** The player loaded the save, set `ashcache_dbg_scene_go` and got no crash. Mara's dialogue shows with subtitles and the voices play. Before D96, every scene start on this save faulted (17:52, 19:07, 21:21).
- **Root cause.** The player actor's scene `voicetagId` was 0 while it had a lipsync set (D96). No shipping scene has that pair.
- **One clean run so far.** D65 also passed once with the bad value, so a single pass is not proof. The next natural run, with no gate, counts as the second.
- **Gate removed (D97).** The `dbg_scene_gate` node is gone. Its two links are one link again, `desc_talk_mara` -> `guard_meet_mara`. Also removed: the `facts.json` `debug` group, the `glue.json` entry and both `validate.py` lines. The CET menu button disappears with the regenerated `init.lua`.
- **`phase_revision` 3 -> 4.** Node ids are positional (`tools/gen_questphase.py:679`), so removing the gate shifted every later id down by one. A save already inside the phase would have resumed on the wrong nodes. The bump re-enters the phase cleanly, and `replaytest` proves a re-entry repeats no items and replays no scene.
- **Next test: natural flow.** Load a save from before the scene and walk to Mara. The scene should start without any CET input. Without the gate, the pin and the scene start share a tick again. The gate test already cleared the pin: it was live 21:17:59-21:21:11 with no fault.

### OI-13 update (2026-09-15 23:32) - both device props are back in the build (D98)

`ac_splinter_box` and `ac_terminal_pc` had been missing from every archive since D77. D78 cleared them the same day, but their `disabled` flags were never removed. That is why the quest could only pass "Find the black box" through CET. They ship again as of the 23:30:06 archive.

Next test: look at the box and check for an interaction prompt.
- Prompt, and pressing it starts Mara: OI-13's device half closes.
- No prompt: read the CET Devices tab while looking at the box.
  - Nothing returned: the entity never spawned (streaming).
  - Not a Device: the buffer is not being applied.
  - A Device with no actions: controller state.

### OI-13 update (2026-09-16 01:30) - D99: doors forced open, computers still under test

Deploy, load the save at "Find the black box" and walk in from the street. Nothing should be
teleported to.

1. **Both clinic doors should stand open** once "go to the clinic" completes. If one is
   still shut, point at it, press probe and read `door open/locked/sealed`. If it reads
   `true / false / false` while the door looks shut, the PS got the action but the entity
   did not animate.
2. **At the box, probe again** and read `powered`, `cameraZoom`, `examine`, `linkBusy` and
   `animState`:
   - `examine true`, no prompt: the action exists and the interaction layer is not
     showing it.
   - `examine false`: the gate that is false names the fix.

### OI-13 update (2026-09-16) — D100: the props were 1.48 m underground

New candidate root cause for the missing prompt, and it explains the cosmetic half
at the same time. `computer_1.ent` mounts its player workspots at local z −1.40 to
−1.52, and vanilla places the same `.ent` 1.484 m above its nearest floor node. We
placed both clinic props at floor level, so the mesh rendered half-sunk (player
screenshots `sc_problem_look*.png`, 2026-09-16) and the interaction workspot sat
*below the floor* — which is a prompt that cannot be reached by standing anywhere.

That is consistent with everything the CET probe has reported: the device is found
by look-at raycast, is `ComputerControllerPS`, state ON, `isInteractive` true, and
still offers nothing.

Fixed by a prop-only `zOffset` in world.json (1.48), applied when the node is
emitted; `pos` still records the verified floor coordinate. Emitted Z is now
25.540 (`ac_splinter_box`) and 25.560 (`ac_terminal_pc`).

**Not yet confirmed in game.** The test is unchanged from D99: walk in from the
street, look at the box, press probe, and read
`powered / cameraZoom / examine / linkBusy / animState`. If a prompt now appears,
OI-13's interaction half closes and the cause was placement, not the buffer. If
`examine` reads true and there is still no prompt, the height was only the
cosmetic half and the interaction layer is the next thread.

### OI-13 CLOSED (2026-09-16 11:34) — it was placement, 1.48 m

Confirmed in game after the D100 deploy. The clinic terminal's computer UI opens
and is usable (screenshot: FILES tab selected, shard being read), the objective
advanced from "Отримай доступ до термінала клініки" to "Переживи зачистку ФІА",
and the Mara scene now starts automatically without a CET nudge.

Root cause, for the record: the entity origin was placed on the floor point, but
`computer_1.ent` carries its player workspots at local z -1.40 to -1.52. The spot
the player has to stand in to receive a prompt was therefore under the floor. The
device, the instancedata buffer, the appearance and the yaw were all correct the
whole time - every probe reading that said "found, powered, isInteractive true,
no prompt" was consistent with this and with nothing else.

Remaining, tracked separately as a cosmetic item, NOT part of OI-13:
`ac_splinter_box` is still a computer screen standing in for a container, and
both props now hang in open air because this .ent's stand and desk are separate
world geometry in vanilla.

### OI-25 - Mr. Blue Eyes talks with a still mouth (2026-09-22, D130)

`lipsync/en-us/mara.anims` is the only lipsync take this mod ships, and
`tools/gen_lipsync.py` is written around her: a female basis take
(`civ_high_f_24_nat_30`), her rig (`h0_009_wa_c__young_skeleton.rig`), and an
output path with her name in it. D130 casts a second body, and the lipmap ends
up naming three scenes and one actor exactly as before, so the man standing in
front of V in `ash_cache_blueeyes.scene` delivers seventeen lines without moving
his jaw. The emotion idles still play, so it is a still mouth on a moving face
rather than a statue.

**What it would take:** a male basis take extracted the same way D109 extracted
hers, his head rig read off `q203_mr_x.ent`, and `gen_lipsync.py` parameterised
on (character, rig, basis, out) instead of the three constants at the top. The
concatenative method itself does not change - it matches jaw opening to loudness
and does not care whose face it is.

**Until then:** the scene ships and plays. This is a quality gap, not a defect,
and it is visible in exactly one conversation.
