# Recipes, and why the Neural Dampener is not built

Measured 2026-09-02 against `r6/cache/tweakdb_ep1.bin` with
`reference/tools/tweakdb_read.py`. Nothing here is copied from a wiki or a mod;
every line is a flat read out of the shipped database.

`ashcache_terminal_full_read` is declared in `source/facts.json` as "reading all
terminal logs (unlocks Neural Dampener recipe)". This file is what came back when
that was priced out.

## A recipe is an ordinary item you carry

There is no separate recipe system to hook. A recipe is a `gamedataItem_Record`
like any other; owning one is what makes the crafting screen offer the thing.
That means the graph already has the verb for it — the same `add_item` node that
grants the two shards and the FIA master key.

`Items.Recipe_BlindProgram`, in full, minus every flat left at its type default:

    itemType              ItemType.Gen_Misc
    tags                  [Recipe, SkipActivityLogOnRemove, HideInBackpackUI, Common]
    quality               Quality.Common
    craftingResult        Items.Recipe_BlindProgram_inline0
    objectActions         [ItemAction.Drop, ItemAction.Disassemble]
    icon                  UIIcon.ItemIcon
    isSingleInstance      True
    mass                  1.0
    canDrop               True
    buyPrice              [Price.BuyPrice_StreetCred_Discount]
    sellPrice             [Price.CyberdeckProgram]
    minigameInstance      minigame_v2.DefaultItemMinigame
    displayName           (LocKey 849)
    localizedDescription  (LocKey 49402)
    upgradeCostMult       1.0
    animName              ui_garment_pose
    animFeatureName       ItemData
    dropObject            defaultItemDrop
    crosshair             Crosshairs.None
    gameplayRestrictions  [GameplayRestriction.VehicleCombatNoInterruptions]

The last tag mirrors `quality`, and the two prices are the ones a *cyberdeck
program* recipe uses — both would change for a different kind of result.

`craftingResult` points at a second, inline record holding exactly two fields:

    Items.Recipe_BlindProgram_inline0.item    = Items.BlindProgram
    Items.Recipe_BlindProgram_inline0.amount  = 1

That two-record `X` + `X_inline0` shape is already how `tools/gen_tweak.py`
emits a readable shard (`itemSecondaryAction` → an inline
`gamedataItemAction_Record`), so a `kind: "recipe"` in `source/items.json` would
need no new machinery in the generator — one more branch in `item_records`.

## What is NOT measured: what a craft costs

`CraftingData` is `0x0` on every recipe sampled — `Recipe_BlindProgram`,
`Recipe_MetalPlating`, `Recipe_HighChargedBattery`, `Recipe_ChemicalDamageRound`.
There is no `ingredients` flat on the record at all; `grep '^Items.Recipe_'` over
the 3.5M-name dictionary returns `CraftingData` and `craftingResult` and nothing
else of the kind.

So the ingredient list is computed somewhere this measurement does not reach —
most likely off the crafted item's quality and type. Under rule 8 that is a TODO,
not a design: a recipe shipped with a guessed cost is a crafting screen that
either gives the item away or can never afford it.

## Why the Neural Dampener is still not built

Three reasons, in increasing order of how much they matter.

1. **The cost mechanism above is unmeasured.**

2. **There is no Neural Dampener to craft.** `grep -i dampener` over the whole
   TweakDB name dictionary returns nothing — it is not a vanilla item under that
   or any name. So the recipe needs a *second* mod-authored record: the dampener
   itself, with a real gameplay effect. Every item this project ships so far is a
   quest object or a readable, and those need no `statModifiers`, no
   `equipArea`, no cyberware slot. Giving a new item an actual effect is a
   subsystem this repo has never touched and cannot check without playing it.

3. **`ashcache_terminal_full_read` is not unblocked work.** This is the one that
   settles it. The fact is set by reading every log on the clinic terminal — the
   same terminal `ashcache_terminal_read` waits on, which `source/glue.json`
   lists under `blocked` as "an interactable computer at `#ac_clinic_terminal`,
   plus its log text". The completionist read cannot exist before the required
   read does. `docs/open_issues.md` and `docs/quest_design.md` both described
   this fact as authoring work waiting on nobody; they were wrong, and are
   corrected.

The order, when the probe comes back and the terminal is real: log text first,
then the full-read fact, then this recipe — and price the cost against a vanilla
recipe for an item of the same quality rather than inventing a number.
