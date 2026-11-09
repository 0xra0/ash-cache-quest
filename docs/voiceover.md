# Voiceover

Ash Cache ships 43 spoken lines as subtitles with no audio. This is how audio
gets added, what is already built, and the one step that cannot be done from
here.

## What the engine needs

Three resources per locale, all keyed off the SAME locstring ruid that
`gen_scene.py` bakes into the `.scene`:

    .scene   scnscreenplayDialogLine.locstringId.ruid = 7731500000000000000
      |
      +-- .xl  localization.subtitles.<loc>  ->  the words   (gen_subtitles.py)
      +-- .xl  localization.vomaps.<loc>     ->  the audio   (gen_vomap.py)

...and a fourth resource that does NOT key off the ruid, which is why it gets its
own section below:

      +-- .xl  localization.lipmaps.<loc>    ->  the mouth   (gen_lipmap.py)

`source/subtitle_ids.json` already allocates every ruid, so nothing new has to be
numbered. A voiced line and its subtitle cannot drift apart, because neither one
is written by hand.

`vomaps` is ArchiveXL's key, read out of its source rather than guessed:
`src/App/Extensions/Localization/Config.cpp:10` defines `VoiceOverMapsNodeKey`,
and `Extension.cpp` hooks `Localization::LoadVoiceOvers` to merge ours into the
game's index. Shape confirmed against a shipped mod: AldecaldosHighStakes carries
a `locVoiceoverMap` of `locVoLineEntry{stringId, femaleResPath, maleResPath}` and
its `.wem` files inside its ordinary archive. **No REDmod is involved** - VO is
archive content like everything else.

`femaleResPath` / `maleResPath` are the **player's** gender, not the speaker's.
Mara says the same words to either V, so one file serves both; High Stakes does
exactly this for every NPC line it ships. Only V's own lines would need two takes.

## Adding a line: the whole workflow

    tools/vo_rip.py mara --one-take --mono     # optional: training material
    <RVC / SoniTranslate / whatever makes the take>
    cp take.wav vo/en-us/mara.mara_open_1.wav
    tools/build.sh

## Adding all 43 at once: render, listen, promote

One file at a time is a `cp`. A whole batch is not, because a batch can be
*incomplete* and nothing downstream will say so - the drop folder is the
manifest, so 30 files and 43 files are equally legal and the thirteen missing
lines play as subtitles over silence. So a batch goes through three steps:

    tools/render_lines.py --locale en-us --tts piper --out <dir>   # never into vo/
    <listen>
    tools/vo_promote.py <dir>          # dry run: what would move, and what is wrong
    tools/vo_promote.py <dir> --yes    # copy, then validate + build

`tools/render_after_training.sh` does the first step unattended, waiting out a
training run, health-gating each model and measuring the result. It stops there
on purpose: it can prove a take is not clipped, not noisy and not hiss, and it
cannot tell you whether it sounds like Mara.

`vo_promote.py` refuses a batch that does not cover every line, that contains a
name matching no line, that did not measure clean *now* (not when it was
rendered), or that carries a locale outside `VO_LOCALES`. It copies sources only
and deletes any stale `.wem` for the keys it replaces, so the build always does
the conversion - see `docs/decisions.md` D43 for why that ordering matters.

That is all, and nothing in that chain leaves this machine or needs an account.
A `.wav` is converted to a `.wem` in place by the build (see below); a `.wem`
dropped in directly is used as-is and never touched.

    vo/en-us/mara.mara_open_1.wav        one take, heard by both Vs
    vo/en-us/mara.mara_open_1.f.wav      split take, female V
    vo/en-us/mara.mara_open_1.m.wav      split take, male V

The stem is the `<scene>.<line id>` key from `source/subtitle_ids.json`; a name
that matches no line fails the build rather than going quiet in game.

**The files on disk are the manifest.** There is no list to keep in step: a line
gets an entry when its `.wem` exists and not before, and removing the last `.wem`
for a locale removes that locale's map from the archive and from the `.xl`. This
is deliberate. An entry whose `.wem` is missing from the archive is a dangling
`raRef` - the scene plays, the subtitle appears, and there is simply no sound,
with nothing in any log.

**Which locales get audio is not the same list as which get text**, and the
difference is `VO_LOCALES` in `tools/gen_vomap.py` — today just `en-us`. `ua-ua`
is translated in full and voiced not at all, so the Ukrainian subtitle sits over
the English take. That is not a fallback that slipped through; it is what vanilla
does for a Ukrainian player, and it is what the player asked for (D42). Audio
found under any locale outside `VO_LOCALES` fails the build, because it would
convert and pack and then never be played.

