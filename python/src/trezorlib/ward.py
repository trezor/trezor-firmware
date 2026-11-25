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

import typing as t
from typing import TYPE_CHECKING, Callable, NamedTuple, Optional

from . import messages
from .ward_trie import OP_COMMIT, OP_REVERT, Link

if TYPE_CHECKING:
    import protobuf

    from .client import Session
    from .ward_trie import WardTrie


class Leaf(NamedTuple):
    """A stored leaf, exactly as the device handed it over: `identity` is the sealed_identity
    (kept beside the leaf, not committed) and `content` the sealed_content. An empty content
    means deleted."""

    identity: Optional[bytes]
    content: Optional[bytes]


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
        leaf = answer.leaf or Leaf(None, None)
        res = session.call(
            messages.WardEntryAck(
                sealed_content=leaf.content or None,
                proof=answer.proof or [],
                witness_entry_key=answer.witness_entry_key,
                witness_commit=answer.witness_commit,
            )
        )

    if isinstance(res, messages.Success):
        return WardResult(res, entry_key)
    leaf_acks = (messages.WardLeafAck, messages.WardFlushQueueAck)
    applied = (messages.WardMutationApplied, messages.WardFlushQueueApplied)
    if not isinstance(res, leaf_acks + applied):
        raise RuntimeError(
            f"unexpected response to {type(msg).__name__}: {type(res).__name__}"
        )

    batch = getattr(res, "leaves", None)
    # A service build published the mutation itself (`*Applied`): the result must carry NO leaf.
    # An empty `Leaf` would be read by `apply` as a deletion of the entry just written.
    carries_leaf = isinstance(res, leaf_acks) and not batch
    return WardResult(
        res,
        b"" if batch else (res.entry_key or entry_key),
        Leaf(res.sealed_identity, res.sealed_content) if carries_leaf else None,
        res.counter,
        getattr(res, "auth_commit", None),
        getattr(res, "wm_sig", None),
        getattr(res, "remaining", None),
        leaves=(
            [
                (bl.entry_key, Leaf(bl.sealed_identity, bl.sealed_content))
                for bl in batch
            ]
            if batch
            else None
        ),
        from_counter=res.from_counter if batch else None,
    )


def _keyed_pull(
    session: "Session",
    cls: type,
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> WardResult:
    """One request naming (app_id, identifier), its pulls answered from `provider`."""
    return _call_answering_pulls(session, cls(app_id=app_id, identifier=identifier), provider)


def _keyed_call(
    session: "Session", cls: type, app_id: str, identifier: bytes, expect: type
) -> t.Any:
    """One request naming (app_id, identifier), with no pulls."""
    return session.call(cls(app_id=app_id, identifier=identifier), expect=expect)


def get_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> WardResult:
    """Display the host-held entry for (app_id, identifier). Builds no leaf."""
    return _keyed_pull(session, messages.WardGetEntry, app_id, identifier, provider)


def set_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    value: Optional[bytes],
    provider: EntryProvider,
    retry: Optional[messages.WardWriteRetry] = None,
) -> WardResult:
    """Create or replace an entry, on confirmation. Needs a synced session.

    The device does not write: store the returned leaf with `apply`. `value=None` is rejected by
    the device; pass b"" for an empty value.

    `retry`: this same write lost a race. Pass the `retry` of its earlier `WardLeafAck`
    (`result.response.retry`) after a sync; the device re-signs it silently if the entry is
    unchanged since, answers a no-op if it already holds this value, and asks otherwise.
    """
    return _call_answering_pulls(
        session,
        messages.WardSetEntry(app_id=app_id, identifier=identifier, value=value, retry=retry),
        provider,
    )


def set_pointer(
    session: "Session",
    app_id: str,
    identifier: bytes,
    target_identifier: bytes,
    provider: EntryProvider,
    retry: Optional[messages.WardWriteRetry] = None,
) -> WardResult:
    """Make an entry point at `target_identifier` in the same `app_id`, on confirmation. Needs a
    synced session. A read of the pointer returns the target's value. Store the returned leaf with
    `apply`."""
    return _call_answering_pulls(
        session,
        messages.WardSetPointer(
            app_id=app_id,
            identifier=identifier,
            target_identifier=target_identifier,
            retry=retry,
        ),
        provider,
    )


