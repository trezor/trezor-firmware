"""CAS: authorising a transition from one root to the next. The ONLY authority in WARD.

Every write moves the tree from `(from_counter, from_root)` to `(to_counter, to_root)`.
This authenticates that step:

    preimage   = len8(tag) || tag || ward_id || from_counter(4B BE) || from_root(32B)
                                             || to_counter(4B BE)   || to_root(32B)
    AuthCommit = HMAC-SHA256(K_auth, preimage)

with `tag` = b"WARD COMMIT v3" for an ordinary write and b"WARD REVERT v3" for a
rollback. Roots appear in their preimage form, so an empty tree is the `EMPTY_ROOT`
stand-in rather than an absent field.

THIS IS THE ONLY KEYED CONSTRUCTION LEFT. There used to be a second, `root_mac` under a separate
K_mac: a commitment to `(counter, root)` that the WM stored, compare-and-swapped on and attested,
and that the transition preimage named in place of the roots themselves. Its purpose was to keep
the WM blind to roots and to make a head unforgeable by the WM. It is gone, and the WM now holds
`(counter, root)` in the clear.

WHAT THAT COSTS, STATED PLAINLY RATHER THAN QUIETLY DROPPED. The WM sees the root sequence, and
roots are content-addressed, so it can watch a wallet return to a state it held before. And it
can now NAME A STATE THIS WALLET NEVER REACHED: it could not compute a mac, but it can certainly
attest a root it invented. A malicious WM used to be bounded to replaying genuine history; it is
no longer.

WHAT CATCHES THAT INSTEAD, AND WHY IT IS ENOUGH. Descent. `verify_chain` anchors on the attested
head and walks authorised links BACK to the device's own, so an invented root has no chain into
it -- forging one needs K_auth, which the WM does not have. A WM's attestation is therefore a
claim about FRESHNESS and ordering only, and the chain is what makes it a claim about state. The
weaker route, `reconcile`, folds a single link for the same reason rather than taking the root on
the WM's word: see the note there about what one link does and does not prove.

WHY A MAC AND NOT A SIGNATURE. K_auth is seed-derived, so every device of a wallet holds
it -- which is exactly the set of parties that need to verify a transition. Another
device of the same wallet checks the chain; the WM and the host cannot, and have no
business doing so. An Ed25519 signature would extend verification to non-seed-holders and
cost a signing operation on every write, buying nothing anyone currently needs. The design
document specifies Ed25519 under K_sig for this; the reference implements both and ships
with the Ed25519 path switched off.

THAT NON-SEED-HOLDER NOW EXISTS: a WM that arbitrates ordering has to be able to tell a real
device's write from anyone else's, or whoever knows `ward_id` could advance the counter and have
every genuine device refused thereafter. Its authorisation is at the bottom of this file, and it
covers THE BYTES ABOVE PLUS THE WM'S HEAD NONCE -- the same statement, made to a verifier holding
a different secret, and pinned to the WM's own place in history so one authorisation moves the
head at most once. The WM is therefore sent the two roots, and sees them.

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

TAG_COMMIT = b"WARD COMMIT v3"  # v3: the preimage names ROOTS again; K_mac is gone
TAG_REVERT = b"WARD REVERT v3"  # v3: as TAG_COMMIT

# The WM's own authorisation. `transition_preimage` plus the WM's HEAD NONCE -- see `wm_preimage`.
TAG_WM_HEAD = b"WARD WM COMMIT v3"  # v3: the head nonce joined the preimage
TAG_WM_INIT = b"WARD WM INIT v3"  # v3: as TAG_WM_HEAD; see `head_init_sig`
# A revert advances the WM head like any write -- forward, carrying an OLDER root -- so the WM
# could not otherwise tell one from an ordinary advance. The tag does not add replay protection
# (the head nonce does that now); it exists so a WM can apply policy to demotions -- rate-limit
# them, alert on them -- rather than having the wire decide for it. Mirrors TAG_COMMIT/TAG_REVERT
# one layer down.
TAG_WM_REVERT = b"WARD WM REVERT v3"


def transition_preimage(
    tag: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
) -> bytes:
    """The bytes a transition is authorised over -- ONE builder for both authenticators.

    Both endpoints are named, not just the destination. Binding only `to` would let a link be
    lifted out of its place in the history and replayed after a different predecessor, which is
    the whole point of a chain.

    THE ENDPOINTS ARE ROOTS. `auth_commit` (HMAC under K_auth, checked by another device) and
    `wm_sig` (Ed25519 under K_sig, checked by the WM) are built from these same bytes and differ
    in tag, key, algorithm, and one field only the WM can supply -- its head nonce, appended by
    `wm_preimage`. The same statement made to two verifiers who hold different secrets. They are
    not redundant: the verifier sets are disjoint, and neither party can check the other's
    authenticator. THE NONCE IS NOT IN HERE, because a device walking the chain holds links and
    no WM state, so folding it in would make history unverifiable. See the WM section at the
    bottom of this file.

    THE ENDPOINTS USED TO BE MAC HEADS, under a second key K_mac, so that a WM verifying a
    `wm_sig` never had to be shown a root. That indirection is gone -- see the module docstring
    for what it cost and what carries the weight instead. The consequence here is the one that
    matters for this function: the WM compare-and-swaps on `from_root` and attests `to_root`,
    and BOTH ARE INSIDE THE BYTES IT VERIFIES. Were the signature to name anything the WM does
    not itself hold, a host could pair a genuine signature with an operand of its choosing and
    strand the wallet at a head no device will accept.

    AN ABSENT ROOT IS THE EMPTY TREE and encodes as `EMPTY_ROOT`, a real 32-byte value. This
    normalisation used to happen one layer down in `root_mac`; with that layer gone it belongs
    here, and it is what keeps the preimage fixed-width when the tree is empty at either end.
    """
    from trezor.wire import DataError

    from .attest import root_or_empty

    from_root = root_or_empty(from_root)
    to_root = root_or_empty(to_root)
    if len(ward_id) != 32 or len(from_root) != 32 or len(to_root) != 32:
        raise DataError("WARD: transition operands must be 32 bytes")

    # THE TAG IS LENGTH-PREFIXED. Concatenating variable-length fields leaves the boundary
    # ambiguous -- the ambiguity `leaf.leaf_hash_of` documents -- and this family's tags have
    # differed in length before and will again, so the prefix makes a cross-domain collision
    # impossible by construction rather than by the lengths happening not to line up.
    return (
        bytes([len(tag)])
        + tag
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
    """Authorise a transition. Only a device holding the seed can produce this.

    Takes ROOTS, which is what a trie operation produces, so every caller states what it actually
    did. There is no longer a conversion step between what a caller holds and what gets signed --
    `transition_macs` was that step, and deleting it deletes the only place in the subsystem where
    a counter could be paired with the wrong root.
    """
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
    """Was this exact transition authorised by a holder of this wallet's K_auth?"""
    expected = auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, tag
    )
    # Length-independent comparison is not needed -- both sides are locally computed and
    # the attacker learns nothing from timing here -- but equality on bytes is constant
    # time in micropython anyway for equal-length inputs.
    return expected == mac


