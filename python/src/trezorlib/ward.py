# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""WARD client: the device stores no entries and PULLS each one from the host mid-workflow
(`WardEntryRequest`, answered like `btc.sign_tx`'s `TxRequest`), with a proof once it holds a root.

The store is keyed by the opaque `entry_key`, which only the device can derive, and holds the leaf
the DEVICE built, verbatim. Writes return that leaf; the caller applies it (`apply`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, NamedTuple, Optional

from . import messages
from .ward_trie import OP_COMMIT, OP_REVERT, Link

if TYPE_CHECKING:
    import protobuf

    from .client import Session


class Leaf(NamedTuple):
    """A stored leaf, exactly as the device handed it over. Both parts empty means deleted."""

    identity: Optional[messages.WardLeafIdentity]
    content: Optional[messages.WardLeafContent]


class Answer(NamedTuple):
    """The host's answer for one path: a leaf with its membership `proof`, or, for an absent
    path, the `witness_*` leaf that occupies it. All-empty means "the tree is empty"."""

    leaf: Optional[Leaf] = None
    proof: Optional[list] = None
    witness_entry_key: Optional[bytes] = None
    witness_commit: Optional[bytes] = None


# Answers a device pull, keyed by the opaque path.
EntryProvider = Callable[[bytes], Answer]

# (to_counter, to_root, limit) -> up to `limit` links ending at that state, NEWEST FIRST.
# A link is (from_counter, from_root, to_counter, to_root, auth_commit).
LinkSource = Callable[[int, Optional[bytes], int], list]


class WardResult(NamedTuple):
    """What a WARD call returns.

    `leaf` is set for direct writes and deletes. `auth_commit` (for other devices) and `wm_sig`
    (for the WM) authorise the transition; both are None when no transition happened -- branch on
    that, not on the counter. `remaining` is set by `flush_queue`; `leaves`/`from_counter` by a
    batched flush, where `entry_key`/`leaf` are unset.
    """

    response: protobuf.MessageType
    entry_key: bytes
    leaf: Optional[Leaf] = None
    counter: Optional[int] = None
    auth_commit: Optional[bytes] = None
    wm_sig: Optional[bytes] = None
    remaining: Optional[int] = None
    leaves: Optional[list] = None
    from_counter: Optional[int] = None


def _call_answering_pulls(
    session: "Session",
    msg: "protobuf.MessageType",
    provider: EntryProvider,
) -> WardResult:
    """Drive a WARD workflow, answering every `WardEntryRequest` from `provider`."""
    res = session.call(msg)
    entry_key = b""
    # A batched flush stages each change it folds; later pulls are proved against the device's
    # RUNNING root, so they are served from a scratch tree with those leaves applied.
    staged: list = []

    while isinstance(res, messages.WardEntryRequest):
        entry_key = res.entry_key or b""
        if res.staged is not None:
            staged.append((res.staged.entry_key, res.staged.commit))
        if staged:
            with_staged = getattr(provider, "with_staged", None)
            if with_staged is None:
                raise RuntimeError("this provider cannot serve a batched flush")
            answer = with_staged(staged)(entry_key)
        else:
            answer = provider(entry_key)
        leaf = answer.leaf
        res = session.call(
            messages.WardEntryAck(
                identity=leaf.identity if leaf is not None else None,
                content=leaf.content if leaf is not None else None,
                proof=answer.proof or [],
                witness_entry_key=answer.witness_entry_key,
                witness_commit=answer.witness_commit,
            )
        )

    if isinstance(res, messages.WardFlushQueueAck) and res.leaves:
        return WardResult(
            res,
            b"",
            None,
            res.counter,
            res.auth_commit,
            res.wm_sig,
            res.remaining,
            leaves=[(bl.entry_key, Leaf(bl.identity, bl.content)) for bl in res.leaves],
            from_counter=res.from_counter,
        )

    if isinstance(res, (messages.WardLeafAck, messages.WardFlushQueueAck)):
        return WardResult(
            res,
            res.entry_key or entry_key,
            Leaf(res.identity, res.content),
            res.counter,
            res.auth_commit,
            res.wm_sig,
            getattr(res, "remaining", None),
        )

    # A service build published the mutation itself: the result must carry NO leaf. An empty
    # `Leaf` would be read by `apply` as a deletion of the entry just written.
    if isinstance(res, (messages.WardMutationApplied, messages.WardFlushQueueApplied)):
        return WardResult(
            res,
            res.entry_key or entry_key,
            counter=res.counter,
            remaining=getattr(res, "remaining", None),
        )

    if not isinstance(res, messages.Success):
        raise RuntimeError(
            f"unexpected response to {type(msg).__name__}: {type(res).__name__}"
        )

    return WardResult(res, entry_key)


def get_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> WardResult:
    """Display the host-held entry for (app_id, identifier). Builds no leaf."""
    return _call_answering_pulls(
        session,
        messages.WardGetEntry(app_id=app_id, identifier=identifier),
        provider,
    )


def set_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    value: Optional[bytes],
    provider: EntryProvider,
) -> WardResult:
    """Create or replace an entry, on confirmation. Needs a synced session.

    The device does not write: store the returned leaf with `apply`. `value=None` is rejected by
    the device; pass b"" for an empty value.
    """
    return _call_answering_pulls(
        session,
        messages.WardSetEntry(app_id=app_id, identifier=identifier, value=value),
        provider,
    )


def delete_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> WardResult:
    """Delete an entry, on confirmation; remove the record with `apply`.

    Idempotent on an absent path (no `auth_commit`, no screen), but the absence must still be
    proved with a non-membership witness.
    """
    return _call_answering_pulls(
        session,
        messages.WardDeleteEntry(app_id=app_id, identifier=identifier),
        provider,
    )


# --- the offline queue: the device's own store; no pulls, own ack types ---------------------


def queue_set_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    value: Optional[bytes],
    mac: Optional[bytes] = None,
    compact: bool = False,
) -> messages.WardQueueSetAck:
    """HOLD a write on the device until `flush_queue` publishes it.

    With `mac` this restores a `queue_get_entry` export (use `restore_queued_entry`). With
    `compact` the device keeps only a hash of the identity; publishing it then needs a named flush.
    """
    return session.call(
        messages.WardQueueSetEntry(
            app_id=app_id,
            identifier=identifier,
            value=value,
            mac=mac,
            compact=compact or None,
        ),
        expect=messages.WardQueueSetAck,
    )


