"""The WARD leaf: two independently sealed parts, and their wire codec.

    part(p)       = encoding(1B) || len8(nonce) || nonce || len8(tag) || tag
                                 || len32(body) || body
    pack_identity = len16(identifier) || identifier || len8(app_id) || app_id
                                      || device_id(1B)
    pack_content  = C_leaf(4B BE) || len32(value) || value
    aad           = domain(1B) || entry_key || key_type

Parts are sealed with ChaCha20-Poly1305 under K_ident(key_type) / K_data(key_type), so the
host can neither read nor forge them; the AAD stops a part being swapped or moved. Sealing
gives no freshness -- only a proof against an attested root does. Byte-identical to the
reference; vectors in `core/tests/test_apps.ward.py`.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    # (encoding, nonce, tag, body)
    Part = tuple[int, bytes, bytes, bytes]

ENC_ENCRYPTED = 0
ENC_PLAINTEXT = 1

# An empty part means DELETED; an entry with an empty value still has a non-empty body.
EMPTY_PART: "Part" = (ENC_PLAINTEXT, b"", b"", b"")

# Per-part dev switches; False (sealed) ships. Debug builds only.
WARD_PLAINTEXT_IDENTITY = False
WARD_PLAINTEXT_CONTENT = False

if (WARD_PLAINTEXT_IDENTITY or WARD_PLAINTEXT_CONTENT) and not __debug__:
    raise RuntimeError("WARD plaintext leaf parts require a __debug__ build")

# --- AEAD (ChaCha20-Poly1305, RFC-7539, 12-byte nonce) ---

# Ciphertext is padded to a bucket so its length leaks only a coarse band.
_AEAD_BUCKETS = (64, 256, 1024, 4096)

# Part-domain separation inside the AAD.
_AAD_IDENTITY = b"\x03"
_AAD_CONTENT = b"\x02"


def _pad_bucket(pt: bytes) -> bytes:
    for b in _AEAD_BUCKETS:
        if len(pt) <= b:
            return pt + b"\x00" * (b - len(pt))
    return pt + b"\x00" * ((-len(pt)) % _AEAD_BUCKETS[-1])


def _clear(body: bytes) -> "Part":
    return (ENC_PLAINTEXT, b"", b"", body)


def _encode_part(
    plaintext: bool,
    key: bytes,
    domain: bytes,
    entry_key: bytes,
    key_type: str,
    pt: bytes,
    nonce: "bytes | None",
) -> "Part":
    """Seal one part under AAD = domain || entry_key || key_type (or, dev builds only, leave it
    clear). The nonce is random per part per write -- `nonce` is for known-answer tests ONLY --
    and NEVER derived from the leaf: a rollback revisits (entry_key, C_leaf) pairs, and a
    repeated nonce breaks ChaCha20-Poly1305."""
    from trezor.crypto import chacha20poly1305_encrypt, random

    if plaintext:
        return _clear(pt)
    nonce = nonce or random.bytes(12)
    cipher = chacha20poly1305_encrypt(key, nonce)
    cipher.auth(domain + entry_key + key_type.encode())
    ct = cipher.encrypt(_pad_bucket(pt))
    return (ENC_ENCRYPTED, nonce, cipher.finish(), ct)


def _decode_part(
    key: bytes, domain: bytes, entry_key: bytes, key_type: str, part: "Part | None", unpack
) -> "Any":
    """`unpack` of a part's plaintext (padding left on), or None for a deleted part."""
    from trezor.crypto import AuthenticationError, chacha20poly1305_decrypt
    from trezor.wire import DataError

    if is_delete(part):
        return None
    assert part is not None
    encoding, nonce, tag, ct = part
    if encoding == ENC_PLAINTEXT:
        return unpack(ct)
    cipher = chacha20poly1305_decrypt(key, nonce)
    cipher.auth(domain + entry_key + key_type.encode())
    pt = cipher.decrypt(ct)
    try:
        cipher.finish(tag)
    except AuthenticationError:
        raise DataError("WARD leaf AEAD tag mismatch")
    return unpack(pt)


# Unpacking a short plaintext; only a part that passed its AEAD, or a dev plaintext one, gets here.
_TRUNCATED = "WARD: truncated leaf part"

# C_leaf: the counter a leaf was COMMITTED at (stamped by the committing device), kept in
# the content body so entry_key stays stable. Nothing reads it yet.
C_LEAF_UNUSED = 0


def part_bytes(part: "Part | None") -> bytes:
    """Canonical framing of one part; the only place a part becomes bytes."""
    from .codec import u32

    encoding, nonce, tag, body = part if part is not None else EMPTY_PART
    return (
        bytes([encoding, len(nonce)]) + nonce + bytes([len(tag)]) + tag + u32(len(body)) + body
    )


def is_delete(part: "Part | None") -> bool:
    """An empty body is a delete, whatever the encoding."""
    return part is None or len(part[3]) == 0


