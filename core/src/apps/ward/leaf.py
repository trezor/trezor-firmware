"""The WARD leaf: two independently sealed parts, and the commitment over them.

    part(p)   = encoding(1B) || len8(nonce) || nonce || len8(tag) || tag
                             || len32(body) || body
    commit    = sha256(0x02 || len8(key_type) || key_type
                            || len32(id_part) || id_part || len32(val_part) || val_part)
    leaf      = sha256(0x00 || entry_key || commit)

    LeafIdentity   identifier, app_id, device_id    sealed under K_ident(key_type)
    LeafContent    C_leaf, value                    sealed under K_data(key_type)

`key_type` is always clear -- it selects the two keys that seal the parts.

Each part is sealed with ChaCha20-Poly1305 under a device-only key, so the host holds
two opaque blobs it can neither read nor forge. The AAD binds a part to its path, its
part-domain and its key_type:

    aad = domain(1B) || entry_key || key_type

so a part cannot be replayed as the other part, nor moved to another path: both fail
the tag check.

What sealing does NOT buy: freshness or existence. The host can still return an older
sealed leaf for the same path, or claim it holds none. Only a proof against an
authenticated root detects those -- which is `trie`'s job, not this module's.

THE COMMITMENT IS KEYLESS, and that is the point of separating it from the sealing: a
host with no keys at all can still recompute `commit` from the two encoded parts and
therefore serve proofs it cannot read.

Split out of `service`. Takes its keys as ARGUMENTS and imports nothing else from the
package, so it can be pinned by known-answer vectors with no wallet in play.
"""

from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _sha256d(data: bytes) -> bytes:
    # Defined here rather than imported: it is two lines, and taking it from another
    # WARD module would create a dependency edge for no reason. Same in `trie`.
    from trezor.crypto.hashlib import sha256

    return sha256(data).digest()


# Per-part leaf mode (dev switch). False = encrypted (production); True = plaintext
# (host-inspectable; debug/emulator builds only). The two parts are INDEPENDENT: a
# build may seal the identity and leave the content readable, or vice versa. The wire
# is a self-describing oneof either way (LeafIdentity / LeafContent), and each part's
# encoding byte is inside the commit, so the modes can never collide.
# FIXME(ward, INACTIVE): both flags are False in every shipped build, so the plaintext
# branches below are unreachable. They are a deliberate dev/emulator switch, not dead
# code -- the wire is self-describing per part either way.
WARD_PLAINTEXT_IDENTITY = False
WARD_PLAINTEXT_CONTENT = False

# The plaintext codecs are compiled in only under __debug__, so a release build
# cannot produce or read a plaintext part -- fail loudly at import, not at first write.
if (WARD_PLAINTEXT_IDENTITY or WARD_PLAINTEXT_CONTENT) and not __debug__:
    raise RuntimeError("WARD plaintext leaf parts require a __debug__ build")

# part encodings (the byte that goes into the commit)
ENC_ENCRYPTED = const(0)
ENC_PLAINTEXT = const(1)

# An absent/empty part: (encoding, nonce, tag, body). An empty CONTENT body is a
# delete; the identity part survives it, so a tombstone stays self-describing.
EMPTY_PART = (ENC_PLAINTEXT, b"", b"", b"")


def part_is_empty(part) -> bool:
    return part is None or len(part[3]) == 0


def _part_bytes(part) -> bytes:
    """encoding(1B) || len8(nonce) || nonce || len8(tag) || tag || len32(body) || body"""
    encoding, nonce, tag, body = part if part is not None else EMPTY_PART
    return (
        bytes([encoding])
        + bytes([len(nonce)])
        + nonce
        + bytes([len(tag)])
        + tag
        + len(body).to_bytes(4, "big")
        + body
    )


