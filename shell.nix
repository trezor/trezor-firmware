with import <nixpkgs> {};

let
  MyPython = python3.withPackages(ps: [
    ps.Mako
    ps.Pyro4
    ps.black
    ps.ed25519
    ps.flake8
    ps.graphviz
    ps.isort
    ps.mock
    ps.munch
    ps.pillow
    ps.pytest
    ps.trezor
  ]);
in
  stdenv.mkDerivation {
    name = "trezor-firmware-dev";
    buildInputs = [
      MyPython
      SDL2
      SDL2_image
      autoflake
      check
      clang-tools
      gcc
      gcc-arm-embedded
      gnumake
      graphviz
      openssl
      pkgconfig
      protobuf
      python2Packages.demjson
      scons
      valgrind
    ];
  }
