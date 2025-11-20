import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

pytestmark = pytest.mark.models("core")


def test_evolu_get_node(session: Session):
    proof = bytes.fromhex(
        "1fb521e8a4e4580377d530a9d6eb0a394ec8340fa42094d9f2e822bb944ce6a2074b81241b3b65dfa15d66e052f2504aba3ad1644844d695b181b3cdc9666cb66b"
    )
    node = evolu.get_node(session, proof=proof, index=0)

    check_value = bytes.fromhex(
        "7b5fd3809dfafaf8b34aa8128a355e6f6dca6e5d8bd70948a3a1d9699d92749f9ba338eb28e6c29b03188bb3b0f93b3a4662fe6dda2a7e9ff8ceb8191a9035fd"
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
        evolu.get_node(session, proof=proof, index=0)


def test_evolu_get_node_no_proof(session: Session):
    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.get_node(session, proof=b"", index=0)


def test_evolu_get_node_none_proof(session: Session):
    with pytest.raises(
        TrezorFailure,
        match="DataError: Failed to decode message: Missing required field. proof_of_delegated_identity",
    ):
        evolu.get_node(session, proof=None, index=0)  # type: ignore

def test_evolu_get_node_index_change(session: Session):
    proof = bytes.fromhex(
        "1fb521e8a4e4580377d530a9d6eb0a394ec8340fa42094d9f2e822bb944ce6a2074b81241b3b65dfa15d66e052f2504aba3ad1644844d695b181b3cdc9666cb66b"
    )
    node_index_0 = evolu.get_node(session, proof=proof, index=0)
    node_index_1 = evolu.get_node(session, proof=proof, index=1)

    assert node_index_0 != node_index_1