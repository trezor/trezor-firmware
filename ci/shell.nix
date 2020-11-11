{ fullDeps ? false }:

# the last successful build of nixos-20.09 (stable) as of 2020-10-11
with import
  (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/0b8799ecaaf0dc6b4c11583a3c96ca5b40fcfdfb.tar.gz";
    sha256 = "11m4aig6cv0zi3gbq2xn9by29cfvnsxgzf9qsvz67qr0yq29ryyz";
  })
{ };

let
  moneroTests = fetchurl {
    url = "https://github.com/ph4r05/monero/releases/download/v0.15.0.0-tests-u18.04-03/trezor_tests";
    sha256 = "1e5dfdb07de4ea46088f4a5bdb0d51f040fe479019efae30f76427eee6edb3f7";
  };
  moneroTestsPatched = runCommandCC "monero_trezor_tests" {} ''
    cp ${moneroTests} $out
    chmod +wx $out
    ${patchelf}/bin/patchelf --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" "$out"
    chmod -w $out
  '';
in
stdenv.mkDerivation ({
  name = "trezor-firmware-env";
  buildInputs = stdenv.lib.optionals fullDeps [
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

  # Fix bdist-wheel problem by setting source date epoch to a more recent date
  SOURCE_DATE_EPOCH = 1600000000;

} // (stdenv.lib.optionalAttrs fullDeps) {
  TREZOR_MONERO_TESTS_PATH = moneroTestsPatched;
})
