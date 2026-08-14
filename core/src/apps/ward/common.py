from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.ui.layouts import StrPropertyType

# Every screen carries this. Sealing the leaf narrowed what needs warning about, but did
# not remove it:
#
#   the host CANNOT forge a value, or move a leaf from one path to another -- the AEAD tag
#   fails, so anything that reaches a screen really was sealed by this device for this
#   path;
#   the host CAN return an OLDER sealed leaf for that path, or claim it holds none at all.
#
# So the value is authentic but its freshness is unproven, and that is what the wording
# has to say. It would be actively worse to soften this to "encrypted": a decrypted value
# looks authoritative on screen, so a vaguer warning next to a more trustworthy value
# misleads more than the blunt version did.
#
# FIXME(ward): do NOT remove this warning until proofs against an attested root land --
# only those detect a stale leaf or a suppressed entry.
WARNING_UNVERIFIED: "StrPropertyType" = (
    "Warning",
    "Not proven current; may be out of date.",
    False,
)

# FIXME(ward): all WARD screen strings are hardcoded English. They need to move into the
# translation blobs (TR.*) before this is shippable; kept literal while the wire shape
# and the screens are still moving.

# GAP(ward): a host cannot know whether its replica is COMPLETE, and this is where that
# surfaces.
#
# A root commits to the whole key set, so a replica missing one leaf does not fail to produce
# a proof -- it produces a well-formed proof that reconstructs to a DIFFERENT root. In an
# eventually-consistent store there is no completeness signal either: "I have everything" and
# "I am still missing rows" are the same observation, which is what eventual consistency
# declines to distinguish. The host cannot check itself against the WM's head, because it
# cannot verify a mac.
#
# So the DEVICE is the completeness oracle, and `WardReconcile` is how it is consulted: an
# accepted reconcile means the host's root matched the attested mac, i.e. its replica really
# was complete at that counter.
#
# Replaying the store's own history (docs/core/misc/ward-trie.md) NARROWS this rather than
# removing it: contiguous counters up to the attested one let the host notice it is MISSING
# something. It still cannot tell whether the head it knows about is current, nor whether the
# history is genuine -- it is the host's own record either way. Currency and authenticity stay
# with the device.
#
# The cost is that ONE refusal below covers three different situations -- a replica that is
# behind, a replica that is partial, and data that is permanently lost -- and the device
# cannot tell them apart. Only the first two are waitable; the third needs `WardRollback`,
# which is why that screen is dangerous rather than routine. See `rollback.py`.


def display_bytes(value: bytes) -> str:
    """Best-effort rendering of an arbitrary byte string for a trusted screen:
    UTF-8 when it decodes cleanly, otherwise hex."""
    try:
        return value.decode()
    except UnicodeError:
        # NOT `ubinascii` -- this firmware has no such module, and the mistake hides:
        # the fallback only runs for non-UTF-8 values, which tests rarely supply.
        return value.hex()


def require_initialized() -> None:
    """Every WARD request needs a seed: the keyed path, the leaf keys and ward_id all
    derive from it."""
    from apps.common.seed import raise_if_not_initialized

    raise_if_not_initialized()


def require_key(app_id: str | None, identifier: bytes | None) -> "tuple[str, bytes]":
    """Validate the (app_id, identifier) pair every WARD request carries.

    GAP(ward): app_id is taken from the WIRE, so there is no ACL -- any caller may claim any
    app_id and read another app's entries. The intended model has core fill it in from the
    caller's identity, which needs a notion of app identity the device does not have yet.
    Deferred until an app boundary actually exists; until then app_id is a namespace, not a
    permission.

    The wire fields are `optional` on purpose -- a proto2 `required` field a caller
    forgets to set is an encode-time failure in every binding -- so the check lives
    here instead, and runs before anything is derived, pulled or shown.

    Also refuses an uninitialised device: deriving the keyed path needs a seed.
    """
    from trezor.wire import DataError

    require_initialized()

    if not app_id or not identifier:
        raise DataError("app_id and identifier are required")
    return app_id, identifier


