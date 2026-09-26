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

## Nix flakes

[Flakes](https://nixos.wiki/wiki/flakes) are experimental yet widely used feature of the Nix package manager. If you prefer you can use the associated tooling instead of `nix-shell`.

| Classic `nix-shell`                                                  | Flakes equivalent                                          |
| -------------------------------------------------------------------- | ---------------------------------------------------------- |
| `nix-shell`                                                          | `nix develop`                                              |
| `nix-shell --run "uv run bash"`                                      | `nix develop --command uv run bash`                        |
| `nix-shell --arg fullDeps true --run "uv run make -C core test_emu"` | `nix develop .#everything -c uv run make -C core test_emu` |

Note that as of 2026 flakes need to be enabled in `nix.conf`:

```
experimental-features = nix-command flakes
```
