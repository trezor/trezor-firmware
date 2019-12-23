# Build

Run the following to checkout the project:

```sh
git clone --recursive https://github.com/trezor/trezor-firmware.git
cd trezor-firmware/core
```

If you are building from an existing checkout, don't forget to use the following to refresh the submodules:

```sh
make vendor
```

After this you will need to install some software dependencies based on what flavor of Core you want to build. You can either build the Emulator or the actual firmware running on ARM devices. Emulator (also called _unix_ port) is a unix version that can run on your computer. See [Emulator](../emulator/index.md) for more information.

## Pipenv

We use [Pipenv](https://docs.pipenv.org/en/latest/) to install and track Python dependencies. You need to install it, sync the packages and then use `pipenv run` for every command or enter `pipenv shell` before typing any commands.

```sh
sudo pip3 install pipenv
pipenv sync
```
