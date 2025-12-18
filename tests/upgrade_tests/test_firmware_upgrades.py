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
from __future__ import annotations

import dataclasses
import functools
from typing import TYPE_CHECKING, List

import pytest
from shamir_mnemonic import shamir

from trezorlib import btc, debuglink, device, exceptions, fido, messages, models
from trezorlib.cardano import get_public_key
from trezorlib.client import ProtocolVersion
from trezorlib.messages import (
    ApplySettings,
    BackupAvailability,
    BackupType,
    CardanoDerivationType,
    RecoveryStatus,
    Success,
)
from trezorlib.tools import H_, parse_path

from ..click_tests import recovery
from ..common import MNEMONIC_SLIP39_BASIC_20_3of6, MNEMONIC_SLIP39_BASIC_20_3of6_SECRET
from ..device_handler import BackgroundDeviceHandler
from ..emulators import ALL_TAGS, EmulatorWrapper
from ..input_flows import InputFlowSlip39BasicBackup
from . import for_all, for_tags, recovery_old, version_from_tag

if TYPE_CHECKING:
    from trezorlib.debuglink import TrezorClientDebugLink as Client
    from trezorlib.transport.session import Session

# **** COMMON DEFINITIONS ****

MNEMONIC = " ".join(["all"] * 12)
PATH = [H_(44), H_(0), H_(0), 0, 0]
ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
LABEL = "test"
STRENGTH = 128


