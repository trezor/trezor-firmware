# Build instructions

## Build instructions for Emulator (Unix port)

Run the following to checkout the project:

```sh
git clone --recursive https://github.com/trezor/trezor-core.git
cd trezor-core
```

If are building the already cloned the project, don't forget to use the following to refresh the submodules:

```sh
make vendor
```

### Linux

#### Debian/Ubuntu

```sh
sudo pip3 install --no-cache-dir pyblake2

sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install scons libsdl2-dev:i386 libsdl2-image-dev:i386 gcc-multilib

make build_unix
```

#### Fedora

```sh
sudo pip3 install --no-cache-dir pyblake2

sudo yum install scons SDL2-devel.i686 SDL2_image-devel.i686

make build_unix
```

#### openSUSE

```sh
sudo pip3 install --no-cache-dir pyblake2

sudo zypper install scons libSDL2-devel-32bit libSDL2_image-devel-32bit

make build_unix
```

#### Arch

```sh
sudo pip3 install --no-cache-dir pyblake2

sudo pacman -S gcc-multilib scons lib32-sdl2 lib32-sdl2_image

make build_unix
```

### OS X

```sh
pip3 install --no-cache-dir pyblake2

brew install scons sdl2 sdl2_image

make build_unix
```

### Windows

Not supported yet ...

## Build instructions for Embedded (ARM port)

### Linux

For flashing firmware to blank device (without bootloader) use `make flash`,
or `make flash STLINK_VER=v2-1` if using a ST-LINK/V2.1 interface.
You need to have OpenOCD installed.

#### Debian/Ubuntu

```sh
sudo pip3 install --no-cache-dir click pyblake2 scons
sudo pip3 install --no-deps git+https://github.com/trezor/python-trezor.git@master

sudo apt-get install gcc-arm-none-eabi libnewlib-arm-none-eabi

make vendor build_boardloader build_bootloader build_firmware
```

### OS X

1. Download [gcc-arm-none-eabi](https://launchpad.net/gcc-arm-embedded/5.0/5-2016-q3-update/)
2. Follow the [install instructions](https://launchpadlibrarian.net/287100883/readme.txt)
3. To install OpenOCD, run `brew install open-ocd`
4. Run `make vendor build_boardloader build_bootloader build_firmware`
