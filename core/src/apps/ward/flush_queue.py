from typing import TYPE_CHECKING

from micropython import const
from trezor import utils

if TYPE_CHECKING:
    from trezor.messages import (
        WardFlushQueue,
        WardFlushQueueAck,
        WardFlushQueueApplied,
    )

    from .offline_store import StoredEntry


async def _seal(
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
    c_leaf: int,
) -> tuple:
    """The (sealed_identity, sealed_content) of a queued change, for publication. The queue's
    `key_type` is the entry_type the value is sealed as."""
    from .keys import derive_k_data, derive_k_ident
    from .leaf import seal_content, seal_identity

    return (
        seal_identity(await derive_k_ident(), identifier, app_id),
        seal_content(await derive_k_data(), key_type, c_leaf, value),
    )


def _derive(
    entry_key: bytes, old_leaf: "bytes | None", parts: tuple, material: tuple, root: bytes
) -> bytes:
    """The root after writing `parts` at `entry_key`, from verified pull material."""
    from .trie import compute_new_root

    proof, witness_entry_key, witness_commit = material
    return compute_new_root(
        entry_key,
        old_leaf,
        parts[1],
        proof,
        root,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )


async def _in_conflict(entry: StoredEntry, old_leaf: bytes) -> bool:
    """Whether `_publish_or_settle` would ask the user about this change (equal values do not)."""
    from .keys import derive_k_data
    from .leaf import open_content

    entry_type, c_leaf, theirs = open_content(await derive_k_data(), old_leaf)
    if entry.base is not None and c_leaf <= entry.base:
        return False
    return not (entry_type == entry.key_type and theirs == entry.value)


async def _publish_or_settle(
    entry: StoredEntry, key_type: str, app_id: str, identifier: bytes, old_leaf: "bytes | None"
) -> bool:
    """Whether to publish this queued change now. False: it was settled here instead.

    A CONFLICT is a published leaf written after the head the change was queued on (`entry.base`;
    a restored change has none, so any differing value counts): another device changed the entry
    without this change in view. The same value settles silently. A real conflict goes to the
    user, never resolved for them: keep yours (publish it over theirs), keep the published value
    (discard yours, held), or cancel (it stays pending and the flush stops).
    """
    from trezor import log
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_action, confirm_properties
    from trezor.wire import ActionCancelled

    from . import offline_store
    from .common import display_bytes, display_content, entry_props
    from .keys import derive_k_data, entry_key_for
    from .leaf import open_content

    # the path, as wardd logs it; values never reach the log
    shown = (await entry_key_for(app_id, identifier))[:6].hex()
    base = "none (restored)" if entry.base is None else "#%d" % entry.base
    if old_leaf is None:
        log.info(__name__, "flush: entry=%s base=%s: nothing published there", shown, base)
        return True  # nothing published here, so nothing to overwrite
    entry_type, c_leaf, theirs = open_content(await derive_k_data(), old_leaf)
    if entry.base is not None and c_leaf <= entry.base:
        log.info(
            __name__,
            "flush: entry=%s base=%s: published at #%d, before it was queued: no conflict",
            shown,
            base,
            c_leaf,
        )
        return True  # written before the change was queued: the user formed it in view of that

    async def keep_theirs() -> None:
        # the queued record becomes an offline copy of what is published, as a landed one would
        await offline_store.put(
            key_type, app_id, identifier, theirs, False, compact=entry.compact
        )

    if entry_type == key_type and theirs == entry.value:
        await keep_theirs()
        log.info(
            __name__,
            "flush: entry=%s base=%s: published at #%d with the same value: settled",
            shown,
            base,
            c_leaf,
        )
        return False

    log.info(
        __name__,
        "flush: CONFLICT entry=%s: published at #%d, after this change was queued at %s",
        shown,
        c_leaf,
        base,
    )

    props = entry_props(app_id, identifier)
    props.append(
        ("Published (change #%d)" % c_leaf, display_content((entry_type, theirs)), True)
    )
    props.append(("Yours (queued offline)", display_bytes(entry.value), True))
    props.append(
        ("Warning", "Another device changed this entry after you queued yours.", False)
    )
    await confirm_properties("ward_conflict", "Conflicting change", props)

    try:
        await confirm_action(
            "ward_conflict_keep_new",
            "Keep your value?",
            "Publish your queued value over the published one.",
            verb="Keep yours",
            br_code=ButtonRequestType.Other,
        )
        log.info(__name__, "flush: conflict entry=%s resolved: KEEP NEW (publish the queued value)", shown)
        return True
    except ActionCancelled:
        pass

    # Declining both leaves the change pending: ActionCancelled ends the flush here.
    try:
        await confirm_action(
            "ward_conflict_keep_original",
            "Keep published value?",
            "Your queued value will be discarded.",
            verb="Keep published",
            hold=True,
            br_code=ButtonRequestType.Other,
        )
    except ActionCancelled:
        log.info(__name__, "flush: conflict entry=%s left unresolved: stays pending", shown)
        raise
    await keep_theirs()
    log.info(
        __name__,
        "flush: conflict entry=%s resolved: KEEP ORIGINAL (queued value discarded)",
        shown,
    )
    return False


