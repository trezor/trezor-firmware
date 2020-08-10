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
from trezorlib.exceptions import TrezorFailure

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


@pytest.mark.parametrize(
    "seconds",
    [
        10,  # 10 seconds, minimum
        60,  # 1 minute
        123,  # 2 minutes
        3601,  # 1 hour
        7227,  # 2 hours
        536870,  # 149 hours, maximum
    ],
)
def test_apply_auto_lock_delay_valid(client, seconds):
    set_autolock_delay(client, seconds * 1000)


@pytest.mark.skip_ui
@pytest.mark.parametrize(
    "seconds", [0, 1, 9, 536871, 2 ** 22],
)
def test_apply_auto_lock_delay_out_of_range(client, seconds):
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                pin_request(client),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )

        delay = seconds * 1000
        with pytest.raises(TrezorFailure):
            device.apply_settings(client, auto_lock_delay_ms=delay)


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
