from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardFlushQueue, WardLeafAck


async def flush_queue(msg: WardFlushQueue) -> WardLeafAck:
    """WardFlushQueue handler: publish ONE queued change, sealed and re-derived.

    WHY A QUEUED CHANGE CANNOT SIMPLY BE SENT. It was made with no host, so the device could
    not pull, could not prove current state, and could not derive a root. What it stored was
    an INTENT -- a value for a path -- and nothing more. An intent formed while the tree was
    at R is not applicable at R': its proof material and its derived root are both relative to
    a state that has moved. So this re-derives it against CURRENT state, pulling the path's
    present leaf and proving it against the trusted root before computing anything. That is
    mandatory machinery, not an optimisation.

    SEALING HAPPENS HERE. Records sit in flash in the clear because `storage.c` already
    encrypts and authenticates them under a PIN-derived key; that protection ends at the
    device boundary, so the parts are built on the way out and nowhere else. See
    `storage/ward.py` for the full argument.

    ONE PER REQUEST, and the host repeats until `remaining` is zero. A queued batch has no
    transaction to apply under -- Evolu's CRDT offers none -- so a partial application is
    always possible; one change per round-trip bounds it to a single step and makes each step
    independently retryable, rather than pretending the batch is atomic.

    NO CONFIRMATION SCREEN. The user held to confirm when the change was queued. Asking again
    would be asking about a decision already made -- the same reasoning `reconcile` gives for
    not re-confirming a recovered counter -- and a screen that always means "yes, the thing
    you already agreed to" is one that gets approved without being read.

    THE RECORD STAYS PENDING. Handing the leaf to the host is not the change taking effect;
    the head moves when the WM confirms the counter, which is `reconcile`'s job and where the
    flag is cleared. A host that never publishes leaves the change queued and re-sendable --
    fail-closed and recoverable, rather than a silent loss.

    REQUIRES A SYNCED SESSION, because with no trusted root there is nothing to derive
    against and nothing to prove the pulled leaf with. Refusing is the honest answer: the
    device cannot publish while it cannot see current state.
    """
    from trezor.messages import WardLeafAck
    from trezor.wire import DataError

    from . import offline_store
    from . import round as sync_round
    from .attest import root_mac
    from .cas import auth_commit, sig_commit
    from .common import pull_leaf, require_initialized
    from .keys import (
        derive_k_auth,
        derive_k_data,
        derive_k_ident,
        derive_k_mac,
        derive_k_sig,
        derive_ward_id,
    )
    from .leaf import (
        encode_content,
        encode_identity,
        make_leaf_content,
        make_leaf_identity,
    )
    from .root import get_counter, get_root
    from .trie import compute_new_root

    require_initialized()

    if not sync_round.is_online():
        raise DataError("WARD: sync before publishing queued changes")

    entry = await offline_store.next_unsent()
    if entry is None:
        return WardLeafAck(remaining=0)

    key_type = entry.key_type
    entry_key = entry.entry_key

    # Re-derivation against CURRENT state. This proves the path's present leaf against the
    # trusted root, so the new root below is computed from a state the host had to
    # demonstrate rather than one it asserted.
    _old_value, old_leaf, material = await pull_leaf(entry_key, key_type)

    from_root = await get_root()
    counter = await get_counter() + 1

    id_part = encode_identity(
        await derive_k_ident(key_type),
        entry_key,
        key_type,
        entry.identifier,
        entry.app_id,
        device_id=entry.device_id,
    )
    val_part = encode_content(
        await derive_k_data(key_type),
        entry_key,
        key_type,
        entry.value,
        c_leaf=counter,
    )

    proof, witness_entry_key, witness_commit = material
    new_root = compute_new_root(
        entry_key,
        old_leaf,
        (key_type, id_part, val_part),
        proof,
        from_root,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )

    # Record the counter this publication claimed, keeping the record PENDING. That number is
    # what `reconcile` later compares an attested counter against to decide the change has
    # landed. Written before the ack goes out so a lost response cannot leave the device
    # unable to recognise its own change being confirmed.
    await offline_store.put(
        entry_key,
        key_type,
        entry.app_id,
        entry.identifier,
        entry.device_id,
        entry.value,
        counter,
        True,
    )

    remaining = await offline_store.count_unsent()

    return WardLeafAck(
        entry_key=entry_key,
        identity=make_leaf_identity(key_type, id_part),
        content=make_leaf_content(val_part),
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
        auth_sig=sig_commit(
            await derive_k_sig(),
            await derive_ward_id(),
            counter - 1,
            from_root,
            counter,
            new_root,
        ),
        # Counts only records NOT YET HANDED OVER, so this one is excluded -- it now carries
        # an assigned counter. The host loops while this is non-zero; a record that was sent
        # but never confirmed comes back only through `reconcile_pending`, which is the point
        # at which the device can tell whether it landed.
        remaining=remaining,
    )
