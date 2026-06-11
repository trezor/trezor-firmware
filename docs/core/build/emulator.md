# Build instructions for Emulator (Unix port)

> **Hint**:
Using emulator as described here is useful during firmware development. If you intend to use the emulator without modifying the firmware, you might be looking for [Trezor User Env](https://github.com/trezor/trezor-user-env/tree/master).

Complete the setup (nix-shell + uv) described in [index.md](index.md) before proceeding.

### Manual Requirements Installation

If you prefer not to use nix-shell, install the following dependencies manually:

* __Debian/Ubuntu__:

```sh
sudo apt-get install scons libsdl2-dev libsdl2-image-dev llvm-dev libclang-dev clang
```

* __Fedora__:

```sh
sudo yum install scons SDL2-devel SDL2_image-devel clang-devel
```

* __OpenSUSE__:

```sh
sudo zypper install scons libSDL2-devel libSDL2_image-devel
```

* __Arch__:

```sh
sudo pacman -S scons sdl2 sdl2_image clang-devel
```

* __Mac OS X__:

```sh
brew install scons sdl2 sdl2_image pkg-config llvm
```

* __Windows__: not supported yet, sorry.

You will also need the protocol buffer compiler `protoc`. [Follow the installation instructions for your system](https://grpc.io/docs/protoc-installation/).

And Rust (currently 1.96 nightly) via [`rustup`](https://rustup.rs/):

```sh
rustup default nightly
rustup update
```

The [bindgen crate](https://rust-lang.github.io/rust-bindgen/requirements.html) requires libclang for generating MicroPython FFI.

## Build

Most `xtask` commands require specifying the model via the `--model` or `-m` option. You can select one of the following models:

- `t2t1` - Model T
- `t3b1` - Trezor Safe 3
- `t3t1` - Trezor Safe 5
- `t3w1` - Trezor Safe 7

Run the build with:

```sh
xtask build firmware --emulator -m t2b1
```

## Run

Now you can start the emulator:

```sh
./emu.py
```

The emulator has a number of interesting features all documented in the [Emulator](../emulator/index.md) section.
