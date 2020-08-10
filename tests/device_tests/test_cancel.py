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

import trezorlib.messages as m
from trezorlib.exceptions import Cancelled

from ..common import TEST_ADDRESS_N

pytestmark = pytest.mark.skip_ui


@pytest.mark.parametrize(
    "message",
    [
        m.Ping(message="hello", button_protection=True),
        m.GetAddress(
            address_n=TEST_ADDRESS_N,
            coin_name="Testnet",
            script_type=m.InputScriptType.SPENDADDRESS,
            show_display=True,
        ),
    ],
)
def test_cancel_message_via_cancel(client, message):
    def input_flow():
        yield
        client.cancel()

    with client, pytest.raises(Cancelled):
        client.set_expected_responses([m.ButtonRequest(), m.Failure()])
        client.set_input_flow(input_flow)
        client.call(message)


@pytest.mark.parametrize(
    "message",
    [
        m.Ping(message="hello", button_protection=True),
        m.GetAddress(
            address_n=TEST_ADDRESS_N,
            coin_name="Testnet",
            script_type=m.InputScriptType.SPENDADDRESS,
            show_display=True,
        ),
    ],
)
def test_cancel_message_via_initialize(client, message):
    resp = client.call_raw(message)
    assert isinstance(resp, m.ButtonRequest)

    client._raw_write(m.ButtonAck())
    client._raw_write(m.Initialize())

    resp = client._raw_read()

    assert isinstance(resp, m.Features)
