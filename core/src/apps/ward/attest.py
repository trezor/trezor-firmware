"""WM attestation: the freshness authority's signature over a TRANSITION.

The WM (WARD Manager) is an external service that keeps the authoritative head per wallet and
signs it on demand. What it signs is the STEP that reached that head, not the head alone:

    from_counter, from_root  ->  to_counter, to_root

which is exactly the statement `cas.auth_commit` MACs. Two verifiers, two secrets, one statement
-- the shape `auth_commit` and `wm_sig` already share, now extended to the third authenticator.

WHY THE STEP AND NOT THE STATE. A bare state left the PREDECESSOR for the host to choose: it
could present any link it held whose `to` end was the attested head, and two such links can exist
at once, because roots are content-addressed and a write and a revert can land on the same root at
the same counter. Nothing was forgeable that way -- the destination was pinned either way -- but
the device credited the wrong transition in `offline_store.reconcile_pending`, so a queued change
was settled or re-offered wrongly, and the "another device discarded N changes" warning could be
raised or suppressed. Naming the step removes that choice. `rollback`'s archived proof had the
same ambiguity and loses it for the same reason.

WHAT IT DOES NOT DO. A WM colluding with a host can still name a transition off the authoritative
line; nothing an attestation says can prevent that, because the WM's whole job is to assert which
state is current. Only `verify_chain`'s walk back to a state this device already holds rules it
out.

IT SIGNS THE ROOT ITSELF. There used to be a keyed indirection here -- `root_mac` under a
seed-derived K_mac, which the WM stored and attested without being able to compute one. That
bought two things: the WM stayed blind to roots, and it was bounded to REPLAYING a state the
wallet genuinely reached rather than naming a fabricated one. Both are gone, deliberately, and
the second is the one worth being honest about: a malicious WM can now attest a root this
wallet never held.

WHAT MAKES THAT SURVIVABLE. An attestation is a claim about FRESHNESS and ORDERING, and about
nothing else. What turns it into a claim about state is DESCENT: `verify_chain` anchors on the
attested head and walks `cas.auth_commit`-authorised links BACK to the device's own head, and
no invented root has such a chain into it -- minting one link needs K_auth, which the WM does
not hold. So the WM decides WHICH of this wallet's genuine states is current; it does not get
to decide what a state is. The counter floor bounds it further, refusing anything below what
this device has already accepted.

    attestation = b"WARD ATTEST v1" || version(1B) || nonce || ward_id(32B)
                                    || from_counter(4B BE) || from_root(32B)
                                    || to_counter(4B BE)   || to_root(32B)
                                    || head_nonce(32B)     || timestamp(8B BE)

signed Ed25519 under the WM key. The nonce is minted by the device per round and must
come back inside the signature, so the host cannot stockpile signed anchors and replay
one later -- against a host-only adversary that closes eclipse entirely.

TWO NONCES, AND THEY POINT IN OPPOSITE DIRECTIONS. The ROUND nonce is the device's, minted
here and quoted back by the WM, and it proves the answer is fresh. The HEAD nonce is the WM's,
part of its state `(counter, root, head_nonce)`, rotated on every transition it accepts, and it
is quoted FORWARD by the device in the next `cas.wm_sig` -- which is what makes an authorisation
single-use even when a `(counter, root)` pair recurs. See the head-nonce section in `cas`. It is
in here rather than on the wire beside the signature because a head nonce the host could choose
would let it aim a genuine device's authorisation at a moment of its own picking.

THE TIMESTAMP IS CARRIED BUT NO LONGER CHECKED. It is still covered by the signature, so a
WM cannot alter it, and it stays in the preimage because removing it would be a version bump
for no gain. But nothing compares it any more: anti-replay is the counter's job, a malicious
WM lies about the clock freely, and an honest one whose clock regressed without its counter
regressing was never an attack. Checking it required storing a time to compare against, and
that storage bought nothing -- see `storage.ward`. A future check can be reinstated without a
wire change, which is exactly why the field stays.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_ATTEST_DOMAIN = b"WARD ATTEST v1"
# 2 when the preimage grew a timestamp; 3 when the 32-byte field stopped being a mac over the
# root and became the root; 4 when it stopped naming a state and started naming a transition;
# 5 when the WM's own head nonce joined it.
#
# The v2->v3 bump was the one that mattered most, and it is worth keeping the reason written down:
# THE LAYOUT DID NOT MOVE. Same offsets, same widths -- so nothing about the bytes would have told
# a v2 signer and a v3 verifier they disagreed about what the field meant, and a root accepted as
# a mac (or the reverse) fails open, not closed. This bump adds 36 bytes, so a stale signature
# cannot even parse; the version still moves, because relying on a length accident is how the
# next change that happens to preserve one gets missed.
_ATTEST_VERSION = 5

NONCE_LENGTH = 32

# The 32-byte stand-in for "the tree is empty", used wherever a root appears inside a
# preimage. Preimages are fixed-width, so an absent root needs SOME encoding, and it must
# be one no real root can take: this is sha256(0x03), domain-separated from the leaf
# (0x00), internal (0x01) and commit (0x02) tags.
#
# An all-zero value would also work in practice but reads as "unset field", which is the
# kind of ambiguity that eventually gets treated as one. Spelled as bytes so the module
# needs no hashing at import time; a unit test asserts it really is sha256(0x03).
EMPTY_ROOT = (
    b"\x08\x4f\xed\x08\xb9\x78\xaf\x4d\x7d\x19\x6a\x74\x46\xa8\x6b\x58"
    b"\x00\x9e\x63\x6b\x61\x1d\xb1\x62\x11\xb6\x5a\x9a\xad\xff\x29\xc5"
)


def root_or_empty(root: bytes | None) -> bytes:
    """A root in its preimage form: itself, or the empty-tree stand-in."""
    return root if root is not None else EMPTY_ROOT


# PLACEHOLDER. Production firmware rejects every WM signature until a real key is
# provisioned here, which is the correct default: a device that accepted a WM key from
# whoever offered one would be verifying freshness against an adversary's clock.
_WM_PUBKEY = b"\x00" * 32

_ZERO_PUBKEY = b"\x00" * 32
_ZERO_SIG = b"\x00" * 64

if __debug__:
    # Well-known debug key, accepted on debug builds only. Its Ed25519 seed is the ASCII
    # string b"AUTHDB QM DEBUG KEY SEED v1 ...." -- tests sign with it, and a unit test
    # asserts this constant really is that seed's public key.
    #
    # Spelled as bytes rather than decoded from hex: this firmware has no `ubinascii`.
    _WM_PUBKEY_DEBUG = (
        b"\x17\xb4\xc2\x1fkU\x93T\x05\xd5\xa4\x8e\xe3\xf2\xf2\x9f"
        b"\x42\xd7\x8c\x9ae\r\x8fhjp[!\xefb\xb0\xb6"
    )


def _verify(message: bytes, signature: bytes) -> bool:
    """Ed25519-verify under the WM key, failing closed.

    Two guards that are not paranoia:

    An all-zero signature must never verify. Against the all-zero placeholder key it is a
    degenerate acceptance -- R=0, S=0 satisfies [S]B = R + [k]A when A is the identity --
    so an unprovisioned device would accept a forged attestation carrying no signature at
    all. Both halves are refused explicitly: the zero signature, and any attempt to verify
    against the placeholder key.

    So an unprovisioned RELEASE build rejects every attestation, and WARD sync cannot
    complete. That is the intended state, and it is why the screens still warn.
    """
    from trezor.crypto.curve import ed25519

    if len(signature) != 64:
        return False
    if signature == _ZERO_SIG:
        return False
    if _WM_PUBKEY != _ZERO_PUBKEY and ed25519.verify(_WM_PUBKEY, signature, message):
        return True
    if __debug__:
        return ed25519.verify(_WM_PUBKEY_DEBUG, signature, message)
    return False


def attestation_preimage(
    ward_id: bytes,
    nonce: bytes,
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
    head_nonce: bytes,
    timestamp: int,
) -> bytes:
    """domain || version(1B) || nonce || ward_id || from(4B||32B) || to(4B||32B) || head_nonce || ts.

    Fixed widths, per `leaf.leaf_hash_of`: the roots arrive from the host, and adjacent
    variable-length fields are re-splittable if their lengths are not pinned. The WM signature
    over the whole preimage makes that unexploitable by a host, but the check belongs here rather
    than in that argument.

    AN ABSENT ROOT IS THE EMPTY TREE and encodes as `EMPTY_ROOT`, at either end. The empty tree is
    a state a wallet genuinely reaches -- at counter 0, and again whenever it is drained -- so it
    has to be attestable rather than unrepresentable.

    GENESIS IS THE SELF-TRANSITION `(0, EMPTY_ROOT) -> (0, EMPTY_ROOT)`. Counter 0 has no
    predecessor and no step produced it, so there is nothing else honest to name. It cannot be
    confused with a real transition: every one of those advances the counter by exactly one, so
    no genuine step has `from == to`. `cas.head_init_sig` uses the same shape one layer up, for
    the same reason.
    """
    from trezor.wire import DataError

    from_root = root_or_empty(from_root)
    to_root = root_or_empty(to_root)
    if (
        len(nonce) != NONCE_LENGTH
        or len(ward_id) != 32
        or len(from_root) != 32
        or len(to_root) != 32
        or len(head_nonce) != NONCE_LENGTH
    ):
        raise DataError("WARD: attestation operands have the wrong length")
    return (
        _ATTEST_DOMAIN
        + bytes([_ATTEST_VERSION])
        + nonce
        + ward_id
        + from_counter.to_bytes(4, "big")
        + from_root
        + to_counter.to_bytes(4, "big")
        + to_root
        + head_nonce
        + timestamp.to_bytes(8, "big")
    )


# THE NONCE IS THE WHOLE ANTI-ECLIPSE ARGUMENT. The device mints it before the host talks to the
# WM, so the WM must sign a value nobody could know in advance and a host cannot keep a drawer of
# previously-signed anchors and serve whichever suits it. `round.clear` then zeroes the slot, so
# the device retains no past nonces and could not tell one it minted last week from arbitrary
# bytes -- which is why there is exactly ONE verification entry point here.
#
# THERE USED TO BE TWO. `verify_archived_attestation` took the nonce as DATA, answering "was this
# EVER a head" rather than "is this the head NOW", and it was admitted for two callers: a chain
# walk anchored on an archived head, and `rollback` proving its target was once authoritative.
# Both are gone. The anchor raised the persisted counter with no freshness and no consent, which
# defeated a user-confirmed recovery; and rollback's requirement asked for proof of headship that
# a host missing rows cannot have, making the escape unavailable in the case it exists for.
#
# So nothing verifies an attestation outside an open round any more, and there is no second entry
# point to reach for. If one is ever wanted again, the rule it broke both times is where to
# start: a path that takes the nonce as DATA must never decide what is CURRENT.
# ---------------------------------------------------------------------------


def verify_attestation(
    ward_id: bytes,
    nonce: bytes,
    from_counter: int,
    from_root: "bytes | None",
    to_counter: int,
    to_root: "bytes | None",
    head_nonce: bytes,
    timestamp: int,
    signature: bytes,
) -> bool:
    """Is this a WM attestation of this transition for this wallet, this round?

    The nonce must be the open round's -- see the note above. Callers get it from
    `round.get()`, never from a message.
    """
    return _verify(
        attestation_preimage(
            ward_id,
            nonce,
            from_counter,
            from_root,
            to_counter,
            to_root,
            head_nonce,
            timestamp,
        ),
        signature,
    )
