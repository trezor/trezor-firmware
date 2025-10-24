import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

pytestmark = pytest.mark.models("t2t1")


def test_evolu_get_delegated_identity_is_constant(session: "Session"):
    private_key = evolu.get_delegated_identity_key(session)
    assert len(private_key) == 32

    private_key_2 = evolu.get_delegated_identity_key(session)
    assert private_key_2 == private_key


def test_evolu_get_node(session: "Session"):
    response = evolu.get_evolu_node(session, proof=None)

    check_value = bytes.fromhex(
        "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"
    )
    assert response == check_value


def test_evolu_sign_request(session: "Session"):
    challenge = "1234"
    size = 10
    proposed_value = bytes.fromhex(
        "1b161be2bfc622b4ffd9943138ab5931e77b4c6835e29b1ac25221c74492495a912c00f488fd5f95b43085f721f36574813785c011c60cf81877ccd057df6bed0c"
    )

    with pytest.raises(
        TrezorFailure,
        match="Optiga is not available",
    ):
        evolu.evolu_sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )
