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

import dataclasses
from typing import TYPE_CHECKING, List, Optional

import pytest
from shamir_mnemonic import shamir

from trezorlib import btc, debuglink, device, exceptions, fido, models
from trezorlib.messages import (
    ApplySettings,
    BackupAvailability,
    BackupType,
    RecoveryStatus,
    Success,
)
from trezorlib.tools import H_

from ..common import MNEMONIC_SLIP39_BASIC_20_3of6, MNEMONIC_SLIP39_BASIC_20_3of6_SECRET
from ..device_handler import BackgroundDeviceHandler
from ..emulators import ALL_TAGS, EmulatorWrapper
from ..input_flows import InputFlowSlip39BasicBackup
from . import for_all, for_tags, recovery_old, version_from_tag

if TYPE_CHECKING:
    from trezorlib.debuglink import TrezorClientDebugLink as Client

models.T1B1 = dataclasses.replace(models.T1B1, minimum_version=(1, 0, 0))
models.T2T1 = dataclasses.replace(models.T2T1, minimum_version=(2, 0, 0))
models.TREZOR_ONE = models.T1B1
models.TREZOR_T = models.T2T1
models.TREZORS = {models.T1B1, models.T2T1}

# **** COMMON DEFINITIONS ****

MNEMONIC = " ".join(["all"] * 12)
PATH = [H_(44), H_(0), H_(0), 0, 0]
ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
LABEL = "test"
STRENGTH = 128


@for_all()
def test_upgrade_load(gen: str, tag: str) -> None:
    def asserts(client: "Client"):
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
        )
        device_id = emu.client.features.device_id
        asserts(emu.client)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)


@for_all("legacy")
def test_upgrade_load_pin(gen: str, tag: str) -> None:
    PIN = "1234"

    def asserts(client: "Client") -> None:
        assert client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        client.use_pin_sequence([PIN])
        assert btc.get_address(client, "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, tag) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client,
            mnemonic=MNEMONIC,
            pin=PIN,
            passphrase_protection=False,
            label=LABEL,
        )
        device_id = emu.client.features.device_id
        asserts(emu.client)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)


# Test progressive upgrade of storage versions without unlocking in between.
# Legacy storage: until legacy-v1.7.3 (pre-norcow)
# Storage Version 0: until core-v2.0.9 (basic norcow)
# Storage Version 1: since legacy-v1.8.0 and core-v2.1.0 (encryption)
# Storage Version 2: since legacy-v1.9.0 and core-v2.3.0 (wipe code)
# Storage Version 3: since legacy-v1.10.0 and core-v2.4.0 (long PIN)
@for_tags(
    ("legacy", ["v1.7.0", "v1.8.0", "v1.9.0"]),
    ("legacy", ["v1.7.0", "v1.8.0"]),
    ("legacy", ["v1.7.0", "v1.9.0"]),
    ("legacy", ["v1.8.0", "v1.9.0"]),
)
def test_storage_upgrade_progressive(gen: str, tags: List[str]):
    PIN = "1234"

    def asserts(client: "Client") -> None:
        assert client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        client.use_pin_sequence([PIN])
        assert btc.get_address(client, "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, tags[0]) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client,
            mnemonic=MNEMONIC,
            pin=PIN,
            passphrase_protection=False,
            label=LABEL,
        )
        device_id = emu.client.features.device_id
        asserts(emu.client)
        storage = emu.get_storage()

    for tag in tags[1:]:
        with EmulatorWrapper(gen, tag, storage=storage) as emu:
            storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)


@for_all("legacy", legacy_minimum_version=(1, 9, 0))
def test_upgrade_wipe_code(gen: str, tag: str):
    PIN = "1234"
    WIPE_CODE = "4321"

    def asserts(client: "Client"):
        assert client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        client.use_pin_sequence([PIN])
        assert btc.get_address(client, "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, tag) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client,
            mnemonic=MNEMONIC,
            pin=PIN,
            passphrase_protection=False,
            label=LABEL,
        )

        # Set wipe code.
        emu.client.use_pin_sequence([PIN, WIPE_CODE, WIPE_CODE])
        device.change_wipe_code(emu.client)

        device_id = emu.client.features.device_id
        asserts(emu.client)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)

        # Check that wipe code is set by changing the PIN to it.
        emu.client.use_pin_sequence([PIN, WIPE_CODE, WIPE_CODE])
        with pytest.raises(
            exceptions.TrezorFailure,
            match="The new PIN must be different from your wipe code",
        ):
            return device.change_pin(emu.client)


@for_all("legacy")
def test_upgrade_reset(gen: str, tag: str):
    def asserts(client: "Client"):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.backup_availability == BackupAvailability.NotAvailable
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, tag) as emu:
        device.setup(
            emu.client,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            entropy_check_count=0,
            backup_type=BackupType.Bip39,
        )
        device_id = emu.client.features.device_id
        asserts(emu.client)
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


@for_all()
def test_upgrade_reset_skip_backup(gen: str, tag: str):
    def asserts(client: "Client"):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.backup_availability == BackupAvailability.Required
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, tag) as emu:
        device.setup(
            emu.client,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            skip_backup=True,
            entropy_check_count=0,
            backup_type=BackupType.Bip39,
        )
        device_id = emu.client.features.device_id
        asserts(emu.client)
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


