{ fullDeps ? false }:

import ../shell.nix { inherit fullDeps; hardwareTest = true; }
