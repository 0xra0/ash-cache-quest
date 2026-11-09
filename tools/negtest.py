#!/usr/bin/env python3
"""Break one thing at a time in a COPY of source/, and assert validate.py notices.

A validator is only worth what its failures are worth, and a check that silently
stops firing is worse than no check - it converts "nobody looked" into "something
looked and was happy". So every check in tools/validate.py that guards a SILENT
in-game failure gets a case here: a minimal mutation, and the fragment of the
error text it must produce.

Nothing is mutated in place. The whole tree is copied to build/negtest/ first
(build/ is generated - rule 4; /tmp is off limits - rule 3), so an interrupted run
cannot leave source/ in a broken state.

    python3 tools/negtest.py

Adding a check to validate.py? Add its case here in the same commit. If you cannot
state the mutation that trips it, the check does not know what it is looking for.
"""
import copy
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "negtest"


def mutate(name, fn):
    """Return a breakage that loads source/<name>, applies fn, and writes it back."""
    def apply():
        p = WORK / "source" / name
        d = json.loads(p.read_text(encoding="utf-8"))
        fn(d)
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return apply


def chain(*breakages):
    """Apply several breakages as one case. Needed where the mutation that
    exercises a check spans two files - making a marker unverified in
    world.json, then aiming characters.json at it."""
    def apply():
        for b in breakages:
            b()
    return apply


def set_char(key, value):
    return mutate("characters.json", lambda d: d["characters"][0].__setitem__(key, value))


def set_scene(key, value):
    return mutate("scene_mara.json", lambda d: d.__setitem__(key, value))


def set_item(idx, key, value):
    return mutate("items.json", lambda d: d["items"][idx].__setitem__(key, value))


def set_area(idx, key, value):
    return mutate("glue.json", lambda d: d["areas"][idx].__setitem__(key, value))


def scene_node(d, nid):
    """One node of a scene, BY ID.

    Not by position: scene_mara.json grew a second 'start' when the journal route
    was added, which shifted every index by one and would have quietly re-pointed
    these cases at a different node - a case that still passes while testing
    something else is the exact failure this file exists to prevent.
    """
    return next(n for n in d["nodes"] if n.get("id") == nid)


def set_line(key, value, nid="sec_open", idx=0):
    return mutate("scene_mara.json",
                  lambda d: scene_node(d, nid)["lines"][idx].__setitem__(key, value))


def opt_condition(nid, opt_id, cond):
    """Put a questCondition on one choice option of scene_mara.json, by id."""
    def setit(d):
        opt = next(o for o in scene_node(d, nid)["options"] if o["id"] == opt_id)
        opt["condition"] = cond
    return mutate("scene_mara.json", setit)


def condition_every_option(nid):
    """Gate every option of a hub, which is how a hub ends up empty in game."""
    def setit(d):
        for o in scene_node(d, nid)["options"]:
            o["condition"] = {"fact": "ashcache_journal_read", "value": 1}
    return mutate("scene_mara.json", setit)


def set_line_ms(line_id, ms):
    """Put an explicit duration on one spoken line of scene_mara.json."""
    def setit(d):
        for n in d["nodes"]:
            for l in n.get("lines", []):
                if l["id"] == line_id:
                    l["ms"] = ms
                    return
        raise KeyError(line_id)
    return mutate("scene_mara.json", setit)


def drop_vo(name, data=b"", locale="en-us"):
    """Put a file in the voiceover drop folder. Like lipsync/, vo/ is not source/
    and reset() never copies it in, so every case here starts from an empty
    folder and creates exactly what it means to test."""
    def apply():
        d = WORK / "vo" / locale
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(data)
    return apply


def drop_narration(name, data=b"RIFF", locale="en-us"):
    """Put a file in the notes-read-aloud drop folder (D125). Same contract as
    drop_vo: narration/ is not source/, reset() never copies it in, so each case
    creates exactly the file it means to test."""
    def apply():
        d = WORK / "narration" / locale
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(data)
    return apply


def real_wem(seconds=0.05):
    """A .wem the encoder itself would have written, so the positive cases below
    are asserting against the real output rather than a hand-typed header that
    could drift away from it."""
    sys.path.insert(0, str(ROOT / "tools"))
    import wav_to_wem
    return wav_to_wem.wem_bytes(bytes(int(48000 * seconds) * 2), 1, 48000)


def renamed_wav():
    """A plain Microsoft WAV with a .wem name: RIFF/WAVE, fmt chunk, format
    0x0001. Packs fine, plays nothing."""
    import struct
    pcm = bytes(4800)
    fmt = struct.pack("<HHIIHH", 1, 1, 48000, 96000, 2, 16)
    body = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(pcm)) + pcm
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body


def wrong_codec():
    """Well-formed, but a codec no shipped file uses."""
    import struct
    fmt = struct.pack("<HHIIHH", 0x1234, 1, 48000, 96000, 2, 16)
    body = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", 0)
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body


