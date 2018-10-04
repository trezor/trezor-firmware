with import <nixpkgs> {};

let
  myPython = python36.withPackages(p: [p.trezor p.Mako p.munch]);
in
  stdenv.mkDerivation {
    name = "trezor-mcu-dev";
    buildInputs = [ myPython protobuf gnumake gcc gcc-arm-embedded-7 pkgconfig SDL2 SDL2_image ];
  }
