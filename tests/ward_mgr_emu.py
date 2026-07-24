"""In-test emulation of the WARD Manager (WM), the external freshness authority.

The device's ``root_mac`` is an HMAC keyed by a secret derived from the device
SEED (``apps.ward.service._derive_mac_key``). A *real* WM never computes it — it
only signs freshness (see ``trezorlib.authdb.QuotaManager``), and the untrusted
host store (Evolu) replays the device-produced ``(root, root_mac)``. But device
tests use the known ``"all all all ..."`` mnemonic, so the harness can reproduce
that secret and mint a valid ``root_mac`` for ANY tree. That lets a test drive a
full initial synchronization in which the device adopts a pre-populated tree it
has never written itself.

Everything here mirrors the firmware byte for byte:
  - ``core/src/apps/common/seed.py``      Slip21Node (SLIP-0021)
  - ``core/src/apps/ward/service.py``     _derive_mac_key / _compute_mac
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import unicodedata
from typing import TYPE_CHECKING, Optional

from trezorlib import _ed25519, ward
from trezorlib.ward import ZERO_MAC

if TYPE_CHECKING:
    from trezorlib.authdb_tree import WARDTree
    from trezorlib.transport.session import Session

# The default device-test mnemonic (tests/conftest.py: " ".join(["all"] * 12)).
DEFAULT_MNEMONIC = " ".join(["all"] * 12)

# SLIP-21 path the firmware folds into the MAC base key (service._derive_mac_key).
_MAC_SLIP21_PATH = [b"AUTHDB MAC v1", b"root_mac"]

# ---------------------------------------------------------------------------
# Debug WM signing. This is the WARD Manager's ROLE, not a device-client call,
# and it forges attestations with a well-known debug key accepted ONLY by debug
# firmware. It lives here (test harness) rather than in trezorlib/ward.py (the
# production device client) so no debug-only forgery ships in the client library.
# ---------------------------------------------------------------------------

# Well-known DEBUG WM/QM Ed25519 seed. Its public key is provisioned as
# _WM_PUBKEY_DEBUG in core/src/apps/ward/service.py; real firmware verifies the
# production key. Used by tests to stand in for the WARD Manager's signatures.
DEBUG_QM_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."

# WARD attestation domains (must match apps.ward.service).
_WARD_FINAL_DOMAIN = b"WARD FINAL v1"
_WARD_ATTEST_DOMAIN = b"WARD ATTEST v1"
_WARD_ATTEST_VERSION = 1


def _ed25519_sign(message: bytes, qm_seed: bytes) -> bytes:
    pk = _ed25519.publickey_unsafe(qm_seed)
    return _ed25519.signature_unsafe(message, qm_seed, pk)


def sign_wm_attestation(
    nonce: bytes,
    counter: int,
    mac: bytes,
    wallet_id: bytes,
    qm_seed: bytes = DEBUG_QM_SEED,
) -> bytes:
    """Produce the WM freshness attestation the device verifies in
    WARDIngestAttestation:

        Ed25519-Sign(qm_seed,
            b"WARD ATTEST v1" || version(1B) || nonce || wallet_id || counter(4B BE) || mac)
    """
    message = (
        _WARD_ATTEST_DOMAIN
        + bytes([_WARD_ATTEST_VERSION])
        + nonce
        + wallet_id
        + counter.to_bytes(4, "big")
        + mac
    )
    return _ed25519_sign(message, qm_seed)


def sign_ward_update(
    counter: int, mac: bytes, wallet_id: bytes, qm_seed: bytes = DEBUG_QM_SEED
) -> bytes:
    """Produce the WM final attestation the device verifies in WARDConfirmCommit:

        Ed25519-Sign(qm_seed, b"WARD FINAL v1" || wallet_id || counter(4B BE) || mac)
    """
    message = _WARD_FINAL_DOMAIN + wallet_id + counter.to_bytes(4, "big") + mac
    return _ed25519_sign(message, qm_seed)


def _hmac_sha512(key: bytes, msg: bytes) -> bytes:
    return _hmac.new(key, msg, hashlib.sha512).digest()


def _hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return _hmac.new(key, msg, hashlib.sha256).digest()


def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """BIP-39 mnemonic -> 64-byte seed (PBKDF2-HMAC-SHA512, 2048 rounds)."""
    m = unicodedata.normalize("NFKD", mnemonic).encode()
    salt = unicodedata.normalize("NFKD", "mnemonic" + passphrase).encode()
    return hashlib.pbkdf2_hmac("sha512", m, salt, 2048, dklen=64)


def _slip21_key(seed: bytes, path: list[bytes]) -> bytes:
    """SLIP-21 symmetric key at ``path`` (matches apps.common.seed.Slip21Node)."""
    data = _hmac_sha512(b"Symmetric key seed", seed)
    for label in path:
        data = _hmac_sha512(data[:32], b"\x00" + label)
    return data[32:64]


class WMEmulator:
    """A full in-harness WARD Manager: it signs freshness attestations AND, using
    the known test seed, reproduces the device-keyed ``root_mac`` so it can attest
    a root the device has never computed."""

    def __init__(
        self,
        mnemonic: str = DEFAULT_MNEMONIC,
        passphrase: str = "",
        qm_seed: bytes = DEBUG_QM_SEED,
    ) -> None:
        self.seed = mnemonic_to_seed(mnemonic, passphrase)
        self.qm_seed = qm_seed

    def _mac_key(self, wallet_id: bytes) -> bytes:
        base_key = _slip21_key(self.seed, _MAC_SLIP21_PATH)
        return _hmac_sha256(base_key, wallet_id)

    def root_mac(self, wallet_id: bytes, counter: int, root: bytes) -> bytes:
        """The device-keyed root MAC: HMAC(mac_key, wallet_id||counter(4B BE)||root)."""
        return _hmac_sha256(
            self._mac_key(wallet_id),
            wallet_id + counter.to_bytes(4, "big") + root,
        )

    def sign_attestation(
        self, wallet_id: bytes, nonce: bytes, counter: int, mac: bytes
    ) -> bytes:
        """Ed25519 WM freshness attestation over
        b"WARD ATTEST v1"||version||nonce||wallet_id||counter||mac."""
        return sign_wm_attestation(nonce, counter, mac, wallet_id, self.qm_seed)

    def sign_final(self, wallet_id: bytes, counter: int, mac: bytes) -> bytes:
        """Ed25519 WM final attestation over
        b"WARD FINAL v1"||wallet_id||counter||mac (verified at WARDConfirmCommit)."""
        return sign_ward_update(counter, mac, wallet_id, self.qm_seed)


def wm_initial_sync(
    session: "Session",
    wm: WMEmulator,
    tree: "WARDTree",
    counter: int,
    wallet_id: Optional[bytes] = None,
) -> tuple[int, Optional[bytes], Optional[bytes]]:
    """Positive path: the WM attests ``tree`` at ``counter`` and the device adopts
    it via the sync round (WARDSync -> WARDIngestAttestation -> WARDReconcile).
    Returns ``(counter, adopted_root, root_mac)``."""
    if wallet_id is None:
        _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None

    root = None if tree.is_empty() else tree.get_root_hash()
    mac = None if root is None else wm.root_mac(wallet_id, counter, root)

    nonce = ward.sync(session)
    sig = wm.sign_attestation(
        wallet_id, nonce, counter, mac if mac is not None else ZERO_MAC
    )
    ward.ingest_attestation(session, counter, mac, sig)
    return ward.reconcile(session, root)