def verify_chain_step(
    k_auth: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: bytes | None,
    link: "tuple",
) -> "tuple[int, bytes | None, bool]":
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
    #
    # WHICH KIND IT WAS IS RETURNED, not swallowed. This used to be a bare `or`, which
    # accepted both and told the caller nothing -- so a device catching up across a history
    # containing demotions could not say that it had, and the tag that exists precisely to
    # carry that distinction was discarded the moment it was checked. Reporting it does not
    # make the step more or less acceptable; it stops the fact being lost.
    if verify_auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, mac
    ):
        return to_counter, to_root, False
    if verify_auth_commit(
        k_auth,
        ward_id,
        from_counter,
        from_root,
        to_counter,
        to_root,
        mac,
        TAG_REVERT,
    ):
        return to_counter, to_root, True
    raise DataError("WARD: chain link is not authorised")


def verify_chain_step_back(
    k_auth: bytes,
    ward_id: bytes,
    running_counter: int,
    running_root: "bytes | None",
    link: "tuple",
) -> "tuple[int, bytes | None, bool]":
    """Fold one link backwards off the running head, or raise. Returns its PREDECESSOR.

    The mirror of `verify_chain_step`, and deliberately a separate function rather than a flag:
    which end is pinned is the whole security content of a walk, and a caller must not be able to
    get it wrong by passing False.

    WHY THE BACKWARD DIRECTION IS THE STRONGER ONE. Folding forward, the `from` end is pinned and
    the `to` end is whatever the host supplies, so the walk's destination is the host's choice
    until a terminal check catches it. Every device hands out an `auth_commit` on `WardLeafAck`
    before it knows whether the write landed, so a host holds genuine links for transitions the
    WM never accepted -- and a forward fold will follow one onto an orphaned branch, from which
    nothing recovers: the counter cannot go back, no later chain from the real line reconnects,
    and `rollback` needs an attestation that branch never had.

    Backwards the `to` end is pinned by a state the caller has ALREADY established -- ultimately
    by the WM's attestation of the head the walk anchored at. So every state reached is an
    ancestor of a head the WM vouched for, and an orphan is refused here, on the root check,
    before its MAC is ever computed. Not a rule that has to be remembered; the shape of the walk.

    `link` is (from_counter, from_root, to_counter, to_root, auth_commit), as on the wire.
    """
    from trezor.wire import DataError

    from .attest import root_or_empty

    from_counter, from_root, to_counter, to_root, mac = link

    # THE PINNED END. `verify_chain_step` checks these two against `from`; here they are `to`,
    # and that inversion is the entire difference between the two directions.
    if to_counter != running_counter:
        raise DataError("WARD: chain link does not end at the running counter")
    if root_or_empty(to_root) != root_or_empty(running_root):
        raise DataError("WARD: chain link does not end at the running root")
    if from_counter != running_counter - 1:
        raise DataError("WARD: chain link must step the counter back by exactly one")

    # Either tag, for the reason given above `verify_chain_step`: a demotion is a real transition
    # and a history containing one must still be walkable. Reported, not swallowed.
    if verify_auth_commit(
        k_auth, ward_id, from_counter, from_root, to_counter, to_root, mac
    ):
        return from_counter, from_root, False
    if verify_auth_commit(
        k_auth,
        ward_id,
        from_counter,
        from_root,
        to_counter,
        to_root,
        mac,
        TAG_REVERT,
    ):
        return from_counter, from_root, True
    raise DataError("WARD: chain link is not authorised")


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


