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

"""WARD client -- sealed leaf, PULL-only, keyed path, proofs against a root.

The device stores no entries. It asks the host for the one it needs mid-workflow, so
the host must be prepared to answer a device-initiated `WardEntryRequest` while its own
call is still in flight. That is the same shape as `btc.sign_tx` answering `TxRequest`:
call, inspect what came back, answer it, repeat until the workflow returns.

Writes work the same way and pull too: the device asks for the CURRENT value so it can
show what is being replaced or removed. The device does not write -- it returns the leaf
it built and the CALLER applies it, see `apply`.

The host must also PROVE its answers once the device holds a root: a present leaf comes
with a membership proof, an absent one with a witness. See `Answer`.

**The store is keyed by the opaque `entry_key`, not by the identifier.** The device
derives that key from a seed this library does not have, so a host CANNOT compute it --
that is the whole point, and why every call returns the key it was asked for. Anything
here that could derive an entry_key would defeat the property being bought.

**The stored unit is a two-part leaf the DEVICE builds.** A write returns that leaf and
the caller stores it verbatim. Do not assemble one here: while the parts are plaintext a
host technically could, but that stops being true the moment they are sealed, and code
that quietly relies on it now would break then.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, NamedTuple, Optional

from . import messages

if TYPE_CHECKING:
    import protobuf

    from .client import Session


class Leaf(NamedTuple):
    """A stored WARD leaf, exactly as the device handed it over.

    Opaque to the host: it holds these two parts and gives them back when asked for the
    path they sit at. Both parts empty means the entry was deleted.
    """

    identity: Optional[messages.WardLeafIdentity]
    content: Optional[messages.WardLeafContent]


class Answer(NamedTuple):
    """What the host hands back for one path.

    A leaf alone is not enough once the device holds a root: the answer has to be
    provable. `proof` accompanies a present leaf; `witness_*` accompany an absent one,
    since absence is shown by exhibiting the leaf that occupies the path instead.

    An all-empty Answer says "the tree is empty", which only a device holding no root can
    accept.
    """

    leaf: Optional[Leaf] = None
    proof: Optional[list] = None
    witness_entry_key: Optional[bytes] = None
    witness_commit: Optional[bytes] = None
    # Delete only. The device must be told which KIND of node the collapsing sibling is,
    # in exactly one of these two forms -- it cannot tell from the proof, which carries
    # only a hash, and it will not infer a leaf from a missing decomposition. A branch is
    # re-derived at the shallower depth it moves to; a leaf promotes unchanged, once its
    # hash has been recomputed and matched. See messages-ward.proto.
    sibling_split_bit: Optional[int] = None
    sibling_left: Optional[bytes] = None
    sibling_right: Optional[bytes] = None
    sibling_entry_key: Optional[bytes] = None
    sibling_commit: Optional[bytes] = None


# Answers a device pull, keyed by the opaque path.
EntryProvider = Callable[[bytes], Answer]


class WardResult(NamedTuple):
    """What a WARD call returns.

    `entry_key` is the opaque 32-byte path the device asked about; callers need it to
    apply a confirmed write or delete, since it is the key their store is organised by
    and they have no other way to learn it.

    `leaf` is the leaf the device built, present for writes and deletes and None for a
    read. For a delete both its parts are empty and the record should be removed.

    `auth_commit` is the authorisation for the transition this call made -- and its ABSENCE
    means no transition was made. That is the shape of an idempotent delete of a path that
    already held nothing: same empty leaf, same counter, nothing to authorise. Callers
    should branch on it rather than on the counter, which is equal to the stored one in that
    case and cannot be compared without knowing the store is in sync.
    """

    response: protobuf.MessageType
    entry_key: bytes
    leaf: Optional[Leaf] = None
    # What a write produced. The caller must publish these to the WM, or the device is
    # ahead of it and its next sync is refused as a rollback.
    counter: Optional[int] = None
    mac: Optional[bytes] = None
    # Authorises this write's transition. The caller stores it with the link so another
    # device of the wallet can later verify the step without having witnessed it.
    auth_commit: Optional[bytes] = None


def _call_answering_pulls(
    session: "Session",
    msg: "protobuf.MessageType",
    provider: EntryProvider,
) -> WardResult:
    """Drive a WARD workflow, answering every `WardEntryRequest` from `provider`.

    Note `Session.call` is used WITHOUT `expect=`: it defaults to the `MessageType`
    base, so either a `WardEntryRequest` or the final `Success` is accepted and we
    dispatch on the type. Using `call_raw` instead would lose Failure-to-exception
    conversion and the button-request handling, both of which we want.

    The loop is not bounded to a single pull on purpose: what a later phase adds is more
    round trips (proof material, lineage), not a different mechanism. Every phase-1
    workflow pulls exactly once, and all pulls in one workflow name the same entry, so
    the last key seen is the workflow's key.
    """
    res = session.call(msg)
    entry_key = b""

    while isinstance(res, messages.WardEntryRequest):
        entry_key = res.entry_key or b""
        answer = provider(entry_key)
        leaf = answer.leaf
        # Hand back exactly what was stored. Absent identity+content means "no entry".
        res = session.call(
            messages.WardEntryAck(
                identity=leaf.identity if leaf is not None else None,
                content=leaf.content if leaf is not None else None,
                proof=answer.proof or [],
                witness_entry_key=answer.witness_entry_key,
                witness_commit=answer.witness_commit,
                sibling_split_bit=answer.sibling_split_bit,
                sibling_left=answer.sibling_left,
                sibling_right=answer.sibling_right,
                sibling_entry_key=answer.sibling_entry_key,
                sibling_commit=answer.sibling_commit,
            )
        )

    if isinstance(res, messages.WardLeafAck):
        return WardResult(
            res,
            res.entry_key or entry_key,
            Leaf(res.identity, res.content),
            res.counter,
            res.mac,
            res.auth_commit,
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
    """Ask the device to display the host-held entry for (app_id, identifier).

    The device derives the keyed path and asks `provider` for the leaf at it; `provider`
    returning None means "no such entry" -- the device says so on screen rather than
    showing an empty value. Returns no leaf, since a read builds none.
    """
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
    """Ask the device to confirm creating or replacing the entry for (app_id, identifier).

    The device pulls the current value from `provider` first, so it shows an "Add entry"
    screen when the entry is new and an "Update entry" screen naming what it replaces
    when it is not.

    **The device does not write.** It returns the leaf it built and the caller must store
    it verbatim under the returned `entry_key` -- see `apply`. A result the caller ignores
    means the user confirmed a write that never happened.

    `value` is typed Optional only so callers can exercise the device-side validation --
    an absent value is rejected, because writing "nothing specified" as if it were an
    empty value would silently blank an entry. Pass b"" for a genuinely empty value.
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
    """Ask the device to confirm deleting the entry for (app_id, identifier).

    The device pulls the entry first so the screen can name the value being removed.

    IDEMPOTENT on a path that already holds nothing: the call succeeds, `auth_commit` is
    None to say no transition happened, the counter is unchanged, and no confirmation is
    shown. `provider` must still PROVE the absence with a non-membership witness -- an
    unwitnessed "I hold none" is refused, so a host cannot get the device to agree that an
    entry it is hiding never existed.

    This covers the retry-after-a-lost-response case only once the caller has applied the
    delete to its own store. A caller that retries while still holding the row serves a
    proof against a root the device has moved past, and is refused.

    **The device does not delete.** It returns a leaf with both parts empty and the
    caller must remove the record at the returned `entry_key` -- see `apply`.
    """
    return _call_answering_pulls(
        session,
        messages.WardDeleteEntry(app_id=app_id, identifier=identifier),
        provider,
    )


