with import <nixpkgs> {};

let
  myPython = python3.withPackages(ps: [ps.trezor ps.pytest ps.flake8 ps.isort ps.black ps.Mako ps.munch ps.Pyro4 ps.pillow]);
in
  stdenv.mkDerivation {
    name = "trezor-core-dev";
    buildInputs = [ myPython protobuf scons gnumake gcc gcc-arm-embedded pkgconfig SDL2 SDL2_image autoflake ];
  }
