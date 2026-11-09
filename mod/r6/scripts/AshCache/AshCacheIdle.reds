module AshCache

// D171: Mara idles in a vanilla workspot instead of standing in a bind pose.
//
// The scene spawns her and drives only her face, so nothing moved her body. A scene
// questUseWorkspot node was tried first and crashed the game on a loader thread
// (crash_20260926_002515). This does it the way AMM's Poses tab does, which held on
// the real, scene-spawned Mara in game while her meeting ran: spawn a small device
// entity on her and play its workspot with WorkspotSystem.PlayInDeviceSimple.
//
// The device (mod\ash_cache\workspots\mara_idle.ent, tools/gen_workspot_ent.py) is AMM's
// ArcadeMachine device cut down to one workWorkspotResourceComponent, ashcache_idle, pointing at
// base\workspots\common\ground\generic__stand_ground_arms_crossed__stand_around__02.workspot.
// That component is turned 180 degrees (copied from AMM's), so the device is spawned
// at her yaw + 180, as AMM does.
//
// Glue only: it reads the world and never writes a fact. A tick once a second (0.2 s while
// she is waiting for the workspot) looks for Mara within 30 m of V; with nobody there it
// does nothing but clean up.

public class AshCacheIdleCallback extends DelayCallback {
  public let sys: wref<AshCacheIdle>;

  public func Call() -> Void {
    if IsDefined(this.sys) {
      this.sys.OnIdleTick();
    }
  }
}

public class AshCacheIdle extends ScriptableSystem {
  private let m_scheduled: Bool;
  private let m_npc: EntityID;
  private let m_played: Bool;
  private let m_ticks: Int32;
  private let m_status: String;
  // Slow ticks (1 s) the same Mara has been in range; nothing touches her before 3.
  private let m_seen: Int32;
  private let m_seenNpc: EntityID;
  // Set by Update when Mara is here but not yet idling: poll fast so the gap before the
  // workspot takes her is a fraction of a second, not the 2-3 s of 1 s ticks.
  private let m_fast: Bool;
  // Whether a scene held her last tick; the tick a scene lets her go restarts the settle.
  private let m_wasInScene: Bool;
  // The hold last sent, kept so D179 can cancel it before the aftertalk.
  private let m_hold: ref<AIHoldPositionCommand>;
  private let m_holdNpc: EntityID;

  // Read from CET: Game.GetScriptableSystemsContainer():Get("AshCache.AshCacheIdle"):Status()
  public func Status() -> String {
    return "ticks=" + IntToString(this.m_ticks) + " played=" + ToString(this.m_played) + " " + this.m_status;
  }

  public func OnAttach() -> Void {
    this.Schedule(3.0);
  }

  public func OnRestored(saveVersion: Int32, gameVersion: Int32) -> Void {
    this.Schedule(3.0);
  }

  // A callback queued before a save loads can be dropped with the old session, which would
  // leave m_scheduled stuck; re-arm whenever V attaches.
  private func OnPlayerAttach(request: ref<PlayerAttachRequest>) -> Void {
    this.m_scheduled = false;
    this.Schedule(3.0);
  }

  private func Schedule(delay: Float) -> Void {
    if this.m_scheduled {
      return;
    }
    this.m_scheduled = true;
    let cb = new AshCacheIdleCallback();
    cb.sys = this;
    GameInstance.GetDelaySystem(this.GetGameInstance()).DelayCallback(cb, delay, false);
  }

  public func OnIdleTick() -> Void {
    this.m_scheduled = false;
    this.m_ticks += 1;
    this.m_fast = false;
    this.Update();
    this.Schedule(this.m_fast ? 0.2 : 1.0);
  }

  // D180: by entity ID, not FindMara. The targeting query FindMara uses returns nothing while V
  // is in a scene (TSQ_ALL at 50 m: 0 parts, live 15:20) and nothing through the clinic's
  // walls, so D179's release, which waited for FindMara, never ran and the aftertalk found her
  // still locked. Deleting the device alone leaves her in its workspot (live test: ws=true).
  private func Release() -> Void {
    let gi = this.GetGameInstance();
    // m_npc, not m_played: the "no mara" branch clears m_played whenever targeting loses her,
    // and she stays in the workspot all the same.
    if EntityID.IsDefined(this.m_npc) {
      let mara = GameInstance.FindEntityByID(gi, this.m_npc) as GameObject;
      if IsDefined(mara) {
        let ws = GameInstance.GetWorkspotSystem(gi);
        if ws.IsActorInWorkspot(mara) {
          ws.StopNpcInWorkspot(mara);
          this.Log("released from workspot");
        }
        let none: EntityID;
        this.m_npc = none;
      }
    }
    if IsDefined(this.m_hold) {
      let held = GameInstance.FindEntityByID(gi, this.m_holdNpc) as ScriptedPuppet;
      if IsDefined(held) {
        AIComponent.CancelCommand(held, this.m_hold);
        this.m_hold = null;
        this.Log("hold cancelled");
      }
    }
    if !EntityID.IsDefined(this.m_npc) {
      AshCacheIdleDespawn();
      this.m_played = false;
    }
  }