def sync(session: "Session") -> messages.WardSyncAck:
    """Open a sync round: the device mints the nonce the WM must sign against.

    The ack also carries the device's current `counter`, which doubles as a "where are you"
    query. A caller that lost a write's response can compare it against its own and learn
    whether the write landed -- without it, the retry fails against a root the device has
    moved past and there is nothing to distinguish that from an entry that never existed.
    """
    return session.call(messages.WardSync(), expect=messages.WardSyncAck)


def ingest_attestation(
    session: "Session",
    counter: int,
    mac: bytes,
    wm_signature: bytes,
    timestamp: int = 0,
) -> messages.WardIngestAttestationAck:
    """Deliver the WM's signed (counter, mac, timestamp) for the open round."""
    return session.call(
        messages.WardIngestAttestation(
            counter=counter, mac=mac, wm_signature=wm_signature, timestamp=timestamp
        ),
        expect=messages.WardIngestAttestationAck,
    )


def recover_counter(
    session: "Session",
    counter: int,
    mac: bytes,
    wm_signature: bytes,
    timestamp: int = 0,
) -> messages.WardRecoverCounterAck:
    """Accept an attestation that goes backwards, after the user confirms.

    Only for recovering a WM whose register or clock regressed. It is the sole path that
    accepts a lower counter, and it holds for confirmation.
    """
    return session.call(
        messages.WardRecoverCounter(
            counter=counter, mac=mac, wm_signature=wm_signature, timestamp=timestamp
        ),
        expect=messages.WardRecoverCounterAck,
    )


