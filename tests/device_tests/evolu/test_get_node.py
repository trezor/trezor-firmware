import pytest

from trezorlib import evolu
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure

pytestmark = pytest.mark.models("core")


def test_evolu_get_node(session: Session):
    proof = bytes.fromhex(
        "1fb521e8a4e4580377d530a9d6eb0a394ec8340fa42094d9f2e822bb944ce6a2074b81241b3b65dfa15d66e052f2504aba3ad1644844d695b181b3cdc9666cb66b"
    )
    node = evolu.get_node(session, proof=proof)

    check_value = bytes.fromhex(
        "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"
    )
    assert node == check_value


def test_evolu_get_node_invalid_proof(session: Session):
    proof = bytes.fromhex(
        "1f354fbb47b4679c1cb0c2c6b96a27f9a147c61ec5ef6f6c42491c839f4b7a95792d099be0f138274e5ef7896058b4de4f383f497792bb157b925e2644a79a0000"  # altered last 2 bytes
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.get_node(session, proof=proof)


def test_evolu_get_node_no_proof(session: Session):
    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.get_node(session, proof=b"")


def test_evolu_get_node_none_proof(session: Session):
    with pytest.raises(
        TrezorFailure,
        match="DataError: Failed to decode message: Missing required field. proof_of_delegated_identity",
    ):
        evolu.get_node(session, proof=None)  # type: ignore
