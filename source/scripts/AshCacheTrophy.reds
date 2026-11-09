module AshCache

// D186: the Liberty beside Mara's body is a trophy V can pick up - the Last Word
// (Items.ashcache_mara_trophy, source/items.json).
//
// The glue's ac_body_gun prop is int_weapons_002__*, a mesh with no item behind it, so it
// can never be picked up. This drops the real item as a vanilla loot drop instead, which
// brings the game's own pickup prompt, loot icon and inventory handling. LootManager.
// SpawnItemDrop MOVES an item out of the owner's inventory (checked live 2026-09-26: a
// drop of an item V did not hold returned true and spawned nothing), so the item is given
// to V first and dropped from V in the same tick.
//
// Same routes as the prop: body placed and ashcache_mara_liberty_given. The drop waits until
// V is within 25 m, so it is made where the world is streamed in, and sets
// ashcache_mara_trophy_dropped, which is also what makes the glue remove the prop.

public class AshCacheTrophyCallback extends DelayCallback {
  public let sys: wref<AshCacheTrophy>;

  public func Call() -> Void {
    if IsDefined(this.sys) {
      this.sys.OnTrophyTick();
    }
  }
}

public class AshCacheTrophy extends ScriptableSystem {
  private let m_scheduled: Bool;
  private let m_status: String;

  // Read from CET: Game.GetScriptableSystemsContainer():Get("AshCache.AshCacheTrophy"):Status()
  public func Status() -> String {
    return this.m_status;
  }

  public func OnAttach() -> Void {
    this.Schedule(5.0);
  }

  public func OnRestored(saveVersion: Int32, gameVersion: Int32) -> Void {
    this.Schedule(5.0);
  }

  private func OnPlayerAttach(request: ref<PlayerAttachRequest>) -> Void {
    this.m_scheduled = false;
    this.Schedule(5.0);
  }

  private func Schedule(delay: Float) -> Void {
    if this.m_scheduled {
      return;
    }
    this.m_scheduled = true;
    let cb = new AshCacheTrophyCallback();
    cb.sys = this;
    GameInstance.GetDelaySystem(this.GetGameInstance()).DelayCallback(cb, delay, false);
  }

  public func OnTrophyTick() -> Void {
    this.m_scheduled = false;
    let gi = this.GetGameInstance();
    let qs = GameInstance.GetQuestsSystem(gi);
    if qs.GetFact(n"ashcache_mara_trophy_dropped") > 0 {
      this.m_status = "dropped";
      return;
    }
    let player = GetPlayer(gi);
    if !IsDefined(player) || qs.GetFact(n"ashcache_mara_body_placed") < 1
        || qs.GetFact(n"ashcache_mara_liberty_given") < 1 {
      this.m_status = "waiting for body";
      this.Schedule(5.0);
      return;
    }
    // ac_mara_liberty_drop in source/world.json: where the look-alike prop lies.
    let at = Vector4(1545.5562, -1981.6118, 73.50, 1.0);
    if Vector4.Distance(player.GetWorldPosition(), at) > 25.0 {
      this.m_status = "waiting for V";
      this.Schedule(2.0);
      return;
    }
    let item = ItemID.FromTDBID(t"Items.ashcache_mara_trophy");
    GameInstance.GetTransactionSystem(gi).GiveItem(player, item, 1);
    let ok = GameInstance.GetLootManager(gi).SpawnItemDrop(player, item, at, Quaternion(0.0, 0.0, 0.0, 1.0));
    this.m_status = "drop=" + ToString(ok);
    qs.SetFact(n"ashcache_mara_trophy_dropped", 1);
  }
}