def lower_models_minimum_version(func):
    """Lowers the minimum_version of models to suppress `OutdatedFirmwareError` in tests."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        original_trezors = models.ALL_MODELS.copy()
        original_t1b1 = models.T1B1
        original_t2t1 = models.T2T1

        models.T1B1 = dataclasses.replace(models.T1B1, minimum_version=(1, 0, 0))
        models.T2T1 = dataclasses.replace(models.T2T1, minimum_version=(2, 0, 0))
        models.TREZOR_ONE = models.T1B1
        models.TREZOR_T = models.T2T1
        models.ALL_MODELS = {models.T1B1, models.T2T1, models.T3W1}

        try:
            result = func(*args, **kwargs)
        finally:
            models.T1B1 = original_t1b1
            models.T2T1 = original_t2t1
            models.TREZOR_ONE = models.T1B1
            models.TREZOR_T = models.T2T1
            models.ALL_MODELS = original_trezors
        return result

    return wrapper


def _get_session(client: "Client", passphrase: str | object = "") -> "Session":
    if client.protocol_version != ProtocolVersion.V1:
        return client.get_session(passphrase=passphrase)
    if client.version >= (2, 3, 0):
        return client.get_session(passphrase=passphrase)

    from trezorlib.transport.session import SessionV1

    from ..common import TEST_ADDRESS_N

    session = SessionV1.new(client)
    resp = session.call_raw(
        messages.GetAddress(address_n=TEST_ADDRESS_N, coin_name="Testnet")
    )
    if isinstance(resp, messages.ButtonRequest):
        resp = session._callback_button(resp)
    if isinstance(resp, messages.PassphraseRequest):
        resp = session.call_raw(messages.PassphraseAck(passphrase=passphrase))
    if isinstance(resp, messages.Deprecated_PassphraseStateRequest):
        session.id = resp.state
        resp = session.call_raw(messages.Deprecated_PassphraseStateAck())
    while isinstance(resp, messages.ButtonRequest):
        resp = session._callback_button(resp)
    return session


@for_all()
@lower_models_minimum_version
def test_upgrade_load(
    gen: str,
    tag: str | None,
    model: str | None,
) -> None:
    def asserts(client: "Client"):
        client.refresh_features()
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert (
            btc.get_address(client.get_session(passphrase=""), "Bitcoin", PATH)
            == ADDRESS
        )

    with EmulatorWrapper(gen, tag, model) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client.get_seedless_session(),
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
@lower_models_minimum_version
def test_upgrade_load_pin(
    gen: str,
    tag: str | None,
    model: str | None,
) -> None:
    PIN = "1234"

    def asserts(client: "Client") -> None:
        assert client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        with client:
            client.use_pin_sequence([PIN])
            session = client.get_session()
            assert btc.get_address(session, "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, tag, model) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client.get_seedless_session(),
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
@lower_models_minimum_version
def test_storage_upgrade_progressive(gen: str, tags: List[str]):
    PIN = "1234"

    def asserts(client: "Client") -> None:
        assert client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        client.use_pin_sequence([PIN])
        assert btc.get_address(client.get_session(), "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, tags[0], model="T1B1") as emu:
        debuglink.load_device_by_mnemonic(
            emu.client.get_seedless_session(),
            mnemonic=MNEMONIC,
            pin=PIN,
            passphrase_protection=False,
            label=LABEL,
        )
        device_id = emu.client.features.device_id
        asserts(emu.client)
        storage = emu.get_storage()

    for tag in tags[1:]:
        with EmulatorWrapper(gen, tag, model="T1B1", storage=storage) as emu:
            storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)


@for_all("legacy", legacy_minimum_version=(1, 9, 0))
@lower_models_minimum_version
def test_upgrade_wipe_code(
    gen: str,
    tag: str | None,
    model: str | None,
):
    PIN = "1234"
    WIPE_CODE = "4321"

    def asserts(client: "Client"):
        assert client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        client.use_pin_sequence([PIN])
        assert btc.get_address(client.get_session(), "Bitcoin", PATH) == ADDRESS

    with EmulatorWrapper(gen, tag, model) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client.get_seedless_session(),
            mnemonic=MNEMONIC,
            pin=PIN,
            passphrase_protection=False,
            label=LABEL,
        )

        # Set wipe code.
        emu.client.use_pin_sequence([PIN, WIPE_CODE, WIPE_CODE])
        session = emu.client.get_seedless_session()
        session.refresh_features()
        device.change_wipe_code(session)

        device_id = emu.client.features.device_id
        asserts(emu.client)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)

        # Check that wipe code is set by changing the PIN to it.
        emu.client.use_pin_sequence([PIN, WIPE_CODE, WIPE_CODE])
        session = emu.client.get_seedless_session()
        session.refresh_features()
        with pytest.raises(
            exceptions.TrezorFailure,
            match="The new PIN must be different from your wipe code",
        ):
            return device.change_pin(session)


@for_all("legacy")
@lower_models_minimum_version
def test_upgrade_reset(
    gen: str,
    tag: str | None,
    model: str | None,
):
    def asserts(client: "Client"):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.backup_availability == BackupAvailability.NotAvailable
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, tag, model) as emu:
        device.setup(
            emu.client.get_seedless_session(),
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label=LABEL,
            entropy_check_count=0,
            backup_type=BackupType.Bip39,
        )
        device_id = emu.client.features.device_id
        asserts(emu.client)
        address = btc.get_address(emu.client.get_session(), "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert btc.get_address(emu.client.get_session(), "Bitcoin", PATH) == address


@for_all()
@lower_models_minimum_version
def test_upgrade_reset_skip_backup(
    gen: str,
    tag: str | None,
    model: str | None,
):
    def asserts(client: "Client"):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.backup_availability == BackupAvailability.Required
        assert not client.features.unfinished_backup
        assert not client.features.no_backup

    with EmulatorWrapper(gen, tag, model) as emu:
        device.setup(
            emu.client.get_seedless_session(),
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
        address = btc.get_address(emu.client.get_session(), "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert btc.get_address(emu.client.get_session(), "Bitcoin", PATH) == address


@for_all(legacy_minimum_version=(1, 7, 2))
@lower_models_minimum_version
def test_upgrade_reset_no_backup(
    gen: str,
    tag: str | None,
    model: str | None,
):
    def asserts(client: "Client"):
        assert not client.features.pin_protection
        assert not client.features.passphrase_protection
        assert client.features.initialized
        assert client.features.label == LABEL
        assert client.features.backup_availability == BackupAvailability.NotAvailable
        assert not client.features.unfinished_backup
        assert client.features.no_backup

    with EmulatorWrapper(gen, tag, model) as emu:
        device.setup(
            emu.client.get_seedless_session(),
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
        address = btc.get_address(emu.client.get_session(), "Bitcoin", PATH)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert device_id == emu.client.features.device_id
        asserts(emu.client)
        assert btc.get_address(emu.client.get_session(), "Bitcoin", PATH) == address


# Although Shamir was introduced in 2.1.2 already, the debug instrumentation was not present until 2.1.9.
@for_all("core", core_minimum_version=(2, 1, 9))
@lower_models_minimum_version
def test_upgrade_shamir_recovery(
    gen: str,
    tag: str | None,
    model: str | None,
):
    if model == "T3W1":
        pytest.xfail("Debug-entering of shares is not implemented for T3W1.")
    with (
        EmulatorWrapper(gen, tag, model) as emu,
        BackgroundDeviceHandler(emu.client) as device_handler,
    ):
        assert emu.client.features.recovery_status == RecoveryStatus.Nothing
        emu.client.watch_layout(True)
        debug = device_handler.debuglink()

        device_handler.run_with_session(
            device.recover, seedless=True, pin_protection=False
        )

        recovery_old.confirm_recovery(debug)
        recovery_old.select_number_of_words(debug, version_from_tag(tag))
        layout = recovery_old.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[0])
        if emu.client.model.internal_name == "T3W1":
            pytest.xfail("Debug-entering of shares is not implemented for T3W1.")
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
        layout = recovery.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[2])
        assert (
            "2 of 3 shares entered" in layout.text_content()
            or "1 more share" in layout.text_content()
        )

        # last one
        layout = recovery.enter_share(debug, MNEMONIC_SLIP39_BASIC_20_3of6[1])
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
@lower_models_minimum_version
def test_upgrade_shamir_backup(
    gen: str,
    tag: str | None,
    model: str | None,
):
    with EmulatorWrapper(gen, tag, model) as emu:
        session = emu.client.get_seedless_session()
        # Generate a new encrypted master secret and record it.
        device.setup(
            session,
            pin_protection=False,
            skip_backup=True,
            backup_type=BackupType.Slip39_Basic,
            entropy_check_count=0,
        )
        device_id = emu.client.features.device_id
        backup_type = emu.client.features.backup_type
        mnemonic_secret = emu.client.debug.state().mnemonic_secret

        # Set passphrase_source = HOST.
        session = emu.client.get_seedless_session()
        resp = session.call(ApplySettings(_passphrase_source=2, use_passphrase=True))
        assert isinstance(resp, Success)

        # Get a passphrase-less and a passphrased address.
        session = _get_session(emu.client)
        address = btc.get_address(session, "Bitcoin", PATH)
        if emu.client.protocol_version == ProtocolVersion.V1:
            session.call(messages.Initialize(new_session=True))
        new_session = _get_session(emu.client, passphrase="TREZOR")
        address_passphrase = btc.get_address(new_session, "Bitcoin", PATH)

        assert emu.client.features.backup_availability == BackupAvailability.Required
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        assert emu.client.features.device_id == device_id

        # Create a backup of the encrypted master secret.
        assert emu.client.features.backup_availability == BackupAvailability.Required
        session = emu.client.get_seedless_session()
        with emu.client as client:
            IF = InputFlowSlip39BasicBackup(client, False)
            client.set_input_flow(IF.get())
            device.backup(session)
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
        assert btc.get_address(_get_session(emu.client), "Bitcoin", PATH) == address
        assert (
            btc.get_address(
                _get_session(emu.client, passphrase="TREZOR"), "Bitcoin", PATH
            )
            == address_passphrase
        )


@for_all(legacy_minimum_version=(1, 8, 4), core_minimum_version=(2, 1, 9))
@lower_models_minimum_version
def test_upgrade_u2f(
    gen: str,
    tag: str | None,
    model: str | None,
):
    """Check U2F counter stayed the same after an upgrade."""
    with EmulatorWrapper(gen, tag, model) as emu:
        debuglink.load_device_by_mnemonic(
            emu.client.get_seedless_session(),
            mnemonic=MNEMONIC,
            pin="",
            passphrase_protection=False,
            label=LABEL,
        )
        session = emu.client.get_seedless_session()
        fido.set_counter(session, 10)

        counter = fido.get_next_counter(session)
        assert counter == 11
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        session = emu.client.get_seedless_session()
        counter = fido.get_next_counter(session)
        assert counter == 12


@for_all("core")
@lower_models_minimum_version
@pytest.mark.parametrize("backup_type", [BackupType.Bip39, BackupType.Slip39_Basic])
@pytest.mark.parametrize(
    "derivation_type",
    [CardanoDerivationType.ICARUS, CardanoDerivationType.ICARUS_TREZOR],
)
def test_cardano_address_does_not_change_by_upgrade(
    gen: str,
    tag: str,
    model: str,
    backup_type: BackupType,
    derivation_type: CardanoDerivationType,
):
    """
    Check that the Cardano address does not change after upgrading app storage from v2
    to the current version.
    """
    ADDRESS_N = parse_path("m/44h/1815h/0h")

    version_tag = version_from_tag(tag)
    if (
        version_tag is not None
        and version_tag == (2, 1, 2)
        and backup_type == BackupType.Slip39_Basic
    ):
        # SLIP-39 was not implemented for Cardano in v2.1.2
        return

    with EmulatorWrapper(gen, tag, model) as emu:
        device.setup(
            emu.client.get_seedless_session(),
            pin_protection=False,
            passphrase_protection=False,
            skip_backup=True,
            backup_type=backup_type,
            entropy_check_count=0,
        )
        session = emu.client.get_session(derive_cardano=True)
        old_key = get_public_key(session, ADDRESS_N, derivation_type, show_display=True)
        storage = emu.get_storage()

    with EmulatorWrapper(gen, storage=storage) as emu:
        session = emu.client.get_session(derive_cardano=True)
        new_key = get_public_key(session, ADDRESS_N, derivation_type, show_display=True)

        assert old_key.xpub == new_key.xpub
        assert old_key.node.public_key == new_key.node.public_key
        assert old_key.node.chain_code == new_key.node.chain_code


if __name__ == "__main__":
    if not ALL_TAGS:
        print("No emulators found. Remember to run download_emulators.sh")
    for model, tag in ALL_TAGS.items():
        print(f"Found versions for {model}: {tag}")
    print()
    print(f"Use `pytest {__file__}` to run tests")
