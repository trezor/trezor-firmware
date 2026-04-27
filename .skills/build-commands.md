# Build Commands

Assumes you are already inside `nix-shell` with the `uv` venv activated. All commands run from the repo root unless noted.

## Model identifiers

| `TREZOR_MODEL` | Device |
|---|---|
| `T1B1` | Trezor One |
| `T2T1` | Trezor Model T |
| `T2B1` | Trezor Safe 3 rev.A |
| `T3B1` | Trezor Safe 3 rev.B |
| `T3T1` | Trezor Safe 5 |
| `T3W1` | Trezor Safe 7 |

Default model when `TREZOR_MODEL` is unset is `T3W1` (set in `core/Makefile`).

## Emulator (Unix port)

```sh
cd core
make build_unix                          # default model
make build_unix TREZOR_MODEL=T3T1        # specific model
make build_unix_debug                    # debug build (no optimizations, for gdb/lldb)
```

Binary output: `core/build/unix/trezor-emu-core`

Run a fresh emulator without animations:
```sh
cd core
./emu.py -ea
```

## Firmware (embedded / ARM)

```sh
cd core
make vendor build_boardloader build_bootloader build_firmware
make build_firmware TREZOR_MODEL=T3T1    # specific model
```

Debug build (enables log output):
```sh
PYOPT=0 make build_firmware
```

## Useful make targets

```sh
make gen        # regenerate auto-generated files (protobuf, mocks, …) after source changes
make style      # apply all formatters: Python, Rust, C, protobuf (run after every code change)
make style_check  # check formatting without applying changes
```
