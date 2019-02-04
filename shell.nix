with import <nixpkgs> {};

let
  myPython = python3.withPackages(p: [p.click p.graphviz p.trezor p.ed25519 p.pillow]) ;
in
  stdenv.mkDerivation {
    name = "trezor-common-dev";
    buildInputs = [ myPython python2Packages.demjson graphviz protobuf ];
  }
