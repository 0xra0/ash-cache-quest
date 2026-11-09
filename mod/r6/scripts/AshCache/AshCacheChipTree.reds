// The Splinter perk tree (D115). Hand-written; the data it reads is generated
// into AshCacheChipData.reds by tools/gen_chip.py from source/chip_tree.json.
//
// Not quest logic (rule 1): the graph never waits on anything here. The tree only
// READS facts the graph already sets (endings, milestones) and WRITES its own
// ashcache_chip_* facts when V buys a perk. Facts, not script fields, because
// facts are saved with the game and script fields are not.
//
// The menu comes from CustomPerkFramework (an installed mod, not ours). Everything
// that touches it is behind @if(ModuleExists), so without it the perks still work
// and Ash Cache still compiles - there is just no screen to buy them from.

module AshCacheChip

@if(ModuleExists("CustomPerkFramework"))
import CustomPerkFramework.*

// ---------------------------------------------------------------- rules --------

public abstract class AshCacheChip {
  // 0 none, 1 partial (tiers below FullTier), 2 full. First matching fact wins,
  // so Burn - listed first - overrides everything after it.
  public static func UnlockLevel(gi: GameInstance) -> Int32 {
    let facts = AshCacheChipData.UnlockFacts();
    let levels = AshCacheChipData.UnlockLevels();
    let i = 0;
    while i < ArraySize(facts) {
      if GetFact(gi, facts[i]) > 0 {
        return levels[i];
      }
      i += 1;
    }
    return 0;
  }

  // True once any ending fact is set: separates "not yet" from "burned".
  public static func Decided(gi: GameInstance) -> Bool {
    let facts = AshCacheChipData.UnlockFacts();
    let i = 0;
    while i < ArraySize(facts) {
      if GetFact(gi, facts[i]) > 0 {
        return true;
      }
      i += 1;
    }
    return false;
  }

  public static func Earned(gi: GameInstance) -> Int32 {
    let facts = AshCacheChipData.PointFacts();
    let values = AshCacheChipData.PointValues();
    let sum = 0;
    let i = 0;
    while i < ArraySize(facts) {
      if GetFact(gi, facts[i]) > 0 {
        sum += values[i];
      }
      i += 1;
    }
    return sum;
  }

  public static func Spent(gi: GameInstance) -> Int32 {
    let costs = AshCacheChipData.PerkCost();
    let sum = 0;
    let i = 0;
    while i < AshCacheChipData.PerkCount() {
      if AshCacheChip.IsBought(gi, i) {
        sum += costs[i];
      }
      i += 1;
    }
    return sum;
  }

  public static func Available(gi: GameInstance) -> Int32 {
    return AshCacheChip.Earned(gi) - AshCacheChip.Spent(gi);
  }

  public static func IsBought(gi: GameInstance, i: Int32) -> Bool {
    let facts = AshCacheChipData.PerkFact();
    return GetFact(gi, facts[i]) > 0;
  }

  // The perk one tier below i in the same branch, or -1 for a tier-1 perk.
  public static func Prerequisite(i: Int32) -> Int32 {
    let branch = AshCacheChipData.PerkBranch();
    let tier = AshCacheChipData.PerkTier();
    if tier[i] <= 1 {
      return -1;
    }
    let j = 0;
    while j < AshCacheChipData.PerkCount() {
      if branch[j] == branch[i] && tier[j] == tier[i] - 1 {
        return j;
      }
      j += 1;
    }
    return -1;
  }

  // Why perk i cannot be bought right now, as display text; "" when it can.
  public static func BlockReason(gi: GameInstance, i: Int32) -> String {
    let level = AshCacheChip.UnlockLevel(gi);
    if level <= 0 {
      return AshCacheChip.Decided(gi) ? GetLocalizedText(AshCacheChipData.SBurned())
                                      : GetLocalizedText(AshCacheChipData.SDormant());
    }
    let tiers = AshCacheChipData.PerkTier();
    let costs = AshCacheChipData.PerkCost();
    if level < 2 && tiers[i] >= AshCacheChipData.FullTier() {
      return GetLocalizedText(AshCacheChipData.SLockedFull());
    }
    let pre = AshCacheChip.Prerequisite(i);
    if pre >= 0 && !AshCacheChip.IsBought(gi, pre) {
      return GetLocalizedText(AshCacheChipData.SLockedPrev());
    }
    if AshCacheChip.Available(gi) < costs[i] {
      return GetLocalizedText(AshCacheChipData.SLockedPoints());
    }
    return "";
  }

