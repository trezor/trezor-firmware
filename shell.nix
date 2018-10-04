with import <nixpkgs> {};

let
  myPython = python36.withPackages(ps: [ps.trezor ps.pytest]);
in
  stdenv.mkDerivation {
    name = "trezor-core-dev";
    buildInputs = [ myPython protobuf scons gnumake gcc gcc-arm-embedded-7 pkgconfig SDL2 SDL2_image ];
  }
