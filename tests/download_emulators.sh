#!/usr/bin/env bash
set -e

SITE="https://firmware.corp.sldev.cz/upgrade_tests/"
cd "$(dirname "$0")"

# download all emulators without index files, without directories and only if not present
wget -e robots=off --no-verbose --no-clobber --no-parent --cut-dirs=2 --no-host-directories --recursive --reject "index.html*" -P emulators/ $SITE

chmod u+x emulators/trezor-emu-*

if [ -f /etc/NIXOS ]; then
  # for this to work you need to run ./download_emulators.sh outside the main nix shell
  cd emulators && nix-shell --run "autoPatchelf trezor-emu*"
fi
