from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardGetEntry


async def get_entry(msg: WardGetEntry) -> Success:
    """WardGetEntry handler: pull the entry, verify it, show it; returns only Success.

    REFUSES WITHOUT A SYNCED SESSION rather than falling back to the local copy -- a fallback
    would let a host force an old value onto the screen by failing the proof. The local read is
    `WardQueueGetEntry`. The value is on screen before the user acts, which is safe only because
    `app_role` limits who may trigger a read.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import (
        WARNING_UNVERIFIED,
        display_bytes,
        online,
        pull_entry,
        require_key,
    )
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]

    if not await online():
        raise DataError("WARD: sync first, or read the local copy with WardQueueGetEntry")

    value = await pull_entry(entry_key, key_type)
    # Absent ("no such entry") and empty are different answers on screen.
    if value is None:
        title = "Entry not found"
        props.append(("Result", "The host holds no entry for this key.", False))
    else:
        title = "Unverified entry"
        props.append(("Value", display_bytes(value), True))
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_get_entry", title, props)

    return Success(message="WARD entry shown")
