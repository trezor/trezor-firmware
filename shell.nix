{ fullDeps ? false
, hardwareTest ? false
, devTools ? false
 }:

let
  # the last commit from master as of 2024-11-21
  rustOverlay = import (builtins.fetchTarball {
    url = "https://github.com/oxalica/rust-overlay/archive/2d484c7a0db32f2700e253160bcd2aaa6cdca3ba.tar.gz";
    sha256 = "17b32lz7kc12l8fwg8kc7ma83b51105z0xp2j0lfnsjr9qqc5r2y";
  });
  # define this variable and devTools if you want nrf{util,connect}
  acceptJlink = builtins.getEnv "TREZOR_FIRMWARE_ACCEPT_JLINK_LICENSE" == "yes";
  # the last successful build of nixpkgs-unstable as of 2024-11-21
  nixpkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/5083ec887760adfe12af64830a66807423a859a7.tar.gz";
    sha256 = "0sr45csfh2ff8w7jpnkkgl22aa89sza4jlhs6wq0368dpmklsl8g";
  }) {
    config = {
      allowUnfree = acceptJlink;
      segger-jlink.acceptLicense = acceptJlink;
    };
    overlays = [ rustOverlay ];
  };
  oldNixpkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/c58e6fbf258df1572b535ac1868ec42faf7675dd.tar.gz";
    sha256 = "18pna0yinvdprhhcmhyanlgrmgf81nwpc0j2z9fy9mc8cqkx3937";
  }) { };
  moneroTests = nixpkgs.fetchurl {
    url = "https://github.com/ph4r05/monero/releases/download/v0.18.3.1-dev-tests-u18.04-01/trezor_tests";
    sha256 = "d8938679b69f53132ddacea1de4b38b225b06b37b3309aa17911cfbe09b70b4a";
  };
  moneroTestsPatched = nixpkgs.runCommandCC "monero_trezor_tests" {} ''
    cp ${moneroTests} $out
    chmod +wx $out
    ${nixpkgs.patchelf}/bin/patchelf \
      --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" \
      --add-rpath "${nixpkgs.udev}/lib" \
      "$out"
    chmod -w $out
  '';
  # do not expose rust's gcc: https://github.com/oxalica/rust-overlay/issues/70
  # Create a wrapper that only exposes $pkg/bin. This prevents pulling in
  # development deps, packages to a nix-shell. This is especially important
  # when packages are combined from different nixpkgs versions.
  mkBinOnlyWrapper = pkg:
    nixpkgs.runCommand "${pkg.pname}-${pkg.version}-bin" { inherit (pkg) meta; } ''
      mkdir -p "$out/bin"
      for bin in "${nixpkgs.lib.getBin pkg}/bin/"*; do
          ln -s "$bin" "$out/bin/"
      done
    '';
  # NOTE: don't forget to update Minimum Supported Rust Version in docs/core/build/emulator.md
  rustProfiles = nixpkgs.rust-bin.nightly."2024-01-21";
  rustNightly = rustProfiles.minimal.override {
    targets = [
      "thumbv7em-none-eabihf" # TT
      "thumbv7m-none-eabi"    # T1
    ];
    # we use rustfmt from nixpkgs because it's built with the nighly flag needed for wrap_comments
    # to use official binary, remove rustfmt from buildInputs and add it to extensions:
    extensions = [ "rust-src" "clippy" "rustfmt" ];
  };
  openocd-stm = (nixpkgs.openocd.overrideAttrs (oldAttrs: {
    src = nixpkgs.fetchFromGitHub {
      owner = "STMicroelectronics";
      repo = "OpenOCD";
      rev = "openocd-cubeide-v1.13.0";
      sha256 = "a811402e19f0bfe496f6eecdc05ecea57f79a323879a810efaaff101cb0f420f";
    };
    version = "stm-cubeide-v1.13.0";
    nativeBuildInputs = oldAttrs.nativeBuildInputs ++ [ nixpkgs.autoreconfHook ];
  }));
  llvmPackages = nixpkgs.llvmPackages_17;
  # see pyright/README.md for update procedure
  pyright = oldNixpkgs.callPackage ./ci/pyright {};
in
with nixpkgs;
stdenvNoCC.mkDerivation ({
  name = "trezor-firmware-env";
  buildInputs = lib.optionals fullDeps [
    bitcoind
    # install other python versions for tox testing
    # NOTE: running e.g. "python3" in the shell runs the first version in the following list,
    #       and poetry uses the default version (currently 3.10)
    python311
    python310
    python39
    oldNixpkgs.python38
  ] ++ [
    SDL2
    SDL2_image
    bash
    bloaty  # for binsize
    check
    crowdin-cli  # for translations
    curl  # for connect tests
    editorconfig-checker
    gcc-arm-embedded
    gcc14
    git
    gitAndTools.git-subrepo
    gnumake
    graphviz
    libffi
    libjpeg
    libusb1
    llvmPackages.clang
    openssl
    perl
    pkg-config
    poetry
    ps
    oldNixpkgs.protobuf3_19
    pyright
    (mkBinOnlyWrapper rustNightly)
    wget
    zlib
    moreutils
  ] ++ lib.optionals (!stdenv.isDarwin) [
    autoPatchelfHook
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
    tio
    ffmpeg_7-headless
    dejavu_fonts
  ] ++ lib.optionals devTools [
    shellcheck
    openocd-stm
  ] ++ lib.optionals (devTools && !stdenv.isDarwin) [
    gdb
    kcachegrind
  ] ++ lib.optionals (devTools && acceptJlink) [
    nrfutil
    nrfconnect
    nrf-command-line-tools
  ];
  LD_LIBRARY_PATH = "${libffi}/lib:${libjpeg.out}/lib:${libusb1}/lib:${libressl.out}/lib";
  DYLD_LIBRARY_PATH = "${libffi}/lib:${libjpeg.out}/lib:${libusb1}/lib:${libressl.out}/lib";
  NIX_ENFORCE_PURITY = 0;

  # Fix bdist-wheel problem by setting source date epoch to a more recent date
  SOURCE_DATE_EPOCH = 1600000000;

  # Used by rust bindgen
  LIBCLANG_PATH = "${llvmPackages.libclang.lib}/lib";

  # don't try to use stack protector for Apple Silicon (emulator) binaries
  # it's broken at the moment
  hardeningDisable = lib.optionals (stdenv.isDarwin && stdenv.isAarch64) [ "stackprotector" ];

  # Enabling rust-analyzer extension in VSCode
  RUST_SRC_PATH = "${rustProfiles.rust-src}/lib/rustlib/src/rust/library";

} // (lib.optionalAttrs fullDeps) {
  TREZOR_MONERO_TESTS_PATH = moneroTestsPatched;
})
