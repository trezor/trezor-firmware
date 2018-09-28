with import <nixpkgs> {};

let
  myPython = python36.withPackages(p: [p.trezor]);
in
  stdenv.mkDerivation {
    name = "trezor-core-dev";
    buildInputs = [ myPython protobuf scons gnumake gcc gcc-arm-embedded pkgconfig SDL2 SDL2_image ];
  }
