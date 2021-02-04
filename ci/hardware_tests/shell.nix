with import ../nixpkgs.nix;

stdenv.mkDerivation rec {
  name = "trezor-firmware-hardware-tests";
  buildInputs = [
    (callPackage ./uhubctl.nix { }) # HACK FIXME replace this with just uhubctl once pinned version of nixpkgs is updated
    ffmpeg
    poetry
    libusb1
    dejavu_fonts
  ];
  LD_LIBRARY_PATH = "${libusb1}/lib";
  NIX_ENFORCE_PURITY = 0;
}
