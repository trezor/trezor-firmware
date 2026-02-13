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
if command -v nix-shell >/dev/null; then
  # Check if model has a tropic subdirectory (e.g., T3W1_tropic_on)
  TROPIC_DIR="tests/emulators/$MODEL/${MODEL}_tropic_on"
  if [ -d "$TROPIC_DIR" ]; then
    nix-shell --run "NIX_BINTOOLS=\$NIX_BINTOOLS_FOR_TARGET autoPatchelf $TROPIC_DIR"
  else
    nix-shell --run "NIX_BINTOOLS=\$NIX_BINTOOLS_FOR_TARGET autoPatchelf tests/emulators/$MODEL"
  fi
fi
