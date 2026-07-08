import pytest
from ecdsa import NIST256p, SigningKey, VerifyingKey

from trezorlib import evolu
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.testing.common import compact_size

from ..certificate import check_signature_optiga
from .common import get_delegated_identity_key, get_invalid_proof, get_proof

pytestmark = pytest.mark.models("core")


def signing_buffer(
    private_key: bytes, challenge: bytes, size: int, rotation_index: int | None = None
) -> bytes:
    public_key: VerifyingKey = SigningKey.from_string(private_key, curve=NIST256p).get_verifying_key()  # type: ignore
    components = [
        b"EvoluSignRegistrationRequestV2:",
        public_key.to_string("uncompressed"),
        challenge,
        size.to_bytes(4, "big"),
    ]
    if rotation_index is not None:
        components.append(rotation_index.to_bytes(4, "big"))
    return b"".join((compact_size(len(comp)) + comp) for comp in components)


@pytest.mark.models("t2t1")
def test_evolu_sign_request_t2t1(client: Client):
    challenge = bytes.fromhex("1234")
    size = 10
    proof = get_proof(
        client, b"EvoluSignRegistrationRequest", [challenge, size.to_bytes(4, "big")]
    )

    with pytest.raises(
        TrezorFailure,
        match="UnexpectedMessage: Unexpected message",
    ):
        evolu.sign_registration_request(
            client.get_session(),
            challenge=challenge,
            size=size,
            proof=proof,
        )


@pytest.mark.models("safe")
@pytest.mark.xfail_if_no_optiga
def test_evolu_sign_request(client: Client):
    delegated_identity_key = get_delegated_identity_key(client).private_key
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

    data = signing_buffer(
        delegated_identity_key, challenge, size, rotation_index=response.rotation_index
    )
    check_signature_optiga(
        response.signature, response.certificate_chain, client.model, data
    )


@pytest.mark.models("safe")
@pytest.mark.xfail_if_no_optiga
def test_evolu_sign_request_invalid_proof(client: Client):
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
@pytest.mark.xfail_if_no_optiga
def test_evolu_sign_request_challenge_too_long(client: Client):
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
@pytest.mark.xfail_if_no_optiga
def test_evolu_sign_request_challenge_too_short(client: Client):
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
@pytest.mark.xfail_if_no_optiga
def test_evolu_sign_request_size_too_small(client: Client):
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
@pytest.mark.xfail_if_no_optiga
def test_evolu_sign_request_size_too_large(client: Client):
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
@pytest.mark.xfail_if_no_optiga
def test_evolu_sign_request_data_higher_bound(client: Client):
    delegated_identity_key = get_delegated_identity_key(client).private_key
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

    data = signing_buffer(
        delegated_identity_key, challenge, size, rotation_index=response.rotation_index
    )
    check_signature_optiga(
        response.signature, response.certificate_chain, client.model, data
    )


@pytest.mark.models("safe")
@pytest.mark.parametrize("rotation_index", [None, 0, 1, 2, 42])
@pytest.mark.xfail_if_no_optiga
def test_evolu_sign_request_with_different_rotation_indices(
    client: Client, rotation_index
):
    evolu.index_management(client.get_session(), rotation_index=rotation_index)
    delegated_identity_key = get_delegated_identity_key(client).private_key
    challenge = bytes.fromhex("1234")
    size = 10
    proof = get_proof(
        client,
        b"EvoluSignRegistrationRequest",
        [challenge, size.to_bytes(4, "big")],
        rotation_index=rotation_index,
    )

    response = evolu.sign_registration_request(
        client.get_session(),
        challenge=challenge,
        size=size,
        proof=proof,
    )

    data = signing_buffer(
        delegated_identity_key, challenge, size, rotation_index=response.rotation_index
    )
    check_signature_optiga(
        response.signature, response.certificate_chain, client.model, data
    )

    assert response.rotation_index is not None
    if rotation_index is None:
        assert response.rotation_index == 0
    else:
        assert response.rotation_index == rotation_index