# --- the WM's authorisation -------------------------------------------------------------
#
# A SECOND AUTHENTICATOR, FOR A DIFFERENT VERIFIER, OVER NEARLY THE SAME BYTES. `auth_commit`
# above is checked by another DEVICE of this wallet; these are checked by the WM. Both cover
# `transition_preimage` -- the same statement, made to two verifiers holding different secrets --
# and differ in tag, key, algorithm, and ONE APPENDED FIELD: the WM's head nonce.
#
# THEY ARE NOT REDUNDANT, which is the question near-identical operands invite. The verifier sets
# are disjoint: K_auth is seed-derived, so only devices of this wallet can check an `auth_commit`,
# and the WM holds no secret of ours, so only an Ed25519 signature under K_sig is checkable by
# it. Neither can stand in for the other.
#
# What the WM one buys: a WM that arbitrates ordering can require that only a holder of this
# wallet's K_sig may advance the head. Without it, whoever knows `ward_id` could advance the
# counter and have every genuine device refused from then on -- the WM becomes a denial-of-service
# oracle. `ward_id` IS the K_sig public key, so the WM verifies with the identifier it already
# keys by; there is no enrolment step and no second value to keep in step.
#
# EVERY OPERAND THE WM ACTS ON IS INSIDE THESE BYTES, and that is load-bearing rather than tidy.
# It compare-and-swaps on `(from_counter, from_root, head_nonce)` and attests `(to_counter,
# to_root)`; all of them are signed. An earlier shape had the signature name mac heads while the
# WM stored something else, and a shape where the two diverge lets a host pair a genuine signature
# with an operand of its own choosing -- which cannot forge state, but can strand the wallet at a
# head no device will ever accept. Keep them the same set.
#
# --- THE HEAD NONCE ----------------------------------------------------------------------
#
# The WM's state is `(counter, root, head_nonce)`, and every transition it accepts ROTATES the
# nonce to a fresh unpredictable value. An authorisation must quote the nonce the WM holds at the
# moment it is presented, so ONE `wm_sig` MOVES THE HEAD AT MOST ONCE, for all time.
#
# WHY THAT IS NEEDED, given that `(from_counter, from_root)` is already in the preimage. A
# compare-and-swap on a counter-and-root pair looks like it pins a transition to a unique place in
# history, and it nearly does -- but ROOTS REPEAT. The trie is content-addressed, so a wallet that
# returns to a state it held before has a root it held before; and a REVERT deliberately carries an
# older root forward under a NEW counter. So `(counter, root)` can genuinely recur, and the moment
# it does, an old authorisation over that pair becomes live again -- a host that kept one can
# re-apply a transition the user authorised once, at a point in history where they never
# authorised it. Recovery is the operation that makes this reachable rather than theoretical: it
# brings an old root forward by construction.
#
# The nonce removes the recurrence. `(counter, root)` may repeat; `(counter, root, head_nonce)`
# may not, because the nonce advances on every accepted transition and never comes back.
#
# WHERE THE DEVICE GETS IT. From the WM, inside the attestation -- see
# `attest.attestation_preimage`, which carries the head nonce alongside the transition and signs
# both. So the device can only mint a `wm_sig` the WM will accept if it has seen a FRESH,
# WM-SIGNED statement of the current head; `round.set_head_nonce` latches it for the session. A
# host feeding a stale nonce does not gain a replay -- it gains a signature the WM refuses.
#
# WHAT IT DOES NOT BUY. It binds an authorisation to a moment in the WM's history, not to a
# moment in real time: a host may still sit on a `wm_sig` and publish it late, as long as no other
# transition has been accepted in between. And it is the WM's own freshness, so a WM that rotates
# predictably, or replays an old nonce, weakens exactly this property -- the device cannot check
# that a nonce is new, only that the WM signed it.

