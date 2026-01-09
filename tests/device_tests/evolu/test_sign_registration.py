import pytest
from ecdsa import NIST256p, SigningKey, VerifyingKey

from trezorlib import evolu
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure

from ...common import compact_size
from ..certificate import check_signature_optiga
from .common import get_delegated_identity_key, get_invalid_proof, get_proof

pytestmark = pytest.mark.models("core")


def signing_buffer(private_key: bytes, challenge: bytes, size: int) -> bytes:
    public_key: VerifyingKey = SigningKey.from_string(private_key, curve=NIST256p).get_verifying_key()  # type: ignore
    components = [
        b"EvoluSignRegistrationRequestV1:",
        public_key.to_string("uncompressed"),
        challenge,
        size.to_bytes(4, "big"),
    ]
    return b"".join((compact_size(len(comp)) + comp) for comp in components)


def optiga_unavailable(client: Client) -> bool:
    """Check if Optiga is unavailable from the presence of its security counter."""
    return client.features.optiga_sec is None


@pytest.mark.models("t2t1")
def test_evolu_sign_request_t2t1(client: Client):
    challenge = bytes.fromhex("1234")
    size = 10
    proof = get_proof(
        client, b"EvoluSignRegistrationRequest", [challenge, size.to_bytes(4, "big")]
    )

    with pytest.raises(
        TrezorFailure,
        match="Optiga is not available",
    ):
        evolu.sign_registration_request(
            client.get_session(),
            challenge=challenge,
            size=size,
            proof=proof,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request(client: Client):
    if optiga_unavailable(client):
        pytest.xfail("Optiga is not available on this device.")
    delegated_identity_key = get_delegated_identity_key(client)
    challenge = bytes.fromhex("1234")
    size = 10
    proposed_value = get_proof(
        client,
        b"EvoluSignRegistrationRequest",
        [challenge, size.to_bytes(4, "big")],
    )

    response = evolu.sign_registration_request(
        client.get_session(),
        challenge=challenge,
        size=size,
        proof=proposed_value,
    )

    data = signing_buffer(delegated_identity_key, challenge, size)
    check_signature_optiga(
        response.signature, response.certificate_chain, client.model, data
    )


@pytest.mark.models("safe")
def test_evolu_sign_request_invalid_proof(client: Client):
    if optiga_unavailable(client):
        pytest.xfail("Optiga is not available on this device.")
    challenge = bytes.fromhex("1234")
    size = 10
    invalid_proof = get_invalid_proof(
        client, b"EvoluSignRegistrationRequest", [challenge, size.to_bytes(4, "big")]
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.sign_registration_request(
            client.get_session(),
            challenge=challenge,
            size=size,
            proof=invalid_proof,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_challenge_too_long(client: Client):
    if optiga_unavailable(client):
        pytest.xfail("Optiga is not available on this device.")
    challenge = b"\x01" * 300  # 300 bytes, max is 255
    size = 10
    proof = get_proof(
        client, b"EvoluSignRegistrationRequest", [challenge, size.to_bytes(4, "big")]
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid challenge length",
    ):
        evolu.sign_registration_request(
            client.get_session(),
            challenge=challenge,
            size=size,
            proof=proof,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_challenge_too_short(client: Client):
    if optiga_unavailable(client):
        pytest.xfail("Optiga is not available on this device.")
    challenge = b""  # 0 bytes, minimum is 1
    size = 10
    proof = get_proof(
        client, b"EvoluSignRegistrationRequest", [challenge, size.to_bytes(4, "big")]
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid challenge length",
    ):
        evolu.sign_registration_request(
            client.get_session(),
            challenge=challenge,
            size=size,
            proof=proof,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_size_too_small(client: Client):
    if optiga_unavailable(client):
        pytest.xfail("Optiga is not available on this device.")
    challenge = bytes.fromhex("1234")
    size = -10
    proof = get_proof(
        client,
        b"EvoluSignRegistrationRequest",
        [challenge, size.to_bytes(4, "big", signed=True)],
    )

    with pytest.raises(
        ValueError,
        match=f"Value {size} in field size_to_acquire does not fit into uint32",
    ):
        evolu.sign_registration_request(
            client.get_session(),
            challenge=challenge,
            size=size,
            proof=proof,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_size_too_large(client: Client):
    if optiga_unavailable(client):
        pytest.xfail("Optiga is not available on this device.")
    challenge = bytes.fromhex("1234")
    size = 0xFFFFFFFF + 1
    proof = get_proof(
        client, b"EvoluSignRegistrationRequest", [challenge, size.to_bytes(5, "big")]
    )

    with pytest.raises(
        ValueError,
        match=f"Value {size} in field size_to_acquire does not fit into uint32",
    ):
        evolu.sign_registration_request(
            client.get_session(),
            challenge=challenge,
            size=size,
            proof=proof,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_data_higher_bound(client: Client):
    if optiga_unavailable(client):
        pytest.xfail("Optiga is not available on this device.")
    delegated_identity_key = get_delegated_identity_key(client)
    challenge = b"\x12" * 255
    size = 0xFFFFFFFF
    proof = get_proof(
        client,
        b"EvoluSignRegistrationRequest",
        [challenge, size.to_bytes(4, "big")],
    )

    response = evolu.sign_registration_request(
        client.get_session(),
        challenge=challenge,
        size=size,
        proof=proof,
    )

    data = signing_buffer(delegated_identity_key, challenge, size)
    check_signature_optiga(
        response.signature, response.certificate_chain, client.model, data
    )
