"""WARD keyed path + two-part leaf primitives (host/reference side).

Implements the key-derivation and hashing layer specified in ward-design.md
§1/§2.1/§2.2/§3 and ToDo-leaf_structure.md.

Canonical layout (must match apps/ward/service.py on firmware and
@trezor/ward on the host):

    SLIP-21 (SLIP-0021) symmetric derivation from the seed, under m/"ward":
        K_path         = SLIP21(seed, [b"ward", b"K_path"]).key()            # HMAC-SHA256 key
        K_ident(type)  = SLIP21(seed, [b"ward", b"K_ident", key_type]).key() # seals LeafIdentity
        K_data(type)   = SLIP21(seed, [b"ward", b"K_data",  key_type]).key() # seals LeafContent

    scope            = app_id || 0x00 || key_type || 0x00 || device_id       # device_id = 0x00 => global
    LeafIdentityMAC  = HMAC-SHA256(K_path, scope || identifier)             # 32B, IS the trie path (§3.1)

A leaf is TWO independently encoded parts, each with its own key, so the identity
and the value are separately discloseable:

    LeafIdentity   identifier, app_id, device_id            sealed under K_ident(key_type)
    LeafContent    C_leaf, value                            sealed under K_data(key_type)

`key_type` is ALWAYS CLEAR — it selects both keys, so it cannot itself be sealed.

Each part is encoded either encrypted (RFC-7539 ChaCha20-Poly1305, 12-byte nonce,
bucket-padded plaintext) or plaintext, independently. The encoding byte is inside
the commit, so the two are domain-separated by construction:

    part(p)   = encoding(1B) || len8(nonce) || nonce || len8(tag) || tag
                             || len32(body) || body
    commit    = SHA-256(0x02 || len8(key_type) || key_type
                             || len32(id_part) || id_part
                             || len32(val_part) || val_part)
    leaf      = SHA-256(0x00 || LeafIdentityMAC || commit)

    identity plaintext = len16(identifier) || identifier || len8(app_id) || app_id
                                           || device_id(1B)
    content  plaintext = C_leaf(4B BE) || len32(value) || value
    AAD: identity 0x03 || mac || key_type,  content 0x02 || mac || key_type

An empty content body is a delete. `LeafIdentityMAC` is a PRF-derived path, NOT an
authenticator (§2.5): it hides the identifier from a keyless host and makes the path
host-unforgeable. Note the MAC is *stored* alongside the leaf, so locating a leaf
never requires a key; K_path is needed only to check that a stored MAC matches its
stored identity, or to compute a MAC for an identity not in the store.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import os
from typing import List, NamedTuple, Optional, Tuple, Union

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

_SLIP21_LABEL_ROOT = b"ward"

# part encodings (the byte that goes into the commit)
ENC_ENCRYPTED = 0
ENC_PLAINTEXT = 1


def _as_bytes(x: Union[str, bytes]) -> bytes:
    return x.encode() if isinstance(x, str) else x


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# --- SLIP-0021 symmetric key derivation (matches apps.common.seed.Slip21Node) ---

def _slip21_master(seed: bytes) -> bytes:
    return _hmac.new(b"Symmetric key seed", seed, hashlib.sha512).digest()


def _slip21_derive(seed: bytes, path: List[bytes]) -> bytes:
    data = _slip21_master(seed)
    for label in path:
        h = _hmac.new(data[0:32], b"\x00", hashlib.sha512)
        h.update(label)
        data = h.digest()
    return data[32:64]  # .key()


def derive_k_path(seed: bytes) -> bytes:
    """K_path: the HMAC-SHA256 key used to derive every LeafIdentityMAC (trie path)."""
    return _slip21_derive(seed, [_SLIP21_LABEL_ROOT, b"K_path"])


def derive_k_ident(seed: bytes, key_type: Union[str, bytes]) -> bytes:
    """K_ident(key_type): the AEAD key sealing the LeafIdentity part. Per-type, so an
    export can hand a host only the types whose identities it may read."""
    return _slip21_derive(seed, [_SLIP21_LABEL_ROOT, b"K_ident", _as_bytes(key_type)])


def derive_k_data(seed: bytes, key_type: Union[str, bytes]) -> bytes:
    """K_data(key_type): the AEAD key sealing the LeafContent part. Separate from
    K_ident so values and identities are independently discloseable."""
    return _slip21_derive(seed, [_SLIP21_LABEL_ROOT, b"K_data", _as_bytes(key_type)])


# --- path derivation ---

def scope_bytes(
    app_id: Union[str, bytes], key_type: Union[str, bytes], device_id: int = 0
) -> bytes:
    """scope = app_id || 0x00 || key_type || 0x00 || device_id(1B). device_id=0 => global."""
    if not 0 <= device_id <= 0xFF:
        raise ValueError("device_id must be a single byte (0 = global)")
    return _as_bytes(app_id) + b"\x00" + _as_bytes(key_type) + b"\x00" + bytes([device_id])


def leaf_identity_mac(
    k_path: bytes,
    app_id: Union[str, bytes],
    identifier: bytes,
    key_type: Union[str, bytes] = "address",
    device_id: int = 0,
) -> bytes:
    """LeafIdentityMAC = HMAC-SHA256(K_path, scope || identifier) — the 32B trie path."""
    msg = scope_bytes(app_id, key_type, device_id) + identifier
    return _hmac.new(k_path, msg, hashlib.sha256).digest()


# Wire/proto and the trie still call this field `entry_key`; the two names are the
# same 32 bytes.
entry_key = leaf_identity_mac


# --- leaf-mode flags (must mirror core service.py) ---
# Each part's encoding is independent and self-describing on the wire; these consts
# are the build's *write* preference. Tests flip them to exercise all four
# combinations. False = encrypted.
WARD_PLAINTEXT_IDENTITY = False
WARD_PLAINTEXT_CONTENT = False


# --- the two parts ---

class Part(NamedTuple):
    """One encoded leaf part. `body` is the ciphertext when encoding == ENC_ENCRYPTED,
    the packed plaintext when ENC_PLAINTEXT. nonce/tag are empty for plaintext."""

    encoding: int
    nonce: bytes
    tag: bytes
    body: bytes

    def is_empty(self) -> bool:
        return len(self.body) == 0


EMPTY_PART = Part(ENC_PLAINTEXT, b"", b"", b"")


class LeafBlob(NamedTuple):
    """A whole leaf as stored/transmitted: the clear key_type plus the two parts.
    Stored alongside its LeafIdentityMAC, which is the record's key."""

    key_type: str
    identity: Part
    content: Part

    def is_delete(self) -> bool:
        return self.content.is_empty()


