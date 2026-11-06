"""Canonical signed WARD transition format shared by the manager and tests."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

EMPTY_ROOT = hashlib.sha256(b"\x03").digest()
TRANSITION_DOMAIN = b"WARD WM TRANSITION v2"


def genesis_nonce(ward_id: str) -> str:
    return hashlib.sha256(b"WARD GENESIS v2" + bytes.fromhex(ward_id)).hexdigest()


def attestation_message(
    ward_id: str,
    nonce: str,
    counter: int,
    mac: str | None,
    timestamp: int,
    head_nonce: str,
) -> bytes:
    return (
        b"WARD ATTEST v2\x02"
        + bytes.fromhex(nonce + ward_id)
        + counter.to_bytes(4, "big")
        + (bytes.fromhex(mac) if mac else bytes(32))
        + timestamp.to_bytes(8, "big")
        + bytes.fromhex(head_nonce)
    )


def root_bytes(value: str | None) -> bytes:
    return bytes.fromhex(value) if value else EMPTY_ROOT


def transition_message(record: Mapping[str, Any]) -> bytes:
    kind = {"commit": b"\x00", "revert": b"\x01"}[record.get("kind", "commit")]
    return (
        TRANSITION_DOMAIN
        + kind
        + bytes.fromhex(record["wardId"])
        + record["fromCounter"].to_bytes(4, "big")
        + root_bytes(record["fromRoot"])
        + record["counter"].to_bytes(4, "big")
        + root_bytes(record["root"])
        + bytes.fromhex(record["mac"])
        + bytes.fromhex(record["authCommit"])
        + bytes.fromhex(record["headNonce"])
    )
