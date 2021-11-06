{ fullDeps ? false
, hardwareTest ? false
 }:

let
  # the last commit from master as of 2021-09-13
  rustOverlay = import (builtins.fetchTarball {
    url = "https://github.com/oxalica/rust-overlay/archive/9fd1c36484a844683153896f37d6fd28b365b931.tar.gz";
    sha256 = "1nylnc16y9jwjajvq2zj314lla2g16p77jhaj3vapfgq17n78i12";
  });
  # the last successful build of nixpkgs-unstable as of 2021-07-09
  nixpkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/7b4ff2184e4cab274ecb2b2eb49d20ef2142ddf1.tar.gz";
    sha256 = "1gdjm0qv5x9jx3zps7vz6yh10rkhmrbk7vf0b2hx5x6wi8yngfnb";
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
  rustStable = nixpkgs.rust-bin.stable."1.55.0".minimal.override {
    targets = [
      "thumbv7em-none-eabihf" # TT
      "thumbv7m-none-eabi"    # T1
    ];
    # we use rustfmt from nixpkgs because it's built with the nighly flag needed for wrap_comments
    # to use official binary, remove rustfmt from buildInputs and add it to extensions:
    extensions = [ "clippy" ];
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
  ] ++ lib.optionals (!stdenv.isDarwin || !stdenv.isAarch64) [
    gcc-arm-embedded  # not yet available for aarch64-darwin
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
  LIBCLANG_PATH = "${llvmPackages.libclang.lib}/lib";

  # don't try to use stack protector for Apple Silicon (emulator) binaries
  # it's broken at the moment
  hardeningDisable = lib.optionals (stdenv.isDarwin && stdenv.isAarch64) [ "stackprotector" ];

} // (lib.optionalAttrs fullDeps) {
  TREZOR_MONERO_TESTS_PATH = moneroTestsPatched;
})
