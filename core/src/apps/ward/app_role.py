"""Which application may operate WARD on this device.

ONE, chosen by the user. Pairing cannot tell paired hosts apart, so on THP the first WARD request
pins the sender's static key after a held confirmation; later requests from that key pass silently
and any other key is refused -- never offered a takeover (recovery is `reset_app`). `app_id` still
arrives on the wire, so this narrows who may name entries to one host rather than stopping it.

The v1 codec has no host identity at all. There the user is the control, per operation: before
anything that can put a stored value on screen, `_confirm_reveal` asks with the domain and key
alone, because the operation's own confirmation already shows the value.
"""

from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from trezor import protobuf
    from trezor.wire import Handler, Msg


def _app_label() -> str:
    """The name for the pinning screen, from the pairing credential. Display only, never trusted."""
    from trezor.wire import context

    channel = getattr(context.get_context(), "channel", None)
    credential = channel.credential if channel is not None else None
    if credential is None:
        return "an unnamed application"

    metadata = credential.cred_metadata
    app_name = metadata.app_name or ""
    host_name = metadata.host_name or ""
    if app_name and host_name:
        return app_name + " on " + host_name
    return app_name or host_name or "an unnamed application"


# Operations whose confirmation can show a stored value the caller did not supply. Excluded:
# flush (already confirmed when queued, returns ciphertext), sync plumbing (verified against the
# device's own keys), rollback/rejoin/reset_service (hold, and show counters, not values).
_REVEALING: tuple[int, ...] | None = None


def _revealing_messages() -> "tuple[int, ...]":
    global _REVEALING
    if _REVEALING is None:
        from trezor.enums import MessageType as MT

        _REVEALING = (
            MT.WardGetEntry,
            MT.WardQueueGetEntry,
            MT.WardQueueSetEntry,
            MT.WardQueueDeleteEntry,
            MT.WardPinCachedEntry,
            MT.WardEraseCachedEntry,
        )
    return _REVEALING


async def _confirm_reveal(msg: "Msg") -> None:
    """Ask before a stored value reaches the display -- domain and key only, never the value."""
    from trezor.ui.layouts import confirm_properties

    from .common import display_bytes

    app_id = getattr(msg, "app_id", None) or ""
    identifier = getattr(msg, "identifier", None) or b""

    await confirm_properties(
        "ward_reveal_entry",
        "Reveal entry?",
        [
            ("Domain", app_id, False),
            ("Key", display_bytes(identifier), True),
            (
                "Reveals",
                "A stored value will be shown on this screen.",
                False,
            ),
        ],
    )


async def require_ward_app(msg_type: int, msg: "Msg") -> None:
    """Refuse with `DataError` unless this channel's host holds the WARD role; pin it on first use.

    Runs from the wire filter, before the request is looked at.
    """
    from storage import ward as storage_ward
    from trezor import wire
    from trezor.wire import context

    if not utils.USE_THP:
        # No identity on this transport: the user decides per operation instead.
        if msg_type in _revealing_messages():
            await _confirm_reveal(msg)
        return

    ctx = context.get_context()
    channel = getattr(ctx, "channel", None)
    if channel is None:
        # A THP build with no channel (DebugLink's codec context) must still fail closed.
        raise wire.DataError("WARD needs a paired THP channel")

    host_key = channel.get_host_static_public_key()
    pinned = storage_ward.get_app_host_key()

    if pinned == host_key:
        return

    if pinned is not None:
        raise wire.DataError("another application holds the WARD app role")

    # First use. Pinning is a flash write: refuse a locked device before the screen, not after.
    from trezor import config

    if not config.is_unlocked():
        raise wire.DataError("unlock the device to grant the WARD app role")

    from trezor.ui.layouts import confirm_properties

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


# A wire filter rather than a check in every handler, so none can be forgotten. `apps.base` installs
# it BEFORE the pinlock filter, so the device is unlocked before the role is decided.
_MESSAGES: tuple[int, ...] | None = None


def _ward_app_messages() -> "tuple[int, ...]":
    """The messages only the WARD app may send. Built on first use to spare boot RAM.

    The list is the policy; a device test fails if a registered WARD message is missing. Excluded:
    WardServiceOpen (the daemon's, pinned separately) and WardResetApp (the escape hatch for a
    lost app key).
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
            MT.WardRejoin,
            MT.WardPinCachedEntry,
            MT.WardEraseCachedEntry,
            MT.WardFlushQueue,
            MT.WardQueueSetEntry,
            MT.WardQueueDeleteEntry,
            MT.WardQueueGetEntry,
            MT.WardResetService,
        )
    return _MESSAGES


def ward_app_filter(msg_type: int, prev_handler: "Handler[Msg]") -> "Handler[Msg]":
    """Wrap a WARD handler with the role check; leave every other message alone."""
    if msg_type not in _ward_app_messages():
        return prev_handler

    async def wrapper(msg: "Msg") -> "protobuf.MessageType":
        await require_ward_app(msg_type, msg)

        return await prev_handler(msg)

    return wrapper
