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

import time

import pytest

from trezorlib import messages, models
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import PinException

from ..common import check_pin_backoff_time, get_test_address
from ..input_flows import InputFlowPINBackoff

PIN4 = "1234"
BAD_PIN = "5678"

pytestmark = pytest.mark.setup_client(pin=PIN4)


@pytest.mark.setup_client(pin=None)
def test_no_protection(client: Client):
    with client:
        client.set_expected_responses([messages.Address])
        get_test_address(client)


def test_correct_pin(client: Client):
    with client:
        client.use_pin_sequence([PIN4])
        # Expected responses differ between T1 and TT
        is_t1 = client.model is models.T1B1
        client.set_expected_responses(
            [
                (is_t1, messages.PinMatrixRequest),
                (
                    not is_t1,
                    messages.ButtonRequest(code=messages.ButtonRequestType.PinEntry),
                ),
                messages.Address,
            ]
        )
        # client.set_expected_responses([messages.ButtonRequest, messages.Address])
        get_test_address(client)


@pytest.mark.models("legacy")
def test_incorrect_pin_t1(client: Client):
    with pytest.raises(PinException):
        client.use_pin_sequence([BAD_PIN])
        get_test_address(client)


@pytest.mark.models("core")
def test_incorrect_pin_t2(client: Client):
    with client:
        # After first incorrect attempt, TT will not raise an error, but instead ask for another attempt
        client.use_pin_sequence([BAD_PIN, PIN4])
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.PinEntry),
                messages.ButtonRequest(code=messages.ButtonRequestType.PinEntry),
                messages.Address,
            ]
        )
        get_test_address(client)


@pytest.mark.models("legacy")
def test_exponential_backoff_t1(client: Client):
    for attempt in range(3):
        start = time.time()
        with client, pytest.raises(PinException):
            client.use_pin_sequence([BAD_PIN])
            get_test_address(client)
        check_pin_backoff_time(attempt, start)


@pytest.mark.models("core")
def test_exponential_backoff_t2(client: Client):
    with client:
        IF = InputFlowPINBackoff(client, BAD_PIN, PIN4)
        client.set_input_flow(IF.get())
        get_test_address(client)