def commit_of(key_type: str, id_part, val_part) -> bytes:
    """Keyless leaf commitment (§2.2) over both parts and the clear key_type. A host
    with no keys can still recompute it whatever each part's encoding is; an empty
    val_part body is a delete."""
    kt = key_type.encode()
    id_bytes = _part_bytes(id_part)
    val_bytes = _part_bytes(val_part)
    return _sha256d(
        b"\x02"
        + bytes([len(kt)])
        + kt
        + len(id_bytes).to_bytes(4, "big")
        + id_bytes
        + len(val_bytes).to_bytes(4, "big")
        + val_bytes
    )


def leaf_hash_of(entry_key_: bytes, commit: bytes) -> bytes:
    """Leaf: sha256(0x00 || entry_key || commit) (§2.2). Takes the commitment
    directly, so a verifier can rebuild a witness leaf from (entry_key, commit).

    THE LENGTHS ARE THE SECURITY. The preimage concatenates two byte strings with
    nothing marking the boundary, so without a fixed width the split is ambiguous:
    (K, C) and (K || C[0], C[1:]) produce IDENTICAL hashes, with no attack on
    SHA-256 involved.

    That was a live proof-soundness break, not a theoretical one. A non-membership
    witness is host-supplied, and the only checks on it were "differs from the
    target" and "agrees at every branch bit". A 33-byte witness key K || C[0]
    differs from K, routes identically (routing reads bits 0..255, i.e. the first
    32 bytes), and hashes to the target's own leaf -- so a host could take the
    target's genuine MEMBERSHIP proof and have it accepted as proof of ABSENCE,
    hiding any present entry on every read.

    Enforced HERE rather than at each call site so no future caller can reintroduce
    it by forgetting. Every firmware caller already passes 32-byte operands
    (`entry_key` is an HMAC, `commit_of` a SHA-256), so this only ever fires on
    something the host made up."""
    from trezor.wire import DataError

    if len(entry_key_) != 32 or len(commit) != 32:
        raise DataError("WARD: leaf operands must be 32 bytes")
    return _sha256d(b"\x00" + entry_key_ + commit)


def leaf_hash(entry_key_: bytes, key_type: str, id_part, val_part) -> bytes:
    """Leaf hash from the two parts: leaf_hash_of(entry_key, commit_of(...))."""
    return leaf_hash_of(entry_key_, commit_of(key_type, id_part, val_part))


# --- AEAD plumbing (ChaCha20-Poly1305 RFC-7539, 12-byte nonce, §2.1) ---

_AEAD_BUCKETS = (64, 256, 1024, 4096)

_AAD_IDENTITY = b"\x03"
_AAD_CONTENT = b"\x02"


def _aead_aad(domain: bytes, entry_key_: bytes, key_type: str) -> bytes:
    """Binds a part to its leaf, its key_type and its part domain, so a part can
    never be consumed as the other part or moved to another path."""
    return domain + entry_key_ + key_type.encode()


def _pad_bucket(pt: bytes) -> bytes:
    for b in _AEAD_BUCKETS:
        if len(pt) <= b:
            return pt + b"\x00" * (b - len(pt))
    rem = (-len(pt)) % _AEAD_BUCKETS[-1]
    return pt + b"\x00" * rem


def _seal(key: bytes, domain: bytes, entry_key_: bytes, key_type: str, pt: bytes):
    """Return an encrypted part (ENC_ENCRYPTED, nonce, tag, ct). The nonce is
    fresh-random per part per write -- never derived (§4.5: rollback can recur
    (entry_key, C_leaf) pairs)."""
    from trezor.crypto import chacha20poly1305_encrypt, random

    nonce = random.bytes(12)
    cipher = chacha20poly1305_encrypt(key, nonce)
    cipher.auth(_aead_aad(domain, entry_key_, key_type))
    ct = cipher.encrypt(_pad_bucket(pt))
    return (ENC_ENCRYPTED, nonce, cipher.finish(), ct)


