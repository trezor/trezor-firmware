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
from trezorlib.btc import get_public_node
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..common import get_test_address

ADDRESS_N = parse_path("44'/0'/0'")
XPUB = "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy"

PIN4 = "1234"


@pytest.mark.skip_ui
@pytest.mark.setup_client(pin=PIN4, passphrase=True)
def test_clear_session(client):
    is_trezor1 = client.features.model == "1"
    init_responses = [
        messages.PinMatrixRequest() if is_trezor1 else messages.ButtonRequest(),
        messages.PassphraseRequest(),
    ]

    cached_responses = [messages.PublicKey()]

    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(init_responses + cached_responses)
        assert get_public_node(client, ADDRESS_N).xpub == XPUB

    with client:
        # pin and passphrase are cached
        client.set_expected_responses(cached_responses)
        assert get_public_node(client, ADDRESS_N).xpub == XPUB

    client.clear_session()

    # session cache is cleared
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(init_responses + cached_responses)
        assert get_public_node(client, ADDRESS_N).xpub == XPUB

    with client:
        # pin and passphrase are cached
        client.set_expected_responses(cached_responses)
        assert get_public_node(client, ADDRESS_N).xpub == XPUB


@pytest.mark.skip_ui
def test_end_session(client):
    # client instance starts out not initialized
    # XXX do we want to change this?
    assert client.session_id is not None

    # get_address will succeed
    with client:
        client.set_expected_responses([messages.Address()])
        get_test_address(client)

    client.end_session()
    assert client.session_id is None
    with pytest.raises(TrezorFailure) as exc:
        get_test_address(client)
    assert exc.value.code == messages.FailureType.InvalidSession
    assert exc.value.message.endswith("Invalid session")

    client.init_device()
    assert client.session_id is not None
    with client:
        client.set_expected_responses([messages.Address()])
        get_test_address(client)

    with client:
        # end_session should succeed on empty session too
        client.set_expected_responses([messages.Success()] * 2)
        client.end_session()
        client.end_session()


@pytest.mark.skip_ui
def test_cannot_resume_ended_session(client):
    session_id = client.session_id
    with client:
        client.set_expected_responses([messages.Features()])
        client.init_device(session_id=session_id)

    assert session_id == client.session_id

    client.end_session()
    with client:
        client.set_expected_responses([messages.Features()])
        client.init_device(session_id=session_id)

    assert session_id != client.session_id


@pytest.mark.skip_ui
def test_end_session_only_current(client):
    """test that EndSession only destroys the current session"""
    session_id_a = client.session_id
    client.init_device(new_session=True)
    session_id_b = client.session_id

    client.end_session()
    assert client.session_id is None

    # resume ended session
    client.init_device(session_id=session_id_b)
    assert client.session_id != session_id_b

    # resume first session that was not ended
    client.init_device(session_id=session_id_a)
    assert client.session_id == session_id_a


@pytest.mark.skip_ui
@pytest.mark.setup_client(passphrase=True)
def test_session_recycling(client):
    session_id_orig = client.session_id
    with client:
        client.set_expected_responses(
            [
                messages.PassphraseRequest(),
                messages.ButtonRequest(),
                messages.ButtonRequest(),
                messages.Address(),
            ]
        )
        client.use_passphrase("TREZOR")
        address = get_test_address(client)

    # create and close 100 sessions - more than the session limit
    for _ in range(100):
        client.init_device(new_session=True)
        client.end_session()

    # it should still be possible to resume the original session
    with client:
        # passphrase should still be cached
        client.set_expected_responses([messages.Features(), messages.Address()])
        client.use_passphrase("TREZOR")
        client.init_device(session_id=session_id_orig)
        assert address == get_test_address(client)
