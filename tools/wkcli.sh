#!/bin/sh
# WolvenKit CLI wrapper for Location Studio build_* tools (they exec a single path).
DOTNET_ROLL_FORWARD=LatestMajor exec dotnet /mnt/sata/Cyberpunk2077/everything/WolvenKit/WolvenKit.CLI/bin/Release/net8.0/WolvenKit.CLI.dll "$@"
