#!/usr/bin/env bash
set -e
if [ $# -lt 1 ]; then
  echo "Usage: $0 <model>"
  exit 1
fi

MODEL="$1"

cd "$(dirname "$0")"

# download emulators for the given model if not already present
uv run python download_emulators.py "$MODEL"

cd ..
# are we in Nix(OS)?
command -v nix-shell >/dev/null && nix-shell --run 'NIX_BINTOOLS=$NIX_BINTOOLS_FOR_TARGET autoPatchelf tests/emulators/$MODEL'
