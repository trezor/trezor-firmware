{ pkgs, stdenv, lib, ... }:

let

  packageName = with lib; concatStrings (map (entry: (concatStrings (mapAttrsToList (key: value: "${key}-${value}") entry))) (importJSON ./package.json));

  nodePackages = import ./node-composition.nix {
    inherit pkgs;
    inherit (stdenv.hostPlatform) system;
  };
in
nodePackages."${packageName}".override {
  meta = with lib; {
    description = "Type checker for the Python language";
    maintainers = with maintainers; [ mmilata ];
    license = licenses.mit;
  };
}
