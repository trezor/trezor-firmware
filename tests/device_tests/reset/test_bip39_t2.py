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

from unittest import mock

import pytest
from mnemonic import Mnemonic

from trezorlib import device, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import ButtonRequestType as B

from ...common import (
    MNEMONIC12,
    click_through,
    generate_entropy,
    read_and_confirm_mnemonic,
)

pytestmark = [pytest.mark.skip_t1]

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2


def reset_device(client, strength):
    mnemonic = None

    def input_flow():
        nonlocal mnemonic
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        yield from click_through(client.debug, screens=3, code=B.ResetDevice)

        # mnemonic phrases
        mnemonic = yield from read_and_confirm_mnemonic(client.debug)

        # confirm recovery seed check
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

        # confirm success
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Success),
                messages.Success,
                messages.Features,
            ]
        )
        client.set_input_flow(input_flow)

        # No PIN, no passphrase, don't display random
        device.reset(
            client,
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="en-US",
        )

    # generate mnemonic locally
    internal_entropy = client.debug.state().reset_entropy
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = client.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.needs_backup is False
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False
    assert resp.backup_type is messages.BackupType.Bip39

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(client)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device(client):
    reset_device(client, 128)  # 12 words


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_192(client):
    reset_device(client, 192)  # 18 words


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_pin(client):
    mnemonic = None
    strength = 256  # 24 words

    def input_flow():
        nonlocal mnemonic

        # Confirm Reset
        br = yield
        assert br.code == B.ResetDevice
        client.debug.press_yes()

        # Enter new PIN
        yield
        client.debug.input("654")

        # Confirm PIN
        yield
        client.debug.input("654")

        # Confirm entropy
        br = yield
        assert br.code == B.ResetDevice
        client.debug.press_yes()

        # Backup your seed
        br = yield
        assert br.code == B.ResetDevice
        client.debug.press_yes()

        # Confirm warning
        br = yield
        assert br.code == B.ResetDevice
        client.debug.press_yes()

        # mnemonic phrases
        mnemonic = yield from read_and_confirm_mnemonic(client.debug)

        # confirm recovery seed check
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

        # confirm success
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.PinEntry),
                messages.ButtonRequest(code=B.PinEntry),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Success),
                messages.Success,
                messages.Features,
            ]
        )
        client.set_input_flow(input_flow)

        # PIN, passphrase, display random
        device.reset(
            client,
            display_random=True,
            strength=strength,
            passphrase_protection=True,
            pin_protection=True,
            label="test",
            language="en-US",
        )

    # generate mnemonic locally
    internal_entropy = client.debug.state().reset_entropy
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = client.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.needs_backup is False
    assert resp.pin_protection is True
    assert resp.passphrase_protection is True


@pytest.mark.setup_client(uninitialized=True)
def test_reset_failed_check(client):
    mnemonic = None
    strength = 256  # 24 words

    def input_flow():
        nonlocal mnemonic
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        yield from click_through(client.debug, screens=3, code=B.ResetDevice)

        # mnemonic phrases, wrong answer
        mnemonic = yield from read_and_confirm_mnemonic(client.debug, choose_wrong=True)

        # warning screen
        br = yield
        assert br.code == B.ResetDevice
        client.debug.press_yes()

        # mnemonic phrases
        mnemonic = yield from read_and_confirm_mnemonic(client.debug)

        # confirm recovery seed check
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

        # confirm success
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Success),
                messages.Success,
                messages.Features,
            ]
        )
        client.set_input_flow(input_flow)

        # PIN, passphrase, display random
        device.reset(
            client,
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="en-US",
        )

    # generate mnemonic locally
    internal_entropy = client.debug.state().reset_entropy
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = client.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.needs_backup is False
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False
    assert resp.backup_type is messages.BackupType.Bip39


@pytest.mark.setup_client(uninitialized=True)
def test_failed_pin(client):
    # external_entropy = b'zlutoucky kun upel divoke ody' * 2
    strength = 128
    ret = client.call_raw(
        messages.ResetDevice(strength=strength, pin_protection=True, label="test")
    )

    # Confirm Reset
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Enter PIN for first time
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.input("654")
    ret = client.call_raw(messages.ButtonAck())

    # Enter PIN for second time
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.input("456")
    ret = client.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.ButtonRequest)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_already_initialized(client):
    with pytest.raises(Exception):
        device.reset(client, False, 128, True, True, "label", "en-US")
