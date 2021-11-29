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

from trezorlib import device, messages

from ...common import MNEMONIC12

PIN4 = "1234"
PIN6 = "789456"

pytestmark = pytest.mark.skip_t2


@pytest.mark.setup_client(uninitialized=True)
def test_pin_passphrase(client):
    mnemonic = MNEMONIC12.split(" ")
    ret = client.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            passphrase_protection=True,
            pin_protection=True,
            label="label",
            language="en-US",
            enforce_wordlist=True,
        )
    )

    # click through confirmation
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for first time
    pin_encoded = client.debug.encode_pin(PIN6)
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))
    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for second time
    pin_encoded = client.debug.encode_pin(PIN6)
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    fakes = 0
    for _ in range(int(12 * 2)):
        assert isinstance(ret, messages.WordRequest)
        (word, pos) = client.debug.read_recovery_word()

        if pos != 0:
            ret = client.call_raw(messages.WordAck(word=mnemonic[pos - 1]))
            mnemonic[pos - 1] = None
        else:
            ret = client.call_raw(messages.WordAck(word=word))
            fakes += 1

    # Workflow succesfully ended
    assert isinstance(ret, messages.Success)

    # 12 expected fake words and all words of mnemonic are used
    assert fakes == 12
    assert mnemonic == [None] * 12

    # Mnemonic is the same
    client.init_device()
    assert client.debug.state().mnemonic_secret == MNEMONIC12.encode()

    assert client.features.pin_protection is True
    assert client.features.passphrase_protection is True

    # Do passphrase-protected action, PassphraseRequest should be raised
    resp = client.call_raw(messages.GetAddress())
    assert isinstance(resp, messages.PassphraseRequest)
    client.call_raw(messages.Cancel())


@pytest.mark.setup_client(uninitialized=True)
def test_nopin_nopassphrase(client):
    mnemonic = MNEMONIC12.split(" ")
    ret = client.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            language="en-US",
            enforce_wordlist=True,
        )
    )

    # click through confirmation
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    fakes = 0
    for _ in range(int(12 * 2)):
        assert isinstance(ret, messages.WordRequest)
        (word, pos) = client.debug.read_recovery_word()

        if pos != 0:
            ret = client.call_raw(messages.WordAck(word=mnemonic[pos - 1]))
            mnemonic[pos - 1] = None
        else:
            ret = client.call_raw(messages.WordAck(word=word))
            fakes += 1

    # Workflow succesfully ended
    assert isinstance(ret, messages.Success)

    # 12 expected fake words and all words of mnemonic are used
    assert fakes == 12
    assert mnemonic == [None] * 12

    # Mnemonic is the same
    client.init_device()
    assert client.debug.state().mnemonic_secret == MNEMONIC12.encode()

    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False

    # Do pin & passphrase-protected action, PassphraseRequest should NOT be raised
    resp = client.call_raw(messages.GetAddress())
    assert isinstance(resp, messages.Address)


@pytest.mark.setup_client(uninitialized=True)
def test_word_fail(client):
    ret = client.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            language="en-US",
            enforce_wordlist=True,
        )
    )

    # click through confirmation
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.WordRequest)
    for _ in range(int(12 * 2)):
        (word, pos) = client.debug.read_recovery_word()
        if pos != 0:
            ret = client.call_raw(messages.WordAck(word="kwyjibo"))
            assert isinstance(ret, messages.Failure)
            break
        else:
            client.call_raw(messages.WordAck(word=word))


@pytest.mark.setup_client(uninitialized=True)
def test_pin_fail(client):
    ret = client.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            passphrase_protection=True,
            pin_protection=True,
            label="label",
            language="en-US",
            enforce_wordlist=True,
        )
    )

    # click through confirmation
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for first time
    pin_encoded = client.debug.encode_pin(PIN4)
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))
    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for second time, but different one
    pin_encoded = client.debug.encode_pin(PIN6)
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # Failure should be raised
    assert isinstance(ret, messages.Failure)


def test_already_initialized(client):
    with pytest.raises(RuntimeError):
        device.recover(
            client, 12, False, False, "label", "en-US", client.mnemonic_callback
        )

    ret = client.call_raw(
        messages.RecoveryDevice(
            word_count=12, type=messages.RecoveryDeviceType.ScrambledWords
        )
    )
    assert isinstance(ret, messages.Failure)
    assert "Device is already initialized" in ret.message
