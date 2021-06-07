{ fullDeps ? false
, hardwareTest ? false
 }:

let
  rustOverlay = import (builtins.fetchTarball {
    url = "https://github.com/oxalica/rust-overlay/archive/4d5d8e4288a8e0efd074e56a448e450b0f8df975.tar.gz";
    sha256 = "1v3xlpna3q5klnhrn3p43bdh24ynaf31s2980r98ypvdpi2wi018";
  });
  # the last successful build of nixpkgs-unstable as of 2021-05-07
  nixpkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/e62feb3bf4a603e26755238303bda0c24651e155.tar.gz";
    sha256 = "1gkamm044jrksjrisr7h9grg8p2y6rk01x6391asrx988hm2rh9s";
  }) { overlays = [ rustOverlay ]; };
  moneroTests = nixpkgs.fetchurl {
    url = "https://github.com/ph4r05/monero/releases/download/v0.17.1.9-tests/trezor_tests";
    sha256 = "410bc4ff2ff1edc65e17f15b549bd1bf8a3776cf67abdea86aed52cf4bce8d9d";
  };
  moneroTestsPatched = nixpkgs.runCommandCC "monero_trezor_tests" {} ''
    cp ${moneroTests} $out
    chmod +wx $out
    ${nixpkgs.patchelf}/bin/patchelf --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" "$out"
    chmod -w $out
  '';
  rustStable = nixpkgs.rust-bin.stable."1.52.1".default.override {
    targets = [
      "thumbv7em-none-eabihf" # TT
      "thumbv7m-none-eabi"    # T1
    ];
  };
in
with nixpkgs;
stdenv.mkDerivation ({
  name = "trezor-firmware-env";
  buildInputs = lib.optionals fullDeps [
    # install other python versions for tox testing
    # NOTE: running e.g. "python3" in the shell runs the first version in the following list,
    #       and poetry uses the default version (currently 3.8)
    python38
    python39
    python37
    python36
  ] ++ [
    SDL2
    SDL2_image
    autoflake
    bash
    check
    clang-tools
    clang
    editorconfig-checker
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
    pkgconfig
    poetry
    protobuf3_6
    rustfmt
    rustStable
    wget
    zlib
    moreutils
  ] ++ lib.optionals (!stdenv.isDarwin) [
    procps
    valgrind
  ] ++ lib.optionals (stdenv.isDarwin) [
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
  ] ++ lib.optionals hardwareTest [
    uhubctl
    ffmpeg
    dejavu_fonts
  ];
  LD_LIBRARY_PATH = "${libffi}/lib:${libjpeg.out}/lib:${libusb1}/lib:${libressl.out}/lib";
  NIX_ENFORCE_PURITY = 0;

  # Fix bdist-wheel problem by setting source date epoch to a more recent date
  SOURCE_DATE_EPOCH = 1600000000;

  # Used by rust bindgen
  LIBCLANG_PATH = "${llvmPackages.libclang}/lib";
} // (lib.optionalAttrs fullDeps) {
  TREZOR_MONERO_TESTS_PATH = moneroTestsPatched;
})
