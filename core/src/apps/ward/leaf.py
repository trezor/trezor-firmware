"""The WARD leaf: two independently encoded parts, plus the wire codec for them.

    part(p)       = encoding(1B) || len8(nonce) || nonce || len8(tag) || tag
                                 || len32(body) || body
    pack_identity = len16(identifier) || identifier || len8(app_id) || app_id
                                      || device_id(1B)
    pack_content  = C_leaf(4B BE) || len32(value) || value

`key_type` is always clear -- it selects the two keys that will seal the parts -- and
travels on the identity part rather than being repeated per part.

Each part is SEALED with ChaCha20-Poly1305 under a device-only key -- the identity under
K_ident(key_type), the content under K_data(key_type) -- so the host holds two opaque
blobs it can neither read nor forge. The AAD binds a part to its path, its part-domain
and its key_type:

    aad = domain(1B) || entry_key || key_type

so a part cannot be replayed as the other part, nor moved to another path: both fail the
tag check.

What sealing does NOT buy: freshness or existence. The host can still return an older
sealed leaf for the same path, or claim it holds none. Only a proof against an attested
root detects those, which is why the screens still warn.

THE DEVICE BUILDS THE LEAF -- now a hard fact, not a convention: the host has none of
the keys, so it cannot produce a part at all.

Byte-for-byte identical to the reference implementation, so its published leaf vectors
pin this code; see `core/tests/test_apps.ward.py`.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    # (encoding, nonce, tag, body)
    Part = tuple[int, bytes, bytes, bytes]

ENC_ENCRYPTED = 0
ENC_PLAINTEXT = 1

# An empty part means DELETED. Distinct from a present part whose body carries a
# zero-length value, which is an entry that exists and whose value happens to be empty.
# Conflating those -- as the reference does, returning an empty part for any empty value
# -- makes an empty-valued entry impossible to represent and impossible to delete.
EMPTY_PART: "Part" = (ENC_PLAINTEXT, b"", b"", b"")

# Per-part mode (dev switch). False = sealed, which is what production ships; True leaves
# that part host-inspectable. The two parts are INDEPENDENT: a build may seal the identity
# and leave the content readable, or the reverse. The wire is self-describing either way,
# and each part's encoding byte sits inside its framing, so the modes cannot collide.
WARD_PLAINTEXT_IDENTITY = False
WARD_PLAINTEXT_CONTENT = False

if (WARD_PLAINTEXT_IDENTITY or WARD_PLAINTEXT_CONTENT) and not __debug__:
    # A release build must never hand the host a readable part. Failing at import is the
    # point: this is not a condition to discover from a screenshot months later.
    raise RuntimeError("WARD plaintext leaf parts require a __debug__ build")

# --- AEAD (ChaCha20-Poly1305, RFC-7539, 12-byte nonce) ---

# Ciphertext is padded up to the next bucket so its length leaks only a coarse band
# rather than the exact size of the value. Plaintext parts are NOT padded: the body is
# readable anyway, so padding would buy nothing and only complicate the layout.
_AEAD_BUCKETS = (64, 256, 1024, 4096)

# Part-domain separation, inside the AAD. Distinct constants are what stop an identity
# part from ever being consumed as a content part.
_AAD_IDENTITY = b"\x03"
_AAD_CONTENT = b"\x02"


def _aead_aad(domain: bytes, entry_key: bytes, key_type: str) -> bytes:
    """Bind a part to its leaf, its part-domain and its key_type.

    Including entry_key is what makes a sealed part unmovable: replaying it under another
    path changes the AAD and the tag check fails.
    """
    return domain + entry_key + key_type.encode()


def _pad_bucket(pt: bytes) -> bytes:
    for b in _AEAD_BUCKETS:
        if len(pt) <= b:
            return pt + b"\x00" * (b - len(pt))
    return pt + b"\x00" * ((-len(pt)) % _AEAD_BUCKETS[-1])


def _seal(
    key: bytes, domain: bytes, entry_key: bytes, key_type: str, pt: bytes, nonce: bytes
) -> "Part":
    """Seal one part. The NONCE IS AN ARGUMENT, never generated here.

    Generation lives in the two encode_* functions, which is the only place it should:
    that keeps this function deterministic and therefore pinnable by a known-answer test,
    while leaving exactly one line in the module capable of getting nonce generation
    wrong.
    """
    from trezor.crypto import chacha20poly1305_encrypt

    cipher = chacha20poly1305_encrypt(key, nonce)
    cipher.auth(_aead_aad(domain, entry_key, key_type))
    ct = cipher.encrypt(_pad_bucket(pt))
    return (ENC_ENCRYPTED, nonce, cipher.finish(), ct)


def _open(
    key: bytes, domain: bytes, entry_key: bytes, key_type: str, part: "Part"
) -> bytes:
    """Open one sealed part, or raise. Padding is left on; the unpackers tolerate it."""
    from trezor.crypto import AuthenticationError, chacha20poly1305_decrypt
    from trezor.wire import DataError

    _encoding, nonce, tag, ct = part
    cipher = chacha20poly1305_decrypt(key, nonce)
    cipher.auth(_aead_aad(domain, entry_key, key_type))
    pt = cipher.decrypt(ct)
    try:
        cipher.finish(tag)
    except AuthenticationError:
        # The host returned a part that was not sealed for this path, this part-domain
        # and this key_type -- forged, corrupted, or lifted from another entry.
        raise DataError("WARD leaf AEAD tag mismatch")
    return pt


def _fresh_nonce() -> bytes:
    """A fresh 12 bytes per part per write -- NEVER derived from the leaf.

    Deriving it from (entry_key, C_leaf) would be catastrophic here, because a rollback
    legitimately re-visits a pair that has already been sealed, and a repeated
    (key, nonce) under ChaCha20-Poly1305 loses both confidentiality and the tag's
    unforgeability.
    """
    from trezor.crypto import random

    return random.bytes(12)


# C_leaf is the global root counter stamped onto a leaf when it changes. It lives inside
# the content body and never in entry_key, so an entry keeps one stable path across
# versions. Nothing reads it yet: no root exists to count, and the trie hashes the
# encoded part without inspecting it. Fixed at 0 until the root lands, at which point a
# real counter drops in without changing this layout or any hash over it.
C_LEAF_UNUSED = 0


def part_bytes(part: "Part | None") -> bytes:
    """Canonical framing of one part; the only place a part becomes bytes."""
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


def is_delete(part: "Part | None") -> bool:
    """An empty body is a delete, whatever the encoding."""
    return part is None or len(part[3]) == 0


# --- identity part ---------------------------------------------------------------
#
# The identity part IS the entry_key preimage, kept so nothing has to recompute it -- the
# scope's three fields plus the identifier, which is exactly what `keys.entry_key` HMACs.
# That it is SEALED is the whole point: the host stores the preimage without holding it, so
# it can serve an entry it cannot name. Storing this part in the clear for indexing would
# undo the keyed path entirely -- the host would hold identifier -> entry_key for every row,
# which is the mapping the HMAC exists to withhold.


def pack_identity(identifier: bytes, app_id: str | bytes, device_id: int = 0) -> bytes:
    """len16(identifier) || identifier || len8(app_id) || app_id || device_id(1B).

    The single point of canonicalisation for the identity body: both the commitment and
    (later) the AEAD go through it, so they can never disagree.
    """
    from trezor.wire import DataError

    if isinstance(app_id, str):
        app_id = app_id.encode()
    if len(identifier) > 0xFFFF:
        raise DataError("identifier too long")
    if len(app_id) > 0xFF:
        raise DataError("app_id too long")
    if not 0 <= device_id <= 0xFF:
        raise DataError("device_id must be a single byte")

    return (
        len(identifier).to_bytes(2, "big")
        + identifier
        + bytes([len(app_id)])
        + app_id
        + bytes([device_id])
    )


def unpack_identity(pt: bytes) -> "tuple[bytes, bytes, int]":
    """Return (identifier, app_id, device_id). Tolerates padding past the end."""
    id_len = int.from_bytes(pt[0:2], "big")
    off = 2 + id_len
    identifier = pt[2:off]
    aid_len = pt[off]
    off += 1
    app_id = pt[off : off + aid_len]
    off += aid_len
    return identifier, app_id, pt[off]


def encode_identity(
    k_ident: bytes,
    entry_key: bytes,
    key_type: str,
    identifier: bytes,
    app_id: str | bytes,
    device_id: int = 0,
    nonce: bytes | None = None,
) -> "Part":
    """Build the identity part, sealed unless this build leaves identities readable.

    `nonce` is for known-answer tests ONLY; production must leave it None so a fresh one
    is generated per write.
    """
    pt = pack_identity(identifier, app_id, device_id)
    if WARD_PLAINTEXT_IDENTITY:
        return (ENC_PLAINTEXT, b"", b"", pt)
    return _seal(
        k_ident, _AAD_IDENTITY, entry_key, key_type, pt, nonce or _fresh_nonce()
    )


def decode_identity(
    k_ident: bytes, entry_key: bytes, key_type: str, part: "Part | None"
) -> "tuple[bytes, bytes, int] | None":
    """Recover (identifier, app_id, device_id), or None for a deleted part."""
    if is_delete(part):
        return None
    assert part is not None
    if part[0] == ENC_PLAINTEXT:
        return unpack_identity(part[3])
    return unpack_identity(_open(k_ident, _AAD_IDENTITY, entry_key, key_type, part))


# --- content part ----------------------------------------------------------------


def pack_content(c_leaf: int, value: bytes) -> bytes:
    """C_leaf(4B BE) || len32(value) || value."""
    return c_leaf.to_bytes(4, "big") + len(value).to_bytes(4, "big") + value


def unpack_content(pt: bytes) -> "tuple[int, bytes]":
    """Return (c_leaf, value). Tolerates padding past the end."""
    c_leaf = int.from_bytes(pt[0:4], "big")
    val_len = int.from_bytes(pt[4:8], "big")
    return c_leaf, pt[8 : 8 + val_len]


def encode_content(
    k_data: bytes,
    entry_key: bytes,
    key_type: str,
    value: bytes | None,
    c_leaf: int = C_LEAF_UNUSED,
    nonce: bytes | None = None,
) -> "Part":
    """Build the content part. `value=None` means DELETE; b"" is a real empty value.

    Note the asymmetry with the reference, which returns an empty part for any
    zero-length value and so cannot tell an empty entry from a deleted one.

    `nonce` is for known-answer tests ONLY; production must leave it None.
    """
    if value is None:
        return EMPTY_PART
    pt = pack_content(c_leaf, value)
    if WARD_PLAINTEXT_CONTENT:
        return (ENC_PLAINTEXT, b"", b"", pt)
    return _seal(k_data, _AAD_CONTENT, entry_key, key_type, pt, nonce or _fresh_nonce())


def decode_content(
    k_data: bytes, entry_key: bytes, key_type: str, part: "Part | None"
) -> "tuple[int, bytes] | None":
    """Recover (c_leaf, value), or None for a deleted part."""
    if is_delete(part):
        return None
    assert part is not None
    if part[0] == ENC_PLAINTEXT:
        return unpack_content(part[3])
    return unpack_content(_open(k_data, _AAD_CONTENT, entry_key, key_type, part))


# --- leaf commitment -------------------------------------------------------------
# The trie will hash THIS, not the value. It belongs to the leaf rather than to the trie:
# it is a function of the parts alone, and a host holding no keys can still recompute it,
# which is what lets one serve proofs without being able to read anything.


def commit_of(key_type: str, id_part: "Part | None", val_part: "Part | None") -> bytes:
    """commit = sha256(0x02 || len8(key_type) || key_type
    || len32(id_part) || id_part || len32(val_part) || val_part)."""
    from trezor.crypto.hashlib import sha256

    kt = key_type.encode()
    id_bytes = part_bytes(id_part)
    val_bytes = part_bytes(val_part)
    return sha256(
        b"\x02"
        + bytes([len(kt)])
        + kt
        + len(id_bytes).to_bytes(4, "big")
        + id_bytes
        + len(val_bytes).to_bytes(4, "big")
        + val_bytes
    ).digest()


def leaf_hash_of(entry_key: bytes, commit: bytes) -> bytes:
    """leaf = sha256(0x00 || entry_key || commit).

    Takes the commitment rather than the parts, so a verifier can rebuild a witness leaf
    from (entry_key, commit) without ever holding the parts themselves.
    """
    from trezor.crypto.hashlib import sha256

    return sha256(b"\x00" + entry_key + commit).digest()


def leaf_hash(
    entry_key: bytes, key_type: str, id_part: "Part | None", val_part: "Part | None"
) -> bytes:
    return leaf_hash_of(entry_key, commit_of(key_type, id_part, val_part))


# --- wire <-> part codec ---------------------------------------------------------
# The wire carries a self-describing "manual oneof" per part (the codegen has no
# `oneof`, so `encoding` is the discriminator and mutual exclusivity is a code
# invariant). These four functions are the ONLY place that mapping happens, and they
# reject a part whose encoding this build does not expect -- an encrypted-only build
# must not silently accept a plaintext part handed to it by the host.


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


def read_leaf_content(content: "Any") -> "Part | None":
    from trezor.wire import DataError

    if content is None:
        return None
    if (content.encoding or ENC_ENCRYPTED) == ENC_PLAINTEXT:
        p = content.plaintext
        body = p.content if (p is not None and p.content is not None) else b""
        # An EMPTY body is a delete and carries nothing, so its encoding byte is
        # immaterial: accept it in either mode. Without this a sealed build would reject
        # its own delete leaf, since EMPTY_PART is plaintext-encoded by construction.
        if len(body) > 0 and not WARD_PLAINTEXT_CONTENT:
            raise DataError("WARD: plaintext content but firmware is encrypted-only")
        return (ENC_PLAINTEXT, b"", b"", body)
    if WARD_PLAINTEXT_CONTENT:
        raise DataError("WARD: encrypted content but firmware is plaintext-only")
    e = content.encrypted
    if e is None:
        return None
    return (ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b"")


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
    from trezor.wire import DataError

    from .keys import ENTRY_TYPE_ADDRESS

    if identity is None:
        return None, None
    key_type = identity.key_type or ENTRY_TYPE_ADDRESS
    if (identity.encoding or ENC_ENCRYPTED) == ENC_PLAINTEXT:
        p = identity.plain
        if p is None or p.identifier is None:
            # No body: a delete's empty part, acceptable in either mode -- see the same
            # reasoning in read_leaf_content.
            return key_type, None
        if not WARD_PLAINTEXT_IDENTITY:
            raise DataError("WARD: plaintext identity but firmware is encrypted-only")
        body = pack_identity(p.identifier, p.app_id or b"", p.device_id or 0)
        return key_type, (ENC_PLAINTEXT, b"", b"", body)
    if WARD_PLAINTEXT_IDENTITY:
        raise DataError("WARD: encrypted identity but firmware is plaintext-only")
    e = identity.encrypted
    if e is None:
        return key_type, None
    return key_type, (ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b"")
