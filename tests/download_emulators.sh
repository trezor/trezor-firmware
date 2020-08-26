#!/usr/bin/env bash
set -e

SITE="https://firmware.corp.sldev.cz/upgrade_tests/"
cd "$(dirname "$0")"

# download all emulators without index files, without directories and only if not present
wget -e robots=off --no-verbose --no-clobber --no-parent --cut-dirs=2 --no-host-directories --recursive --reject "index.html*" -P emulators/ $SITE

chmod u+x emulators/trezor-emu-*

# are we in Nix(OS)?
if command -v nix-shell >/dev/null; then
  nix-shell -p autoPatchelfHook SDL2 SDL2_image --run "autoPatchelf emulators/trezor-emu-*"
# remove NixOS specific interpreter
elif command -v patchelf >/dev/null; then
  patchelf --set-interpreter /lib64/ld-linux-x86-64.so.2 emulators/trezor-emu-*
else
  echo "Not on NixOS and patchelf not found: emulators probably have wrong ELF interpreter."
fi
