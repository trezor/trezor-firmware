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

    from .attest import root_mac
    from .cas import auth_commit
    from .common import WARNING_UNVERIFIED, display_bytes, pull_leaf, require_key
    from .keys import (
        ENTRY_TYPE_ADDRESS,
        derive_k_auth,
        derive_k_mac,
        derive_ward_id,
        entry_key_for,
    )
    from .leaf import EMPTY_PART, make_leaf_content, make_leaf_identity
    from .root import get_counter, get_root, set_root
    from .trie import compute_new_root

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)
    current, old_leaf, material = await pull_leaf(entry_key, key_type)
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

    # Derive the root the deletion leaves behind. The sibling decomposition matters here:
    # removing a leaf re-parents its sibling, whose hash commits to a skiplen measured
    # from its old parent -- see `trie.compute_new_root`.
    proof, _witness_key, _witness_commit, sibling_node = material
    from_root = await get_root()
    counter = await get_counter() + 1
    new_root = compute_new_root(
        entry_key,
        old_leaf,
        None,
        proof,
        from_root,
        sibling_node=sibling_node,
    )
    await set_root(new_root, counter)

    return WARDLeafAck(
        entry_key=entry_key,
        identity=make_leaf_identity(key_type, EMPTY_PART),
        content=make_leaf_content(EMPTY_PART),
        counter=counter,
        mac=root_mac(await derive_k_mac(), await derive_ward_id(), counter, new_root),
        auth_commit=auth_commit(
            await derive_k_auth(),
            await derive_ward_id(),
            counter - 1,
            from_root,
            counter,
            new_root,
        ),
    )
