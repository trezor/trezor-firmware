from __future__ import annotations

from typing import Optional, Protocol, Tuple


class QuotaManager(Protocol):
    """The WARD Manager (freshness authority), external to the device.

    sign_attestation(wallet_id, nonce, counter, mac) returns the WM's Ed25519
    signature over b"WARD ATTEST v1"||version||nonce||wallet_id||counter||mac --
    the freshness attestation WARDIngestAttestation verifies (bootstrap/refresh).

    sign_final(wallet_id, counter, mac) returns the WM's Ed25519 signature over
    b"WARD FINAL v1"||wallet_id||counter||mac -- the final attestation
    WARDConfirmCommit verifies before the device advances its counter.
    """

    def sign_attestation(
        self, wallet_id: bytes, nonce: bytes, counter: int, mac: bytes
    ) -> bytes: ...

    def sign_final(self, wallet_id: bytes, counter: int, mac: bytes) -> bytes: ...


class EvoluStore(Protocol):
    """The untrusted host store holding the attested root blob (Evolu's role)."""

    def get_root(self) -> Tuple[Optional[bytes], int, Optional[bytes]]:
        """Return (root, counter, root_mac); root/root_mac None for a fresh wallet."""
        ...

    def put_root(self, root: bytes, counter: int, root_mac: bytes) -> None:
        """Persist a freshly attested (root, counter, root_mac)."""
        ...
