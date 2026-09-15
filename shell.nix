{
  fullDeps ? false,
  hardwareTest ? false,
  devTools ? false,
  ...
}:
let
  whichShell =
    if fullDeps then
      "everything"
    else if devTools || hardwareTest then
      "default"
    else
      "minimal";
in
(import (
  let
    lock = builtins.fromJSON (builtins.readFile ./flake.lock);
    nodeName = lock.nodes.root.inputs.flake-compat;
  in
  fetchTarball {
    url =
      lock.nodes.${nodeName}.locked.url
        or "https://github.com/NixOS/flake-compat/archive/${lock.nodes.${nodeName}.locked.rev}.tar.gz";
    sha256 = lock.nodes.${nodeName}.locked.narHash;
  }
) { src = ./.; }).outputs.devShells."${builtins.currentSystem}"."${whichShell}"
