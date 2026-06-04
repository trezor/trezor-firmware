from __future__ import annotations

from hashlib import sha256

import pytest

from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from . import ethereum_ext
from .definitions import (
    make_eth_display_format,
    make_eth_network,
    make_eth_token,
    make_payload,
    sign_payload,
)
from .generated import messages as ethereum_messages
from .test_definitions import (
    DEFAULT_ERC20_PARAMS,
    ERC20_FAKE_ADDRESS,
    get_clear_signing_sign_tx_params,
)


def _fails_network(
    session: Session, instance_id: int, network: bytes, match: str
) -> None:
    with pytest.raises(TrezorFailure, match=match):
        ethereum_ext.get_address(
            session,
            instance_id,
            parse_path("m/44h/666666h/0h"),
            show_display=False,
            encoded_network=network,
        )


def _fails_token(session: Session, instance_id: int, token: bytes, match: str) -> None:
    with pytest.raises(TrezorFailure, match=match):
        params = DEFAULT_ERC20_PARAMS.copy()
        params.update(to=ERC20_FAKE_ADDRESS)
        ethereum_ext.sign_tx(
            session,
            instance_id,
            **params,
            definitions=ethereum_messages.Definitions(encoded_token=token),
        )


def _fails_display_format(
    session: Session, instance_id: int, display_format: bytes, match: str
) -> None:
    with pytest.raises(TrezorFailure, match=match):
        ethereum_ext.sign_tx(
            session,
            instance_id,
            **get_clear_signing_sign_tx_params(),
            definitions=ethereum_messages.Definitions(
                encoded_display_format=display_format,
            ),
        )


def _fails_display_format_via_request(
    session: Session, instance_id: int, display_format: bytes, match: str
) -> None:
    calls: list[ethereum_messages.DefinitionRequest] = []

    def provider(
        req: ethereum_messages.DefinitionRequest,
    ) -> ethereum_messages.DefinitionAck:
        calls.append(req)
        return ethereum_messages.DefinitionAck(
            definitions=ethereum_messages.Definitions(
                encoded_display_format=display_format,
            )
        )

    with pytest.raises(TrezorFailure, match=match):
        ethereum_ext.sign_tx(
            session,
            instance_id,
            **get_clear_signing_sign_tx_params(supports_definition_request=True),
            definition_provider=provider,
        )

    # Firmware requests the display format once then fails validation. No token requests follow.
    assert len(calls) == 1
    assert calls[0].func_sig is not None


def _make_token_payload(
    timestamp: int = 0xFFFF_FFFF,
    message: ethereum_messages.TokenInfo | bytes = make_eth_token(),
) -> bytes:
    return make_payload(
        data_type=ethereum_messages.DefinitionType.TOKEN,
        message=message,
        timestamp=timestamp,
    )


def _make_display_format_payload(
    timestamp: int = 0xFFFF_FFFF,
    message: ethereum_messages.DisplayFormatInfo | bytes | None = None,
) -> bytes:
    if message is None:
        message = make_eth_display_format()
    return make_payload(
        data_type=ethereum_messages.DefinitionType.DISPLAY_FORMAT,
        message=message,
        timestamp=timestamp,
    )


def _cases(session: Session, instance_id: int) -> list[tuple]:
    cases: list[tuple] = [
        (make_payload, _fails_network),
        (_make_token_payload, _fails_token),
        (_make_display_format_payload, _fails_display_format),
        (_make_display_format_payload, _fails_display_format_via_request),
    ]

    return cases


def test_short_message(session: Session, instance_id: int) -> None:
    for _, check in _cases(session, instance_id):
        check(session, instance_id, b"\x00", "Invalid definition")