def delete_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
    retry: Optional[messages.WardWriteRetry] = None,
) -> WardResult:
    """Delete an entry, on confirmation; remove the record with `apply`.

    Idempotent on an absent path (no `auth_commit`, no screen), but the absence must still be
    proved with a non-membership witness. `retry` as for `set_entry`.
    """
    return _call_answering_pulls(
        session,
        messages.WardDeleteEntry(app_id=app_id, identifier=identifier, retry=retry),
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
    return _keyed_call(session, messages.WardQueueDeleteEntry, app_id, identifier, messages.WardQueueDeleteAck)


def queue_get_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
) -> messages.WardQueueGetAck:
    """Export a queued change or pinned copy for backup; keep the whole ack. A record the device
    cannot read fails rather than reading as missing."""
    return _keyed_call(session, messages.WardQueueGetEntry, app_id, identifier, messages.WardQueueGetAck)


def sync(session: "Session", wm_challenge: bytes | None = None) -> messages.WardSyncAck:
    """Open a sync round: the device mints the nonce the WM signs. The ack's `counter` also tells a
    caller that lost a write's response whether it landed."""
    return session.call(
        messages.WardSync(wm_challenge=wm_challenge), expect=messages.WardSyncAck
    )


def _fields(params: dict) -> dict:
    """A wrapper's own parameters, minus the session, as message fields of the same names."""
    return {k: v for k, v in params.items() if k != "session"}


def ingest_attestation(
    session: "Session",
    from_counter: int,
    from_root: Optional[bytes],
    to_counter: int,
    to_root: Optional[bytes],
    wm_signature: bytes,
    timestamp: int = 0,
) -> messages.WardIngestAttestationAck:
    """Deliver the WM's signed transition into its head for the open round. Genesis is
    `(0, empty) -> (0, empty)`."""
    msg = messages.WardIngestAttestation(**_fields(locals()))
    return session.call(msg, expect=messages.WardIngestAttestationAck)


