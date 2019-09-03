with import <nixpkgs> {};

let
  MyPython = python3.withPackages(ps: [
    ps.Mako
    ps.Pyro4
    ps.black
    ps.coverage
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
      gnumake
      graphviz
      openssl
      pipenv
      pkgconfig
      protobuf
      python2Packages.demjson
      scons
      valgrind
      zlib
    ] ++ stdenv.lib.optionals (!stdenv.isDarwin) [
      gcc-arm-embedded
    ] ++ stdenv.lib.optionals (stdenv.isDarwin) [
      darwin.apple_sdk.frameworks.CoreAudio
      darwin.apple_sdk.frameworks.AudioToolbox
      darwin.apple_sdk.frameworks.ForceFeedback
      darwin.apple_sdk.frameworks.CoreVideo
      darwin.apple_sdk.frameworks.Cocoa
      darwin.apple_sdk.frameworks.Carbon
      darwin.apple_sdk.frameworks.IOKit
      darwin.apple_sdk.frameworks.QuartzCore
      darwin.apple_sdk.frameworks.Metal
      darwin.libobjc
      libiconv
    ];
  }
