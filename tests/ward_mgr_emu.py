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

# Transition-auth domains + empty-root sentinel (must match apps.ward.service). Used
# by the WM CAS to verify a batch-update SigCommit at ingest.
_TAG_COMMIT = b"WARD COMMIT v1"
_TAG_REVERT = b"WARD REVERT v1"
_EMPTY_ROOT_HASH = hashlib.sha256(b"\x03").digest()


class WMConflict(Exception):
    """Raised when a submitted transition does not extend the WM's current head
    (the successor-only CAS compare failed) — the analogue of the HTTP 409 the
    connect client reacts to. Carries the current head so the caller can rebase."""

    def __init__(self, counter: int, root: Optional[bytes], mac: Optional[bytes]) -> None:
        super().__init__("WM head advanced (409): rebase required")
        self.counter = counter
        self.root = root
        self.mac = mac


def _norm_root(r: Optional[bytes]) -> Optional[bytes]:
    """Normalise the empty tree to None (the device sends either None or the 32-byte
    EMPTY_ROOT_HASH sentinel for empty)."""
    return None if (r is None or r == _EMPTY_ROOT_HASH) else r


def _transition_preimage(
    tag: bytes,
    ward_id: bytes,
    from_counter: int,
    from_root: Optional[bytes],
    to_counter: int,
    to_root: Optional[bytes],
) -> bytes:
    fr = _EMPTY_ROOT_HASH if from_root is None else from_root
    tr = _EMPTY_ROOT_HASH if to_root is None else to_root
    return (
        tag
        + ward_id
        + from_counter.to_bytes(4, "big")
        + fr
        + to_counter.to_bytes(4, "big")
        + tr
    )


def _ed25519_sign(message: bytes, qm_seed: bytes) -> bytes:
    pk = _ed25519.publickey_unsafe(qm_seed)
    return _ed25519.signature_unsafe(message, qm_seed, pk)


def sign_wm_attestation(
    nonce: bytes,
    counter: int,
    mac: bytes,
    ward_id: bytes,
    qm_seed: bytes = DEBUG_QM_SEED,
) -> bytes:
    """Produce the WM freshness attestation the device verifies in
    WARDIngestAttestation:

        Ed25519-Sign(qm_seed,
            b"WARD ATTEST v1" || version(1B) || nonce || ward_id || counter(4B BE) || mac)

    The WM signs over the SLIP21-derived ward_id (32B), NOT the local wallet_id.
    """
    message = (
        _WARD_ATTEST_DOMAIN
        + bytes([_WARD_ATTEST_VERSION])
        + nonce
        + ward_id
        + counter.to_bytes(4, "big")
        + mac
    )
    return _ed25519_sign(message, qm_seed)


def sign_ward_update(
    counter: int, mac: bytes, ward_id: bytes, qm_seed: bytes = DEBUG_QM_SEED
) -> bytes:
    """Produce the WM final attestation the device verifies in WARDConfirmCommit:

        Ed25519-Sign(qm_seed, b"WARD FINAL v1" || ward_id || counter(4B BE) || mac)

    The WM signs over the SLIP21-derived ward_id (32B), NOT the local wallet_id.
    """
    message = _WARD_FINAL_DOMAIN + ward_id + counter.to_bytes(4, "big") + mac
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


def device_ward_keys(
    key_type: str = "address",
    mnemonic: str = DEFAULT_MNEMONIC,
    passphrase: str = "",
) -> tuple[bytes, bytes]:
    """Reproduce the device's WARD keys (K_index, K_data(key_type)) from the known
    test seed, so a host-side WARDTree computes the SAME entry_keys / leaf commits
    the device does and its proofs verify on-device. Mirrors
    ``apps.ward.service._derive_k_index`` / ``_derive_k_data`` and
    ``trezorlib.ward_crypto`` (SLIP-21 under m/"ward")."""
    seed = mnemonic_to_seed(mnemonic, passphrase)
    k_index = _slip21_key(seed, [b"ward", b"K_index"])
    k_data = _slip21_key(seed, [b"ward", b"K_data", key_type.encode()])
    return k_index, k_data


