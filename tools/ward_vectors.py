#!/usr/bin/env python3
"""Generate canonical, public-test-seed WARD v2 interoperability vectors."""

from __future__ import annotations

import argparse
import hmac
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from trezorlib import ward_crypto as wc
from trezorlib.ward_protocol import (
    EMPTY_ROOT,
    attestation_message,
    genesis_nonce,
    transition_message,
)

ROOT = Path(__file__).resolve().parent.parent


def vectors() -> dict:
    seed = bytes.fromhex("11" * 64)
    path, identity, data = (
        wc.derive_k_path(seed),
        wc.derive_k_ident(seed, "address"),
        wc.derive_k_data(seed, "address"),
    )
    preimage = b"WARD PATH v2\x07bitcoin\x07address\x07\x00\x05alice"
    entry_key = hmac.digest(path, preimage, "sha256")
    leaf = wc.LeafBlob(
        "address",
        wc.encode_identity(
            identity, entry_key, "address", b"alice", "bitcoin", 7, nonce=b"Z" * 12
        ),
        wc.encode_content(
            data, entry_key, "address", 5, b"data_alice", nonce=b"Z" * 12
        ),
    )
    commit = wc.commit_of(leaf)

    def part(value):
        return {
            "encoding": value.encoding,
            "nonceHex": value.nonce.hex(),
            "tagHex": value.tag.hex(),
            "bodyHex": value.body.hex(),
        }

    wallet_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("12" * 32))
    ward_id = wallet_key.public_key().public_bytes_raw().hex()
    record = {
        "wardId": ward_id,
        "fromCounter": 0,
        "fromRoot": "",
        "counter": 1,
        "root": wc.leaf_hash_of(entry_key, commit).hex(),
        "mac": "11" * 32,
        "authCommit": "33" * 32,
        "kind": "commit",
        "headNonce": genesis_nonce(ward_id),
    }
    record["signature"] = wallet_key.sign(transition_message(record)).hex()
    wm_key = Ed25519PrivateKey.from_private_bytes(b"AUTHDB QM DEBUG KEY SEED v1 ....")
    attestation = {
        "wardId": "ab" * 32,
        "nonce": "cd" * 32,
        "counter": 7,
        "mac": "bb" * 32,
        "timestamp": 1700000000,
        "headNonce": "68" * 32,
    }
    message = attestation_message(
        attestation["wardId"],
        attestation["nonce"],
        7,
        attestation["mac"],
        1700000000,
        attestation["headNonce"],
    )
    return {
        "generatedBy": "tools/ward_vectors.py",
        "version": 2,
        "seedHex": seed.hex(),
        "emptyRoot": EMPTY_ROOT.hex(),
        "pathKey": path.hex(),
        "identityKey": identity.hex(),
        "dataKey": data.hex(),
        "identityPreimage": preimage.hex(),
        "entryKey": entry_key.hex(),
        "leaf": {
            "entryKey": entry_key.hex(),
            "keyType": "address",
            "identity": part(leaf.identity),
            "content": part(leaf.content),
        },
        "commit": commit.hex(),
        "leafHash": wc.leaf_hash_of(entry_key, commit).hex(),
        "transition": record,
        "transitionMessage": transition_message(record).hex(),
        "attestation": attestation,
        "attestationMessage": message.hex(),
        "attestationSignature": wm_key.sign(message).hex(),
        "managerPublicKey": wm_key.public_key().public_bytes_raw().hex(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = [ROOT / "common/tests/fixtures/ward/protocol_v2.json"]
    if args.suite:
        files.append(args.suite / "packages/wardd/mocks/mockProtocolV2.json")
    content = json.dumps(vectors(), indent=4) + "\n"
    for path in files:
        if args.check:
            if not path.exists() or path.read_text() != content:
                return 1
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
