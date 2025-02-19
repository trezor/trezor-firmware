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
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path

from ...common import MNEMONIC12

PIN4 = "1234"
PIN6 = "789456"

pytestmark = pytest.mark.models("legacy")


@pytest.mark.setup_client(uninitialized=True)
def test_pin_passphrase(session: Session):
    debug = session.client.debug
    mnemonic = MNEMONIC12.split(" ")
    ret = session.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            passphrase_protection=True,
            pin_protection=True,
            label="label",
            enforce_wordlist=True,
        )
    )

    # click through confirmation
    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for first time
    pin_encoded = debug.encode_pin(PIN6)
    ret = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))
    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for second time
    pin_encoded = debug.encode_pin(PIN6)
    ret = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    fakes = 0
    for _ in range(int(12 * 2)):
        assert isinstance(ret, messages.WordRequest)
        (word, pos) = debug.read_recovery_word()

        if pos != 0:
            ret = session.call_raw(messages.WordAck(word=mnemonic[pos - 1]))
            mnemonic[pos - 1] = None
        else:
            ret = session.call_raw(messages.WordAck(word=word))
            fakes += 1

    # Workflow succesfully ended
    assert isinstance(ret, messages.Success)

    # 12 expected fake words and all words of mnemonic are used
    assert fakes == 12
    assert mnemonic == [None] * 12

    # Mnemonic is the same
    session.init_session()
    session.client.refresh_features()
    assert debug.state().mnemonic_secret == MNEMONIC12.encode()

    assert session.features.pin_protection is True
    assert session.features.passphrase_protection is True

    # Do passphrase-protected action, PassphraseRequest should be raised
    resp = session.call_raw(
        messages.GetAddress(address_n=parse_path("m/44'/0'/0'/0/0"))
    )
    assert isinstance(resp, messages.PassphraseRequest)
    session.call_raw(messages.Cancel())


@pytest.mark.setup_client(uninitialized=True)
def test_nopin_nopassphrase(session: Session):
    mnemonic = MNEMONIC12.split(" ")
    ret = session.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            enforce_wordlist=True,
        )
    )

    # click through confirmation
    assert isinstance(ret, messages.ButtonRequest)
    debug = session.client.debug
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    fakes = 0
    for _ in range(int(12 * 2)):
        assert isinstance(ret, messages.WordRequest)
        (word, pos) = debug.read_recovery_word()

        if pos != 0:
            ret = session.call_raw(messages.WordAck(word=mnemonic[pos - 1]))
            mnemonic[pos - 1] = None
        else:
            ret = session.call_raw(messages.WordAck(word=word))
            fakes += 1

    # Workflow succesfully ended
    assert isinstance(ret, messages.Success)

    # 12 expected fake words and all words of mnemonic are used
    assert fakes == 12
    assert mnemonic == [None] * 12

    # Mnemonic is the same
    session.init_session()
    session.client.refresh_features()
    assert debug.state().mnemonic_secret == MNEMONIC12.encode()

    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False

    # Do pin & passphrase-protected action, PassphraseRequest should NOT be raised
    resp = session.call_raw(
        messages.GetAddress(address_n=parse_path("m/44'/0'/0'/0/0"))
    )
    assert isinstance(resp, messages.Address)


@pytest.mark.setup_client(uninitialized=True)
def test_word_fail(session: Session):
    debug = session.client.debug
    ret = session.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            enforce_wordlist=True,
        )
    )

    # click through confirmation
    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.WordRequest)
    for _ in range(int(12 * 2)):
        (word, pos) = debug.read_recovery_word()
        if pos != 0:
            ret = session.call_raw(messages.WordAck(word="kwyjibo"))
            assert isinstance(ret, messages.Failure)
            break
        else:
            session.call_raw(messages.WordAck(word=word))


@pytest.mark.setup_client(uninitialized=True)
def test_pin_fail(session: Session):
    debug = session.client.debug
    ret = session.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            passphrase_protection=True,
            pin_protection=True,
            label="label",
            enforce_wordlist=True,
        )
    )

    # click through confirmation
    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for first time
    pin_encoded = debug.encode_pin(PIN4)
    ret = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))
    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for second time, but different one
    pin_encoded = debug.encode_pin(PIN6)
    ret = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # Failure should be raised
    assert isinstance(ret, messages.Failure)


def test_already_initialized(session: Session):
    with pytest.raises(RuntimeError):
        device.recover(
            session,
            word_count=12,
            pin_protection=False,
            passphrase_protection=False,
            label="label",
            input_callback=session.client.mnemonic_callback,
        )

    ret = session.call_raw(
        messages.RecoveryDevice(
            word_count=12,
            input_method=messages.RecoveryDeviceInputMethod.ScrambledWords,
        )
    )
    assert isinstance(ret, messages.Failure)
    assert "Device is already initialized" in ret.message
