{ withEmulator ? false }:
let
  lock = builtins.fromJSON (builtins.readFile ../../flake.lock);
  nixpkgs = lock.nodes.nixpkgs.locked;
  pkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/${nixpkgs.rev}.tar.gz";
    sha256 = nixpkgs.narHash;
  }) {
    config.allowUnfree = true;
    config.android_sdk.accept_license = true;
  };
  android = pkgs.androidenv.composeAndroidPackages {
    toolsVersion = null;
    # SDL's Java sources are compiled against API 35, as in its Gradle project.
    platformVersions = [ "28" "35" ];
    buildToolsVersions = [ "35.0.0" ];
    includeNDK = true;
    ndkVersions = [ "28.2.13676358" ];
    includeEmulator = withEmulator;
    includeSystemImages = withEmulator;
    systemImageTypes = [ "default" ];
    abiVersions = [ "x86_64" ];
  };
  sdk = android.androidsdk;
in
pkgs.mkShell {
  inputsFrom = [ (import ../../shell.nix { }) ];
  packages = [ sdk android.platform-tools pkgs.jdk17_headless pkgs.unzip pkgs.zip ];
  ANDROID_HOME = "${sdk}/libexec/android-sdk";
  ANDROID_NDK_HOME = "${android.ndk-bundle}/libexec/android-sdk/ndk/28.2.13676358";
  SDL3_SOURCE = pkgs.applyPatches {
    name = "sdl3-headless-source";
    src = pkgs.sdl3.src;
    patches = [ ./sdl3-headless.patch ];
  };
  SDL3_IMAGE_SOURCE = pkgs.sdl3-image.src;
  LIBJPEG_SOURCE = pkgs.libjpeg_turbo.src;
  ANDROID_PKG_CONFIG = "${pkgs.pkg-config-unwrapped}/bin/pkg-config";
  # inputsFrom brings the main shell's packages, not its environment.
  LIBCLANG_PATH = "${pkgs.llvmPackages.libclang.lib}/lib";
  # Unlike the main shell, mkShell wraps the host compiler with hardening.
  # Its _FORTIFY_SOURCE breaks host tools built with -O0 -Werror (mpy-cross).
  hardeningDisable = [ "fortify" ];
}
