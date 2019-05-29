#!/usr/bin/env python3
import os

from emulator_wrapper import EmulatorWrapper
from trezorlib import btc, debuglink, device
from trezorlib.tools import H_

MNEMONIC = " ".join(["all"] * 12)
PATH = [H_(44), H_(0), H_(0), 0, 0]
ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
LABEL = "test"
LANGUAGE = "english"
STRENGTH = 128

ROOT = os.path.dirname(os.path.abspath(__file__)) + "/../../../../"
CORE_BUILD = ROOT + "core/build/unix/micropython"
LEGACY_BUILD = ROOT + "legacy/firmware/trezor.elf"


def check_version(tag, ver_emu):
    if tag.startswith("v") and len(tag.split(".")) == 3:
        assert tag == "v" + ".".join(["%d" % i for i in ver_emu])


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


def try_tags(gen, tags_from, tag_to):
    for v0 in tags_from + [tag_to]:
        v1 = tag_to
        print("[%s] %s => %s" % (gen, v0, v1))
        print("- test_upgrade_load")
        test_upgrade_load(gen, v0, v1)
        if gen != "core":
            print("- test_upgrade_reset")
            test_upgrade_reset(gen, v0, v1)
            print("- test_upgrade_reset_skip_backup")
            test_upgrade_reset(gen, v0, v1)
            print("- test_upgrade_reset_no_backup")
            test_upgrade_reset(gen, v0, v1)


# try_tags("core", ["v2.1.0"], CORE_BUILD)  TODO

try_tags(
    "legacy",
    ["v1.6.2", "v1.6.3", "v1.7.0", "v1.7.1", "v1.7.2", "v1.7.3", "v1.8.0", "v1.8.1"],
    LEGACY_BUILD,
)

print("ALL OK")
