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

from trezorlib import cardano, exceptions, messages, models
from trezorlib.client import ProtocolVersion
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import Address, parse_path
from trezorlib.transport.session import Session, SessionV1

from ..common import get_test_address

ADDRESS_N = parse_path("m/44h/0h/0h")
XPUB = "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy"

PIN4 = "1234"


def _get_public_node(
    session: "Session",
    address: "Address",
) -> messages.PublicKey:

    resp = session.call_raw(
        messages.GetPublicKey(address_n=address),
    )
    if isinstance(resp, messages.ButtonRequest):
        resp = session._callback_button(resp)
    if isinstance(resp, messages.PinMatrixRequest):
        resp = session._callback_pin(resp)
    return resp


@pytest.mark.setup_client(pin=PIN4, passphrase="")
def test_clear_session(client: Client):
    is_t1 = client.model is models.T1B1
    v1 = client.protocol_version == ProtocolVersion.V1
    init_responses = [
        (v1, messages.Features),
        messages.PinMatrixRequest if is_t1 else messages.ButtonRequest,
        (not v1, messages.Success),
        (v1, messages.PassphraseRequest),
        (v1, messages.Address),
    ]

    lock_unlock = [
        messages.Success,
        messages.PinMatrixRequest if is_t1 else messages.ButtonRequest,
    ]

    cached_responses = [messages.PublicKey]
    with client:
        client.use_pin_sequence([PIN4, PIN4])
        client.set_expected_responses(init_responses + lock_unlock + cached_responses)
        session = client.get_session()
        session.lock()
        assert _get_public_node(session, ADDRESS_N).xpub == XPUB

    session.resume()
    with client:
        # pin and passphrase are cached
        client.set_expected_responses(cached_responses)
        assert _get_public_node(session, ADDRESS_N).xpub == XPUB

    session.lock()
    session.end()

    # session cache is cleared
    with client:
        client.use_pin_sequence([PIN4, PIN4])
        client.set_expected_responses(init_responses + cached_responses)
        session = client.get_session()
        assert _get_public_node(session, ADDRESS_N).xpub == XPUB

    session.resume()
    with client:
        # pin and passphrase are cached
        client.set_expected_responses(cached_responses)
        assert _get_public_node(session, ADDRESS_N).xpub == XPUB


def test_end_session(client: Client):
    # client instance starts out not initialized
    # XXX do we want to change this?
    session = client.get_session()
    assert session.id is not None

    # get_address will succeed
    with client:
        client.set_expected_responses([messages.Address])
        get_test_address(session)

    session.end()
    # assert client.session_id is None
    with pytest.raises(TrezorFailure) as exc:
        get_test_address(session)
    assert exc.value.code == messages.FailureType.InvalidSession
    assert exc.value.message.endswith("Invalid session")

    session = client.get_session()
    assert session.id is not None
    with client:
        client.set_expected_responses([messages.Address])
        get_test_address(session)

    with client:
        # end_session should succeed on empty session too
        client.set_expected_responses([messages.Success] * 2)
        session.end()
        session.end()


@pytest.mark.protocol("protocol_v1")
def test_cannot_resume_ended_session(client: Client):
    session = client.get_session()
    session_id = session.id

    session.resume()

    assert session.id == session_id

    session.end()
    with pytest.raises(exceptions.FailedSessionResumption) as e:
        session.resume()

    assert e.value.received_session_id != session_id


@pytest.mark.protocol("protocol_v1")
def test_end_session_only_current(client: Client):
    """test that EndSession only destroys the current session"""
    session_a = client.get_session()
    session_b = client.get_session()
    session_b_id = session_b.id

    session_b.end()
    # assert client.session_id is None

    # resume ended session
    with pytest.raises(exceptions.FailedSessionResumption) as e:
        session_b.resume()

    assert e.value.received_session_id != session_b_id

    # resume first session that was not ended
    session_a.resume()
    assert session_a.id == session_a.id


@pytest.mark.setup_client(passphrase=True)
def test_session_recycling(client: Client):
    session = client.get_session(passphrase="TREZOR")
    with client:
        client.set_expected_responses([messages.Address])
        address = get_test_address(session)

    # create and close 100 sessions - more than the session limit
    for _ in range(100):
        session_x = client.get_seedless_session()
        session_x.end()

    # it should still be possible to resume the original session
    with client:
        # passphrase should still be cached
        expected_responses = [messages.Address] * 3
        if client.protocol_version == ProtocolVersion.V1:
            expected_responses = [messages.Features] + expected_responses
        client.set_expected_responses(expected_responses)
        session.resume()
        get_test_address(session)
        get_test_address(session)
        assert address == get_test_address(session)


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.models("core")
@pytest.mark.protocol("protocol_v1")
def test_derive_cardano_empty_session(client: Client):
    # start new session
    session = SessionV1.new(client)
    session.init_session(derive_cardano=True)
    session_id = session.id

    # restarting same session should go well
    session.resume()
    assert session.id == session_id

    # restarting same session should go well with any setting
    session.init_session(derive_cardano=False)
    assert session_id == session.id
    session.init_session(derive_cardano=True)
    assert session_id == session.id


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.models("core")
@pytest.mark.protocol("protocol_v1")
def test_derive_cardano_running_session(client: Client):
    # start new session
    session = client.get_session(derive_cardano=False)
    session_id = session.id
    # force derivation of seed
    get_test_address(session)

    # session should not have Cardano capability
    with pytest.raises(TrezorFailure, match="not enabled"):
        cardano.get_public_key(session, parse_path("m/44h/1815h/0h"))

    # restarting same session should go well
    session.resume()
    assert session.id == session_id

    # restarting same session should go well if we _don't_ want to derive cardano
    session.init_session(derive_cardano=False)
    assert session.id == session_id

    # restarting with derive_cardano=True should kill old session and create new one
    with pytest.raises(exceptions.FailedSessionResumption) as e:
        session.init_session(derive_cardano=True)
    session_2 = SessionV1(client, e.value.received_session_id)
    session_2.derive_cardano = True
    session_2_id = session_2.id
    assert session_2_id != session.id

    # new session should have Cardano capability
    cardano.get_public_key(session_2, parse_path("m/44h/1815h/0h"))

    # restarting with derive_cardano=True should keep same session
    session_2.resume()
    assert session_2.id == session_2_id

    # restarting with derive_cardano=False should kill old session and create new one
    with pytest.raises(exceptions.FailedSessionResumption) as e:
        session_2.init_session(derive_cardano=False)
    session_3 = SessionV1(client, e.value.received_session_id)

    assert session_2.id != session_3.id

    with pytest.raises(TrezorFailure, match="not enabled"):
        cardano.get_public_key(session_3, parse_path("m/44h/1815h/0h"))
