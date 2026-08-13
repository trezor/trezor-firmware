from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WARDDeleteEntry


async def delete_entry(msg: WARDDeleteEntry) -> Success:
    """WARDDeleteEntry handler: confirm removing a host-held entry.

    The device pulls the entry first so the screen can name what is being removed --
    confirming a deletion by key alone tells the user nothing about what they are
    losing. Held-to-confirm, because it is destructive and unlike a write it cannot be
    undone by repeating it with the old value (the host is the only place that value
    still exists).

    The device performs no delete. On Success the HOST removes the entry from its own
    store; see `set_entry` for why the device is only a confirmation screen here.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import WARNING_UNVERIFIED, display_bytes, pull_entry, require_key

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    current = await pull_entry(app_id, identifier)
    if current is None:
        # The host asked to delete this entry and, answering the pull, reported that it
        # does not hold it -- a contradiction, so one side is wrong. Refuse rather than
        # return a Success the host could bank as a completed delete. This deliberately
        # makes delete non-idempotent: a no-op delete is a host bug worth surfacing, not
        # a success worth papering over.
        raise DataError("no such entry")

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
        ("Deleting value", display_bytes(current), True),
        WARNING_UNVERIFIED,
    ]

    await confirm_properties("ward_delete_entry", "Delete entry", props, hold=True)

    return Success(message="WARD delete confirmed")
