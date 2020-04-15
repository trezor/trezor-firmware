with import <nixpkgs> {};
stdenv.mkDerivation rec {
  name = "tpmb-arduino";
  buildInputs = [ arduino ];
}