  public static func Buy(player: ref<PlayerPuppet>, i: Int32) -> Bool {
    let gi = player.GetGame();
    if AshCacheChip.IsBought(gi, i) || NotEquals(AshCacheChip.BlockReason(gi, i), "") {
      return false;
    }
    let facts = AshCacheChipData.PerkFact();
    SetFactValue(gi, facts[i], 1);
    AshCacheChip.Sync(player);
    return true;
  }

  public static func ResetAll(player: ref<PlayerPuppet>) -> Void {
    let gi = player.GetGame();
    let facts = AshCacheChipData.PerkFact();
    let i = 0;
    while i < AshCacheChipData.PerkCount() {
      SetFactValue(gi, facts[i], 0);
      i += 1;
    }
    AshCacheChip.Sync(player);
  }

  // Makes the player's status effects match the facts: every bought perk the
  // current unlock level allows is applied once, everything else removed.
  // Idempotent, so it is safe on load, on buy, on reset and on every tick.
  public static func Sync(player: ref<PlayerPuppet>) -> Void {
    let gi = player.GetGame();
    let level = AshCacheChip.UnlockLevel(gi);
    let effects = AshCacheChipData.PerkEffect();
    let tiers = AshCacheChipData.PerkTier();
    let i = 0;
    while i < AshCacheChipData.PerkCount() {
      let allowed = level >= 2 || (level == 1 && tiers[i] < AshCacheChipData.FullTier());
      let want = allowed && AshCacheChip.IsBought(gi, i);
      let has = StatusEffectSystem.ObjectHasStatusEffect(player, effects[i]);
      if want && !has {
        StatusEffectHelper.ApplyStatusEffect(player, effects[i]);
      } else if !want && has {
        StatusEffectHelper.RemoveStatusEffect(player, effects[i]);
      }
      i += 1;
    }
  }
}

// ---------------------------------------------------------------- runtime ------

public class AshCacheChipTickCallback extends DelayCallback {
  public let sys: wref<AshCacheChipSystem>;

  public func Call() -> Void {
    if IsDefined(this.sys) {
      this.sys.Tick();
    }
  }
}

// Re-applies bought perks after a load (the effects are savable: false), puts
// the tree in the menu once V holds the splinter, and says so once it unlocks.
// A 3 s poll rather than an event: the ending facts are set inside a scene, and
// nothing announces a fact change to script.
public class AshCacheChipSystem extends ScriptableSystem {
  public func OnAttach() -> Void {
    this.Arm(3.0);
  }

  public func OnRestored(saveVersion: Int32, gameVersion: Int32) -> Void {
    this.Arm(3.0);
  }

  private func Arm(delay: Float) -> Void {
    let cb = new AshCacheChipTickCallback();
    cb.sys = this;
    GameInstance.GetDelaySystem(this.GetGameInstance()).DelayCallback(cb, delay, false);
  }

  public func Tick() -> Void {
    let gi = this.GetGameInstance();
    let player = GetPlayer(gi);
    if IsDefined(player) && !player.IsReplacer() {
      AshCacheChip.Sync(player);
      if GetFact(gi, AshCacheChipData.VisibleFact()) > 0 {
        AshCacheChipRegisterTree(gi);
      }
      if AshCacheChip.UnlockLevel(gi) > 0 && GetFact(gi, AshCacheChipData.NotifiedFact()) <= 0 {
        SetFactValue(gi, AshCacheChipData.NotifiedFact(), 1);
        this.Notify(GetLocalizedText(AshCacheChipData.SUnlockedMsg()));
      }
      // Near a fragment the poll speeds up, or a walking V could cross the
      // radius between two ticks.
      let nearest = this.UpdateFragments(player);
      if nearest >= 0.0 && nearest < 30.0 {
        this.Arm(0.5);
        return;
      }
    }
    this.Arm(3.0);
  }

