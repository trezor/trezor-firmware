# Trezor App Tool

`trezor-app-tool` supports the development workflow for Trezor external applications. It builds, packages, checks, and tests apps with the target, features, and artifacts required by Trezor firmware.

## Invocation

The tool is available in two development contexts.

### Standalone Application Repository

In a standalone external-app repository, enter the repository's Nix shell and run `app-tool` directly:

```sh
nix-shell
app-tool <command> [options]
```

Use `--package` when the repository contains more than one application. A single-app repository can omit it.

### Trezor Firmware Repository

From the `trezor-firmware` repository, run app-tool through `xtask`:

```sh
xtask apps <command> [options]
```

Use `--package` to select one or more external apps. Without it, the command operates on the applicable apps in the repository.

## Package Selection

`-p`, `--package <PACKAGE>` selects an app package. Repeat the option to work with multiple apps:

```sh
xtask apps build -p app-one -p app-two --model t3w1
```

## Commands

| Command | Purpose |
| --- | --- |
| `build` | Build and package external applications. |
| `check` | Type-check external applications. |
| `clippy` | Run Clippy checks. |
| `size` | Show binary size information. |
| `test` | Run Rust unit tests. |
| `device-test` | Run device tests against an emulator or physical device. |
| `fmt` | Format application sources and check formatting. |
| `clean` | Remove app build artifacts. |

Run `app-tool --help` or `xtask apps --help` to list commands, and append `--help` to a command for its complete options.

## Build

Builds the selected apps for hardware or the emulator, converts each ELF into a loadable app binary, and publishes the resulting artifacts. Every build also creates the app proofs and a RootPacket signed with development keys, which only non-production firmware accepts; `--production` does not change that yet. Use `--production` for a production build and `--debug` to use the debug firmware profile.

```sh
app-tool build [--package <PACKAGE>] --model <MODEL> [options]
xtask apps build [--package <PACKAGE>] --model <MODEL> [options]
```

## Check and Lint

`check` type-checks the selected apps without producing app artifacts. `clippy` runs the same target, feature, and profile configuration through Clippy. Pass the same target options that would be used for `build`.

```sh
app-tool check [--package <PACKAGE>] --model <MODEL> [options]
app-tool clippy [--package <PACKAGE>] --model <MODEL> [options]
```

## Size Analysis

Displays section sizes for the selected app binary using the requested target configuration. Build the app first so the binary is available for analysis. Requires `cargo-binutils` and the toolchain's `llvm-tools` component. The repository's nix shell provides both; with rustup, run `cargo install cargo-binutils` and `rustup component add llvm-tools`.

```sh
app-tool size [--package <PACKAGE>] --model <MODEL> [options]
```

## Rust Unit Tests

Runs host-side Rust unit tests with the selected model and language features. Use `-t`, `--test <TEST>` to run a specific test; without it, all package tests run.

```sh
app-tool test [--package <PACKAGE>] [options]
```

## Device Tests

Runs an app's Python device tests against an already-built artifact and a running emulator or reachable physical device. It does not start the emulator. Use `-t`, `--test <TEST>` to select a test, and `--ui [test|record]` to check UI screenshots against the app's fixtures or record them (`--ui` alone means `test`).

```sh
app-tool device-test [--package <PACKAGE>] --model <MODEL> [options]
```

## Formatting

Formats Rust sources, application translations, and Python files in each app's `tests/` directory. Pass `--check` to report formatting differences without changing files.

```sh
app-tool fmt [--package <PACKAGE>] [--check]
```

## Cleaning

Removes the build artifacts for the current app workspace.

```sh
app-tool clean
```