NO_HEAD_NONCE = b"\x00" * 32
"""The nonce a WM holds before it has accepted any transition for a wallet -- see `head_init_sig`.

A NEWLY ENROLLED HEAD CARRIES IT, and the first ordinary advance therefore quotes it; the WM
rotates to a real value when it accepts that advance, and must never rotate back. So this is a
starting state rather than a reachable one, which is what keeps `head_init_sig` from being
replayable as an advance once a wallet is moving -- the tag would stop it anyway.
"""


def wm_preimage(
    tag: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
    head_nonce: bytes,
) -> bytes:
    """`transition_preimage`, with the WM's head nonce appended.

    APPENDED RATHER THAN WOVEN IN, so the two preimages stay visibly the same statement plus one
    field -- and so `auth_commit`, which no verifier of the chain could supply a nonce for, keeps
    exactly the bytes it had. A chain walker holds links, not WM state; putting the nonce in the
    shared builder would have made history unverifiable.

    Fixed width, so the append is unambiguous without a length prefix.
    """
    from trezor.wire import DataError

    if len(head_nonce) != 32:
        raise DataError("WARD: the WM head nonce must be 32 bytes")
    return (
        transition_preimage(
            tag, ward_id, from_counter, from_root, to_counter, to_root
        )
        + head_nonce
    )


def wm_sig(
    k_sig: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    head_nonce: bytes,
    tag: bytes = TAG_WM_HEAD,
) -> bytes:
    """Authorise a head advance to the WM. Only a holder of this wallet's K_sig can produce this.

    `tag` says WHAT KIND of advance: an ordinary write (TAG_WM_HEAD) or a demotion
    (TAG_WM_REVERT). Both move the head forward by one counter, so the WM cannot tell them apart
    from the operands -- see TAG_WM_REVERT.

    `head_nonce` is the WM's current freshness token, learned from its latest attestation. It is
    what makes this authorisation single-use; see the section above.

    Not a generic signing API: the preimage is built here from typed arguments, so this can never
    be pointed at bytes a caller chose.
    """
    from trezor.crypto.curve import ed25519

    return ed25519.sign(
        k_sig,
        wm_preimage(
            tag, ward_id, from_counter, from_root, to_counter, to_root, head_nonce
        ),
    )


