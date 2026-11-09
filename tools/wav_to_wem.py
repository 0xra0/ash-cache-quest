#!/usr/bin/env python3
"""Any audio file -> a Wwise PCM .wem the game can play, with no Wwise installed.

    tools/wav_to_wem.py                     convert every vo/<locale>/*.wav
    tools/wav_to_wem.py in.wav out.wem      one file
    tools/wav_to_wem.py --force --rate 24000

WHY THIS EXISTS
The modding guides all say the same thing: .wem is Wwise's container, only Wwise
writes it, and it has to be Wwise 2023.1.14 exactly, which is free but behind an
Audiokinetic account and is a Windows GUI. That is true for Wwise VORBIS, which
is a stripped Vorbis whose codebooks live outside the stream - nothing free
writes it, and ww2ogg only runs the decode direction.

It is NOT true of the container itself. A .wem is a RIFF, and Wwise supports
uncompressed PCM as well as Vorbis. PCM needs no encoder at all - just the right
96 bytes in front of the samples.

WHAT IS VERIFIED, AND WHAT IS NOT (rule 8)
Verified: the shipped game decodes PCM .wem. A census of every .wem in
audio_1_general (4434) and audio_2_soundbanks (4796) found 127 files with
wFormatTag 0xFFFE - WAVE_FORMAT_EXTENSIBLE, 16-bit PCM - and the mod
LizziesBDs ships 116 more of them. A codec the shipped data uses is a codec the
shipped runtime has.

NOT verified: that PCM is accepted on the VOICEOVER path specifically. All 127
vanilla PCM files and all 116 of the mod's live under base\\sound\\soundbanks\\
media (bank media, streamed by id). Every custom voice line in all 24 installed
mods that ship a vomap - 342 files - is Vorbis. So no shipped example proves
PCM through the locVoiceoverMap external-source path, which is the one this
project uses. Both paths end in the same Wwise source reader dispatching on the
fmt tag, so it should hold, but "should" is not "does". This is a TODO under
rule 8: try it, and if the line is silent in game, the fallback is the Wwise
route in docs/voiceover.md, unchanged and still documented.

The failure mode if it does not work is exactly today's status quo - a subtitle
with no sound - so trying costs nothing but the rebuild.

THE FORMAT, read off the shipped files rather than a spec
Header is exactly 96 bytes, identical in vanilla and in the mod:

    0x00  "RIFF" u32 filesize-8  "WAVE"
    0x0c  "fmt " u32 24
          u16 0xFFFE   wFormatTag, WAVE_FORMAT_EXTENSIBLE
          u16 channels
          u32 sample rate
          u32 rate * channels * 2      nAvgBytesPerSec
          u16 channels * 2             nBlockAlign
          u16 16                       wBitsPerSample
          u16 6                        cbSize - Wwise's short extension
          u16 0                        reserved
          u32 AkChannelConfig          (mask << 12) | (type << 8) | channels
    0x2c  "hash" u32 16  <16 bytes>
    0x44  "junk" u32 12  <12 zero bytes>
    0x58  "data" u32 payload size
    0x60  interleaved signed 16-bit little-endian samples

The junk chunk is not filler for its own sake: it is what puts the payload at
0x60, which is 16-byte aligned. Every shipped PCM file has it, at exactly this
size, so it is reproduced rather than dropped.

AkChannelConfig confirmed against all 127 vanilla files: 1ch 0x4101 (mask 0x4,
front centre), 2ch 0x3102 (0x3, FL FR), 4ch 0x603104, 6ch 0x60F106. The low byte
is the channel count, the next nibble is 1 for a standard configuration, and the
rest is the speaker mask - so the number is not the mask and cannot be guessed
from the channel count alone.

The hash chunk is Wwise's own content hash from its conversion cache; the value
here does not reproduce it (MD5 of the payload was checked against a shipped
file and does not match). It is written as a deterministic MD5 of the samples
so a rebuild is reproducible and the field is never left looking uninitialised.
Nothing suggests the runtime reads it - the decoder needs fmt and data.

SIZE
48 kHz mono 16-bit is 96 KB per second, about 5x a Vorbis take. 43 lines at
roughly 4 seconds each is ~17 MB per locale. That is fine for a quest mod and
lossless, but --rate 24000 halves it, and the game itself ships plenty of
24 kHz voice lines (every holocall) if size ever matters more than fidelity.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_vomap import VO_LOCALES, split_stem

ROOT = pathlib.Path(__file__).resolve().parent.parent
# What a drop folder may hold besides .wem. Anything ffmpeg reads would work;
# this list is deliberately short so a stray file is a mistake, not an input.
SOURCES = (".wav", ".flac", ".ogg", ".mp3", ".m4a")

WAVE_FORMAT_EXTENSIBLE = 0xFFFE
# Speaker masks, in the order Wwise packs them. Only mono and stereo are ever
# wanted for dialogue; the rest are here because the census found them and a
# reader should not have to wonder what 0x60F106 was.
MASKS = {1: 0x4, 2: 0x3, 4: 0x603, 6: 0x60F}


def channel_config(channels):
    """The packed AkChannelConfig for a standard N-channel layout."""
    if channels not in MASKS:
        sys.exit(f"no known speaker mask for {channels} channels")
    return (MASKS[channels] << 12) | (1 << 8) | channels


def wem_bytes(pcm, channels, rate):
    """Wrap raw interleaved s16le samples in the 96-byte Wwise PCM header."""
    block = channels * 2
    if len(pcm) % block:
        # A partial frame would make nBlockAlign and the data size disagree,
        # which is the kind of thing a decoder reads straight off the end of.
        pcm = pcm[: len(pcm) - (len(pcm) % block)]

    fmt = struct.pack("<HHIIHHHHI",
                      WAVE_FORMAT_EXTENSIBLE, channels, rate,
                      rate * block, block, 16,
                      6, 0, channel_config(channels))
    assert len(fmt) == 24, len(fmt)

    body = (b"fmt " + struct.pack("<I", len(fmt)) + fmt
            + b"hash" + struct.pack("<I", 16) + hashlib.md5(pcm).digest()
            + b"junk" + struct.pack("<I", 12) + bytes(12)
            + b"data" + struct.pack("<I", len(pcm)) + pcm)
    out = b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body
    assert out.index(b"data") + 8 == 0x60, "payload must land 16-byte aligned"
    return out


def decode(src, rate, channels):
    """src -> raw s16le, via ffmpeg. Resampling and downmix happen here."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(src),
         "-f", "s16le", "-acodec", "pcm_s16le",
         "-ar", str(rate), "-ac", str(channels), "-"],
        capture_output=True)
    if r.returncode or not r.stdout:
        sys.exit(f"ffmpeg could not decode {src}:\n{r.stderr.decode(errors='replace').strip()}")
    return r.stdout