# --- identity part ---------------------------------------------------------------
#
# The identity part is the entry_key preimage. It MUST stay sealed: in the clear the host
# would hold identifier -> entry_key, the mapping the HMAC exists to withhold.


def pack_identity(identifier: bytes, app_id: str | bytes, device_id: int = 0) -> bytes:
    """len16(identifier) || identifier || len8(app_id) || app_id || device_id(1B)."""
    from trezor.wire import DataError

    from .codec import lp

    if isinstance(app_id, str):
        app_id = app_id.encode()
    ident = lp(2, identifier, "identifier too long")
    aid = lp(1, app_id, "app_id too long")
    if not 0 <= device_id <= 0xFF:
        raise DataError("device_id must be a single byte")
    return ident + aid + bytes([device_id])


def unpack_identity(pt: bytes) -> "tuple[bytes, bytes, int]":
    """Return (identifier, app_id, device_id). Tolerates padding past the end."""
    from .codec import Reader

    r = Reader(pt, error=_TRUNCATED)
    return r.lp(2), r.lp(1), r.uint(1)


def encode_identity(
    k_ident: bytes,
    entry_key: bytes,
    key_type: str,
    identifier: bytes,
    app_id: str | bytes,
    device_id: int = 0,
    nonce: bytes | None = None,
) -> "Part":
    """Build the identity part. `nonce` is for known-answer tests ONLY."""
    return _encode_part(
        WARD_PLAINTEXT_IDENTITY,
        k_ident,
        _AAD_IDENTITY,
        entry_key,
        key_type,
        pack_identity(identifier, app_id, device_id),
        nonce,
    )


def decode_identity(
    k_ident: bytes, entry_key: bytes, key_type: str, part: "Part | None"
) -> "tuple[bytes, bytes, int] | None":
    """Recover (identifier, app_id, device_id), or None for a deleted part."""
    return _decode_part(k_ident, _AAD_IDENTITY, entry_key, key_type, part, unpack_identity)


# --- content part ----------------------------------------------------------------


def pack_content(c_leaf: int, value: bytes) -> bytes:
    """C_leaf(4B BE) || len32(value) || value."""
    from .codec import u32

    return u32(c_leaf) + u32(len(value)) + value


def unpack_content(pt: bytes) -> "tuple[int, bytes]":
    """Return (c_leaf, value). Tolerates padding past the end."""
    from .codec import Reader

    r = Reader(pt, error=_TRUNCATED)
    return r.uint(4), r.lp(4)


def encode_content(
    k_data: bytes,
    entry_key: bytes,
    key_type: str,
    value: bytes | None,
    c_leaf: int = C_LEAF_UNUSED,
    nonce: bytes | None = None,
) -> "Part":
    """Build the content part. `value=None` means DELETE; b"" is a real empty value.

    `nonce` is for known-answer tests ONLY.
    """
    if value is None:
        return EMPTY_PART
    return _encode_part(
        WARD_PLAINTEXT_CONTENT,
        k_data,
        _AAD_CONTENT,
        entry_key,
        key_type,
        pack_content(c_leaf, value),
        nonce,
    )


def decode_content(
    k_data: bytes, entry_key: bytes, key_type: str, part: "Part | None"
) -> "tuple[int, bytes] | None":
    """Recover (c_leaf, value), or None for a deleted part."""
    return _decode_part(k_data, _AAD_CONTENT, entry_key, key_type, part, unpack_content)


# --- leaf commitment: a function of the encoded parts, so a keyless host can serve proofs.


def commit_of(key_type: str, id_part: "Part | None", val_part: "Part | None") -> bytes:
    """commit = sha256(0x02 || len8(key_type) || key_type
    || len32(id_part) || id_part || len32(val_part) || val_part)."""
    from .codec import u32

    from trezor.crypto.hashlib import sha256

    kt = key_type.encode()
    id_bytes = part_bytes(id_part)
    val_bytes = part_bytes(val_part)
    return sha256(
        b"\x02"
        + bytes([len(kt)])
        + kt
        + u32(len(id_bytes))
        + id_bytes
        + u32(len(val_bytes))
        + val_bytes
    ).digest()


def leaf_hash_of(entry_key: bytes, commit: bytes) -> bytes:
    """leaf = sha256(0x00 || entry_key || commit), both operands exactly 32 bytes.

    THE WIDTHS ARE THE SECURITY: without them (K, C) and (K || C[0], C[1:]) hash alike, which
    let a host pass a membership proof off as non-membership.
    """
    from trezor.crypto.hashlib import sha256
    from trezor.wire import DataError

    if len(entry_key) != 32 or len(commit) != 32:
        raise DataError("WARD: leaf operands must be 32 bytes")
    return sha256(b"\x00" + entry_key + commit).digest()


