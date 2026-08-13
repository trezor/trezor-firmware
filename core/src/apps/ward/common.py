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


def display_bytes(value: bytes) -> str:
    """Best-effort rendering of an arbitrary byte string for a trusted screen:
    UTF-8 when it decodes cleanly, otherwise hex."""
    try:
        return value.decode()
    except UnicodeError:
        from ubinascii import hexlify

        return hexlify(value).decode()


def require_key(app_id: str | None, identifier: bytes | None) -> "tuple[str, bytes]":
    """Validate the (app_id, identifier) pair every WARD request carries.

    The wire fields are `optional` on purpose -- a proto2 `required` field a caller
    forgets to set is an encode-time failure in every binding -- so the check lives
    here instead, and runs before anything is derived, pulled or shown.

    Also refuses an uninitialised device: deriving the keyed path needs a seed.
    """
    from trezor.wire import DataError

    from apps.common.seed import raise_if_not_initialized

    raise_if_not_initialized()

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
      write_material  (proof, witness_entry_key, witness_commit, sibling_node), which a
                      write feeds to `trie.compute_new_root`.

    The identity part is returned but nothing reads it yet: the device already knows the
    identifier and app_id, having derived the path from them, so it is carried only
    because the leaf hash commits to it.
    """
    from trezor.messages import WARDEntryAck, WARDEntryRequest
    from trezor.wire import context

    from .keys import derive_k_data
    from .leaf import (
        decode_content,
        is_delete,
        read_leaf_content,
        read_leaf_identity,
    )

    # Mirrors apps/webauthn/list_resident_credentials.py, which uses the same primitive
    # to ask the host for data mid-workflow.
    ack = await context.call(
        WARDEntryRequest(entry_key=entry_key),
        expected_type=WARDEntryAck,
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
    material = (
        ack.proof,
        ack.witness_entry_key,
        ack.witness_commit,
        sibling_node,
    )

    if not present:
        return None, None, material

    # Opening is the other half of authenticity: a part the host forged, corrupted, or
    # lifted from another path fails the tag and raises here.
    decoded = decode_content(await derive_k_data(key_type), entry_key, key_type, val_part)
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

    Does nothing when the device holds no root: there is then nothing to check against,
    and checking a proof against a root the host supplied would be theatre. That is the
    state every release build is in today -- see `root.py` -- and it is why the screens
    still warn.
    """
    from trezor.wire import DataError

    from .trie import verify_membership, verify_nonmembership

    if root is None:
        return

    if present:
        if not verify_membership(
            entry_key, key_type, id_part, val_part, proof, root
        ):
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
