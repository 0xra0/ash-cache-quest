# Ash Cache quest mod

Custom Cyberpunk 2077 quest. Read `docs/tech_spec.md` before writing anything.

## Hard rules

1. **The engine runs the quest.** Quest logic lives in the `.questphase` graph and
   the `.journal`. Do NOT write a quest state machine in redscript — that produces
   a quest with no journal entry, no objectives and no map markers. Redscript is
   glue only: reward grants, shard hooks, epilogue scheduling.
2. **Game directory writes are allowed (user, 2026-09-25).** Location Studio and
   cp77wb live tools (`wb_live_*`, `mcp__location-studio__*`) may be used freely,
   and the game folder may be modified. Still: back up any file before overwriting
   it (`.bak-<date>-<tag>`), develop against `mod/`, and say what was changed.
3. **Never use `/tmp`.** All working files live under `/mnt/sata`.
4. `source/` is hand-edited. `build/` is generated — never hand-edit it.
5. Every fact, objective, LocKey and item id is prefixed `ashcache_` / `ash_cache`.
6. LocKeys come from the reserved block in `source/lockeys.json`. Never invent one.
7. `ua-ua` is a real translation, not an en-us alias. The player is Ukrainian.
8. Do not invent engine APIs. **For redscript, verify by compiling** — see
   "Type-checking redscript" below; that beats every other kind of evidence.
   Otherwise verify against the extracted reference quests in
   `/mnt/sata/Cyberpunk2077/questmod-research/` or the installed mods' redscript in
   the game's `r6/scripts/`. If it cannot be verified, mark it TODO and say so.

## Toolchain

    WK="DOTNET_ROLL_FORWARD=LatestMajor dotnet /mnt/sata/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll"

Wine build for final packing: `/mnt/sata/weapon_mod/wkcli_win/WolvenKit.CLI.exe`.

The game itself is at

    /mnt/ssd/Cyberpunk 2077/game/prefix/drive_c/game

which is READ-ONLY from here (rule 2). Under it: `r6/scripts/` is 3,100 `.reds`
files of installed, working mods; `bin/x64/plugins/cyber_engine_tweaks/mods/` is
the same for CET Lua; `r6/logs/redscript_rCURRENT.log` shows what the game's own
compiler accepted last launch.

## Type-checking redscript

    tools/lint_glue.sh          # runs inside build.sh, step 3b

There is a native `redscript-cli` at `/mnt/sata/redscript/target/release/`, and
the game ships its compiled script bundle at `r6/cache/final.redscripts`. Together
they type-check mod redscript against the real game's RTTI in under a second, with
no game running:

    redscript-cli lint -s <dir of .reds> -b ".../r6/cache/final.redscripts"

Use it on anything new. Two traps it caught immediately, both of which would have
shipped from copying working code:

  - the installed mod SmugglersCache writes `private func OnAttach()`; redscript
    refuses to narrow an override's visibility, so it must be `public`
  - decompiled vanilla writes `new Vector4(x, y, z, w)`; the compiler wants
    `Vector4(x, y, z, w)`

`lint` exits 0 even when it reports errors — read the verdict out of the text.
And note the game compiles with its own older `scc.exe`, so where the two
disagree, prefer the construct that appears in an installed mod the game's log
shows compiling.

To read the vanilla side of any API rather than guess at it:

    redscript-cli decompile -b ".../r6/cache/final.redscripts" \
                            -o /mnt/sata/Cyberpunk2077/questmod-research/vanilla_scripts.reds

That is 560k lines of the game's own script source — every class, every native
signature, every enum. Grep it before writing a call.

## Reference material

Extracted, working quests to copy patterns from:
`/mnt/sata/Cyberpunk2077/questmod-research/`
- `extracted/` — Hot Fuzz, a complete 11-file quest
- `slots/AldecaldosHighStakes/` — the closest analogue: ArchiveXL injection + VO + redscript glue
- `undermine/` — largest reference, and the only one shipping real ua-ua subtitles
- `vanilla_ex/` — extracted from the GAME, for things no mod does. Its README says
  how to pull more, and how to read TweakDB *values* (not just names) out of
  `tweakdb_ep1.bin` with `/mnt/sata/weapon_mod/tweakdb_read.py`.

### Tool and loader source, checked out locally

Prefer these over reverse-engineering a shipped DLL — reading `ArchiveXL.dll`'s
constant pool cost an evening that one `grep` of the source would have ended (D20).

    /mnt/sata/cp2077-archive-xl     ArchiveXL  - .xl semantics, quest phase injection
    /mnt/sata/cp2077-tweak-xl       TweakXL    - .yaml record merging
    /mnt/sata/cp2077-codeware       Codeware   - the scripted API surface both add
    /mnt/sata/RED4ext               RED4ext    - the loader
    /mnt/sata/RED4ext.SDK           RED4ext.SDK - generated headers for every engine class
    /mnt/sata/RED4.RTTIDumper       RTTI dumper
    /mnt/sata/CyberEngineTweaks     CET        - what the Lua overlay can actually call
    /mnt/sata/WolvenKit-new         WolvenKit at HEAD (the CLI in use is still the
                                    older build named in "Toolchain" above)

Modding documentation, quest creation included:

    /mnt/sata/WolvenKit-8-Wiki
    /mnt/sata/Cyberpunk-Modding-Docs
    /mnt/sata/Red4Ext-Wiki
    /mnt/sata/Redscript-Wiki

ArchiveXL's quest phase behaviour is entirely in one 393-line file,
`src/App/Extensions/QuestPhase/Extension.cpp`. Both D20 and D21 came out of it.

`/mnt/sata/cp2077-tweakdb/tweakdbstr.txt` is every TweakDB name in the game,
3.5M lines. `tools/validate.py` checks every record id the mod uses against it —
both that inherited ones exist and that defined ones do not (D11).

`reference/codex_paths.txt` is the same idea for the journal's codex tree: all
1013 `gameJournalCodex*` entries of the shipped game, walked out of the two
`cooked_journal.journal` resources. `validate.py` checks every codex path the
journal links against it, class included. A codex link that resolves to nothing
renders as nothing, silently — and vanilla's own paths are misspelt, so they
cannot be reasoned about and have to be looked up (D23).

Voice is `docs/voiceover.md`: custom VO is ordinary archive content through
ArchiveXL's `localization.vomaps`, no REDmod. `tools/vo_rip.py` pulls any of the
game's own speakers out as `.wav` for training.

FACTS have no such dump — they are bare CNames living inside `.questphase`
resources, and a misspelt one reads 0 forever with no error anywhere. Every
vanilla fact this mod reads gets its provenance written into `reference/facts.md`
before it is used, and that file says how to check a new one.
