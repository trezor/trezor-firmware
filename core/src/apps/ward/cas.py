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
    from trezor.wire import DataError

    from .attest import root_or_empty

    # Fixed widths, for the reason spelled out in `leaf.leaf_hash_of`: concatenating
    # variable-length fields leaves the boundary ambiguous, and here from_root || to_counter
    # || to_root can be re-split so a shifted (to_counter, to_root) reproduces a genuine
    # authorisation byte for byte. Nothing exploits that today -- the shifted counter lands
    # out of range and the handlers reject it -- which is accident, not design.
    from_root = root_or_empty(from_root)
    to_root = root_or_empty(to_root)
    if len(ward_id) != 32 or len(from_root) != 32 or len(to_root) != 32:
        raise DataError("WARD: transition operands must be 32 bytes")

    return (
        tag
        + ward_id
        + from_counter.to_bytes(4, "big")
        + from_root
        + to_counter.to_bytes(4, "big")
        + to_root
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


# --- the queued INTENT ---------------------------------------------------------------------
#
# A queued change can be exported for BACKUP and handed back later. What comes back is host-held
# material, so the device must be able to tell its own intent from anything else -- which is what
# `delete_entry` records as decided and unbuilt: "a queued intent additionally carries a MAC over
# (entry_key, op, counter) under K_auth" -- over the IDENTITY rather than the path, since a queued
# change has no path until it is published, and the path is derived from the identity anyway.
#
# THE COUNTER IS NOT IN HERE. A restore sends only the fields the host was given, and the record's
# counter is not one of them -- a restored change comes back at "no counter assigned", because after
# a restore nobody knows whether an earlier publication landed. That is the honest state, and it
# costs the replay bound `delete_entry` wanted the counter for: adding it back is a WIRE change.
#
# Same key as a transition, because the question is the same one: was this produced by a device of
# THIS wallet. A different key would buy nothing -- the verifier set is identical -- and the tag
# below is what keeps the two preimages from ever colliding.

TAG_INTENT = b"WARD INTENT v1"

OP_SET = 1  # queue a value at a path
# OP_DELETE is deliberately absent: a queued delete needs the sealed tombstone `delete_entry`
# describes, and until that exists there is no delete intent to authenticate. The op is inside the
# MAC anyway, so adding one later does not change the preimage's shape.


def intent_preimage(
    ward_id: bytes,
    op: int,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
) -> bytes:
    """The bytes a queued intent is authenticated over.

    THE VALUE IS BOUND, not just the path. The blob travels in the clear, so a MAC over
    (identity, op) alone would authenticate a KEY while leaving the host free to substitute any value
    at it -- protection that looks like protection and is not. Everything the device would
    write back on a restore is therefore in here.

    Length-prefixed, not concatenated, for the reason `transition_preimage` and `leaf.leaf_hash_of`
    already give: adjacent variable-length fields leave their boundary ambiguous, so
    (app_id="ab", identifier="c") and (app_id="a", identifier="bc") would otherwise MAC alike.

    THE IDENTITY IS WHAT IS BOUND, not the keyed path. The path is a deterministic function of
    (key_type, app_id, identifier) under K_path, so binding the identity binds the path it derives --
    and a queued change HAS no path yet, which is why the store does not hold one either. `ward_id`
    keeps this scoped to the wallet, so a blob cannot be replayed into a different one.

    NOT `offline_store.encode_record`. That is the canonical form of a record in FLASH -- it is
    prefixed with the device-local slot key and its sameness is what makes a no-op refresh
    detectable. This is a WIRE contract. Two encoders for two audiences, deliberately, because a
    change to either one for its own reasons must not silently redefine the other.
    """
    from trezor.wire import DataError

    kt = key_type.encode()
    ai = app_id.encode()
    if len(ward_id) != 32:
        raise DataError("WARD: intent operands must be 32 bytes")
    if len(kt) > 0xFF or len(ai) > 0xFF:
        raise DataError("WARD: key_type or app_id too long to authenticate")
    if len(identifier) > 0xFFFF or len(value) > 0xFFFF:
        raise DataError("WARD: identifier or value too long to authenticate")

    return (
        TAG_INTENT
        + ward_id
        + bytes([op])
        + bytes([len(kt)])
        + kt
        + bytes([len(ai)])
        + ai
        + len(identifier).to_bytes(2, "big")
        + identifier
        + len(value).to_bytes(2, "big")
        + value
    )


def intent_mac(
    k_auth: bytes,
    ward_id: bytes,
    op: int,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
) -> bytes:
    """Authenticate a queued intent. Only a device holding the seed can produce this."""
    from trezor.crypto import hmac

    return hmac(
        hmac.SHA256,
        k_auth,
        intent_preimage(ward_id, op, key_type, app_id, identifier, value),
    ).digest()


def verify_intent_mac(
    k_auth: bytes,
    ward_id: bytes,
    op: int,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
    mac: bytes,
) -> bool:
    """Did a device of this wallet queue EXACTLY this intent?

    Note what a true answer does and does not mean. It means these bytes were queued by a device
    of this wallet at some point. It does NOT mean they should be queued again now -- see the
    replay note in `queue_set_entry`.
    """
    expected = intent_mac(k_auth, ward_id, op, key_type, app_id, identifier, value)
    return expected == mac
