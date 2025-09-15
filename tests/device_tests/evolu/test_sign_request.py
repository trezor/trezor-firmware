import pytest

from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib import evolu
from hashlib import sha256


@pytest.mark.models("core")
def test_evolu_get_delegated_identity(session: "Session"):
    response = evolu.get_delegetad_identity_key(session)
    private_key = response.private_key
    public_key = response.public_key
    assert len(private_key) == 32
    assert len(public_key) == 65

    response_2 = evolu.get_delegetad_identity_key(session)
    assert response_2.public_key == public_key
    assert response_2.private_key == private_key


@pytest.mark.models("core")
def test_evolu_get_node(session: "Session"):
    response = evolu.get_delegetad_identity_key(session)
    private_key = response.private_key
    public_key = response.public_key
    assert len(private_key) == 32
    assert len(public_key) == 65
    assert evolu.get_delegetad_identity_key(session).private_key == private_key

    buffer = b"EvoluGetNode" + b"|" + private_key
    proof = sha256(buffer).digest()

    node = evolu.get_evolu_node(session, proof=proof)
    assert len(node.data) == 64


@pytest.mark.models("core")
def test_evolu_sign_registration_request(session: "Session"):
    response = evolu.get_delegetad_identity_key(session)
    private_key = response.private_key
    public_key = response.public_key
    assert len(private_key) == 32
    assert len(public_key) == 65

    challenge = 1234567890
    size = 42

    buffer = (
        b"EvoluSignRegistrationRequest"
        + b"|"
        + private_key
        + b"|"
        + challenge.to_bytes(16, "big")
        + b"|"
        + size.to_bytes(16, "big")
    )
    proof = sha256(buffer).digest()

    result = evolu.evolu_sign_registration_request(
        session, challenge=challenge, size=size, proof=proof
    )

    check_registraion_request = (
        f"{{challenge:{challenge},public_key:{public_key.hex()},size:{size}}}"
    )
    assert result.registration_request == check_registraion_request
    assert len(result.certificates) >= 1