## Making the .wem, without Wwise

    vo/en-us/mara.mara_open_1.wav
    tools/build.sh

The build converts it. `tools/wav_to_wem.py` runs first and turns any `.wav`,
`.flac`, `.ogg`, `.mp3` or `.m4a` in a drop folder into a `.wem` beside it; a
`.wem` with no source file next to it was hand-encoded and is never touched.

**This works because `.wem` does not have to mean Vorbis.** Wwise Vorbis is a
stripped Vorbis whose codebooks live outside the stream — `ww2ogg` only runs the
decode direction and nothing free runs the other way. But the container is a
plain RIFF, and Wwise also plays **uncompressed PCM**, which needs no encoder:
96 bytes of header in front of the samples.

That the game decodes PCM is not a guess. Every `.wem` in `audio_1_general`
(4,434) and `audio_2_soundbanks` (4,796) was read: **127 carry `wFormatTag`
`0xFFFE`**, 16-bit PCM. The mod LizziesBDs ships 116 more. The header this tool
writes is byte-identical to a shipped one apart from the sizes and the hash, and
a vanilla line round-tripped through it comes back sample-identical.

**What is not verified (rule 8):** those 243 PCM files all live under
`base\sound\soundbanks\media` — bank media. Every custom voice line in all 24
installed mods that ship a `vomap` (342 files) is Vorbis, so nothing shipped
proves PCM through `locVoiceoverMap`'s external-source path, which is the one
this project uses. It should hold — both paths end in the same Wwise source
reader dispatching on the `fmt` tag — but only the game can say. The failure
mode is a subtitle with no sound, which is what happens today anyway.

Size: 96 KB/s, about 17 MB per locale for 43 lines, lossless. `--rate 24000`
halves it; the game ships 24 kHz voice for every holocall.

### If PCM turns out not to play: the Wwise route

Unchanged, and still the guaranteed answer.

  - **Wwise 2023.1.14 exactly.** The wiki calls the version a hard requirement -
    it is what the game was built with, and another version's output may not be
    recognised at all. Free, but the download needs an Audiokinetic account.
  - New project -> Project Settings -> Source Settings -> Default Conversion
    Settings -> **Vorbis Quality High**.
  - Project -> Import Audio Files, `Import as: Sound SFX`.
  - ShareSets -> Vorbis Quality High: **Mono**, **48000**, **Vorbis**. Convert.
  - The `.wem` files land in
    `WwiseProjects/<project>/.cache/Windows/Voices/English(US)`. Ignore the `.dat`.

Source: `Cyberpunk-Modding-Docs/modding-guides/quest/adding-a-custom-voiceline-to-a-scene.md`
(written 2026-09-02, the freshest thing on the subject).

Under wine, `WwiseConsole.exe` can do the conversion headlessly once the GUI has
made the project once. That is untested here and is marked TODO under rule 8.

## Lipsync

A voiced line with no lipsync plays over a face frozen in its idle, which reads
as a broken NPC rather than as a missing feature. Everything except the animation
file itself is built and verified.

**It does not key off the ruid.** That was the going-in assumption and it was
wrong. The lipsync map keys off the actor's **voicetag**, one level above the
line; the line-level key lives *inside* the animation set, as the animation's
name:

    .scene   scnActorDef.voicetagId.id                     who is speaking
    .lipmap  scenePaths[i]      = FNV1a64(scene depot path) which scene
    .lipmap  sceneEntries[i].actorVoiceTags[j]              who, again
    .lipmap  sceneEntries[i].animSets[j]  ->  that actor's .anims
    .scene   screenplayDialogLine.femaleLipsyncAnimationName = f_<ruid:016X>
    .anims   animations[k].name                             = f_<ruid:016X>

Verified end to end on one vanilla line - see OI-17 for the full read-back. Two
consequences worth knowing while authoring:

  - A **voicetag is global to a character**, not per scene. `source/voicetags.json`
    is append-only; renumbering one unbinds that character's lipsync from every
    scene at once. `tools/alloc_voicetags.py` owns the block.
  - V keeps voicetag `0` and gets no animset. The game ships lipsync for the
    player in **zero** of its 5688 lipsync animsets, because V is normally seen
    from the inside.

