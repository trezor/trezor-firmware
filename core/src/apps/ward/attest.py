"""WM attestation: the WM's Ed25519 signature over the TRANSITION that reached its head.

    b"WARD ATTEST v1" || version(1B) || nonce || ward_id(32B)
        || from_counter(4B BE) || from_root(32B) || from_head_nonce(32B)
        || to_counter(4B BE)   || to_root(32B)   || to_head_nonce(32B)
        || timestamp(8B BE)

It attests freshness and ordering only. The WM signs roots in the clear and could name one the
wallet never held; descent (`verify_chain` walking K_auth links back to this device's head) is
what turns an attestation into a statement about state, and the counter floor bounds it.

The round nonce is the device's, minted per round, so signed anchors cannot be stockpiled and
replayed. The head nonces are the WM's: `from_head_nonce` is the one consumed by this step, so
the attestation names one OCCURRENCE of a transition even when `(counter, root)` pairs recur.
The timestamp is signed but not checked.
"""

_ATTEST_DOMAIN = b"WARD ATTEST v1"
# Bumped on every change of meaning, even when the layout would not reveal it.
_ATTEST_VERSION = 6

NONCE_LENGTH = 32

# The empty-tree stand-in inside fixed-width preimages: sha256(0x02), domain-separated from the
# leaf (0x00), internal (0x01) and value (0x03) tags. A unit test asserts the value.
EMPTY_ROOT = (
    b"\xdb\xc1\xb4\xc9\x00\xff\xe4\x8d\x57\x5b\x5d\xa5\xc6\x38\x04\x01"
    b"\x25\xf6\x5d\xb0\xfe\x3e\x24\x49\x4b\x76\xea\x98\x64\x57\xd9\x86"
)


def root_or_empty(root: bytes | None) -> bytes:
    """A root in its preimage form: itself, or the empty-tree stand-in."""
    return root if root is not None else EMPTY_ROOT


def same_root(a: "bytes | None", b: "bytes | None") -> bool:
    """Equal as trees: `None` and EMPTY_ROOT both mean the empty tree."""
    return root_or_empty(a) == root_or_empty(b)


def app_root(root: "bytes | None") -> "bytes | None":
    """A root in app form: the empty tree as None."""
    return None if root == EMPTY_ROOT else root


# PLACEHOLDER: until a real key is provisioned, release builds reject every attestation.
_WM_PUBKEY = b"\x00" * 32

_ZERO_PUBKEY = b"\x00" * 32
_ZERO_SIG = b"\x00" * 64

if __debug__:
    # Debug-only key; its seed is b"AUTHDB QM DEBUG KEY SEED v1 ....", asserted by a unit test.
    _WM_PUBKEY_DEBUG = (
        b"\x17\xb4\xc2\x1fkU\x93T\x05\xd5\xa4\x8e\xe3\xf2\xf2\x9f"
        b"\x42\xd7\x8c\x9ae\r\x8fhjp[!\xefb\xb0\xb6"
    )


def _verify(message: bytes, signature: bytes) -> bool:
    """Ed25519-verify under the WM key, failing closed.

    The all-zero signature and the all-zero placeholder key are both refused: against the
    identity point, R=0, S=0 verifies any message.
    """
    from trezor.crypto.curve import ed25519

    if len(signature) != 64 or signature == _ZERO_SIG:
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
    from_head_nonce: bytes,
    to_counter: int,
    to_root: "bytes | None",
    to_head_nonce: bytes,
    timestamp: int,
) -> bytes:
    """The fixed-width signed preimage; an absent root encodes as `EMPTY_ROOT`.

    Genesis is the self-transition `(0, EMPTY_ROOT) -> (0, EMPTY_ROOT)` with one head nonce at
    both ends; no genuine step has `from == to` or equal head nonces.
    """
    from trezor.wire import DataError

    from .codec import u32

    from_root = root_or_empty(from_root)
    to_root = root_or_empty(to_root)
    if (
        len(nonce) != NONCE_LENGTH
        or len(ward_id) != 32
        or len(from_root) != 32
        or len(to_root) != 32
        or len(from_head_nonce) != NONCE_LENGTH
        or len(to_head_nonce) != NONCE_LENGTH
    ):
        raise DataError("WARD: attestation operands have the wrong length")
    return (
        _ATTEST_DOMAIN
        + bytes([_ATTEST_VERSION])
        + nonce
        + ward_id
        + u32(from_counter)
        + from_root
        + from_head_nonce
        + u32(to_counter)
        + to_root
        + to_head_nonce
        + timestamp.to_bytes(8, "big")
    )


def verify_attestation(
    ward_id: bytes,
    nonce: bytes,
    from_counter: int,
    from_root: "bytes | None",
    from_head_nonce: bytes,
    to_counter: int,
    to_root: "bytes | None",
    to_head_nonce: bytes,
    timestamp: int,
    signature: bytes,
) -> bool:
    """Is this a WM attestation of this transition for this wallet, this round?

    The ONLY verification entry point. `nonce` must be the open round's (`round.get()`), never
    a message field: a path taking the nonce as data must never decide what is current. The one
    caller that does is `catch_up`, which decides only what WAS a head, for one session, and
    persists nothing.
    """
    return _verify(
        attestation_preimage(
            ward_id, nonce, from_counter, from_root, from_head_nonce,
            to_counter, to_root, to_head_nonce, timestamp,
        ),
        signature,
    )