  // Echo fragments (D117). One exists in the world only while the tree is
  // unlocked and its fact is 0; walking within FragRadius sets the fact, which is
  // already a point source. Returns the distance to the nearest one left, or -1.
  private func UpdateFragments(player: ref<PlayerPuppet>) -> Float {
    let gi = this.GetGameInstance();
    let facts = AshCacheChipData.FragFacts();
    let pos = AshCacheChipData.FragPos();
    let yaw = AshCacheChipData.FragYaw();
    let open = AshCacheChip.UnlockLevel(gi) > 0;
    let here = player.GetWorldPosition();
    let nearest = -1.0;
    let i = 0;
    while i < ArraySize(facts) {
      if !open || GetFact(gi, facts[i]) > 0 {
        AshCacheChipFragDespawn(facts[i]);
      } else {
        let d = Vector4.Distance(here, pos[i]);
        if d <= AshCacheChipData.FragRadius() {
          SetFactValue(gi, facts[i], 1);
          AshCacheChipFragDespawn(facts[i]);
          this.Notify(GetLocalizedText(AshCacheChipData.SFragMsg()) + " "
            + IntToString(this.FragmentsTaken()) + "/" + IntToString(ArraySize(facts)));
        } else {
          // The fact doubles as the entity tag.
          AshCacheChipFragSpawn(facts[i], pos[i], yaw[i]);
          if nearest < 0.0 || d < nearest {
            nearest = d;
          }
        }
      }
      i += 1;
    }
    return nearest;
  }

  private func FragmentsTaken() -> Int32 {
    let gi = this.GetGameInstance();
    let facts = AshCacheChipData.FragFacts();
    let n = 0;
    let i = 0;
    while i < ArraySize(facts) {
      if GetFact(gi, facts[i]) > 0 {
        n += 1;
      }
      i += 1;
    }
    return n;
  }

  private func Notify(text: String) -> Void {
    let msg: SimpleScreenMessage;
    msg.isShown = true;
    msg.duration = 8.0;
    msg.message = text;
    msg.type = SimpleMessageType.Relic;
    GameInstance.GetBlackboardSystem(this.GetGameInstance())
      .Get(GetAllBlackboardDefs().UI_Notifications)
      .SetVariant(GetAllBlackboardDefs().UI_Notifications.WarningMessage, ToVariant(msg), true);
  }
}

// Codeware's DynamicEntitySystem places the shard. Not saved (persistSpawn false):
// after a load the tag is empty again and the next tick re-creates it, so the
// save never carries a fragment the facts say is gone. IsPopulated counts
// registered entities, not only streamed-in ones, so this never duplicates.
@if(ModuleExists("Codeware"))
public func AshCacheChipFragSpawn(tag: CName, pos: Vector4, yaw: Float) -> Void {
  let des = GameInstance.GetDynamicEntitySystem();
  if !IsDefined(des) || !des.IsReady() || des.IsPopulated(tag) {
    return;
  }
  let spec = new DynamicEntitySpec();
  spec.templatePath = AshCacheChipData.FragTemplate();
  // Drawn above the recorded spot. `pos` is where V's FEET were, and the template's
  // mesh is a few centimetres of splinter, so at pos it lies on the floor outside the
  // standing view cone - fragment 1 was walked onto and never seen. The trigger in
  // UpdateFragments still measures from pos, which is verified to fire.
  spec.position = Vector4(pos.X, pos.Y, pos.Z + AshCacheChipData.FragZOffset(), 1.0);
  let rot: EulerAngles;
  rot.Yaw = yaw;
  spec.orientation = EulerAngles.ToQuat(rot);
  spec.persistState = false;
  spec.persistSpawn = false;
  spec.alwaysSpawned = false;
  spec.spawnInView = true;
  spec.active = true;
  ArrayPush(spec.tags, tag);
  // A refused spawn is otherwise indistinguishable from a shard that is merely hard
  // to see: the fact fires on walk-over either way, so the points arrive and nothing
  // reports that the template never loaded.
  if !EntityID.IsDefined(des.CreateEntity(spec)) {
    FTLogWarning("ashcache: fragment " + NameToString(tag) + " did not spawn");
  }
}

@if(ModuleExists("Codeware"))
public func AshCacheChipFragDespawn(tag: CName) -> Void {
  let des = GameInstance.GetDynamicEntitySystem();
  if IsDefined(des) && des.IsReady() && des.IsPopulated(tag) {
    des.DeleteTagged(tag);
  }
}

