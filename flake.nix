{
  description = "Trezor Firmware development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    flake-utils.url = "github:numtide/flake-utils";
    flake-compat = {
      url = "github:NixOS/flake-compat";
      flake = false;
    };
    monero-tests = {
      url = "https://github.com/ph4r05/monero/releases/download/v0.18.3.1-dev-tests-u18.04-01/trezor_tests";
      flake = false;
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      rust-overlay,
      flake-utils,
      monero-tests,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        overlays = [ (import rust-overlay) ];

        pkgs = import nixpkgs {
          inherit system overlays;
          config.allowUnfree = true;
          config.segger-jlink.acceptLicense = true;
        };
        lib = pkgs.lib;
        isDarwin = pkgs.stdenv.hostPlatform.isDarwin;

        # do not expose rust's gcc: https://github.com/oxalica/rust-overlay/issues/70
        # Create a wrapper that only exposes $pkg/bin. This prevents pulling in
        # development deps, packages to a nix-shell. This is especially important
        # when packages are combined from different nixpkgs versions.
        mkBinOnlyWrapper =
          pkg:
          pkgs.runCommand "${pkg.pname}-${pkg.version}-bin" { inherit (pkg) meta; } ''
            mkdir -p "$out/bin"
            for bin in "${pkgs.lib.getBin pkg}/bin/"*; do
                ln -s "$bin" "$out/bin/"
            done
          '';
        # NOTE: don't forget to update Minimum Supported Rust Version in docs/core/build/emulator.md
        rustProfiles = pkgs.rust-bin.nightly."2026-03-16";
        rustNightly = rustProfiles.minimal.override {
          targets = [
            "thumbv8m.main-none-eabihf" # T3
            "thumbv7em-none-eabihf" # T2
            "thumbv7m-none-eabi" # T1
          ];
          # we use rustfmt from nixpkgs because it's built with the nighly flag needed for wrap_comments
          # to use official binary, remove rustfmt from buildInputs and add it to extensions:
          extensions = [
            "rust-src"
            "clippy"
            "rustfmt"
          ];
        };
        openocd-stm = (
          pkgs.openocd.overrideAttrs (oldAttrs: {
            src = pkgs.fetchFromGitHub {
              owner = "STMicroelectronics";
              repo = "OpenOCD";
              rev = "openocd-cubeide-v1.13.0";
              sha256 = "a811402e19f0bfe496f6eecdc05ecea57f79a323879a810efaaff101cb0f420f";
            };
            version = "stm-cubeide-v1.13.0";
            nativeBuildInputs = oldAttrs.nativeBuildInputs ++ [ pkgs.autoreconfHook ];
          })
        );
        moneroTestsPatched = pkgs.runCommandCC "monero_trezor_tests" { } ''
          cp ${monero-tests} $out
          chmod +wx $out
          ${pkgs.patchelf}/bin/patchelf \
          --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" \
          --add-rpath "${pkgs.udev}/lib" \
          "$out"
          chmod -w $out
        '';

        mkShellFromParams =
          {
            fullDeps ? false,
            devTools ? false,
          }:
          with pkgs;
          pkgs.mkShellNoCC (
            rec {
              name = "trezor-firmware-env";
              nativeBuildInputs = lib.optionals (!isDarwin) [ pkgs.autoPatchelfHook ];
              buildInputs = [
                sdl3
                sdl3-image
                sdl2-compat # for running old emulators used in upgrade tests
                SDL2_image # for running old emulators used in upgrade tests
                bash
                bloaty # for binsize
                cargo-audit
                cargo-vet
                check
                curl # for connect tests
                editorconfig-checker
                gcc-arm-embedded-13
                gcc14
                git
                git-subrepo
                gnumake
                graphviz
                libffi
                libjpeg
                libusb1
                llvmPackages.clang
                openssl
                perl
                pkg-config
                ps
                protobuf_31 # version needs to be <= than the one in pyproject.toml
                pyright
                python3
                ruff
                (mkBinOnlyWrapper rustNightly)
                s5cmd # CI S3 upload
                sccache
                uv
                wget
                zlib
                moreutils
              ]
              ++ lib.optionals fullDeps [
                #bitcoind # for HWI tests which are currently disabled
              ]
              ++ lib.optionals (!isDarwin) [
                procps
                valgrind
              ]
              ++ lib.optionals (isDarwin) [
                libiconv
              ]
              ++ lib.optionals devTools [
                cmake
                ninja
                tio
                shellcheck
                crowdin-cli # for translations, pulls in openjdk
                openocd-stm # compiled from source
                nrfutil # compiled from source
                nrfconnect # compiled from source
                # CI hardware tests:
                uhubctl
                socat
                ffmpeg_7-headless
                dejavu_fonts
              ]
              ++ lib.optionals (devTools && !isDarwin) [
                gdb
                kdePackages.kcachegrind
              ];

              LD_LIBRARY_PATH = lib.makeLibraryPath [ libffi libjpeg libusb1 libressl ];
              DYLD_LIBRARY_PATH = LD_LIBRARY_PATH;

              # Fix bdist-wheel problem by setting source date epoch to a more recent date
              SOURCE_DATE_EPOCH = 1600000000;

              # Used by rust bindgen
              LIBCLANG_PATH = "${llvmPackages.libclang.lib}/lib";

              # Enabling rust-analyzer extension in VSCode
              RUST_SRC_PATH = "${rustProfiles.rust-src}/lib/rustlib/src/rust/library";

              # Avoid printing "Using udevCheckHook", there are no rules to check
              dontUdevCheck = 1;

              # Force uv to use the nix-provided Python instead of its own managed builds.
              # Without this, uv defaults to python-preference=managed + python-downloads=automatic,
              # silently downloading/reusing its own interpreter and ignoring python3 on PATH.
              UV_PYTHON_PREFERENCE = "only-system";
              UV_PYTHON_DOWNLOADS = "never";
            }
            // (lib.optionalAttrs fullDeps) {
              # ~250MiB binary
              TREZOR_MONERO_TESTS_PATH = moneroTestsPatched;
            }
          );
      in
      {
        devShells = {
          # Only necessary dependencies for building and running tests in CI.
          minimal = mkShellFromParams { };

          # Includes various development and testing tools.
          default = mkShellFromParams { devTools = true; };

          # The default shell with additional large or slow to build dependencies.
          everything = mkShellFromParams {
            devTools = true;
            fullDeps = true;
          };
        };
      }
    );
}
