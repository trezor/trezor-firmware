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

from trezorlib import cardano, messages, models
from trezorlib.btc import get_public_node
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..common import get_test_address

ADDRESS_N = parse_path("m/44h/0h/0h")
XPUB = "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy"

PIN4 = "1234"


@pytest.mark.setup_client(pin=PIN4, passphrase="")
def test_clear_session(client: Client):
    is_t1 = client.model is models.T1B1
    init_responses = [
        messages.PinMatrixRequest if is_t1 else messages.ButtonRequest,
        messages.PassphraseRequest,
    ]

    cached_responses = [messages.PublicKey]
    session = client.get_session()
    session.lock()
    with client, session:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(init_responses + cached_responses)
        assert get_public_node(session, ADDRESS_N).xpub == XPUB

    client.resume_session(session)
    with session:
        # pin and passphrase are cached
        session.set_expected_responses(cached_responses)
        assert get_public_node(session, ADDRESS_N).xpub == XPUB

    session.lock()
    session.end()
    session = client.get_session()

    # session cache is cleared
    with client, session:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(init_responses + cached_responses)
        assert get_public_node(session, ADDRESS_N).xpub == XPUB

    client.resume_session(session)
    with session:
        # pin and passphrase are cached
        session.set_expected_responses(cached_responses)
        assert get_public_node(session, ADDRESS_N).xpub == XPUB


def test_end_session(client: Client):
    # client instance starts out not initialized
    # XXX do we want to change this?
    session = client.get_session()
    assert session.id is not None

    # get_address will succeed
    with session as session:
        session.set_expected_responses([messages.Address])
        get_test_address(session)

    session.end()
    # assert client.session_id is None
    with pytest.raises(TrezorFailure) as exc:
        get_test_address(session)
    assert exc.value.code == messages.FailureType.InvalidSession
    assert exc.value.message.endswith("Invalid session")

    session = client.get_session()
    assert session.id is not None
    with session as session:
        session.set_expected_responses([messages.Address])
        get_test_address(session)

    # TODO: is the following valid? I do not think so
    # with session as session:
    #     # end_session should succeed on empty session too
    #     session.set_expected_responses([messages.Success] * 2)
    #     session.end_session()
    #     session.end_session()


def test_cannot_resume_ended_session(client: Client):
    session = client.get_session()
    session_id = session.id

    session_resumed = client.resume_session(session)

    assert session_resumed.id == session_id

    session.end()
    session_resumed2 = client.resume_session(session)

    assert session_resumed2.id != session_id


def test_end_session_only_current(client: Client):
    """test that EndSession only destroys the current session"""
    session_a = client.get_session()
    session_b = client.get_session()
    session_b_id = session_b.id

    session_b.end()
    # assert client.session_id is None

    # resume ended session
    session_b_resumed = client.resume_session(session_b)
    assert session_b_resumed.id != session_b_id

    # resume first session that was not ended
    session_a_resumed = client.resume_session(session_a)
    assert session_a_resumed.id == session_a.id


@pytest.mark.setup_client(passphrase=True)
def test_session_recycling(client: Client):
    session = client.get_session(passphrase="TREZOR")
    with client, session:
        session.set_expected_responses(
            [
                messages.PassphraseRequest,
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.Address,
            ]
        )
        _ = get_test_address(session)
        # address = get_test_address(session)

    # create and close 100 sessions - more than the session limit
    for _ in range(100):
        session_x = client.get_session()
        session_x.end()

    # it should still be possible to resume the original session
    # TODO imo not True anymore
    # with client, session:
    #     # passphrase should still be cached
    #     session.set_expected_responses([messages.Features, messages.Address])
    #     client.use_passphrase("TREZOR")
    #     client.resume_session(session)
    #     assert address == get_test_address(session)


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.models("core")
def test_derive_cardano_empty_session(client: Client):
    # start new session
    session = client.get_session(derive_cardano=True)
    # session_id = client.session_id

    # restarting same session should go well
    session2 = client.resume_session(session)
    assert session.id == session2.id

    # restarting same session should go well with any setting
    # TODO I do not think that it holds True now
    # client.init_device(derive_cardano=False)
    # assert session_id == client.session_id
    # client.init_device(derive_cardano=True)
    # assert session_id == client.session_id


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.models("core")
def test_derive_cardano_running_session(client: Client):
    # start new session
    session = client.get_session(derive_cardano=False)

    # force derivation of seed
    get_test_address(session)

    # session should not have Cardano capability
    with pytest.raises(TrezorFailure, match="not enabled"):
        cardano.get_public_key(session, parse_path("m/44h/1815h/0h"))

    # restarting same session should go well
    session2 = client.resume_session(session)
    assert session.id == session2.id

    # TODO restarting same session should go well if we _don't_ want to derive cardano
    # # client.init_device(derive_cardano=False)
    # # assert session_id == client.session_id

    # restarting with derive_cardano=True should kill old session and create new one
    session3 = client.get_session(derive_cardano=True)
    assert session3.id != session.id

    # new session should have Cardano capability
    cardano.get_public_key(session3, parse_path("m/44h/1815h/0h"))

    # restarting with derive_cardano=True should keep same session
    session4 = client.resume_session(session3)
    assert session4.id == session3.id

    # # restarting with no setting should keep same session
    # client.init_device()
    # assert session_id == client.session_id

    # # restarting with derive_cardano=False should kill old session and create new one
    # client.init_device(derive_cardano=False)
    # assert session_id != client.session_id

    # with pytest.raises(TrezorFailure, match="not enabled"):
    #     cardano.get_public_key(client, parse_path("m/44h/1815h/0h"))