@for_all(legacy_minimum_version=(1, 7, 2))
def test_upgrade_reset_no_backup(gen: str, tag: str):
    def asserts(client: "Client"):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.backup_availability == BackupAvailability.NotAvailable
        assert not client.features.unfinished_backup
        assert client.features.no_backup

    with EmulatorWrapper(gen, tag) as emu:
        device.setup(
            emu.client,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            no_backup=True,
            entropy_check_count=0,
            backup_type=BackupType.Bip39,
        )

        device_id = emu.client.features.device_id
        asserts(emu.client)
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address


# Although Shamir was introduced in 2.1.2 already, the debug instrumentation was not present until 2.1.9.
@for_all("core", core_minimum_version=(2, 1, 9))
def test_upgrade_shamir_recovery(gen: str, tag: Optional[str]):
    with EmulatorWrapper(gen, tag) as emu, BackgroundDeviceHandler(
        emu.client
    ) as device_handler:
        assert emu.client.features.recovery_status == RecoveryStatus.Nothing
        emu.client.watch_layout(True)
        debug = device_handler.debuglink()

        device_handler.run(device.recover, pin_protection=False)

        recovery_old.confirm_recovery(debug)
        recovery_old.select_number_of_words(debug)
        layout = recovery_old.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[0])
        if not debug.legacy_ui and not debug.legacy_debug:
            assert (
                "1 of 3 shares entered" in layout.text_content()
                or "2 more shares" in layout.text_content()
            )

        device_id = emu.client.features.device_id
        storage = emu.get_storage()
        device_handler.check_finalize()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        assert emu.client.features.recovery_status == RecoveryStatus.Recovery
        debug = emu.client.debug
        emu.client.watch_layout(True)

        # second share
        layout = recovery_old.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[2])
        assert (
            "2 of 3 shares entered" in layout.text_content()
            or "1 more share" in layout.text_content()
        )

        # last one
        layout = recovery_old.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[1])
        assert (
            "Wallet recovery completed" in layout.text_content()
            or "finished recovering" in layout.text_content()
        )

        # Check the result
        state = debug.state()
        assert state.mnemonic_secret is not None
        assert state.mnemonic_secret.hex() == MNEMONIC_SLIP39_BASIC_20_3of6_SECRET
        assert state.mnemonic_type == BackupType.Slip39_Basic


@for_all("core", core_minimum_version=(2, 1, 9))
def test_upgrade_shamir_backup(gen: str, tag: Optional[str]):
    with EmulatorWrapper(gen, tag) as emu:
        # Generate a new encrypted master secret and record it.
        device.setup(
            emu.client,
            pin_protection=False,
            skip_backup=True,
            backup_type=BackupType.Slip39_Basic,
            entropy_check_count=0,
        )
        device_id = emu.client.features.device_id
        backup_type = emu.client.features.backup_type
        mnemonic_secret = emu.client.debug.state().mnemonic_secret

        # Set passphrase_source = HOST.
        resp = emu.client.call(ApplySettings(_passphrase_source=2, use_passphrase=True))
        assert isinstance(resp, Success)

        # Get a passphrase-less and a passphrased address.
        address = btc.get_address(emu.client, "Bitcoin", PATH)
        emu.client.init_device(new_session=True)
        emu.client.use_passphrase("TREZOR")
        address_passphrase = btc.get_address(emu.client, "Bitcoin", PATH)

        assert emu.client.features.backup_availability == BackupAvailability.Required
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert emu.client.features.device_id == device_id

        # Create a backup of the encrypted master secret.
        assert emu.client.features.backup_availability == BackupAvailability.Required
        with emu.client:
            IF = InputFlowSlip39BasicBackup(emu.client, False)
            emu.client.set_input_flow(IF.get())
            device.backup(emu.client)
        assert (
            emu.client.features.backup_availability == BackupAvailability.NotAvailable
        )

        # Check the backup type.
        assert emu.client.features.backup_type == backup_type
        tag_version = version_from_tag(tag)
        if tag_version is not None:
            assert (
                backup_type == BackupType.Slip39_Basic
                if tag_version < (2, 7, 1)
                else BackupType.Slip39_Basic_Extendable
            )

        # Check that the backup contains the originally generated encrypted master secret.
        groups = shamir.decode_mnemonics(IF.mnemonics[:3])
        ems = shamir.recover_ems(groups)
        assert ems.ciphertext == mnemonic_secret

        # Check that addresses are the same after firmware upgrade and backup.
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address
        emu.client.init_device(new_session=True)
        emu.client.use_passphrase("TREZOR")
        assert btc.get_address(emu.client, "Bitcoin", PATH) == address_passphrase


@for_all(legacy_minimum_version=(1, 8, 4), core_minimum_version=(2, 1, 9))
def test_upgrade_u2f(gen: str, tag: str):
    """Check U2F counter stayed the same after an upgrade."""
    with EmulatorWrapper(gen, tag) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client,
            mnemonic=MNEMONIC,
            pin="",
            passphrase_protection=False,
            label=LABEL,
        )

        fido.set_counter(emu.client, 10)

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
        print(f"Found versions for {k}: {v}")
    print()
    print(f"Use `pytest {__file__}` to run tests")