async def pull_leaf(entry_key: bytes, key_type: str) -> tuple:
    """PULL the host's leaf for an already-derived keyed path, verified.

    This is the one mechanism the whole subsystem is built on: the device holds nothing,
    so it asks the host mid-workflow and the host answers while its own call is still in
    flight. The request names ONLY the opaque path -- see `keys.entry_key_for`.

    Returns `(value, old_leaf, write_material)`:

      value           the decoded value, or None when nothing is there (no such entry, or
                      a tombstone). Distinct from b"", an entry whose value IS empty.
      old_leaf        (key_type, id_part, val_part) as received, or None -- what a write
                      must prove it is replacing.
      write_material  (proof, witness_entry_key, witness_commit, sibling_node,
                      sibling_leaf), which a write feeds to `trie.compute_new_root`.

    The identity part is returned but nothing reads it yet: the device already knows the
    identifier and app_id, having derived the path from them, so it is carried only
    because the leaf hash commits to it.
    """
    from trezor.messages import WardEntryAck, WardEntryRequest
    from trezor.wire import context

    from .keys import derive_k_data
    from .leaf import decode_content, is_delete, read_leaf_content, read_leaf_identity

    # Mirrors apps/webauthn/list_resident_credentials.py, which uses the same primitive
    # to ask the host for data mid-workflow.
    ack = await context.call(
        WardEntryRequest(entry_key=entry_key),
        expected_type=WardEntryAck,
    )

    val_part = read_leaf_content(ack.content)
    wire_key_type, id_part = read_leaf_identity(ack.identity)
    present = val_part is not None and not is_delete(val_part)
    leaf_key_type = wire_key_type or key_type

    # Check the answer against the root the device trusts, BEFORE opening anything. A host
    # that says "no such entry" has to prove it, or it could hide any entry it dislikes
    # simply by denying it exists.
    from .root import get_root

    _verify_against_root(
        await get_root(),
        entry_key,
        leaf_key_type,
        id_part,
        val_part,
        present,
        ack.proof,
        ack.witness_entry_key,
        ack.witness_commit,
    )

    sibling_node = None
    if ack.sibling_split_bit is not None:
        sibling_node = (
            ack.sibling_split_bit,
            ack.sibling_left or b"",
            ack.sibling_right or b"",
        )
    sibling_leaf = None
    if ack.sibling_entry_key is not None and ack.sibling_commit is not None:
        sibling_leaf = (ack.sibling_entry_key, ack.sibling_commit)
    material = (
        ack.proof,
        ack.witness_entry_key,
        ack.witness_commit,
        sibling_node,
        sibling_leaf,
    )

    if not present:
        return None, None, material

    # Opening is the other half of authenticity: a part the host forged, corrupted, or
    # lifted from another path fails the tag and raises here.
    decoded = decode_content(
        await derive_k_data(key_type), entry_key, key_type, val_part
    )
    value = None if decoded is None else decoded[1]
    return value, (leaf_key_type, id_part, val_part), material


async def pull_entry(entry_key: bytes, key_type: str) -> bytes | None:
    """Just the value, for the read path -- see `pull_leaf`."""
    value, _old_leaf, _material = await pull_leaf(entry_key, key_type)
    return value


def _verify_against_root(
    root: bytes | None,
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

    Does nothing when the device holds NO root: there is then nothing to check against,
    and checking a proof against a root the host supplied would be theatre. That is the
    state every release build is in today -- see `root.py` -- and it is why the screens
    still warn.

    An EMPTY TREE is a different thing entirely and is checked here rather than waved
    through. It used to be recorded as "no root", so deleting a wallet's last entry
    silently turned verification off -- reachable by ordinary use, and from a state the
    user has every reason to think is protected. The tree now says it is empty, and an
    empty tree has exactly one honest answer: nothing is present, and no witness is needed
    to say so, since there is no leaf to exhibit.
    """
    from trezor.wire import DataError

    from .attest import EMPTY_ROOT
    from .trie import verify_membership, verify_nonmembership

    if root is None:
        return

    if root == EMPTY_ROOT:
        if present:
            raise DataError("WARD: the tree is empty; no entry can be in it")
        return

    if present:
        if not verify_membership(entry_key, key_type, id_part, val_part, proof, root):
            raise DataError("WARD: entry does not match the trusted root")
        return

    # Absence has to be proved too. An empty tree is the one case with nothing to show:
    # the device knows the tree is empty because it holds no root at all, which is
    # handled above, so reaching here without a witness means the host simply declined.
    if witness_entry_key is None or witness_commit is None:
        raise DataError("WARD: absence claimed without a witness")
    if not verify_nonmembership(
        entry_key, witness_entry_key, witness_commit, proof, root
    ):
        raise DataError("WARD: absence does not match the trusted root")
