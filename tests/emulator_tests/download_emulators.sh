#!/usr/bin/env bash
SITE="https://firmware.corp.sldev.cz/upgrade_tests/"
cd "$(dirname "$0")"

# download all emulators without index files, without directories and only if not present
wget -e robots=off --no-verbose --no-clobber --no-parent --cut-dirs=2 --no-host-directories --recursive --reject "index.html*" -P emulators/ $SITE

chmod u+x emulators/trezor-emu-*

if [ -f /etc/NIXOS ]; then
  cd emulators && nix-shell --run "autoPatchelf trezor-emu*"
fi
