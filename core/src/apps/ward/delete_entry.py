from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDDeleteEntry, WARDLeafAck


async def delete_entry(msg: WARDDeleteEntry) -> WARDLeafAck:
    """WARDDeleteEntry handler: confirm removing a host-held entry.

    The device pulls the entry first so the screen can name what is being removed --
    confirming a deletion by key alone tells the user nothing about what they are
    losing. Held-to-confirm, because it is destructive and unlike a write it cannot be
    undone by repeating it with the old value (the host is the only place that value
    still exists).

    Returns a leaf with BOTH PARTS EMPTY. That is the wire's way of saying "deleted",
    and the host removes the record entirely -- WARD does a full delete, so a later
    non-membership proof for this path must succeed. Note the reference keeps the
    identity part alive on delete, leaving a self-describing tombstone; we do not, since
    a tombstone that survives is a record of which entries once existed.
    """
    from trezor.messages import WARDLeafAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import WARNING_UNVERIFIED, display_bytes, pull_entry, require_key
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for
    from .leaf import EMPTY_PART, make_leaf_content, make_leaf_identity

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)
    current = await pull_entry(entry_key, key_type)
    if current is None:
        # The host asked to delete this entry and, answering the pull, reported that it
        # does not hold it -- a contradiction, so one side is wrong. Refuse rather than
        # return a leaf the host could bank as a completed delete. This deliberately
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

    return WARDLeafAck(
        entry_key=entry_key,
        identity=make_leaf_identity(key_type, EMPTY_PART),
        content=make_leaf_content(EMPTY_PART),
    )