  // Status for CET, and a line in the log whenever it changes, to time the idle against the scene.
  private func Log(status: String) -> Void {
    if NotEquals(status, this.m_status) {
      FTLog("ashcache idle t=" + IntToString(this.m_ticks) + ": " + status);
    }
    this.m_status = status;
  }

  private func FindMara(player: ref<GameObject>) -> ref<GameObject> {
    let parts: array<TS_TargetPartInfo>;
    let query = TSQ_NPC();
    query.maxDistance = 30.0;
    GameInstance.GetTargetingSystem(this.GetGameInstance()).GetTargetParts(player, query, parts);
    let i = 0;
    while i < ArraySize(parts) {
      let npc = TS_TargetPartInfo.GetComponent(parts[i]).GetEntity() as NPCPuppet;
      if IsDefined(npc) && npc.GetRecordID() == t"Character.ashcache_mara" {
        return npc;
      }
      i += 1;
    }
    return null;
  }

  private func Update() -> Void {
    let gi = this.GetGameInstance();
    let player = GetPlayer(gi);
    if !IsDefined(player) || !AshCacheIdleReady() {
      this.Log("not ready");
      return;
    }
    // D179/D180: from the terminal (progress 5) until the aftertalk has run, Mara belongs to
    // the aftertalk. Still locked in the idle workspot under a 99999 s hold when it opens, she
    // cannot be cast: it plays its opening lines and stalls at its hub. Checked before FindMara,
    // which is blind in a scene and through walls; Release finds her by ID.
    if GetFact(gi, n"ashcache_progress") >= 5 && GetFact(gi, n"ashcache_mara_warned") == 0 {
      this.Release();
      this.Log("mara released for aftertalk");
      return;
    }
    let mara = this.FindMara(player);
    if !IsDefined(mara) {
      if this.m_played || AshCacheIdleDeviceUp() {
        AshCacheIdleDespawn();
        this.m_played = false;
      }
      this.m_seen = 0;
      this.Log("no mara");
      return;
    }
    // Leave a Mara the scene has just spawned alone for 3 s. Taking the splinter starts
    // talk_mara, which spawns her beside V, and the hold/device/PlayInDeviceSimple fired
    // within a second of her appearing crashed twice on a worker thread (null +0xF8,
    // crash_20260926_123320 and _132623; the 13:26 gamelog breaks off mid "ashcache idle").
    if mara.GetEntityID() != this.m_seenNpc {
      this.m_seenNpc = mara.GetEntityID();
      this.m_seen = 0;
    }
    // D178: the same wait after a scene releases her. With the hold and workspot sent within a
    // second of talk_mara ending the game crashed on a worker thread (null +0xF8,
    // crash_20260926_141749, 1.3 s after ashcache_mara_choice_made).
    let inScene = GameInstance.GetSceneSystem(gi).GetScriptInterface().IsEntityInScene(mara.GetEntityID());
    if this.m_wasInScene && !inScene {
      this.m_seen = 0;
    }
    this.m_wasInScene = inScene;
    if this.m_seen < 3 {
      this.m_seen += 1;
      this.Log("mara settling");
      return;
    }
    // A new Mara (the scene respawned her) needs a new device under her.
    if this.m_played && mara.GetEntityID() != this.m_npc {
      AshCacheIdleDespawn();
      this.m_played = false;
    }
    // Her base record (a q306 airport traveller) has an AI that walks off as soon as nothing
    // commands it, and PlayInDeviceSimple bypasses the AI, so in the workspot she kept trying
    // to leave on the spot. A long hold gives her AI a command to sit on; AMM does the same to
    // its posed NPCs (Util:HoldPosition, 99999 s). The scene drops AI commands when it releases
    // her, so a hold sent during the dialog was gone after it: re-send whenever it is not active.
    let ai = (mara as ScriptedPuppet).GetAIControllerComponent();
    if IsDefined(ai) && !ai.IsCommandActive(n"AIHoldPositionCommand") {
      let hold = new AIHoldPositionCommand();
      hold.duration = 99999.0;
      hold.ignoreInCombat = false;
      hold.removeAfterCombat = false;
      AIComponent.SendCommand(mara as ScriptedPuppet, hold);
      this.m_hold = hold;
      this.m_holdNpc = mara.GetEntityID();
      this.Log("hold sent");
    }
    // Not "is she in any workspot": while the scene plays her lines it drives her through the
    // workspot system too, so that read true for the whole dialog and the arms-crossed idle only
    // started once the scene let her go. Play once per Mara straight away (a manual play mid-
    // dialog held), and again only if she has since dropped out of every workspot.
    let ws = GameInstance.GetWorkspotSystem(gi);
    if this.m_played && mara.GetEntityID() == this.m_npc {
      if ws.IsActorInWorkspot(mara) {
        this.Log("mara in workspot");
        return;
      }
      this.m_played = false;
    }
    this.m_fast = true;
    if !AshCacheIdleDeviceUp() {
      let pos = mara.GetWorldPosition();
      AshCacheIdleSpawn(pos, mara.GetWorldYaw() + 180.0);
      this.Log("device spawn requested");
      return;
    }
    let device = AshCacheIdleDevice(gi);
    if !IsDefined(device) {
      this.Log("device populated but not resolved");
      return;
    }
    // AMM's argument set, proven live on Mara: the component is the ACTOR data name, the device
    // data name matches nothing, and DontPlayAtResourcePosition plays her where the scene stands
    // her. With the default (PlayAtResourcePosition) and the component as device data the call
    // was accepted every tick and she never entered the workspot.
    ws.PlayInDeviceSimple(device, mara, false, n"ashcache_idle", n"AMM_WORKSPOT", n"None", 0.0,
      WorkspotSlidingBehaviour.DontPlayAtResourcePosition);
    this.m_npc = mara.GetEntityID();
    this.m_played = true;
    this.Log("PlayInDeviceSimple called");
  }
}

