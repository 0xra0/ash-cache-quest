# Ash Cache — the quest as built

**This document describes what the source files actually contain.** It is a map,
not a design authority: every act, objective, ending, character and item below is
read out of `source/`, and if the two ever disagree the source is right and this
file is stale. Design *decisions* and their reasoning live in `docs/decisions.md`;
what is still unproven lives in `docs/open_issues.md`.

## Premise

V is contacted by an unknown number. Cynosure did not only take V's scan during
the Phantom Liberty raid — they kept a piece of the echo grown from it, and the
FIA is about to burn the evidence. The trail runs to a motel in Dogtown, to a
courier who never opened the case he was carrying, and to a ripperdoc clinic off a
Dogtown street where the woman who hid it nine years ago is still waiting to find
out whether she did the right thing.

The object at the centre is **the splinter**: not a weapon, not intelligence, but
a person who has not happened yet.

## Cast

| Who | What they are | Where |
|---|---|---|
| **V** | the player | `scnPlayerActorDef`, acquired `findInContext` |
| **Mara Voss** | FIA, nine years undercover, hid the case herself | `Character.ashcache_mara`, spawned at `#ac_mara` |
| **the courier** | dead before the quest starts; speaks only through his audio log | no body, no record |
| **Mr. Blue Eyes** | three SMS, one ending, and one conversation | `Character.ashcache_blueeyes`, spawned at `#ac_motel_entrance` |
| **the unknown caller** | makes the call that starts the quest; never identified | `Character.ashcache_unknown_caller`, a voice |
| **the echo** | two seconds of V's own voice, played down that line | `Character.ashcache_echo_voice`, a voice |

Mara is the only character with a body. `source/characters.json` carries her
casting and three costed alternatives; see D10.

## Structure

Five journal phases, fifteen objectives, four endings. `ashcache_progress` runs
0→7 alongside as a single linear spine the graph gates on.

### Act 1 — the signal   (`ac_ph1_signal`)

An unknown number calls. It does not say who it is, and V never finds out. Two
seconds of a recording come down the line — V's own voice, saying words V never
said — and then a riddle instead of an address: *find the place where dogs sleep*.

This used to be two SMS, the second of which could only *describe* that recording.
D126 made it a holocall so the recording could actually play.

    ac_obj_goto_dogtown      -> #ac_motel_entrance
    ac_obj_search_room       -> #ac_motel_room7
    ac_obj_search_motel      optional

Room 7 holds the **courier's audio log**, which is where the quest stops being a
delivery job: the courier was not the thief, he was the lock, and somebody picked
him. Blue Eyes says so directly in the SMS that follows.

### Act 2 — the clinic   (`ac_ph2_clinic`)

    ac_obj_goto_clinic       -> #ac_clinic_entrance
    ac_obj_find_box          -> #ac_splinter_case
    ac_obj_read_journal      optional
    ac_obj_open_cabinet      optional

The black box is in a wall in a ripperdoc clinic in Dogtown — vanilla's own
shopfront, four metres below street level, walked into off the street (D19).
The quest borrows both of that shopfront's doors rather than keeping them: shut and
locked when the quest starts, forced open on arrival, left open afterwards (D128).
Opening it grants **the splinter**. The two optional beats — **Mara's journal shard** and the
FIA-locked cabinet — are where her side of it is available *before* she says any
of it out loud, which is what makes the confrontation play differently.

### Act 3 — the truth   (`ac_ph3_truth`)

    ac_obj_talk_mara         -> #ac_mara
    ac_obj_terminal          -> #ac_clinic_terminal

Mara is standing in the clinic when V arrives; she does not walk in. The scene has
**two openings and two hubs**, and which one plays is decided by the graph:

    obj_mara_on → route_mara  (If ashcache_journal_read == 1)
                    True  → meet_mara : mara_meet_in_journal   4 options
                    False → meet_mara : mara_meet_in           3 options

| Option | Line | Section | Sets |
|---|---|---|---|
| `opt_level` | "Then start talking. What's in the box?" | `sec_trust` | `ashcache_mara_trusted` |
| `opt_price` | "What's your cut in this?" | `sec_deal` | `ashcache_mara_trusted` |
| `opt_hostile` | "You're FIA. That's all I need to know." | `sec_hostile` | `ashcache_mara_hostile` |
| `opt_break_j` | "Your journal doesn't say \"it\". It says \"she\"." | `sec_break` | `ashcache_mara_break` **+** `ashcache_mara_trusted` |

The first three appear in both hubs — suffixed `_j` in the journal one, because a
locstring ruid is allocated per option id and two hubs cannot share one — and route
to the same sections. Every route converges on `ashcache_mara_choice_made`.

Three of the four routes to trust is deliberate: levelling with her, pricing her
out and breaking her are different conversations that land in the same place.
`opt_break_j` sets `ashcache_mara_break` *alongside* trust rather than instead of
it — breaking her is a way of earning her, not a fifth disposition — which is what
`facts.json` has always said ("micro-choice A, or C" for trusted, "C only" for
break).