def _part_bytes(p: Part) -> bytes:
    return (
        bytes([p.encoding])
        + bytes([len(p.nonce)])
        + p.nonce
        + bytes([len(p.tag)])
        + p.tag
        + len(p.body).to_bytes(4, "big")
        + p.body
    )


def commit_of(leaf: LeafBlob) -> bytes:
    """Keyless leaf commitment (§2.2) over both parts and the clear key_type. A host
    holding no keys can still recompute it, whatever each part's encoding is."""
    kt = _as_bytes(leaf.key_type)
    id_part = _part_bytes(leaf.identity)
    val_part = _part_bytes(leaf.content)
    return sha256(
        b"\x02"
        + bytes([len(kt)])
        + kt
        + len(id_part).to_bytes(4, "big")
        + id_part
        + len(val_part).to_bytes(4, "big")
        + val_part
    )


def leaf_hash_of(mac: bytes, commit: bytes) -> bytes:
    """leaf = SHA-256(0x00 || LeafIdentityMAC || commit) (§2.2)."""
    return sha256(b"\x00" + mac + commit)


def leaf_hash(mac: bytes, leaf: LeafBlob) -> bytes:
    return leaf_hash_of(mac, commit_of(leaf))


# --- AEAD plumbing (RFC-7539 ChaCha20-Poly1305, 12-byte nonce) ---

NONCE_LEN = 12
TAG_LEN = 16
_BUCKETS = (64, 256, 1024, 4096)

AAD_IDENTITY = b"\x03"
AAD_CONTENT = b"\x02"


def _aad(domain: bytes, mac: bytes, key_type: Union[str, bytes]) -> bytes:
    return domain + mac + _as_bytes(key_type)


def _pad_bucket(pt: bytes) -> bytes:
    for b in _BUCKETS:
        if len(pt) <= b:
            return pt + b"\x00" * (b - len(pt))
    rem = (-len(pt)) % _BUCKETS[-1]
    return pt + b"\x00" * rem


def _seal(
    key: bytes, domain: bytes, mac: bytes, key_type: Union[str, bytes], pt: bytes,
    nonce: Optional[bytes] = None,
) -> Part:
    if nonce is None:
        nonce = os.urandom(NONCE_LEN)
    if len(nonce) != NONCE_LEN:
        raise ValueError("nonce must be 12 bytes (RFC-7539)")
    ct_and_tag = ChaCha20Poly1305(key).encrypt(
        nonce, _pad_bucket(pt), _aad(domain, mac, key_type)
    )
    return Part(ENC_ENCRYPTED, nonce, ct_and_tag[-TAG_LEN:], ct_and_tag[:-TAG_LEN])


def _open(
    key: bytes, domain: bytes, mac: bytes, key_type: Union[str, bytes], part: Part
) -> bytes:
    if part.encoding == ENC_PLAINTEXT:
        return part.body
    return ChaCha20Poly1305(key).decrypt(
        part.nonce, part.body + part.tag, _aad(domain, mac, key_type)
    )


# --- LeafIdentity part ---

def pack_identity(identifier: bytes, app_id: Union[str, bytes], device_id: int = 0) -> bytes:
    """Canonical identity plaintext: len16(identifier) || identifier || len8(app_id)
    || app_id || device_id(1B). The single source of canonicalization — both the
    commit and the AEAD go through it."""
    aid = _as_bytes(app_id)
    if len(aid) > 0xFF:
        raise ValueError("app_id too long")
    if not 0 <= device_id <= 0xFF:
        raise ValueError("device_id must be a single byte")
    return (
        len(identifier).to_bytes(2, "big")
        + identifier
        + bytes([len(aid)])
        + aid
        + bytes([device_id])
    )