@if(!ModuleExists("Codeware"))
public func AshCacheChipFragSpawn(tag: CName, pos: Vector4, yaw: Float) -> Void {}

@if(!ModuleExists("Codeware"))
public func AshCacheChipFragDespawn(tag: CName) -> Void {}

@if(ModuleExists("CustomPerkFramework"))
public func AshCacheChipRegisterTree(gi: GameInstance) -> Void {
  let sys = CustomPerkFrameworkSystem.GetInstance(gi);
  if IsDefined(sys) {
    // RegisterTree refuses a duplicate id, so calling it every tick is a no-op
    // after the first - and re-registers after a load, which clears the list.
    sys.RegisterTree(new AshCacheChipTree());
  }
}

@if(!ModuleExists("CustomPerkFramework"))
public func AshCacheChipRegisterTree(gi: GameInstance) -> Void {}

// ---------------------------------------------------------------- menu ---------

@if(ModuleExists("CustomPerkFramework"))
public class AshCacheChipTree extends CustomPerkTree {
  private let m_area: ref<AshCacheChipArea>;

  public func GetTreeId() -> CName { return n"AshCacheChip"; }
  public func GetTreeName() -> String { return GetLocalizedText(AshCacheChipData.STreeName()); }
  public func GetTreeTagline() -> String { return GetLocalizedText(AshCacheChipData.STreeTagline()); }
  public func GetAccentColor() -> HDRColor { return HDRColor(0.20, 0.07, 0.02, 1.0); }
  public func GetTextColor() -> HDRColor { return AshCacheChipArea.Ember(); }
  public func GetBackgroundColor() -> HDRColor { return HDRColor(0.035, 0.02, 0.015, 1.0); }
  public func GetVignetteColor() -> HDRColor { return HDRColor(1.0, 0.35, 0.08, 1.0); }
  public func GetVignetteOpacity() -> Float { return 0.6; }
  public func GetIconAtlas() -> ResRef { return r"base\\gameplay\\gui\\fullscreen\\hub_menu\\hub_atlas.inkatlas"; }
  public func GetIconPart() -> CName { return n"ico_cyberware"; }
  public func UsesSharedPerkPoints() -> Bool { return false; }
  public func GetSortOrder() -> Int32 { return 10; }

  public func GetAvailablePerkPoints(player: wref<PlayerPuppet>) -> Int32 {
    return AshCacheChip.Available(player.GetGame());
  }

  public func GetSpentPerkPoints(player: wref<PlayerPuppet>) -> Int32 {
    return AshCacheChip.Spent(player.GetGame());
  }

  public func PopulateContent(contentArea: wref<inkCompoundWidget>, player: wref<PlayerPuppet>) -> Void {
    this.m_area = new AshCacheChipArea();
    this.m_area.Create(contentArea, player);
  }

  public func ClearContent() -> Void {
    this.m_area = null;
  }
}

// One clickable perk. Holds its index so the callback knows what was clicked.
@if(ModuleExists("CustomPerkFramework"))
public class AshCacheChipNode {
  public let index: Int32;
  public let area: wref<AshCacheChipArea>;
  public let bg: wref<inkRectangle>;

  protected cb func OnNodeRelease(evt: ref<inkPointerEvent>) -> Bool {
    if evt.IsAction(n"click") && IsDefined(this.area) {
      this.area.OnBuy(this.index);
    }
    return false;
  }

  protected cb func OnNodeHoverOver(evt: ref<inkPointerEvent>) -> Bool {
    if IsDefined(this.bg) {
      this.bg.SetOpacity(0.95);
    }
    return false;
  }

  protected cb func OnNodeHoverOut(evt: ref<inkPointerEvent>) -> Bool {
    if IsDefined(this.bg) {
      this.bg.SetOpacity(0.7);
    }
    return false;
  }
}

@if(ModuleExists("CustomPerkFramework"))
public class AshCacheChipArea {
  private let m_parent: wref<inkCompoundWidget>;
  private let m_root: wref<inkVerticalPanel>;
  private let m_player: wref<PlayerPuppet>;
  private let m_nodes: array<ref<AshCacheChipNode>>;