async def flush_queue(
    msg: WardFlushQueue,
) -> "WardFlushQueueAck | WardFlushQueueApplied":
    """WardFlushQueue handler: publish ONE queued change (or, opted in, a batch).

    A queued change is an intent formed with no host, so it is RE-DERIVED here against current,
    proven state and sealed on the way out. No screen: the user confirmed when queueing. The record
    stays PENDING until an adoption settles it, so a host that never publishes loses nothing.
    """
    from trezor.messages import WardFlushQueueAck
    from trezor.wire import DataError

    from . import offline_store
    from .transition import authorise
    from .common import online, pull_leaf, require_initialized
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for
    from .root import get_counter, get_root, root_for_write

    require_initialized()

    if not await online():
        raise DataError("WARD: sync before publishing queued changes")

    # batching: opt-in, unnamed drain only, connect builds only
    max_batch = msg.max_batch or 1
    named = msg.app_id is not None and msg.identifier is not None
    if max_batch > 1 and not named and not utils.USE_WARD_SERVICE_CHANNEL:
        from .transition import MAX_BATCH

        return await _flush_batch(min(max_batch, MAX_BATCH))

    def nothing_published(
        remaining: int,
    ) -> "WardFlushQueueAck | WardFlushQueueApplied":
        if utils.USE_WARD_SERVICE_CHANNEL:
            from trezor.messages import WardFlushQueueApplied

            return WardFlushQueueApplied(remaining=remaining)
        return WardFlushQueueAck(remaining=remaining)

    # One change is published; one settled by `_publish_or_settle` moves on to the next.
    while True:
        app_id, identifier = msg.app_id, msg.identifier
        key_type = ENTRY_TYPE_ADDRESS

        if named:
            status, entry = await offline_store.get(key_type, app_id, identifier)
            if status != offline_store.VALID or entry is None or not entry.pending:
                raise DataError("WARD: no queued change for this entry")
            # A named change may be re-offered: that is how a lost response (and any compact
            # record) gets back.
        else:
            entry = await offline_store.next_unsent()
            if entry is None:
                return nothing_published(0)
            if entry.compact:
                raise DataError(
                    "WARD: the next queued change is stored compactly; name it with app_id and identifier"
                )
            app_id, identifier = entry.app_id, entry.identifier
            key_type = entry.key_type
        entry_key = await entry_key_for(app_id, identifier)

        # The pull may sync (service builds), so the head is read only after it.
        _old_value, old_leaf, material = await pull_leaf(entry_key)

        if await _publish_or_settle(entry, key_type, app_id, identifier, old_leaf):
            break
        if named:
            return nothing_published(await offline_store.count_unsent())

    from_root = await get_root()
    counter = await get_counter() + 1

    # sealed under the identity verified against the record (the request's, when compact)
    parts = await _seal(key_type, app_id, identifier, entry.value, counter)
    new_root = _derive(entry_key, old_leaf, parts, material, root_for_write(from_root))

    step, advance = await authorise(counter - 1, from_root, counter, new_root)

    # Claim and OFFERED flag go to flash before anything leaves the device.
    await offline_store.mark_offered(entry, counter, step)

    from trezor import log

    log.info(__name__, "flush: publishing entry=%s as change #%d", entry_key[:6].hex(), counter)

    remaining = await offline_store.count_unsent()

    if utils.USE_WARD_SERVICE_CHANNEL:
        from trezor.messages import WardFlushQueueApplied

        from .service import publish

        await publish(
            entry_key, parts[0], parts[1], from_root, counter, new_root, step, advance
        )
        return WardFlushQueueApplied(
            entry_key=entry_key, counter=counter, remaining=remaining
        )

    return WardFlushQueueAck(
        entry_key=entry_key,
        sealed_identity=parts[0],
        sealed_content=parts[1],
        counter=counter,
        auth_commit=step,
        wm_sig=advance,
        remaining=remaining,
    )


