# Build instructions

## Build instructions for Emulator (Unix port)

Run the following to checkout the project:

```sh
git clone --recursive https://github.com/trezor/trezor-core.git
cd trezor-core
```

If you are building from an existing checkout, don't forget to use the following to refresh the submodules:

```sh
make vendor
```

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

* __Mac OS X__:

  ```sh
  brew install scons sdl2 sdl2_image
  ```

* __Windows__: not supported yet, sorry.

Run the build with:

```sh
make build_unix
```

Now you can start the emulator:

```sh
./emu.sh
```

## Build instructions for Embedded (ARM port)

### Requirements

You will need the GCC ARM toolchain for building and OpenOCD for flashing to a device.
You will also need Python dependencies for signing.

#### Debian/Ubuntu

```sh
sudo apt-get install scons gcc-arm-none-eabi libnewlib-arm-none-eabi
```

#### OS X

1. Download [gcc-arm-none-eabi](https://developer.arm.com/open-source/gnu-toolchain/gnu-rm/downloads)
2. Follow the [install instructions](https://launchpadlibrarian.net/287100883/readme.txt)
3. To install OpenOCD, run `brew install open-ocd`
4. Run `make vendor build_boardloader build_bootloader build_firmware`

### Building

```sh
sudo pip3 install pipenv
pipenv install
pipenv run make vendor build_boardloader build_bootloader build_firmware
```

### Uploading

Use `make upload` to upload the firmware to a production device (with a bootloader).

### Flashing

For flashing firmware to blank device (without bootloader) use `make flash`,
or `make flash STLINK_VER=v2-1` if using a ST-LINK/V2.1 interface.
You need to have OpenOCD installed.
