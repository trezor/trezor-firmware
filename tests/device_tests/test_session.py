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

from trezorlib import btc, cardano, exceptions, messages, models, protocol_v1
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext
from trezorlib.exceptions import InvalidSessionError, TrezorFailure
from trezorlib.tools import parse_path

from ..common import get_test_address

ADDRESS_N = parse_path("m/44h/0h/0h")
XPUB = "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy"
XPUB_XYZ = "xpub6CzEwks5KV5kxxUTWtG9frJeoWMTPs6ZX4bSABMHry16MFXukicyRmau446SzcMUZh3wVABJir3PMNhQbw1N3PJDDos6BBGogCDHScx5Nkq"
PIN4 = "1234"
DATA_ERROR_INVALID_MESSAGE = "Passphrase provided when it shouldn't be!"
DATA_ERROR_ON_DEVICE = "Providing passphrase in message is not allowed when PASSPHRASE_ALWAYS_ON_DEVICE is True."


@pytest.mark.setup_client(pin=PIN4, passphrase="")
def test_clear_session(test_ctx: TrezorTestContext):
    is_t1 = test_ctx.model is models.T1B1
    if test_ctx.is_protocol_v1():
        # SessionV1.derive()
        init_responses = [
            messages.Features,
            messages.PinMatrixRequest if is_t1 else messages.ButtonRequest,
            messages.PassphraseRequest,
            messages.PublicKey,
            messages.Features,
        ]
    else:
        # ThpSession.derive()
        init_responses = [messages.ButtonRequest, messages.Success]

    lock_unlock = [
        messages.Success,
        messages.Features,
        messages.PinMatrixRequest if is_t1 else messages.ButtonRequest,
    ]

    cached_responses = [messages.PublicKey]
    with test_ctx:
        test_ctx.use_pin_sequence([PIN4, PIN4])
        test_ctx.set_expected_responses(init_responses + lock_unlock + cached_responses)
        session = test_ctx.get_session()
        session.lock()
        assert btc.get_public_node(session, ADDRESS_N).xpub == XPUB

    with test_ctx:
        # pin and passphrase are cached
        test_ctx.set_expected_responses(cached_responses)
        assert btc.get_public_node(session, ADDRESS_N).xpub == XPUB

    session.lock()
    session.close()

    # session cache is cleared
    with test_ctx:
        test_ctx.use_pin_sequence([PIN4, PIN4])
        test_ctx.set_expected_responses(init_responses + cached_responses)
        session = test_ctx.get_session()
        assert btc.get_public_node(session, ADDRESS_N).xpub == XPUB

    with test_ctx:
        # pin and passphrase are cached
        test_ctx.set_expected_responses(cached_responses)
        assert btc.get_public_node(session, ADDRESS_N).xpub == XPUB


def test_end_session(test_ctx: TrezorTestContext):
    session = test_ctx.get_session()
    assert session.id is not None

    # get_address will succeed
    with test_ctx:
        test_ctx.set_expected_responses([messages.Address])
        get_test_address(session)

    session.close()
    # avoid trezorlib's check
    session.is_invalid = False
    with pytest.raises(InvalidSessionError), test_ctx:
        test_ctx.set_expected_responses([messages.Failure])
        get_test_address(session)

    session = test_ctx.get_session()
    assert session.id is not None
    with test_ctx:
        test_ctx.set_expected_responses([messages.Address])
        get_test_address(session)

    with test_ctx:
        test_ctx.set_expected_responses([messages.Success] * 2)
        session.call(messages.EndSession())
        # end_session should succeed on empty session too
        session.call(messages.EndSession())


@pytest.mark.protocol("v1")
def test_cannot_resume_ended_session(test_ctx: TrezorTestContext):
    session = test_ctx.get_session()
    session_id = session.id

    assert isinstance(session, protocol_v1.SessionV1)
    session.initialize()

    assert session.id == session_id

    session.close()
    with pytest.raises(exceptions.InvalidSessionError):
        session.initialize()


@pytest.mark.protocol("v1")
def test_end_session_only_current(test_ctx: TrezorTestContext):
    """test that EndSession only destroys the current session"""
    session_a = test_ctx.get_session()
    session_b = test_ctx.get_session()
    session_b.call(messages.EndSession(), expect=messages.Success)

    assert isinstance(session_a, protocol_v1.SessionV1)
    assert isinstance(session_b, protocol_v1.SessionV1)

    # resume ended session
    with pytest.raises(exceptions.InvalidSessionError):
        session_b.initialize()

    # resume first session that was not ended
    session_a.initialize()


