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
  openssl
  pipenv
  pkgconfig
  protobuf
  python2Packages.demjson
  scons
  valgrind
  zlib
];
shellHook = ''
  pipenv shell
'';
}
