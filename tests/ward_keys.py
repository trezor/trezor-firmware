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
import os

__all__ = [
    "bip39_seed",
    "slip21_key",
    "derive_k_path",
    "derive_k_ident",
    "derive_k_data",
    "derive_ward_id",
    "derive_k_auth",
    "auth_commit",
    "EMPTY_ROOT",
    "entry_key",
    "open_content",
    "open_identity",
    "unpack_content",
    "unpack_identity",
    "pack_content",
    "pack_identity",
    "seal_content",
    "seal_identity",
    "value_digest",
    "wm_sig",
    "verify_wm_sig",
    "head_init_sig",
    "verify_head_init_sig",
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


def derive_k_sig(seed: bytes) -> bytes:
    """K_sig = SLIP21(seed, [b"ward", b"K_sig"]) -- the Ed25519 secret behind ward_id."""
    return slip21_key(seed, [b"ward", b"K_sig"])


def derive_ward_id(seed: bytes) -> bytes:
    """ward_id = ed25519.publickey(K_sig).

    The WM-facing handle IS the key that verifies a transition, so there is no second
    per-wallet value to keep in step. See `apps.ward.keys.derive_ward_id`.
    """
    from trezorlib import _ed25519

    return _ed25519.publickey_unsafe(derive_k_sig(seed))


# The empty-tree stand-in used wherever a root appears in a preimage: sha256(0x02),
# domain-separated from the leaf/internal/value tags. Mirrors apps.ward.attest.EMPTY_ROOT.
EMPTY_ROOT = hashlib.sha256(b"\x02").digest()


def _root_or_empty(root):
    return root if root is not None else EMPTY_ROOT


def derive_k_auth(seed: bytes) -> bytes:
    """K_auth, which authorises a transition. Every device of the wallet holds it."""
    return slip21_key(seed, [b"ward", b"K_auth"])


TAG_COMMIT = b"WARD COMMIT v3"
TAG_REVERT = b"WARD REVERT v3"


def transition_preimage(
    tag: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
) -> bytes:
    """len8(tag) || tag || ward_id || from_counter || from_root || to_counter || to_root.

    ONE preimage for both authenticators: the MAC a device checks under K_auth, and the
    Ed25519 signature the WM checks under K_sig. They differ only in tag, key and algorithm.

    ROOTS, NOT MAC HEADS. There used to be a second key, K_mac, whose output these operands
    were -- it kept the WM blind to roots and made a head unforgeable by it. Both are gone: the
    WM holds `(counter, root)` in the clear, and what proves a head real is folding these MACs
    into a chain, not a commitment the WM could not compute.

    An absent root is the empty tree and encodes as EMPTY_ROOT, so the preimage stays
    fixed-width at either end.
    """
    return (
        bytes([len(tag)])
        + tag
        + ward_id
        + from_counter.to_bytes(4, "big")
        + _root_or_empty(from_root)
        + to_counter.to_bytes(4, "big")
        + _root_or_empty(to_root)
    )


def auth_commit(
    k_auth: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
    tag: bytes = TAG_COMMIT,
) -> bytes:
    """HMAC(K_auth, transition_preimage(tag, ward_id, from..., to...))."""
    return hmac.new(
        k_auth,
        transition_preimage(tag, ward_id, from_counter, from_root, to_counter, to_root),
        hashlib.sha256,
    ).digest()


# --- the WM's authorisation, over the SAME BYTES -------------------------------------------
#
# Written out here rather than imported, like everything else in this file: an oracle that shared
# code with the firmware would agree with it by construction and prove nothing.

TAG_WM_HEAD = b"WARD WM COMMIT v5"
TAG_WM_INIT = b"WARD WM INIT v4"
TAG_WM_REVERT = b"WARD WM REVERT v5"
# Without a WM (the MVP build): the step signed for the host.
TAG_STEP = b"WARD STEP v2"


def wm_sig(
    k_sig: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
    tag: bytes = TAG_WM_HEAD,
    session_nonce: bytes = b"",
) -> bytes:
    """The signature a WM checks before letting a head advance: Ed25519 over THE BYTES
    `auth_commit` MACs, under the WM's own tag, followed by the SESSION NONCE -- the round nonce
    the device picked for its latest sync. The WM accepts it only while that is the wallet's
    latest sync, and only after a predecessor check. Enrolment and the MVP's host
    step carry no nonce."""
    from trezorlib import _ed25519

    return _ed25519.signature_unsafe(
        transition_preimage(tag, ward_id, from_counter, from_root, to_counter, to_root)
        + session_nonce,
        k_sig,
        ward_id,
    )


def session_proof(
    k_sig: bytes, ward_id: bytes, challenge: bytes, nonce: bytes
) -> bytes:
    from trezorlib import _ed25519

    return _ed25519.signature_unsafe(
        b"WARD SESSION OPEN v1" + ward_id + challenge + nonce, k_sig, ward_id
    )


def verify_wm_sig(
    ward_id: bytes,
    from_counter: int,
    from_root,
    to_counter: int,
    to_root,
    sig: bytes,
    tag: bytes = TAG_WM_HEAD,
    session_nonce: bytes = b"",
) -> bool:
    """What a WM does: verify with `ward_id` alone, against the session nonce IT holds."""
    from trezorlib import _ed25519

    try:
        _ed25519.checkvalid(
            sig,
            transition_preimage(tag, ward_id, from_counter, from_root, to_counter, to_root)
            + session_nonce,
            ward_id,
        )
        return True
    except Exception:
        return False


def head_init_sig(k_sig: bytes, ward_id: bytes, counter: int, root) -> bytes:
    """Authorises the first head a WM ever holds for this wallet: a self-transition
    `(counter, root) -> (counter, root)` under its own tag, so it can never be replayed as an
    advance. It is not secret; a wiped WM can be enrolled again with it."""
    return wm_sig(k_sig, ward_id, counter, root, counter, root, TAG_WM_INIT)


def verify_head_init_sig(ward_id: bytes, counter: int, root, sig: bytes) -> bool:
    return verify_wm_sig(ward_id, counter, root, counter, root, sig, TAG_WM_INIT)


def derive_k_ident(seed: bytes) -> bytes:
    """K_ident = SLIP21(seed, ["ward", "K_ident"])."""
    return slip21_key(seed, [b"ward", b"K_ident"])


def derive_k_data(seed: bytes) -> bytes:
    """K_data = SLIP21(seed, ["ward", "K_data"])."""
    return slip21_key(seed, [b"ward", b"K_data"])


def pack_identity(identifier: bytes, app_id: str | bytes, device_id: int = 0) -> bytes:
    """leaf_identity = device_id(1B) || len8(app_id) || app_id || identifier; device_id 0 is an
    entry shared by all devices."""
    if isinstance(app_id, str):
        app_id = app_id.encode()
    return bytes([device_id, len(app_id)]) + app_id + identifier


def unpack_identity(pt: bytes) -> tuple[bytes, bytes, int]:
    """Inverse of `pack_identity`: (identifier, app_id, device_id)."""
    app_len = pt[1]
    return pt[2 + app_len :], pt[2 : 2 + app_len], pt[0]


def entry_key(
    k_path: bytes,
    app_id: str,
    identifier: bytes,
    device_id: int = 0,
) -> bytes:
    """entry_key = HMAC-SHA256(K_path, "WARD PATH v1" || leaf_identity)."""
    preimage = b"WARD PATH v1" + pack_identity(identifier, app_id, device_id)
    return hmac.new(k_path, preimage, hashlib.sha256).digest()


def pack_content(entry_type: str, c_leaf: int, value: bytes) -> bytes:
    """leaf_content = len8(entry_type) || entry_type || C_leaf(4B BE) || value."""
    et = entry_type.encode()
    return bytes([len(et)]) + et + c_leaf.to_bytes(4, "big") + value


def unpack_content(pt: bytes) -> tuple[str, int, bytes]:
    """Inverse of `pack_content`: (entry_type, c_leaf, value)."""
    off = 1 + pt[0]
    return pt[1:off].decode(), int.from_bytes(pt[off : off + 4], "big"), pt[off + 4 :]


# --- sealed parts ----------------------------------------------------------------
# Test-only. A real host holds neither K_ident nor K_data and cannot open or build a part;
# these exist so a test can prove what the device sealed, and stage the one state a
# single-device harness cannot reach: a never-synced device whose host already holds an
# entry. Only a test may hold these keys, and only because it knows the device's seed.
#
#   seal(K, d, pt) = 0x01 || nonce(12B) || tag(16B) || AES-256-GCM(K, nonce, aad=d, pt)

DOMAIN_CONTENT = 0x02
DOMAIN_IDENTITY = 0x04


def seal(key: bytes, domain: int, pt: bytes, nonce: bytes | None = None) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = nonce or os.urandom(12)
    sealed = AESGCM(key).encrypt(nonce, pt, bytes([domain]))
    return b"\x01" + nonce + sealed[-16:] + sealed[:-16]


def open_sealed(key: bytes, domain: int, sealed: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    assert sealed[0] == 0x01, "unknown sealing scheme"
    nonce, tag, ct = sealed[1:13], sealed[13:29], sealed[29:]
    return AESGCM(key).decrypt(nonce, ct + tag, bytes([domain]))


def open_identity(k_ident: bytes, sealed_identity: bytes) -> bytes:
    return open_sealed(k_ident, DOMAIN_IDENTITY, sealed_identity)


def open_content(k_data: bytes, sealed_content: bytes) -> bytes:
    return open_sealed(k_data, DOMAIN_CONTENT, sealed_content)


def seal_identity(
    k_ident: bytes, identifier: bytes, app_id: str | bytes, device_id: int = 0
) -> bytes:
    return seal(k_ident, DOMAIN_IDENTITY, pack_identity(identifier, app_id, device_id))


def seal_content(
    k_data: bytes, value: bytes, c_leaf: int = 0, entry_type: str = "address"
) -> bytes:
    return seal(k_data, DOMAIN_CONTENT, pack_content(entry_type, c_leaf, value))


def value_digest(sealed_content: bytes) -> bytes:
    """The leaf commitment: sha256(0x03 || sealed_content)."""
    return hashlib.sha256(b"\x03" + sealed_content).digest()
