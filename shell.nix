with import <nixpkgs> {};

let
  myPython = python36.withPackages(ps: [ps.trezor ps.pytest ps.flake8 ps.isort ps.black ps.Mako ps.munch]);
in
  stdenv.mkDerivation {
    name = "trezor-core-dev";
    buildInputs = [ myPython protobuf scons gnumake gcc gcc-arm-embedded-7 pkgconfig SDL2 SDL2_image autoflake ];
  }