@if(ModuleExists("Codeware"))
public func AshCacheIdleReady() -> Bool {
  let des = GameInstance.GetDynamicEntitySystem();
  return IsDefined(des) && des.IsReady();
}

@if(!ModuleExists("Codeware"))
public func AshCacheIdleReady() -> Bool {
  return false;
}

@if(ModuleExists("Codeware"))
public func AshCacheIdleDeviceUp() -> Bool {
  return GameInstance.GetDynamicEntitySystem().IsPopulated(n"ashcache_idle_device");
}

@if(!ModuleExists("Codeware"))
public func AshCacheIdleDeviceUp() -> Bool {
  return false;
}

@if(ModuleExists("Codeware"))
public func AshCacheIdleDevice(gi: GameInstance) -> ref<GameObject> {
  let ents = GameInstance.GetDynamicEntitySystem().GetTagged(n"ashcache_idle_device");
  if ArraySize(ents) == 0 {
    return null;
  }
  return ents[0] as GameObject;
}

@if(!ModuleExists("Codeware"))
public func AshCacheIdleDevice(gi: GameInstance) -> ref<GameObject> {
  return null;
}

@if(ModuleExists("Codeware"))
public func AshCacheIdleSpawn(pos: Vector4, yaw: Float) -> Void {
  let spec = new DynamicEntitySpec();
  spec.templatePath = r"mod\\ash_cache\\workspots\\mara_idle.ent";
  spec.position = pos;
  let rot: EulerAngles;
  rot.Yaw = yaw;
  spec.orientation = EulerAngles.ToQuat(rot);
  spec.persistState = false;
  spec.persistSpawn = false;
  spec.alwaysSpawned = false;
  spec.spawnInView = true;
  spec.active = true;
  ArrayPush(spec.tags, n"ashcache_idle_device");
  if !EntityID.IsDefined(GameInstance.GetDynamicEntitySystem().CreateEntity(spec)) {
    FTLogWarning("ashcache: idle device did not spawn");
  }
}

@if(!ModuleExists("Codeware"))
public func AshCacheIdleSpawn(pos: Vector4, yaw: Float) -> Void {}

@if(ModuleExists("Codeware"))
public func AshCacheIdleDespawn() -> Void {
  let des = GameInstance.GetDynamicEntitySystem();
  if IsDefined(des) && des.IsReady() && des.IsPopulated(n"ashcache_idle_device") {
    des.DeleteTagged(n"ashcache_idle_device");
  }
}

@if(!ModuleExists("Codeware"))
public func AshCacheIdleDespawn() -> Void {}
