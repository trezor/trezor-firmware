from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardFlushQueue, WardFlushQueueAck


async def flush_queue(msg: WardFlushQueue) -> WardFlushQueueAck:
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
    from trezor.messages import WardFlushQueueAck
    from trezor.wire import DataError

    from . import offline_store
    from . import round as sync_round
    from .attest import root_mac
    from .cas import auth_commit, sig_commit
    from .common import pull_leaf, require_initialized
    from .keys import (
        ENTRY_TYPE_ADDRESS,
        derive_k_auth,
        derive_k_data,
        derive_k_ident,
        derive_k_mac,
        derive_k_sig,
        derive_ward_id,
        entry_key_for,
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

    # NAMED, OR THE NEXT ONE. A host that says which entry to publish gets that one -- and that is
    # the only way a COMPACT record can be published, since such a record holds a hash of its identity
    # and a hash cannot be turned back into a keyed path. Unnamed, this takes the next queued change
    # as it always has.
    app_id, identifier = msg.app_id, msg.identifier
    key_type = ENTRY_TYPE_ADDRESS

    if app_id is not None and identifier is not None:
        status, entry = await offline_store.get(key_type, app_id, identifier)
        if status != offline_store.VALID or entry is None or not entry.pending:
            raise DataError("WARD: no queued change for this entry")
        # AN ALREADY-OFFERED CHANGE MAY BE OFFERED AGAIN when the caller names it. The offered flag
        # exists to stop the UNNAMED loop handing the same change out forever; a caller asking for
        # this entry by name is saying it did not get it, or lost the response, and refusing would
        # strand the change -- a compact record offered by a session that then dropped has no claim
        # left for a reconcile to settle, so this is its only way back.
    else:
        entry = await offline_store.next_unsent()
        if entry is None:
            return WardFlushQueueAck(remaining=0)
        if entry.compact:
            # The device cannot say WHICH entry this is -- that is what the compact form gives up --
            # so it cannot ask for the identity by name either. The host holds the backup and can.
            raise DataError(
                "WARD: the next queued change is stored compactly; name it with app_id and identifier"
            )
        app_id, identifier = entry.app_id, entry.identifier
        key_type = entry.key_type
    # THE KEYED PATH IS ASSIGNED HERE. A queued change has none -- it is not in the trie -- so the
    # identity (from the record, or from the request when the record is compact) is turned into a path
    # at the moment of publication, which is the only moment a path means anything.
    entry_key = await entry_key_for(app_id, identifier, key_type)

    # Re-derivation against CURRENT state. This proves the path's present leaf against the
    # trusted root, so the new root below is computed from a state the host had to
    # demonstrate rather than one it asserted.
    _old_value, old_leaf, material = await pull_leaf(entry_key, key_type)

    from_root = await get_root()
    counter = await get_counter() + 1

    # The identity SEALED into the leaf is the one that was verified against the record, not whatever
    # the record happens to carry: for a compact record those fields are empty, and the request is
    # where its identity came from.
    id_part = encode_identity(
        await derive_k_ident(key_type),
        entry_key,
        key_type,
        identifier,
        app_id,
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

    # The transition's own authorisation, computed here rather than in the ack below because the
    # CLAIM has to carry it: it is what lets a later chain sync decide whether THIS change landed,
    # rather than inferring it from the counter alone.
    step = auth_commit(
        await derive_k_auth(),
        await derive_ward_id(),
        counter - 1,
        from_root,
        counter,
        new_root,
    )

    # Mark the record OFFERED, keeping it PENDING. That flag is what stops this loop offering the
    # same change forever, and the claim beside it is what a later adoption settles it by. Both are
    # written before the ack goes out, so a lost response cannot leave the device offering it again
    # as though nothing had happened.
    await offline_store.mark_offered(entry, counter, step)

    remaining = await offline_store.count_unsent()

    return WardFlushQueueAck(
        entry_key=entry_key,
        identity=make_leaf_identity(key_type, id_part),
        content=make_leaf_content(val_part),
        counter=counter,
        mac=root_mac(await derive_k_mac(), await derive_ward_id(), counter, new_root),
        auth_commit=step,
        auth_sig=sig_commit(
            await derive_k_sig(),
            await derive_ward_id(),
            counter - 1,
            from_root,
            counter,
            new_root,
        ),
        # Counts only records NOT YET HANDED OVER, so this one is excluded -- it is marked offered
        # now. The host loops while this is non-zero; a record that was sent but never confirmed
        # comes back only through `reconcile_pending`, which is the point at which the device can
        # tell the head has moved at all.
        remaining=remaining,
    )