def unpack_identity(pt: bytes) -> Tuple[bytes, bytes, int]:
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
    k_ident: bytes,
    mac: bytes,
    key_type: Union[str, bytes],
    identifier: bytes,
    app_id: Union[str, bytes],
    device_id: int = 0,
    plaintext: Optional[bool] = None,
    nonce: Optional[bytes] = None,
) -> Part:
    """Encode the LeafIdentity part for this build's mode (or an explicit override)."""
    pt = pack_identity(identifier, app_id, device_id)
    if WARD_PLAINTEXT_IDENTITY if plaintext is None else plaintext:
        return Part(ENC_PLAINTEXT, b"", b"", pt)
    return _seal(k_ident, AAD_IDENTITY, mac, key_type, pt, nonce)


def decode_identity(
    k_ident: bytes, mac: bytes, key_type: Union[str, bytes], part: Part
) -> Tuple[bytes, bytes, int]:
    """Return (identifier, app_id, device_id). Raises on tag failure (hard abort, §3.1)."""
    return unpack_identity(_open(k_ident, AAD_IDENTITY, mac, key_type, part))


# --- LeafContent part ---

def pack_content(c_leaf: int, value: bytes) -> bytes:
    """Canonical content plaintext: C_leaf(4B BE) || len32(value) || value. The
    identifier used to live here; it is in the identity part now."""
    return c_leaf.to_bytes(4, "big") + len(value).to_bytes(4, "big") + value


def unpack_content(pt: bytes) -> Tuple[int, bytes]:
    """Return (c_leaf, value). Tolerates bucket padding past the end."""
    c_leaf = int.from_bytes(pt[0:4], "big")
    val_len = int.from_bytes(pt[4:8], "big")
    return c_leaf, pt[8 : 8 + val_len]


def encode_content(
    k_data: bytes,
    mac: bytes,
    key_type: Union[str, bytes],
    c_leaf: int,
    value: bytes,
    plaintext: Optional[bool] = None,
    nonce: Optional[bytes] = None,
) -> Part:
    """Encode the LeafContent part for this build's mode (or an explicit override)."""
    pt = pack_content(c_leaf, value)
    if WARD_PLAINTEXT_CONTENT if plaintext is None else plaintext:
        return Part(ENC_PLAINTEXT, b"", b"", pt)
    return _seal(k_data, AAD_CONTENT, mac, key_type, pt, nonce)


def decode_content(
    k_data: bytes, mac: bytes, key_type: Union[str, bytes], part: Part
) -> Tuple[int, bytes]:
    """Return (c_leaf, value). Raises on tag failure (hard abort, §3.1)."""
    return unpack_content(_open(k_data, AAD_CONTENT, mac, key_type, part))


# --- whole-leaf convenience ---

def encode_leaf(
    k_ident: bytes,
    k_data: bytes,
    mac: bytes,
    key_type: str,
    c_leaf: int,
    identifier: bytes,
    app_id: Union[str, bytes],
    value: bytes,
    device_id: int = 0,
    plaintext_identity: Optional[bool] = None,
    plaintext_content: Optional[bool] = None,
    id_nonce: Optional[bytes] = None,
    val_nonce: Optional[bytes] = None,
) -> LeafBlob:
    """Build a whole LeafBlob. An empty `value` produces a FULL DELETE: both parts are
    empty, because the leaf ceases to exist -- there is no tombstone to describe."""
    if len(value) == 0:
        return LeafBlob(key_type, EMPTY_PART, EMPTY_PART)
    identity = encode_identity(
        k_ident, mac, key_type, identifier, app_id, device_id,
        plaintext=plaintext_identity, nonce=id_nonce,
    )
    content = encode_content(
        k_data, mac, key_type, c_leaf, value,
        plaintext=plaintext_content, nonce=val_nonce,
    )
    return LeafBlob(key_type, identity, content)


def decode_leaf(
    k_ident: bytes, k_data: bytes, mac: bytes, leaf: LeafBlob
) -> Tuple[int, bytes, bytes, int, bytes]:
    """Return (c_leaf, identifier, app_id, device_id, value)."""
    identifier, app_id, device_id = decode_identity(k_ident, mac, leaf.key_type, leaf.identity)
    if leaf.content.is_empty():
        return 0, identifier, app_id, device_id, b""
    c_leaf, value = decode_content(k_data, mac, leaf.key_type, leaf.content)
    return c_leaf, identifier, app_id, device_id, value


def verify_mac(k_path: bytes, mac: bytes, leaf: LeafBlob, k_ident: bytes) -> bool:
    """Check that a *stored* MAC really is the MAC of its stored identity. This is the
    integrity check the old format made impossible in either direction."""
    identifier, app_id, device_id = decode_identity(k_ident, mac, leaf.key_type, leaf.identity)
    return leaf_identity_mac(k_path, app_id, identifier, leaf.key_type, device_id) == mac