def drop_anims(name, locale="en-us"):
    """Put a lipsync animset on disk. lipsync/ is a DROP FOLDER, not source/ - the
    files in it are the manifest gen_lipmap.py reads, so breaking it means creating
    a file rather than editing one, and reset() never copies it in."""
    def apply():
        d = WORK / "lipsync" / locale
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(b"")
    return apply


def both(*breakages):
    """Two breakages at once, for a check whose branch needs more than one thing
    wrong before it can be reached at all."""
    def apply():
        for b in breakages:
            b()
    return apply


# (label, breakage, fragment the resulting error must contain)
def sector(d, sid):
    return next(s for s in d["sectors"] if s["id"] == sid)


def set_probe(kind, key, value, sid="ash_cache_probe"):
    """Mutate the single node of one kind in a probe sector.

    By id, not by position: there are three probe sectors now and which one is
    last is an implementation detail of world.json, not something these cases
    should depend on.
    """
    return mutate("world.json",
                  lambda d: sector(d, sid)[kind][0].__setitem__(key, value))


def set_geom(kind, key, value):
    """Mutate the one geometry node of its kind at the landfill (D132).

    Geometry does not live in a probe sector: a probe sector is disabled, and a
    disabled sector is never built, so a case aimed at one would prove that
    validate.py reads world.json and nothing about what ships. The landfill
    carries the only mesh and the only collision box in the project, and both
    of them are live.
    """
    return mutate("world.json",
                  lambda d: sector(d, "ash_cache_landfill")[kind][0].__setitem__(key, value))


