import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

pytestmark = pytest.mark.models("core")


def test_evolu_get_node(session: Session):
    proof = bytes.fromhex(
        "1fb521e8a4e4580377d530a9d6eb0a394ec8340fa42094d9f2e822bb944ce6a2074b81241b3b65dfa15d66e052f2504aba3ad1644844d695b181b3cdc9666cb66b"
    )
    node = evolu.get_node(
        session, proof=proof, node_rotation_index=0, delegated_identity_rotation_index=0
    )

    check_value = bytes.fromhex(
        "abc92324efc946fa715d738accbd1e204bff40d43a5a944933808f81227877b351c5296b887bc9aa765f2b643e91bd38a16b6feb4659f754f94a4f9f8a75ae17"
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
        evolu.get_node(
            session,
            proof=proof,
            node_rotation_index=0,
            delegated_identity_rotation_index=0,
        )


def test_evolu_get_node_no_proof(session: Session):
    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.get_node(
            session,
            proof=b"",
            node_rotation_index=0,
            delegated_identity_rotation_index=0,
        )


def test_evolu_get_node_none_proof(session: Session):
    with pytest.raises(
        TrezorFailure,
        match="DataError: Failed to decode message: Missing required field. proof_of_delegated_identity",
    ):
        evolu.get_node(session, proof=None, node_rotation_index=0, delegated_identity_rotation_index=0)  # type: ignore


def test_evolu_get_node_index_change(session: Session):
    proof = bytes.fromhex(
        "1fb521e8a4e4580377d530a9d6eb0a394ec8340fa42094d9f2e822bb944ce6a2074b81241b3b65dfa15d66e052f2504aba3ad1644844d695b181b3cdc9666cb66b"
    )
    node_index_0 = evolu.get_node(
        session, proof=proof, node_rotation_index=0, delegated_identity_rotation_index=0
    )
    node_index_1 = evolu.get_node(
        session, proof=proof, node_rotation_index=1, delegated_identity_rotation_index=0
    )

    assert node_index_0 != node_index_1


def test_evolu_get_node_index_1(session: Session):
    proof = bytes.fromhex(
        "1fb521e8a4e4580377d530a9d6eb0a394ec8340fa42094d9f2e822bb944ce6a2074b81241b3b65dfa15d66e052f2504aba3ad1644844d695b181b3cdc9666cb66b"
    )
    node = evolu.get_node(
        session, proof=proof, node_rotation_index=1, delegated_identity_rotation_index=0
    )

    check_value = bytes.fromhex(
        "8465c8de92d35053d4de324166f2fbf73281a64a9e63661a7f4617890743152ae4b3989931093f9f9dda0eb30f1949899f14dfb145a51ef0e611dc99a8a4c742"
    )
    assert node == check_value
