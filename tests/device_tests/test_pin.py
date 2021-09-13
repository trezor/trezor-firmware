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

from trezorlib import messages
from trezorlib.exceptions import PinException

from ..common import get_test_address

PIN4 = "1234"
BAD_PIN = "5678"

pytestmark = pytest.mark.setup_client(pin=PIN4)


@pytest.mark.setup_client(pin=None)
def test_no_protection(client):
    with client:
        client.set_expected_responses([messages.Address])
        get_test_address(client)


def test_correct_pin(client):
    with client:
        client.use_pin_sequence([PIN4])
        # Expected responses differ between T1 and TT
        is_t1 = client.features.model == "1"
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


@pytest.mark.skip_t2
def test_incorrect_pin_t1(client):
    with pytest.raises(PinException):
        client.use_pin_sequence([BAD_PIN])
        get_test_address(client)


@pytest.mark.skip_t1
def test_incorrect_pin_t2(client):
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


def _check_backoff_time(attempts: int, start: float) -> None:
    """Helper to assert the exponentially growing delay after incorrect PIN attempts"""
    expected = (2 ** attempts) - 1
    got = round(time.time() - start, 2)
    assert got >= expected


@pytest.mark.skip_t2
def test_exponential_backoff_t1(client):
    for attempt in range(3):
        start = time.time()
        with client, pytest.raises(PinException):
            client.use_pin_sequence([BAD_PIN])
            get_test_address(client)
        _check_backoff_time(attempt, start)


@pytest.mark.skip_t1
def test_exponential_backoff_t2(client):
    def input_flow():
        """Inputting some bad PINs and finally the correct one"""
        yield  # PIN entry
        for attempt in range(3):
            start = time.time()
            client.debug.input(BAD_PIN)
            yield  # PIN entry
            _check_backoff_time(attempt, start)
        client.debug.input(PIN4)

    with client:
        client.set_input_flow(input_flow)
        get_test_address(client)