CASES = [
    ("cast: marker points at nothing",
     set_char("marker", "#ac_nowhere"), "no world node defines"),
    ("cast: marker is only deferred",
     set_char("marker", "#ac_badlands_cache"), "only defers"),
    ("cast: marker written without '#'",
     set_char("marker", "ac_mara"), "must be a NodeRef starting"),
    ("cast: record breaks the rule 5 prefix",
     set_char("record", "mara_voss"), "rule 5"),
    ("cast: displayName has no string behind it",
     set_char("displayName", "char_nobody"), "strings.json does not define"),
    ("cast: two characters share one record",
     mutate("characters.json", lambda d: d["characters"].append(
         dict(copy.deepcopy(d["characters"][0]), id="mara2", actorName="Mara2"))),
     "share the TweakDB record"),
    ("cast: scene casts an unknown character",
     set_scene("actors", ["marra"]), "characters.json does not define"),
    # Used to empty scene_mara.json's cast. That stopped firing the moment a SECOND
    # scene cast Mara (D123, scene_aftertalk.json): emptying one cast list no longer
    # leaves her uncast, so the case silently tested nothing. Adding a character
    # nobody casts tests the invariant head-on and cannot rot again as scenes are
    # added. negtest reports 'checks that did not fire' precisely so this is loud.
    ("cast: character nobody casts",
     mutate("characters.json", lambda d: d["characters"].append(
         dict(copy.deepcopy(d["characters"][0]), id="mara_uncast",
              actorName="MaraUncast", record="ashcache_mara_uncast"))),
     "no scene casts them"),
    # D126. A voice is allowed to have no marker ONLY because every scene that
    # casts it is a holocall, where gen_scene builds it with voice_actor_def() and
    # never asks where it stands. Both halves of that bargain get a case, because
    # breaking either one is silent: a voice with a marker is a claim about a body
    # that will never exist, and a voice cast in an ordinary scene goes back
    # through actor_def() and spawns at the world origin.
    ("cast: a voice also carries a spawn marker",
     mutate("characters.json", lambda d: next(
         c for c in d["characters"] if c["id"] == "unknown").__setitem__("marker", "#ac_mara")),
     "is a voice and also carries a marker"),
    ("cast: a voice is cast in a scene that is not a holocall",
     set_scene("actors", ["mara", "unknown"]), "the scene is not a holocall"),
    ("cast: line speaker is not in the cast",
     set_line("actor", "Mira"), "no speaker and no nameplate"),
    ("cast: 'to' names someone not cast",
     set_line("to", "Nobody"), "no speaker and no nameplate"),
    # A thread filed under a folder that is not a contact folder has nowhere in the
    # phone UI to appear, and nothing says so at build time (OI-2).
    # Rule 8, mechanised: a TweakDB id is unguessable and a wrong one is silent.
    ("tweakdb: inherits a record the game does not have",
     set_char("base", "Character.q306_fia_agent_corpo_scene_xx"),
     "which the game does not have"),
    # Only fireable together with the rule-5 error, because no vanilla record is
    # prefixed ashcache_ - which is the point of rule 5.
    ("tweakdb: defines a record vanilla already has",
     set_char("record", "Judy"), "would overwrite it"),
    # The phase entry socket. This one cost a whole evening of in-game testing:
    # the mod merged, every layer reported green, and not one node ever ran.
    ("graph: phase entry socket is not the name ArchiveXL wires",
     mutate("quest_graph.json",
            lambda d: next(n for n in d["nodes"] if n.get("type") == "input")
            .__setitem__("socket", "In")),
     "the phase would merge and never execute"),
    ("graph: no input node at all",
     mutate("quest_graph.json",
            lambda d: d["nodes"].remove(
                next(n for n in d["nodes"] if n.get("type") == "input"))),
     "ArchiveXL cannot wire the phase into its parent"),
    # Links that name a socket their endpoint does not have. Each of these three
    # shapes was live in source/quest_graph.json for a day (D127): gen_questphase
    # sys.exits on all of them, so the questphase never rebuilt and the archive
    # kept shipping the previous one, while validate.py printed OK. The build
    # failed honestly; the failure was believed to be somewhere else. These are
    # here so the cheap tool catches it first.
    ("graph: link enters a condition on a journal socket",
     mutate("quest_graph.json",
            lambda d: d["links"].__setitem__(
                next(i for i, l in enumerate(d["links"])
                     if l[1] == "guard_hook"), ["await_start", "guard_hook", "Active"])),
     "has no input socket 'Active'"),
    ("graph: link into a four-socket journal node names none of them",
     mutate("quest_graph.json",
            lambda d: d["links"].__setitem__(
                next(i for i, l in enumerate(d["links"])
                     if l[0] == "mark_hook"), ["mark_hook", "quest_active"])),
     "name one explicitly"),
    ("graph: link leaves a condition by a socket it does not have",
     mutate("quest_graph.json",
            lambda d: d["links"].__setitem__(
                next(i for i, l in enumerate(d["links"])
                     if l[0] == "guard_hook:True"), ["guard_hook:Out", "hook_start"])),
     "has no output socket 'Out'"),
    # The phase revision. Not a style field: it is the identity a save remembers
    # this phase by, and the only lever that re-enters a phase on a save which has
    # already been told the phase started.
    ("graph: phase revision is missing",
     mutate("quest_graph.json", lambda d: d.pop("phase_revision")),
     "must be an integer >= 1"),
    ("graph: phase revision is not a number",
     mutate("quest_graph.json", lambda d: d.__setitem__("phase_revision", "r2")),
     "must be an integer >= 1"),
    # Items. Every one of these is silent: the item simply never appears, or
    # appears with no name, or opens an empty reader.
    ("items: graph grants an item nobody defines",
     mutate("quest_graph.json",
            lambda d: next(n for n in d["nodes"] if n.get("type") == "add_item")
            .__setitem__("item", "ashcache_ghost")),
     "which items.json does not define"),
    ("items: defined but never granted",
     mutate("quest_graph.json",
            lambda d: d["nodes"].remove(
                next(n for n in d["nodes"] if n.get("id") == "give_splinter"))),
     "but no graph node grants it"),
    # inject_loot puts an item inside a container instead of into the player's
    # hands. It reaches the same items.json cross-check by a second path, so it
    # gets both halves of the claim: a typo inside one is still caught, and a
    # correct one still counts as the grant that keeps the item alive.
    ("items: loot node injects an item nobody defines",
     mutate("quest_graph.json",
            lambda d: next(n for n in d["nodes"] if n.get("id") == "give_splinter")
            .update({"type": "inject_loot", "target": "#ac_splinter_case",
                     "item": None, "items": [{"item": "ashcache_ghost"}]})),
     "which items.json does not define"),
    ("items: loot node is a legal way to grant an item",
     mutate("quest_graph.json",
            lambda d: next(n for n in d["nodes"] if n.get("id") == "give_splinter")
            .update({"type": "inject_loot", "target": "#ac_splinter_case",
                     "item": None, "items": [{"item": "ashcache_splinter"}]})),
     None),
    ("items: record breaks the rule 5 prefix",
     set_item(0, "record", "splinter"), "rule 5"),
    ("items: displayName has no string behind it",
     set_item(0, "displayName", "item_nope"), "strings.json does not define"),
    ("items: shard's onscreen body has no string behind it",
     set_item(1, "onscreen", {"group": "ash_cache", "entry": "mara_journal",
                              "title": "shard_mara_journal_title", "body": "nope"}),
     "would open an empty reader"),
    ("items: quest item inherits a record the game does not have",
     set_item(0, "base", "Items.q003_chip_that_isnt"), "which the game does not have"),
    # Glue. This layer is invisible in every artifact the build produces - the
    # archive, the YAML and the .reds all look identical whether the trigger is
    # armed in the right act or the wrong one. The only symptom of any of these
    # is a quest that stops advancing, hours in.
    ("glue: arrival trigger aimed at a marker that does not exist",
     set_area(0, "marker", "ac_nowhere"), "which world.json does not define"),
    ("glue: arrival armed during the wrong act",
     set_area(0, "stage", 3), "outside that act"),
    ("glue: arrival sets a fact facts.json never declared",
     set_area(0, "fact", "ashcache_at_nowhere"), "facts.json does not declare"),
    ("glue: arrival sets a fact no graph node waits on",
     set_area(0, "fact", "ashcache_terminal_full_read"), "no graph node waits on it"),
    ("glue: shard hook reads an item that is not a shard",
     mutate("glue.json", lambda d: d["shards"][0].__setitem__("item", "splinter")),
     "does not define as a shard"),
    ("glue: shard hook sets a fact the graph owns",
     mutate("glue.json", lambda d: d["shards"][0].__setitem__("fact", "ashcache_mara_trusted")),
     "the graph should own it"),
    ("glue: quest gates itself on one of its own facts",
     mutate("glue.json", lambda d: d["start"].__setitem__("prerequisite", "ashcache_start")),
     "gates itself on itself"),
    # The two halves of the OI-13 bookkeeping. Neither is a runtime failure; both
    # are the file quietly stopping to describe reality.
    ("glue: a blocked fact dropped from the list without being implemented",
     # Was ashcache_box_opened until D65 placed the prop and took it off the
     # list. Any fact still on it works; cabinet_opened is the one the graph
     # waits on and nothing sets, which is exactly what this case is about.
     mutate("glue.json", lambda d: d["blocked"].pop("ashcache_cabinet_opened")),
     "does not list it under 'blocked'"),
    ("glue: blocked list still names a fact the graph stopped waiting on",
     mutate("glue.json",
            lambda d: d["blocked"].__setitem__("ashcache_terminal_full_read", "nothing")),
     "remove it from 'blocked'"),
    # The choice hub. 'goto' is an annotation gen_scene.py never reads - 'links'
    # does the routing - so these two are the file describing a route it does not
    # take. With two hubs sharing four destinations that is easy to do by hand.
    ("scene: option's goto disagrees with the link that routes it",
     mutate("scene_decision.json",
            lambda d: next(o for n in d["nodes"] for o in n.get("options", [])
                           if o["id"] == "opt_absorb").__setitem__("goto", "sec_destroy")),
     "lies about where the choice leads"),
    ("scene: option annotated with a goto that nothing links",
     mutate("scene_decision.json",
            lambda d: d["links"].remove(["hub_hide:opt_hide_h", "sec_hide"])),
     "lead nowhere"),
    # A graph scene node's sockets are generated from ITS OWN entries list, not
    # read from the .scene - so a name that does not exist over there is a socket
    # wired to nothing, and the quest stops at the ending with no error anywhere.
    ("scene: graph enters the scene by a name the scene does not declare",
     mutate("quest_graph.json",
            lambda d: next(n for n in d["nodes"] if n.get("id") == "decide_scene")
            .__setitem__("entries", ["decide_in", "decide_in_hyde"])),
     "does not declare"),
    # The contact is not decoration: it owns the avatar and the sender name, and it
    # is a real level of the journal tree, so losing it silently shortens the path
    # of every message under it and the SMS never arrives (D22).
    ("journal: sms thread has no contact",
     mutate("journal.json",
            lambda d: d["phoneConversations"][0].pop("contact")),
     "has no contact block"),
    ("journal: contact is a bare folder string again",
     mutate("journal.json",
            lambda d: d["phoneConversations"][0].__setitem__("contact", "contacts")),
     "has no contact block"),
    # Was aimed at sms_hook_01, the first of the two messages the quest used to open
    # with. D126 replaced both with a holocall, so there is no such node any more and
    # this case died with a StopIteration rather than a verdict. Re-aimed at
    # sms_blueeyes, which is now the quest's FIRST phone message and tests the same
    # invariant: a message path that omits the contact segment addresses nothing.
    ("journal: sms graph node keeps the old three-segment path",
     mutate("quest_graph.json",
            lambda d: next(n for n in d["nodes"] if n.get("id") == "sms_blueeyes")
            .__setitem__("path", "contacts/ac_msg_blueeyes/ac_msg_blueeyes_01")),
     "which journal.json does not define"),
    # The journal description and the codex links are the two things that make the
    # quest read like a vanilla one, and both fail by simply not rendering.
    ("journal: objective summary names a string that does not exist",
     mutate("journal.json",
            lambda d: d["phases"][0]["objectives"][0].__setitem__("summary", "str.desc_nope")),
     "which strings.json does not define"),
    # The one that actually shipped: the leaf 'cyanosure' is misspelt in vanilla,
    # and checking that famous typo made the two segments in front of it look
    # already-verified. They were the wrong way round, and a codex link that
    # resolves to nothing renders as nothing, silently.
    ("journal: codex path has its segments the wrong way round",
     mutate("journal.json",
            lambda d: d["codexLinks"][1].__setitem__(
                "path", "ep1/codex/quest/locations/cyanosure")),
     "which is not a codex entry in the game's journal"),
    ("journal: codex link points at a description instead of an entry",
     mutate("journal.json",
            lambda d: d["codexLinks"][1].__setitem__(
                "path", "ep1/codex/locations/quest/cyanosure/cyanosure_desc")),
     "has to point at a gameJournalCodexEntry"),
    ("journal: phone avatar is not a real TweakDB record",
     mutate("journal.json",
            lambda d: d["phoneConversations"][0]["contact"].__setitem__(
                "avatar", "PhoneAvatars.Avatar_Nobody")),
     "which the game does not have"),
    # --- world nodes beyond markers (D15). Every one of these fails in game by
    # --- the object simply not being there, which looks exactly like bad
    # --- coordinates (OI-9) and exactly like the instanceData question being
    # --- answered "no". Three conclusions, one symptom - so they get caught here.
    ("world: prop points at an .ent the game does not have",
     set_probe("props", "template", "base\\gameplay\\devices\\masters\\computers\\computer_9.ent"),
     "not in the game's archives"),
    ("world: prop template written with forward slashes",
     set_probe("props", "template", "base/gameplay/devices/masters/computers/computer_1.ent"),
     "forward slashes"),
    ("world: mesh path written with forward slashes",
     set_geom("meshes", "mesh",
              "base/environment/architecture/common/int/int_ent_industrial_a/"
              "int_ent_industrial_a_wall_gf_h400_l300_a.mesh"),
     "backslash-separated"),
    ("world: mesh path points at a .ent instead of a .mesh",
     set_geom("meshes", "mesh", "base\\quest\\main_quests\\prologue\\q004\\"
              "entities\\q004_data_shard.ent"),
     "needs a 'mesh' depot path"),
    ("world: mesh path is not in the game's archives",
     set_geom("meshes", "mesh", "base\\environment\\architecture\\common\\int\\"
              "int_ent_industrial_a\\int_ent_industrial_a_wall_gf_h999_l300_a.mesh"),
     "not in the game's archives"),
    ("world: mesh given a zero scale, which draws nothing at all",
     set_geom("meshes", "scale", [1.0, 0.0, 1.0]), "three positive numbers"),
    ("world: collision node with an empty box list",
     set_geom("collisions", "boxes", []), "at least one entry in 'boxes'"),
    ("world: collision box with a zero half-extent - a wall with no thickness",
     set_geom("collisions", "boxes", [{"offset": [0.0, 0.0, 2.0], "half": [1.5, 0.0, 2.0]}]),
     "HALF extents"),
    ("world: prop has no template at all",
     mutate("world.json", lambda d: sector(d, "ash_cache_probe")["props"][0].pop("template")),
     "needs a 'template' depot path"),
    ("world: trigger has no size, so it collapses to a unit box",
     mutate("world.json", lambda d: sector(d, "ash_cache_probe")["triggers"][0].pop("size")),
     "three positive numbers"),
    ("world: trigger given a negative extent",
     set_probe("triggers", "size", [4.0, -4.0, 2.0]), "three positive numbers"),
    ("world: spawner asks for a TweakDB record that does not exist",
     set_probe("spawners", "record", "Vehicle.hackable_thorton_galactica",
               "ash_cache_probe_car"),
     "which the game does not have"),
    ("world: spawner has no record",
     mutate("world.json",
            lambda d: sector(d, "ash_cache_probe_car")["spawners"][0].pop("record")),
     "needs a 'record' TweakDB id"),
    ("world: a prop steals the NodeRef of a marker",
     set_probe("props", "id", "ac_mara"), "same NodeRef"),
    ("world: a placed node breaks the rule 5 prefix",
     set_probe("props", "id", "probe_computer"), "must be prefixed 'ac_'"),
    # Raising the gameplay tier is the one edit in this project that can leave the
    # player permanently unable to move with nothing logged anywhere. Both halves
    # of the guard get a case, because each strands a different player: the one
    # who finishes the scene, and the one who is interrupted out of it.
    ("tier: a scene raises the tier and never lowers it",
     mutate("scene_mara.json", lambda d: (
         d["nodes"].remove(next(n for n in d["nodes"] if n["id"] == "tier_off")),
         d["links"].remove(["fact_made", "tier_off"]),
         d["links"].remove(["tier_off", "end"]),
         d["links"].append(["fact_made", "end"]))),
     "never sets it back to Tier1_FullGameplay"),
    ("tier: a tier-raising scene leaves Default INT unwired",
     mutate("quest_graph.json",
            lambda d: d["links"].remove(["meet_mara:Default INT", "mara_int_wait"])),
     "'Default INT' output is not wired"),
    ("tier: a tier-raising scene leaves Default RET unwired",
     mutate("quest_graph.json",
            lambda d: d["links"].remove(["meet_mara:Default RET", "mara_ret_wait"])),
     "'Default RET' output is not wired"),
    # Three of ten positions in this project were derived by offsetting a known
    # one, and in game all three were wrong - inside rock, inside a parking
    # garage, unreachable. Every position that was stood on was right. These four
    # cases keep that record from being forgotten by the next person to add a
    # marker in a hurry.
    ("world: a node does not say whether it was stood on",
     mutate("world.json", lambda d: sector(d, "ash_cache_clinic")["markers"][0].pop("verified")),
     "has no 'verified' flag"),
    ("world: a scene is anchored to a position nobody has stood on",
     mutate("world.json", lambda d: next(
         m for m in sector(d, "ash_cache_clinic")["markers"] if m["id"] == "ac_mara"
     ).__setitem__("verified", False)),
     "it plays, wrong, wherever it lands"),
    # This one used to lean on #ac_splinter_case being unverified. It was stood
    # on and captured on 2026-09-06, so pointing at it stopped proving anything
    # and the case silently passed nothing. The mutation now MAKES a marker
    # unverified rather than assuming one is, which is what the check is about
    # and cannot rot the same way.
    ("world: an actor spawns at a position nobody has stood on",
     chain(mutate("world.json", lambda d: next(
         m for m in sector(d, "ash_cache_clinic")["markers"]
         if m["id"] == "ac_splinter_case").__setitem__("verified", False)),
           set_char("marker", "#ac_splinter_case")),
     "she would arrive inside whatever is there"),
    # Same rot, other direction: ac_motel_room7 was collapsed onto the entrance
    # until it got its own captured position, so a lone collapsedOnto no longer
    # had a collision to be wrong about. The mutation now recreates the
    # collision it is supposed to explain, then mis-declares it.
    ("world: a collapse is declared onto the wrong node",
     mutate("world.json", lambda d: (lambda ms: next(
         m for m in ms if m["id"] == "ac_motel_room7").update({
             "pos": next(m for m in ms if m["id"] == "ac_motel_entrance")["pos"],
             "collapsedOnto": "ac_clinic_entrance"}))(
         sector(d, "ash_cache_motel")["markers"])),
     "declares collapsedOnto"),
    ("world: two triggers copy-pasted onto the same point",
     mutate("world.json", lambda d: sector(d, "ash_cache_probe")["triggers"].append(
         dict(sector(d, "ash_cache_probe")["triggers"][0], id="ac_probe_trigger_2"))),
     "sit at the same point"),
    # spawnOnStart is the difference between quest content and set dressing. A
    # quest spawner that ships with it set has its ambush already standing there
    # when the player first walks past, hours early, and nothing logs it.
    ("world: quest content spawns before the quest starts",
     mutate("world.json", lambda d: sector(d, "ash_cache_clinic").__setitem__(
         "spawners", [{"id": "ac_clinic_guard", "pos": [-2081.0, -2207.0, -194.78],
                       "yaw": 0.0, "record": "Character.q305_fia_agent",
                       "spawnOnStart": True}])),
     "outside a probe sector"),
    # The graph reaches into the world by name. A condition aimed at a node that
    # was never placed never becomes true - the quest stops dead, in silence.
    ("graph: a condition waits on a world node nobody placed",
     mutate("quest_graph.json", lambda d: d["nodes"].append(
         {"id": "wait_ghost", "type": "pause",
          "condition": {"interaction": "#ac_ghost_box"}})),
     "no world node defines"),
    ("graph: a device condition names a node nobody placed",
     mutate("quest_graph.json", lambda d: d["nodes"].append(
         {"id": "wait_ghost_door", "type": "pause",
          "condition": {"device": "#ac_ghost_door", "controller": "DoorControllerPS"}})),
     "no world node defines"),
    ("graph: a spawn node activates a spawner nobody placed",
     mutate("quest_graph.json", lambda d: d["nodes"].append(
         {"id": "spawn_ghost", "type": "spawn",
          "actions": [{"community": "#ac_ghost_crew"}]})),
     "no world node defines"),
    # A NodeRef quoted inside a _comment is prose, not a use. If the walker
    # counted it, a world node nothing actually points at would look referenced.
    ("graph: a NodeRef mentioned only in a comment does not count as a use",
     mutate("quest_graph.json", lambda d: d["nodes"].append(
         {"id": "note", "type": "set_fact", "fact": "ashcache_start",
          "_comment": "one day this will wait on #ac_ghost_box"})),
     None),

    # The antagonist really did ship as Hale in seven spoken lines and Gale in the
    # journal shard - in BOTH locales, independently. Nothing else can catch it:
    # two spellings of one name are two valid strings that localise and build.
    ("text: one character's name spelled two ways",
     set_line("en-us", "Don't turn around. That case has Gale's name on it too.",
              nid="sec_open"),
     "differ by one letter"),
    # ...and the check must survive contact with ordinary prose. 'Hate' opening a
    # sentence is one substitution away from 'Hale', and a version of this check
    # that compared every capitalised word would report it. Sentence-initial
    # capitals are grammar; only mid-sentence ones are names.
    ("text: a sentence-opening capital is not a proper noun",
     set_line("en-us", "Hate it or not, Hale is already moving.", nid="sec_open"),
     None),

    # Lipsync binds through numbers and every way it can be wrong is silent: the
    # map merges, ArchiveXL logs success, and the face just never moves. See
    # tools/gen_lipmap.py for the chain these five guard.
    ("lipsync: a speaking actor has no voicetag",
     mutate("voicetags.json", lambda d: d.pop("mara")),
     "speaks in a scene but has no voicetag"),
    # Johnny's real tag. Reusing a vanilla number is not a hypothetical mistake -
    # the Kidnap mod reuses this exact one ON PURPOSE to borrow Johnny's lipsync,
    # which is precisely why an accidental reuse would look like it worked.
    ("lipsync: a voicetag that belongs to a vanilla character",
     mutate("voicetags.json", lambda d: d.__setitem__("mara", "1103967280742240508")),
     "outside the reserved block"),
    ("lipsync: an actor left on the player's voicetag 0",
     mutate("voicetags.json", lambda d: d.__setitem__("mara", "0")),
     "PLAYER's tag"),
    ("lipsync: two characters share one voicetag",
     mutate("voicetags.json", lambda d: d.__setitem__("ghost", d["mara"])),
     "share voicetag"),
    # The map keys on FNV1a64 of the scene's depot path. Move the scene and the
    # hash still computes, still merges, and matches nothing in the game.
    ("lipsync: a scene moved to a depot path the map does not hash",
     mutate("quest_graph.json", lambda d: next(
         n for n in d["nodes"] if n.get("type") == "scene").__setitem__(
         "file", "mod\\ash_cache\\scenes\\ash_cache_mara.scene")),
     "key on a path no scene has"),
    ("lipsync: an animset naming nobody in any scene's cast",
     drop_anims("johnny.anims"),
     "is in no scene's cast"),
    ("lipsync: an animset for a character with no voicetag",
     both(drop_anims("mara.anims"), mutate("voicetags.json", lambda d: d.pop("mara"))),
     "who has no voicetag"),
    # ...and the check must not fire on the thing it exists to permit.
    ("lipsync: an animset for a cast character with a voicetag is legal",
     drop_anims("mara.anims"),
     None),

    # Voiceover. Every one of these packs without complaint and makes no sound;
    # the renamed-.wav case is the one that will actually happen, because the
    # audio arrives from an RVC pipeline as .wav and the extensions differ by
    # one keystroke.
    ("vo: a .wem named after no line",
     drop_vo("mara.not_a_line.wem", real_wem()),
     "names no line in"),
    ("vo: a source file named after no line",
     drop_vo("mara.not_a_line.wav", b"RIFF"),
     "names no line in"),
    ("vo: a plain Microsoft WAV renamed to .wem",
     drop_vo("decision.dec_absorb_1.wem", renamed_wav()),
     "plain Microsoft WAV"),
    ("vo: a codec nothing in the game or any mod uses",
     drop_vo("decision.dec_absorb_1.wem", wrong_codec()),
     "nothing in the game or in any installed mod uses"),
    ("vo: a truncated .wem",
     drop_vo("decision.dec_absorb_1.wem", b"RIFF\x00\x00"),
     "not a RIFF/WAVE file at all"),
    ("vo: a file that is not audio at all",
     drop_vo("decision.dec_absorb_1.txt", b"notes to self"),
     "is not audio the build knows"),
    # Notes read aloud (D125). Worse than a missing recording, because Shard
    # Audio Framework draws the "Toggle Audio" button on every uncrypted shard
    # whether or not anything answers it: the button is there, it is pressed, and
    # nothing happens.
    ("narration: a recording named after no shard",
     drop_narration("mara_diary.wav"),
     "names no shard in"),
    ("narration: a file that is not audio at all",
     drop_narration("mara_journal.txt", b"notes to self"),
     "is not audio Audioware can read"),
    ("narration: a recording under a locale that ships no voiceover",
     drop_narration("mara_journal.wav", locale="ua-ua"),
     "ships no voiceover"),
    # An "ms" override and a recording are each fine alone. Together, the override
    # wins by design, so a stale one silently truncates the voice.
    ("timing: an explicit ms shorter than the recording beside it",
     both(set_line_ms("mara_open_1", 1500),
          drop_vo("mara.mara_open_1.wem", real_wem(4.0))),
     "before the voice stops"),
    ("timing: an explicit ms longer than the recording is legal - it only adds silence",
     both(set_line_ms("mara_open_1", 9000),
          drop_vo("mara.mara_open_1.wem", real_wem(4.0))),
     None),

    # ...and the two states the folder is legitimately in.
    ("vo: a real PCM .wem under a real line name is legal",
     drop_vo("decision.dec_absorb_1.wem", real_wem()),
     None),
    ("vo: a .wav not yet converted is legal - validate runs before the build",
     drop_vo("decision.dec_absorb_1.wav", b"RIFF"),
     None),

    # D42 made the voice locales a smaller set than the text locales. Audio under
    # a locale the mod does not voice converts, packs and never plays - the same
    # silent nothing as a misnamed file, but harder to notice because the name is
    # right and the folder looks deliberate.
    ("vo: a correctly named .wem under a locale that ships no voiceover",
     drop_vo("decision.dec_absorb_1.wem", real_wem(), locale="ua-ua"),
     "ships no voiceover"),
    ("vo: a source file awaiting conversion under an unvoiced locale, same problem",
     drop_vo("decision.dec_absorb_1.wav", b"RIFF", locale="ua-ua"),
     "ships no voiceover"),

    # A choice option may carry a questCondition (reference/choice_conditions.md).
    # A failing condition REMOVES the option, so the ways to get this wrong are a
    # fact that will never be true and a hub with no unconditional way out.
    ("choice: option gated on a fact facts.json does not declare",
     opt_condition("hub", "opt_price", {"fact": "ashcache_no_such_fact", "value": 1}),
     "does not declare"),
    ("choice: every option in a hub is gated, so the hub can open empty",
     condition_every_option("hub"),
     "every one of them is conditional"),
    ("choice: gating one option of a hub is legal",
     opt_condition("hub", "opt_price", {"fact": "ashcache_journal_read", "value": 1}),
     None),

    # The bug this locks out shipped for weeks: 12 descriptions written,
    # localized and present in the resource, every one of them filtered out of
    # GetDescriptions because nothing set its state. QuestLogUtils
    # .UnpackRecursiveWithFilter skips any entry that is Inactive and exempts
    # only JournalQuestMapPinBase - so the map pins kept working and hid it.
    ("journal: an objective's description paragraph is never activated",
     mutate("quest_graph.json", lambda d: (
         d["nodes"].remove(next(n for n in d["nodes"]
                                if n["id"] == "desc_goto_dogtown")),
         d.__setitem__("links", [l for l in d["links"]
                                 if "desc_goto_dogtown" not in l]))),
     "no graph node ever activates it"),

    # A Quest-category sector loads because an ACTIVE PHASE names its prefab -
    # there is no proximity streaming to fall back on. So a prefab ref with a
    # typo is not "slightly wrong": it streams nothing, logs nothing, and looks
    # exactly like the feature not existing. The refs are quoted from vanilla in
    # reference/examples/quest_prefab_streaming.json; this holds that line.
    ("cynosure: a held prefab ref that was never read out of vanilla",
     mutate("cynosure_graph.json", lambda d: (
         [n for n in d["nodes"] if n.get("id") == "cyn_hold"][0]
         .__setitem__("prefabs", ["#q305_pr_inner_bunkers"]))),
     "not one of the refs verified against vanilla"),
    # The safety argument for shipping an untested world change is that it is
    # off until the player asks for it. If anything in the mod can set it, that
    # argument is gone and a playthrough gets two extra sectors it never chose.
    ("cynosure: the quest graph sets the opt-in fact itself",
     mutate("quest_graph.json", lambda d: d["nodes"].append(
         {"id": "cyn_force", "type": "set_fact",
          "fact": "ashcache_cynosure_open", "value": 1})),
     "it is opt-in on purpose"),
    # OI-18 / reference/examples/journal_icons.json. Both of these are legal enum
    # values and legal TweakDB records - they serialize, load and work. The only
    # symptom is a placeholder icon, which is why nothing else ever says so.
    ("journal: a quest type the journal list cannot draw",
     mutate("journal.json",
            lambda d: d["quest"].__setitem__("type", "VehicleQuest")),
     "the generic (!)"),
    ("journal: a real district that has no UIIcon behind it",
     mutate("journal.json",
            lambda d: d["quest"].__setitem__("districtID", "Districts.Brooklyn")),
     "there is no UIIcon."),
    # Positive control. 16 of the 55 vanilla ep1 quests ship no districtID at all,
    # so an empty one must stay legal - a check that forbade it would be wrong
    # about the game rather than strict about the mod.
    ("journal: no districtID at all, as 16 vanilla ep1 quests ship",
     mutate("journal.json", lambda d: d["quest"].__setitem__("districtID", "")),
     None),
]


