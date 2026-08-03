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
from mnemonic import Mnemonic

from trezorlib import device, messages
from trezorlib.btc import get_public_node
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType, TrezorTestContext
from trezorlib.exceptions import TrezorFailure

from ...common import EXTERNAL_ENTROPY, MNEMONIC12, MOCK_GET_ENTROPY, generate_entropy
from ...input_flows import (
    FlowAdapter,
    InputFlowBip39ResetBackup,
    InputFlowBip39ResetFailedCheck,
    InputFlowBip39ResetPIN,
    normal,
    try_to_cancel,
)

pytestmark = pytest.mark.models("core")

# Internal entropy of the final ResetDevice round, per model, after
# random.reseed(MOCK_SEED).
# Generated with:
#   tools/gen_rng_mock_vectors.py --model MODEL --seed 3735928559 --mcu-offset 48
# Plain-RNG consumes 48 words between the reseed and the final round, which is
# unrelated to this test and may need to be adjusted when plain RNG usage changes.
MOCK_SEED = 0xDEADBEEF
MOCK_INTERNAL_ENTROPY = {
    "T2T1": "f2116aa6a9489ab3f4f9b8ecc3dc3e5e46dba0a0edf9cde568129e61a752f3f8",
    "T2B1": "7848b308f76310aa0701dafd18fe7d4231560079beeaec01b5a9138b6f43e056",
    "T3B1": "7848b308f76310aa0701dafd18fe7d4231560079beeaec01b5a9138b6f43e056",
    "T3T1": "7848b308f76310aa0701dafd18fe7d4231560079beeaec01b5a9138b6f43e056",
    "T3W1": "d3a61e63a6cea246b6dce9005067965ead5f2ef3633a4ad58a264c78f7ec9b25",
}

FLOW_ADAPTERS = [
    normal,
    try_to_cancel(
        {
            "setup_device",
            "confirm_setup_device",
            "backup_device",
            "success_backup",
        }
    ),
]


