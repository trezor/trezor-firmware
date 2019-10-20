import os
from collections import defaultdict

import pytest

from trezorlib import MINIMUM_FIRMWARE_VERSION, btc, debuglink, device
from trezorlib.tools import H_

MINIMUM_FIRMWARE_VERSION["1"] = (1, 0, 0)
MINIMUM_FIRMWARE_VERSION["T"] = (2, 0, 0)

try:
    from .emulator_wrapper import EmulatorWrapper
except ImportError:
    pass

# **** COMMON DEFINITIONS ****

MNEMONIC = " ".join(["all"] * 12)
PATH = [H_(44), H_(0), H_(0), 0, 0]
ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
LABEL = "test"
LANGUAGE = "english"
STRENGTH = 128

ROOT = os.path.dirname(os.path.abspath(__file__)) + "/../../"
LOCAL_BUILDS = {
    "core": ROOT + "core/build/unix/micropython",
    "legacy": ROOT + "legacy/firmware/trezor.elf",
}
BIN_DIR = os.path.dirname(os.path.abspath(__file__)) + "/emulators"


def check_version(tag, ver_emu):
    if tag.startswith("v") and len(tag.split(".")) == 3:
        assert tag == "v" + ".".join(["%d" % i for i in ver_emu])


def check_file(gen, tag):
    if tag.startswith("/"):
        filename = tag
    else:
        filename = "%s/trezor-emu-%s-%s" % (BIN_DIR, gen, tag)
    if not os.path.exists(filename):
        raise ValueError(filename + " not found. Do not forget to build firmware.")


def get_tags():
    files = os.listdir(BIN_DIR)
    if not files:
        raise ValueError(
            "No files found. Use download_emulators.sh to download emulators."
        )

    result = defaultdict(list)
    for f in sorted(files):
        try:
            _, _, gen, tag = f.split("-", maxsplit=3)
            result[gen].append(tag)
        except ValueError:
            pass
    return result


ALL_TAGS = get_tags()


def for_all(*args, minimum_version=(1, 0, 0)):
    if not args:
        args = ("core", "legacy")

    all_params = []
    for gen in args:
        try:
            to_tag = LOCAL_BUILDS[gen]
            from_tags = ALL_TAGS[gen] + [to_tag]
            for from_tag in from_tags:
                if from_tag.startswith("v"):
                    tag_version = tuple(int(n) for n in from_tag[1:].split("."))
                    if tag_version < minimum_version:
                        continue
                check_file(gen, from_tag)
                all_params.append((gen, from_tag, to_tag))
        except KeyError:
            pass

    return pytest.mark.parametrize("gen, from_tag, to_tag", all_params)


@for_all()
def test_upgrade_load(gen, from_tag, to_tag):
    def asserts(tag, client):
        check_version(tag, emu.client.version)
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.language == LANGUAGE
        assert btc.get_address(client, "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, from_tag) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client,
            mnemonic=MNEMONIC,
            pin="",
            passphrase_protection=False,
            label=LABEL,
            language=LANGUAGE,
        )
        device_id = emu.client.features.device_id
        asserts(from_tag, emu.client)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)


@for_all("legacy")
def test_upgrade_reset(gen, from_tag, to_tag):
    def asserts(tag, client):
        check_version(tag, emu.client.version)
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.language == LANGUAGE
        assert not client.features.needs_backup
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, from_tag) as emu:
        device.reset(
            emu.client,
            display_random=False,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            language=LANGUAGE,
        )
        device_id = emu.client.features.device_id
        asserts(from_tag, emu.client)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)


@for_all()
def test_upgrade_reset_skip_backup(gen, from_tag, to_tag):
    def asserts(tag, client):
        check_version(tag, emu.client.version)
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.language == LANGUAGE
        assert client.features.needs_backup
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, from_tag) as emu:
        device.reset(
            emu.client,
            display_random=False,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            language=LANGUAGE,
            skip_backup=True,
        )
        device_id = emu.client.features.device_id
        asserts(from_tag, emu.client)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)


@for_all(minimum_version=(1, 7, 2))
def test_upgrade_reset_no_backup(gen, from_tag, to_tag):
    def asserts(tag, client):
        check_version(tag, emu.client.version)
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.language == LANGUAGE
        assert not client.features.needs_backup
        assert not client.features.unfinished_backup
        assert client.features.no_backup

    with EmulatorWrapper(gen, from_tag) as emu:
        device.reset(
            emu.client,
            display_random=False,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            language=LANGUAGE,
            no_backup=True,
        )
        device_id = emu.client.features.device_id
        asserts(from_tag, emu.client)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)


if __name__ == "__main__":
    if not ALL_TAGS:
        print("No versions found. Remember to run download_emulators.sh")
    for k, v in ALL_TAGS.items():
        print("Found versions for {}:".format(k), v)
    print()
    print("Use `pytest {}` to run tests".format(__file__))
