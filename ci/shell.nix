# nixos-unstable from 2020-06-02
with import (builtins.fetchTarball https://github.com/NixOS/nixpkgs/archive/467ce5a9f45aaf96110b41eb863a56866e1c2c3c.tar.gz) {};

stdenv.mkDerivation {
  name = "trezor-firmware-env";
  buildInputs = [
    SDL2
    SDL2_image
    autoflake
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
    libressl
    libusb1
    pipenv
    pkgconfig
    protobuf3_6
    valgrind
    zlib
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
