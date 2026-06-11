# Build

_Building for Trezor Model One? See the [legacy](../../legacy/index.md) documentation._

## Setup

Install [Nix](https://nix.dev/manual/nix/stable/installation/installing-binary) (provides the `nix-shell` command). All system dependencies are managed by it.

We use [uv](https://docs.astral.sh/uv/) to manage Python dependencies. It is installed automatically inside nix-shell.

**The recommended setup is to first enter nix-shell, then initialize the `uv` environment within it.**

## New Project

```sh
git clone --recurse-submodules https://github.com/trezor/trezor-firmware.git
cd trezor-firmware
nix-shell
uv sync
source .venv/bin/activate
```

## Existing Project

```sh
git submodule update --init --recursive --force
nix-shell
uv sync
source .venv/bin/activate
```

After completing setup, see [Emulator](emulator.md) or [Embedded](embedded.md) build instructions.
