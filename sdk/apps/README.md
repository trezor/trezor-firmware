# Trezor Modular Apps

Modular apps developed by Trezor that can be loaded and run on Trezor firmware.

## Prerequisites

Same as for the firmware in general — Nix shell, uv virtual environment, and the Trezor VS Code extension(not required but highly recommended).

## Configuration

| Option        | Description         | Example        |
|---------------|---------------------|----------------|
| `model`       | Target Trezor model | `t3w1`         |
| `lang`        | Firmware language   | `en`, `cs`     |
| `debug`       | Enable debug build  |                |
| `emulator`    | Build for emulator  |                |
| `log-level`   | Set log verbosity   | `debug`, `info`|

See all available options:

```bash
cargo app-tool --help
```

## Commands

All commands are run from the `sdk/apps` directory as `cargo app-tool <command>` (a cargo alias defined in `sdk/apps/.cargo/config.toml`). From the repository root, `xtask apps <command>` does the same.

Commands accept `-p <app>` to select the target app (e.g. `-p ethereum`); it may be repeated. Without `-p`, every app in the workspace is processed. Device tests run a single app, so they need `-p` whenever the workspace contains more than one.

### Build

Emulator debug build with English language for T3W1 model:

```bash
cargo app-tool build -p ethereum -m t3w1 --lang en -d -e
```

Besides the app image (`<app>.elf`), the build writes everything needed to load the app into the artifact directory: the app's Merkle proof (`<app>.proof`) and the timestamped, dev-signed root packet of the app's ring (`rootpacket_0-timestamped-signed.tmr` for ring 0, `rootpacket_12-timestamped-signed.tmr` for rings 1 and 2).

The proofs cover all apps published for the model, so every build refreshes the whole artifact directory. Production builds (`--production`) are skipped, as they need a production-signed root packet.

### Other Commands

Available commands: `clippy`, `check`, `size`, `clean`, `fmt`

```bash
cargo app-tool <command> -p <app>
```

### Unit Tests

```bash
cargo app-tool test -p <app> -m <model> -t <test> [options]
```

See all available options:

```bash
cargo app-tool test --help
```

```bash
cargo app-tool test -p ethereum --lang en -m t3t1
```

### Device Tests

#### Emulator

##### Prerequisites

A running emulator with external app support enabled, with disabled animations, matching the target model.

##### Run

```bash
cargo app-tool device-test -p <app> -m <model> -t <test> [options]
```

See all available options:

```bash
cargo app-tool device-test --help
```

```bash
cargo app-tool device-test -p ethereum -m t3w1 -e -t 'tests/test_getpublickey.py::test_getpublickey'
```

> The model and emulator flags must match the existing build, otherwise the artifact will not be found.

##### UI Results

Results are shown automatically at the end of each test run. To show them manually:

```bash
uv run ./sdk/apps/<app>/tests/show_results.py
```

#### Hardware

> **Note:** Hardware device testing is not yet supported (TODO).

### Code Style

`fmt` formats the Rust sources, the Python tests (linter, imports, ...) and the translation files of the selected apps:

```bash
# Check
cargo app-tool fmt --check -p <app>

# Fix
cargo app-tool fmt -p <app>
```

## Debugging

### Trezor Firmware

Before debugging the app itself, it helps to have debug output from the firmware side.

Build the firmware with debug enabled and Python optimizations disabled.

> **Note:** If the firmware is built with frozen Python modules (default), any change to Python source files requires rebuilding the firmware. Building without frozen modules allows faster iteration during development but makes device tests considerably slower.

Then use the VS Code extension to start the debugger. You can customize the debug launch configuration at:

```
core/embed/xtask/tf-tools/debug/emu-firmware.json
```

For example, to disable animations, add:

```json
"environment": [
    {
        "name": "TREZOR_DISABLE_ANIMATION",
        "value": "1"
    }
]
```

For more verbose output from the debug link, decrease the log level in `core/src/trezor/log.py`:

```python
# Lower value = more messages; 0 gives maximum verbosity
# Be cautious — level 0 can produce a large amount of output
_min_level = 0
```

### Emulator

Enable debug build and set the log level:

```bash
cargo app-tool build -p ethereum -m t3w1 --lang en -d -e --log-level trace
```

Logs are printed directly to the terminal where the emulator is running.

Then use the Trezor Firmware VS Code extension to start the debugger.

You can customize the debug launch configuration at:

```
core/embed/xtask/tf-tools/debug/emu-firmware.json
```

For example, to disable animations:

```json
"environment": [
    {
        "name": "TREZOR_DISABLE_ANIMATION",
        "value": "1"
    }
]
```

### Hardware

> **Note:** Hardware debugging is not yet supported (TODO).