def restore_queued_entry(
    session: "Session",
    backup: messages.WardQueueGetAck,
    compact: bool = False,
) -> messages.WardQueueSetAck:
    """Re-queue a `queue_get_entry` backup unchanged. Every field is MAC'd, so only a PENDING
    record (one with a MAC) can be restored."""
    if backup.mac is None:
        raise ValueError(
            "this backup carries no intent MAC; only a queued (pending) change can be restored"
        )

    return queue_set_entry(
        session,
        backup.app_id or "",
        backup.identifier or b"",
        backup.value or b"",
        mac=backup.mac,
        compact=compact,
    )


def queue_delete_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
) -> messages.WardQueueDeleteAck:
    """Discard a queued (pending) change, on confirmation. Not a WARD deletion; `missing` is an
    answer, not a failure."""
    return session.call(
        messages.WardQueueDeleteEntry(app_id=app_id, identifier=identifier),
        expect=messages.WardQueueDeleteAck,
    )


def queue_get_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
) -> messages.WardQueueGetAck:
    """Export a queued change or pinned copy for backup; keep the whole ack. A record the device
    cannot read fails rather than reading as missing."""
    return session.call(
        messages.WardQueueGetEntry(app_id=app_id, identifier=identifier),
        expect=messages.WardQueueGetAck,
    )


def sync(session: "Session") -> messages.WardSyncAck:
    """Open a sync round: the device mints the nonce the WM signs. The ack's `counter` also tells a
    caller that lost a write's response whether it landed."""
    return session.call(messages.WardSync(), expect=messages.WardSyncAck)


def ingest_attestation(
    session: "Session",
    from_counter: int,
    from_root: Optional[bytes],
    to_counter: int,
    to_root: Optional[bytes],
    wm_signature: bytes,
    from_head_nonce: bytes,
    to_head_nonce: bytes,
    timestamp: int = 0,
) -> messages.WardIngestAttestationAck:
    """Deliver the WM's signed transition into its head for the open round. Genesis is
    `(0, empty) -> (0, empty)`; the head nonces are the WM's, covered by its signature."""
    return session.call(
        messages.WardIngestAttestation(
            from_counter=from_counter,
            from_root=from_root,
            to_counter=to_counter,
            to_root=to_root,
            wm_signature=wm_signature,
            from_head_nonce=from_head_nonce,
            to_head_nonce=to_head_nonce,
            timestamp=timestamp,
        ),
        expect=messages.WardIngestAttestationAck,
    )


def reconcile(
    session: "Session",
    link: Optional[tuple] = None,
) -> messages.WardReconcileAck:
    """Adopt the attested head one step on, by the `auth_commit` of `link` (a 5-tuple; only its
    last element is sent). `link=None` only at counter 0. Prefer `verify_chain`."""
    auth_commit = None
    if link is not None:
        auth_commit = link[4]

    return session.call(
        messages.WardReconcile(auth_commit=auth_commit),
        expect=messages.WardReconcileAck,
    )


