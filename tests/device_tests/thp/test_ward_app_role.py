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

"""Which application may operate WARD, and what happens to the ones that may not.

WHAT IS BEING TESTED. The first host to send a user-facing WARD message is pinned in flash by its
static key, after the user holds to confirm; every other host is refused from then on, and
`WardResetApp` is the only way back. See `apps.ward.app_role`.

WHY THIS FILE DOES NOT USE `ward_app_pinned`. Every other WARD test module imports that fixture so it
can get on with what it is actually about. These tests are about the pinning itself, so they need an
unpinned device -- which is why the fixture is opt-in per module rather than autouse everywhere.

THP, because the whole mechanism is about host static keys: a second host means a second handshake
with a key of its own, and a codec-protocol context has no key at all.
"""

import pytest

from trezorlib import exceptions
from trezorlib import messages as m
from trezorlib import ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_app import reject_flow
from .connect import prepare_channel_for_pairing

pytestmark = [
    pytest.mark.protocol("thp"),
    pytest.mark.models("core"),
]

_APP = "TEST"
_IDENT = b"addr1"

_KEY_A = b"\x71" * 32
_KEY_B = b"\x72" * 32


def _offline_read(session: Session) -> m.WardQueueGetAck:
    """The cheapest host-facing WARD request there is: the device's own store, no backend.

    Used as the probe throughout, because what is under test is who may ask -- not what the answer
    is. It reaches the role check the same way every other WARD message does.
    """
    return ward.queue_get_entry(session, app_id=_APP, identifier=_IDENT)


def _screens(ctx) -> list[str]:
    """The ButtonRequest names raised so far in this block.

    ASSERTED INSTEAD OF `set_expected_responses`, and for a reason worth keeping: a WARD request
    raises its OWN screen too, so a fixed sequence here would be pinning `ward_queue_get_entry`
    alongside the one screen these tests are about -- and `actual_responses` carries whatever the
    session setup did before the block as well. Filtering to the names says exactly what is meant:
    the role screen appeared, or it did not.
    """
    return [r.name for r in ctx.actual_responses if type(r).__name__ == "ButtonRequest"]


def _rehandshake(test_ctx: Client, host_static_privkey: bytes) -> Session:
    """A fresh channel with a chosen static key, paired, and a session on it.

    THE KEY IS THE IDENTITY, so this is what "a different application" means at this layer. Pairing
    is skipped as the rest of the THP tests skip it: it proves the host holds a credential, which
    every host in this file does, and is exactly the granularity the pin exists to improve on.
    """
    pairing = prepare_channel_for_pairing(
        test_ctx, host_static_privkey=host_static_privkey
    )
    pairing.skip()

    return test_ctx.get_session()


def test_the_first_app_to_ask_is_pinned_after_a_held_confirmation(
    client: Client,
) -> None:
    """One screen, then silence. The role costs a confirmation once and nothing afterwards.

    The second request asserts the ABSENCE of the ButtonRequest, which is the half that matters for
    every other test in the suite: a device that asked again per operation would make the sequences
    those tests pin unpredictable, and would train a user to hold through anything.
    """
    session = _rehandshake(client, _KEY_A)

    with session.test_ctx as ctx:
        ctx.actual_responses.clear()
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        _offline_read(session)
        # The role is asked about BEFORE the request is looked at, which is why it comes first.
        assert _screens(ctx) == ["ward_app_role", "ward_queue_get_entry"]

    with session.test_ctx as ctx:
        ctx.actual_responses.clear()
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        _offline_read(session)
        assert _screens(ctx) == ["ward_queue_get_entry"]


def test_another_app_is_refused(client: Client) -> None:
    """A second host, with a key of its own, gets a failure rather than a screen.

    REFUSED, NOT OFFERED A TAKEOVER, and the assertion is deliberately about both halves: the
    request fails, and no ButtonRequest was raised on the way. A screen here would mean any host
    could summon a "let me have WARD" prompt by asking, which is not a pin but a phishing surface.
    """
    session_a = _rehandshake(client, _KEY_A)
    with session_a.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session_a).get())
        _offline_read(session_a)

    session_b = _rehandshake(client, _KEY_B)
    with session_b.test_ctx as ctx:
        ctx.set_expected_responses([m.Failure])
        with pytest.raises(exceptions.TrezorFailure):
            _offline_read(session_b)


