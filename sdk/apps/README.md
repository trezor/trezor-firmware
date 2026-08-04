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
xtask modular --help
```

## Commands

All commands require `-p <app>` to specify the target app (e.g. `-p ethereum`).

### Build

Emulator debug build with English language for T3W1 model:

```bash
xtask modular build -p ethereum -m t3w1 --lang en -d -e
```

### Other Commands

Available commands: `clippy`, `check`, `clean`, `fmt`

```bash
xtask modular <command> -p <app>
```

### Unit Tests

```bash
xtask modular unit-tests -p <app> -m <model> -t <test> [options]
```

See all available options:

```bash
xtask modular unit-tests --help
```

```bash
xtask modular unit-tests -p ethereum --lang en -m t3t1
```

### Device Tests

#### Emulator

##### Prerequisites

A running emulator with external app support enabled, with disabled animations, matching the target model.

##### Run

```bash
xtask modular device-tests -p <app> -m <model> -t <test> [options]
```

See all available options:

```bash
xtask modular device-tests --help
```

```bash
xtask modular device-tests -p ethereum -m t3w1 -e -t 'tests/test_getpublickey.py::test_getpublickey'
```

> The model and emulator flags must match the existing build, otherwise the artifact will not be found.

##### UI Results

Results are shown automatically at the end of each test run. To show them manually:

```bash
uv run ./sdk/apps/<app>/tests/show_results.py
```

#### Hardware

> **Note:** Hardware device testing is not yet supported (TODO).

#### Python Style

To check or fix the Python style (linter, imports, ...) of test files:

```bash
# Check
xtask modular py-style-check -p <app>

# Fix
xtask modular py-style -p <app>
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
xtask modular build -p ethereum -m t3w1 --lang en -d -e --log-level trace
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
