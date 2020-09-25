# Build

## New Project

Run the following to checkout the project:

```sh
git clone --recurse-submodules https://github.com/trezor/trezor-firmware.git
cd trezor-firmware/core
```

After this you will need to install some software dependencies based on what flavor
of Core you want to build. You can either build the Emulator or the actual firmware
running on ARM devices. Emulator (also called _unix_ port) is a unix version that can
run on your computer. See [Emulator](../emulator/index.md) for more information.

## Existing Project

If you are building from an existing checkout, do not forget to refresh the submodules
 and the poetry environment:

```sh
git submodule update --init --recursive --force
poetry install
```

## Poetry

We use [Poetry](https://python-poetry.org/) to install and track Python dependencies. You need to install it, sync the packages and then use `poetry run` for every command or enter `poetry shell` before typing any commands. **The commands in this section suppose you are in a `poetry shell` environment!**

```sh
sudo pip3 install poetry
poetry install
poetry shell
```
