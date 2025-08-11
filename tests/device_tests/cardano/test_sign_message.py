import pytest

from trezorlib import cardano, messages, tools
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

from ...common import parametrize_using_common_fixtures

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.cardano,
    pytest.mark.models("core"),
]


@parametrize_using_common_fixtures("cardano/sign_message.json")
def test_cardano_sign_message(session: Session, parameters, result):
    response = call_sign_message(session, parameters)
    assert response == _transform_expected_result(result)


@parametrize_using_common_fixtures("cardano/sign_message.failed.json")
def test_cardano_sign_message_failed(session: Session, parameters, result):
    with pytest.raises(TrezorFailure, match=result["error_message"]):
        call_sign_message(session, parameters)


def call_sign_message(
    session: Session,
    parameters,
) -> messages.CardanoSignMessageFinished:
    with session.client:
        return cardano.sign_message(
            session=session,
            payload=bytes.fromhex(parameters["payload"]),
            prefer_hex_display=parameters["prefer_hex_display"],
            signing_path=tools.parse_path(parameters["signing_path"]),
            address_parameters=cardano.parse_optional_address_parameters(
                parameters.get("address_parameters")
            ),
            protocol_magic=parameters.get("protocol_magic"),
            network_id=parameters.get("network_id"),
        )


def _transform_expected_result(result: dict) -> messages.CardanoSignMessageFinished:
    return messages.CardanoSignMessageFinished(
        signature=bytes.fromhex(result["signature"]),
        address=bytes.fromhex(result["address"]),
        pub_key=bytes.fromhex(result["pub_key"]),
    )
