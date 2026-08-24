"""Which application may operate WARD on this device, and how the device knows.

WHAT THIS IS NOT. It is not a boundary between "the wallet" and "the WARD app". The user-facing WARD
messages arrive on the ORDINARY interface, the same one a wallet uses, and they are expected to come
from a wallet eventually -- today's app is a proof of concept for exactly that. What crosses a channel
of its own is the replica traffic behind them, and that is the daemon's business, not this file's. See
`docs/core/misc/ward-channels.md`.

WHAT IT IS. A bound on how many parties may operate WARD on one device: ONE, chosen by the user.
Several hosts can be connected on that interface at once, and pairing does not tell them apart -- it
proves a host holds a credential this device issued, and every paired host holds one. So "some paired
host" is the wrong granularity for "may read, write and queue this wallet's WARD entries", and without
a pin any connected host has that power. The daemon is already pinned this way
(`apps.ward.service`), and this is deliberately the same shape so neither has to be reasoned about
alone.

WHAT IT DOES NOT REACH. `app_id` still arrives on the wire, so the pinned host may name any app's
entries; this narrows who can do that to one host rather than stopping it. See the gap recorded in
`common.require_key`.

TRUST ON FIRST USE, WITH A HELD CONFIRMATION. There is no useful moment before the first request at
which an app could announce itself -- the request IS the announcement, and refusing until some
earlier message had arrived would only move the question one message earlier. So the first WARD
request pins the app that made it, and the user holds to allow it; every request after that from that
same key is silent, and every request from any other key is refused.

REFUSED, NOT OFFERED A TAKEOVER. A screen that any host could summon by asking is not a pin: it
would turn the boundary into a phishing question, and the honest answer to "another app is asking" is
that the user did not ask for another app. Recovering from a lost app key is an ownership migration
with a user decision in it, and it lives in `apps.ward.reset_app`.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor import protobuf
    from trezor.wire import Handler, Msg


def _app_label() -> str:
    """The name to put on the pinning screen. Best effort, and never trusted.

    It comes from the pairing credential this device itself issued, so it is not a claim the current
    request makes -- but it is still a name a host chose for itself, and two apps may choose the
    same one. What is actually pinned is the static key; this is only there so the screen says
    something more useful than "an application".
    """
    from trezor.wire import context

    channel = getattr(context.get_context(), "channel", None)
    credential = channel.credential if channel is not None else None
    if credential is None:
        # Unpaired, or paired by a route that issues no credential -- the debug skip-pairing
        # shortcut is one. Named honestly rather than left blank: the user is being asked about an
        # application the device cannot name.
        return "an unnamed application"

    metadata = credential.cred_metadata
    app_name = metadata.app_name or ""
    host_name = metadata.host_name or ""
    if app_name and host_name:
        return app_name + " on " + host_name
    return app_name or host_name or "an unnamed application"


async def require_ward_app() -> None:
    """Refuse unless this channel belongs to the app that holds the WARD role.

    RUN BEFORE THE HANDLER, from the wire filter below, and therefore before the request has been
    looked at at all. That order is deliberate: the question here is who is speaking, not what they
    said, and a request that turns out to be malformed does not make its sender more entitled to ask
    it.

    Raises `DataError` in every refusing case, which is the failure every WARD handler already
    raises -- so a caller without standing gets the same shape of answer as one that asked wrongly,
    and learns nothing from the difference.
    """
    from storage import ward as storage_ward
    from trezor import wire
    from trezor.wire import context

    ctx = context.get_context()
    channel = getattr(ctx, "channel", None)
    if channel is None:
        # NO CHANNEL, NO IDENTITY, NO WARD. A codec-protocol context has no static key at all, so
        # there is nothing to pin and nothing to compare -- and "cannot identify the caller" must
        # fail closed here, or the whole pin is optional for anyone able to reach the device over
        # the older protocol.
        raise wire.DataError("WARD needs a paired THP channel")

    host_key = channel.get_host_static_public_key()
    pinned = storage_ward.get_app_host_key()

    if pinned == host_key:
        # The ordinary case, and it writes nothing and shows nothing: an app that already holds the
        # role must not pay a screen per operation, and a flash write per request would be worse
        # than useless.
        return

    if pinned is not None:
        # Not repairable by connecting a different app: the pin is in flash precisely so that
        # unplugging the device does not clear it.
        raise wire.DataError("another application holds the WARD app role")

    # --- first use ---------------------------------------------------------------------------
    #
    # PINNING IS A FLASH WRITE, so it needs the device unlocked, and saying so beats letting
    # `config.set` fail with an opaque storage error at the one moment the caller can least
    # interpret it. Stated before the screen rather than after, so the user is not asked to allow
    # something that then cannot be stored.
    from trezor import config

    if not config.is_unlocked():
        raise wire.DataError("unlock the device to grant the WARD app role")

    from trezor.ui.layouts import confirm_properties

    # HELD, and the wording names the durable consequence rather than the request in front of it:
    # what the user is allowing is not this one read, it is which application owns WARD on this
    # device from here on.
    await confirm_properties(
        "ward_app_role",
        "Allow WARD access",
        [
            ("Application", _app_label(), False),
            (
                "Grants",
                "Reading, writing and queueing this wallet's WARD entries, from now on.",
                False,
            ),
            (
                "Note",
                "Only one application can do this. Others will be refused until you reset it.",
                False,
            ),
        ],
        hold=True,
    )

    storage_ward.set_app_host_key(host_key)


# --- how it gets called ----------------------------------------------------------------------
#
# A WIRE FILTER, NOT A LINE IN EVERY HANDLER. `trezor.wire.filters` exists for exactly this shape --
# "run something before this message reaches its handler, or refuse it" -- and it is what the PIN
# lock uses (`apps.common.lock_manager._pinlock_filter`). Sixteen call sites would have been sixteen
# chances to forget, and the one that got forgotten would be a WARD operation any paired host could
# perform: the failure would be silent, because nothing about a missing check looks wrong.
#
# ORDER MATTERS AND IT IS ARRANGED IN `apps.base`: this filter is appended BEFORE the pinlock one, so
# the pinlock behaviour still triggers first and the device is unlocked before the role is decided.
# The unlock check inside `require_ward_app` therefore rarely fires -- it stays because "cannot write
# flash" must fail closed on its own terms, not because some other filter usually got there first.
_MESSAGES: tuple[int, ...] | None = None


def _ward_app_messages() -> "tuple[int, ...]":
    """The host-facing WARD messages, which is to say: the ones the WARD app may send.

    BUILT ON FIRST USE, not at import: this module is imported during boot to install the filter,
    and `MessageType` in a module-level tuple would be RAM spent before any WARD message exists.

    THE LIST IS THE POLICY, so it is here rather than derived from `workflow_handlers`: being
    dispatchable and being a WARD operation are different properties, and a message added to the
    registry must be classified deliberately. `tests/device_tests/ward/test_app_role.py` enumerates
    the registry's WARD entries and fails if one is missing from here, so "deliberately" is enforced
    rather than hoped for.

    NOT INCLUDED, each for its own reason:
      WardServiceOpen   the daemon's, on the WARD interface, with a pin of its own.
      WardResetApp      the escape hatch for a lost app key -- requiring the role to retire the pin
                        would make the pin unrecoverable, which is the one thing it must not be.
    """
    global _MESSAGES
    if _MESSAGES is None:
        from trezor.enums import MessageType as MT

        _MESSAGES = (
            MT.WardGetEntry,
            MT.WardSetEntry,
            MT.WardDeleteEntry,
            MT.WardSync,
            MT.WardIngestAttestation,
            MT.WardReconcile,
            MT.WardVerifyChain,
            MT.WardRollback,
            MT.WardRecoverCounter,
            MT.WardPinCachedEntry,
            MT.WardEraseCachedEntry,
            MT.WardFlushQueue,
            MT.WardQueueSetEntry,
            MT.WardQueueDeleteEntry,
            MT.WardQueueGetEntry,
            # The daemon binding is WARD state, so changing it is a WARD operation: an app that may
            # not read an entry may not decide which daemon serves them either.
            MT.WardResetService,
        )
    return _MESSAGES


def ward_app_filter(msg_type: int, prev_handler: "Handler[Msg]") -> "Handler[Msg]":
    """Wrap a WARD handler with the role check; leave every other message alone."""
    if msg_type not in _ward_app_messages():
        return prev_handler

    async def wrapper(msg: "Msg") -> "protobuf.MessageType":
        await require_ward_app()

        return await prev_handler(msg)

    return wrapper