def reconcile(
    session: "Session",
    link: Optional[tuple] = None,
) -> messages.WardReconcileAck:
    """Adopt the attested head one step on, by the `auth_commit` of `link` (a 5-tuple; only its
    last element is sent). `link=None` only at counter 0. Prefer `verify_chain`."""
    return session.call(
        messages.WardReconcile(auth_commit=link[4] if link is not None else None),
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
    return _chain_walk(
        session,
        messages.WardVerifyChain(),
        link_source,
        max_links_per_ack,
        messages.WardVerifyChainAck,
        "the chain walk",
    )


class CachedAttestation(NamedTuple):
    """A WM attestation kept from an earlier round, with the round nonce it was signed over.

    Its `to` end is the head it vouches for; `catch_up` names that head separately.
    """

    nonce: bytes
    from_counter: int
    from_root: Optional[bytes]
    timestamp: int
    wm_signature: bytes


def catch_up(
    session: "Session",
    to_counter: int,
    to_root: Optional[bytes],
    attestation: Optional[CachedAttestation],
    link_source: LinkSource,
    max_links_per_ack: int = 64,
) -> messages.WardCatchUpAck:
    """Follow the wallet's own chain to `(to_counter, to_root)` WITHOUT the WM, for this session.

    `attestation` is the WM's cached attestation of that head. The device checks it, refuses one
    older than its stored head's, walks back to its stored head and reads from the named head
    under a warning dated by the attestation. Nothing is persisted unless the user allowed it for
    this wallet (`set_persist_without_wm`); `persisted` in the ack says which. A head below the
    stored counter is refused.

    On a firmware built without a WM (the MVP) `attestation` may be None: the chain alone decides,
    and the head is always persisted.
    """
    return _chain_walk(
        session,
        messages.WardCatchUp(
            to_counter=to_counter,
            to_root=to_root,
            **(
                {}
                if attestation is None
                else dict(
                    nonce=attestation.nonce,
                    from_counter=attestation.from_counter,
                    from_root=attestation.from_root,
                    timestamp=attestation.timestamp,
                    wm_signature=attestation.wm_signature,
                )
            ),
        ),
        link_source,
        max_links_per_ack,
        messages.WardCatchUpAck,
        "the catch-up",
    )


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
    return _chain_walk(
        session,
        messages.WardRejoin(fork_counter=fork_counter),
        link_source,
        max_links_per_ack,
        messages.WardRejoinAck,
        "the rejoin",
    )


# Links with WM attestations are ~250 bytes each; 16 keep a page well inside the 8704-byte buffer.
_ACCEPTANCE_PAGE = 16

# `(from_counter, from_root, to_counter, to_root)` -> the WM's archived attestation of that step.
AcceptanceSource = t.Callable[
    [int, Optional[bytes], int, Optional[bytes]],
    Optional[messages.WardChainAcceptance],
]


def _chain_walk(
    session: "Session",
    msg: "protobuf.MessageType",
    link_source: LinkSource,
    max_links_per_ack: int,
    expected: type,
    what: str,
    acceptance_source: "AcceptanceSource | None" = None,
) -> t.Any:
    """Send `msg`, answer the device's `WardChainRequest`s from `link_source`, and return the
    final response, which must be an `expected`. A request with `with_acceptance` gets each
    link's archived WM attestation from `acceptance_source`, in smaller pages."""
    res = session.call(msg)
    while isinstance(res, messages.WardChainRequest):
        receipts = bool(res.with_acceptance) and acceptance_source is not None
        limit = min(max_links_per_ack, _ACCEPTANCE_PAGE) if receipts else max_links_per_ack
        links = link_source(res.to_counter, res.to_root, limit)
        res = session.call(
            messages.WardChainLinkAck(
                links=[
                    messages.WardChainLink(
                        from_counter=fc,
                        from_root=fr,
                        to_counter=tc,
                        to_root=tr,
                        auth_commit=ac,
                        acceptance=(
                            acceptance_source(fc, fr, tc, tr)
                            if receipts and acceptance_source is not None
                            else None
                        ),
                    )
                    # the operation is host-side bookkeeping, never on the wire
                    for (fc, fr, tc, tr, ac) in (lnk[:5] for lnk in links)
                ]
            )
        )
    if not isinstance(res, expected):
        raise RuntimeError(f"unexpected response to {what}: {res}")
    return res


def rollback(
    session: "Session",
    from_counter: int,
    from_root: Optional[bytes],
    to_counter: int,
    to_root: Optional[bytes],
    wm_signature: bytes,
    *,
    recovered_counter: int,
    link_source: LinkSource,
    acceptance_source: "AcceptanceSource | None" = None,
    recovered_root: Optional[bytes] = None,
    timestamp: int = 0,
) -> messages.WardRollbackAck:
    """Mint a REVERT to a verified historical head, on confirmation.

    The operands are the WM's own head, attested this round. Nothing is adopted: publish the
    REVERT to the WM, sync, and record it with `apply_rollback`.
    `acceptance_source` supplies each historical link's archived WM attestation. The live
    attestation already proves the newest step when the WM is the anchor.
    """
    msg = messages.WardRollback(
        from_counter=from_counter,
        from_root=from_root,
        to_counter=to_counter,
        to_root=to_root,
        wm_signature=wm_signature,
        recovered_counter=recovered_counter,
        recovered_root=recovered_root,
        timestamp=timestamp,
    )
    return _chain_walk(
        session, msg, link_source, 64, messages.WardRollbackAck, "the revert", acceptance_source
    )


def roll_forward(
    session: "Session",
    from_counter: int,
    from_root: Optional[bytes],
    to_counter: int,
    to_root: Optional[bytes],
    wm_signature: bytes,
    links: "list[messages.WardChainLink]",
    timestamp: int = 0,
    final: bool = True,
) -> messages.WardRollForwardAck:
    """Have the device sign again, for this round's session, transitions the WM accepted before
    its register went back.

    The first five operands are the WM's live attestation of its current head, against the open
    round. `links` run oldest first from that head; each must carry its WM acceptance record
    (`WardChainLink.acceptance`) and its `auth_commit`. Returns one `wm_sig` per link, to submit to
    the WM as ordinary advances. At most 16 links per call.

    Only in a round whose `ingest_attestation` reported `wm_behind`. The device asks the user to
    approve on the first page; `final` marks the last page, on which it shows the restored head and
    when the WM accepted its last change (also returned as `last_timestamp`).
    """
    return session.call(
        messages.WardRollForward(
            from_counter=from_counter,
            from_root=from_root,
            to_counter=to_counter,
            to_root=to_root,
            timestamp=timestamp,
            wm_signature=wm_signature,
            links=links,
            final=final,
        ),
        expect=messages.WardRollForwardAck,
    )


def _log(store, *link: object, wm_sig: Optional[bytes]) -> None:  # noqa: ANN001
    """Record a transition (the `Link` fields), the WM's copy of its authorisation, and the new
    counter."""
    entry = Link(*link)
    store.links.append(entry)
    store.wm_sigs[entry.to_counter] = wm_sig
    store.counter = entry.to_counter


def apply_rollback(
    store: "WardTrie",
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
        from_counter,
        from_root,
        ack.counter,
        ack.new_root or None,
        ack.auth_commit,
        OP_REVERT,
        wm_sig=ack.wm_sig,
    )


def leaf_is_delete(leaf: Optional[Leaf]) -> bool:
    """An empty sealed_content is a deletion."""
    return leaf is None or not leaf.content


def store_provider(store: "WardTrie") -> EntryProvider:
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


def apply(store: "WardTrie", result: WardResult) -> None:
    """Apply a confirmed write, delete or batched flush to the caller's store.

    Raises on a service-build result, which carries no leaf. No `auth_commit` means nothing
    changed, and the store must not still hold the entry. A batch logs ONE link; a real host
    applies it in one transaction and publishes to the WM only after it commits.
    """
    if result.leaves:
        if store.counter != result.from_counter:
            raise ValueError(
                "this batch starts at counter %s but the store is at %s"
                % (result.from_counter, store.counter)
            )
        writes = result.leaves
    elif result.leaf is None:
        raise ValueError("this result carries no leaf; nothing to apply")
    elif result.auth_commit is None:
        if result.entry_key in store:
            raise ValueError(
                "device reports no change but the store still holds this entry; "
                "the two disagree about the current state"
            )
        if result.counter is not None:
            store.counter = result.counter
        return
    else:
        writes = [(result.entry_key, result.leaf)]

    before_root, before_counter = store.root(), store.counter
    for entry_key, leaf in writes:
        if leaf_is_delete(leaf):
            store.remove(entry_key)
        else:
            store.set(entry_key, leaf)
    if result.counter is not None:
        _log(
            store,
            before_counter,
            before_root,
            result.counter,
            store.root(),
            result.auth_commit,
            OP_COMMIT,
            wm_sig=result.wm_sig,
        )


def pin_cached_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> WardResult:
    """Keep a verified copy of (app_id, identifier) on the device, on confirmation. Needs a synced
    session; fails if the device store is full (it never evicts)."""
    return _keyed_pull(session, messages.WardPinCachedEntry, app_id, identifier, provider)


def erase_cached_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
) -> messages.Success:
    """Remove the device's local copy of (app_id, identifier), on confirmation. Not a WARD
    deletion; the device derives the path, so a host cannot name an arbitrary record."""
    return _keyed_call(session, messages.WardEraseCachedEntry, app_id, identifier, messages.Success)


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


def set_persist_without_wm(session: "Session", allow: bool) -> messages.Success:
    """Allow (held to confirm) or stop `catch_up` persisting a cached-attested head for the active
    wallet while the WM is unreachable. Refused on a firmware built without a WM."""
    return session.call(
        messages.WardSetPersistWithoutWm(allow=allow), expect=messages.Success
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
