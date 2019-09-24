with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "trezor-firmware-dev";
  buildInputs = [
    SDL2
    SDL2_image
    autoflake
    check
    clang-tools
    gcc
    gcc-arm-embedded
    gnumake
    graphviz
    libusb1
    openssl
    pipenv
    pkgconfig
    protobuf
    scons
    valgrind
    zlib
  ];
  LD_LIBRARY_PATH="${libusb1}/lib";
  shellHook = ''
    pipenv shell
    exit
  '';
}
