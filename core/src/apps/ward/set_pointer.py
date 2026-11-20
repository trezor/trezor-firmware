from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardLeafAck, WardMutationApplied, WardSetPointer


async def set_pointer(msg: WardSetPointer) -> "WardLeafAck | WardMutationApplied":
    """WardSetPointer handler: confirm making an entry point at another, then build its leaf.

    The value is the target's leaf_identity, always in the caller's own app_id, so a read follows
    it one hop and returns the target's value. Pulls the current entry first so an overwrite
    names what it replaces. The target is not pulled: it need not exist yet, and a read of a
    pointer to an absent target is "not found". Requires a synced session.
    """
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import (
        add_freshness,
        commit_change,
        display_bytes,
        display_content,
        entry_props,
        online,
        pull_leaf,
        require_key,
    )
    from .keys import ENTRY_TYPE_POINTER, entry_key_for
    from .leaf import pack_identity

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    target = msg.target_identifier
    if not target:
        raise DataError("target_identifier is required")
    if target == identifier:
        raise DataError("WARD: an entry cannot point at itself")
    value = pack_identity(target, app_id)

    entry_key = await entry_key_for(app_id, identifier)

    if not await online():
        raise DataError("WARD: sync first to set a pointer")

    old, old_leaf, material = await pull_leaf(entry_key)

    props = entry_props(app_id, identifier)
    if old is None:
        title = "Add pointer"
    else:
        title = "Update pointer"
        props.append(("Replaces", display_content(old), True))
    props.append(("Points to", display_bytes(target), True))
    add_freshness(props)

    await confirm_properties("ward_set_pointer", title, props)

    return await commit_change(
        entry_key,
        app_id,
        identifier,
        value,
        old_leaf,
        material,
        entry_type=ENTRY_TYPE_POINTER,
    )
