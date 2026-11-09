# vo/ — the voiceover drop folder

Drop audio here, run `tools/build.sh`, and the line is voiced. Nothing else to
edit: the files in this folder *are* the manifest `tools/gen_vomap.py` reads.

    vo/en-us/mara.mara_open_1.wav      one take, heard by both Vs
    vo/en-us/mara.mara_open_1.f.wav    split take, female V
    vo/en-us/mara.mara_open_1.m.wav    split take, male V

The stem is the `<scene>.<line id>` key from `source/subtitle_ids.json`. A name
that matches no line fails the build; it does not go quiet in game.

`.wav`, `.flac`, `.ogg`, `.mp3` and `.m4a` are converted to `.wem` in place by
`tools/wav_to_wem.py` at the start of every build — 48 kHz mono 16-bit Wwise
PCM, no Wwise installed. A `.wem` with no source file beside it was encoded by
hand and is never touched, so a real Wwise Vorbis encode always wins.

The `.f` / `.m` split is the **player's** gender, not the speaker's. Mara says
the same words to either V, so one file normally serves both; only V's own lines
would ever need two takes.

**Only `en-us` gets audio** (`VO_LOCALES` in `tools/gen_vomap.py`). `ua-ua` is a
real translation and keeps every subtitle, onscreen and journal entry — it just
has no recordings of its own, so a Ukrainian player reads Ukrainian and hears
English, exactly as they do in vanilla, which ships `lang_ua_text.archive` and
no Ukrainian voice at all. Dropping audio into `vo/ua-ua/` is therefore a build
error, not a silent nothing: it would convert, pack, and never play. See
`docs/decisions.md` D42 for why, and for what to change if that ever stops being
true.

Whether the game accepts PCM on this path is the one thing not verified from
here; see OI-16 and `docs/voiceover.md`. If a line is silent in game with
everything else correct, that is the suspect, and the Wwise fallback is
documented.
