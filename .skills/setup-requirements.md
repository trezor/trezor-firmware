# Setup Requirements

## Environment bootstrap (mandatory order)

```sh
# 1. Enter nix-shell from the repo root — provides all system deps (SDL2, protoc, Rust, clang, uv)
nix-shell

# 2. Inside nix-shell: install Python deps and activate
uv sync
source .venv/bin/activate
```

For embedded dev tools (OpenOCD, gcc-arm-embedded, gdb): `nix-shell --arg devTools true`

## Existing checkout

```sh
git submodule update --init --recursive --force
nix-shell
uv sync && source .venv/bin/activate
```