def _open(key: bytes, domain: bytes, entry_key_: bytes, key_type: str, part) -> bytes:
    """Return a part's plaintext. Raises on tag mismatch (hard abort, §3.1)."""
    from trezor.crypto import AuthenticationError, chacha20poly1305_decrypt

    encoding, nonce, tag, body = part
    if encoding == ENC_PLAINTEXT:
        return body
    cipher = chacha20poly1305_decrypt(key, nonce)
    cipher.auth(_aead_aad(domain, entry_key_, key_type))
    pt = cipher.decrypt(body)
    try:
        cipher.finish(tag)
    except AuthenticationError:
        raise ValueError("WARD leaf AEAD tag mismatch")
    return pt


# --- LeafIdentity part: the whole entry_key preimage ---


def pack_identity(identifier: bytes, app_id, device_id: int = 0) -> bytes:
    """len16(identifier) || identifier || len8(app_id) || app_id || device_id(1B).
    The single source of canonicalization -- both the commit and the AEAD go
    through it."""
    if app_id is None:
        app_id = b""
    elif isinstance(app_id, str):
        app_id = app_id.encode()
    return (
        len(identifier).to_bytes(2, "big")
        + identifier
        + bytes([len(app_id)])
        + app_id
        + bytes([device_id & 0xFF])
    )


def unpack_identity(pt: bytes) -> tuple:
    """Return (identifier, app_id, device_id). Tolerates bucket padding past the end."""
    id_len = int.from_bytes(pt[0:2], "big")
    off = 2 + id_len
    identifier = pt[2:off]
    aid_len = pt[off]
    off += 1
    app_id = pt[off : off + aid_len]
    off += aid_len
    return identifier, app_id, pt[off]


def encode_identity(
    k_ident: bytes, entry_key_: bytes, key_type: str, identifier: bytes, app_id,
    device_id: int = 0,
):
    """Build the LeafIdentity part for this build's mode."""
    pt = pack_identity(identifier, app_id, device_id)
    if WARD_PLAINTEXT_IDENTITY:
        return (ENC_PLAINTEXT, b"", b"", pt)
    return _seal(k_ident, _AAD_IDENTITY, entry_key_, key_type, pt)


# FIXME(ward, PUSH-ONLY): no on-device caller. The identity part is written on every
# write but never read back here, so firmware does NOT verify that a leaf's
# (identifier, app_id, device_id) matches the entry_key it derived -- the identity
# contributes only its bytes to commit_of. It is host-consumed via exported K_ident.
def decode_identity(k_ident: bytes, entry_key_: bytes, key_type: str, part) -> tuple:
    """Return (identifier, app_id, device_id) from a LeafIdentity part."""
    return unpack_identity(_open(k_ident, _AAD_IDENTITY, entry_key_, key_type, part))


# --- LeafContent part: C_leaf + value ---


def pack_content(c_leaf: int, value: bytes) -> bytes:
    """C_leaf(4B BE) || len32(value) || value. The identifier used to live here; it
    is in the identity part now."""
    return c_leaf.to_bytes(4, "big") + len(value).to_bytes(4, "big") + value


def unpack_content(pt: bytes) -> tuple:
    """Return (c_leaf, value). Tolerates bucket padding past the end."""
    c_leaf = int.from_bytes(pt[0:4], "big")
    val_len = int.from_bytes(pt[4:8], "big")
    return c_leaf, pt[8 : 8 + val_len]


def encode_content(k_data: bytes, entry_key_: bytes, key_type: str, c_leaf: int, value: bytes):
    """Build the LeafContent part for this build's mode. An empty value is a delete."""
    if len(value) == 0:
        return EMPTY_PART
    pt = pack_content(c_leaf, value)
    if WARD_PLAINTEXT_CONTENT:
        return (ENC_PLAINTEXT, b"", b"", pt)
    return _seal(k_data, _AAD_CONTENT, entry_key_, key_type, pt)


def decode_content(k_data: bytes, entry_key_: bytes, key_type: str, part) -> tuple:
    """Return (c_leaf, value) from a LeafContent part; (0, b"") for a delete."""
    if part_is_empty(part):
        return 0, b""
    return unpack_content(_open(k_data, _AAD_CONTENT, entry_key_, key_type, part))
