from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardLeafAck, WardMutationApplied, WardSetEntry


async def set_entry(msg: WardSetEntry) -> "WardLeafAck | WardMutationApplied":
    """WardSetEntry handler: confirm creating or replacing an entry, then build its leaf.

    Pulls the current value first so an overwrite names what it replaces. Requires a synced
    session; queueing is `WardQueueSetEntry`.
    """
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import (
        WARNING_UNVERIFIED,
        commit_change,
        display_bytes,
        entry_props,
        online,
        pull_leaf,
        require_key,
    )
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    # Empty is a legitimate value; absent is not -- it would silently blank the entry.
    value = msg.value
    if value is None:
        raise DataError("value is required")

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    if not await online():
        raise DataError("WARD: sync first, or queue the change with WardQueueSetEntry")

    old, old_leaf, material = await pull_leaf(entry_key, key_type)

    props = entry_props(app_id, identifier)
    if old is None:
        title = "Add entry"
    else:
        title = "Update entry"
        props.append(("Replaces", display_bytes(old), True))
    props.append(("New value", display_bytes(value), True))
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_set_entry", title, props)

    return await commit_change(
        entry_key, key_type, app_id, identifier, value, old_leaf, material
    )
