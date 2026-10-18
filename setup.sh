#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
if [ ! -d DragonFF ]; then git clone https://github.com/Parik27/DragonFF.git DragonFF; git -C DragonFF checkout --detach 54baca8ea2ed95fe5a86917f44399ce677379c59; fi
if [ ! -d gta4-webmap/converter ]; then git clone --filter=blob:none https://github.com/Infinity-Loops/GTA4Unity.git gta4-webmap/converter; git -C gta4-webmap/converter checkout --detach c107e46cf8ab4e3d42f9c0bf685f80bb732a3609; fi
dotnet build gta4-webmap/extractor/Gta4MapExtractor.csproj -c Release --nologo
