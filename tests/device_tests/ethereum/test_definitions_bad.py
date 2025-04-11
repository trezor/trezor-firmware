from __future__ import annotations

from hashlib import sha256

import pytest

from trezorlib import ethereum
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import DefinitionType
from trezorlib.tools import parse_path

from ...definitions import (
    make_eth_defs,
    make_eth_network,
    make_eth_token,
    make_payload,
    sign_payload,
)
from .test_definitions import DEFAULT_ERC20_PARAMS, ERC20_FAKE_ADDRESS

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


def fails(client: Client, network: bytes, match: str) -> None:
    with pytest.raises(TrezorFailure, match=match):
        ethereum.get_address(
            client,
            parse_path("m/44h/666666h/0h"),
            show_display=False,
            encoded_network=network,
        )


def test_short_message(client: Client) -> None:
    fails(client, b"\x00", "Invalid definition")


def test_mangled_signature(client: Client) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [])
    bad_signature = signature[:-1] + b"\xff"
    fails(client, payload + proof + bad_signature, "Invalid definition signature")


def test_not_enough_signatures(client: Client) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [], threshold=1)
    fails(client, payload + proof + signature, "Invalid definition signature")


def test_missing_signature(client: Client) -> None:
    payload = make_payload()
    proof, _ = sign_payload(payload, [])
    fails(client, payload + proof, "Invalid definition")


def test_mangled_payload(client: Client) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [])
    bad_payload = payload[:-1] + b"\xff"
    fails(client, bad_payload + proof + signature, "Invalid definition signature")


def test_proof_length_mismatch(client: Client) -> None:
    payload = make_payload()
    _, signature = sign_payload(payload, [])
    bad_proof = b"\x01"
    fails(client, payload + bad_proof + signature, "Invalid definition")


def test_bad_proof(client: Client) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [sha256(b"x").digest()])
    bad_proof = proof[:-1] + b"\xff"
    fails(client, payload + bad_proof + signature, "Invalid definition signature")


def test_trimmed_proof(client: Client) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [])
    bad_proof = proof[:-1]
    fails(client, payload + bad_proof + signature, "Invalid definition")


def test_bad_prefix(client: Client) -> None:
    payload = make_payload()
    payload = b"trzd2" + payload[5:]
    proof, signature = sign_payload(payload, [])
    fails(client, payload + proof + signature, "Invalid definition")


def test_bad_type(client: Client) -> None:
    # assuming we expect a network definition
    payload = make_payload(
        data_type=DefinitionType.ETHEREUM_TOKEN, message=make_eth_token()
    )
    proof, signature = sign_payload(payload, [])
    fails(client, payload + proof + signature, "Definition type mismatch")


def test_outdated(client: Client) -> None:
    payload = make_payload(timestamp=0)
    proof, signature = sign_payload(payload, [])
    fails(client, payload + proof + signature, "Definition is outdated")


def test_malformed_protobuf(client: Client) -> None:
    payload = make_payload(message=b"\x00")
    proof, signature = sign_payload(payload, [])
    fails(client, payload + proof + signature, "Invalid definition")


def test_protobuf_mismatch(client: Client) -> None:
    payload = make_payload(
        data_type=DefinitionType.ETHEREUM_NETWORK, message=make_eth_token()
    )
    proof, signature = sign_payload(payload, [])
    fails(client, payload + proof + signature, "Invalid definition")

    payload = make_payload(
        data_type=DefinitionType.ETHEREUM_TOKEN, message=make_eth_network()
    )
    proof, signature = sign_payload(payload, [])
    # have to do this manually to invoke a method that eats token definitions
    with pytest.raises(TrezorFailure, match="Invalid definition"):
        params = DEFAULT_ERC20_PARAMS.copy()
        params.update(to=ERC20_FAKE_ADDRESS)
        ethereum.sign_tx(
            client,
            **params,
            definitions=make_eth_defs(None, payload + proof + signature),
        )


def test_trailing_garbage(client: Client) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [])
    fails(client, payload + proof + signature + b"\x00", "Invalid definition")
