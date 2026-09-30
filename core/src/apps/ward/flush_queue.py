from typing import TYPE_CHECKING

from micropython import const
from trezor import utils

if TYPE_CHECKING:
    from trezor.messages import (
        WardFlushQueue,
        WardFlushQueueAck,
        WardFlushQueueApplied,
    )


async def flush_queue(
    msg: WardFlushQueue,
) -> "WardFlushQueueAck | WardFlushQueueApplied":
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

    ONE PER REQUEST BY DEFAULT, and the host repeats until `remaining` is zero. A queued batch has
    no transaction to apply under -- Evolu's CRDT offers none -- so a partial application is
    always possible; one change per round-trip bounds it to a single step and makes each step
    independently retryable, rather than pretending the batch is atomic.

    A HOST MAY OPT IN TO BATCHING (`max_batch`), and then owns the atomicity: see `_flush_batch`
    and `WardFlushQueue.max_batch` for what it undertakes.

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
    from .cas import auth_commit, wm_sig
    from .common import online, pull_leaf, require_initialized
    from .keys import (
        ENTRY_TYPE_ADDRESS,
        derive_k_auth,
        derive_k_sig,
        derive_k_data,
        derive_k_ident,
        derive_ward_id,
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

    require_initialized()

    if not await online():
        raise DataError("WARD: sync before publishing queued changes")

    # OPT-IN BATCHING. Only when the host asks, only for the unnamed drain, and only on connect: a
    # named flush publishes THAT change, and a service build publishes one change per WardPublish.
    max_batch = msg.max_batch or 1
    named = msg.app_id is not None and msg.identifier is not None
    if max_batch > 1 and not named and not utils.USE_WARD_SERVICE_CHANNEL:
        from .cas import MAX_BATCH

        return await _flush_batch(min(max_batch, MAX_BATCH))

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
            # AN EMPTY DRAIN PUBLISHES NOTHING. No transition, so no claim and no dropped latch --
            # the same reasoning as an idempotent delete. The host's loop ends on the zero.
            if utils.USE_WARD_SERVICE_CHANNEL:
                from trezor.messages import WardFlushQueueApplied

                return WardFlushQueueApplied(remaining=0)
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
        root_for_write(from_root),
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

    # THE WM-FACING AUTHORISATION for the same transition, under K_sig rather than K_auth. Same
    # transition, one statement to two verifiers, plus the WM's HEAD NONCE -- the freshness token
    # it rotates on every transition it accepts. Without the signature the WM has nothing to check
    # when the host publishes, and whoever knows `ward_id` could advance the counter and have every
    # genuine device refused from then on. Without the nonce, an authorisation would stay live
    # wherever its `(counter, root)` predecessor recurred, which a revert can arrange.
    #
    # The nonce comes from this session's latest verified attestation, which `online()` above
    # guarantees exists: a session that has not synced cannot write, and therefore cannot be asked
    # to authorise against a head it has not seen.
    advance = wm_sig(
        await derive_k_sig(),
        await derive_ward_id(),
        counter - 1,
        from_root,
        counter,
        new_root,
        sync_round.require_head_nonce(),
    )

    # Mark the record OFFERED, keeping it PENDING. That flag is what stops this loop offering the
    # same change forever, and the claim beside it is what a later adoption settles it by. Both are
    # written before the ack goes out, so a lost response cannot leave the device offering it again
    # as though nothing had happened.
    await offline_store.mark_offered(entry, counter, step)

    remaining = await offline_store.count_unsent()

    identity = make_leaf_identity(key_type, id_part)
    content = make_leaf_content(val_part)

    if utils.USE_WARD_SERVICE_CHANNEL:
        # THE ORDER ACROSS THE TWO WRITES IS THE SAME ONE `mark_offered` ARGUES FOR, extended by one
        # step: claim, then flag, then drop the latch, then publish. The claim is already in flash
        # by the time the mutation leaves the device, so a publication whose answer is lost is
        # settled by the next sync instead of being stranded.
        from trezor.messages import WardFlushQueueApplied

        from .service import publish

        await publish(entry_key, identity, content, from_root, counter, new_root, step)
        # `remaining` was counted BEFORE the publish and stands regardless of how it went: it
        # describes what is still queued and un-offered, and this record is neither.
        return WardFlushQueueApplied(
            entry_key=entry_key, counter=counter, remaining=remaining
        )

    return WardFlushQueueAck(
        entry_key=entry_key,
        identity=identity,
        content=content,
        counter=counter,
        auth_commit=step,
        wm_sig=advance,
        # Counts only records NOT YET HANDED OVER, so this one is excluded -- it is marked offered
        # now. The host loops while this is non-zero; a record that was sent but never confirmed
        # comes back only through `reconcile_pending`, which is the point at which the device can
        # tell the head has moved at all.
        remaining=remaining,
    )


# The most a batch's leaves may occupy in one WardFlushQueueAck. The wire buffer is 8704 bytes; the
# rest is headroom for the ack's own fields and framing.
_BATCH_BYTES = const(7000)


async def _flush_batch(limit: int) -> "WardFlushQueueAck":
    """Fold up to `limit` queued changes into ONE transition (F, R_F) -> (F + n, R_T).

    ONE TRANSITION, NOT n. One `auth_commit` and one `wm_sig` over the whole step, so the WM
    compare-and-swaps once and rotates once, and the queue drains in one round trip instead of n.
    The counter advances by n, so it still counts changes: each leaf is stamped with its own
    `c_leaf` (F + i), and the rollback and rejoin screens still say how many changes are at stake.

    SEQUENTIAL, AGAINST ROOTS THIS DEVICE DERIVED. Change i is pulled and proved against R_{i-1},
    the root the batch has built so far -- never one the host names -- which is the whole of the
    soundness argument, unchanged from a single write. The host cannot produce that proof alone,
    since R_{i-1} holds leaves it has not seen yet, so each request after the first STAGES the
    previous change (its entry_key and commit) for the host to apply to a scratch tree. That is a
    hint the host needs, not something trusted: a wrong proof fails against the device's own root.

    ALL OR NOTHING. Any failed pull or proof raises before anything is filed or flagged, so the
    batch either goes out whole or leaves every record exactly as it was. The claims are checked
    for room first, for the same reason: a change offered with no claim could never settle.

    NO DUPLICATES TO COLLAPSE. The queue holds at most one record per identity -- a replacement
    keeps its slot -- so no path appears twice in a batch, and no change is proved against a leaf
    the batch itself just wrote.
    """
    from storage import ward as ward_store
    from trezor.messages import WardBatchedLeaf, WardFlushQueueAck
    from trezor.wire import DataError

    from . import offline_store
    from . import round as sync_round
    from .cas import auth_commit, wm_sig
    from .common import pull_leaf
    from .keys import (
        derive_k_auth,
        derive_k_data,
        derive_k_ident,
        derive_k_sig,
        derive_wallet_id,
        derive_ward_id,
        entry_key_for,
    )
    from .leaf import (
        commit_of,
        encode_content,
        encode_identity,
        make_leaf_content,
        make_leaf_identity,
        part_bytes,
    )
    from .root import get_counter, get_root, root_for_write
    from .trie import compute_new_root

    # In queue order, and only records the unnamed drain may publish: compact ones are absent from
    # enumeration by construction, and are skipped here too should one ever appear.
    queued = [
        e
        for e in await offline_store.list_entries()
        if e.pending and not e.offered and not e.compact
    ][:limit]
    if not queued:
        return WardFlushQueueAck(remaining=0)

    from_counter = await get_counter()
    from_root = await get_root()
    running = root_for_write(from_root)

    folded = []  # (entry, entry_key, key_type, id_part, val_part)
    used = 0
    staged = None
    for entry in queued:
        key_type = entry.key_type
        entry_key = await entry_key_for(entry.app_id, entry.identifier, key_type)
        _value, old_leaf, material = await pull_leaf(
            entry_key, key_type, root=running, staged=staged
        )
        c_leaf = from_counter + len(folded) + 1
        id_part = encode_identity(
            await derive_k_ident(key_type), entry_key, key_type, entry.identifier, entry.app_id
        )
        val_part = encode_content(
            await derive_k_data(key_type), entry_key, key_type, entry.value, c_leaf=c_leaf
        )
        size = len(part_bytes(id_part)) + len(part_bytes(val_part)) + 64
        if folded and used + size > _BATCH_BYTES:
            # What does not fit waits for the next flush, still queued and un-offered.
            break
        proof, witness_entry_key, witness_commit = material
        running = compute_new_root(
            entry_key,
            old_leaf,
            (key_type, id_part, val_part),
            proof,
            running,
            witness_entry_key=witness_entry_key,
            witness_commit=witness_commit,
        )
        folded.append((entry, entry_key, key_type, id_part, val_part))
        used += size
        staged = (entry_key, commit_of(key_type, id_part, val_part))

    to_counter = from_counter + len(folded)
    ward_id = await derive_ward_id()
    step = auth_commit(
        await derive_k_auth(), ward_id, from_counter, from_root, to_counter, running
    )
    advance = wm_sig(
        await derive_k_sig(),
        ward_id,
        from_counter,
        from_root,
        to_counter,
        running,
        sync_round.require_head_nonce(),
    )

    # Room for EVERY claim before filing any of them -- see the docstring.
    if not ward_store.claims_fit(
        await derive_wallet_id(), [e[0].slot for e in folded]
    ):
        raise DataError("WARD: cannot record this batch; settle the pending changes first")
    # Every record names the batch's single authorisation and its to_counter, so one adopted link
    # settles them all -- see `offline_store.reconcile_pending`.
    for entry, *_rest in folded:
        await offline_store.mark_offered(entry, to_counter, step)

    return WardFlushQueueAck(
        counter=to_counter,
        from_counter=from_counter,
        auth_commit=step,
        wm_sig=advance,
        remaining=await offline_store.count_unsent(),
        leaves=[
            WardBatchedLeaf(
                entry_key=entry_key,
                identity=make_leaf_identity(key_type, id_part),
                content=make_leaf_content(val_part),
            )
            for _entry, entry_key, key_type, id_part, val_part in folded
        ],
    )
