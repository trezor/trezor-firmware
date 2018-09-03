# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from .common import TrezorTest


@pytest.mark.skip_t2
class TestMsgChangepin(TrezorTest):
    def test_set_pin(self):
        self.setup_mnemonic_nopin_nopassphrase()
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is False

        # Check that there's no PIN protection
        ret = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.Success)

        # Let's set new PIN
        ret = self.client.call_raw(proto.ChangePin())
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Send the PIN for first time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for second time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now we're done
        assert isinstance(ret, proto.Success)

        # Check that there's PIN protection now
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is True
        ret = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.PinMatrixRequest)
        self.client.call_raw(proto.Cancel())

        # Check that the PIN is correct
        assert self.client.debug.read_pin()[0] == self.pin6

    def test_change_pin(self):
        self.setup_mnemonic_pin_passphrase()
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is True

        # Check that there's PIN protection
        ret = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.PinMatrixRequest)
        self.client.call_raw(proto.Cancel())

        # Check current PIN value
        assert self.client.debug.read_pin()[0] == self.pin4

        # Let's change PIN
        ret = self.client.call_raw(proto.ChangePin())
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Send current PIN
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.read_pin_encoded()
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send new PIN for first time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for second time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now we're done
        assert isinstance(ret, proto.Success)

        # Check that there's still PIN protection now
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is True
        ret = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.PinMatrixRequest)
        self.client.call_raw(proto.Cancel())

        # Check that the PIN is correct
        assert self.client.debug.read_pin()[0] == self.pin6

    def test_remove_pin(self):
        self.setup_mnemonic_pin_passphrase()
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is True

        # Check that there's PIN protection
        ret = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.PinMatrixRequest)
        self.client.call_raw(proto.Cancel())

        # Let's remove PIN
        ret = self.client.call_raw(proto.ChangePin(remove=True))
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Send current PIN
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.read_pin_encoded()
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now we're done
        assert isinstance(ret, proto.Success)

        # Check that there's no PIN protection now
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is False
        ret = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.Success)

    def test_set_failed(self):
        self.setup_mnemonic_nopin_nopassphrase()
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is False

        # Check that there's no PIN protection
        ret = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.Success)

        # Let's set new PIN
        ret = self.client.call_raw(proto.ChangePin())
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Send the PIN for first time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for second time, but with typo
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.encode_pin(self.pin4)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now it should fail, because pins are different
        assert isinstance(ret, proto.Failure)

        # Check that there's still no PIN protection now
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is False
        ret = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(ret, proto.Success)

    def test_set_failed_2(self):
        self.setup_mnemonic_pin_passphrase()
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is True

        # Let's set new PIN
        ret = self.client.call_raw(proto.ChangePin())
        assert isinstance(ret, proto.ButtonRequest)

        # Press button
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Send current PIN
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.read_pin_encoded()
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for first time
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Send the PIN for second time, but with typo
        assert isinstance(ret, proto.PinMatrixRequest)
        pin_encoded = self.client.debug.encode_pin(self.pin6 + "3")
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Now it should fail, because pins are different
        assert isinstance(ret, proto.Failure)

        # Check that there's still old PIN protection
        features = self.client.call_raw(proto.Initialize())
        assert features.pin_protection is True
        assert self.client.debug.read_pin()[0] == self.pin4
