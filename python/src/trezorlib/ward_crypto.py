"""WARD keyed path + leaf primitives (host/reference side).

Implements the key-derivation and hashing layer specified in ward-design.md
§1/§2.1/§2.2/§3, replacing the earlier unkeyed
``entry_key = sha256(app_id || 0x00 || type || 0x00 || address)``.

Canonical layout (must match apps/ward/service.py on firmware and
@trezor/ward on the host):

    SLIP-21 (SLIP-0021) symmetric derivation from the seed, under m/"ward":
        K_index        = SLIP21(seed, [b"ward", b"K_index"]).key()          # HMAC-SHA256 key
        K_data(type)   = SLIP21(seed, [b"ward", b"K_data", key_type]).key() # per-entry-type AEAD key

    scope     = app_id || 0x00 || key_type || 0x00 || device_id            # device_id = 0x00 => global
    entry_key = HMAC-SHA256(K_index, scope || identifier)                  # 32B, IS the trie path (§3.1)

    commit    = SHA-256(0x02 || nonce || tag || len32(ct) || ct)           # §2.2 (keyless, host-verifiable)
    leaf      = SHA-256(0x00 || entry_key || commit)                       # §2.2

Leaf value codec (§2.1, ChaCha20-Poly1305 RFC-7539, 12-byte nonce):
    plaintext = C_leaf(4B BE) || len16(identifier) || identifier
                             || len32(value) || value || zero-padding
    (nonce, tag, ct) = AEAD(K_data(key_type), nonce, aad = 0x02 || entry_key || entry_type,
                            plaintext-bucketed-to 64/256/1024/4096 B)
    A len(value)==0 write is a delete.

`entry_key` is a PRF-derived path, NOT an authenticator (§2.5): it hides the
identifier from a keyless host and makes the path host-unforgeable.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import os
from typing import List, Tuple, Union

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

_SLIP21_LABEL_ROOT = b"ward"


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


def derive_k_index(seed: bytes) -> bytes:
    """K_index: the HMAC-SHA256 key used to derive every entry_key path."""
    return _slip21_derive(seed, [_SLIP21_LABEL_ROOT, b"K_index"])


def derive_k_data(seed: bytes, key_type: Union[str, bytes]) -> bytes:
    """K_data(key_type): the per-entry-type AEAD key. Separate key per type is
    what lets the PUSH flow hand a host only the types it may decrypt (and why
    entry_type travels in the clear — it selects the key)."""
    return _slip21_derive(seed, [_SLIP21_LABEL_ROOT, b"K_data", _as_bytes(key_type)])


# --- path + leaf hashing ---

def scope_bytes(
    app_id: Union[str, bytes], key_type: Union[str, bytes], device_id: int = 0
) -> bytes:
    """scope = app_id || 0x00 || key_type || 0x00 || device_id(1B). device_id=0 => global."""
    if not 0 <= device_id <= 0xFF:
        raise ValueError("device_id must be a single byte (0 = global)")
    return _as_bytes(app_id) + b"\x00" + _as_bytes(key_type) + b"\x00" + bytes([device_id])


def entry_key(
    k_index: bytes,
    app_id: Union[str, bytes],
    identifier: bytes,
    key_type: Union[str, bytes] = "address",
    device_id: int = 0,
) -> bytes:
    """entry_key = HMAC-SHA256(K_index, scope || identifier) — the 32B trie path (§3.1)."""
    msg = scope_bytes(app_id, key_type, device_id) + identifier
    return _hmac.new(k_index, msg, hashlib.sha256).digest()


# Leaf-content mode (must mirror core service.py WARD_PLAINTEXT_LEAVES for the host
# oracle / proof serving to match the device). False = encrypted leaves; True = plaintext
# leaves (host-inspectable). The wire is a self-describing oneof either way; this const
# picks the commit domain tag + codec. Tests flip it to exercise both modes.
WARD_PLAINTEXT_LEAVES = False


def commit_of(nonce: bytes, tag: bytes, ct: bytes) -> bytes:
    """Keyless leaf-value commitment (§2.2); a host with no keys can still recompute it.
    Domain-separated by leaf mode: encrypted = SHA-256(0x02 || nonce || tag || len32(ct)
    || ct); plaintext = SHA-256(0x04 || len32(content) || content) (nonce/tag empty,
    ct == content). A len(ct)==0 leaf is a delete (resolves to the empty sentinel)."""
    tag_byte = b"\x04" if WARD_PLAINTEXT_LEAVES else b"\x02"
    return sha256(tag_byte + nonce + tag + len(ct).to_bytes(4, "big") + ct)


def leaf_hash_of(entry_key_: bytes, commit: bytes) -> bytes:
    """leaf = SHA-256(0x00 || entry_key || commit) (§2.2)."""
    return sha256(b"\x00" + entry_key_ + commit)


# --- leaf value codec (AEAD, RFC-7539 ChaCha20-Poly1305, 12-byte nonce) ---

NONCE_LEN = 12
TAG_LEN = 16
_BUCKETS = (64, 256, 1024, 4096)


def _aad(entry_key_: bytes, entry_type: Union[str, bytes]) -> bytes:
    return b"\x02" + entry_key_ + _as_bytes(entry_type)


def _pad_bucket(pt: bytes) -> bytes:
    for b in _BUCKETS:
        if len(pt) <= b:
            return pt + b"\x00" * (b - len(pt))
    # larger than the largest bucket: pad up to a 4096 multiple
    rem = (-len(pt)) % _BUCKETS[-1]
    return pt + b"\x00" * rem


def encrypt_leaf(
    k_data: bytes,
    entry_key_: bytes,
    entry_type: Union[str, bytes],
    c_leaf: int,
    identifier: bytes,
    value: bytes,
    nonce: bytes = None,
) -> Tuple[bytes, bytes, bytes]:
    """Return (nonce, tag, ct). nonce is random per write unless supplied (tests)."""
    if nonce is None:
        nonce = os.urandom(NONCE_LEN)
    if len(nonce) != NONCE_LEN:
        raise ValueError("nonce must be 12 bytes (RFC-7539)")
    pt = (
        c_leaf.to_bytes(4, "big")
        + len(identifier).to_bytes(2, "big")
        + identifier
        + len(value).to_bytes(4, "big")
        + value
    )
    ct_and_tag = ChaCha20Poly1305(k_data).encrypt(nonce, _pad_bucket(pt), _aad(entry_key_, entry_type))
    ct, tag = ct_and_tag[:-TAG_LEN], ct_and_tag[-TAG_LEN:]
    return nonce, tag, ct


def decrypt_leaf(
    k_data: bytes,
    entry_key_: bytes,
    entry_type: Union[str, bytes],
    nonce: bytes,
    tag: bytes,
    ct: bytes,
) -> Tuple[int, bytes, bytes]:
    """Return (c_leaf, identifier, value). Raises on tag failure (hard abort, §3.1)."""
    pt = ChaCha20Poly1305(k_data).decrypt(nonce, ct + tag, _aad(entry_key_, entry_type))
    c_leaf = int.from_bytes(pt[0:4], "big")
    id_len = int.from_bytes(pt[4:6], "big")
    off = 6 + id_len
    identifier = pt[6:off]
    val_len = int.from_bytes(pt[off:off + 4], "big")
    off += 4
    value = pt[off:off + val_len]
    return c_leaf, identifier, value


# --- plaintext leaf codec (no encryption; host-inspectable dev mode) ---
# content = C_leaf(4B BE) || len16(identifier) || identifier || len32(value) || value
# (the same packed plaintext, minus the AEAD and the bucket padding). The "ct" slot of
# the (nonce, tag, ct) blob carries `content`; nonce/tag stay empty.


def pack_leaf(c_leaf: int, identifier: bytes, value: bytes) -> bytes:
    """Plaintext leaf content (no encryption). Mirrors encrypt_leaf's plaintext."""
    return (
        c_leaf.to_bytes(4, "big")
        + len(identifier).to_bytes(2, "big")
        + identifier
        + len(value).to_bytes(4, "big")
        + value
    )


