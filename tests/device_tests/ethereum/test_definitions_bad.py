from __future__ import annotations

from hashlib import sha256

import pytest

from trezorlib import ethereum, messages, models
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import DefinitionType
from trezorlib.tools import parse_path

from ...definitions import (
    make_eth_erc7730_display_format,
    make_eth_network,
    make_eth_token,
    make_payload,
    sign_payload,
)
from .test_definitions import (
    DEFAULT_ERC20_PARAMS,
    ERC20_FAKE_ADDRESS,
    get_clear_signing_sign_tx_params,
)

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


def _fails_network(session: Session, network: bytes, match: str) -> None:
    with pytest.raises(TrezorFailure, match=match):
        ethereum.get_address(
            session,
            parse_path("m/44h/666666h/0h"),
            show_display=False,
            encoded_network=network,
        )


def _fails_token(session: Session, token: bytes, match: str) -> None:
    with pytest.raises(TrezorFailure, match=match):
        params = DEFAULT_ERC20_PARAMS.copy()
        params.update(to=ERC20_FAKE_ADDRESS)
        ethereum.sign_tx(
            session,
            **params,
            definitions=messages.EthereumDefinitions(encoded_tokens=[token]),
        )


def _fails_erc7730_display_format(
    session: Session, erc7730_display_format: bytes, match: str
) -> None:
    with pytest.raises(TrezorFailure, match=match):
        ethereum.sign_tx(
            session,
            **get_clear_signing_sign_tx_params(),
            definitions=messages.EthereumDefinitions(
                encoded_erc7730_display_format=erc7730_display_format,
            ),
        )


def _make_token_payload(
    timestamp: int = 0xFFFF_FFFF,
    message: messages.EthereumTokenInfo | bytes = make_eth_token(),
) -> bytes:
    return make_payload(
        data_type=DefinitionType.ETHEREUM_TOKEN,
        message=message,
        timestamp=timestamp,
    )


def _make_erc7730_payload(
    timestamp: int = 0xFFFF_FFFF,
    message: messages.EthereumERC7730DisplayFormatInfo | bytes | None = None,
) -> bytes:
    if message is None:
        message = make_eth_erc7730_display_format()
    return make_payload(
        data_type=DefinitionType.ETHEREUM_ERC7730_DISPLAY_FORMAT,
        message=message,
        timestamp=timestamp,
    )


def _cases(session: Session) -> list[tuple]:
    cases: list[tuple] = [
        (make_payload, _fails_network),
        (_make_token_payload, _fails_token),
    ]
    if session.model in models.CORE_MODELS:
        cases.append((_make_erc7730_payload, _fails_erc7730_display_format))
    return cases


def test_short_message(session: Session) -> None:
    for _, check in _cases(session):
        check(session, b"\x00", "Invalid definition")


def test_mangled_signature(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        proof, signature = sign_payload(payload, [])
        bad_signature = signature[:-1] + b"\xff"
        check(session, payload + proof + bad_signature, "Invalid definition signature")


def test_not_enough_signatures(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        proof, signature = sign_payload(payload, [], threshold=1)
        check(session, payload + proof + signature, "Invalid definition signature")


def test_missing_signature(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        proof, _ = sign_payload(payload, [])
        check(session, payload + proof, "Invalid definition")


def test_mangled_payload(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        proof, signature = sign_payload(payload, [])
        bad_payload = payload[:-1] + b"\xff"
        check(session, bad_payload + proof + signature, "Invalid definition signature")


def test_proof_length_mismatch(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        _, signature = sign_payload(payload, [])
        bad_proof = b"\x01"
        check(session, payload + bad_proof + signature, "Invalid definition")


def test_bad_proof(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        proof, signature = sign_payload(payload, [sha256(b"x").digest()])
        bad_proof = proof[:-1] + b"\xff"
        check(session, payload + bad_proof + signature, "Invalid definition signature")


def test_trimmed_proof(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        proof, signature = sign_payload(payload, [])
        bad_proof = proof[:-1]
        check(session, payload + bad_proof + signature, "Invalid definition")


def test_bad_prefix(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        payload = b"trzd2" + payload[5:]
        proof, signature = sign_payload(payload, [])
        check(session, payload + proof + signature, "Invalid definition")


def test_bad_type(session: Session) -> None:
    cases = [
        (DefinitionType.ETHEREUM_TOKEN, make_eth_token(), _fails_network),
        (DefinitionType.ETHEREUM_NETWORK, make_eth_network(), _fails_token),
    ]
    if session.model in models.CORE_MODELS:
        cases += [
            (
                DefinitionType.ETHEREUM_ERC7730_DISPLAY_FORMAT,
                make_eth_erc7730_display_format(),
                _fails_network,
            ),
            (
                DefinitionType.ETHEREUM_ERC7730_DISPLAY_FORMAT,
                make_eth_erc7730_display_format(),
                _fails_token,
            ),
            (
                DefinitionType.ETHEREUM_TOKEN,
                make_eth_token(),
                _fails_erc7730_display_format,
            ),
            (
                DefinitionType.ETHEREUM_NETWORK,
                make_eth_network(),
                _fails_erc7730_display_format,
            ),
        ]
    for data_type, message, check in cases:
        payload = make_payload(data_type=data_type, message=message)
        proof, signature = sign_payload(payload, [])
        check(session, payload + proof + signature, "Definition type mismatch")


def test_outdated(session: Session) -> None:
    for make, check in _cases(session):
        payload = make(timestamp=0)
        proof, signature = sign_payload(payload, [])
        check(session, payload + proof + signature, "Definition is outdated")


def test_malformed_protobuf(session: Session) -> None:
    for make, check in _cases(session):
        payload = make(message=b"\x00")
        proof, signature = sign_payload(payload, [])
        check(session, payload + proof + signature, "Invalid definition")


def test_protobuf_mismatch(session: Session) -> None:
    cases = [
        (DefinitionType.ETHEREUM_NETWORK, make_eth_token(), _fails_network),
        (DefinitionType.ETHEREUM_TOKEN, make_eth_network(), _fails_token),
    ]
    if session.model in models.CORE_MODELS:
        cases += [
            (
                DefinitionType.ETHEREUM_NETWORK,
                make_eth_erc7730_display_format(),
                _fails_network,
            ),
            (
                DefinitionType.ETHEREUM_TOKEN,
                make_eth_erc7730_display_format(),
                _fails_token,
            ),
            (
                DefinitionType.ETHEREUM_ERC7730_DISPLAY_FORMAT,
                make_eth_token(),
                _fails_erc7730_display_format,
            ),
            (
                DefinitionType.ETHEREUM_ERC7730_DISPLAY_FORMAT,
                make_eth_network(),
                _fails_erc7730_display_format,
            ),
        ]
    for data_type, message, check in cases:
        payload = make_payload(data_type=data_type, message=message)
        proof, signature = sign_payload(payload, [])
        check(session, payload + proof + signature, "Invalid definition")


def test_trailing_garbage(session: Session) -> None:
    for make, check in _cases(session):
        payload = make()
        proof, signature = sign_payload(payload, [])
        check(session, payload + proof + signature + b"\x00", "Invalid definition")
