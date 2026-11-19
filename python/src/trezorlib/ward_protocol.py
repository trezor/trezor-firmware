"""Canonical signed WARD transition format shared by the manager and tests."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

EMPTY_ROOT = hashlib.sha256(b"\x02").digest()
ATTEST_DOMAIN = b"WARD ATTEST v1"
ATTEST_VERSION = 1
TRANSITION_DOMAIN = b"WARD WM TRANSITION v1"
FINAL_DOMAIN = b"WARD FINAL v1"


def attestation_message(
    ward_id: str,
    nonce: str,
    counter: int,
    mac: str | None,
    timestamp: int,
) -> bytes:
    return (
        ATTEST_DOMAIN
        + bytes([ATTEST_VERSION])
        + bytes.fromhex(nonce + ward_id)
        + counter.to_bytes(4, "big")
        + (bytes.fromhex(mac) if mac else bytes(32))
        + timestamp.to_bytes(8, "big")
    )


def root_bytes(value: str | None) -> bytes:
    return bytes.fromhex(value) if value else EMPTY_ROOT


def transition_body(record: Mapping[str, Any]) -> bytes:
    """The transition fields shared by the wallet and manager signatures."""
    kind = {"commit": b"\x00", "revert": b"\x01"}[record["kind"]]
    return (
        kind
        + bytes.fromhex(record["wardId"])
        + record["fromCounter"].to_bytes(4, "big")
        + root_bytes(record["fromRoot"])
        + record["counter"].to_bytes(4, "big")
        + root_bytes(record["root"])
        + bytes.fromhex(record["mac"])
        + bytes.fromhex(record["authCommit"])
    )


def transition_message(record: Mapping[str, Any]) -> bytes:
    """The bytes the wallet signs to authorize a transition."""
    return TRANSITION_DOMAIN + transition_body(record)


def finalization_message(record: Mapping[str, Any], timestamp: int) -> bytes:
    """The bytes the manager signs after accepting a transition at `timestamp`."""
    return FINAL_DOMAIN + transition_body(record) + timestamp.to_bytes(8, "big")
