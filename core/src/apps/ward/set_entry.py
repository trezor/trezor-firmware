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
        display_bytes,
        finish_write,
        online,
        pull_leaf,
        require_key,
    )
    from .keys import (
        ENTRY_TYPE_ADDRESS,
        derive_k_data,
        derive_k_ident,
        entry_key_for,
    )
    from .leaf import (
        encode_content,
        encode_identity,
        make_leaf_content,
        make_leaf_identity,
    )
    from .root import get_counter, get_root, root_for_write
    from .trie import compute_new_root

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

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]
    if old is None:
        title = "Add entry"
    else:
        title = "Update entry"
        props.append(("Replaces", display_bytes(old), True))
    props.append(("New value", display_bytes(value), True))
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_set_entry", title, props)

    # Sealed only after confirmation; the leaf is stamped with the counter it lands at (C_leaf).
    from_root = await get_root()
    counter = await get_counter() + 1
    id_part = encode_identity(
        await derive_k_ident(key_type), entry_key, key_type, identifier, app_id
    )
    val_part = encode_content(
        await derive_k_data(key_type), entry_key, key_type, value, c_leaf=counter
    )

    # The device DERIVES its new root from proven state rather than being told one.
    proof, witness_entry_key, witness_commit = material
    new_root = compute_new_root(
        entry_key,
        old_leaf,
        (key_type, id_part, val_part),
        proof,
        root_for_write(from_root),
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )

    return await finish_write(
        entry_key,
        make_leaf_identity(key_type, id_part),
        make_leaf_content(val_part),
        from_root,
        counter,
        new_root,
    )
