# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import pytest

from tests.emulator_tests.emulators import ALL_TAGS, EmulatorWrapper
from trezorlib import MINIMUM_FIRMWARE_VERSION, btc, debuglink, device
from trezorlib.tools import H_

from . import SELECTED_GENS

MINIMUM_FIRMWARE_VERSION["1"] = (1, 0, 0)
MINIMUM_FIRMWARE_VERSION["T"] = (2, 0, 0)


# **** COMMON DEFINITIONS ****

MNEMONIC = " ".join(["all"] * 12)
PATH = [H_(44), H_(0), H_(0), 0, 0]
ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
LABEL = "test"
LANGUAGE = "english"
STRENGTH = 128


def for_all(*args, minimum_version=(1, 0, 0)):
    if not args:
        args = ("core", "legacy")

    # If any gens were selected, use them. If none, select all.
    enabled_gens = SELECTED_GENS or args

    all_params = []
    for gen in args:
        if gen not in enabled_gens:
            continue
        try:
            to_tag = None
            from_tags = ALL_TAGS[gen] + [to_tag]
            for from_tag in from_tags:
                if from_tag is not None and from_tag.startswith("v"):
                    tag_version = tuple(int(n) for n in from_tag[1:].split("."))
                    if tag_version < minimum_version:
                        continue
                all_params.append((gen, from_tag, to_tag))
        except KeyError:
            pass

    if not all_params:
        return pytest.mark.skip("no versions are applicable")

    return pytest.mark.parametrize("gen, from_tag, to_tag", all_params)


@for_all()
def test_upgrade_load(gen, from_tag, to_tag):
    def asserts(tag, client):
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
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


@for_all()
def test_upgrade_reset_skip_backup(gen, from_tag, to_tag):
    def asserts(tag, client):
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
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


@for_all(minimum_version=(1, 7, 2))
def test_upgrade_reset_no_backup(gen, from_tag, to_tag):
    def asserts(tag, client):
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
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(to_tag, emu.client)
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


if __name__ == "__main__":
    if not ALL_TAGS:
        print("No versions found. Remember to run download_emulators.sh")
    for k, v in ALL_TAGS.items():
        print("Found versions for {}:".format(k), v)
    print()
    print("Use `pytest {}` to run tests".format(__file__))