class WMEmulator:
    """A full in-harness WARD Manager: it signs freshness attestations AND, using
    the known test seed, reproduces the device-keyed ``root_mac`` so it can attest
    a root the device has never computed."""

    def __init__(
        self,
        mnemonic: str = DEFAULT_MNEMONIC,
        passphrase: str = "",
        qm_seed: bytes = DEBUG_QM_SEED,
        verify_sig_commit: bool = False,
    ) -> None:
        self.seed = mnemonic_to_seed(mnemonic, passphrase)
        self.qm_seed = qm_seed
        # Successor-only CAS register + transition history, per ward_id.
        self._heads: dict[bytes, tuple[int, Optional[bytes], Optional[bytes]]] = {}
        self._history: dict[bytes, list[dict]] = {}
        # When True (WARD_KSIG on), verify the device's Ed25519 SigCommit at ingest
        # (F4 pre-filter). The harness derives K_sig from the known test seed; a real
        # WM would hold the ward's provisioned K_sig public key.
        self.verify_sig_commit = verify_sig_commit

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
        self, ward_id: bytes, nonce: bytes, counter: int, mac: bytes
    ) -> bytes:
        """Ed25519 WM freshness attestation over
        b"WARD ATTEST v1"||version||nonce||ward_id||counter||mac."""
        return sign_wm_attestation(nonce, counter, mac, ward_id, self.qm_seed)

    def sign_final(self, ward_id: bytes, counter: int, mac: bytes) -> bytes:
        """Ed25519 WM final attestation over
        b"WARD FINAL v1"||ward_id||counter||mac (verified at WARDConfirmCommit)."""
        return sign_ward_update(counter, mac, ward_id, self.qm_seed)

    # --- successor-only CAS register + transition history (batch-update) --------

    def k_sig_pubkey(self) -> bytes:
        """The ward family's Ed25519 K_sig public key, reproduced from the test seed
        (SLIP-21 m/"ward"/"K_sig"). A real WM would hold this provisioned."""
        return _ed25519.publickey_unsafe(_slip21_key(self.seed, [b"ward", b"K_sig"]))

    def head(self, ward_id: bytes) -> tuple[int, Optional[bytes], Optional[bytes]]:
        """Current authenticated head (counter, root, mac); genesis is (0, None, None)."""
        return self._heads.get(ward_id, (0, None, None))

    def transitions(self, ward_id: bytes) -> list[dict]:
        return list(self._history.get(ward_id, []))

    def auth_commit(
        self,
        ward_id: bytes,
        from_counter: int,
        from_root: Optional[bytes],
        to_counter: int,
        to_root: Optional[bytes],
    ) -> bytes:
        """Mint an `AuthCommit` with the ward family's `K_auth` reproduced from the
        test seed (SLIP-21 m/"ward"/"K_auth"), matching `service.auth_commit` byte for
        byte. Simulates a family peer authorizing a transition; used to build a chain
        for `ward.verify_chain`. Roots default to the empty-tree sentinel."""
        k_auth = _slip21_key(self.seed, [b"ward", b"K_auth"])
        return _hmac_sha256(
            k_auth,
            _transition_preimage(
                _TAG_COMMIT, ward_id, from_counter, from_root, to_counter, to_root
            ),
        )

    def chain_links(self, ward_id: bytes) -> list:
        """Host link-assembly driver: assemble the ordered `verify_chain` links from
        the stored commit history (a real host assembles the same tuples from its
        `WardTransition` lineage). Roots are returned in 32-byte MAC-preimage form
        (empty-tree sentinel for empty). Each link is
        `(from_counter, from_root, to_counter, to_root, auth_commit, sig_commit)`."""
        out = []  # type: list[tuple]
        for t in self.transitions(ward_id):
            if t["kind"] != "commit":
                continue
            fr = t["from_root"] if t["from_root"] is not None else _EMPTY_ROOT_HASH
            tr = t["to_root"] if t["to_root"] is not None else _EMPTY_ROOT_HASH
            out.append(
                (t["from_counter"], fr, t["to_counter"], tr, t["auth"], t["sig_commit"])
            )
        return out

    def submit_transition(
        self,
        ward_id: bytes,
        from_counter: int,
        from_root: Optional[bytes],
        to_counter: int,
        to_root: Optional[bytes],
        mac: Optional[bytes],
        *,
        auth: Optional[bytes] = None,
        sig_commit: Optional[bytes] = None,
        kind: str = "commit",
    ) -> bytes:
        """Successor-only compare-and-swap (ward-design §4.1 step 6, F1 defence in
        depth). Accepts the transition iff it extends the CURRENT head
        (``from == head`` and ``to_counter > from_counter``), advances the head, stores
        a TransitionRecord, and returns the WM final signature over
        ``(ward_id, to_counter, mac)``. Raises :class:`WMConflict` if another writer
        advanced the head first (the caller then rebases and retries).

        When ``verify_sig_commit`` is on (WARD_KSIG), the device's Ed25519 SigCommit is
        verified against the ward's K_sig public key BEFORE the head advances, so an
        unauthorised transition is rejected at ingest (F4) rather than only by a later
        syncing device. Raises ValueError on an invalid SigCommit."""
        cur_c, cur_r, cur_m = self.head(ward_id)
        if from_counter != cur_c or _norm_root(from_root) != _norm_root(cur_r):
            raise WMConflict(cur_c, cur_r, cur_m)
        if to_counter <= from_counter:
            raise WMConflict(cur_c, cur_r, cur_m)

        if self.verify_sig_commit:
            if sig_commit is None:
                raise ValueError("WM requires a SigCommit (WARD_KSIG) but none supplied")
            tag = _TAG_REVERT if kind == "revert" else _TAG_COMMIT
            pre = _transition_preimage(
                tag, ward_id, from_counter, from_root, to_counter, to_root
            )
            try:
                _ed25519.checkvalid(sig_commit, pre, self.k_sig_pubkey())
            except Exception:
                raise ValueError("WM: SigCommit verification failed (unauthorised transition)")

        self._heads[ward_id] = (to_counter, _norm_root(to_root), mac)
        self._history.setdefault(ward_id, []).append(
            {
                "from_counter": from_counter,
                "from_root": _norm_root(from_root),
                "to_counter": to_counter,
                "to_root": _norm_root(to_root),
                "mac": mac,
                "auth": auth,
                "sig_commit": sig_commit,
                "kind": kind,
            }
        )
        return self.sign_final(ward_id, to_counter, mac if mac is not None else ZERO_MAC)


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
    # root_mac stays keyed by the local wallet_id (device-internal MAC); the WM's
    # Ed25519 attestation binds the SLIP21-derived ward_id it gets from the device.
    mac = None if root is None else wm.root_mac(wallet_id, counter, root)

    nonce, ward_id = ward.sync(session)
    assert ward_id is not None
    sig = wm.sign_attestation(
        ward_id, nonce, counter, mac if mac is not None else ZERO_MAC
    )
    ward.ingest_attestation(session, counter, mac, sig)
    return ward.reconcile(session, root)
