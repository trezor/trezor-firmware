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

from trezorlib import MINIMUM_FIRMWARE_VERSION, btc, debuglink, device, fido
from trezorlib.messages import BackupType
from trezorlib.tools import H_

from ..click_tests import recovery
from ..common import MNEMONIC_SLIP39_BASIC_20_3of6, MNEMONIC_SLIP39_BASIC_20_3of6_SECRET
from ..device_handler import BackgroundDeviceHandler
from ..emulators import ALL_TAGS, EmulatorWrapper
from . import for_all

MINIMUM_FIRMWARE_VERSION["1"] = (1, 0, 0)
MINIMUM_FIRMWARE_VERSION["T"] = (2, 0, 0)


# **** COMMON DEFINITIONS ****

MNEMONIC = " ".join(["all"] * 12)
PATH = [H_(44), H_(0), H_(0), 0, 0]
ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
LABEL = "test"
LANGUAGE = "en-US"
STRENGTH = 128


@for_all()
def test_upgrade_load(gen, tag):
    def asserts(client):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert btc.get_address(client, "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, tag) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client,
            mnemonic=MNEMONIC,
            pin="",
            passphrase_protection=False,
            label=LABEL,
            language=LANGUAGE,
        )
        device_id = emu.client.features.device_id
        asserts(emu.client)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert emu.client.features.language == LANGUAGE


@for_all("legacy")
def test_upgrade_reset(gen, tag):
    def asserts(client):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert not client.features.needs_backup
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, tag) as emu:
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
        asserts(emu.client)
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert emu.client.features.language == LANGUAGE
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


@for_all()
def test_upgrade_reset_skip_backup(gen, tag):
    def asserts(client):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.needs_backup
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, tag) as emu:
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
        asserts(emu.client)
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert emu.client.features.language == LANGUAGE
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


@for_all(legacy_minimum_version=(1, 7, 2))
def test_upgrade_reset_no_backup(gen, tag):
    def asserts(client):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert not client.features.needs_backup
        assert not client.features.unfinished_backup
        assert client.features.no_backup

    with EmulatorWrapper(gen, tag) as emu:
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
        asserts(emu.client)
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert emu.client.features.language == LANGUAGE
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


# Although Shamir was introduced in 2.1.2 already, the debug instrumentation was not present until 2.1.9.
@for_all("core", core_minimum_version=(2, 1, 9))
def test_upgrade_shamir_recovery(gen, tag):
    with EmulatorWrapper(gen, tag) as emu, BackgroundDeviceHandler(
        emu.client
    ) as device_handler:
        assert emu.client.features.recovery_mode is False
        emu.client.watch_layout(True)
        debug = device_handler.debuglink()

        device_handler.run(device.recover, pin_protection=False)

        recovery.confirm_recovery(debug)
        recovery.select_number_of_words(debug)
        layout = recovery.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[0])
        assert "2 more shares" in layout.text

        device_id = emu.client.features.device_id
        storage = emu.get_storage()
        device_handler.check_finalize()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        assert emu.client.features.recovery_mode
        debug = emu.client.debug
        emu.client.watch_layout(True)

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


@for_all(legacy_minimum_version=(1, 8, 4), core_minimum_version=(2, 1, 9))
def test_upgrade_u2f(gen, tag):
    """Check U2F counter stayed the same after an upgrade."""
    with EmulatorWrapper(gen, tag) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client,
            mnemonic=MNEMONIC,
            pin="",
            passphrase_protection=False,
            label=LABEL,
        )

        success = fido.set_counter(emu.client, 10)
        assert "U2F counter set" in success

        counter = fido.get_next_counter(emu.client)
        assert counter == 11
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        counter = fido.get_next_counter(emu.client)
        assert counter == 12


if __name__ == "__main__":
    if not ALL_TAGS:
        print("No versions found. Remember to run download_emulators.sh")
    for k, v in ALL_TAGS.items():
        print("Found versions for {}:".format(k), v)
    print()
    print("Use `pytest {}` to run tests".format(__file__))
