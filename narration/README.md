# narration/ — the notes, read aloud

One recording per shard, in V's voice, played by the **Toggle Audio** button
already on every shard in this game.

    narration/en-us/mara_journal.wav        <- the onscreen entry id, nothing else

    tools/render_lines.py --shards --tts piper

The stem is the `onscreen.entry` of a shard in `source/items.json`. A name that
matches no shard fails the build; it does not go quiet in game — which matters
more here than it does in `vo/`, because the button is drawn either way.

## Why this is not a folder inside vo/

`vo/` is spoken lines, and everything downstream of it is the engine's own
voiceover path: `.wav` → `.wem` → packed into the archive → named by
`locVoiceoverMap` → played by a scene that is waiting for it.

A shard reaches none of that. A `gameJournalOnscreen` has a title and a
description and nowhere to hang a sound, and nothing is playing when the player
opens one. So these files are never converted, never packed, and never mapped.
They are copied into the Audioware bank as-is and that is the whole route.
Keeping them out of `vo/` also keeps `validate.py`'s rule that every directory
under `vo/` is a locale that must ship voiceover — a guard worth more than the
convenience of one shared folder.

## How the button finds them

Shard Audio Framework (installed separately, `r6/scripts/shardaudioframework/`)
does exactly one thing:

    let text = StringToName(this.m_data.text);
    GameInstance.GetAudioSystem(GetGameInstance()).Play(text);

and vanilla's `ReadAction` sets `m_data.text = entry.GetDescription()`, which is
the onscreen entry's **raw** description — `"LocKey#77315028"`, not the prose.
So the CName the game asks for is this quest's own LocKey for that shard body.
`tools/gen_audioware.py` derives it from `source/items.json` + `source/lockeys.json`,
the same two files the journal is built from, so it cannot drift from the note.

Without Shard Audio Framework installed there is no button and these files are
inert. Nothing else in the quest depends on it.

## What is read

The shard body itself — the same string the journal draws. Not a script written
for the voice. V reads what is in front of him, which is the point of the beat
and also means a note added later is voiced without writing anything new.

`tools/render_lines.py:narration_text()` flattens it first: paragraph breaks are
collapsed (piper's CLI treats one line as one utterance and would leave a
forty-second note playing as its closing sentence), brackets around a header are
dropped while the words stay, and a dash left dangling becomes an ellipsis
because "Take the—" is a man being cut off, not a man finishing.

## Only en-us

Same rule as `vo/`, same reason: `gen_vomap.VO_LOCALES`, `docs/decisions.md` D42.
A Ukrainian player reads Ukrainian and hears English, as they do in vanilla. All
18 locales in the bank point at the en-us file on purpose.