def reset_device(session: Session, strength: int, adapt_flow: FlowAdapter):
    debug = session.debug
    with session.test_ctx as client:
        IF = InputFlowBip39ResetBackup(session)
        client.set_input_flow(adapt_flow(session, IF.get()))

        # No PIN, no passphrase, don't display random
        device.setup(
            session,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # generate mnemonic locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    session.refresh_features()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is messages.BackupType.Bip39

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(session)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize("adapt_flow", FLOW_ADAPTERS, ids=lambda f: f.__name__)
def test_reset_device(session: Session, adapt_flow: FlowAdapter):
    reset_device(session, 128, adapt_flow)  # 12 words


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize("adapt_flow", FLOW_ADAPTERS, ids=lambda f: f.__name__)
def test_reset_device_192(session: Session, adapt_flow: FlowAdapter):
    reset_device(session, 192, adapt_flow)  # 18 words


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_pin(test_ctx: TrezorTestContext):
    debug = test_ctx.debug
    strength = 256  # 24 words

    with test_ctx:
        IF = InputFlowBip39ResetPIN(test_ctx)
        test_ctx.set_input_flow(IF.get())

        # PIN, passphrase, display random
        device.setup(
            test_ctx.get_seedless_session(),
            strength=strength,
            passphrase_protection=True,
            pin_protection=True,
            label="test",
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # generate mnemonic locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    session = test_ctx.get_session()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.pin_protection is True
    assert session.features.passphrase_protection is True


@pytest.mark.setup_client(uninitialized=True)
def test_reset_entropy_check(test_ctx: TrezorTestContext):
    strength = 128  # 12 words

    with test_ctx:
        IF = InputFlowBip39ResetBackup(test_ctx)
        test_ctx.set_input_flow(IF.get())

        # No PIN, no passphrase
        path_xpubs = device.setup(
            test_ctx.get_seedless_session(),
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            entropy_check_count=2,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # Generate the mnemonic locally.
    internal_entropy = test_ctx.debug.state().reset_entropy
    assert internal_entropy is not None
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Check that the device generated the correct mnemonic for the given entropies.
    assert IF.mnemonic == expected_mnemonic

    # Check that the device is properly initialized.
    session = test_ctx.get_session()

    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is messages.BackupType.Bip39

    # Check that the XPUBs are the same as those from the entropy check.
    for path, xpub in path_xpubs:
        res = get_public_node(session, path)
        assert res.xpub == xpub


@pytest.mark.emulator
@pytest.mark.setup_client(uninitialized=True)
def test_reset_entropy_mock_streams(session: Session):
    """Verify that the seed's internal entropy is exactly what the model's
    deterministic emulator entropy sources produce together, proving on the
    running firmware that every source contributed at every byte position. A
    dropped source, a lost strong=True, a truncated buffer each give a
    different value."""
    STRENGTH = 128
    MOCK_ENTROPY_CHECK_COUNT = 1
    debug = session.debug
    model = session.features.internal_model
    calls = 0

    def get_entropy() -> bytes:
        nonlocal calls
        calls += 1
        if calls == MOCK_ENTROPY_CHECK_COUNT:
            debug.reseed(MOCK_SEED)
        return EXTERNAL_ENTROPY

    with session.test_ctx as client:
        IF = InputFlowBip39ResetBackup(session)
        client.set_input_flow(IF.get())
        device.setup(
            session,
            strength=STRENGTH,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            entropy_check_count=MOCK_ENTROPY_CHECK_COUNT,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=get_entropy,
        )

    assert calls == MOCK_ENTROPY_CHECK_COUNT + 1

    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None

    expected = MOCK_INTERNAL_ENTROPY.get(model)
    assert internal_entropy.hex() == expected

    entropy = generate_entropy(STRENGTH, internal_entropy, EXTERNAL_ENTROPY)
    assert IF.mnemonic == Mnemonic("english").to_mnemonic(entropy)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_failed_check(test_ctx: TrezorTestContext):
    debug = test_ctx.debug
    strength = 256  # 24 words

    with test_ctx:
        IF = InputFlowBip39ResetFailedCheck(test_ctx)
        test_ctx.set_input_flow(IF.get())

        # PIN, passphrase, display random
        device.setup(
            test_ctx.get_seedless_session(),
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # generate mnemonic locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    session = test_ctx.get_session()
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is messages.BackupType.Bip39


@pytest.mark.setup_client(uninitialized=True)
def test_failed_pin(session: Session):
    debug = session.debug
    strength = 128
    ret = session.call_raw(
        messages.ResetDevice(strength=strength, pin_protection=True, label="test")
    )

    # Confirm Reset
    assert isinstance(ret, messages.ButtonRequest)

    session.write(messages.ButtonAck())
    debug.press_yes()
    session.read()

    # Enter PIN for first time
    debug.input("654")
    ret = session.call_raw(messages.ButtonAck())

    # Re-enter PIN for TR
    if session.layout_type is LayoutType.Caesar:
        assert isinstance(ret, messages.ButtonRequest)
        debug.press_yes()
        ret = session.call_raw(messages.ButtonAck())

    # Enter PIN for second time
    assert isinstance(ret, messages.ButtonRequest)
    debug.input("456")
    ret = session.call_raw(messages.ButtonAck())

    # PIN mismatch
    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.ButtonRequest)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_already_initialized(session: Session):
    with pytest.raises(Exception):
        device.setup(
            session,
            strength=128,
            passphrase_protection=True,
            pin_protection=True,
            label="label",
        )


@pytest.mark.setup_client(uninitialized=True)
def test_entropy_check(session: Session):
    with session.test_ctx as client:
        delizia = client.debug.layout_type is LayoutType.Delizia
        delizia_eckhart = client.debug.layout_type in (
            LayoutType.Delizia,
            LayoutType.Eckhart,
        )
        client.set_expected_responses(
            [
                (session.test_ctx.is_protocol_v1(), messages.Features),
                messages.ButtonRequest(name="setup_device"),
                (delizia, messages.ButtonRequest(name="confirm_setup_device")),
                messages.EntropyRequest,
                messages.EntropyCheckReady,
                messages.PublicKey,
                messages.PublicKey,
                messages.EntropyRequest,
                messages.EntropyCheckReady,
                messages.PublicKey,
                messages.PublicKey,
                messages.EntropyRequest,
                messages.EntropyCheckReady,
                messages.PublicKey,
                messages.PublicKey,
                (delizia_eckhart, messages.ButtonRequest(name="backup_device")),
                messages.Success,
                messages.Features,
            ]
        )
        device.setup(
            session,
            strength=128,
            entropy_check_count=2,
            backup_type=messages.BackupType.Bip39,
            skip_backup=True,
            pin_protection=False,
            passphrase_protection=False,
            _get_entropy=MOCK_GET_ENTROPY,
        )


@pytest.mark.setup_client(uninitialized=True)
def test_no_entropy_check(session: Session):
    with session.test_ctx as client:
        delizia_eckhart = client.debug.layout_type in (
            LayoutType.Delizia,
            LayoutType.Eckhart,
        )
        delizia = client.debug.layout_type is LayoutType.Delizia
        client.set_expected_responses(
            [
                (session.test_ctx.is_protocol_v1(), messages.Features),
                messages.ButtonRequest(name="setup_device"),
                (delizia, messages.ButtonRequest(name="confirm_setup_device")),
                messages.EntropyRequest,
                (delizia_eckhart, messages.ButtonRequest(name="backup_device")),
                messages.Success,
                messages.Features,
            ]
        )
        device.setup(
            session,
            strength=128,
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            skip_backup=True,
            pin_protection=False,
            passphrase_protection=False,
            _get_entropy=MOCK_GET_ENTROPY,
        )
