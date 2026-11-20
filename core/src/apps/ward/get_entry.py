from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardGetEntry


async def get_entry(msg: WardGetEntry) -> Success:
    """WardGetEntry handler: pull the entry, verify it, show it; returns only Success.

    FRESH when this session adopted a WM-attested head: the screen then carries no warning. With no
    WM to attest (a failed or skipped sync) the entry is still proved, against the head this
    device last adopted, and shown as unverified with the warning -- a host that fails the sync
    on purpose gets an old value onto the screen only under that warning. With no stored head at
    all there is nothing to prove against, and it refuses. The device-local read is
    `WardQueueGetEntry`. The value is on screen before the user acts, which is safe only because
    `app_role` limits who may trigger a read.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import (
        add_freshness,
        display_bytes,
        entry_props,
        is_fresh,
        online,
        read_entry,
        require_key,
    )
    from .root import get_root

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    props = entry_props(app_id, identifier)

    # A service build drives a sync here. A failed one leaves the read on the stored head; with no
    # head to fall back on, why the sync failed is the answer.
    try:
        await online()
    except Exception:
        if await get_root() is None:
            raise
    if not is_fresh() and await get_root() is None:
        raise DataError("WARD: sync first, or read the local copy with WardQueueGetEntry")

    value, target = await read_entry(app_id, identifier)
    if target is not None:
        props.append(("Points to", display_bytes(target), True))
    # Absent ("no such entry") and empty are different answers on screen.
    if value is None:
        title = "Entry not found"
        props.append(("Result", "The host holds no entry for this key.", False))
    else:
        title = "Entry" if is_fresh() else "Unverified entry"
        props.append(("Value", display_bytes(value), True))
    add_freshness(props)

    await confirm_properties("ward_get_entry", title, props)

    return Success(message="WARD entry shown")
