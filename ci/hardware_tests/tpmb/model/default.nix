with import <nixpkgs> {};
stdenv.mkDerivation rec {
  name = "tpmb-model";
  buildInputs = [ openscad prusa-slicer ];
}
