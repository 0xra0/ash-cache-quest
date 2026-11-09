#!/usr/bin/env python3
"""source/journal.json  ->  build/ash_cache.journal.json  (CR2W JSON for WolvenKit)

The journal is what makes the quest exist in the UI: the entry in the log, its
phases, the objective list, the map pins, and the SMS threads. Quest LOGIC is not
here - that is the .questphase graph. This file is purely what the player reads.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cr2w import (H, check_enum, cname, envelope, lockey, noderef, respath_null,
                  tweakdbid, vector3)
from enums import gameContactType, gameJournalQuestType, gamedataMappinVariant

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Both verified working reference mods (Hot Fuzz, Aldecaldos High Stakes) place their
# quest under this folder path regardless of quest type. Following the proven path.
QUEST_FOLDER = "quests/main_quest/prologue"


def load(name):
    return json.loads((ROOT / "source" / name).read_text(encoding="utf-8"))


class Resolver:
    def __init__(self, lockeys):
        self.lockeys = lockeys

    def __call__(self, ref):
        """'str.obj_talk_mara' -> LocalizationString for its allocated LocKey."""
        if not isinstance(ref, str) or not ref.startswith("str."):
            sys.exit(f"expected a 'str.<id>' reference, got {ref!r}")
        sid = ref[4:]
        if sid not in self.lockeys:
            sys.exit(f"string id {sid!r} has no LocKey - run tools/alloc_lockeys.py")
        return lockey(self.lockeys[sid])


def mappin(spec):
    check_enum(spec.get("variant", "QuestGiverVariant"), gamedataMappinVariant,
               f"mappin variant for {spec['id']!r}")
    return H({
        "$type": "gameJournalQuestMapPin",
        "enableGPS": spec.get("enableGPS", 0),
        "entries": [],
        "id": spec["id"],
        "journalEntryOverrideDataList": [],
        "mappinData": {
            "$type": "gamemappinsMappinData",
            "active": 1,
            "debugCaption": "",
            "localizedCaption": {"unk1": "0", "value": ""},
            "mappinType": tweakdbid("Mappins.QuestStaticMappinDefinition"),
            "scriptData": None,
            "variant": spec.get("variant", "QuestGiverVariant"),
            "visibleThroughWalls": spec.get("visibleThroughWalls", 1),
        },
        "offset": vector3(z=spec.get("offsetZ", 0.5)),
        "reference": {
            "$type": "gameEntityReference",
            "dynamicEntityUniqueName": cname("None"),
            "names": [],
            "reference": noderef(spec["nodeRef"]),
            "sceneActorContextName": cname("None"),
            "slotName": cname("None"),
        },
        # slotName is a CName; uiAnimation is a TweakDBID despite the name.
        # Both values copied from the working Hot Fuzz reference.
        "slotName": cname(spec.get("slotName", "UI_Interaction")),
        "uiAnimation": tweakdbid(""),
    })


def quest_description(ref, R):
    """The paragraph the Journal shows above the objective list.

    Vanilla hangs this off an OBJECTIVE, not off the quest, and always with the
    literal id "description" - Hot Fuzz puts one on its first objective, Undermine
    puts one on nearly every objective of every quest. A description per objective
    reads as a story that grows while the player plays, which is the whole
    difference between a quest that feels vanilla and a quest that is a list of
    instructions.

    IT DOES NOT INHERIT THE OBJECTIVE'S STATE. This is a separate journal entry
    and it has to be activated in its own right, by a graph node addressing
    '<objective path>/description'. QuestLogUtils.UnpackRecursiveWithFilter tests
    every entry individually and skips any whose own state is Inactive, exempting
    only JournalQuestMapPinBase - so an unactivated description is silently
    dropped by GetDescriptions and the journal's description panel renders empty
    while the objectives and map pins above it work perfectly. That is exactly
    what shipped here until 2026-09-04; the pins are what hid it. validate.py
    now reports an unactivated description as dead UI and negtest.py holds it.

    Verified 2026-09-08 against the game's own decompiled scripts rather than
    inferred (D49): questLogDetailsPanel.script:151-167 is the entire render
    path - GetDescriptions, dedupe, SetText, no branch - and questLogUtils
    .script:85-104 is the walk. Two things that reading only the filter missed:

      * ACTIVE IS THE ONLY STATE THAT RENDERS. The recursion into an objective
        uses GetDefaultFilter(), which is {active, inactive}: succeeded = false.
        A description ever set to Succeeded vanishes as completely as one left
        Inactive. This one is already unbuildable rather than merely forbidden:
        INPUTS['journal_entry'] in gen_questphase.py declares Active and
        Inactive only, and the link check refuses the socket by name - which is
        also the socket set vanilla ships on its own description nodes.
      * The codex links beside it are NOT a control. PopulateCodexLinks unpacks
        with includeInactive = TRUE and then force-activates each target with
        ChangeEntryStateByHash, so they draw whatever state they are in. The
        description is the only child of an objective filtered on its own state,
        which is why it is the one thing that can be blank while its siblings
        look perfect.
    """
    return H({
        "$type": "gameJournalQuestDescription",
        "description": R(ref),
        "id": "description",
        "journalEntryOverrideDataList": [],
    })


def codex_link(spec):
    """A cross-reference into the game's own codex - the portraits and location
    cards that appear beside a vanilla quest.

    The path is a journal path like 'codex/characters/quests/judy_alvarez', and the
    art comes from the codex entry it names, so linking is free. Vanilla repeats
    the SAME set on every objective of a quest rather than putting them on the
    quest itself; Hot Fuzz does exactly that with three links on all three of its
    objectives, so that is what this follows.

    A wrong path fails silently - there is no error, the link simply never renders.
    One shipping reference mod carries 'odex/glossary/world/militech' and has
    presumably never shown that link to anybody. gen_cet.py resolves every path in
    game so this mod cannot join it.
    """
    return H({
        "$type": "gameJournalQuestCodexLink",
        "id": spec["id"],
        "journalEntryOverrideDataList": [],
        "path": H({
            "$type": "gameJournalPath",
            "className": cname("gameJournalCodexEntry"),
            "editorPath": "",
            "fileEntryIndex": 1,
            "realPath": spec["path"],
        }),
    })


def objective(spec, R, codex_links=()):
    # Vanilla's child order on an objective: map pin, description, codex links.
    entries = []
    if "mapPin" in spec:
        entries.append(mappin(spec["mapPin"]))
    if "summary" in spec:
        entries.append(quest_description(spec["summary"], R))
    entries.extend(codex_link(c) for c in codex_links)
    return H({
        "$type": "gameJournalQuestObjective",
        "counter": spec.get("counter", 0),
        "description": R(spec["description"]),
        "districtID": spec.get("districtID", ""),
        "entries": entries,
        "id": spec["id"],
        "itemID": tweakdbid(""),
        "journalEntryOverrideDataList": [],
        "locationPrefabRef": noderef(spec.get("locationPrefabRef", "")),
        "optional": 1 if spec.get("optional") else 0,
    })


def phase(spec, R, codex_links=()):
    return H({
        "$type": "gameJournalQuestPhase",
        "entries": [objective(o, R, codex_links) for o in spec["objectives"]],
        "id": spec["id"],
        "journalEntryOverrideDataList": [],
        "locationPrefabRef": noderef(spec.get("locationPrefabRef", "")),
    })


def quest(j, R):
    q = j["quest"]
    return H({
        "$type": "gameJournalQuest",
        "districtID": q.get("districtID", ""),
        "entries": [phase(p, R, j.get("codexLinks", [])) for p in j["phases"]],
        "id": q["id"],
        "journalEntryOverrideDataList": [],
        "recommendedLevelID": tweakdbid(q.get("recommendedLevelID", "Character.ScaleToPlayerLevel")),
        "title": R(q["title"]),
        "type": check_enum(q.get("type", "SideQuest"), gameJournalQuestType, "quest type"),
    })


def phone_message(spec, R):
    return H({
        "$type": "gameJournalPhoneMessage",
        "attachment": None,
        "delay": spec.get("delay", 0),
        "id": spec["id"],
        "imageId": {"$type": "TweakDBID", "$storage": "uint64", "$value": "0"},
        "isQuestImportant": 1 if spec.get("questImportant") else 0,
        "journalEntryOverrideDataList": [],
        "sender": spec.get("sender", "NPC"),
        "text": R(spec["text"]),
    })


def phone_conversation(spec, R):
    return H({
        "$type": "gameJournalPhoneConversation",
        "entries": [phone_message(m, R) for m in spec["messages"]],
        "id": spec["id"],
        "journalEntryOverrideDataList": [],
        "title": R(spec["title"]),
    })


def contact(spec, conversations, R):
    """The phone contact an SMS thread hangs off.

    This layer was missing, and its absence is why the mod's messages arrived with
    no name and no portrait: the avatar and the display name live on the CONTACT,
    never on the conversation. Undermine authors one ('uqs') and files all three of
    its threads under it. An earlier reading of that same file concluded the
    threads sat directly under the 'contacts' folder - it had simply not walked
    deep enough to see the contact in between. See OI-2 and D22.

    avatarID is a PhoneAvatars.* TweakDB record. Undermine leaves it 0 and gets the
    blank silhouette; there are 377 real ones in the game, including an Avatar_Unknown
    that is exactly what an anonymous sender should look like.
    """
    return H({
        "$type": "gameJournalContact",
        "avatarID": tweakdbid(spec.get("avatar", "")),
        "entries": conversations,
        "id": spec["id"],
        "isCallableDefault": 1 if spec.get("callable") else 0,
        "journalEntryOverrideDataList": [],
        "name": R(spec["name"]),
        "type": check_enum(spec.get("type", "Texter"), gameContactType,
                           f"contact type for {spec['id']!r}"),
        "useFlatMessageLayout": 1 if spec.get("flatLayout", True) else 0,
    })


# Which class each top-level folder id is written as. This is a lookup and not a
# rule, because there is no rule: the two references are each internally consistent
# and disagree with each other. High Stakes writes every folder it touches as
# gameJournalFolderEntry - including a bare 'onscreens' - while Undermine writes
# every folder it touches as gameJournalPrimaryFolderEntry, including a bare
# 'contacts'. Both ship and both work, so the engine accepts either at the root.
#
# An earlier version of this file inferred the type from how many slashes the id
# had, which fit three of the four samples and got 'onscreens' wrong. Matching the
# observed sample for each specific id is the only thing the evidence supports.
FOLDER_TYPE = {
    "quests/main_quest/prologue": "gameJournalFolderEntry",       # HotFuzz, HighStakes
    "contacts":                   "gameJournalPrimaryFolderEntry",  # Undermine
    "onscreens":                  "gameJournalFolderEntry",       # HighStakes
}


def folder(fid, entries):
    # A contact subfolder ('contacts/panam') is the High Stakes shape.
    default = "gameJournalFolderEntry"
    return H({
        "$type": FOLDER_TYPE.get(fid, default),
        "entries": entries,
        "id": fid,
        "journalEntryOverrideDataList": [],
    })


def onscreen_group(group, shards, R):
    """The 'onscreens' subtree a readable shard's Read action opens.

    An item action's journalEntry is a path into this tree - gen_tweak.py writes
    'onscreens/<group>/<entry>' and this builds the folder, group and entry it
    names. Copied from Aldecaldos High Stakes, whose regina_shard does exactly
    this; vanilla's mq006_body_shard does the same with a much deeper path.
    """
    return H({
        "$type": "gameJournalOnscreenGroup",
        "entries": [H({"$type": "gameJournalOnscreen",
                       "description": R(s["body"]),
                       "iconID": tweakdbid(""),
                       "id": s["entry"],
                       "journalEntryOverrideDataList": [],
                       "tag": cname("None"),
                       "title": R(s["title"])}) for s in shards],
        "id": group,
        "journalEntryOverrideDataList": [],
    })


def main():
    j = load("journal.json")
    lockeys = {k: v for k, v in load("lockeys.json").items() if not k.startswith("_")}
    R = Resolver(lockeys)

    folders = [folder(QUEST_FOLDER, [quest(j, R)])]

    # SMS threads hang off a CONTACT, and the contact hangs off the 'contacts'
    # folder. Two shapes ship, and the difference is who owns the avatar:
    #
    #   contacts/<vanilla contact>   the thread is appended to a real vanilla
    #                                contact's history and inherits that person's
    #                                name and portrait. Hot Fuzz does this with
    #                                contacts/judy; High Stakes with contacts/panam
    #                                and contacts/reginald_reggie_jones. No contact
    #                                entry is authored - vanilla already has one.
    #   contacts + an authored       a NEW contact, carrying its own name, type and
    #   gameJournalContact           avatar. Undermine does this: folder 'contacts'
    #                                -> Contact 'uqs' -> its three threads.
    #
    # Ash Cache's senders are anonymous, so there is no vanilla person to file them
    # under and the second shape is the right one. This used to emit the folder and
    # then drop the conversations straight into it, which is neither shape: the
    # messages arrived owned by nobody, so the phone had no name and no portrait to
    # show. That was read off Undermine, whose three thread ids do sit under
    # 'contacts' - but under a Contact in between that the earlier pass never
    # descended into. Re-walking the tree is what found it. OI-2, D22.
    #
    # This also lengthens the journal path of every message by one segment, which
    # the quest graph's sms nodes have to match exactly or they address nothing.
    # validate.py checks that.
    by_contact = {}
    for conv in j.get("phoneConversations", []):
        c = conv["contact"]
        entry = by_contact.setdefault(c["id"], (c, []))
        # An empty "messages" is a contact who CALLS and never texts (D126). The
        # conversation is dropped rather than written empty, because an empty
        # gameJournalPhoneConversation is a real thing the player sees: a blank
        # thread under a name in the messages app with nothing in it to open. The
        # contact itself still has to be emitted - it is what a holocall's
        # questCallContact node names, and what supplies the name and the avatar
        # the phone draws while it rings.
        if conv["messages"]:
            entry[1].append(phone_conversation(conv, R))
    if by_contact:
        folders.append(folder("contacts",
                              [contact(c, convs, R) for c, convs in by_contact.values()]))

    # Readable shards (source/items.json) put their text here, not in the item
    # record: the record only names the path, and this is what sits at the end of
    # it. A shard whose journalEntry points at nothing opens an empty reader.
    groups = {}
    for item in load("items.json")["items"]:
        if item.get("kind") != "shard":
            continue
        o = item["onscreen"]
        groups.setdefault(o["group"], []).append(
            {"entry": o["entry"], "title": f"str.{o['title']}", "body": f"str.{o['body']}"})
    if groups:
        folders.append(folder("onscreens",
                              [onscreen_group(g, sh, R) for g, sh in sorted(groups.items())]))

    root = {
        "$type": "gameJournalResource",
        "cookingPlatform": "PLATFORM_PC",
        "entry": H({
            "$type": "gameJournalRootFolderEntry",
            "descriptor": respath_null(),
            "entries": folders,
            "id": "",
            "journalEntryOverrideDataList": [],
        }),
    }

    out = ROOT / "build" / "ash_cache.journal.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope(root, "CR2W"), indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")

    n_obj = sum(len(p["objectives"]) for p in j["phases"])
    n_sms = sum(len(c["messages"]) for c in j.get("phoneConversations", []))
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"  quest '{j['quest']['id']}' ({j['quest'].get('type')}), "
          f"{len(j['phases'])} phases, {n_obj} objectives, {n_sms} sms in "
          f"{len(j.get('phoneConversations', []))} threads "
          f"under {len(by_contact)} contact(s), "
          f"{sum(len(v) for v in groups.values())} onscreen shard(s)")


if __name__ == "__main__":
    main()