def run():
    r = subprocess.run([sys.executable, "tools/validate.py"], cwd=WORK,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def reset():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    # reference/ comes along too: check_codex reads reference/codex_paths.txt and
    # degrades to a note when it is absent, so a work tree without it would let
    # every codex case pass by not running at all.
    for d in ("source", "tools", "reference"):
        shutil.copytree(ROOT / d, WORK / d, ignore=shutil.ignore_patterns("__pycache__"))
    # assets/ is linked, not copied: validate.py's Cynosure asset check reads it (a baseline
    # without it fails on every CYN_ASSET_*), no case mutates it, and it is ~100 MB of CR2W.
    (WORK / "assets").symlink_to(ROOT / "assets")


def main():
    reset()
    rc, out = run()
    if rc != 0:
        shutil.rmtree(WORK)
        sys.exit(f"baseline is already failing - fix that before trusting this:\n{out}")
    print(f"baseline clean: {out.strip().splitlines()[-1]}\n")

    failed = []
    for label, breakage, expect in CASES:
        reset()
        breakage()
        rc, out = run()
        # expect None means the opposite claim: this edit is LEGAL and the
        # validator must stay quiet. A check that fires on correct source costs
        # more than one that misses, because the fix is to weaken the check.
        if expect is None:
            if rc == 0:
                print(f"  allowed  {label}")
            else:
                failed.append(label)
                print(f"  FALSE +  {label}\n             should have passed, got rc={rc}\n{out}")
            continue
        hit = [l.strip(" -") for l in out.splitlines() if expect in l]
        if rc != 0 and hit:
            print(f"  caught   {label}\n             {hit[0][:104]}")
        else:
            failed.append(label)
            print(f"  MISSED   {label}\n             expected {expect!r}, got rc={rc}\n{out}")

    shutil.rmtree(WORK)
    n_pos = sum(1 for c in CASES if c[2] is None)
    print(f"\n{len(CASES) - len(failed)}/{len(CASES)} cases held "
          f"({len(CASES) - n_pos} silent failures caught, "
          f"{n_pos} legal edit(s) left alone).")
    if failed:
        sys.exit("checks that did not fire: " + ", ".join(failed))


if __name__ == "__main__":
    main()
