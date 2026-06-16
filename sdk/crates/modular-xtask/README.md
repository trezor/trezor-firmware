# Modular App Build & Test Toolkit

This crate provides a robust workflow for building, testing, and analyzing modular applications—especially those targeting embedded hardware.
**Do not use pure Cargo for these tasks.**
Always use `cargo xtask ...` commands, as they create proper Cargo invocations and workflows, which can be quite complex.

---

## Prerequisites

- **Rust** (nightly, with `cargo-binutils`)
- **ARM binutils** (for cross-compilation)
- **Python** (for test orchestration and result processing)

> **Note:**
> While Nix is not a strict prerequisite, entering the provided Nix shell (`nix-shell`) will ensure all dependencies are available and correctly configured.

Additionally, the environment includes **uv** for Python-related tasks.
`uv` requires a `.venv` virtual environment to be created, but you do not need to activate it manually—`xtask` will call `uv run` commands as needed.

---

## Available Commands

All commands are invoked via:

```sh
cargo xtask <command> [options]
```

### Build

- Runs a series of steps:
  - `cargo build`
  - ELF postprocessing (to minimize loadable app size)
  - Size analysis of individual modules (HW targets only)
  - Publishing the final binary to the publish folder, i.e. `target/artifacts/<model>/<app.elf>`

### Other Cargo-like Commands

- `clean`, `clippy`, `fmt`, `check`

### Unit Tests

- Runs `cargo test` in the background
- Executes unit tests with SDK functionality replaced or mocked (e.g., crypto functions)

### Device Tests

- Runs device tests (currently only on emulator)
  - **A proper binary must be built prior to running device tests**
  - Emulator must match the modular app's language
  - Spawns `pytest` for all or specified tests
  - UI results can be shown/updated via Python scripts:
    - `show_results.py`
    - `update_results.py`

### Python Style & Checks

- Ensures consistent Python code style and catches obvious issues

---

## Usage

- List all commands:

  ```sh
  cargo xtask --help
  ```

- List options for a specific command:

  ```sh
  cargo xtask <command> --help
  ```

---

## Common Arguments

- `--project` (or `-p`): The workspace member (app) to build or test.
  **Note:** You should specify the application crate; do not build `xtask` itself.
- `--model` (e.g., `t3w1`, `t3t1`): Model-specific translations/definitions (e.g., tokens)
- `--lang`: Selects language for the binary
- `--log-level`: Sets the log level for the built firmware (e.g., `error`, `warn`, `info`, `debug`, `trace`)
- `--emulator`: Build or run for the emulator target instead of hardware
- `--debug`: Enables debug symbols, custom panic handler, and error context chaining
  **Note:** This significantly increases binary size and is not recommended for hardware (may cause insufficient memory).

---

## Notes

- For best results, use the provided Nix shell to ensure all dependencies are available and consistent.
- Device tests currently run only on the emulator.
- Python scripts are used for test orchestration and UI result processing.
- The Trezor SDK is currently a local dependency; you must provide the correct path to it.
- Running `cargo xtask clean` removes all workspace builds, including any builds performed by `xtask build`.

---

## Example

```sh
nix-shell
cargo xtask build -p funnycoin --model t3w1 --lang en --log-level trace --emulator
cargo xtask unit-tests -p funnycoin --model t3t1 --lang cs
cargo xtask clippy
cargo xtask device-tests -p funnycoin -m t3w1
cargo xtask py-style-check
```
