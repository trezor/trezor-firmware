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
                                    || counter(4B BE) || mac(32B)

signed Ed25519 under the WM key. The nonce is minted by the device per round and must
come back inside the signature, so the host cannot stockpile signed anchors and replay
one later -- against a host-only adversary that closes eclipse entirely.

NO TIMESTAMP, deliberately. The design calls for `t_anchor >= t_last - epsilon` as a
second monotonicity check, and it is omitted here because its failure mode is a
PERMANENTLY LOCKED OUT wallet: a backward clock jump past epsilon bricks the device until
a recovery path exists that can accept a lower timestamp, and that path is by
construction a user-confirmable rollback to arbitrary past state -- the strongest
social-engineering target in the protocol. Shipping the check before its recovery is
shipping a brick with no key. It also buys less than it looks: a malicious WM simply lies
about the time, so it constrains honest-but-broken and partitioned operators only.

FIXME(ward): add the timestamp check together with the counter-reset recovery path, not
before it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_ATTEST_DOMAIN = b"WARD ATTEST v1"
_ATTEST_VERSION = 1
_ROOT_MAC_DOMAIN = b"WARD ROOT v1"

NONCE_LENGTH = 32

# PLACEHOLDER. Production firmware rejects every WM signature until a real key is
# provisioned here, which is the correct default: a device that accepted a WM key from
# whoever offered one would be verifying freshness against an adversary's clock.
_WM_PUBKEY = b"\x00" * 32

_ZERO_PUBKEY = b"\x00" * 32
_ZERO_SIG = b"\x00" * 64

if __debug__:
    from ubinascii import unhexlify

    # Well-known debug key, accepted on debug builds only. Its Ed25519 seed is the ASCII
    # string b"AUTHDB QM DEBUG KEY SEED v1 ...." -- tests sign with it.
    _WM_PUBKEY_DEBUG = unhexlify(
        b"17b4c21f6b55935405d5a48ee3f2f29f42d78c9a650d8f686a705b21ef62b0b6"
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
    ward_id: bytes, nonce: bytes, counter: int, mac: bytes
) -> bytes:
    """b"WARD ATTEST v1" || version(1B) || nonce || ward_id || counter(4B BE) || mac."""
    return (
        _ATTEST_DOMAIN
        + bytes([_ATTEST_VERSION])
        + nonce
        + ward_id
        + counter.to_bytes(4, "big")
        + mac
    )


def verify_attestation(
    ward_id: bytes, nonce: bytes, counter: int, mac: bytes, signature: bytes
) -> bool:
    """Is this a WM attestation of (counter, mac) for this wallet, this round?"""
    return _verify(attestation_preimage(ward_id, nonce, counter, mac), signature)


def root_mac(k_mac: bytes, ward_id: bytes, counter: int, root: bytes | None) -> bytes:
    """mac = HMAC-SHA256(K_mac, domain || ward_id || counter(4B BE) || root).

    An ABSENT root -- the empty tree -- macs the all-zero root rather than being skipped,
    so the empty tree still has a distinct, attestable mac at every counter. Leaving it
    unbound would let a WM attest "empty" for any counter it liked.

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
        _ROOT_MAC_DOMAIN
        + ward_id
        + counter.to_bytes(4, "big")
        + (root if root is not None else bytes(32)),
    ).digest()
