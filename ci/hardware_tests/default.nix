with import <nixpkgs> {};

stdenv.mkDerivation rec {
  name = "trezor-firmware-hardware-tests";
  buildInputs = [
    uhubctl
    ffmpeg
    pipenv
    libusb1
    dejavu_fonts
  ];
  LD_LIBRARY_PATH = "${libusb1}/lib";
  NIX_ENFORCE_PURITY = 0;
}
