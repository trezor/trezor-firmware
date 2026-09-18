# App Build and Testing

This document covers what's needed to build and try out a modular app: getting a Trezor firmware build with external app support running in the emulator, then building the app itself against it.

## Prerequisite: Firmware with extapp Support

Testing a modular app requires a Trezor firmware build with external app loading enabled, running in the emulator.

From a Trezor nix environment, build the firmware with the `--apps` flag:

```sh
xtask build firmware -m t3w1 -e --apps -d
```

Then run the emulator:

```sh
uv run ./emu.py
```

## Building the App

With a Nix environment set up, build the app with:

```sh
cargo xtask build -e
```

> Temporary: when developing an app inside the `trezor-firmware` repo (e.g. under `sdk/apps`), use `xtask modular build -p <app-name>` instead. The rest is the same.

Besides the app binary, this build also generates the app's Merkle proof and the signed root packet needed to load it — both are written alongside the binary in the artifact directory, so no separate step is needed to produce them for device tests.

## Unit Tests

Unit tests cover isolated functions in the app and run on the host — compiled against the host triple, with the standard library available (see [Allocation](development.md#allocation) for how app code adapts to that) — rather than against real firmware.

Since there's no Core to talk to on the host, the SDK crate provides a mock SDK for this. Part of it is **functional** — e.g. the hash functions delegate to real software implementations — and part of it is only a **stub** that fakes success/failure without doing real work, most notably anything that would talk to Core over IPC. Keep that split in mind when writing or trusting a unit test: a passing test only tells you as much as the mock actually does.

Run unit tests with:

```sh
cargo xtask unit-tests -m t3w1 --lang en
```

Some tests check that the correct language and model were compiled in (see [Cargo Features](development.md#cargo-features)), so it's worth running more `-m`/`--lang` combinations than just one. For example, `test_model_t3w1` is gated behind `#[cfg(feature = "model_t3w1")]` and asserts that `model_t3w1` — and only `model_t3w1` — is enabled:

```rust
#[test]
#[cfg(feature = "model_t3w1")]
fn test_model_t3w1() {
    assert!(cfg!(feature = "model_t3w1"));
    assert!(!cfg!(feature = "model_t3t1"));
}
```

Run just that test with `-t`:

```sh
cargo xtask unit-tests -m t3w1 -t 'tests::test_model_t3w1'
```

## Device Tests

Device tests drive the app running against a real Trezor Core (in the emulator), through `trezorlib` — unlike unit tests, they exercise the actual wire protocol, UI, and Core services, not a host-side mock. They test real functionality: each test provides inputs, checks the results against expected outputs, and can also assert that a particular error is raised. There's more than one way to set this up; what follows is one way, based on how it's currently done in-repo (e.g. `sdk/apps/tron/tests`).

### Prerequisites

- A `uv` environment with `trezorlib` (to load and drive the app) and `pytest` (to run the tests) available.
- The app built and its emulator running — see [Prerequisite: Firmware with extapp Support](#prerequisite-firmware-with-extapp-support) and [Building the App](#building-the-app) above.

Everything described below lives in the app's `tests/` folder, but the commands themselves are run from the app root, alongside `Cargo.toml`.

Before running the tests for the first time, create the `uv` venv:

```sh
uv venv .venv
```

### Generated Protobuf

Device tests talk to the app using the same `.proto` message definitions as the app itself (see [Protobuf Messages](development.md#protobuf-messages)), but from Python via `trezorlib` rather than `prost`. The `protob/` folder ships a `pb2py` script and a `messages.py.mako` template that generate `trezorlib`-style Python message classes from the same `.proto` files. This is a separate, unrelated toolchain from the Rust build — nothing here feeds back into the app binary.

Run it before running the tests; the generated classes land in `tests/generated/`.

### Test Structure

- `conftest.py` — pytest fixtures and setup: connecting to the emulator, loading the app, and so on.
- `input_flows.py` / `common.py` — helper functions shared across test files. Input flows are layout-specific: they drive a test through the on-device UI — going forward, going back, confirming, cancelling, opening the menu, and so on. A good place to start reading to get your bearings on how the tests drive the app.
- `ui_tests/` — with UI testing enabled, each run's screenshots are recorded and compared against the already-recorded expected ones. A test can then fail for two independent reasons: the result doesn't match what was expected, or the recorded screenshots don't match.
- `test_<xx>.py` — the actual test cases.

### Running

With the app built and its emulator running:

```sh
cargo xtask device-tests -e -m t3w1
```

> The `-m`/`-e` flags must match the running build, or the artifact won't be found.

To run only certain tests:

```sh
cargo xtask device-tests -e -m t3w1 -t 'tests/test_xxx.py::test_name'
```

To view the UI results (also shown automatically at the end of a run):

```sh
uv run ./tests/show_results.py
```

If a UI diff is expected (e.g. a layout was intentionally changed), update the recorded screenshots with:

```sh
uv run ./tests/update_fixtures.py local
```

Alternatively, update tests one by one from the browser view opened by `show_results.py`.

### On Failure

If a test fails, rebuild the app with the [`debug`](development.md#cargo-features) feature to get a traceback instead of a bare error. This enables the [`ResultExt`](logging.md#2-use-the-resultext-trait) trait's `.c()` method, which wraps a `Result`'s error with its call-site location:

```rust
use sdk::ResultExt;

fn my_function() -> Result<(), Error> {
    some_operation().c()?;  // wraps error with file + line on failure
    Ok(())
}
```

It's also worth cutting down log noise: filter to just what's relevant, either at [build time](logging.md#build-time-filtering) or at [runtime via `trezorctl`](logging.md#runtime-filtering).
