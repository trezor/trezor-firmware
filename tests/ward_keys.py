# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""TEST-ONLY oracle for the WARD keyed path.

**A real host cannot do this and must never try.** Deriving `entry_key` needs the seed,
which is exactly what a host does not have -- that is the property the keyed path buys,
and it is why `trezorlib.ward` deliberately has no derivation in it. This module exists
only so tests can assert that the device asked for the *right* opaque key rather than
merely some 32 bytes.

Kept in `tests/` rather than `trezorlib/` on purpose: the reference implementation put
its equivalent in a host-side tree object that then held `K_path`, which conflated "the
store" with "the deriver" and made it easy to write host code that could not exist in
production.

Mirrors `core/src/apps/ward/keys.py`; the shared vectors are pinned in
`core/tests/test_apps.ward.py`.
"""

from __future__ import annotations

import hashlib
import hmac

__all__ = [
    "bip39_seed",
    "slip21_key",
    "derive_k_path",
    "derive_k_ident",
    "derive_k_data",
    "derive_ward_id",
    "derive_k_mac",
    "root_mac",
    "entry_key",
    "open_content",
    "open_identity",
    "unpack_content",
    "unpack_identity",
]


def bip39_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """BIP-39 seed: PBKDF2-HMAC-SHA512(mnemonic, "mnemonic" + passphrase, 2048)."""
    return hashlib.pbkdf2_hmac(
        "sha512", mnemonic.encode(), b"mnemonic" + passphrase.encode(), 2048, 64
    )


def slip21_key(seed: bytes, path: list[bytes]) -> bytes:
    """SLIP-0021 symmetric derivation; returns the node's 32-byte key (data[32:64])."""
    data = hmac.new(b"Symmetric key seed", seed, hashlib.sha512).digest()
    for label in path:
        h = hmac.new(data[0:32], b"\x00", hashlib.sha512)
        h.update(label)
        data = h.digest()
    return data[32:64]


def derive_k_path(seed: bytes) -> bytes:
    """K_path = SLIP21(seed, ["ward", "K_path"])."""
    return slip21_key(seed, [b"ward", b"K_path"])


def derive_ward_id(seed: bytes) -> bytes:
    """The handle the WM knows this wallet by."""
    return slip21_key(seed, [b"ward", b"ward_id"])


def derive_k_mac(seed: bytes) -> bytes:
    """K_mac, which MACs the root the WM attests. A real host has neither this nor a way
    to obtain it -- that is what stops the WM fabricating state."""
    return slip21_key(seed, [b"ward", b"K_mac"])


def root_mac(k_mac: bytes, ward_id: bytes, counter: int, root) -> bytes:
    """HMAC(K_mac, b"WARD ROOT v1" || ward_id || counter(4B BE) || root).

    An absent root -- the empty tree -- macs the all-zero root, so "empty" is still bound
    to a counter rather than being unbound.
    """
    return hmac.new(
        k_mac,
        b"WARD ROOT v1"
        + ward_id
        + counter.to_bytes(4, "big")
        + (root if root is not None else bytes(32)),
        hashlib.sha256,
    ).digest()


def derive_k_ident(seed: bytes, key_type: str = "address") -> bytes:
    """K_ident(key_type) = SLIP21(seed, ["ward", "K_ident", key_type])."""
    return slip21_key(seed, [b"ward", b"K_ident", key_type.encode()])


def derive_k_data(seed: bytes, key_type: str = "address") -> bytes:
    """K_data(key_type) = SLIP21(seed, ["ward", "K_data", key_type])."""
    return slip21_key(seed, [b"ward", b"K_data", key_type.encode()])


def entry_key(
    k_path: bytes,
    app_id: str,
    identifier: bytes,
    key_type: str = "address",
    device_id: int = 0,
) -> bytes:
    """entry_key = HMAC-SHA256(K_path, app_id || 0x00 || key_type || 0x00 || dev || id)."""
    scope = app_id.encode() + b"\x00" + key_type.encode() + b"\x00" + bytes([device_id])
    return hmac.new(k_path, scope + identifier, hashlib.sha256).digest()


# --- opening a sealed part -------------------------------------------------------
# Also test-only. A real host holds neither K_ident nor K_data and cannot open a part;
# these exist so a test can prove that what the device sealed really does contain what it
# claimed, and that the AAD really is bound to the path.

_AAD_IDENTITY = b"\x03"
_AAD_CONTENT = b"\x02"


def _open(key: bytes, domain: bytes, entry_key_: bytes, key_type: str, part) -> bytes:
    """Open a sealed part. `part` is a LeafContent.encrypted / LeafIdentity.encrypted."""
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

    aad = domain + entry_key_ + key_type.encode()
    # `cryptography` expects the tag appended to the ciphertext; the wire keeps them apart
    return ChaCha20Poly1305(key).decrypt(part.nonce, part.ct + part.tag, aad)


def open_identity(k_ident: bytes, entry_key_: bytes, key_type: str, part) -> bytes:
    return _open(k_ident, _AAD_IDENTITY, entry_key_, key_type, part)


def open_content(k_data: bytes, entry_key_: bytes, key_type: str, part) -> bytes:
    return _open(k_data, _AAD_CONTENT, entry_key_, key_type, part)


def unpack_identity(pt: bytes) -> tuple[bytes, bytes, int]:
    """len16(identifier) || identifier || len8(app_id) || app_id || device_id(1B)."""
    id_len = int.from_bytes(pt[0:2], "big")
    off = 2 + id_len
    identifier = pt[2:off]
    aid_len = pt[off]
    off += 1
    app_id = pt[off : off + aid_len]
    off += aid_len
    return identifier, app_id, pt[off]


def unpack_content(pt: bytes) -> tuple[int, bytes]:
    """C_leaf(4B BE) || len32(value) || value."""
    c_leaf = int.from_bytes(pt[0:4], "big")
    val_len = int.from_bytes(pt[4:8], "big")
    return c_leaf, pt[8 : 8 + val_len]
