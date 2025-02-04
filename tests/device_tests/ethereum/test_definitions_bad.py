from __future__ import annotations

from hashlib import sha256

import pytest

from trezorlib import ethereum
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import EthereumDefinitionType
from trezorlib.tools import parse_path

from .common import make_defs, make_network, make_payload, make_token, sign_payload
from .test_definitions import DEFAULT_ERC20_PARAMS, ERC20_FAKE_ADDRESS

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.ethereum,
    pytest.mark.models(skip=["eckhart"]),
]


def fails(session: Session, network: bytes, match: str) -> None:
    with pytest.raises(TrezorFailure, match=match):
        ethereum.get_address(
            session,
            parse_path("m/44h/666666h/0h"),
            show_display=False,
            encoded_network=network,
        )


def test_short_message(session: Session) -> None:
    fails(session, b"\x00", "Invalid Ethereum definition")


def test_mangled_signature(session: Session) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [])
    bad_signature = signature[:-1] + b"\xff"
    fails(session, payload + proof + bad_signature, "Invalid definition signature")


def test_not_enough_signatures(session: Session) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [], threshold=1)
    fails(session, payload + proof + signature, "Invalid definition signature")


def test_missing_signature(session: Session) -> None:
    payload = make_payload()
    proof, _ = sign_payload(payload, [])
    fails(session, payload + proof, "Invalid Ethereum definition")


def test_mangled_payload(session: Session) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [])
    bad_payload = payload[:-1] + b"\xff"
    fails(session, bad_payload + proof + signature, "Invalid definition signature")


def test_proof_length_mismatch(session: Session) -> None:
    payload = make_payload()
    _, signature = sign_payload(payload, [])
    bad_proof = b"\x01"
    fails(session, payload + bad_proof + signature, "Invalid Ethereum definition")


def test_bad_proof(session: Session) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [sha256(b"x").digest()])
    bad_proof = proof[:-1] + b"\xff"
    fails(session, payload + bad_proof + signature, "Invalid definition signature")


def test_trimmed_proof(session: Session) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [])
    bad_proof = proof[:-1]
    fails(session, payload + bad_proof + signature, "Invalid Ethereum definition")


def test_bad_prefix(session: Session) -> None:
    payload = make_payload()
    payload = b"trzd2" + payload[5:]
    proof, signature = sign_payload(payload, [])
    fails(session, payload + proof + signature, "Invalid Ethereum definition")


def test_bad_type(session: Session) -> None:
    # assuming we expect a network definition
    payload = make_payload(data_type=EthereumDefinitionType.TOKEN, message=make_token())
    proof, signature = sign_payload(payload, [])
    fails(session, payload + proof + signature, "Definition type mismatch")


def test_outdated(session: Session) -> None:
    payload = make_payload(timestamp=0)
    proof, signature = sign_payload(payload, [])
    fails(session, payload + proof + signature, "Definition is outdated")


def test_malformed_protobuf(session: Session) -> None:
    payload = make_payload(message=b"\x00")
    proof, signature = sign_payload(payload, [])
    fails(session, payload + proof + signature, "Invalid Ethereum definition")


def test_protobuf_mismatch(session: Session) -> None:
    payload = make_payload(
        data_type=EthereumDefinitionType.NETWORK, message=make_token()
    )
    proof, signature = sign_payload(payload, [])
    fails(session, payload + proof + signature, "Invalid Ethereum definition")

    payload = make_payload(
        data_type=EthereumDefinitionType.TOKEN, message=make_network()
    )
    proof, signature = sign_payload(payload, [])
    # have to do this manually to invoke a method that eats token definitions
    with pytest.raises(TrezorFailure, match="Invalid Ethereum definition"):
        params = DEFAULT_ERC20_PARAMS.copy()
        params.update(to=ERC20_FAKE_ADDRESS)
        ethereum.sign_tx(
            session,
            **params,
            definitions=make_defs(None, payload + proof + signature),
        )


def test_trailing_garbage(session: Session) -> None:
    payload = make_payload()
    proof, signature = sign_payload(payload, [])
    fails(session, payload + proof + signature + b"\x00", "Invalid Ethereum definition")
