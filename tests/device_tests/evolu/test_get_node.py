import pytest

from trezorlib import evolu
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.exceptions import TrezorFailure

from .common import get_invalid_proof, get_proof

pytestmark = [
    pytest.mark.models("core"),
    # the tests vectors in this test are for the SLIP-14 seed. It should be initialized from `conftest.py` already but we set it explicitly to be sure
    pytest.mark.setup_client(
        mnemonic="all all all all all all all all all all all all", passphrase=False
    ),
]


def test_evolu_get_node(client: Client):
    proof = get_proof(client, b"EvoluGetNode", [])
    node = evolu.get_node(client.get_session(), proof=proof, node_rotation_index=0)

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
    proof = get_proof(client, b"EvoluGetNode", [])
    node = evolu.get_node(client.get_session(), proof=proof, node_rotation_index=0)

    # expected node for the SLIP-14 seed
    check_value = bytes.fromhex(
        "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"
    )

    # check that the generated node is different
    assert node != check_value


def test_evolu_get_node_invalid_proof(client: Client):
    invalid_proof = get_invalid_proof(client, b"EvoluGetNode", [])

    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.get_node(client.get_session(), proof=invalid_proof, node_rotation_index=0)


def test_evolu_get_node_no_proof(client: Client):
    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.get_node(client.get_session(), proof=b"", node_rotation_index=0)


def test_evolu_get_node_none_proof(client: Client):
    with pytest.raises(
        TrezorFailure,
        match="DataError: Failed to decode message: Missing required field. proof_of_delegated_identity",
    ):
        evolu.get_node(client.get_session(), proof=None, node_rotation_index=0)  # type: ignore


def test_evolu_get_node_index_change(client: Client):
    proof = bytes.fromhex(
        "1fb521e8a4e4580377d530a9d6eb0a394ec8340fa42094d9f2e822bb944ce6a2074b81241b3b65dfa15d66e052f2504aba3ad1644844d695b181b3cdc9666cb66b"
    )
    node_index_0 = evolu.get_node(
        client.get_session(), proof=proof, node_rotation_index=0
    )
    node_index_1 = evolu.get_node(
        client.get_session(), proof=proof, node_rotation_index=1
    )

    assert node_index_0 != node_index_1


def test_evolu_get_node_index_1(client: Client):
    proof = bytes.fromhex(
        "1fb521e8a4e4580377d530a9d6eb0a394ec8340fa42094d9f2e822bb944ce6a2074b81241b3b65dfa15d66e052f2504aba3ad1644844d695b181b3cdc9666cb66b"
    )
    node = evolu.get_node(client.get_session(), proof=proof, node_rotation_index=1)

    check_value = bytes.fromhex(
        "8465c8de92d35053d4de324166f2fbf73281a64a9e63661a7f4617890743152ae4b3989931093f9f9dda0eb30f1949899f14dfb145a51ef0e611dc99a8a4c742"
    )
    assert node == check_value
