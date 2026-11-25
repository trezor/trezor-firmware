"""The WARD leaf: two independently sealed parts, and the digest the trie commits to
(docs/ward/ward_leaf_encryption.md).

    leaf_identity   = device_id(1B) || len8(app_id) || app_id || identifier
    leaf_content    = len8(entry_type) || entry_type || C_leaf(4B BE) || value
    seal(K, d, pt)  = 0x01 || nonce(12B) || tag(16B) || AES-256-GCM(K, nonce, aad=d, pt)
    sealed_content  = seal(K_data,  0x02, leaf_content)
    sealed_identity = seal(K_ident, 0x04, leaf_identity)
    value_digest    = sha256(0x03 || sealed_content)
    leaf            = sha256(0x00 || entry_key || value_digest)

Only `sealed_content` is in the trie. `sealed_identity` is stored beside the leaf: the path
already authenticates the identity, so the trie does not commit to it. An EMPTY
sealed_content is a delete; a sealed value, even b"", is never empty.

The parts are sealed under device-only keys, so the host can neither read nor forge them.
Sealing gives no freshness -- only a proof against an attested root does. The digest is
keyless, so a host with no keys can still serve proofs. Vectors in
`core/tests/test_apps.ward.py`.
"""

from micropython import const

SCHEME_AESGCM = const(0x01)  # the first byte of a sealed part; the only scheme
DOMAIN_CONTENT = const(0x02)  # AAD of sealed_content
DOMAIN_IDENTITY = const(0x04)  # AAD of sealed_identity; 0x03 is the trie value domain

_NONCE_LEN = const(12)
_TAG_LEN = const(16)
_SEALED_MIN = const(1 + _NONCE_LEN + _TAG_LEN)

# The delete marker: an empty sealed_content.
EMPTY = b""

# C_leaf: the counter a leaf was committed at (stamped by the committing device).
C_LEAF_UNUSED = 0


def _as_bytes(x: "str | bytes | None") -> bytes:
    if x is None:
        return b""
    if isinstance(x, str):
        return x.encode()
    return bytes(x)


def is_delete(sealed_content: "bytes | None") -> bool:
    return not sealed_content


# --- the trie commitment: keyless, so a host can compute it ---


def value_digest(sealed_content: bytes) -> bytes:
    """sha256(0x03 || sealed_content): the trie's value domain, over sealed bytes only."""
    from trezor.crypto.hashlib import sha256

    return sha256(b"\x03" + sealed_content).digest()


def leaf_hash_of(entry_key: bytes, digest: bytes) -> bytes:
    """leaf = sha256(0x00 || entry_key || value_digest), both operands exactly 32 bytes.

    THE WIDTHS ARE THE SECURITY: without them (K, D) and (K || D[0], D[1:]) hash alike, which
    let a host pass a membership proof off as non-membership.
    """
    from trezor.crypto.hashlib import sha256
    from trezor.wire import DataError

    if len(entry_key) != 32 or len(digest) != 32:
        raise DataError("WARD: leaf operands must be 32 bytes")
    return sha256(b"\x00" + entry_key + digest).digest()


def leaf_hash(entry_key: bytes, sealed_content: bytes) -> bytes:
    return leaf_hash_of(entry_key, value_digest(sealed_content))


# --- sealing (AES-256-GCM, 12-byte random nonce, 1-byte domain as AAD) ---


def seal(key: bytes, domain: int, pt: bytes, nonce: "bytes | None" = None) -> bytes:
    """0x01 || nonce || tag || ct. The nonce is fresh-random per seal -- never derived from the
    leaf: in a lost race two devices seal the same entry at the same counter, and the host keeps
    both seals. `nonce` is for known-answer tests ONLY."""
    from trezor.crypto import aesgcm_encrypt, random

    nonce = nonce or random.bytes(_NONCE_LEN)
    cipher = aesgcm_encrypt(key, nonce)
    cipher.auth(bytes([domain]))
    ct = cipher.encrypt(pt)
    return bytes([SCHEME_AESGCM]) + nonce + cipher.finish() + ct


