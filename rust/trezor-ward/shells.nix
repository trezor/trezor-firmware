# The dev shells of trezor-ward, for the flake of whichever repository holds the crate:
#
#   devShells = { ... } // import ./rust/trezor-ward/shells.nix { inherit pkgs; rust = ...; };
#
# `pkgs` has to carry oxalica's rust-overlay. `rust` is the toolchain to develop with, as the
# overlay's set of profiles, e.g. `pkgs.rust-bin.nightly."2026-03-16"`.
{ pkgs, rust }:
let
  # The oldest toolchain the crate promises to build with, as Cargo.toml declares it.
  msrv = (pkgs.lib.importTOML ./Cargo.toml).package.rust-version;

  # Where the verifier runs.
  embeddedTargets = [
    "thumbv8m.main-none-eabihf"
    "thumbv7em-none-eabihf"
    "thumbv7m-none-eabi"
  ];

  # Where the prover runs: in WebAssembly, where a browser loads the first target and the
  # tests run on the second, since the test harness needs a system interface, ...
  wasmTarget = "wasm32-unknown-unknown";
  wasmTestTarget = "wasm32-wasip1";
  # ... and natively, on the most common target of each desktop and mobile platform. A
  # toolchain has the target of the machine at hand in any case; it is listed all the same,
  # so that the list is whole on every machine.
  nativeTargets = [
    "x86_64-unknown-linux-gnu"
    "x86_64-pc-windows-msvc"
    "aarch64-apple-darwin"
    "aarch64-apple-ios"
    "aarch64-linux-android"
  ];
in
{
  # For working on the crate, under the toolchain passed in.
  ward = pkgs.mkShell {
    name = "trezor-ward-env";
    packages = [
      (rust.minimal.override {
        targets = embeddedTargets ++ [
          wasmTarget
          wasmTestTarget
        ];
        extensions = [
          "rust-src"
          "clippy"
          "rustfmt"
          "llvm-tools-preview" # what cargo-llvm-cov reads the coverage data with
        ];
      })
      pkgs.cargo-hack # every combination of features
      pkgs.cargo-llvm-cov # test coverage
      pkgs.wasmtime.out # runs the wasm32-wasip1 tests; only the binary, not the C API
    ];
  };

  # Nothing but the oldest supported toolchain, to check that promise. The prover's platforms
  # are only compiled with it, so the target that runs the WebAssembly tests is left out.
  ward-msrv = pkgs.mkShell {
    name = "trezor-ward-msrv-env";
    packages = [
      (pkgs.rust-bin.fromRustupToolchain {
        channel = msrv;
        profile = "minimal";
        targets = nativeTargets ++ [ wasmTarget ];
      })
      pkgs.cargo-hack
    ];
  };
}
