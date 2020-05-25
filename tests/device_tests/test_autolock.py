#
# This file is part of the Trezor project.
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

import time

import pytest

from trezorlib import device, messages

from ..common import TEST_ADDRESS_N, get_test_address

PIN4 = "1234"

pytestmark = pytest.mark.setup_client(pin=PIN4)


def pin_request(client):
    return (
        messages.PinMatrixRequest()
        if client.features.model == "1"
        else messages.ButtonRequest()
    )


def set_autolock_delay(client, delay):
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                pin_request(client),
                messages.ButtonRequest(),
                messages.Success(),
                messages.Features(),
            ]
        )
        device.apply_settings(client, auto_lock_delay_ms=delay)


def test_apply_auto_lock_delay(client):
    set_autolock_delay(client, 10 * 1000)

    time.sleep(0.1)  # sleep less than auto-lock delay
    with client:
        # No PIN protection is required.
        client.set_expected_responses([messages.Address()])
        get_test_address(client)

    time.sleep(10.1)  # sleep more than auto-lock delay
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses([pin_request(client), messages.Address()])
        get_test_address(client)


def test_apply_minimal_auto_lock_delay(client):
    """
    Verify that the delay is not below the minimal auto-lock delay (10 secs)
    otherwise the device may auto-lock before any user interaction.
    """
    set_autolock_delay(client, 1 * 1000)

    time.sleep(0.1)  # sleep less than auto-lock delay
    with client:
        # No PIN protection is required.
        client.set_expected_responses([messages.Address()])
        get_test_address(client)

    # sleep more than specified auto-lock delay (1s) but less than minimal allowed (10s)
    time.sleep(3)
    with client:
        # No PIN protection is required.
        client.set_expected_responses([messages.Address()])
        get_test_address(client)

    time.sleep(10.1)  # sleep more than the minimal auto-lock delay
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses([pin_request(client), messages.Address()])
        get_test_address(client)


@pytest.mark.skip_t1
def test_autolock_cancels_ui(client):
    set_autolock_delay(client, 10 * 1000)

    resp = client.call_raw(
        messages.GetAddress(
            coin_name="Testnet",
            address_n=TEST_ADDRESS_N,
            show_display=True,
            script_type=messages.InputScriptType.SPENDADDRESS,
        )
    )
    assert isinstance(resp, messages.ButtonRequest)

    # send an ack, do not read response
    client._raw_write(messages.ButtonAck())
    # sleep more than auto-lock delay
    time.sleep(10.1)
    resp = client._raw_read()

    assert isinstance(resp, messages.Failure)
    assert resp.code == messages.FailureType.ActionCancelled
