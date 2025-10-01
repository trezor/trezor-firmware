import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

pytestmark = pytest.mark.models("t2t1")


def test_evolu_get_delegated_identity_is_constant(session: "Session"):
    with pytest.raises(
        TrezorFailure, match="Cannot enable Secure Sync since bootloader is unlocked."
    ):
        evolu.get_delegated_identity_key(session)


def test_evolu_get_node(session: "Session"):
    response = evolu.get_evolu_node(session, proof=None)

    check_value = bytes.fromhex(
        "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"
    )
    assert response.data == check_value


def test_evolu_sign_request(session: "Session"):
    challenge = "1234"
    size = 10
    proposed_value = bytes.fromhex(
        "1f8edb0ea453a16538fd36aa556c84a96f8bdfaa22625081347be10942c250874d798bb910e8b542d54500d2e846bc84a838127d9c91c1c26a73ecef1ffda0eb69"
    )

    with pytest.raises(
        TrezorFailure,
        match="Cannot sign registration request since bootloader is unlocked.",
    ):
        evolu.evolu_sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )
