#!/usr/bin/env python3
"""source/*.json  ->  build/cet/init.lua

The dev console. NOT SHIPPED - build.sh deploys it to dev/cet/, and the deploy
step copies mod/ only. The tech spec's own table says CET Lua is "Dev only, not
shipped", and it stays that way: the quest must be playable by someone who has
never heard of CET.

WHY IT IS THIS BIG
------------------
A quest mod fails in six independent places and every one of them looks the same
from inside the game - nothing happens. The archive can fail to mount; it can
mount with the .journal missing; TweakXL can refuse the item records; the
localization jsons can be absent so every line renders as LocKey#77315001; the
redscript glue can fail to compile so no trigger ever fires; and the graph can be
running perfectly while the beat you are waiting on is one of the four nobody has
authored yet (OI-13). Six causes, one symptom.

So the panel's first tab is not a cheat menu, it is a layer test. Each row asks
the engine one question whose answer can only be produced by that layer:

  archive        does quests/main_quest/prologue/ash_cache resolve to an entry?
                 the .journal only exists inside ashcache.archive.
  onscreens      do the two shard bodies resolve? same archive, different file,
                 so this separates "archive missing" from "file missing".
  localization   does LocKey#77315000 come back as text rather than as itself?
  tweaks         does TweakDB have Items.ashcache_splinter? that is r6/tweaks/,
                 a loose file, deployed separately from the archive - the single
                 most common half-deploy.
  glue           is AshCache.AshCacheGlue attached? that is r6/scripts/, also
                 loose, also deployed separately.
  progress       where the graph actually is, so a green stack with a stuck
                 quest points at OI-13 rather than at the build.

Then Journal shows every objective's live gameJournalEntryState, because "there
is no map pin" and "the objective never activated" are the same sentence to a
player and different bugs to fix. Trace polls every fact four times a second and
logs transitions, which turns "I walked in and nothing happened" into a timeline
with the exact fact that did or did not flip. Report writes all of it to
report.txt next to this file, for pasting back.

The build stamp is in the report on purpose. Testing a stale deploy against fresh
source produces bug reports for code that is not running, and that is expensive
to discover by reading.

EVERY API HERE WAS READ OUT OF AN INSTALLED, WORKING CET MOD (rule 8), not
recalled - the mods directory under bin/x64/plugins/cyber_engine_tweaks holds a
few hundred of them:

  Game.GetQuestsSystem():GetFactStr/SetFactStr            119 mods
  Game.GetJournalManager():GetEntryByString(path, class)   29 mods
  ...:GetEntryState(e) == gameJournalEntryState.Active     (same)
  Game.GetLocalizedText("LocKey#N")                        112 mods
  TweakDB:GetRecord("Items.x")                              48 mods
  Game.GetTransactionSystem():GetItemQuantity(p, ItemID.new(TweakDBID.new(s)))
                                                            25 mods
  Game.GetScriptableSystemsContainer():Get("Module.Class")  66 mods
  Game.GetTeleportationFacility():Teleport(e, Vector4, EulerAngles)
  ImGui.SetClipboardText, io.open("report.txt", "w") at mod root, os.date

gameJournalEntryState's five members are checked against WolvenKit's
cp77enums.cs, the same oracle tools/refresh_enums.py reads.
"""
import hashlib
import json
import pathlib
import time

# The journal root every path hangs off, taken from the generator that WRITES the
# resource rather than copied. A debug tool that disagrees with the thing it is
# debugging reports the archive as unmounted forever, and the tester goes looking
# in the wrong place - which is worse than having no panel. validate.py keeps its
# own copy on purpose: the validator has to be able to reject the source without
# any generator being importable.
from gen_journal import QUEST_FOLDER as QUEST_ROOT
import gen_xl

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "cet" / "init.lua"

# The redscript system the glue layer attaches. Module-qualified, which is how
# ScriptableSystemsContainer keys a class declared inside a redscript module -
# see NightCityAllies.Persistence.PersistenceSystem in the installed mods.
GLUE_SYSTEM = "AshCache.AshCacheGlue"

# The gates behind each act, in spine order. Jumping to act N means everything up
# to and including N-1 has notionally happened, so all of it gets set at once.
# Kept here rather than derived from the graph: "what a tester means by act 4" is
# a judgement about the story, not a fact about the node list.
ACTS = [
    (1, "Act 1 - the SMS, go to Dogtown", ["ashcache_start"]),
    (2, "Act 2 - the courier's room searched", ["ashcache_at_motel", "ashcache_courier_log_played"]),
    # D118 moved ashcache_box_opened out of act 3 and into act 4, with
    # ashcache_splinter_given beside it. Act 3 IS the case: since the case now
    # takes two prompts (open it, then take the splinter), setting box_opened as
    # part of arriving at the clinic landed the tester past the beat they came to
    # look at. The pair has to travel together, because take_chip is a scene the
    # walk BLOCKS on - box_opened without splinter_given would park a tester
    # jumping to act 5 at a prompt back in the clinic. The cost is that a jumped
    # -ahead tester does not hold the splinter item, only the fact that says they do.
    (3, "Act 3 - at the clinic, case not yet opened", ["ashcache_at_clinic"]),
    # D119: act 4 is now also "standing at the terminal with nothing downloaded".
    # It deliberately does NOT set ashcache_terminal_read - that fact is the
    # guard in front of the terminal menu, and setting it here would skip the
    # beat the button exists to reach. Same reasoning as act 3 and the case.
    (4, "Act 4 - Mara met, terminal not yet read",
        ["ashcache_box_opened", "ashcache_splinter_given",
         "ashcache_mara_choice_made"]),
    # terminal_full_read travels with terminal_read: it is set inside the same
    # scene, so a tester jumped past the menu never had the chance to take the
    # optional read, and the chip tree would otherwise owe them a point they
    # cannot earn any more.
    (5, "Act 5 - terminal read", ["ashcache_terminal_read",
                                  "ashcache_terminal_full_read"]),
    (6, "Act 6 - cleanup survived", ["ashcache_cleanup_done"]),
    # D120: this one forces ONE ending, so say which. It is now a live test
    # rather than a bookmark - the walk lands on br_destroy, the guard reads
    # ashcache_epilogue_played as 0 and the burn beat plays. To try the other two,
    # take Act 6 instead and choose in the hub; deliberately not listed here,
    # because a button per ending would be four ways to skip the one scene that
    # makes the ending mean anything.
    (7, "Act 7 - decided: burn the splinter", ["ashcache_decision_made",
                                               "ashcache_end_destroy"]),
]


def lua_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def fact_groups(facts):
    """[(group label, [fact name])] in the order facts.json declares them."""
    out = []
    for group, body in facts.items():
        if group.startswith("_") or group == "ending_gates":
            continue
        names = [k for k in body if not k.startswith("_")]
        if names:
            out.append((group, names))
    return out


def source_stamp(src):
    """A build identity the report can carry back.

    Hashes source/, not build/, because gen_cet.py runs before the archive is
    packed - there is nothing downstream to hash yet. It answers the only
    question that matters when a report disagrees with the code in front of me:
    is the game running this source or an older one. tools/collect_logs.py
    recomputes it and compares.
    """
    h = hashlib.sha1()
    for path in sorted(src.glob("*.json")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:8]


PANEL = r'''
----------------------------------------------------------------- runtime state
local qs, shown = nil, false

-- The trace. Newest first, so the thing that just happened is the thing you are
-- looking at; capped because this polls forever and a tester leaves the game on.
local trace, TRACE_MAX = {}, 240
local lastFact, lastObj = {}, {}
local accFast, accSlow = 0.0, 0.0
local baselined = false
local entryCache = {}
-- What the Voice tab last asked the audio system to play, echoed back so a
-- press that does nothing is distinguishable from a press that did not register.
local voSaid = ""

-- A COPY OF THE TRACE THAT SURVIVES THE PROCESS.
--
-- The in-memory trace is gone the instant the game dies, which is the one
-- moment it is worth reading. Every crash in this quest so far has been a
-- redDispatcher job thread faulting some milliseconds AFTER the main thread did
-- something, so the last thing this panel saw is the only witness to what that
-- something was - and CrashBreadcrumb, which used to supply the position half
-- of it, is no longer installed.
--
-- Appended, and FLUSHED per line. A buffered write that never reaches disk is
-- not evidence; it is the absence of evidence, indistinguishable from a panel
-- that saw nothing.
local trail = nil

-- Each line is stamped to the millisecond and with a frame number, so it can be
-- laid against CrashLogger's breadcrumbs: its "first-chance ACCESS_VIOLATION"
-- line carries milliseconds (17:52:28.503 on 2026-09-15), and a whole-second
-- trail cannot say whether a fact edge came before that fault or after it.
-- os.date has only seconds; the fraction is the dt summed since os.time() last
-- ticked over, so it is right to within one frame and needs only the stdlib.
local frame, wallSec, wallFrac = 0, os.time(), 0.0
local function stamp()
  return string.format("%s.%03d f%-6d", os.date("%H:%M:%S", wallSec),
                       math.min(999, math.floor(wallFrac * 1000)), frame)
end

local function trailWrite(kind, text)
  if not trail then return end
  trail:write(string.format("%s %-5s %s\n", stamp(), kind, text))
  trail:flush()
end

-- The hot window. Every Acts crash so far faulted within a second of a fact
-- write, and inside that second the graph runs an item grant with its popup, an
-- objective with its popup, and a scene start. A 0.25 s poll cannot order three
-- things that fast. So for HOT_SECONDS after any write, fact edge or item change,
-- each frame opens with a "tick" line: the last tick before a crash is the last
-- frame the main thread finished, and every line after it happened inside it.
--
-- The window stamps frames; it does not poll faster. Build 2026-09-15 18:02 also
-- polled facts, items and objectives every frame while hot, and every save load
-- after it froze or crashed (OI-21). A load opens the window by itself - item
-- counts go 0 -> -1 at detach and -1 -> 0 at attach - so that build called
-- GetFactStr, GetEntryState and GetItemQuantity every frame through world
-- teardown and attach. The 17:34 build polled at 0.25 s / 1 s and loaded fine.
local HOT_SECONDS, hot = 6.0, 0.0
local lastItem = {}

local function fact(n) return qs and qs:GetFactStr(n) or 0 end
-- Fact writes are QUEUED here, never applied here.
--
-- ImGui button callbacks run inside CET's D3D12 present hook: the render
-- thread, in the middle of a frame. Calling questsSystem:SetFactStr from there
-- re-enters the fact dispatch on a thread the engine never calls it from, and
-- every edge it fires kicks spawns and scene starts onto redDispatcher job
-- threads at once. Six of those from one press of an Acts button is what killed
-- the game twice on 2026-09-09 - crash signatures CFBFFB1D and 17370EC2, both a
-- redDispatcher reading 0xFFFFFFFFFFFFFFFF, the second one with
-- cyber_engine_tweaks.asi and Codeware.dll still on the stack.
--
-- onUpdate runs on the game main thread at a tick boundary, which is where the
-- engine itself changes facts. So the queue is drained there, one write per
-- tick: the graph gets each edge in its own frame, exactly as a quest node
-- would deliver it. Order is preserved, so gates still land before progress.
local factQueue = {}
local FACT_QUEUE_MAX = 64

-- Step mode drains the queue by hand instead of one write per frame.
--
-- One per frame is 16 ms apart, and an Acts press is six of them: the graph
-- gets six fact edges inside a tenth of a second, which is a cadence no quest
-- node produces. That is a suspect for the crash that has followed the Acts
-- buttons since 2026-09-09, and it is also the reason the trail cannot say
-- WHICH edge did it - they all land inside one second. Step mode makes each
-- edge a separate press, so the trail's last line names one fact, and a burst
-- that only kills at speed stops killing.
--
-- Off by default: the diagnostic must be able to reproduce the crash before it
-- can explain it.
local stepMode, stepOnce = false, false

local function setFact(n, v)
  if #factQueue >= FACT_QUEUE_MAX then return end
  factQueue[#factQueue + 1] = { n = n, v = v }
end

local function note(kind, text)
  table.insert(trace, 1, { t = os.date("%H:%M:%S"), kind = kind, text = text })
  while #trace > TRACE_MAX do table.remove(trace) end
  trailWrite(kind, text)
end

-- Main thread, one write per tick. See the comment on setFact.
local function drainFactQueue()
  if #factQueue == 0 or qs == nil then return end
  if stepMode then
    if not stepOnce then return end
    stepOnce = false
  end
  local job = table.remove(factQueue, 1)
  -- Bracketed on purpose. SetFactStr returns as soon as the edge is queued; the
  -- graph work it starts runs on job threads and can fault after we are back.
  -- So a trail ending on "wr->" blames this write, and a trail ending on the
  -- matching "write" line says the main thread survived it and the fault came
  -- out of what it set in motion. Those are different bugs.
  trailWrite("wr->", string.format("%s = %d   (%d queued behind)",
       job.n, job.v, #factQueue))
  qs:SetFactStr(job.n, job.v)
  hot = HOT_SECONDS
  note("write", string.format("%s = %d   (%d still queued)",
       (job.n:gsub("^ashcache_", "")), job.v, #factQueue))
end

-- GetEntryByString returns nil for a path the journal does not have, which is
-- exactly the signal the diagnostics want - but it is also a lookup by string on
-- every call, so found entries are cached. Misses are NOT cached: a journal
-- entry can appear when the quest starts, and a cached nil would report the
-- archive as broken for the rest of the session.
local function entry(path, class)
  if entryCache[path] then return entryCache[path] end
  local jm = Game.GetJournalManager()
  if not jm then return nil end
  local e = jm:GetEntryByString(path, class)
  if e then entryCache[path] = e end
  return e
end

local function stateName(s)
  if s == nil then return "-" end
  if s == gameJournalEntryState.Active    then return "ACTIVE"    end
  if s == gameJournalEntryState.Succeeded then return "done"      end
  if s == gameJournalEntryState.Failed    then return "FAILED"    end
  if s == gameJournalEntryState.Inactive  then return "inactive"  end
  if s == gameJournalEntryState.Undefined then return "undefined" end
  return tostring(s)
end

local function objState(path)
  local jm = Game.GetJournalManager()
  if not jm then return nil end
  local e = entry(path, "gameJournalQuestObjective")
  if not e then return nil end
  local s = jm:GetEntryState(e)
  -- Undefined is the zero state, and a cached handle from before the quest's own
  -- journal file was loaded reports it forever: the 12:34 report showed all fifteen
  -- objectives Undefined, with one inactive->undefined transition at the moment the
  -- entries were first cached and nothing after it, while the player was demonstrably
  -- walking the quest. Whether that is a stale handle or a genuine zero, re-resolving
  -- once costs a string lookup and cannot report LESS than the cache did.
  if s == gameJournalEntryState.Undefined then
    entryCache[path] = nil
    local fresh = jm:GetEntryByString(path, "gameJournalQuestObjective")
    if fresh then
      entryCache[path] = fresh
      s = jm:GetEntryState(fresh)
    end
  end
  return s
end

-- The description paragraph is a SEPARATE journal entry - id 'description', a
-- child of the objective - and it carries its own state, which it does NOT
-- inherit from the objective. QuestLogUtils.GetDescriptions walks the quest with
-- inactive = false and UnpackRecursiveWithFilter drops every entry whose own
-- state is Inactive, exempting only JournalQuestMapPinBase. So a description
-- that was never activated renders as an empty panel while the objectives and
-- the three codex cards above it look perfect.
--
-- The codex cards are NOT evidence that the objective's children are alive:
-- PopulateCodexLinks unpacks with includeInactive = TRUE and then force-
-- activates whatever it finds. Only the description is filtered on its own
-- state, which is why it is the one thing that can be blank while everything
-- around it is right. Both facts read off the game's own scripts,
-- cyberpunk/UI/fullscreen/quest_log/{questLogUtils,questLogDetailsPanel}.script.
local function descState(path)
  local jm = Game.GetJournalManager()
  if not jm then return nil end
  local full = path .. "/description"
  local e = entry(full, "gameJournalQuestDescription")
  if not e then return nil end
  local s = jm:GetEntryState(e)
  -- Same stale-handle re-resolve objState() needs, for the same reason.
  if s == gameJournalEntryState.Undefined then
    entryCache[full] = nil
    local fresh = jm:GetEntryByString(full, "gameJournalQuestDescription")
    if fresh then
      entryCache[full] = fresh
      s = jm:GetEntryState(fresh)
    end
  end
  return s
end

local function itemCount(tdbid)
  local p = Game.GetPlayer()
  local ts = Game.GetTransactionSystem()
  if not p or not ts then return -1 end
  return ts:GetItemQuantity(p, ItemID.new(TweakDBID.new(tdbid)))
end

local function locText(key)
  local s = Game.GetLocalizedText("LocKey#" .. tostring(key))
  if s == nil or s == "" or s == ("LocKey#" .. tostring(key)) then return nil end
  return s
end

-- What the game made of a placed device node. Every call is wrapped: a probe
-- that errors tells us nothing, and CET will happily throw on a nil method.
-- GetLookAtObject is vanilla - core/systems/targetingSystem.script:93,
-- ( instigator, optional withLOS, optional ignoreTransparent ) : GameObject.
local deviceProbe = nil

local function probeLookAt()
  local out = {}
  local function add(s) out[#out + 1] = s end
  local function try(fn, fallback)
    local ok, v = pcall(fn)
    if ok and v ~= nil then return v end
    return fallback
  end
  local p = Game.GetPlayer()
  if not p then add("!no player") return out end

  local obj = try(function()
    return Game.GetTargetingSystem():GetLookAtObject(p, false, false)
  end)
  if not obj then
    add("!look-at returned NOTHING.")
    add("The game says the crosshair is not on any object. Either the entity "
        .. "never spawned, or you are not pointing at it. Use go above, then "
        .. "turn to face it and probe again.")
    return out
  end

  add("class      " .. tostring(try(function() return obj:GetClassName().value end, "?")))
  add("entityID   " .. tostring(try(function() return tostring(obj:GetEntityID().hash) end, "?")))
  add("display    " .. tostring(try(function() return obj:GetDisplayName() end, "")))

  local ps = try(function() return obj:GetDevicePS() end)
  if not ps then
    add("!not a Device - GetDevicePS() returned nothing.")
    add("The .ent loaded and something is standing there, but the device "
        .. "components did not attach. That points at the instanceData buffer, "
        .. "not at the sector or the position.")
    return out
  end

  add("devicePS   " .. tostring(try(function() return ps:GetClassName().value end, "?")))
  add("deviceName " .. tostring(try(function() return ps:GetDeviceName() end, "")))
  add("state      " .. tostring(try(function() return EnumValueToString(
        "EDeviceStatus", EnumInt(ps:GetDeviceState())) end, "?")))
  add("ON         " .. tostring(try(function() return ps:IsON() end, "?")))
  add("unpowered  " .. tostring(try(function() return ps:IsUnpowered() end, "?")))
  add("disabled   " .. tostring(try(function() return ps:IsDisabled() end, "?")))
  add("interactive " .. tostring(try(function() return ps:IsInteractive() end, "?")))
  -- The gates GetActions walks before it offers the player anything. Called
  -- one by one because GetActions itself takes a GetActionsContext struct that
  -- CET cannot build. A door prints "-" for the computer lines and vice versa.
  add("powered    " .. tostring(try(function() return ps:IsPowered() end, "?")))
  add("cameraZoom " .. tostring(try(function() return ps:HasUICameraZoom() end, "?")))
  add("examine    " .. tostring(try(function() return ps:ShouldShowExamineIntaraction() end, "?")))
  add("linkBusy   " .. tostring(try(function() return ps:IsPersonalLinkConnecting() end, "?")))
  add("animState  " .. tostring(try(function() return EnumValueToString(
        "EComputerAnimationState", EnumInt(ps:GetAnimationState())) end, "-")))
  add("door open/locked/sealed "
      .. tostring(try(function() return ps:IsOpen() end, "-")) .. " / "
      .. tostring(try(function() return ps:IsLocked() end, "-")) .. " / "
      .. tostring(try(function() return ps:IsSealed() end, "-")))
  add("It IS a device. Whatever is missing is runtime state, not authoring - "
      .. "read the lines above for which one.")
  return out
end

local function glueSystem()
  local c = Game.GetScriptableSystemsContainer()
  return c and c:Get(GLUE_SYSTEM) or nil
end

--------------------------------------------------------------- the layer report
-- Each row is one question only its own layer can answer, so a red row names the
-- thing to go fix rather than the thing that looked wrong.
local function diagnose()
  local rows = {}
  local function add(ok, name, detail, hint)
    rows[#rows + 1] = { ok = ok, name = name, detail = detail, hint = hint }
  end

  local q = entry(QUEST_ROOT .. "/" .. QUEST_ID, "gameJournalQuest")
  add(q ~= nil, "archive",
      q and "quest entry resolves" or ("nothing at " .. QUEST_ROOT .. "/" .. QUEST_ID),
      "the .journal lives inside ashcache.archive and nowhere else, so this is "
      .. "the mount test. Check archive/pc/mod/ holds BOTH ashcache.archive and "
      .. "ashcache.archive.xl - ArchiveXL needs the .xl to place the sectors.")

  local nOn, missOn = 0, nil
  for _, o in ipairs(ONSCREENS) do
    if entry(o.path, "gameJournalOnscreen") then nOn = nOn + 1 else missOn = missOn or o.label end
  end
  add(missOn == nil, "onscreens",
      string.format("%d/%d shard bodies resolve%s", nOn, #ONSCREENS,
                    missOn and (", missing " .. missOn) or ""),
      "same archive as the quest entry but a different file. Archive green and "
      .. "this red means the pack step dropped the localization tree, not that "
      .. "the mod is unmounted.")

  local nLoc, missLoc = 0, nil
  for _, k in ipairs(LOCKEYS) do
    if locText(k.key) then nLoc = nLoc + 1 else missLoc = missLoc or k.label end
  end
  add(missLoc == nil, "localization",
      string.format("%d/%d lockeys render%s", nLoc, #LOCKEYS,
                    missLoc and (", first missing " .. missLoc) or ""),
      "onscreens.json under localization/<locale>/ did not mount, or the "
      .. "language you are running is not one of the two the mod ships. Every "
      .. "line will read as its own LocKey number in game.")

  local nRec, missRec = 0, nil
  for _, r in ipairs(RECORDS) do
    if TweakDB:GetRecord(r) then nRec = nRec + 1 else missRec = missRec or r end
  end
  add(missRec == nil, "tweaks",
      string.format("%d/%d records exist%s", nRec, #RECORDS,
                    missRec and (", missing " .. missRec) or ""),
      "r6/tweaks/ash_cache.yaml is a LOOSE file - it is not in the archive and "
      .. "does not travel with it. This red with archive green is a half "
      .. "deploy. TweakXL's own log names the line it choked on.")

  local g = glueSystem()
  add(g ~= nil, "glue",
      g and "AshCacheGlue attached" or ("no " .. GLUE_SYSTEM),
      "r6/scripts/AshCache/AshCacheGlue.reds is also loose. If it failed to "
      .. "compile the whole game falls back to vanilla scripts, so check "
      .. "r6/logs/redscript_rCURRENT.log for the first error. No glue means no "
      .. "arrival triggers and no shard hooks: the quest cannot start on its own.")

  -- The journal's furniture. Neither of these can stop the quest, which is exactly
  -- why they need a row: a dead codex path or a missing contact costs the quest its
  -- vanilla look and reports nothing at all while doing it.
  local nCx, missCx = 0, nil
  for _, c in ipairs(CODEX) do
    if entry(c.path, "gameJournalCodexEntry") then nCx = nCx + 1 else missCx = missCx or c.path end
  end
  add(missCx == nil, "codex",
      string.format("%d/%d codex links resolve%s", nCx, #CODEX,
                    missCx and (", dead: " .. missCx) or ""),
      "these are paths into the GAME's codex, not ours, so a red row is a wrong "
      .. "string and nothing else - fix the path in journal.json codexLinks. "
      .. "Note vanilla really does spell it 'distrcts'.")

  local nCt, missCt = 0, nil
  for _, c in ipairs(CONTACTS) do
    if entry(c.path, "gameJournalContact") then nCt = nCt + 1 else missCt = missCt or c.label end
  end
  add(missCt == nil, "contacts",
      string.format("%d/%d sms contacts resolve%s", nCt, #CONTACTS,
                    missCt and (", missing " .. missCt) or ""),
      "the contact owns the avatar and the sender name. Red here means the "
      .. "messages will arrive from nobody, and it also means every sms graph "
      .. "node is addressing a path one level too short (D22).")

  local prog = fact("ashcache_progress")
  add(true, "progress", string.format("ashcache_progress = %d", prog),
      "not a pass/fail. The graph is edge-driven: if this is where you expect "
      .. "and nothing is moving, the next beat is probably one of the four in "
      .. "OI-13 that has no world content yet. The Facts tab colours those.")

  return rows
end

local function blockedNow()
  local out = {}
  for _, g in ipairs(GROUPS) do
    for _, f in ipairs(g.facts) do
      if ORIGIN[f] == "BLOCKED" and fact(f) == 0 then out[#out + 1] = f end
    end
  end
  return out
end

---------------------------------------------------------------------- the report
local function buildReport()
  local L = {}
  local function w(s) L[#L + 1] = s end

  w("Ash Cache - dev report")
  w("written  " .. os.date("%Y-%m-%d %H:%M:%S"))
  w("build    " .. BUILD_STAMP .. "  source " .. BUILD_SRC)
  w("phase    " .. PHASE_RES)
  w("")
  w("== layers ==")
  for _, r in ipairs(diagnose()) do
    w(string.format("  [%s] %-13s %s", r.ok and "ok" or "XX", r.name, r.detail))
  end
  w("")
  w("== facts ==")
  for _, g in ipairs(GROUPS) do
    w("  " .. g.name)
    for _, f in ipairs(g.facts) do
      w(string.format("    %d  %-34s %s", fact(f), f, ORIGIN[f] or "graph"))
    end
  end
  w("")
  w("== journal ==")
  for _, o in ipairs(OBJECTIVES) do
    local e = entry(o.path, "gameJournalQuestObjective")
    w(string.format("    %-9s %-24s %s%s", stateName(objState(o.path)), o.id,
                    e and "" or "NO ENTRY  ", o.optional and "(optional)" or ""))
    if o.hasDesc then
      local de = entry(o.path .. "/description", "gameJournalQuestDescription")
      w(string.format("      desc %-9s %s", stateName(descState(o.path)),
                      de and "" or "NO ENTRY"))
    end
  end
  w("")
  w("== items ==")
  for _, it in ipairs(ITEMS) do
    w(string.format("    %3d  %s", itemCount(it.id), it.id))
  end
  w("")
  local p = Game.GetPlayer()
  if p then
    local pos = p:GetWorldPosition()
    local rot = p:GetWorldOrientation():ToEulerAngles()
    w(string.format("== player ==\n    pos [%.2f, %.2f, %.2f]  yaw %.1f",
                    pos.x, pos.y, pos.z, rot.yaw))
    w("")
  end
  w("== trace (newest first) ==")
  if #trace == 0 then w("    nothing changed while the panel was loaded") end
  for _, t in ipairs(trace) do
    w(string.format("    %s  %-5s %s", t.t, t.kind, t.text))
  end
  return table.concat(L, "\n")
end

local reportStatus = ""
local captured, captureStatus = {}, ""

local function writeReport()
  local text = buildReport()
  ImGui.SetClipboardText(text)
  -- CET sandboxes io to this mod's own folder, so a bare filename lands next to
  -- init.lua. The clipboard copy happens first and unconditionally: if the file
  -- write is refused, the report is still recoverable with one paste.
  local f = io.open("report.txt", "w")
  if f then
    f:write(text)
    f:close()
    reportStatus = "written to mods/ash_cache_debug/report.txt (and copied)"
  else
    reportStatus = "could not open report.txt - copied to the clipboard only"
  end
end

------------------------------------------------------------------------ polling
registerForEvent("onInit", function()
  qs = Game.GetQuestsSystem()
  -- Append, never truncate: the session that matters is the one that did not
  -- get to close the file.
  trail = io.open("trail.log", "a")
  trailWrite("sess", string.format("==== session start   build %s (%s) ====",
             BUILD_STAMP, BUILD_SRC))
end)

registerForEvent("onOverlayOpen",  function() shown = true  end)
registerForEvent("onOverlayClose", function() shown = false end)

-- Facts are cheap to read and are the whole causal chain, so they are polled
-- fast. Journal states go through a string lookup per objective, so they are
-- polled once a second - a beat that takes under a second to appear and vanish
-- is not a beat anyone is debugging.
registerForEvent("onUpdate", function(dt)
  if not qs then return end
  dt = dt or 0
  frame = frame + 1
  local now = os.time()
  if now ~= wallSec then wallSec, wallFrac = now, 0.0 else wallFrac = wallFrac + dt end
  if hot > 0 then
    hot = hot - dt
    trailWrite("tick", string.format("dt %.1f ms", dt * 1000))
  end

  -- Before anything else: this is the main thread, so it is the only safe place
  -- in the whole panel to write a fact.
  drainFactQueue()

  accFast = accFast + dt
  if accFast >= 0.25 then
    accFast = 0
    for _, g in ipairs(GROUPS) do
      for _, f in ipairs(g.facts) do
        local v, prev = fact(f), lastFact[f]
        lastFact[f] = v
        if prev ~= nil and prev ~= v then
          hot = HOT_SECONDS
          note("fact", string.format("%s  %d -> %d   [%s]",
               (f:gsub("^ashcache_", "")), prev, v, ORIGIN[f] or "graph"))
        end
      end
    end
    if not baselined then
      -- One line saying where the save already was, so a trace that opens with
      -- no events is distinguishable from a trace of a quest that never started.
      baselined = true
      local on = {}
      for _, g in ipairs(GROUPS) do
        for _, f in ipairs(g.facts) do
          if lastFact[f] ~= 0 then on[#on + 1] = (f:gsub("^ashcache_", "")) end
        end
      end
      note("base", #on == 0 and "every fact 0 - quest has not started"
                             or ("already set: " .. table.concat(on, ", ")))
    end
  end

  accSlow = accSlow + dt
  local slowDue = accSlow >= 1.0
  if slowDue then
    accSlow = 0
    -- The position half of the old CrashBreadcrumb. One line a second is enough
    -- to answer the only question a stack cannot: where was the player standing.
    local pp = Game.GetPlayer()
    if pp then
      local ppos = pp:GetWorldPosition()
      trailWrite("pos", string.format("%.1f %.1f %.1f", ppos.x, ppos.y, ppos.z))
    end
  end
  -- Items and objectives: once a second, hot or not. See the hot window comment.
  if slowDue then
    for _, it in ipairs(ITEMS) do
      local q, prev = itemCount(it.id), lastItem[it.id]
      lastItem[it.id] = q
      if prev ~= nil and prev ~= q then
        hot = HOT_SECONDS
        note("item", string.format("%s  %d -> %d", it.label, prev, q))
      end
    end
    for _, o in ipairs(OBJECTIVES) do
      local s, prev = stateName(objState(o.path)), lastObj[o.path]
      lastObj[o.path] = s
      if prev ~= nil and prev ~= s then
        note("obj", string.format("%s  %s -> %s", o.id, prev, s))
      end
      -- The description transition is the whole point of the probe: the graph
      -- fires the objective node and the description node in the same beat, so
      -- an objective that goes ACTIVE with no matching desc line one second
      -- later means the desc node was never entered - a stale save, not a bad
      -- archive. Sharing lastObj is safe: the key carries the /description.
      if o.hasDesc then
        local dk = o.path .. "/description"
        local ds, dprev = stateName(descState(o.path)), lastObj[dk]
        lastObj[dk] = ds
        if dprev ~= nil and dprev ~= ds then
          note("obj", string.format("%s/description  %s -> %s", o.id, dprev, ds))
        end
      end
    end
  end
end)

--------------------------------------------------------------------------- draw
registerForEvent("onDraw", function()
  if not shown then return end
  ImGui.SetNextWindowSize(560, 680, ImGuiCond.FirstUseEver)
  if not ImGui.Begin("Ash Cache - dev") then ImGui.End() return end

  if ImGui.Button("write report") then writeReport() end
  ImGui.SameLine()
  ImGui.TextDisabled(BUILD_SRC .. " / " .. BUILD_STAMP .. " / " .. PHASE_RES)
  if reportStatus ~= "" then ImGui.TextWrapped(reportStatus) end
  ImGui.Separator()

  if ImGui.BeginTabBar("ac_tabs") then

    if ImGui.BeginTabItem("Status") then
      local rows, bad = diagnose(), 0
      for _, r in ipairs(rows) do if not r.ok then bad = bad + 1 end end
      if bad == 0 then
        ImGui.TextColored(0.4, 1.0, 0.4, 1.0, "every layer up")
      else
        ImGui.TextColored(1.0, 0.4, 0.4, 1.0, bad .. " layer(s) down - fix these first")
      end
      ImGui.Separator()
      for _, r in ipairs(rows) do
        if r.ok then
          ImGui.TextColored(0.4, 1.0, 0.4, 1.0, string.format("ok  %-13s", r.name))
        else
          ImGui.TextColored(1.0, 0.4, 0.4, 1.0, string.format("XX  %-13s", r.name))
        end
        ImGui.SameLine()
        ImGui.Text(r.detail)
        if ImGui.IsItemHovered() then ImGui.SetTooltip(r.hint) end
      end
      ImGui.Separator()
      local bl = blockedNow()
      ImGui.TextWrapped(string.format(
        "%d fact(s) still have nothing behind them (OI-13). Reaching a beat "
        .. "that waits on one of these is not a bug in what is built - set it "
        .. "by hand on the Facts tab to see what comes after.", #bl))
      for _, f in ipairs(bl) do
        ImGui.TextColored(1.0, 0.6, 0.2, 1.0, "    " .. (f:gsub("^ashcache_", "")))
      end
      ImGui.EndTabItem()
    end

    if ImGui.BeginTabItem("Facts") then
      for _, g in ipairs(GROUPS) do
        if ImGui.CollapsingHeader(g.name) then
          for _, f in ipairs(g.facts) do
            local v = fact(f)
            local origin = ORIGIN[f]
            local label = f:gsub("^ashcache_", "")
            if origin == "BLOCKED" then
              ImGui.TextColored(1.0, 0.6, 0.2, 1.0, string.format("%d  %s", v, label))
              if ImGui.IsItemHovered() then
                ImGui.SetTooltip("nothing sets this yet - OI-13")
              end
            elseif origin == "scene" then
              ImGui.TextColored(0.6, 0.8, 1.0, 1.0, string.format("%d  %s", v, label))
              if ImGui.IsItemHovered() then
                ImGui.SetTooltip("set inside a .scene - needs the conversation played "
                  .. "and that option picked, not just the graph reaching it")
              end
            else
              ImGui.Text(string.format("%d  %s", v, label))
            end
            ImGui.SameLine()
            if ImGui.SmallButton("set##" .. f)   then setFact(f, 1) end
            ImGui.SameLine()
            if ImGui.SmallButton("clear##" .. f) then setFact(f, 0) end
          end
        end
      end
      ImGui.EndTabItem()
    end

    if ImGui.BeginTabItem("Journal") then
      ImGui.TextWrapped("What the engine thinks the log says. 'NO ENTRY' means the "
        .. "archive never delivered that objective; 'undefined' means it delivered "
        .. "it and the graph has not activated it yet. A missing map pin is almost "
        .. "always the second one.")
      ImGui.TextWrapped("The indented 'desc' line is the description paragraph, a "
        .. "separate entry with a separate state. The journal screen prints it only "
        .. "while it is ACTIVE, so an objective that is ACTIVE over a desc that is "
        .. "not is exactly the blank-description bug. 'force' sets it by hand: if "
        .. "the paragraph then appears, everything but the graph flow was fine.")
      ImGui.Separator()
      local qe = entry(QUEST_ROOT .. "/" .. QUEST_ID, "gameJournalQuest")
      ImGui.Text("quest: " .. (qe and stateName(Game.GetJournalManager():GetEntryState(qe))
                                  or "NO ENTRY"))
      ImGui.Separator()
      local phase = nil
      for _, o in ipairs(OBJECTIVES) do
        if o.phase ~= phase then
          phase = o.phase
          ImGui.TextDisabled(phase)
        end
        local e = entry(o.path, "gameJournalQuestObjective")
        local s = stateName(objState(o.path))
        if not e then
          ImGui.TextColored(1.0, 0.4, 0.4, 1.0, string.format("    NO ENTRY  %s", o.id))
        elseif s == "ACTIVE" then
          ImGui.TextColored(0.4, 1.0, 0.4, 1.0, string.format("    %-9s %s", s, o.id))
        elseif s == "done" then
          ImGui.TextDisabled(string.format("    %-9s %s", s, o.id))
        else
          ImGui.Text(string.format("    %-9s %s", s, o.id))
        end
        if o.optional then ImGui.SameLine() ImGui.TextDisabled("(optional)") end
        if o.hasDesc then
          local de = entry(o.path .. "/description", "gameJournalQuestDescription")
          local ds = stateName(descState(o.path))
          if not de then
            ImGui.TextColored(1.0, 0.4, 0.4, 1.0, "        desc NO ENTRY")
          elseif ds == "ACTIVE" then
            ImGui.TextColored(0.4, 1.0, 0.4, 1.0, "        desc ACTIVE")
          else
            ImGui.TextColored(1.0, 0.8, 0.3, 1.0, string.format("        desc %-9s", ds))
            ImGui.SameLine()
            -- Not a fix, a discriminator. If forcing this makes the paragraph
            -- appear in the real journal screen, the resource, the localization
            -- and the UI are all proven and the only thing that failed was the
            -- graph reaching the node on THIS save. If it stays blank with the
            -- state reading ACTIVE, the fault is downstream of the state and
            -- D48 is wrong. ChangeEntryState is the same call the game's own
            -- PopulateCodexLinks makes on codex links every time it draws.
            if ImGui.Button("force##d" .. o.id) then
              local jm = Game.GetJournalManager()
              jm:ChangeEntryState(o.path .. "/description",
                                  "gameJournalQuestDescription",
                                  gameJournalEntryState.Active,
                                  JournalNotifyOption.DoNotNotify)
              entryCache[o.path .. "/description"] = nil
              note("act", o.id .. "/description forced Active")
            end
          end
        end
      end
      ImGui.Separator()
      ImGui.TextDisabled("messages")
      for _, m in ipairs(MESSAGES) do
        local e = entry(m.path, m.class)
        if e then
          ImGui.Text(string.format("    ok       %s", m.id))
        else
          ImGui.TextColored(1.0, 0.4, 0.4, 1.0, string.format("    NO ENTRY  %s", m.id))
        end
      end
      ImGui.EndTabItem()
    end

    if ImGui.BeginTabItem("Items") then
      ImGui.TextWrapped("Granted by graph nodes, not by redscript (D12). A count of "
        .. "0 after the beat that grants it means the add_item node did not run; a "
        .. "count of -1 means there is no player yet.")
      ImGui.Separator()
      for _, it in ipairs(ITEMS) do
        local n = itemCount(it.id)
        if n > 0 then
          ImGui.TextColored(0.4, 1.0, 0.4, 1.0, string.format("%3d  %s", n, it.label))
        else
          ImGui.Text(string.format("%3d  %s", n, it.label))
        end
        ImGui.SameLine()
        ImGui.TextDisabled(it.id)
      end
      ImGui.EndTabItem()
    end

    if ImGui.BeginTabItem("Voice") then
      ImGui.TextWrapped("Plays a line through the SAME call a scnAudioEvent makes: "
        .. "Game.GetAudioSystem():Play(name). No quest state, no scene, no save - "
        .. "if a button here speaks, the recording, the Audioware bank and the name "
        .. "are all good, and anything still silent in the conversation is the scene "
        .. "event. If nothing here speaks, check that Audioware is installed and that "
        .. "r6/audioware/ash_cache/ was deployed.")
      ImGui.Separator()
      if ImGui.Button("stop everything") then
        for _, v in ipairs(VOLINES) do Game.GetAudioSystem():Stop(v.event) end
        voSaid = "stopped"
      end
      ImGui.SameLine()
      ImGui.TextDisabled(voSaid)
      ImGui.Separator()
      for _, v in ipairs(VOLINES) do
        if ImGui.Button("play##vo" .. v.key) then
          Game.GetAudioSystem():Stop(v.event)
          Game.GetAudioSystem():Play(v.event)
          voSaid = v.event
        end
        ImGui.SameLine()
        ImGui.Text(v.key)
      end
      ImGui.EndTabItem()
    end

    if ImGui.BeginTabItem("Trace") then
      ImGui.TextWrapped("Every fact change since the panel loaded, newest first, "
        .. "polled 4x a second. This is the answer to 'I walked in and nothing "
        .. "happened' - either the fact flipped and the graph ignored it, or it "
        .. "never flipped and the trigger is what to look at.")
      ImGui.SameLine()
      if ImGui.SmallButton("clear") then trace = {} end
      ImGui.Separator()
      for _, t in ipairs(trace) do
        ImGui.TextDisabled(t.t)
        ImGui.SameLine()
        if t.kind == "fact" then
          ImGui.Text(t.text)
        elseif t.kind == "obj" then
          ImGui.TextColored(0.6, 0.8, 1.0, 1.0, t.text)
        else
          ImGui.TextColored(1.0, 0.9, 0.5, 1.0, t.text)
        end
      end
      ImGui.EndTabItem()
    end

    if ImGui.BeginTabItem("Acts") then
      ImGui.TextWrapped("Sets ashcache_progress and every gate behind it. "
        .. "The graph is edge-driven, so jumping forward past a beat leaves "
        .. "its journal objective unticked - the state is right, the log is not.")
      ImGui.TextWrapped("Writes are queued and applied one per frame on the "
        .. "game thread, so a jump takes a fraction of a second to finish. "
        .. "The buttons are disabled while that is happening.")
      ImGui.Separator()
      ImGui.Text(string.format("progress = %d", fact("ashcache_progress")))
      local pending = #factQueue
      if pending > 0 then
        ImGui.TextColored(1.0, 0.8, 0.3, 1.0,
          string.format("applying... %d write(s) left", pending))
      else
        ImGui.TextColored(0.5, 0.9, 0.5, 1.0, "idle")
      end
      stepMode = ImGui.Checkbox("step - apply one write per press", stepMode)
      if stepMode then
        ImGui.SameLine()
        if pending > 0 then
          if ImGui.Button("apply next") then stepOnce = true end
        else
          ImGui.TextDisabled("(nothing queued)")
        end
      end
      ImGui.Separator()
      for _, a in ipairs(ACTS) do
        if pending > 0 then
          ImGui.TextDisabled(a.label)
        elseif ImGui.Button(a.label) then
          for _, prev in ipairs(ACTS) do
            if prev.value <= a.value then
              for _, g in ipairs(prev.gates) do setFact(g, 1) end
            end
          end
          setFact("ashcache_progress", a.value - 1)
          note("act", string.format("queued %s (%d write(s))", a.label, #factQueue))
        end
      end
      ImGui.Separator()
      if pending > 0 then
        ImGui.TextDisabled("reset the whole quest")
      elseif ImGui.Button("reset the whole quest") then
        for _, g in ipairs(GROUPS) do
          for _, f in ipairs(g.facts) do setFact(f, 0) end
        end
        note("act", string.format("queued full reset (%d write(s))", #factQueue))
      end
      ImGui.EndTabItem()
    end

    -------------------------------------------------------------------- Devices
    -- WHY THIS EXISTS
    -- ac_terminal_pc is, field for field, a copy of the vanilla computer on node
    -- 12 of quest_73110a178d6e7404: same computer_1.ent, same appearance, same
    -- ComputerControllerPS with isInteractive = 1, deviceState = ON and
    -- tweakDBRecord Devices.Computer. It is authored correctly and it still does
    -- nothing in game, which means the fault is in what the runtime makes of the
    -- node - and no amount of diffing JSON can see that. This tab asks the
    -- running game instead. Three answers, three different fixes:
    --
    --   nothing there          the entity never spawns. The sector, the .ent
    --                          path or the position is the problem, not the
    --                          device data.
    --   there, not a Device    the .ent loaded but the device components did
    --                          not attach - instanceData is being dropped.
    --   there, IS a Device     it exists and is inert: power, registration or
    --                          persistency. Read the state line for which.
    if ImGui.BeginTabItem("Devices") then
      local p = Game.GetPlayer()
      ImGui.TextWrapped("Walk up to the terminal, put the crosshair on it, and "
        .. "press probe. This asks the game what it actually built from our "
        .. "node. It changes no state and needs no save.")
      ImGui.Separator()
      if p then
        local pos = p:GetWorldPosition()
        for _, m in ipairs(MARKERS) do
          if m.dev then
            local dx, dy, dz = pos.x - m.x, pos.y - m.y, pos.z - m.z
            local away = math.sqrt(dx * dx + dy * dy + dz * dz)
            if ImGui.Button("go##dev" .. m.id) then
              Game.GetTeleportationFacility():Teleport(
                p, Vector4.new(m.x, m.y, m.z, 0), EulerAngles.new(0, 0, m.yaw))
            end
            ImGui.SameLine()
            ImGui.Text(string.format("%-18s %-9s %.1fm away", m.id, m.dev, away))
          end
        end
      end
      ImGui.Separator()
      if ImGui.Button("probe what I am looking at") then
        deviceProbe = probeLookAt()
      end
      ImGui.SameLine()
      if ImGui.SmallButton("clear##dev") then deviceProbe = nil end
      ImGui.Separator()
      if deviceProbe then
        for _, line in ipairs(deviceProbe) do
          if line:sub(1, 1) == "!" then
            ImGui.TextColored(1.0, 0.5, 0.5, 1.0, line:sub(2))
          else
            ImGui.TextWrapped(line)
          end
        end
      else
        ImGui.TextDisabled("no probe yet")
      end
      ImGui.EndTabItem()
    end

    if ImGui.BeginTabItem("Surveyor") then
      local p = Game.GetPlayer()
      if p then
        local pos = p:GetWorldPosition()
        local rot = p:GetWorldOrientation():ToEulerAngles()
        ImGui.TextWrapped("Stand where the marker belongs, face the way it "
          .. "should face, and paste this into source/world.json (OI-9). "
          .. "Do the clinic first - #ac_mara is the scene origin and its yaw "
          .. "is the direction the conversation faces.")
        ImGui.Separator()
        ImGui.TextWrapped("The ac_probe_* nodes are the OTHER question "
          .. "(D15), and they answer it just by being looked at. Teleport "
          .. "to each and report back what is or is not standing there.")
        ImGui.Bullet()
        ImGui.TextWrapped("ac_probe_computer - a vanilla computer .ent with a "
          .. "null instanceData. There AND usable -> box_opened, terminal_read and "
          .. "cabinet_opened are a line of JSON each. There but inert -> devices need "
          .. "the instance buffer, which is transcription. Not there -> they need a "
          .. "mod-authored .ent.")
        ImGui.Bullet()
        ImGui.TextWrapped("ac_probe_car - the control. A Vehicle record is "
          .. "the only kind vanilla ever puts in a spawner. If the car is missing, "
          .. "ignore the NPC result entirely: the spot or the node is what failed.")
        ImGui.Bullet()
        ImGui.TextWrapped("ac_probe_npc - an FIA agent from a Character "
          .. "record. No vanilla quest sector has ever done this. Car there AND agent "
          .. "there -> cleanup_done is authorable today. Car there, agent NOT -> the "
          .. "FIA crew needs a .community, which nothing here has a sample of.")
        ImGui.Separator()
        local block = string.format(
          "\"pos\": [%.2f, %.2f, %.2f],\n\"yaw\": %.1f,\n\"_source\": \"verified - stood on\"",
          pos.x, pos.y, pos.z, rot.yaw)
        ImGui.InputTextMultiline("##ac_pos", block, 4096, 500, 76)
        if ImGui.Button("copy this block") then ImGui.SetClipboardText(block) end
        ImGui.Separator()
        ImGui.TextWrapped("go: teleport to where the marker currently thinks it is. "
          .. "set: overwrite it with where you are standing right now. Then write "
          .. "markers.txt and send that one file back - it is the whole of OI-9, "
          .. "with no JSON to edit by hand and nothing to transcribe wrongly.")
        for _, m in ipairs(MARKERS) do
          if ImGui.Button("go##" .. m.id) then
            Game.GetTeleportationFacility():Teleport(
              p, Vector4.new(m.x, m.y, m.z, 0), EulerAngles.new(0, 0, m.yaw))
          end
          ImGui.SameLine()
          if ImGui.Button("set##" .. m.id) then
            captured[m.id] = { x = pos.x, y = pos.y, z = pos.z, yaw = rot.yaw }
            captureStatus = ""
          end
          ImGui.SameLine()
          local c = captured[m.id]
          local dx, dy, dz = pos.x - m.x, pos.y - m.y, pos.z - m.z
          local away = math.sqrt(dx * dx + dy * dy + dz * dz)
          if c then
            local mx, my, mz = c.x - m.x, c.y - m.y, c.z - m.z
            ImGui.Text(string.format("%-22s CAPTURED, moved %.1fm", m.id,
                                     math.sqrt(mx * mx + my * my + mz * mz)))
          else
            ImGui.Text(string.format("%-22s %s  %.1fm away", m.id, m.kind, away))
          end
        end
        ImGui.Separator()
        -- Written as the exact JSON the marker entry in source/world.json needs, so
        -- the fix is a paste and not a retyping. A marker that was never captured is
        -- left out entirely rather than written at its current value: a coordinate
        -- nobody stood on must not come back looking verified.
        if ImGui.Button("write markers.txt") then
          local n, body = 0, {}
          body[#body + 1] = "captured " .. os.date("%Y-%m-%d %H:%M:%S")
          body[#body + 1] = "build " .. BUILD_STAMP .. "  source " .. BUILD_SRC
          body[#body + 1] = ""
          for _, m in ipairs(MARKERS) do
            local c = captured[m.id]
            if c then
              n = n + 1
              body[#body + 1] = string.format(
                "%s\n  \"pos\": [%.2f, %.2f, %.2f],\n  \"yaw\": %.1f,\n"
                .. "  \"_source\": \"verified - stood on %s\"\n",
                m.id, c.x, c.y, c.z, c.yaw, os.date("%Y-%m-%d"))
            end
          end
          if n == 0 then
            captureStatus = "nothing captured yet - stand somewhere and press set"
          else
            local f = io.open("markers.txt", "w")
            if f then
              f:write(table.concat(body, "\n"))
              f:close()
              captureStatus = n .. " marker(s) written to mods/ash_cache_debug/markers.txt"
            else
              ImGui.SetClipboardText(table.concat(body, "\n"))
              captureStatus = "could not open markers.txt - " .. n .. " copied to the clipboard"
            end
          end
        end
        ImGui.SameLine()
        if ImGui.Button("forget captures") then captured = {}; captureStatus = "" end
        if captureStatus ~= "" then ImGui.TextWrapped(captureStatus) end
      else
        ImGui.Text("no player yet")
      end
      ImGui.EndTabItem()
    end

    ImGui.EndTabBar()
  end
  ImGui.End()
end)
'''


def main():
    src = ROOT / "source"
    facts = json.loads((src / "facts.json").read_text(encoding="utf-8"))
    world = json.loads((src / "world.json").read_text(encoding="utf-8"))
    glue = json.loads((src / "glue.json").read_text(encoding="utf-8"))
    journal = json.loads((src / "journal.json").read_text(encoding="utf-8"))
    items = json.loads((src / "items.json").read_text(encoding="utf-8"))
    chars = json.loads((src / "characters.json").read_text(encoding="utf-8"))
    lockeys = json.loads((src / "lockeys.json").read_text(encoding="utf-8"))

    blocked = {k for k in glue["blocked"] if not k.startswith("_")}
    by_glue = {glue["start"]["fact"]}
    by_glue |= {a["fact"] for a in glue["areas"]}
    by_glue |= {s["fact"] for s in glue["shards"]}

    # A fact set by a scnQuestNode inside a .scene reaches the save the same way a
    # graph node's does, but a tester cannot reach it the same way: it needs the
    # conversation played and the right option picked. Worth saying so on the panel,
    # or every ending fact sitting at 0 looks like the graph is broken.
    by_scene = set()
    for path in sorted(src.glob("scene_*.json")):
        scene = json.loads(path.read_text(encoding="utf-8"))
        for node in scene["nodes"]:
            if node.get("type") == "quest" and "fact" in node.get("node", {}):
                by_scene.add(node["node"]["fact"])

    quest_id = journal["quest"]["id"]
    D = []

    D.append("-- GENERATED by tools/gen_cet.py from source/. Do not hand-edit.")
    D.append("--")
    D.append("-- DEV ONLY. Not part of the mod. Copy this folder to")
    D.append("--   bin/x64/plugins/cyber_engine_tweaks/mods/ash_cache_debug/")
    D.append("-- and open it from CET's overlay.")
    D.append("")
    D.append(f"local BUILD_STAMP = {lua_str(time.strftime('%Y-%m-%d %H:%M'))}")
    D.append(f"local BUILD_SRC   = {lua_str(source_stamp(src))}")
    # The depot name the phase ships under. It is not decoration: ArchiveXL turns
    # this path into the phase node id, and a save remembers "this phase already
    # started" against that id. Reading it back in game is the only way to tell a
    # stale archive from a fresh one without unpacking anything (D21).
    D.append(f"local PHASE_RES   = {lua_str(gen_xl.phase_resource_name(gen_xl.phase_revision()))}")
    D.append(f"local QUEST_ROOT  = {lua_str(QUEST_ROOT)}")
    D.append(f"local QUEST_ID    = {lua_str(quest_id)}")
    D.append(f"local GLUE_SYSTEM = {lua_str(GLUE_SYSTEM)}")
    D.append("")

    D.append("-- What sets each fact for real, so the panel says whether a value being 0")
    D.append("-- is a bug or just a beat that has not been authored yet (OI-13).")
    D.append("local ORIGIN = {}")
    for f in sorted(by_glue):
        D.append(f"ORIGIN[{lua_str(f)}] = \"glue\"")
    for f in sorted(by_scene - by_glue):
        D.append(f"ORIGIN[{lua_str(f)}] = \"scene\"")
    for f in sorted(blocked):
        D.append(f"ORIGIN[{lua_str(f)}] = \"BLOCKED\"")

    D += ["", "local GROUPS = {"]
    for group, names in fact_groups(facts):
        inner = ", ".join(lua_str(n) for n in names)
        D.append(f"  {{ name = {lua_str(group)}, facts = {{ {inner} }} }},")

    D += ["}", "", "local ACTS = {"]
    for value, label, gates in ACTS:
        inner = ", ".join(lua_str(g) for g in gates)
        D.append(f"  {{ value = {value}, label = {lua_str(label)}, gates = {{ {inner} }} }},")

    D += ["}", "",
          "-- Every objective the journal declares, in book order, so the panel can",
          "-- distinguish 'the archive never delivered it' from 'the graph has not",
          "-- activated it'. Those look identical in game and are different bugs.",
          "-- hasDesc marks the ones that also carry a description paragraph, which",
          "-- is a third entry with a third state and its own way of going missing.",
          "local OBJECTIVES = {"]
    n_obj = 0
    for ph in journal["phases"]:
        for o in ph["objectives"]:
            path = f"{QUEST_ROOT}/{quest_id}/{ph['id']}/{o['id']}"
            opt = "true" if o.get("optional") else "false"
            # hasDesc is 'this objective declares a summary', i.e. gen_journal.py
            # emitted a gameJournalQuestDescription child under it. Only those
            # are worth probing; asking for a description that was never authored
            # would report NO ENTRY and read as a broken archive.
            has_desc = "true" if o.get("summary") else "false"
            D.append(f"  {{ id = {lua_str(o['id'])}, phase = {lua_str(ph['id'])}, "
                     f"path = {lua_str(path)}, optional = {opt}, "
                     f"hasDesc = {has_desc} }},")
            n_obj += 1

    D += ["}", "", "local MESSAGES = {"]
    n_msg = 0
    for conv in journal.get("phoneConversations", []):
        contact = conv.get("contact", "contacts")
        root = f"{contact}/{conv['id']}"
        D.append(f"  {{ id = {lua_str(conv['id'])}, path = {lua_str(root)}, "
                 f"class = \"gameJournalPhoneConversation\" }},")
        n_msg += 1
        for m in conv["messages"]:
            D.append(f"  {{ id = {lua_str(conv['id'] + '/' + m['id'])}, "
                     f"path = {lua_str(root + '/' + m['id'])}, "
                     f"class = \"gameJournalPhoneMessage\" }},")
            n_msg += 1

    D += ["}", "",
          "-- TweakXL records. These come from r6/tweaks/, a LOOSE file that does not",
          "-- travel with the archive - which is why they get their own layer row.",
          "local RECORDS = {"]
    records = [f"Character.{c['record']}" for c in chars["characters"]]
    records += [f"Items.{it['record']}" for it in items["items"]]
    for r in records:
        D.append(f"  {lua_str(r)},")

    D += ["}", "", "local ITEMS = {"]
    for it in items["items"]:
        D.append(f"  {{ id = {lua_str('Items.' + it['record'])}, "
                 f"label = {lua_str(it['id'])} }},")

    D += ["}", "", "local ONSCREENS = {"]
    n_os = 0
    for it in items["items"]:
        os_ = it.get("onscreen")
        if os_:
            path = f"onscreens/{os_['group']}/{os_['entry']}"
            D.append(f"  {{ label = {lua_str(os_['entry'])}, path = {lua_str(path)} }},")
            n_os += 1

    D += ["}", "",
          "-- Codex links and phone contacts: the two things that give the journal its",
          "-- vanilla FURNITURE - the location cards and character portraits beside the",
          "-- text, and the avatar the SMS arrives under. Both fail the same silent way:",
          "-- a codex path that resolves to nothing simply does not draw, and a contact",
          "-- that is not there gets the blank silhouette. Neither logs anything. One",
          "-- reference mod ships 'odex/glossary/world/militech' - a missing leading c -",
          "-- and has presumably never once rendered it.",
          "local CODEX = {"]
    n_codex = 0
    for c in journal.get("codexLinks", []):
        D.append(f"  {{ label = {lua_str(c['id'])}, path = {lua_str(c['path'])} }},")
        n_codex += 1

    D += ["}", "", "local CONTACTS = {"]
    n_contact = 0
    for conv in journal.get("phoneConversations", []):
        c = conv["contact"]
        D.append(f"  {{ label = {lua_str(c['id'])}, "
                 f"path = {lua_str('contacts/' + c['id'])}, "
                 f"avatar = {lua_str(c.get('avatar', ''))} }},")
        n_contact += 1

    D += ["}", "",
          "-- Every reserved LocKey. Checked individually rather than by sampling,",
          "-- because a half-mounted localization tree renders SOME lines and the",
          "-- one it drops is the one nobody thinks to look at.",
          "local LOCKEYS = {"]
    n_lk = 0
    for label, key in lockeys.items():
        if label.startswith("_"):
            continue
        D.append(f"  {{ label = {lua_str(label)}, key = {key} }},")
        n_lk += 1

    D += ["}", "",
          "-- Every recording, and the CName a scnAudioEvent names to play it. This",
          "-- tab exists to split one question in two. The scene路 is: .scene ->",
          "-- scnAudioEvent -> vanilla AudioSystem::Play -> Audioware -> the .wav.",
          "-- Pressing a button here enters that chain at the third link, from",
          "-- anywhere, with no quest state involved. Silent here = Audioware, the",
          "-- bank, or a name that does not match. Speaks here but not in the scene",
          "-- = the scene event is the link that does not arrive. D67.",
          "local VOLINES = {"]
    import gen_audioware
    n_vo = 0
    for key, srcf in sorted(gen_audioware.sources().items()):
        D.append(f"  {{ key = {lua_str(key)}, "
                 f"event = {lua_str(gen_audioware.event_name(key))} }},")
        n_vo += 1

    D += ["}", "", "local MARKERS = {"]
    # Every placed node, not just markers. A prop or a trigger you cannot teleport
    # to is a prop you cannot check, and checking them is the entire point of the
    # probe sector (D15).
    n_mark = 0
    for sec in world["sectors"]:
        for kind, key in (("marker", "markers"), ("trigger", "triggers"),
                          ("spawner", "spawners"), ("prop", "props")):
            for m in sec.get(key, []):
                x, y, z = m["pos"]
                origin = m.get("_source", "").split(" - ")[0] or kind
                # `dev` is the .ent's device flavour, or nil for a plain prop.
                # The Devices tab needs to know which placed nodes are SUPPOSED
                # to be interactive before it can report that they are not.
                dev = (f", dev = {lua_str(m['device'])}"
                       if kind == "prop" and m.get("device") else "")
                D.append(f"  {{ id = {lua_str(m['id'])}, x = {x}, y = {y}, z = {z}, "
                         f"yaw = {m.get('yaw', 0.0)}, kind = {lua_str(kind)}, "
                         f"src = {lua_str(origin)}{dev} }},")
                n_mark += 1
    D += ["}"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(D) + "\n" + PANEL, encoding="utf-8")

    n_facts = sum(len(f) for _, f in fact_groups(facts))
    print(f"cet: {n_facts} fact(s) in {len(fact_groups(facts))} group(s), "
          f"{n_obj} objective(s), {n_msg} message(s), {len(records)} record(s), "
          f"{n_os} onscreen(s), {n_lk} lockey(s), {n_mark} placed node(s), "
          f"{len(ACTS)} act jump(s) -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
