"""WM attestation: the freshness authority's signature, and the root MAC it signs.

The WM (WARD Manager) is an external service that keeps the authoritative
`(counter, mac)` per wallet. It is NOT trusted with contents:

    mac = HMAC-SHA256(K_mac, b"WARD ROOT v1" || ward_id || counter(4B BE) || root)

K_mac is seed-derived, so only the device family can compute a mac. The WM signs one
without being able to produce one, which bounds a malicious WM to REPLAYING a
`(counter, mac)` pair this wallet genuinely reached -- it cannot fabricate a state. The
counter floor then bounds which replays are acceptable. That pair of properties is the
whole freshness story, and it is why the mac exists rather than the WM signing the root
directly: a WM that signed roots would learn the entire history of every wallet it serves.

    attestation = b"WARD ATTEST v1" || version(1B) || nonce || ward_id(32B)
                                    || counter(4B BE) || mac(32B) || timestamp(8B BE)

signed Ed25519 under the WM key. The nonce is minted by the device per round and must
come back inside the signature, so the host cannot stockpile signed anchors and replay
one later -- against a host-only adversary that closes eclipse entirely.

THE TIMESTAMP constrains honest-but-broken operators, not hostile ones -- a malicious WM
simply lies about the time. What it catches is an operator who restored from a backup or
whose clock jumped, which typically regresses the counter and the clock together, and it
forces a forking WM to keep time monotone per device on every branch. The device has no
clock and needs none: this is a stored-value comparison, the same cost as the counter.

It ships WITH its recovery path, never before. A backward jump past EPSILON locks the
wallet out, and monotonicity that protects against replay becomes a denial of service
against the owner; WardRecoverCounter is the way back. Shipping the check alone would have
been shipping a brick with no key.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_ATTEST_DOMAIN = b"WARD ATTEST v1"
# Bumped when the preimage layout changed to carry a timestamp. The version byte exists
# for exactly this: changing the layout while leaving the version at 1 would let a v1
# signer and a v2 verifier disagree about what was signed, silently.
_ATTEST_VERSION = 2
_ROOT_MAC_DOMAIN = b"WARD ROOT v1"

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


# Allowance for clock jitter and NTP correction, in seconds. Too generous weakens the
# check; too tight turns ordinary time-sync hiccups into support tickets. A real tuning
# decision rather than a free win.
EPSILON_SECONDS = 300


def attestation_preimage(
    ward_id: bytes, nonce: bytes, counter: int, mac: bytes, timestamp: int
) -> bytes:
    """domain || version(1B) || nonce || ward_id || counter(4B BE) || mac || ts(8B BE)."""
    return (
        _ATTEST_DOMAIN
        + bytes([_ATTEST_VERSION])
        + nonce
        + ward_id
        + counter.to_bytes(4, "big")
        + mac
        + timestamp.to_bytes(8, "big")
    )


def verify_attestation(
    ward_id: bytes,
    nonce: bytes,
    counter: int,
    mac: bytes,
    timestamp: int,
    signature: bytes,
) -> bool:
    """Is this a WM attestation of (counter, mac, timestamp) for this wallet, this round?"""
    return _verify(
        attestation_preimage(ward_id, nonce, counter, mac, timestamp), signature
    )


def root_mac(k_mac: bytes, ward_id: bytes, counter: int, root: bytes | None) -> bytes:
    """mac = HMAC-SHA256(K_mac, domain || ward_id || counter(4B BE) || root).

    An ABSENT root -- the empty tree -- macs the EMPTY_ROOT stand-in rather than being
    skipped, so the empty tree still has a distinct, attestable mac at every counter.
    Leaving it unbound would let a WM attest "empty" for any counter it liked.

    The counter is inside the mac, and that is load-bearing rather than tidy: roots are
    content-addressed and therefore REPEAT whenever contents repeat -- change a label and
    change it back and the root returns. Any check that identifies a state by its root
    alone can be fed an old signature naming today's root. Binding the counter is what
    makes a mac name one moment instead of one shape, and the same rule applies to every
    other comparison in this subsystem that starts from a root.
    """
    from trezor.crypto import hmac

    return hmac(
        hmac.SHA256,
        k_mac,
        _ROOT_MAC_DOMAIN + ward_id + counter.to_bytes(4, "big") + root_or_empty(root),
    ).digest()
