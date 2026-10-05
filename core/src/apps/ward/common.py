from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from trezor.messages import WardLeafAck, WardMutationApplied
    from trezor.ui.layouts import StrPropertyType

# Every screen carries this. The AEAD stops a host forging a value or moving a leaf between
# paths, but it can still serve an OLDER sealed leaf or deny holding one: the value is
# authentic, its freshness is not proven.
# FIXME(ward): do NOT remove until proofs against an attested root land.
WARNING_UNVERIFIED: "StrPropertyType" = (
    "Warning",
    "Not proven current; may be out of date.",
    False,
)

# FIXME(ward): all WARD screen strings are hardcoded English; move them to TR.* before shipping.

# GAP(ward): a host cannot know whether its replica is COMPLETE -- a missing leaf yields a
# well-formed proof against a different root. The device is the completeness oracle: an
# accepted adoption proves the replica held the tree that step produced. One refusal therefore
# covers a replica that is behind, one that is partial, and data that is lost; only
# `WardRollback` recovers the last.


def display_bytes(value: bytes) -> str:
    """UTF-8 when it decodes cleanly, otherwise hex."""
    try:
        return value.decode()
    except UnicodeError:
        # NOT `ubinascii`: this firmware has no such module.
        return value.hex()


def require_initialized() -> None:
    """Every WARD request needs a seed."""
    from apps.common.seed import raise_if_not_initialized

    raise_if_not_initialized()


def require_key(app_id: str | None, identifier: bytes | None) -> "tuple[str, bytes]":
    """Validate the (app_id, identifier) pair, before anything is derived, pulled or shown.

    GAP(ward): app_id comes from the wire, so it is a namespace, not a permission.
    """
    from trezor.wire import DataError

    require_initialized()

    if not app_id or not identifier:
        raise DataError("app_id and identifier are required")
    return app_id, identifier


async def online() -> bool:
    """Whether a WM attestation has been bound to a held tree in THIS session.

    A service build drives one sync attempt itself and raises whatever it failed with; a
    connect build can only report what the host has already done.
    """
    from . import round as sync_round

    if sync_round.is_online():
        return True

    if not utils.USE_WARD_SERVICE_CHANNEL:
        return False

    from .service import become_ready

    return await become_ready()


async def online_or_offline() -> bool:
    """`online`, but a failed sync answers False. Only for `label`, which may fall back to the
    device's own store and says so on screen."""
    try:
        return await online()
    except Exception:
        return False


async def pull_leaf(
    entry_key: bytes,
    key_type: str,
    root: "bytes | None" = None,
    staged: "tuple | None" = None,
) -> tuple:
    """Ask the backend for its leaf at `entry_key`, verify it against the trusted root, open it.

    Returns `(value, old_leaf, (proof, witness_entry_key, witness_commit))`; value and old_leaf
    are None when nothing is there. `root`/`staged` are given only by a batched flush, to prove
    against its running root.
    """
    from trezor.wire import DataError

    from .keys import derive_k_data
    from .leaf import (
        decode_content,
        is_delete,
        read_leaf_content,
        read_leaf_identity,
    )
    from .root import get_counter, get_root

    if utils.USE_WARD_SERVICE_CHANNEL:
        from .service import fetch

        # A batched flush is connect-only; nothing on a service build stages a leaf.
        assert staged is None
        ack = await fetch(entry_key)
    else:
        from trezor.messages import WardEntryAck, WardEntryRequest, WardStagedLeaf
        from trezor.wire import context

        request = WardEntryRequest(entry_key=entry_key)
        if staged is not None:
            request.staged = WardStagedLeaf(entry_key=staged[0], commit=staged[1])
        ack = await context.call(request, expected_type=WardEntryAck)

    val_part = read_leaf_content(ack.content)
    wire_key_type, id_part = read_leaf_identity(ack.identity)
    present = val_part is not None and not is_delete(val_part)

    # The key_type is an input to entry_key, so the host does not get to name it.
    if wire_key_type is not None and wire_key_type != key_type:
        raise DataError("WARD: leaf key_type does not match the requested path")

    # Verified BEFORE opening anything; an absence has to be proved too.
    verify_leaf_against_root(
        await get_root() if root is None else root,
        await get_counter(),
        entry_key,
        key_type,
        id_part,
        val_part,
        present,
        ack.proof,
        ack.witness_entry_key,
        ack.witness_commit,
    )

    material = (ack.proof, ack.witness_entry_key, ack.witness_commit)
    if not present:
        return None, None, material

    # The AAD binds the part to this path and key type, so a successful open is authenticity.
    decoded = decode_content(
        await derive_k_data(key_type), entry_key, key_type, val_part
    )
    value = None if decoded is None else decoded[1]
    return value, (key_type, id_part, val_part), material


async def pull_entry(entry_key: bytes, key_type: str) -> bytes | None:
    """Just the value, for the read path -- see `pull_leaf`."""
    value, _old_leaf, _material = await pull_leaf(entry_key, key_type)
    return value


async def finish_write(
    entry_key: bytes,
    identity,
    content,
    from_root: bytes | None,
    counter: int,
    new_root: bytes | None,
) -> "WardLeafAck | WardMutationApplied":
    """Authorise `(counter - 1, from_root) -> (counter, new_root)` and hand it on.

    NOT COMMITTED HERE: the head moves only when a WM attestation names this transition and the
    device re-verifies it. A connect build returns the leaf and authorisations; a service build
    publishes and adopts, returning no leaf -- a replica owner reads an absent content body as a
    deletion.
    """
    from .cas import authorise

    step, advance = await authorise(counter - 1, from_root, counter, new_root)

    if utils.USE_WARD_SERVICE_CHANNEL:
        from trezor.messages import WardMutationApplied

        from .service import publish

        await publish(
            entry_key, identity, content, from_root, counter, new_root, step, advance
        )
        return WardMutationApplied(entry_key=entry_key, counter=counter)

    from trezor.messages import WardLeafAck

    return WardLeafAck(
        entry_key=entry_key,
        identity=identity,
        content=content,
        counter=counter,
        auth_commit=step,
        wm_sig=advance,
    )


def verify_leaf_against_root(
    root: bytes | None,
    counter: int,
    entry_key: bytes,
    key_type: str,
    id_part,
    val_part,
    present: bool,
    proof,
    witness_entry_key,
    witness_commit,
) -> None:
    """Check the host's answer against the device's trusted root, or raise.

    No root at counter 0 is a genuinely empty wallet and passes; no root at a non-zero counter
    fails, because "cannot verify" must never read as "verified". An EMPTY_ROOT tree admits only
    absence, with no witness needed.
    """
    from trezor.wire import DataError

    from .attest import EMPTY_ROOT
    from .trie import verify_membership, verify_nonmembership

    if root is None:
        if counter > 0:
            raise DataError("no trusted root; sync before reading")
        return

    if root == EMPTY_ROOT:
        if present:
            raise DataError("WARD: the tree is empty; no entry can be in it")
        return

    if present:
        if not verify_membership(entry_key, key_type, id_part, val_part, proof, root):
            raise DataError("WARD: entry does not match the trusted root")
        return

    if witness_entry_key is None or witness_commit is None:
        raise DataError("WARD: absence claimed without a witness")
    if not verify_nonmembership(
        entry_key, witness_entry_key, witness_commit, proof, root
    ):
        raise DataError("WARD: absence does not match the trusted root")