  public static func Ember() -> HDRColor { return HDRColor(1.15, 0.52, 0.18, 1.0); }
  public static func Grey() -> HDRColor { return HDRColor(0.42, 0.42, 0.42, 1.0); }
  public static func Owned() -> HDRColor { return HDRColor(1.25, 0.95, 0.55, 1.0); }

  public func Create(parent: wref<inkCompoundWidget>, player: wref<PlayerPuppet>) -> Void {
    this.m_parent = parent;
    this.m_player = player;
    this.Build();
  }

  public func OnBuy(i: Int32) -> Void {
    if AshCacheChip.Buy(this.m_player, i) {
      this.Rebuild();
    }
  }

  protected cb func OnResetRelease(evt: ref<inkPointerEvent>) -> Bool {
    if evt.IsAction(n"click") {
      AshCacheChip.ResetAll(this.m_player);
      this.Rebuild();
    }
    return false;
  }

  private func Rebuild() -> Void {
    if IsDefined(this.m_root) && IsDefined(this.m_parent) {
      this.m_parent.RemoveChild(this.m_root);
    }
    ArrayClear(this.m_nodes);
    this.Build();
    let sys = CustomPerkFrameworkSystem.GetInstance(this.m_player.GetGame());
    if IsDefined(sys) {
      sys.RefreshPopupHeader();
    }
  }

  private func Text(parent: ref<inkCompoundWidget>, s: String, size: Int32, style: CName, color: HDRColor) -> ref<inkText> {
    let t = new inkText();
    t.SetFontFamily("base\\gameplay\\gui\\fonts\\raj\\raj.inkfontfamily");
    t.SetFontStyle(style);
    t.SetFontSize(size);
    t.SetText(s);
    t.SetTintColor(color);
    t.Reparent(parent);
    return t;
  }

  private func Build() -> Void {
    let gi = this.m_player.GetGame();
    let level = AshCacheChip.UnlockLevel(gi);

    let root = new inkVerticalPanel();
    root.SetName(n"ashcacheChipArea");
    root.SetAnchor(inkEAnchor.Centered);
    root.SetAnchorPoint(Vector2(0.5, 0.5));
    root.SetFitToContent(true);
    root.Reparent(this.m_parent);
    this.m_root = root;

    let points = this.Text(root, GetLocalizedText(AshCacheChipData.SPoints()) + ": " + ToString(AshCacheChip.Available(gi)),
                           52, n"Semi-Bold", AshCacheChipArea.Ember());
    points.SetHAlign(inkEHorizontalAlign.Center);
    points.SetMargin(inkMargin(0.0, 0.0, 0.0, 30.0));

    let columns = new inkHorizontalPanel();
    columns.SetFitToContent(true);
    columns.SetHAlign(inkEHorizontalAlign.Center);
    columns.SetChildMargin(inkMargin(40.0, 0.0, 40.0, 0.0));
    columns.Reparent(root);

    let b = 0;
    while b < AshCacheChipData.BranchCount() {
      this.BuildBranch(columns, b, level);
      b += 1;
    }

    let footer = new inkHorizontalPanel();
    footer.SetFitToContent(true);
    footer.SetHAlign(inkEHorizontalAlign.Center);
    footer.SetMargin(inkMargin(0.0, 36.0, 0.0, 0.0));
    footer.Reparent(root);

    let note = "";
    if level == 1 {
      note = GetLocalizedText(AshCacheChipData.SPartial());
    } else if level <= 0 {
      note = AshCacheChip.Decided(gi) ? GetLocalizedText(AshCacheChipData.SBurned())
                                      : GetLocalizedText(AshCacheChipData.SDormant());
    }
    let noteText = this.Text(footer, note, 34, n"Regular", AshCacheChipArea.Grey());
    noteText.SetVAlign(inkEVerticalAlign.Center);
    noteText.SetMargin(inkMargin(0.0, 0.0, 60.0, 0.0));

    let reset = new inkCanvas();
    reset.SetSize(260.0, 70.0);
    reset.SetInteractive(true);
    reset.Reparent(footer);
    let resetBg = new inkRectangle();
    resetBg.SetAnchor(inkEAnchor.Fill);
    resetBg.SetTintColor(HDRColor(0.25, 0.09, 0.03, 1.0));
    resetBg.SetOpacity(0.8);
    resetBg.Reparent(reset);
    let resetText = this.Text(reset, GetLocalizedText(AshCacheChipData.SReset()), 36, n"Semi-Bold", AshCacheChipArea.Ember());
    resetText.SetAnchor(inkEAnchor.Centered);
    resetText.SetAnchorPoint(Vector2(0.5, 0.5));
    reset.RegisterToCallback(n"OnRelease", this, n"OnResetRelease");
  }

