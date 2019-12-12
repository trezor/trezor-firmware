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

from trezorlib import MINIMUM_FIRMWARE_VERSION, btc, debuglink, device, fido
from trezorlib.messages import BackupType
from trezorlib.tools import H_

from ..click_tests import recovery
from ..common import MNEMONIC_SLIP39_BASIC_20_3of6, MNEMONIC_SLIP39_BASIC_20_3of6_SECRET
from ..device_handler import BackgroundDeviceHandler
from ..emulators import ALL_TAGS, EmulatorWrapper
from . import SELECTED_GENS

MINIMUM_FIRMWARE_VERSION["1"] = (1, 0, 0)
MINIMUM_FIRMWARE_VERSION["T"] = (2, 0, 0)


# **** COMMON DEFINITIONS ****

MNEMONIC = " ".join(["all"] * 12)
PATH = [H_(44), H_(0), H_(0), 0, 0]
ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
LABEL = "test"
LANGUAGE = "en-US"
STRENGTH = 128


def for_all(*args, legacy_minimum_version=(1, 0, 0), core_minimum_version=(2, 0, 0)):
    if not args:
        args = ("core", "legacy")

    # If any gens were selected, use them. If none, select all.
    enabled_gens = SELECTED_GENS or args

    all_params = []
    for gen in args:
        if gen == "legacy":
            minimum_version = legacy_minimum_version
        elif gen == "core":
            minimum_version = core_minimum_version
        else:
            raise ValueError

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
        assert emu.client.features.language == LANGUAGE


@for_all("legacy")
def test_upgrade_reset(gen, from_tag, to_tag):
    def asserts(tag, client):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
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
        assert emu.client.features.language == LANGUAGE
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


@for_all()
def test_upgrade_reset_skip_backup(gen, from_tag, to_tag):
    def asserts(tag, client):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
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
        assert emu.client.features.language == LANGUAGE
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


@for_all(legacy_minimum_version=(1, 7, 2))
def test_upgrade_reset_no_backup(gen, from_tag, to_tag):
    def asserts(tag, client):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
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
        assert emu.client.features.language == LANGUAGE
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


# Although Shamir was introduced in 2.1.2 already, the debug instrumentation was not present until 2.1.9.
@for_all("core", core_minimum_version=(2, 1, 9))
def test_upgrade_shamir_recovery(gen, from_tag, to_tag):
    with EmulatorWrapper(gen, from_tag) as emu, BackgroundDeviceHandler(
        emu.client
    ) as device_handler:
        assert emu.client.features.recovery_mode is False
        debug = device_handler.debuglink()

        device_handler.run(device.recover, pin_protection=False)

        recovery.confirm_recovery(debug)
        recovery.select_number_of_words(debug)
        layout = recovery.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[0])
        assert "2 more shares" in layout.text

        device_id = emu.client.features.device_id
        storage = emu.storage()
        device_handler.check_finalize()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu, BackgroundDeviceHandler(
        emu.client
    ) as device_handler:
        assert device_id == emu.client.features.device_id
        assert emu.client.features.recovery_mode
        debug = device_handler.debuglink()

        # second share
        layout = recovery.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[2])
        assert "1 more share" in layout.text

        # last one
        layout = recovery.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[1])
        assert "You have successfully" in layout.text

        # Check the result
        state = debug.state()
        assert state.mnemonic_secret.hex() == MNEMONIC_SLIP39_BASIC_20_3of6_SECRET
        assert state.mnemonic_type == BackupType.Slip39_Basic
        device_handler.check_finalize()


@for_all(legacy_minimum_version=(1, 8, 4), core_minimum_version=(2, 1, 9))
def test_upgrade_u2f(gen, from_tag, to_tag):
    """
    Check U2F counter stayed the same after an upgrade.
    """
    with EmulatorWrapper(gen, from_tag) as emu:
        success = fido.set_counter(emu.client, 10)
        assert "U2F counter set" in success

        counter = fido.get_next_counter(emu.client)
        assert counter == 11
        storage = emu.storage()

    with EmulatorWrapper(gen, to_tag, storage=storage) as emu:
        counter = fido.get_next_counter(emu.client)
        assert counter == 12


if __name__ == "__main__":
    if not ALL_TAGS:
        print("No versions found. Remember to run download_emulators.sh")
    for k, v in ALL_TAGS.items():
        print("Found versions for {}:".format(k), v)
    print()
    print("Use `pytest {}` to run tests".format(__file__))