def reconcile(session: "Session", root: Optional[bytes]) -> messages.WardReconcileAck:
    """Supply the root and adopt it, if it matches what was attested."""
    return session.call(
        messages.WardReconcile(root=root), expect=messages.WardReconcileAck
    )


def verify_chain(session: "Session", links) -> messages.WardVerifyChainAck:
    """Adopt the attested head by proving it descends from the device's current one.

    Used instead of `reconcile` when the device has fallen more than a step behind.
    `links` are ordered from the device's own head forward.
    """
    return session.call(
        messages.WardVerifyChain(
            links=[
                messages.WardChainLink(
                    from_counter=fc,
                    from_root=fr,
                    to_counter=tc,
                    to_root=tr,
                    auth_commit=ac,
                )
                for (fc, fr, tc, tr, ac) in links
            ]
        ),
        expect=messages.WardVerifyChainAck,
    )


def rollback(
    session: "Session", to_root: Optional[bytes], auth_commit: bytes
) -> messages.WardRollbackAck:
    """Undo the device's most recent transition, one step.

    `auth_commit` is the authorisation that CREATED the current head, which the caller
    holds as the last entry of its transition log. The device checks it names its own
    counter and root, so the demotion target cannot be chosen by the caller.
    """
    return session.call(
        messages.WardRollback(to_root=to_root, auth_commit=auth_commit),
        expect=messages.WardRollbackAck,
    )


def apply_rollback(store, ack: messages.WardRollbackAck) -> None:
    """Roll the caller's store back to match, and record the demotion as a transition.

    The store must be able to reproduce the demoted tree, so this only rewinds the
    bookkeeping -- restoring the leaves themselves is the caller's business, since only it
    knows what the earlier tree held.
    """
    store.links.append(
        (
            store.counter,
            store.root(),
            ack.counter,
            ack.new_root or None,
            ack.auth_commit,
        )
    )
    store.counter = ack.counter


def leaf_is_delete(leaf: Optional[Leaf]) -> bool:
    """A leaf whose content body is empty is a deletion, not an empty-valued entry."""
    if leaf is None or leaf.content is None:
        return True
    content = leaf.content
    if content.plaintext is not None:
        return not content.plaintext.content
    if content.encrypted is not None:
        return not content.encrypted.ct
    return True


def store_provider(store) -> EntryProvider:
    """An `EntryProvider` backed by anything with the `WardTrie` shape.

    Serving needs NO key: the leaf commitment is over the encoded parts, so a host proves
    what it holds without being able to read it. Note also what the store is not keyed by
    -- there is no identifier in it anywhere, which is what the keyed path buys.
    """

    def provider(entry_key: bytes) -> Answer:
        if entry_key in store:
            sib = store.sibling_decomposition(entry_key)
            leaf_sib = store.sibling_leaf(entry_key) if sib is None else None
            return Answer(
                leaf=store.blobs[entry_key],
                proof=store.membership_proof(entry_key),
                sibling_split_bit=None if sib is None else sib[0],
                sibling_left=None if sib is None else sib[1],
                sibling_right=None if sib is None else sib[2],
                sibling_entry_key=None if leaf_sib is None else leaf_sib[0],
                sibling_commit=None if leaf_sib is None else leaf_sib[1],
            )
        proof, witness_key, witness_commit = store.nonmembership_proof(entry_key)
        return Answer(
            proof=proof, witness_entry_key=witness_key, witness_commit=witness_commit
        )

    return provider


def apply(store, result: WardResult) -> None:
    """Apply a confirmed write or delete to the caller's store.

    The device confirmed and built the leaf; persisting it is the host's job, and a
    result the caller drops on the floor means the user approved a change that never
    happened. An empty content body is a delete, so the record goes away rather than
    being kept as a tombstone.

    NO AUTH_COMMIT MEANS NOTHING CHANGED. A delete of an already-absent path succeeds
    idempotently and authorises no transition, so there is nothing to apply. That is
    asserted rather than assumed: if the device reports no transition while the store still
    holds the entry, the two disagree about the world, and continuing would leave a row the
    device believes is gone -- every later proof for it refused, with nothing to say why.
    Failing here names it instead.
    """
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
    if leaf_is_delete(result.leaf):
        store.remove(result.entry_key)
    else:
        store.set(result.entry_key, result.leaf)

    # Keep the counter with the root. The device is the counter authority, and a store
    # that tracked only the root could not tell the WM which state it is publishing.
    if result.counter is not None:
        # The transition log. The host cannot forge or read these -- it holds them so
        # another device of the wallet can verify the steps it missed.
        store.links.append(
            (
                before_counter,
                before_root,
                result.counter,
                store.root(),
                result.auth_commit,
            )
        )
        store.counter = result.counter