  private func BuildBranch(parent: ref<inkCompoundWidget>, b: Int32, level: Int32) -> Void {
    let col = new inkVerticalPanel();
    col.SetFitToContent(true);
    col.Reparent(parent);

    let names = AshCacheChipData.BranchName();
    let title = this.Text(col, GetLocalizedText(names[b]), 56, n"Semi-Bold", AshCacheChipArea.Ember());
    title.SetHAlign(inkEHorizontalAlign.Center);
    title.SetMargin(inkMargin(0.0, 0.0, 0.0, 16.0));

    // Tiers top to bottom, as the data orders them within the branch.
    let branches = AshCacheChipData.PerkBranch();
    let tiers = AshCacheChipData.PerkTier();
    let tier = 1;
    while tier <= AshCacheChipData.TierCount() {
      let i = 0;
      while i < AshCacheChipData.PerkCount() {
        if branches[i] == b && tiers[i] == tier {
          this.BuildNode(col, i);
        }
        i += 1;
      }
      tier += 1;
    }
  }

  private func BuildNode(parent: ref<inkCompoundWidget>, i: Int32) -> Void {
    let gi = this.m_player.GetGame();
    let bought = AshCacheChip.IsBought(gi, i);
    let reason = bought ? "" : AshCacheChip.BlockReason(gi, i);
    let buyable = !bought && Equals(reason, "");

    let node = new inkCanvas();
    node.SetSize(640.0, 200.0);
    node.SetMargin(inkMargin(0.0, 10.0, 0.0, 10.0));
    node.SetInteractive(true);
    node.Reparent(parent);

    let bg = new inkRectangle();
    bg.SetAnchor(inkEAnchor.Fill);
    bg.SetTintColor(bought ? HDRColor(0.30, 0.13, 0.04, 1.0) : HDRColor(0.09, 0.06, 0.05, 1.0));
    bg.SetOpacity(0.7);
    bg.Reparent(node);

    let bar = new inkRectangle();
    bar.SetAnchor(inkEAnchor.LeftFillVerticaly);
    bar.SetSize(10.0, 200.0);
    bar.SetTintColor(bought ? AshCacheChipArea.Owned() : (buyable ? AshCacheChipArea.Ember() : AshCacheChipArea.Grey()));
    bar.Reparent(node);

    let body = new inkVerticalPanel();
    body.SetMargin(inkMargin(34.0, 18.0, 24.0, 12.0));
    body.Reparent(node);

    let nameColor = bought ? AshCacheChipArea.Owned() : (buyable ? AshCacheChipArea.Ember() : AshCacheChipArea.Grey());
    let costs = AshCacheChipData.PerkCost();
    let names = AshCacheChipData.PerkName();
    let descs = AshCacheChipData.PerkDesc();
    this.Text(body, GetLocalizedText(names[i]) + "  [" + ToString(costs[i]) + "]", 42, n"Semi-Bold", nameColor);
    this.Text(body, GetLocalizedText(descs[i]), 32, n"Regular", HDRColor(0.85, 0.82, 0.78, 1.0));
    let status = bought ? GetLocalizedText(AshCacheChipData.SOwned())
                        : (buyable ? GetLocalizedText(AshCacheChipData.SBuyHint()) : reason);
    let statusText = this.Text(body, status, 28, n"Regular", bought ? AshCacheChipArea.Owned() : AshCacheChipArea.Grey());
    statusText.SetMargin(inkMargin(0.0, 8.0, 0.0, 0.0));

    let ctl = new AshCacheChipNode();
    ctl.index = i;
    ctl.area = this;
    ctl.bg = bg;
    ArrayPush(this.m_nodes, ctl);
    node.RegisterToCallback(n"OnRelease", ctl, n"OnNodeRelease");
    node.RegisterToCallback(n"OnHoverOver", ctl, n"OnNodeHoverOver");
    node.RegisterToCallback(n"OnHoverOut", ctl, n"OnNodeHoverOut");
  }
}