def leaf_hash(
    entry_key: bytes, key_type: str, id_part: "Part | None", val_part: "Part | None"
) -> bytes:
    return leaf_hash_of(entry_key, commit_of(key_type, id_part, val_part))


# --- wire <-> part codec ---------------------------------------------------------
# The only place the wire's manual oneof is mapped; a part in an encoding this build does
# not expect is rejected.


def make_leaf_content(part: "Part | None") -> "Any":
    from trezor.messages import WardEncryptedLeaf, WardLeafContent, WardPlaintextLeaf

    encoding, nonce, tag, body = part if part is not None else EMPTY_PART
    if encoding == ENC_PLAINTEXT:
        return WardLeafContent(
            encoding=ENC_PLAINTEXT, plaintext=WardPlaintextLeaf(content=body)
        )
    return WardLeafContent(
        encoding=ENC_ENCRYPTED,
        encrypted=WardEncryptedLeaf(nonce=nonce, tag=tag, ct=body),
    )


# Fixed by the AEAD; checked before a sealed part reaches the cipher.
_NONCE_LEN = 12
_TAG_LEN = 16


def _require_canonical(encoding: "Any", sealed: "Any", clear: "Any") -> int:
    """The discriminator of a manual oneof, strictly: unknown encodings and both arms set are
    refused, since either would frame the commit differently from the host twins."""
    from trezor.wire import DataError

    e = encoding if encoding is not None else ENC_ENCRYPTED
    if e not in (ENC_ENCRYPTED, ENC_PLAINTEXT):
        raise DataError("WARD: unknown leaf part encoding")
    if sealed is not None and clear is not None:
        raise DataError("WARD: leaf part sets both encodings")
    return e


def _mode_error(sealed: bool, what: str) -> Exception:
    from trezor.wire import DataError

    if sealed:
        return DataError("WARD: encrypted %s but firmware is plaintext-only" % what)
    return DataError("WARD: plaintext %s but firmware is encrypted-only" % what)


def _sealed_part(e: "Any", what: str) -> "Part":
    """A sealed wire part, its nonce and tag at the AEAD's fixed widths."""
    from trezor.wire import DataError

    if len(e.nonce or b"") != _NONCE_LEN or len(e.tag or b"") != _TAG_LEN:
        raise DataError("WARD: sealed %s has a malformed nonce or tag" % what)
    return (ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b"")


def read_leaf_content(content: "Any") -> "Part | None":
    if content is None:
        return None
    if _require_canonical(content.encoding, content.encrypted, content.plaintext) == (
        ENC_PLAINTEXT
    ):
        p = content.plaintext
        body = p.content if (p is not None and p.content is not None) else b""
        # An empty body is a delete (EMPTY_PART is plaintext-encoded): accepted in either mode.
        if len(body) > 0 and not WARD_PLAINTEXT_CONTENT:
            raise _mode_error(False, "content")
        return _clear(body)
    if WARD_PLAINTEXT_CONTENT:
        raise _mode_error(True, "content")
    e = content.encrypted
    return None if e is None else _sealed_part(e, "content")


def make_leaf_identity(key_type: str, part: "Part | None") -> "Any":
    from trezor.messages import (
        WardEncryptedIdentity,
        WardLeafIdentity,
        WardPlainIdentity,
    )

    encoding, nonce, tag, body = part if part is not None else EMPTY_PART
    if encoding == ENC_PLAINTEXT:
        plain = WardPlainIdentity()
        if len(body) > 0:
            identifier, app_id, device_id = unpack_identity(body)
            plain = WardPlainIdentity(
                identifier=identifier, app_id=app_id.decode(), device_id=device_id
            )
        return WardLeafIdentity(encoding=ENC_PLAINTEXT, key_type=key_type, plain=plain)
    return WardLeafIdentity(
        encoding=ENC_ENCRYPTED,
        key_type=key_type,
        encrypted=WardEncryptedIdentity(nonce=nonce, tag=tag, ct=body),
    )


def read_leaf_identity(identity: "Any") -> "tuple[str | None, Part | None]":
    from .keys import ENTRY_TYPE_ADDRESS

    if identity is None:
        return None, None
    key_type = identity.key_type or ENTRY_TYPE_ADDRESS
    if _require_canonical(identity.encoding, identity.encrypted, identity.plain) == (
        ENC_PLAINTEXT
    ):
        p = identity.plain
        if p is None or p.identifier is None:
            # A delete's empty part, accepted in either mode.
            return key_type, None
        if not WARD_PLAINTEXT_IDENTITY:
            raise _mode_error(False, "identity")
        return key_type, _clear(
            pack_identity(p.identifier, p.app_id or b"", p.device_id or 0)
        )
    if WARD_PLAINTEXT_IDENTITY:
        raise _mode_error(True, "identity")
    e = identity.encrypted
    return key_type, None if e is None else _sealed_part(e, "identity")
