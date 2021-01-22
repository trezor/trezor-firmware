# the last successful build of nixpkgs-unstable as of 2020-12-30
import (builtins.fetchTarball {
  url = "https://github.com/NixOS/nixpkgs/archive/bea44d5ebe332260aa34a1bd48250b6364527356.tar.gz";
  sha256 = "14sfk04iyvyh3jl1s2wayw1y077dwpk2d712nhjk1wwfjkdq03r3";
}) { }
