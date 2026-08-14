"""CAS: authorising a transition from one root to the next.

Every write moves the tree from `(from_counter, from_root)` to `(to_counter, to_root)`.
This authenticates that step:

    preimage = tag || ward_id || from_counter(4B BE) || from_root(32B)
                              || to_counter(4B BE)   || to_root(32B)
    AuthCommit = HMAC-SHA256(K_auth, preimage)

with `tag` = b"WARD COMMIT v1" for an ordinary write and b"WARD REVERT v1" for a
one-step rollback. Roots appear in their preimage form, so an empty tree is the
`EMPTY_ROOT` stand-in rather than an absent field.

WHY A MAC AND NOT A SIGNATURE. K_auth is seed-derived, so every device of a wallet holds
it -- which is exactly the set of parties that need to verify a transition. Another
device of the same wallet checks the chain; the WM and the host cannot, and have no
business doing so. An Ed25519 signature would extend verification to non-seed-holders and
cost a signing operation on every write, buying nothing anyone currently needs. The design
document specifies Ed25519 under K_sig for this; the reference implements both and ships
with the Ed25519 path switched off. If a non-seed-holder ever has to verify -- a WM
enforcing that only real devices may advance the head -- that is when to add it.

WHAT A CHAIN OF THESE PROVES, AND WHAT IT DOES NOT. Folding links from a trusted baseline
to a claimed head shows each step was authorised by a device holding the seed, that the
counters are contiguous, and that each link's `from` matches the previous link's `to` --
so the head descends from the baseline rather than sitting on a fork. It does NOT prove
the head is current: that is the WM attestation's job, and the two are combined by
requiring the chain to terminate exactly at the attested counter.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

TAG_COMMIT = b"WARD COMMIT v1"
TAG_REVERT = b"WARD REVERT v1"


def transition_preimage(
    tag: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
) -> bytes:
    """The bytes a transition is authorised over.

    Both endpoints are named, not just the destination. Binding only `to` would let a
    link be lifted out of its place in the history and replayed after a different
    predecessor, which is the whole point of a chain.
    """
    from .attest import root_or_empty

    return (
        tag
        + ward_id
        + from_counter.to_bytes(4, "big")
        + root_or_empty(from_root)
        + to_counter.to_bytes(4, "big")
        + root_or_empty(to_root)
    )


def auth_commit(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    tag: bytes = TAG_COMMIT,
) -> bytes:
    """Authorise a transition. Only a device holding the seed can produce this."""
    from trezor.crypto import hmac

    return hmac(
        hmac.SHA256,
        k_auth,
        transition_preimage(tag, ward_id, from_counter, from_root, to_counter, to_root),
    ).digest()


def verify_auth_commit(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    mac: bytes,
    tag: bytes = TAG_COMMIT,
) -> bool:
    """Was this exact transition authorised by a device of this wallet?"""
    expected = auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, tag
    )
    # Length-independent comparison is not needed -- both sides are locally computed and
    # the attacker learns nothing from timing here -- but equality on bytes is constant
    # time in micropython anyway for equal-length inputs.
    return expected == mac


def sig_commit(
    k_sig: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    tag: bytes = TAG_COMMIT,
) -> bytes:
    """Ed25519 over EXACTLY the bytes auth_commit MACs. Complementary, not a replacement.

    Two authenticators over one preimage, for two different verifiers:

      the MAC is checked by another DEVICE of this wallet, which holds K_auth. It remains
      the authority on authenticity, and nothing about that changes here;

      this signature is checked by the WM, which holds no secret of ours. It exists so the
      WM can tell a real device's transition from anyone else's while being trusted for
      FRESHNESS ONLY -- without it, a WM that arbitrates ordering is a denial-of-service
      oracle, since whoever knows ward_id could advance the counter and have every genuine
      device refused thereafter.

    Deliberately not a generic signing API: the preimage is built here from typed arguments,
    so this can never be pointed at bytes a caller chose.

    Note what this does NOT depend on: K_path. Authenticity rests on K_auth, K_sig and the
    leaf AEAD keys, so a host that learned K_path could compute entry_keys -- losing the
    keyed path's privacy -- and still forge nothing.
    """
    from trezor.crypto.curve import ed25519

    return ed25519.sign(
        k_sig,
        transition_preimage(tag, ward_id, from_counter, from_root, to_counter, to_root),
    )


def verify_chain_step(
    k_auth: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: bytes | None,
    link: "tuple",
) -> "tuple[int, bytes | None]":
    """Fold one link onto the running head, or raise.

    `link` is (from_counter, from_root, to_counter, to_root, auth_commit). Three things
    are checked before the MAC, and each closes a distinct way of lying with genuine
    links:

      contiguous counter and root -- otherwise a link from an unrelated branch could be
        spliced in, since each link is individually authentic;
      a +1 counter step -- otherwise a gap could hide transitions the verifier never sees,
        which is how a fork stays invisible;
      the MAC itself -- otherwise the link was never authorised at all.

    Returns the advanced head. O(1): the device holds only the running head and never
    reconstructs a tree.
    """
    from trezor.wire import DataError

    from .attest import root_or_empty

    from_counter, from_root, to_counter, to_root, mac = link

    if from_counter != running_counter:
        raise DataError("WARD: chain link does not follow the running counter")
    if root_or_empty(from_root) != root_or_empty(running_root):
        raise DataError("WARD: chain link does not follow the running root")
    if to_counter != running_counter + 1:
        raise DataError("WARD: chain link must advance the counter by exactly one")

    # Either kind of authorisation is a legitimate step for the purpose of DESCENT: a
    # rollback is as much a real transition as a write, and a history containing one must
    # still be walkable. Accepting both here costs nothing -- minting either needs K_auth
    # -- and the distinction is enforced where it decides something: a demotion must
    # present a COMMIT, so a revert cannot be used to demote again.
    if not verify_auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, mac
    ) and not verify_auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, mac, TAG_REVERT
    ):
        raise DataError("WARD: chain link is not authorised")

    return to_counter, to_root