def open_sealed(key: bytes, domain: int, sealed: bytes) -> bytes:
    """A sealed part's plaintext. An unknown scheme, a short part or a tag mismatch raises."""
    from trezor.crypto import AuthenticationError, aesgcm_decrypt
    from trezor.wire import DataError

    check_sealed(sealed)
    nonce = sealed[1 : 1 + _NONCE_LEN]
    tag = sealed[1 + _NONCE_LEN : _SEALED_MIN]
    cipher = aesgcm_decrypt(key, nonce)
    cipher.auth(bytes([domain]))
    pt = cipher.decrypt(sealed[_SEALED_MIN:])
    try:
        cipher.finish(tag)
    except AuthenticationError:
        raise DataError("WARD: leaf tag mismatch")
    return pt


def check_sealed(sealed: bytes) -> None:
    """Refuse a part that is not a well-formed sealing, before it is hashed or opened."""
    from trezor.wire import DataError

    if len(sealed) < _SEALED_MIN or sealed[0] != SCHEME_AESGCM:
        raise DataError("WARD: malformed sealed leaf part")


# --- leaf_identity: the whole entry_key preimage ---


def pack_identity(identifier: bytes, app_id: "str | bytes", device_id: int = 0) -> bytes:
    """device_id(1B) || len8(app_id) || app_id || identifier. device_id 0 means an entry shared
    by all devices, and 1 to 255 is one device's slot. The identifier runs to the end. The single
    source of canonicalization -- both entry_key and sealed_identity go through it."""
    from trezor.wire import DataError

    app = _as_bytes(app_id)
    if len(app) > 255 or not 0 <= device_id <= 255:
        raise DataError("WARD identity exceeds canonical encoding bounds")
    return bytes([device_id, len(app)]) + app + identifier


def unpack_identity(pt: bytes) -> "tuple[bytes, bytes, int]":
    """Return (identifier, app_id, device_id). A buffer too short for its app_id raises
    DataError; the identifier is whatever follows."""
    from trezor.wire import DataError

    if len(pt) < 2 or len(pt) < 2 + pt[1]:
        raise DataError("WARD: malformed leaf identity")
    device_id = pt[0]
    app_len = pt[1]
    return bytes(pt[2 + app_len :]), bytes(pt[2 : 2 + app_len]), device_id


def seal_identity(
    k_ident: bytes,
    identifier: bytes,
    app_id: "str | bytes",
    device_id: int = 0,
    nonce: "bytes | None" = None,
) -> bytes:
    return seal(
        k_ident, DOMAIN_IDENTITY, pack_identity(identifier, app_id, device_id), nonce
    )


def open_identity(k_ident: bytes, sealed_identity: bytes) -> "tuple[bytes, bytes, int]":
    """Return (identifier, app_id, device_id) from a sealed_identity."""
    return unpack_identity(open_sealed(k_ident, DOMAIN_IDENTITY, sealed_identity))


# --- leaf_content: entry_type, C_leaf and the value ---


def pack_content(entry_type: str, c_leaf: int, value: bytes) -> bytes:
    """len8(entry_type) || entry_type || C_leaf(4B BE) || value. The value runs to the end;
    there is no padding."""
    from trezor.wire import DataError

    et = entry_type.encode()
    if len(et) > 255:
        raise DataError("WARD entry_type too long")
    return bytes([len(et)]) + et + c_leaf.to_bytes(4, "big") + value


def unpack_content(pt: bytes) -> "tuple[str, int, bytes]":
    """Return (entry_type, c_leaf, value). A short buffer raises DataError."""
    from trezor.wire import DataError

    if len(pt) < 1 or len(pt) < 1 + pt[0] + 4:
        raise DataError("WARD: malformed leaf content")
    off = 1 + pt[0]
    entry_type = bytes(pt[1:off]).decode()
    c_leaf = int.from_bytes(pt[off : off + 4], "big")
    return entry_type, c_leaf, bytes(pt[off + 4 :])


def seal_content(
    k_data: bytes,
    entry_type: str,
    c_leaf: int,
    value: bytes,
    nonce: "bytes | None" = None,
) -> bytes:
    """Seal a present value, including b''. Deletion is EMPTY, chosen by the caller."""
    return seal(k_data, DOMAIN_CONTENT, pack_content(entry_type, c_leaf, value), nonce)


def open_content(k_data: bytes, sealed_content: bytes) -> "tuple[str, int, bytes]":
    """Return (entry_type, c_leaf, value) from a sealed_content."""
    return unpack_content(open_sealed(k_data, DOMAIN_CONTENT, sealed_content))
