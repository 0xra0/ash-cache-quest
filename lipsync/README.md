# lipsync/ — the drop folder for facial animation

    lipsync/en-us/mara.anims
    lipsync/ua-ua/mara.anims

One `animAnimSet` per character per locale, named by the character's `id` in
`source/characters.json`. Drop a file here and run `tools/build.sh`; there is no
list to keep in step. `tools/gen_lipmap.py` reads this directory, `build.sh`
packs the map and the animsets together, and `gen_xl.py` emits a
`localization.lipmaps` entry only for a locale that actually has one — because a
lipmap naming an animset that was not packed merges cleanly, logs success, and
moves no mouth.

A filename that names nobody in any scene's cast fails the build rather than
going quiet in game.

**Nothing here yet, and there is no way to author one from this repo.** An
`animAnimSet` needs a rig, opaque compressed `animationDataChunks`, and one
`animAnimationBufferCompressed` per take (344 joints, 414 tracks,
`AdditiveFromRefPose`). See `docs/voiceover.md` and OI-17.

Each animation inside the set must be named `f_<locstring ruid as 16 uppercase
hex digits>` — `tools/gen_scene.py` already writes those names into the `.scene`,
so `python3 -c "import json;print(...)"` on `source/subtitle_ids.json` gives the
list. The prefix is the *player's* gender, not the speaker's; only `f_` ships in
vanilla.