The two openings are not the same lines twice: on the journal path she can see the
shard in V's hands, so she opens defensive and short, and that is what gives the
fourth option ground to stand on. The gate is a graph branch rather than a
greyed-out option for the reason given in D14 and repeated in D17. That reason was
wrong in its premise and right in its conclusion (D26): the condition field is real
and 1,177 vanilla scenes use it, but it removes an option rather than greying it,
so a branch is still the only way to vary the hub. Route evaluation is one-shot:
read the shard after the conversation
starts and you get the three-option hub, exactly as `route_hide` behaves.

The terminal is the required beat. `ashcache_terminal_full_read` is declared for
the completionist read that unlocks a Neural Dampener recipe. That one is **blocked,
not merely unwritten**: the fact is set by reading the same clinic terminal that
`ashcache_terminal_read` waits on, which `glue.json` already lists under `blocked`,
so the completionist read cannot exist before the required read does. The recipe
record's shape has been measured out of the shipped TweakDB anyway — see
`reference/crafting.md`, which also records what is still unmeasured and why the
item behind the recipe does not exist.

### Act 4 — cleanup   (`ac_ph4_cleanup`)

    ac_obj_survive
    ac_obj_decide            -> #ac_splinter_case

Hale's FIA crew arrives. If Mara was trusted she fights alongside V, and OI-1 is
about the fact that she can therefore die and close an ending the player earned.
The graph already tests `ashcache_mara_dead == 0` on both Hide gates as a safety
net; keeping her alive is still the real fix.

### Act 5 — resolution   (`ac_ph5_resolution`)

Four endings, chosen in `source/scene_decision.json` — a second scene, V alone
with the case. Three are always offered; the fourth is gated twice, once as
`gate_hide` (which sets `ashcache_hide_available`) and again as `br_hide` in the
ending switch (D6).

The gate is expressed as **which door of the scene the graph opens**, not as a
greyed-out option:

    obj_decide_on → route_hide  (If ashcache_hide_available == 1)
                      True  → decide_scene : decide_in_hide   4 options
                      False → decide_scene : decide_in        3 options

Each option leads to one closing line and then to a `scnQuestNode` setting its
`ashcache_end_*` fact, and all four converge on one more setting
`ashcache_decision_made`. The ending fact is always set *before* the decision fact,
so a save taken between the two can never read as "decided" with no decision
recorded. D14 has the reasoning; OI-14 and D26 record what was measured since —
the option *can* be gated, it just cannot be shown greyed.

The scene has no cast: V is alone, and a `scnActorDef` spawns rather than
references, so casting Mara would raise her into the finale on the branches where
she is dead or was told to get lost.

| Ending | Fact | Gate | Marker |
|---|---|---|---|
| destroy the splinter | `ashcache_end_destroy` | — | — |
| absorb the echo | `ashcache_end_absorb` | — | — |
| hand it to Blue Eyes | `ashcache_end_blueeyes` | — | — (drop box at the clinic, D120/D130) |
| bury it in the Badlands | `ashcache_end_hide` | Mara trusted **and** alive | `#ac_badlands_cache` |

Hide is the only ending that needs another person: Mara names the Badlands cache,
hands over the **FIA Master Key**, and seals it. That is why it is the gated one.

### Act 6 — the aftermath   (`ac_ph6_aftermath`)

Three optional objectives that open *after* the quest is logged as done. The graph
parks between `quest_done` and `phase_out`, so the journal already reads complete
while the phase waits — and never going is a legitimate way to finish this quest.

| beat | reached on | marker | payload |
|---|---|---|---|
| the landfill | the two endings where Mara dies (D122) | `#ac_landfill_body` | her body, and the coroner's note for the wound V's choices gave her |
| the shaft head | every ending (D129, D131) | `#ac_cynosure_shaft` | the site, worked: the closure order, the survey abstract, and a warm plate |
| the meeting | every ending (D130) | `#ac_motel_entrance` | a conversation, and `ashcache_blueeyes_offer` |

They run in that order, in one corridor, and the order is the fiction: the man
who asks for the meeting is watching the shaft, not V. The message arrives the
moment the closure order is in V's hands, which is also why the meeting is the
one beat that cannot be reached without the one before it.

The second one is the only place in this quest where the location the plot is
named after is a place rather than a word, and it closes the address Mara gives
on the phone. Cynosure is not under
the Badlands: the outer bunker's node transforms run X -2411..-2074, Y -2598..-2166,
Z -208..-57, which is under **Dogtown**, with the motel inside that footprint and
the clinic just outside it. The box spent nine years in a wall 250 m above the hole
it came out of. The shard V finds reconciles the two addresses — the Badlands portal
is the one on the form and has been nine kilometres of collapsed tunnel since '69 —
and confirms that the scan the splinter was cut from is still filed below.