The `f_` / `m_` prefix on the animation name is the **player's** gender, the same
split the `.wem` pair uses - not the speaker's. Vanilla writes both names on every
line and then ships only the `f_` animation, so an `m_` name that resolves to
nothing is demonstrably harmless.

### Adding lipsync

    lipsync/en-us/mara.anims
    tools/build.sh

Same drop-folder rule as the audio, for the same reason: a lipmap naming an
animset that was not packed merges cleanly, logs success and moves no mouth. One
animset per character per locale, holding every line that character says
anywhere - Kidnap's layout, and the map is small enough that per-scene files buy
nothing.

`lipmaps` is ArchiveXL's own key (`Localization/Config.cpp:9`,
`LipMapsNodeKey`), merged by hooking `Localization::LoadLipsyncs`.
`MergeLipsyncResource` rejects the **whole** resource if `scenePaths` and
`sceneEntries` differ in length, which is why `gen_lipmap.py` never builds the two
arrays in separate passes.

### Making the .anims: what the obstacle actually is

Not the file format. A lipsync take is an ordinary skeletal animation on the
character's own face rig - `animAnimSet` -> `animAnimation` named
`f_<ruid:016X>`, `AdditiveFromRefPose`, ~51 of the rig's 344 joints moving.
WolvenKit writes these: `AnimationTools.ImportAnims` takes a **glTF** and an
existing `.anims` and re-encodes it through `AnimSIMDEncoder`, producing an
`animAnimationBufferSimd` - a buffer type vanilla itself ships (13 of 208
sampled animations use it exclusively, 22 more alongside the compressed one), so
the runtime plays it.

Export already works here:

    WolvenKit.CLI export <vanilla lipsync>.anims -o out -gp "<game dir>"

Import does not, headless: `ImportCommand.cs` declares no `--gamepath`, so the
rig cannot be resolved. Use the WolvenKit **GUI** (it has a project, and
therefore a game path), or patch the CLI. See OI-17 for the exact failure and
the `GltfImportArgs` setting that routes a `.glb` to the anim importer.

**What is genuinely missing is the animation itself** - face-rig curves matching
the audio. Transplanting a vanilla take of similar length is possible and cheap
and matches nothing; Rhubarb Lip Sync gives viseme timings but the mapping onto
this rig is unbuilt; authoring in Blender is real work times 43 lines.
**TODO, unverified (rule 8).**

## Training a voice on the game's own actors

The game names every voice file after who says it:

    base\localization\en-us\vo\johnny_sq031_f_1a589ce2ca2c5000.wem
                               ^^^^^^ ^^^^^ ^ ^^^^^^^^^^^^^^^^
                               speaker quest |  locstring ruid, hex
                                             player gender variant

so one speaker's entire corpus is a prefix match. 110,495 English lines across
the base game and Phantom Liberty.

    tools/vo_rip.py --list                       who is in the game, ranked
    tools/vo_rip.py songbird --one-take --mono   -> /mnt/sata/Cyberpunk2077/vo_corpus/

`vo_rip.py` reads the two `lang_en_voice.archive` files (rule 2: read only, it
never writes to the game directory), decodes Custom Vorbis at 48 kHz through
`vgmstream-cli`, and optionally downmixes with `sox` for an RVC front end.

Line counts worth knowing:

    v 29250   johnny 2714   panam 2420   reed 1926   songbird 1863
    judy 1482  jackie 1134  takemura 975  rogue 900  kerry 839  myers 617

`--one-take` matters: the `_f_` and `_m_` files of one ruid are the same NPC
performance recorded against a different V, so they are near-duplicates for
training purposes and doubling the corpus with them buys nothing. A line can also
exist twice at once, in `vo/` and `vo_holocall/` - separate mixes of one take,
same file name, so the decode count exceeds the file count on purpose.

## What is still missing

One encoder, and one unverified assumption:

  - `<audio> -> .anims` — the container is writable (WolvenKit, from glTF), and
    the CLI cannot do it headless; what is missing is viseme data. OI-17. This
    is the real blocker.
  - `.wav -> .wem` is **written** (`tools/wav_to_wem.py`, PCM) but the VO path's
    acceptance of PCM is untested in game. OI-16.

Everything else is built, wired into `tools/build.sh`, emitted into the `.xl`,
checked by `tools/validate.py` and frozen by `tools/negtest.py`. Drop a file in
`vo/<loc>/` or `lipsync/<loc>/` and rebuild; that is the whole workflow.