def test_every_host_facing_ward_message_is_covered(client: Client) -> None:
    """The check is installed once, for a LIST of messages, and this is that list's test.

    A filter covers whatever it is told to cover, so the failure mode is a message left out --
    silently, since nothing about a missing check looks wrong from the outside. So every request in
    `apps.ward.app_role._ward_app_messages` is sent by the wrong host here and every one must fail.

    THE REQUESTS ARE DELIBERATELY MALFORMED OR INAPPLICABLE, and it does not weaken the test: the
    role check runs before the handler looks at the request at all, so a refusal on those grounds is
    the only outcome available -- and if the role check were missing, these would fail differently
    (a DataError about the request, not about the role) or succeed outright. What is asserted is that
    the answer is the role's.
    """
    session_a = _rehandshake(client, _KEY_A)
    with session_a.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session_a).get())
        _offline_read(session_a)

    session_b = _rehandshake(client, _KEY_B)

    requests = [
        m.WardGetEntry(app_id=_APP, identifier=_IDENT),
        m.WardSetEntry(app_id=_APP, identifier=_IDENT, value=b"v"),
        m.WardDeleteEntry(app_id=_APP, identifier=_IDENT),
        m.WardSync(),
        m.WardIngestAttestation(),
        m.WardReconcile(),
        m.WardVerifyChain(),
        m.WardRollback(),
        m.WardRecoverCounter(),
        m.WardPinCachedEntry(app_id=_APP, identifier=_IDENT),
        m.WardEraseCachedEntry(app_id=_APP, identifier=_IDENT),
        m.WardFlushQueue(),
        m.WardQueueSetEntry(app_id=_APP, identifier=_IDENT, value=b"v"),
        m.WardQueueDeleteEntry(app_id=_APP, identifier=_IDENT),
        m.WardQueueGetEntry(app_id=_APP, identifier=_IDENT),
    ]

    for request in requests:
        answer = session_b.call_raw(request)
        assert isinstance(answer, m.Failure), (
            f"{type(request).__name__} was answered with "
            f"{type(answer).__name__} by a host that does not hold the WARD role"
        )
        assert "WARD" in (answer.message or "") or "application" in (
            answer.message or ""
        ), f"{type(request).__name__} failed for some other reason: {answer.message}"


def test_reset_hands_the_role_to_whoever_asks_next(client: Client) -> None:
    """The way back, and it is available to a host that holds nothing.

    That is the whole point of the escape hatch: the reason to send it is that the pinned app cannot
    ask any more, so requiring the role would make the pin unrecoverable. What stands in its way is
    the held screen and nothing else.
    """
    session_a = _rehandshake(client, _KEY_A)
    with session_a.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session_a).get())
        _offline_read(session_a)

    session_b = _rehandshake(client, _KEY_B)

    # Refused before the reset...
    with pytest.raises(exceptions.TrezorFailure):
        _offline_read(session_b)

    with session_b.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_reset_app"), m.WardResetAppAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session_b).get())
        ack = ward.reset_app(session_b)
    # `was_bound` is the difference between retiring a pin and there having been none, which success
    # alone does not carry.
    assert ack.was_bound is True

    # ...and now the ordinary first-use path, for the host that asked.
    with session_b.test_ctx as ctx:
        ctx.actual_responses.clear()
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session_b).get())
        _offline_read(session_b)
        assert _screens(ctx) == ["ward_app_role", "ward_queue_get_entry"]


def test_resetting_an_unclaimed_device_says_so(client: Client) -> None:
    """It succeeds and reports `was_bound=False` rather than failing.

    A host recovering from a lost app cannot know whether a pin exists, so asking is legitimate --
    and the screen is shown either way, so that "is anything bound?" cannot be answered by a request
    the user never sees.
    """
    session = _rehandshake(client, _KEY_A)

    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_reset_app"), m.WardResetAppAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ack = ward.reset_app(session)

    assert ack.was_bound is False


def test_a_refused_confirmation_grants_nothing(client: Client) -> None:
    """Declining the screen must leave the role unclaimed, not pin the asker anyway.

    Otherwise "no" would be indistinguishable from "yes" a moment later, and the confirmation would
    be decoration: the second request below would find the pin already in place and sail through
    without asking anyone.
    """
    session = _rehandshake(client, _KEY_A)

    with session.test_ctx as ctx:
        ctx.set_expected_responses([m.ButtonRequest(name="ward_app_role"), m.Failure])
        ctx.set_input_flow(reject_flow(session))
        # `Cancelled`, not `TrezorFailure`: the device answers Failure_ActionCancelled and trezorlib
        # turns that one code into its own exception. Worth pinning rather than widening -- a refused
        # screen and a refused ROLE are different answers, and only the second is a DataError.
        with pytest.raises(exceptions.Cancelled):
            _offline_read(session)

    # Asked again, the device asks again -- which it would not if the refusal had pinned anything.
    with session.test_ctx as ctx:
        ctx.actual_responses.clear()
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        _offline_read(session)
        assert _screens(ctx) == ["ward_app_role", "ward_queue_get_entry"]