@pytest.mark.setup_client(passphrase=True)
def test_session_recycling(test_ctx: TrezorTestContext):
    session = test_ctx.get_session(passphrase="TREZOR")
    with test_ctx:
        test_ctx.set_expected_responses([messages.Address])
        address = get_test_address(session)

    # create and close 100 sessions - more than the session limit
    for _ in range(100):
        session_x = test_ctx.get_session()
        session_x.close()

    # it should still be possible to resume the original session
    with test_ctx:
        # passphrase should still be cached
        expected_responses = [messages.Address] * 3
        if test_ctx.is_protocol_v1():
            expected_responses = [messages.Features] + expected_responses
        test_ctx.set_expected_responses(expected_responses)
        get_test_address(session)
        get_test_address(session)
        assert address == get_test_address(session)


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.models("core")
@pytest.mark.protocol("v1")
def test_derive_cardano_empty_session(test_ctx: TrezorTestContext):
    assert isinstance(test_ctx.client, protocol_v1.TrezorClientV1)

    def session_id_for_derive_cardano(session_id: bytes, derive: bool | None) -> bytes:
        features = test_ctx.client._call(
            test_ctx.client._last_active_session,
            messages.Initialize(session_id=session_id, derive_cardano=derive),
            expect=messages.Features,
        )
        assert features.session_id is not None
        return features.session_id

    # start new session
    session_id = session_id_for_derive_cardano(b"", True)

    # restarting same session should go well
    assert session_id == session_id_for_derive_cardano(session_id, None)

    # restarting same session should go well with any setting
    assert session_id == session_id_for_derive_cardano(session_id, False)
    assert session_id == session_id_for_derive_cardano(session_id, True)


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.models("core")
@pytest.mark.protocol("v1")
def test_derive_cardano_running_session(test_ctx: TrezorTestContext):
    # start new session
    session = test_ctx.get_session(derive_cardano=False)
    assert isinstance(session, protocol_v1.SessionV1)

    # session should not have Cardano capability
    with pytest.raises(TrezorFailure, match="not enabled"):
        cardano.get_public_key(session, parse_path("m/44h/1815h/0h"))

    # restarting same session should go well
    session.initialize()

    # restarting same session should go well if we _don't_ want to derive cardano
    session.initialize(derive_cardano=False)

    # restarting with derive_cardano=True should kill old session and create new one
    with pytest.raises(exceptions.InvalidSessionError) as e:
        session.initialize(derive_cardano=True)
    features = messages.Features.ensure_isinstance(e.value.from_message)
    assert features.session_id is not None
    assert features.session_id != session.id

    session_2 = protocol_v1.SessionV1(test_ctx.client, id=features.session_id)
    # manually activate the new session, to avoid re-sending Initialize
    test_ctx.client._last_active_session = session_2
    # new session should have Cardano capability
    cardano.get_public_key(session_2, parse_path("m/44h/1815h/0h"))

    # restarting with derive_cardano=True should keep same session
    session_2.initialize(derive_cardano=True)

    # restarting with derive_cardano=False should kill old session and create new one
    with pytest.raises(exceptions.InvalidSessionError) as e:
        session_2.initialize(derive_cardano=False)

    session_2.is_invalid = False
    test_ctx.client._last_active_session = session_2
    with pytest.raises(TrezorFailure, match="not enabled"):
        cardano.get_public_key(session_2, parse_path("m/44h/1815h/0h"))


def _create_session_passphrase_on_device(
    session: Session,
    passphrase_on_device: str = "",
    passphrase_in_message: str | None = None,
    on_device: bool = True,
    error_message: str | None = None,
) -> None:

    res = session.call_raw(
        messages.ThpCreateNewSession(
            passphrase=passphrase_in_message, on_device=on_device
        )
    )

    if error_message is not None:
        # Failed to create session - expected
        assert isinstance(res, messages.Failure)
        assert res.code == messages.FailureType.DataError
        assert res.message == error_message
        return

    # Device waits for passphrase entry on device
    assert isinstance(res, messages.ButtonRequest)
    assert res.code == messages.ButtonRequestType.PassphraseEntry

    # Input passphrase on device
    # TODO handle empty passphrase better - check that confirm screen is displayed
    session.debug.input(passphrase_on_device)
    session.write(messages.ButtonAck())
    response_success = session.read()

    # Session was Successfully created
    assert isinstance(response_success, messages.Success)


@pytest.mark.models("core")
@pytest.mark.protocol("thp")
@pytest.mark.setup_client(passphrase=True)
def test_create_session_with_passphrase_on_device(session: Session):

    # Set always_on_device to True
    msg = messages.ApplySettings(passphrase_always_on_device=True)
    session.call(msg, expect=messages.Success)

    # Assert session works
    res = session.client.ping("PING")
    assert res == "PING"

    _create_session_passphrase_on_device(session, passphrase_on_device="XYZ")
    assert btc.get_public_node(session, ADDRESS_N).xpub == XPUB_XYZ

    _create_session_passphrase_on_device(session)
    assert btc.get_public_node(session, ADDRESS_N).xpub == XPUB

    # Cannot use passphrase in-message when always_on_device
    _create_session_passphrase_on_device(
        session,
        passphrase_in_message="xyz",
        on_device=False,
        error_message=DATA_ERROR_ON_DEVICE,
    )
    # Cannot use empty passphrase in-message when always_on_device
    _create_session_passphrase_on_device(
        session,
        passphrase_in_message="",
        on_device=False,
        error_message=DATA_ERROR_ON_DEVICE,
    )
    # Message with both on_device and passphrase in-message is invalid
    _create_session_passphrase_on_device(
        session,
        passphrase_in_message="",
        on_device=True,
        error_message=DATA_ERROR_INVALID_MESSAGE,
    )

    _create_session_passphrase_on_device(session, passphrase_on_device="XYZ")
    assert btc.get_public_node(session, ADDRESS_N).xpub == XPUB_XYZ