def unpack_leaf(content: bytes) -> Tuple[int, bytes, bytes]:
    """Return (c_leaf, identifier, value) from a plaintext leaf `content`."""
    c_leaf = int.from_bytes(content[0:4], "big")
    id_len = int.from_bytes(content[4:6], "big")
    off = 6 + id_len
    identifier = content[6:off]
    val_len = int.from_bytes(content[off:off + 4], "big")
    off += 4
    value = content[off:off + val_len]
    return c_leaf, identifier, value


def encode_leaf(
    k_data: bytes,
    entry_key_: bytes,
    entry_type: Union[str, bytes],
    c_leaf: int,
    identifier: bytes,
    value: bytes,
    nonce: bytes = None,
) -> Tuple[bytes, bytes, bytes]:
    """(nonce, tag, ct) for the current leaf mode — plaintext (b"", b"", content) or
    the AEAD blob. Mirrors core service.py _encode_leaf."""
    if WARD_PLAINTEXT_LEAVES:
        return b"", b"", pack_leaf(c_leaf, identifier, value)
    return encrypt_leaf(k_data, entry_key_, entry_type, c_leaf, identifier, value, nonce)


def decode_leaf(
    k_data: bytes,
    entry_key_: bytes,
    entry_type: Union[str, bytes],
    nonce: bytes,
    tag: bytes,
    ct: bytes,
) -> Tuple[int, bytes, bytes]:
    """(c_leaf, identifier, value) for the current leaf mode. Mirrors core _decode_leaf."""
    if WARD_PLAINTEXT_LEAVES:
        return unpack_leaf(ct)
    return decrypt_leaf(k_data, entry_key_, entry_type, nonce, tag, ct)