def verify_wm_sig(
    ward_id: bytes,
    from_counter: int,
    from_root: bytes | None,
    to_counter: int,
    to_root: bytes | None,
    head_nonce: bytes,
    signature: bytes,
    tag: bytes = TAG_WM_HEAD,
) -> bool:
    """What the WM checks. Verifies against `ward_id`, which IS the public key.

    `head_nonce` is the WM's OWN current value, never one taken off the wire -- that is the whole
    content of the check. A WM that verified against a nonce the presenter supplied would be
    verifying that the presenter can copy a number.

    A WM that accepts both kinds checks this twice, once per tag, and learns which it was from
    which call succeeded -- that being the point of having two.

    On the device only so the construction can be pinned by a test; the party that needs it is the
    WM.
    """
    from trezor.crypto.curve import ed25519

    if len(signature) != 64:
        return False
    try:
        return ed25519.verify(
            ward_id,
            signature,
            wm_preimage(
                tag, ward_id, from_counter, from_root, to_counter, to_root, head_nonce
            ),
        )
    except Exception:
        return False


def head_init_sig(
    k_sig: bytes, ward_id: bytes, counter: int, root: bytes | None
) -> bytes:
    """Authorise the FIRST head the WM ever holds for this wallet. ENROLMENT, not recovery.

    A compare-and-swap needs something to compare against, and a WM that has never seen this
    wallet has nothing. The first head therefore has to be supplied by the device and
    authenticated, or it would be a value anyone who knows `ward_id` could set.

    UNDER `NO_HEAD_NONCE`, which is the same rule stated one layer down: every other
    authorisation quotes the nonce of an existing head, and enrolment is exactly the case where
    there is no existing head to quote. The WM mints its first real nonce when it accepts this,
    and must never rotate back to the all-zero value -- otherwise these bytes would be replayable
    as an ordinary advance, which is what the distinct tag also guards.

    WHAT IT PROVES, AND WHAT IT CANNOT. It proves the head it names was a GENUINE STATE OF THIS
    WALLET -- only a holder of K_sig can mint one. It does NOT prove that head is the LATEST
    state, and no signature a single device can produce ever could: every device of the wallet
    holds an authentic one over its own head, and they disagree whenever one is behind. So a WM
    may accept this only at COUNTER 0, where there is nothing to choose between; enrolling at an
    arbitrary counter would grant whichever device reached an empty WM first the power to pin the
    head to older state. `adopt.verify_round_attestation` enforces the other half of that rule --
    only counter 0 may attest itself -- so a WM that ignored it would produce attestations no
    device accepts.

    GAP(ward): RE-SEEDING A WM THAT LOST ITS REGISTER is therefore out of scope here, and
    deliberately: it needs the WM's own persisted head restored, or a named recovery operation
    with a policy for which device's claim wins. Do not widen this to cover it.

    A SELF-TRANSITION, `(counter, root) -> (counter, root)`, under its own tag. Separate from
    `wm_sig` rather than an advance from a zero head: there is no predecessor to name, and
    inventing one would give a genuine-looking authorisation for a transition that never
    happened. The tag is what stops these bytes being replayed as an advance; `from == to` would
    also give it away, but relying on that is relying on an accident of the operands rather than
    on domain separation.
    """
    from trezor.crypto.curve import ed25519

    return ed25519.sign(
        k_sig,
        wm_preimage(
            TAG_WM_INIT, ward_id, counter, root, counter, root, NO_HEAD_NONCE
        ),
    )


def verify_head_init_sig(
    ward_id: bytes, counter: int, root: bytes | None, signature: bytes
) -> bool:
    """What the WM checks before adopting a wallet it has never seen."""
    from trezor.crypto.curve import ed25519

    if len(signature) != 64:
        return False
    try:
        return ed25519.verify(
            ward_id,
            signature,
            wm_preimage(
                TAG_WM_INIT, ward_id, counter, root, counter, root, NO_HEAD_NONCE
            ),
        )
    except Exception:
        return False