def convert(src, dst, rate, channels):
    dst.write_bytes(wem_bytes(decode(src, rate, channels), channels, rate))
    return dst.stat().st_size


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", type=pathlib.Path)
    ap.add_argument("dst", nargs="?", type=pathlib.Path)
    ap.add_argument("--rate", type=int, default=48000)
    ap.add_argument("--channels", type=int, default=1,
                    help="1 for dialogue - a voice line is mono in the game too")
    ap.add_argument("--force", action="store_true",
                    help="reconvert even when the .wem is newer than its source")
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is not installed - it decodes and resamples the input")

    if a.src:
        if not a.dst:
            ap.error("give an output path, or no arguments to sweep vo/")
        n = convert(a.src, a.dst, a.rate, a.channels)
        print(f"wrote {a.dst}  ({n} bytes, {a.channels}ch {a.rate} Hz PCM)")
        return

    # Sweep mode. The .wem lands beside its source so that gen_vomap.py keeps
    # globbing one folder and the drop-folder-is-the-manifest rule is untouched:
    # nothing downstream needs to know some .wem files were generated.
    # The name is checked BEFORE anything is written. gen_vomap.py would catch a
    # stem naming no line anyway, but only after this tool had already dropped a
    # .wem next to the bad .wav - and that .wem would still be sitting there,
    # still failing the build, after the .wav was renamed to something correct.
    keys = json.loads((ROOT / "source" / "subtitle_ids.json").read_text(encoding="utf-8"))
    keys.pop("_comment", None)

    made = skipped = kept = 0
    for locale in VO_LOCALES:
        d = ROOT / "vo" / locale
        if not d.is_dir():
            continue
        for src in sorted(p for p in d.iterdir() if p.suffix.lower() in SOURCES):
            key, _ = split_stem(src.stem)
            if key not in keys:
                sys.exit(f"vo/{locale}/{src.name} names no line in "
                         f"source/subtitle_ids.json (expected <scene>.<line id>"
                         f"[.f|.m]{src.suffix})")
            dst = src.with_suffix(".wem")
            if dst.exists() and not a.force:
                if dst.stat().st_mtime >= src.stat().st_mtime:
                    skipped += 1
                    continue
            n = convert(src, dst, a.rate, a.channels)
            made += 1
            print(f"  {src.relative_to(ROOT)} -> {dst.name}  ({n // 1024} KiB)")
        # Hand-made Wwise encodes are left exactly alone: a .wem with no source
        # beside it was not made here and must not be touched or counted.
        kept += sum(1 for p in d.glob("*.wem")
                    if not any(p.with_suffix(e).exists() for e in SOURCES))

    if made or skipped:
        print(f"wem: {made} converted, {skipped} already current, "
              f"{kept} hand-encoded left alone")
    else:
        print(f"wem: nothing to convert (drop {'/'.join(SOURCES)} into vo/<locale>/)")


if __name__ == "__main__":
    main()
