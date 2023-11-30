{ fullDeps ? false
, hardwareTest ? false
, devTools ? false
 }:

let
  # the last commit from master as of 2023-04-14
  rustOverlay = import (builtins.fetchTarball {
    url = "https://github.com/oxalica/rust-overlay/archive/db7bf4a2dd295adeeaa809d36387098926a15487.tar.gz";
    sha256 = "0gk6kag09w8lyn9was8dpjgslxw5p81bx04379m9v6ky09kw482d";
  });
  # define this variable and devTools if you want nrf{util,connect}
  acceptJlink = builtins.getEnv "TREZOR_FIRMWARE_ACCEPT_JLINK_LICENSE" == "yes";
  # the last successful build of nixpkgs-unstable as of 2023-04-14
  nixpkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/c58e6fbf258df1572b535ac1868ec42faf7675dd.tar.gz";
    sha256 = "18pna0yinvdprhhcmhyanlgrmgf81nwpc0j2z9fy9mc8cqkx3937";
  }) {
    config = {
      allowUnfree = acceptJlink;
      segger-jlink.acceptLicense = acceptJlink;
    };
    overlays = [ rustOverlay ];
  };
  # commit before python36 was removed
  oldPythonNixpkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/b9126f77f553974c90ab65520eff6655415fc5f4.tar.gz";
    sha256 = "02s3qkb6kz3ndyx7rfndjbvp4vlwiqc42fxypn3g6jnc0v5jyz95";
  }) { };
  moneroTests = nixpkgs.fetchurl {
    url = "https://github.com/ph4r05/monero/releases/download/v0.18.1.1-dev-tests-u18.04-02/trezor_tests";
    sha256 = "81424cfc3965abdc24de573274bf631337b52fd25cefc895513214c613fe05c9";
  };
  moneroTestsPatched = nixpkgs.runCommandCC "monero_trezor_tests" {} ''
    cp ${moneroTests} $out
    chmod +wx $out
    ${nixpkgs.patchelf}/bin/patchelf --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" "$out"
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
  rustProfiles = nixpkgs.rust-bin.nightly."2023-04-14";
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
      rev = "openocd-cubeide-v1.12.0";
      sha256 = "7REQi9pcT6pn8yiAMpQpRQ+0ouMQelcciMAHyUonkVA=";
    };
    version = "stm-cubeide-v1.12.0";
    nativeBuildInputs = oldAttrs.nativeBuildInputs ++ [ nixpkgs.autoreconfHook ];

    # following two lines can be removed after bumping nixpkgs to newer than c58e6fbf258df1572b535ac1868ec42faf7675dd
    buildInputs = oldAttrs.buildInputs ++ [ nixpkgs.jimtcl nixpkgs.libjaylink ];
    configureFlags = oldAttrs.configureFlags ++ [ "--disable-internal-jimtcl" "--disable-internal-libjaylink" ];
  }));
  llvmPackages = nixpkgs.llvmPackages_14;
  # see pyright/README.md for update procedure
  pyright = nixpkgs.callPackage ./pyright {};
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
    python38
    oldPythonNixpkgs.python37
    oldPythonNixpkgs.python36
  ] ++ [
    SDL2
    SDL2_image
    bash
    bloaty  # for binsize
    check
    curl  # for connect tests
    editorconfig-checker
    gcc-arm-embedded
    git
    gitAndTools.git-subrepo
    gnumake
    graphviz
    libffi
    libjpeg
    libusb1
    llvmPackages.clang
    openssl
    pkgconfig
    poetry
    protobuf3_19
    pyright
    (mkBinOnlyWrapper rustNightly)
    wget
    zlib
    moreutils
  ] ++ lib.optionals (!stdenv.isDarwin) [
    autoPatchelfHook
    gcc11
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
  ] ++ lib.optionals devTools [
    shellcheck
    gdb
    openocd-stm
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
