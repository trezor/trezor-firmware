"""Device-level proof-soundness checks for the hardened WARD trie verifier."""

from __future__ import annotations

import pytest

from trezorlib import ward, ward_crypto
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session

from ...ward_mgr_emu import device_ward_keys

_APP = "bitcoin"
_K_PATH, _K_DATA, _K_IDENT = device_ward_keys()

pytestmark = [pytest.mark.models("core")]


def _tree() -> WARDTree:
    return WARDTree(_K_PATH, _K_DATA, _K_IDENT)


def _addr_bit(entry_key: bytes, bit: int) -> int:
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def _find_identifier_with_bits(prefix_bits: tuple[int, ...]) -> bytes:
    tree = _tree()
    for i in range(200000):
        ident = f"ward-mpt-{i:06d}".encode()
        ek = tree._ek(_APP, ident, "address", 0)
        if tuple(_addr_bit(ek, b) for b in range(len(prefix_bits))) == prefix_bits:
            return ident
    raise AssertionError(f"no identifier found for prefix bits {prefix_bits}")


def _crafted_tree() -> tuple[WARDTree, bytes, bytes, bytes]:
    """Return a 3-leaf tree with the exact prefix layout needed for the attack.

    Prefixes:
    - target  = 010...
    - witness = 011...
    - other   = 1...

    That ensures the witness proof has two steps: actual split at bit 2, then the
    root split at bit 0. Relabelling bit 2 -> bit 1 preserves witness
    reconstruction while making the target falsely appear to share the witness path.
    """
    target = _find_identifier_with_bits((0, 1, 0))
    witness = _find_identifier_with_bits((0, 1, 1))
    other = _find_identifier_with_bits((1,))

    tree = _tree()
    tree.insert(_APP, target, b"target-present", counter=1)
    tree.insert(_APP, witness, b"witness-present", counter=1)
    tree.insert(_APP, other, b"other-present", counter=1)
    return tree, target, witness, other


def test_ward_lookup_rejects_relabelled_nonmembership_proof(session: Session) -> None:
    """A present key must not verify as absent under a relabelled witness proof."""
    tree, target, witness, _other = _crafted_tree()
    ward.debug_set_root(session, tree.get_root_hash())

    target_ek = tree._ek(_APP, target, "address", 0)
    witness_ek = tree._ek(_APP, witness, "address", 0)
    witness_leaf = tree.get_leaf(witness_ek)
    assert witness_leaf is not None

    honest_proof = tree.get_proof_by_key(witness_ek)
    assert len(honest_proof) == 2
    assert int.from_bytes(honest_proof[0][0:2], "big") == 2
    assert int.from_bytes(honest_proof[0][2:4], "big") == 1
    assert int.from_bytes(honest_proof[1][0:2], "big") == 0
    assert int.from_bytes(honest_proof[1][2:4], "big") == 0

    # Sanity-check the intended vulnerable prefix layout on the actual derived keys.
    assert tuple(_addr_bit(target_ek, b) for b in range(3)) == (0, 1, 0)
    assert tuple(_addr_bit(witness_ek, b) for b in range(3)) == (0, 1, 1)

    forged_proof = [
        (1).to_bytes(2, "big") + (0).to_bytes(2, "big") + honest_proof[0][4:],
        honest_proof[1],
    ]
    witness_commit = ward_crypto.commit_of(
        witness_leaf
    )

    valid, membership, counter = ward.lookup(
        session,
        _APP,
        target,
        forged_proof,
        witness_entry_key=witness_ek,
        witness_commit=witness_commit,
    )

    assert not valid, (
        "forged non-membership proof for a PRESENT key was accepted: "
        f"valid={valid}, membership={membership}, counter={counter}"
    )