def verify_chain(
    session: "Session",
    link_source: LinkSource,
    max_links_per_ack: int = 64,
) -> messages.WardVerifyChainAck:
    """Adopt the attested head by walking back from it to the device's own head.

    `link_source(to_counter, to_root, limit)` returns contiguous links ending at that state,
    newest first; returning none ends the walk with a failure.
    """
    res = _answer_chain_pulls(
        session, session.call(messages.WardVerifyChain()), link_source, max_links_per_ack
    )
    if not isinstance(res, messages.WardVerifyChainAck):
        raise RuntimeError(f"unexpected response to the chain walk: {res}")
    return res


def rejoin(
    session: "Session",
    fork_counter: int,
    link_source: LinkSource,
    max_links_per_ack: int = 64,
) -> messages.WardRejoinAck:
    """Rejoin the WM's history after it lost the device's branch, on confirmation.

    `fork_counter` is the last shared counter (`WardTrie.fork_point`); `link_source` must serve
    both branches back to it, so the host must have kept the device's links.
    """
    res = _answer_chain_pulls(
        session,
        session.call(messages.WardRejoin(fork_counter=fork_counter)),
        link_source,
        max_links_per_ack,
    )
    if not isinstance(res, messages.WardRejoinAck):
        raise RuntimeError(f"unexpected response to the rejoin: {res}")
    return res


def _answer_chain_pulls(
    session: "Session",
    res: object,
    link_source: LinkSource,
    max_links_per_ack: int,
) -> object:
    """Answer the device's `WardChainRequest`s until it says something else, and return that."""
    while isinstance(res, messages.WardChainRequest):
        links = link_source(res.to_counter, res.to_root, max_links_per_ack)
        res = session.call(
            messages.WardChainLinkAck(
                links=[
                    messages.WardChainLink(
                        from_counter=fc,
                        from_root=fr,
                        to_counter=tc,
                        to_root=tr,
                        auth_commit=ac,
                    )
                    # the operation is host-side bookkeeping, never on the wire
                    for (fc, fr, tc, tr, ac) in (lnk[:5] for lnk in links)
                ]
            )
        )
    return res


def rollback(
    session: "Session",
    from_counter: int,
    from_root: Optional[bytes],
    to_counter: int,
    to_root: Optional[bytes],
    wm_signature: bytes,
    from_head_nonce: bytes,
    to_head_nonce: bytes,
    recovered_root: Optional[bytes] = None,
    timestamp: int = 0,
) -> messages.WardRollbackAck:
    """Mint a REVERT from the WM's attested head to `recovered_root`, on confirmation.

    The operands are the WM's own head, attested this round. Nothing is adopted: publish the
    REVERT to the WM, sync, and record it with `apply_rollback`.
    """
    return session.call(
        messages.WardRollback(
            from_counter=from_counter,
            from_root=from_root,
            to_counter=to_counter,
            to_root=to_root,
            wm_signature=wm_signature,
            from_head_nonce=from_head_nonce,
            to_head_nonce=to_head_nonce,
            recovered_root=recovered_root,
            timestamp=timestamp,
        ),
        expect=messages.WardRollbackAck,
    )


def _log(store, link: Link, wm_sig: Optional[bytes]) -> None:  # noqa: ANN001
    """Record a transition, the WM's copy of its authorisation, and the new counter."""
    store.links.append(link)
    store.wm_sigs[link.to_counter] = wm_sig
    store.counter = link.to_counter


def apply_rollback(
    store,
    ack: messages.WardRollbackAck,
    from_counter: int,
    from_root: Optional[bytes],
) -> None:
    """Record a demotion as a REVERT link; restoring the leaves is the caller's business.

    Pass the same `(from_counter, from_root)` given to `rollback` -- the WM's head, which the
    `auth_commit` covers, not the store's.
    """
    _log(
        store,
        Link(
            from_counter,
            from_root,
            ack.counter,
            ack.new_root or None,
            ack.auth_commit,
            OP_REVERT,
        ),
        ack.wm_sig,
    )


def leaf_is_delete(leaf: Optional[Leaf]) -> bool:
    """An empty content body is a deletion. Dispatches on `encoding`, as the firmware does."""
    if leaf is None or leaf.content is None:
        return True
    content = leaf.content
    encoding = 0 if content.encoding is None else content.encoding
    if encoding not in (0, 1):
        raise ValueError(f"unknown leaf content encoding: {encoding!r}")
    if content.encrypted is not None and content.plaintext is not None:
        raise ValueError("leaf content sets both encodings")
    if encoding == 1:
        return not (content.plaintext is not None and content.plaintext.content)
    return not (content.encrypted is not None and content.encrypted.ct)


