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

from trezorlib import messages as proto

from .common import MNEMONIC12

PIN4 = "1234"
PIN6 = "789456"


@pytest.mark.skip_t2
class TestMsgChangepin:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_set_pin(self, client):
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is False

        # Check that there's no PIN protection
        ret = client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.Success)

        # Let's set new PIN
        ret = client.call_raw(proto.ChangePin())
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Send the PIN for first time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(PIN6)
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for second time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(PIN6)
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now we're done
        assert isinstance(ret, proto.Success)

        # Check that there's PIN protection now
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is True

        # Check that the PIN is correct
        self.check_pin(client, PIN6)

    @pytest.mark.setup_client(mnemonic=MNEMONIC12, pin=True, passphrase=True)
    def test_change_pin(self, client):
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is True

        # Check that there's PIN protection
        ret = client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.PinMatrixRequest)
        client.call_raw(proto.Cancel())

        # Check current PIN value
        self.check_pin(client, PIN4)

        # Let's change PIN
        ret = client.call_raw(proto.ChangePin())
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Send current PIN
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.read_pin_encoded()
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send new PIN for first time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(PIN6)
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for second time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(PIN6)
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now we're done
        assert isinstance(ret, proto.Success)

        # Check that there's still PIN protection now
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is True

        # Check that the PIN is correct
        self.check_pin(client, PIN6)

    @pytest.mark.setup_client(mnemonic=MNEMONIC12, pin=True, passphrase=True)
    def test_remove_pin(self, client):
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is True

        # Check that there's PIN protection
        ret = client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.PinMatrixRequest)
        client.call_raw(proto.Cancel())

        # Let's remove PIN
        ret = client.call_raw(proto.ChangePin(remove=True))
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Send current PIN
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.read_pin_encoded()
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now we're done
        assert isinstance(ret, proto.Success)

        # Check that there's no PIN protection now
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is False
        ret = client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.Success)

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_set_failed(self, client):
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is False

        # Check that there's no PIN protection
        ret = client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.Success)

        # Let's set new PIN
        ret = client.call_raw(proto.ChangePin())
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Send the PIN for first time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(PIN6)
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for second time, but with typo
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(PIN4)
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now it should fail, because pins are different
        assert isinstance(ret, proto.Failure)

        # Check that there's still no PIN protection now
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is False
        ret = client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.Success)

    @pytest.mark.setup_client(mnemonic=MNEMONIC12, pin=True, passphrase=True)
    def test_set_failed_2(self, client):
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is True

        # Let's set new PIN
        ret = client.call_raw(proto.ChangePin())
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Send current PIN
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.read_pin_encoded()
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for first time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(PIN6)
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for second time, but with typo
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(PIN6 + "3")
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now it should fail, because pins are different
        assert isinstance(ret, proto.Failure)

        # Check that there's still old PIN protection
        features = client.call_raw(proto.Initialize())
        assert features.pin_protection is True
        self.check_pin(client, PIN4)

    def check_pin(self, client, pin):
        client.clear_session()
        ret = client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = client.debug.encode_pin(pin)
        ret = client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        assert isinstance(ret, proto.Success)
