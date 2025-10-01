import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session

pytestmark = pytest.mark.models("safe")


@pytest.mark.protocol("protocol_v1")
def test_evolu_get_delegated_identity_is_constant(session: "Session"):
    response = evolu.get_delegated_identity_key(session)
    private_key = response.private_key
    assert len(private_key) == 32

    response_2 = evolu.get_delegated_identity_key(session)
    assert response_2.private_key == private_key


@pytest.mark.protocol("protocol_v1")
def test_evolu_get_delegated_identity_test_vector(session: "Session"):
    # on emulator, the additional salt is all zeroes. So the delegated identity key is constant.
    response = evolu.get_delegated_identity_key(session)
    private_key = response.private_key
    assert private_key == bytes.fromhex(
        "0e71b5d486a6738f85db46d4dfc8446ccb4d9804aa48e7624620f7cea291f278"
    )


def test_evolu_get_node(session: "Session"):
    proof = bytes.fromhex(
        "1fc2775112bbaa1018b1211037a8100f8be4b338c8a58e24cb1f2e314f57a5f0443bf6813d9035e0e8390fef66eefb6cc6249439a24cfb5b50a4ff026e7aeebe92"
    )
    response = evolu.get_evolu_node(session, proof=proof)

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
    response = evolu.evolu_sign_registration_request(
        session,
        challenge=bytes.fromhex(challenge),
        size=size,
        proof=proposed_value,
    )

    check_signature = bytes.fromhex(
        "3045022100d53f7ffc3a3e35e4f4e0dad909b81e99640f520067fdc50f860c758ea9ef7c910220507de3adf5238a8c3c1debccda21773d1ea7b07c249227d6e727ae78f97dab5c"
    )

    assert response.signature == check_signature
