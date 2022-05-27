{ pkgs, nodejs-14_x, stdenv, lib, ... }:

let

  packageName = with lib; concatStrings (map (entry: (concatStrings (mapAttrsToList (key: value: "${key}-${value}") entry))) (importJSON ./package.json));

  nodePackages = import ./node-composition.nix {
    inherit pkgs;
    inherit (stdenv.hostPlatform) system;
    # FIXME: drop after https://github.com/NixOS/nixpkgs/issues/145432 is fixed
    nodejs = nodejs-14_x;
  };
in
nodePackages."${packageName}".override {
  meta = with lib; {
    description = "Type checker for the Python language";
    maintainers = with maintainers; [ mmilata ];
    license = licenses.mit;
  };
}
