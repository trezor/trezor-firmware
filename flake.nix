{
  description = "Trezor Firmware development environment";

  inputs = {
    self.submodules = true;

    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    flake-utils.url = "github:numtide/flake-utils";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
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
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      monero-tests,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (system:
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
        mkBinOnlyWrapper = pkg:
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
        openocd-stm = pkgs.openocd.overrideAttrs (oldAttrs: {
          src = pkgs.fetchFromGitHub {
            owner = "STMicroelectronics";
            repo = "OpenOCD";
            rev = "openocd-cubeide-v1.13.0";
            sha256 = "a811402e19f0bfe496f6eecdc05ecea57f79a323879a810efaaff101cb0f420f";
          };
          version = "stm-cubeide-v1.13.0";
          nativeBuildInputs = oldAttrs.nativeBuildInputs ++ [ pkgs.autoreconfHook ];
        });
        moneroTestsPatched = pkgs.runCommandCC "monero_trezor_tests" { } ''
          cp ${monero-tests} $out
          chmod +wx $out
          ${pkgs.patchelf}/bin/patchelf \
          --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" \
          --add-rpath "${pkgs.udev}/lib" \
          "$out"
          chmod -w $out
        '';

        # uv2nix setup
        workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
        pyOverlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };
        editableOverlay = workspace.mkEditablePyprojectOverlay { root = "$REPO_ROOT"; };
        hacks = pkgs.callPackage pyproject-nix.build.hacks { };
        # https://pyproject-nix.github.io/uv2nix/overriding/index.html
        pyprojectOverrides = final: prev:
          {
            dbus-fast = prev.dbus-fast.overrideAttrs (old: {
              nativeBuildInputs = old.nativeBuildInputs ++ final.resolveBuildSystem { setuptools = [ ]; poetry-core = [ ]; };
            });
            libcst =
              (hacks.importCargoLock { prev = prev.libcst; cargoRoot = "native"; }).overrideAttrs (old: {
                nativeBuildInputs = old.nativeBuildInputs ++ final.resolveBuildSystem { setuptools = [ ]; setuptools-rust = [ ]; };
              });
          }
          // lib.genAttrs
            [ "crcmod" "demjson3" "docopt" "fido2" "markupsafe" "pyyaml" "pyyaml-ft" ]
            (pkgName: prev."${pkgName}".overrideAttrs (old: {
              nativeBuildInputs = old.nativeBuildInputs ++ final.resolveBuildSystem { setuptools = [ ]; };
            }));
        pythonSet = (pkgs.callPackage pyproject-nix.build.packages { python = pkgs.python3; }).overrideScope
          (lib.composeManyExtensions [
            pyproject-build-systems.overlays.wheel
            pyOverlay
            editableOverlay
            pyprojectOverrides
          ]);
        uv2NixVirtualenv = pythonSet.mkVirtualEnv "trezor-firmware-py-env" workspace.deps.all;

        mkShellFromParams =
          {
            fullDeps ? false,
            devTools ? false,
            useUv2Nix ? false,
          }:
          with pkgs;
          pkgs.mkShellNoCC ({
            name = "trezor-firmware-env";
            nativeBuildInputs = lib.optionals (!isDarwin) [ autoPatchelfHook ];
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
              # CI hardware tests:
              uhubctl
              socat
              ffmpeg_7-headless
              dejavu_fonts
            ]
            ++ lib.optionals (devTools && !isDarwin) [
              gdb
              kdePackages.kcachegrind
              nrfutil # compiled from source
              nrfconnect # compiled from source
            ]
            ++ lib.optionals useUv2Nix [
              uv2NixVirtualenv
            ];

            shellHook = lib.optionalString useUv2Nix ''
              # https://pyproject-nix.github.io/pyproject.nix/build.html#pythonpath-leaking-into-unrelated-builds
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
              source ${uv2NixVirtualenv}/bin/activate
            '';

            env = rec {
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
            // lib.optionalAttrs useUv2Nix {
              UV_PYTHON = pythonSet.python.interpreter;
              UV_NO_SYNC = 1;
            }
            // lib.optionalAttrs (fullDeps && !isDarwin) {
              # ~250MiB binary
              TREZOR_MONERO_TESTS_PATH = moneroTestsPatched;
            };
          });
      in
      {
        devShells = {
          # Only necessary dependencies for building and running tests in CI.
          minimal = mkShellFromParams { };
          minimal-uv2nix = mkShellFromParams { useUv2Nix = true; };

          # Includes various development and testing tools.
          default = mkShellFromParams { devTools = true; };
          default-uv2nix = mkShellFromParams {
            devTools = true;
            useUv2Nix = true;
          };

          # The default shell with additional large or slow to build dependencies.
          everything = mkShellFromParams {
            devTools = true;
            fullDeps = true;
          };
          everything-uv2nix = mkShellFromParams {
            devTools = true;
            fullDeps = true;
            useUv2Nix = true;
          };
        };
      }
    );
}
