with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "trezor-patch-emulators";
  buildInputs = [
    autoPatchelfHook
    SDL2
    SDL2_image
  ];
}
