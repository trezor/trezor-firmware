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

from trezorlib import device, messages as proto

from ..common import generate_entropy


def reset_device(client, strength):
    # No PIN, no passphrase
    external_entropy = b"zlutoucky kun upel divoke ody" * 2

    ret = client.call_raw(
        proto.ResetDevice(
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            language="en-US",
            label="test",
        )
    )

    assert isinstance(ret, proto.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(proto.ButtonAck())

    # Provide entropy
    assert isinstance(ret, proto.EntropyRequest)
    internal_entropy = client.debug.state().reset_entropy
    ret = client.call_raw(proto.EntropyAck(entropy=external_entropy))

    # Generate mnemonic locally
    entropy = generate_entropy(strength, internal_entropy, external_entropy)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    mnemonic = []
    for _ in range(strength // 32 * 3):
        assert isinstance(ret, proto.ButtonRequest)
        mnemonic.append(client.debug.read_reset_word())
        client.debug.press_yes()
        client.call_raw(proto.ButtonAck())

    mnemonic = " ".join(mnemonic)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic

    mnemonic = []
    for _ in range(strength // 32 * 3):
        assert isinstance(ret, proto.ButtonRequest)
        mnemonic.append(client.debug.read_reset_word())
        client.debug.press_yes()
        resp = client.call_raw(proto.ButtonAck())

    assert isinstance(resp, proto.Success)

    mnemonic = " ".join(mnemonic)

    # Compare that second pass printed out the same mnemonic once again
    assert mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = client.call_raw(proto.Initialize())
    assert resp.initialized is True
    assert resp.needs_backup is False
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False

    # Do pin & passphrase-protected action, PassphraseRequest should NOT be raised
    resp = client.call_raw(proto.GetAddress())
    assert isinstance(resp, proto.Address)


@pytest.mark.skip_t2
class TestMsgResetDevice:
    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device_128(self, client):
        reset_device(client, 128)

    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device_192(self, client):
        reset_device(client, 192)

    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device_256_pin(self, client):
        external_entropy = b"zlutoucky kun upel divoke ody" * 2
        strength = 256

        ret = client.call_raw(
            proto.ResetDevice(
                display_random=True,
                strength=strength,
                passphrase_protection=True,
                pin_protection=True,
                language="en-US",
                label="test",
            )
        )

        # Do you want ... ?
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Entropy screen #1
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Entropy screen #2
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        assert isinstance(ret, proto.PinMatrixRequest)

        # Enter PIN for first time
        pin_encoded = client.debug.encode_pin("654")
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        assert isinstance(ret, proto.PinMatrixRequest)

        # Enter PIN for second time
        pin_encoded = client.debug.encode_pin("654")
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Provide entropy
        assert isinstance(ret, proto.EntropyRequest)
        internal_entropy = client.debug.state().reset_entropy
        ret = client.call_raw(proto.EntropyAck(entropy=external_entropy))

        # Generate mnemonic locally
        entropy = generate_entropy(strength, internal_entropy, external_entropy)
        expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

        mnemonic = []
        for _ in range(strength // 32 * 3):
            assert isinstance(ret, proto.ButtonRequest)
            mnemonic.append(client.debug.read_reset_word())
            client.debug.press_yes()
            client.call_raw(proto.ButtonAck())

        mnemonic = " ".join(mnemonic)

        # Compare that device generated proper mnemonic for given entropies
        assert mnemonic == expected_mnemonic

        mnemonic = []
        for _ in range(strength // 32 * 3):
            assert isinstance(ret, proto.ButtonRequest)
            mnemonic.append(client.debug.read_reset_word())
            client.debug.press_yes()
            resp = client.call_raw(proto.ButtonAck())

        assert isinstance(resp, proto.Success)

        mnemonic = " ".join(mnemonic)

        # Compare that second pass printed out the same mnemonic once again
        assert mnemonic == expected_mnemonic

        # Check if device is properly initialized
        resp = client.call_raw(proto.Initialize())
        assert resp.initialized is True
        assert resp.needs_backup is False
        assert resp.pin_protection is True
        assert resp.passphrase_protection is True

        # Do passphrase-protected action, PassphraseRequest should be raised
        resp = client.call_raw(proto.GetAddress())
        assert isinstance(resp, proto.PassphraseRequest)
        client.call_raw(proto.Cancel())

    @pytest.mark.setup_client(uninitialized=True)
    def test_failed_pin(self, client):
        # external_entropy = b'zlutoucky kun upel divoke ody' * 2
        strength = 128

        ret = client.call_raw(
            proto.ResetDevice(
                display_random=True,
                strength=strength,
                passphrase_protection=True,
                pin_protection=True,
                language="en-US",
                label="test",
            )
        )

        # Do you want ... ?
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Entropy screen #1
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Entropy screen #2
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        assert isinstance(ret, proto.PinMatrixRequest)

        # Enter PIN for first time
        pin_encoded = client.debug.encode_pin("1234")
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        assert isinstance(ret, proto.PinMatrixRequest)

        # Enter PIN for second time
        pin_encoded = client.debug.encode_pin("6789")
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        assert isinstance(ret, proto.Failure)

    def test_already_initialized(self, client):
        with pytest.raises(Exception):
            device.reset(client, False, 128, True, True, "label", "en-US")
