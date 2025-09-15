import hmac
from hashlib import sha256

import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session

pytestmark = pytest.mark.models("core")


def test_evolu_get_delegated_identity(session: "Session"):
    response = evolu.get_delegated_identity_key(session)
    private_key = response.private_key
    public_key = response.public_key
    assert len(private_key) == 32
    assert len(public_key) == 65

    response_2 = evolu.get_delegated_identity_key(session)
    assert response_2.public_key == public_key
    assert response_2.private_key == private_key


def test_evolu_get_node(session: "Session"):
    response = evolu.get_delegated_identity_key(session)
    private_key = response.private_key
    public_key = response.public_key
    assert len(private_key) == 32
    assert len(public_key) == 65
    assert evolu.get_delegated_identity_key(session).private_key == private_key

    proof = hmac.HMAC(private_key, b"EvoluGetNode", sha256).digest()

    node = evolu.get_evolu_node(session, proof=proof)
    assert len(node.data) == 64


def test_evolu_sign_registration_request(session: "Session"):
    response = evolu.get_delegated_identity_key(session)
    private_key = response.private_key
    public_key = response.public_key
    assert len(private_key) == 32
    assert len(public_key) == 65

    challenge = 1234567890
    size = 42

    message = (
        b"EvoluSignRegistrationRequest"
        + b"\x00"
        + challenge.to_bytes(16, "big")
        + b"\x00"
        + size.to_bytes(16, "big")
    )
    proof = hmac.HMAC(private_key, message, sha256).digest()

    result = evolu.evolu_sign_registration_request(
        session, challenge=challenge, size=size, proof=proof
    )

    check_registraion_request = (
        f"{{challenge:{challenge},public_key:{public_key.hex()},size:{size}}}"
    )
    assert result.registration_request == check_registraion_request
    assert len(result.certificates) >= 1