def test_mangled_signature(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        proof, signature = sign_payload(payload, [])
        bad_signature = signature[:-1] + b"\xff"
        check(
            session,
            instance_id,
            payload + proof + bad_signature,
            "Invalid definition signature",
        )


def test_not_enough_signatures(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        proof, signature = sign_payload(payload, [], threshold=1)
        check(
            session,
            instance_id,
            payload + proof + signature,
            "Invalid definition signature",
        )


def test_missing_signature(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        proof, _ = sign_payload(payload, [])
        check(session, instance_id, payload + proof, "Invalid definition")


def test_mangled_payload(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        proof, signature = sign_payload(payload, [])
        bad_payload = payload[:-1] + b"\xff"
        check(
            session,
            instance_id,
            bad_payload + proof + signature,
            "Invalid definition signature",
        )


def test_proof_length_mismatch(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        _, signature = sign_payload(payload, [])
        bad_proof = b"\x01"
        check(
            session, instance_id, payload + bad_proof + signature, "Invalid definition"
        )


def test_bad_proof(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        proof, signature = sign_payload(payload, [sha256(b"x").digest()])
        bad_proof = proof[:-1] + b"\xff"
        check(
            session,
            instance_id,
            payload + bad_proof + signature,
            "Invalid definition signature",
        )


def test_trimmed_proof(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        proof, signature = sign_payload(payload, [])
        bad_proof = proof[:-1]
        check(
            session, instance_id, payload + bad_proof + signature, "Invalid definition"
        )


def test_bad_prefix(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        payload = b"trzd2" + payload[5:]
        proof, signature = sign_payload(payload, [])
        check(session, instance_id, payload + proof + signature, "Invalid definition")


def test_bad_type(session: Session, instance_id: int) -> None:
    cases = [
        (ethereum_messages.DefinitionType.TOKEN, make_eth_token(), _fails_network),
        (ethereum_messages.DefinitionType.NETWORK, make_eth_network(), _fails_token),
        (
            ethereum_messages.DefinitionType.DISPLAY_FORMAT,
            make_eth_display_format(),
            _fails_network,
        ),
        (
            ethereum_messages.DefinitionType.DISPLAY_FORMAT,
            make_eth_display_format(),
            _fails_token,
        ),
        (
            ethereum_messages.DefinitionType.TOKEN,
            make_eth_token(),
            _fails_display_format,
        ),
        (
            ethereum_messages.DefinitionType.NETWORK,
            make_eth_network(),
            _fails_display_format,
        ),
        (
            ethereum_messages.DefinitionType.TOKEN,
            make_eth_token(),
            _fails_display_format_via_request,
        ),
        (
            ethereum_messages.DefinitionType.NETWORK,
            make_eth_network(),
            _fails_display_format_via_request,
        ),
    ]
    for data_type, message, check in cases:
        payload = make_payload(data_type=data_type, message=message)
        proof, signature = sign_payload(payload, [])
        check(
            session,
            instance_id,
            payload + proof + signature,
            "Definition type mismatch",
        )


def test_outdated(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make(timestamp=0)
        proof, signature = sign_payload(payload, [])
        check(
            session, instance_id, payload + proof + signature, "Definition is outdated"
        )


def test_malformed_protobuf(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make(message=b"\x00")
        proof, signature = sign_payload(payload, [])
        check(session, instance_id, payload + proof + signature, "Invalid definition")


def test_protobuf_mismatch(session: Session, instance_id: int) -> None:
    cases = [
        (ethereum_messages.DefinitionType.NETWORK, make_eth_token(), _fails_network),
        (ethereum_messages.DefinitionType.TOKEN, make_eth_network(), _fails_token),
        (
            ethereum_messages.DefinitionType.NETWORK,
            make_eth_display_format(),
            _fails_network,
        ),
        (
            ethereum_messages.DefinitionType.TOKEN,
            make_eth_display_format(),
            _fails_token,
        ),
        (
            ethereum_messages.DefinitionType.DISPLAY_FORMAT,
            make_eth_token(),
            _fails_display_format,
        ),
        (
            ethereum_messages.DefinitionType.DISPLAY_FORMAT,
            make_eth_network(),
            _fails_display_format,
        ),
        (
            ethereum_messages.DefinitionType.DISPLAY_FORMAT,
            make_eth_token(),
            _fails_display_format_via_request,
        ),
        (
            ethereum_messages.DefinitionType.DISPLAY_FORMAT,
            make_eth_network(),
            _fails_display_format_via_request,
        ),
    ]
    for data_type, message, check in cases:
        payload = make_payload(data_type=data_type, message=message)
        proof, signature = sign_payload(payload, [])
        check(session, instance_id, payload + proof + signature, "Invalid definition")


def test_trailing_garbage(session: Session, instance_id: int) -> None:
    for make, check in _cases(session, instance_id):
        payload = make()
        proof, signature = sign_payload(payload, [])
        check(
            session,
            instance_id,
            payload + proof + signature + b"\x00",
            "Invalid definition",
        )