def store_provider(store) -> EntryProvider:
    """An `EntryProvider` backed by anything with the `WardTrie` shape. Needs no key."""

    def provider(entry_key: bytes) -> Answer:
        if entry_key in store:
            return Answer(
                leaf=store.blobs[entry_key],
                proof=store.membership_proof(entry_key),
            )
        proof, witness_key, witness_commit = store.nonmembership_proof(entry_key)
        return Answer(
            proof=proof, witness_entry_key=witness_key, witness_commit=witness_commit
        )

    provider.with_staged = lambda staged: store_provider(store.scratch(staged))  # type: ignore[attr-defined]
    return provider


def _put(store, entry_key: bytes, leaf: Leaf) -> None:  # noqa: ANN001
    if leaf_is_delete(leaf):
        store.remove(entry_key)
    else:
        store.set(entry_key, leaf)


def apply(store, result: WardResult) -> None:
    """Apply a confirmed write or delete to the caller's store.

    Raises on a service-build result, which carries no leaf. No `auth_commit` means nothing
    changed, and the store must not still hold the entry.
    """
    if result.leaves:
        _apply_batch(store, result)
        return

    if result.leaf is None:
        raise ValueError("this result carries no leaf; nothing to apply")

    if result.auth_commit is None:
        if result.entry_key in store:
            raise ValueError(
                "device reports no change but the store still holds this entry; "
                "the two disagree about the current state"
            )
        if result.counter is not None:
            store.counter = result.counter
        return

    before_root, before_counter = store.root(), store.counter
    _put(store, result.entry_key, result.leaf)
    if result.counter is not None:
        _log(
            store,
            Link(
                before_counter,
                before_root,
                result.counter,
                store.root(),
                result.auth_commit,
                OP_COMMIT,
            ),
            result.wm_sig,
        )


def _apply_batch(store, result: WardResult) -> None:  # noqa: ANN001
    """Apply every leaf of a batched flush and log ONE link. A real host does this in one
    transaction and publishes to the WM only after it commits."""
    if store.counter != result.from_counter:
        raise ValueError(
            "this batch starts at counter %s but the store is at %s"
            % (result.from_counter, store.counter)
        )
    before_root = store.root()
    for entry_key, leaf in result.leaves or ():
        _put(store, entry_key, leaf)
    _log(
        store,
        Link(
            result.from_counter,
            before_root,
            result.counter,
            store.root(),
            result.auth_commit,
            OP_COMMIT,
        ),
        result.wm_sig,
    )


def pin_cached_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> WardResult:
    """Keep a verified copy of (app_id, identifier) on the device, on confirmation. Needs a synced
    session; fails if the device store is full (it never evicts)."""
    return _call_answering_pulls(
        session,
        messages.WardPinCachedEntry(app_id=app_id, identifier=identifier),
        provider,
    )


def erase_cached_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
) -> messages.Success:
    """Remove the device's local copy of (app_id, identifier), on confirmation. Not a WARD
    deletion; the device derives the path, so a host cannot name an arbitrary record."""
    return session.call(
        messages.WardEraseCachedEntry(app_id=app_id, identifier=identifier),
        expect=messages.Success,
    )


def flush_queue(
    session: "Session",
    provider: EntryProvider,
    app_id: Optional[str] = None,
    identifier: Optional[bytes] = None,
    max_batch: int = 1,
) -> WardResult:
    """Publish the next queued change (or the named one), re-derived against current state.

    Loop while `remaining` is non-zero; `apply` and publish each result as for a write. Naming an
    entry is the only way to publish a COMPACT record. `max_batch > 1` folds up to that many into
    ONE transition -- only if the caller can store all its leaves and link in one transaction, and
    the provider offers `with_staged`. A service build answers `WardFlushQueueApplied` with no leaf.
    """
    return _call_answering_pulls(
        session,
        messages.WardFlushQueue(
            app_id=app_id,
            identifier=identifier,
            max_batch=max_batch if max_batch > 1 else None,
        ),
        provider,
    )


def reset_app(session: "Session") -> messages.WardResetAppAck:
    """Retire the pinned WARD app, on confirmation. Discards nothing; `was_bound` says whether a
    pin was retired."""
    return session.call(messages.WardResetApp(), expect=messages.WardResetAppAck)


def reset_service(
    session: "Session", force: bool = False
) -> messages.WardResetServiceAck:
    """Unbind the WARD service daemon, on confirmation (service builds, ordinary session).

    Refused while queued changes are unresolved unless `force`; `unresolved` reports them.
    """
    return session.call(
        messages.WardResetService(force=force or None),
        expect=messages.WardResetServiceAck,
    )
