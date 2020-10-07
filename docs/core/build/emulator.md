# Build instructions for Emulator (Unix port)

First clone, initialize submodules, install Poetry and enter the Poetry shell as 
defined [here](index.md). **Do not forget you need to be in a `poetry shell`
environment!**

## Dependencies

Install the required packages, depending on your operating system.

* __Debian/Ubuntu__:

```sh
sudo apt-get install scons libsdl2-dev libsdl2-image-dev
```

* __Fedora__:

```sh
sudo yum install scons SDL2-devel SDL2_image-devel
```

* __OpenSUSE__:

```sh
sudo zypper install scons libSDL2-devel libSDL2_image-devel
```

* __Arch__:

```sh
sudo pacman -S scons sdl2 sdl2_image
```

* __NixOS__:

There is a `shell.nix` file in the root of the project. Just run the following **before** entering the `core` directory:

```sh
nix-shell
```

* __Mac OS X__:

_Consider using [Nix](https://nixos.org/download.html). With Nix all you need to do is `nix-shell`._

For other users:

```sh
brew install scons sdl2 sdl2_image pkg-config
```

* __Windows__: not supported yet, sorry.

## Build

Run the build with:

```sh
make build_unix
```

## Run

Now you can start the emulator:

```sh
./emu.py
```

The emulator has a number of interesting features all documented in the [Emulator](../emulator/index.md) section.

## Building for debugging and hacking in Emulator (Unix port)

Build the debuggable unix binary so you can attach the gdb or lldb.
This removes optimizations and reduces address space randomization.
Beware that this will significantly bloat the final binary
and the firmware runtime memory limit HEAPSIZE may have to be increased.

```sh
DEBUG_BUILD=1 make build_unix
```
