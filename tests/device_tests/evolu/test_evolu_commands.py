import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session

pytestmark = pytest.mark.models("safe")


@pytest.mark.protocol("protocol_v1")
def test_evolu_get_delegated_identity_is_constant(session: "Session"):
    private_key = evolu.get_delegated_identity_key(session)
    assert len(private_key) == 32

    private_key_2 = evolu.get_delegated_identity_key(session)
    assert private_key_2 == private_key


@pytest.mark.protocol("protocol_v1")
def test_evolu_get_delegated_identity_test_vector(session: "Session"):
    # on emulator, the master key is all zeroes. So the delegated identity key is constant.
    private_key = evolu.get_delegated_identity_key(session)
    assert private_key == bytes.fromhex(
        "c6389a1a662218ce2ff8db74dd2e2e428a23e9388ae3279466fedfcbd82efb34"
    )


def test_evolu_get_node(session: "Session"):
    proof = bytes.fromhex(
        "1b161be2bfc622b4ffd9943138ab5931e77b4c6835e29b1ac25221c74492495a912c00f488fd5f95b43085f721f36574813785c011c60cf81877ccd057df6bed0c"
    )
    node = evolu.get_evolu_node(session, proof=proof)

    check_value = bytes.fromhex(
        "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"
    )
    assert node == check_value


def test_evolu_sign_request(session: "Session"):
    challenge = "1234"
    size = 10
    proposed_value = bytes.fromhex(
        "1c551ff04b45f68eb42352fd0f3bf311fc6c971132150412a3d3d052c19500b9097ceb0dfcb779b431547eda0b65be04055ee2620606c2be77a0e0e6e3055b4d53"
    )
    response = evolu.evolu_sign_registration_request(
        session,
        challenge=bytes.fromhex(challenge),
        size=size,
        proof=proposed_value,
    )

    check_signature = bytes.fromhex(
        "304402201c841f9844ee8b6869b571cfb8cd0589ff6a17f82b345b750c3a79384317b6310220259965c99279cb2295cc71c59ca57ee2bebf52a08ab83d1e778908888f0355e0"
    )

    assert response.signature == check_signature
