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

from trezorlib import messages

PIN4 = "1234"
WIPE_CODE4 = "4321"
WIPE_CODE6 = "456789"

pytestmark = pytest.mark.skip_t2


def _set_wipe_code(client, wipe_code):
    # Set/change wipe code.
    ret = client.call_raw(messages.ChangeWipeCode())
    assert isinstance(ret, messages.ButtonRequest)

    # Confirm intent to set/change wipe code.
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    if client.features.pin_protection:
        # Send current PIN.
        assert isinstance(ret, messages.PinMatrixRequest)
        pin_encoded = client.debug.read_pin_encoded()
        ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # Send the new wipe code for the first time.
    assert isinstance(ret, messages.PinMatrixRequest)
    wipe_code_encoded = client.debug.encode_pin(wipe_code)
    ret = client.call_raw(messages.PinMatrixAck(pin=wipe_code_encoded))

    # Send the new wipe code for the second time.
    assert isinstance(ret, messages.PinMatrixRequest)
    wipe_code_encoded = client.debug.encode_pin(wipe_code)
    ret = client.call_raw(messages.PinMatrixAck(pin=wipe_code_encoded))

    # Now we're done.
    assert isinstance(ret, messages.Success)


def _remove_wipe_code(client):
    # Remove wipe code
    ret = client.call_raw(messages.ChangeWipeCode(remove=True))
    assert isinstance(ret, messages.ButtonRequest)

    # Confirm intent to remove wipe code.
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Send current PIN.
    assert isinstance(ret, messages.PinMatrixRequest)
    pin_encoded = client.debug.read_pin_encoded()
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # Now we're done.
    assert isinstance(ret, messages.Success)


def _check_wipe_code(client, wipe_code):
    # Try to change the PIN to the current wipe code value. The operation should fail.
    ret = client.call_raw(messages.ChangePin())
    assert isinstance(ret, messages.ButtonRequest)

    # Confirm intent to change PIN.
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Send current PIN.
    assert isinstance(ret, messages.PinMatrixRequest)
    pin_encoded = client.debug.read_pin_encoded()
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # Send the new wipe code for the first time.
    assert isinstance(ret, messages.PinMatrixRequest)
    wipe_code_encoded = client.debug.encode_pin(wipe_code)
    ret = client.call_raw(messages.PinMatrixAck(pin=wipe_code_encoded))

    # Send the new wipe code for the second time.
    assert isinstance(ret, messages.PinMatrixRequest)
    wipe_code_encoded = client.debug.encode_pin(wipe_code)
    ret = client.call_raw(messages.PinMatrixAck(pin=wipe_code_encoded))

    # Expect failure.
    assert isinstance(ret, messages.Failure)


@pytest.mark.setup_client(pin=PIN4)
def test_set_remove_wipe_code(client):
    # Check that wipe code protection status is not revealed in locked state.
    assert client.features.wipe_code_protection is None

    # Test set wipe code.
    _set_wipe_code(client, WIPE_CODE4)

    # Check that there's wipe code protection now.
    client.init_device()
    assert client.features.wipe_code_protection is True

    # Check that the wipe code is correct.
    _check_wipe_code(client, WIPE_CODE4)

    # Test change wipe code.
    _set_wipe_code(client, WIPE_CODE6)

    # Check that there's still wipe code protection now.
    client.init_device()
    assert client.features.wipe_code_protection is True

    # Check that the PIN is correct.
    _check_wipe_code(client, WIPE_CODE6)

    # Test remove wipe code.
    _remove_wipe_code(client)

    # Check that there's no wipe code protection now.
    client.init_device()
    assert client.features.wipe_code_protection is False


def test_set_wipe_code_mismatch(client):
    # Check that there is no wipe code protection.
    assert client.features.wipe_code_protection is False

    # Let's set a new wipe code.
    ret = client.call_raw(messages.ChangeWipeCode())
    assert isinstance(ret, messages.ButtonRequest)

    # Confirm intent to set wipe code.
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Send the new wipe code for the first time.
    assert isinstance(ret, messages.PinMatrixRequest)
    wipe_code_encoded = client.debug.encode_pin(WIPE_CODE4)
    ret = client.call_raw(messages.PinMatrixAck(pin=wipe_code_encoded))

    # Send the new wipe code for the second time, but different.
    assert isinstance(ret, messages.PinMatrixRequest)
    wipe_code_encoded = client.debug.encode_pin(WIPE_CODE6)
    ret = client.call_raw(messages.PinMatrixAck(pin=wipe_code_encoded))

    # The operation should fail, because the wipe codes are different.
    assert isinstance(ret, messages.Failure)
    assert ret.code == messages.FailureType.WipeCodeMismatch

    # Check that there is no wipe code protection.
    client.init_device()
    assert client.features.wipe_code_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_set_wipe_code_to_pin(client):
    # Check that wipe code protection status is not revealed in locked state.
    assert client.features.wipe_code_protection is None

    # Let's try setting the wipe code to the curent PIN value.
    ret = client.call_raw(messages.ChangeWipeCode())
    assert isinstance(ret, messages.ButtonRequest)

    # Confirm intent to set wipe code.
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Send current PIN.
    assert isinstance(ret, messages.PinMatrixRequest)
    pin_encoded = client.debug.read_pin_encoded()
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # Send the new wipe code.
    assert isinstance(ret, messages.PinMatrixRequest)
    pin_encoded = client.debug.read_pin_encoded()
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # The operation should fail, because the wipe code must be different from the PIN.
    assert isinstance(ret, messages.Failure)
    assert ret.code == messages.FailureType.ProcessError

    # Check that there is no wipe code protection.
    client.init_device()
    assert client.features.wipe_code_protection is False


def test_set_pin_to_wipe_code(client):
    # Set wipe code.
    _set_wipe_code(client, WIPE_CODE4)

    # Try to set the PIN to the current wipe code value.
    ret = client.call_raw(messages.ChangePin())
    assert isinstance(ret, messages.ButtonRequest)

    # Confirm intent to set PIN.
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Send the new PIN for the first time.
    assert isinstance(ret, messages.PinMatrixRequest)
    pin_encoded = client.debug.encode_pin(WIPE_CODE4)
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # Send the new PIN for the second time.
    assert isinstance(ret, messages.PinMatrixRequest)
    pin_encoded = client.debug.encode_pin(WIPE_CODE4)
    ret = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # The operation should fail, because the PIN must be different from the wipe code.
    assert isinstance(ret, messages.Failure)
    assert ret.code == messages.FailureType.ProcessError

    # Check that there is no PIN protection.
    client.init_device()
    assert client.features.pin_protection is False
    ret = client.call_raw(messages.Ping(pin_protection=True))
    assert isinstance(ret, messages.Success)