D131 turned that pin into a site. Arriving opens a prompt on the pad, and the
scene behind it is `scene_terminal.json`'s shape — V alone, three things to do,
each gone once done, each looping back to the hub, plus one unconditional way
out. Pull the **closure plate** and the Agency stencil turns out to be painted
over a Militech weld years older than it: the feds did not seal this, they found
it sealed and did the paperwork. Jack the **maintenance port** and the facility
describes itself, floor by floor — nine levels, minus three the cold store,
minus seven the archive where V's own scan is filed with the originals, four
through six under water since '71 — and the cold store is short exactly one
item, 0-1140, signed out nine years ago on a badge that resolves to nobody by a
carrier who never signed out at grade. That is the box V pulled out of a motel
wall 250 m straight up. Put a hand on the **weld** and there is no item at all,
which makes it the best thing on the site: the plate is warm, the air moves
outward, and the pumps on the landing log a maintenance cycle every eleven days
on a facility that shut four years ago.

Each of the two documents is granted by the graph after the scene exits, on the
fact the scene set, so a player who only pries the plate leaves without the
survey. Everything is visible in the hub from the first frame — nothing here is
hidden behind a guess.

The third is the only conversation in the phase, and the only time in the quest
that Mr. Blue Eyes is a man rather than a number. The scene has **four entry
points** — one per ending — chosen by four positive conditions on the same
`ashcache_end_*` facts the ending switch reads; they converge after two lines,
because what he came to say does not depend on what V did, only his opinion of
the person he says it to. He is `Character.q203_mr_x`, vanilla's own record for
him, his nameplate reads NO CALLER ID, he is not kept alive past the scene, and
he has no voice model because the shipped game gives him no voiced line to clone
(D130). He also has no lipsync take — OI-25.

The way *in* to Cynosure is not part of any of this. It is built, it is not
shipped, and it is waiting on one save load: see `mod/bisect/`, D116 and D129.

## Items

| Item | Kind | Granted |
|---|---|---|
| The Splinter | quest object, undroppable | opening the black box |
| Mara's Journal | readable shard | with the journal objective |
| Courier's Audio Log | readable shard | with the room objective |
| FIA Master Key | quest object, undroppable | Hide ending only |

All four are TweakXL records inheriting vanilla ones, granted by the graph rather
than by redscript. See D12.

## World

Two streaming sectors, six markers, two deferred.

    ash_cache_motel     #ac_motel_entrance   #ac_motel_room7
    ash_cache_clinic    #ac_clinic_entrance  #ac_clinic_terminal
                        #ac_splinter_case    #ac_mara
    deferred            #ac_badlands_cache

The clinic sector carries the scene origin, so the `yaw` on `#ac_mara` decides
which way the confrontation faces. Four of the six coordinates have never been
stood on — that is OI-9, and it is the one thing here that cannot be done without
the game running.

Both anchors are positions vanilla vouches for: the motel is AMM's "Dogtown
Apartment", the clinic is vanilla's own GPS entrance marker
`{loc_q303_macs_clinic_gps}`, one of only four registered pedestrian entrances in
Dogtown. Neither needs a teleport, and neither needs Phantom Liberty progress
(D19).

## What is not built yet

The resources exist and cross-reference correctly. Ten facts used to gate the
graph with nothing setting them (**OI-12**); six of those now have something behind
them — the arrival triggers, the start gate and the shard-read hooks are the glue
layer (D13), and the ending choice is a scene (D14).

**Four remain, and they are what stops the quest being playable** (**OI-13**):

    box_opened       an interactable prop at #ac_splinter_case
    terminal_read    an interactable computer at #ac_clinic_terminal, and its log
    cabinet_opened   the optional FIA-locked cabinet
    cleanup_done     the FIA cleanup encounter

Three of the four are on the main spine, so each is a hard stop rather than a
missed optional beat. None is faked: `validate.py` prints them on every build and
fails if `glue.json`'s `blocked` list and the real leftovers ever disagree.

All four used to share one blocker — the sector generator wrote named points and
nothing else, so there was no way to put an *object* anywhere. It now writes four
node types (D15), and the graph nodes and conditions that drive them are measured,
emitted and round-tripped through the engine format (D16). What is left is two
questions that need the game, and three probe sectors ask them at a verified
coordinate reachable from the CET Surveyor tab: does a vanilla device `.ent` placed
with a null `instanceData` appear and work, and does a spawner accept a `Character`
record. The first decides whether three of these four cost a line of JSON each or an
entity apiece; the second is the last thing standing between `cleanup_done` and
being authorable.

Subtitles carry every line in both `en-us` and `ua-ua`. The audio under them is
`en-us` only: D2's "no voice acting" was overtaken by the local TTS -> RVC
pipeline (OI-16), and D42 settled that Ukrainian ships as text over the English
recording, as vanilla does.
