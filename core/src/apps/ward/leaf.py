"""The WARD leaf: two independently encoded parts, plus the wire codec for them.

    part(p)       = encoding(1B) || len8(nonce) || nonce || len8(tag) || tag
                                 || len32(body) || body
    pack_identity = len16(identifier) || identifier || len8(app_id) || app_id
                                      || device_id(1B)
    pack_content  = C_leaf(4B BE) || len32(value) || value

`key_type` is always clear -- it selects the two keys that will seal the parts -- and
travels on the identity part rather than being repeated per part.

Byte-for-byte identical to the reference implementation, so its published leaf vectors
apply; see `core/tests/test_apps.ward.py`.

THE DEVICE BUILDS THE LEAF. The host stores what it is given and must not synthesise
one. While the bodies are plaintext a host could technically build its own, so the rule
is a convention here -- but it becomes a hard fact once the parts are sealed under
device-only keys, and the protocol is shaped for that now so nothing has to change then.

FIXME(ward): the parts are NOT YET SEALED. Sealing replaces the bodies below with
ChaCha20-Poly1305 ciphertext under K_ident/K_data with the AAD binding entry_key, which
is why `entry_key` and `key_type` are already parameters of every encode/decode call
here despite being unused: only the bodies of these functions change, never their
callers.
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

# Per-part mode. The two parts are INDEPENDENT: a build may seal one and leave the other
# readable. Both are plaintext for now, which is the only mode that exists.
#
# FIXME(ward): when sealing lands these default to False (encrypted) and plaintext
# becomes a debug-only switch, guarded by `if plaintext and not __debug__: raise`. That
# guard is deliberately absent while plaintext is the ONLY mode, since it would make a
# production build impossible.
WARD_PLAINTEXT_IDENTITY = True
WARD_PLAINTEXT_CONTENT = True

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
    entry_key: bytes,
    key_type: str,
    identifier: bytes,
    app_id: str | bytes,
    device_id: int = 0,
) -> "Part":
    """Build the identity part. `entry_key`/`key_type` are the future AEAD AAD."""
    return (ENC_PLAINTEXT, b"", b"", pack_identity(identifier, app_id, device_id))


def decode_identity(
    entry_key: bytes, key_type: str, part: "Part | None"
) -> "tuple[bytes, bytes, int] | None":
    """Recover (identifier, app_id, device_id), or None for a deleted part."""
    if is_delete(part):
        return None
    assert part is not None
    return unpack_identity(part[3])


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
    entry_key: bytes,
    key_type: str,
    value: bytes | None,
    c_leaf: int = C_LEAF_UNUSED,
) -> "Part":
    """Build the content part. `value=None` means DELETE; b"" is a real empty value.

    Note the asymmetry with the reference, which returns an empty part for any
    zero-length value and so cannot tell an empty entry from a deleted one.
    """
    if value is None:
        return EMPTY_PART
    return (ENC_PLAINTEXT, b"", b"", pack_content(c_leaf, value))


def decode_content(
    entry_key: bytes, key_type: str, part: "Part | None"
) -> "tuple[int, bytes] | None":
    """Recover (c_leaf, value), or None for a deleted part."""
    if is_delete(part):
        return None
    assert part is not None
    return unpack_content(part[3])


# --- wire <-> part codec ---------------------------------------------------------
# The wire carries a self-describing "manual oneof" per part (the codegen has no
# `oneof`, so `encoding` is the discriminator and mutual exclusivity is a code
# invariant). These four functions are the ONLY place that mapping happens, and they
# reject a part whose encoding this build does not expect -- an encrypted-only build
# must not silently accept a plaintext part handed to it by the host.


def make_leaf_content(part: "Part | None") -> "Any":
    from trezor.messages import EncryptedLeaf, LeafContent, PlaintextLeaf

    encoding, nonce, tag, body = part if part is not None else EMPTY_PART
    if encoding == ENC_PLAINTEXT:
        return LeafContent(encoding=ENC_PLAINTEXT, plaintext=PlaintextLeaf(content=body))
    return LeafContent(
        encoding=ENC_ENCRYPTED, encrypted=EncryptedLeaf(nonce=nonce, tag=tag, ct=body)
    )


def read_leaf_content(content: "Any") -> "Part | None":
    from trezor.wire import DataError

    if content is None:
        return None
    if (content.encoding or ENC_ENCRYPTED) == ENC_PLAINTEXT:
        if not WARD_PLAINTEXT_CONTENT:
            raise DataError("WARD: plaintext content but firmware is encrypted-only")
        p = content.plaintext
        body = p.content if (p is not None and p.content is not None) else b""
        return (ENC_PLAINTEXT, b"", b"", body)
    if WARD_PLAINTEXT_CONTENT:
        raise DataError("WARD: encrypted content but firmware is plaintext-only")
    e = content.encrypted
    if e is None:
        return None
    return (ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b"")


def make_leaf_identity(key_type: str, part: "Part | None") -> "Any":
    from trezor.messages import EncryptedIdentity, LeafIdentity, PlainIdentity

    encoding, nonce, tag, body = part if part is not None else EMPTY_PART
    if encoding == ENC_PLAINTEXT:
        plain = PlainIdentity()
        if len(body) > 0:
            identifier, app_id, device_id = unpack_identity(body)
            plain = PlainIdentity(
                identifier=identifier, app_id=app_id.decode(), device_id=device_id
            )
        return LeafIdentity(
            encoding=ENC_PLAINTEXT, key_type=key_type, plain=plain
        )
    return LeafIdentity(
        encoding=ENC_ENCRYPTED,
        key_type=key_type,
        encrypted=EncryptedIdentity(nonce=nonce, tag=tag, ct=body),
    )


def read_leaf_identity(identity: "Any") -> "tuple[str | None, Part | None]":
    from trezor.wire import DataError

    from .keys import ENTRY_TYPE_ADDRESS

    if identity is None:
        return None, None
    key_type = identity.key_type or ENTRY_TYPE_ADDRESS
    if (identity.encoding or ENC_ENCRYPTED) == ENC_PLAINTEXT:
        if not WARD_PLAINTEXT_IDENTITY:
            raise DataError("WARD: plaintext identity but firmware is encrypted-only")
        p = identity.plain
        if p is None or p.identifier is None:
            return key_type, None
        body = pack_identity(p.identifier, p.app_id or b"", p.device_id or 0)
        return key_type, (ENC_PLAINTEXT, b"", b"", body)
    if WARD_PLAINTEXT_IDENTITY:
        raise DataError("WARD: encrypted identity but firmware is plaintext-only")
    e = identity.encrypted
    if e is None:
        return key_type, None
    return key_type, (ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b"")
