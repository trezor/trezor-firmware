# the last successful build of nixos-unstable - 2020-07-01
with import (builtins.fetchTarball https://github.com/NixOS/nixpkgs/archive/55668eb671b915b49bcaaeec4518cc49d8de0a99.tar.gz) {};

stdenv.mkDerivation {
  name = "trezor-firmware-env";
  buildInputs = [
    SDL2
    SDL2_image
    autoflake
    bash
    check
    clang-tools
    gcc
    gcc-arm-embedded
    git
    gitAndTools.git-subrepo
    gnumake
    graphviz
    libffi
    libjpeg
    libusb1
    openssl
    pipenv
    pkgconfig
    poetry
    protobuf3_6
    valgrind
    wget
    zlib
  ] ++ stdenv.lib.optionals (!stdenv.isDarwin) [
    procps
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
  LD_LIBRARY_PATH = "${libffi}/lib:${libjpeg.out}/lib:${libusb1}/lib:${libressl.out}/lib";
  NIX_ENFORCE_PURITY = 0;
}
