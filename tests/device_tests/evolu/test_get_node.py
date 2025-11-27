import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure

from .common import sign_proof, get_delegated_identity_key

pytestmark = [
    pytest.mark.models("core"),
    # the tests vectors in this test are for the SLIP-14 seed. It should be initialized from `conftest.py` already but we set it explicitly to be sure
    pytest.mark.setup_client(
        mnemonic="all all all all all all all all all all all all", passphrase=False
    ),
]


def test_evolu_get_node(client: Client):
    delegated_identity_key = get_delegated_identity_key(client)
    proof = sign_proof(delegated_identity_key, b"EvoluGetNode", [])
    node = evolu.get_node(client.get_session(), proof=proof)

    # expected node for the SLIP-14 seed
    check_value = bytes.fromhex(
        "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"
    )
    assert node == check_value


@pytest.mark.setup_client(
    # a different seed
    mnemonic="valve multiply shuffle venue then cruel genre venture fruit hammer sponsor luxury",
    passphrase=False,
)
def test_evolu_get_node_different_seed(client: Client):
    delegated_identity_key = get_delegated_identity_key(client)
    proof = sign_proof(delegated_identity_key, b"EvoluGetNode", [])
    node = evolu.get_node(client.get_session(), proof=proof)

    # expected node for the SLIP-14 seed
    check_value = bytes.fromhex(
        "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"
    )

    # check that the generated node is different
    assert node != check_value


def test_evolu_get_node_invalid_proof(session: Session):
    # zeroed last 2 bytes of the hardcoded proof => it should be invalid for every test
    proof = bytes.fromhex(
        "1f354fbb47b4679c1cb0c2c6b96a27f9a147c61ec5ef6f6c42491c839f4b7a95792d099be0f138274e5ef7896058b4de4f383f497792bb157b925e2644a79a0000"
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