# The most a batch's leaves may occupy in one WardFlushQueueAck (wire buffer 8704 bytes).
_BATCH_BYTES = const(7000)


async def _flush_batch(limit: int) -> "WardFlushQueueAck":
    """Fold up to `limit` queued changes into ONE transition (F, R_F) -> (F + n, R_T).

    Change i is proved against R_{i-1}, the root this device built so far; the previous change is
    STAGED for the host only so it can serve that proof. All or nothing: any failure raises before
    a claim is filed or a flag flipped, and room for every claim is checked first.
    """
    from storage import ward as ward_store
    from trezor.messages import WardBatchedLeaf, WardFlushQueueAck
    from trezor.wire import DataError

    from . import offline_store
    from .transition import authorise
    from .common import pull_leaf
    from .keys import derive_wallet_id, entry_key_for
    from .leaf import value_digest
    from .root import get_counter, get_root, root_for_write

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

    folded = []  # (entry, entry_key, key_type, parts)
    used = 0
    staged = None
    for entry in queued:
        key_type = entry.key_type
        entry_key = await entry_key_for(entry.app_id, entry.identifier)
        _value, old_leaf, material = await pull_leaf(
            entry_key, root=running, staged=staged
        )
        if folded and old_leaf is not None and await _in_conflict(entry, old_leaf):
            break  # resolved at the head of the next flush, never in the middle of a batch
        if not await _publish_or_settle(
            entry, key_type, entry.app_id, entry.identifier, old_leaf
        ):
            continue
        parts = await _seal(
            key_type,
            entry.app_id,
            entry.identifier,
            entry.value,
            from_counter + len(folded) + 1,
        )
        size = len(parts[0]) + len(parts[1]) + 64
        if folded and used + size > _BATCH_BYTES:
            break  # waits for the next flush, still queued
        running = _derive(entry_key, old_leaf, parts, material, running)
        folded.append((entry, entry_key, key_type, parts))
        used += size
        staged = (entry_key, value_digest(parts[1]))

    if not folded:
        return WardFlushQueueAck(remaining=await offline_store.count_unsent())

    to_counter = from_counter + len(folded)
    step, advance = await authorise(from_counter, from_root, to_counter, running)

    if not ward_store.claims_fit(
        await derive_wallet_id(), [e[0].slot for e in folded]
    ):
        raise DataError("WARD: cannot record this batch; settle the pending changes first")
    # every claim names the batch's one authorisation, so one adopted link settles them all
    for entry, *_rest in folded:
        await offline_store.mark_offered(entry, to_counter, step)

    from trezor import log

    log.info(
        __name__,
        "flush: publishing %d change(s) as #%d -> #%d",
        len(folded),
        from_counter,
        to_counter,
    )

    return WardFlushQueueAck(
        counter=to_counter,
        from_counter=from_counter,
        auth_commit=step,
        wm_sig=advance,
        remaining=await offline_store.count_unsent(),
        leaves=[
            WardBatchedLeaf(
                entry_key=entry_key,
                sealed_identity=parts[0],
                sealed_content=parts[1],
            )
            for _entry, entry_key, key_type, parts in folded
        ],
    )
