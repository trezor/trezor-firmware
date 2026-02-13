from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import EvoluRegistrationRequest, EvoluSignRegistrationRequest

BYTES_IN_UINT32 = 4


async def sign_registration_request(
    msg: EvoluSignRegistrationRequest,
) -> EvoluRegistrationRequest:
    """
    Signs a registration request for this device to register `msg.size_to_acquire` bytes of space on the Quota Manager server.
    The request is signed using the device's Optiga certificate.

    This function only works if the bootloader is locked and if the device has Optiga available.

    We require a proof of delegated identity to be provided. It proves that the `delegated_identity_key`
    has already been issued to this Suite.

    Returns the signature and the Optiga's certificate chain which are to be sent to the Quota Manager server during the registration request.

    Args:
        msg (EvoluSignRegistrationRequest): The protobuf message containing the proof of delegated identity,
            the challenge from the Quota Manager server, and the size to acquire.
    Returns:
        EvoluRegistrationRequest: The signature of the registration request and the Optiga's certificate chain.
    Raises:
        wire.ProcessError: If the bootloader is unlocked or signing is inaccessible.
        RuntimeError: If Optiga is not available.
        ValueError: If the delegated identity proof is invalid.

    """
    from trezor import utils
    from trezor.messages import EvoluRegistrationRequest
    from trezor.utils import BufferReader

    from apps.common.certificates import parse_cert_chain
    from apps.evolu.common import check_delegated_identity_proof

    if utils.USE_OPTIGA:
        from trezor.crypto import optiga
    else:
        raise RuntimeError("Optiga is not available")

    challenge_bytes, size_bytes = _check_data(
        msg.challenge_from_server, msg.size_to_acquire
    )

    if not check_delegated_identity_proof(
        provided_proof=msg.proof_of_delegated_identity,
        delegated_identity_rotation_index=0,  # this is happening right after the delegated_identity_key is generated and never more
        header=b"EvoluSignRegistrationRequest",
        arguments=[
            challenge_bytes,
            size_bytes,
        ],
    ):
        raise ValueError("Invalid proof")

    signature = _get_signature(challenge_bytes, size_bytes)
    r = BufferReader(optiga.get_certificate(optiga.DEVICE_CERT_INDEX))
    certificates = parse_cert_chain(r)

    return EvoluRegistrationRequest(
        certificate_chain=certificates,
        signature=signature,
    )


def _check_data(challenge: AnyBytes, size: int) -> tuple[AnyBytes, bytes]:
    from trezor import wire

    if not 1 <= len(challenge) <= 255:
        raise wire.DataError("Invalid challenge length")
    if not 0 <= size <= 0xFFFFFFFF:
        raise wire.DataError("Invalid size_to_acquire")

    size_to_acquire_bytes = size.to_bytes(BYTES_IN_UINT32, "big")

    return challenge, size_to_acquire_bytes


def _get_signature(challenge_bytes: AnyBytes, size_bytes: bytes) -> bytes:
    from trezorutils import delegated_identity

    from trezor import utils, wire
    from trezor.crypto import optiga
    from trezor.crypto.hashlib import sha256

    from apps.common.writers import write_compact_size

    from .common import get_public_key_from_private_key

    private_key = delegated_identity(0)
    public_key = get_public_key_from_private_key(private_key)

    header = b"EvoluSignRegistrationRequestV1:"
    components = [
        header,
        public_key,
        challenge_bytes,
        size_bytes,
    ]
    hash_writer = utils.HashWriter(sha256())
    for component in components:
        write_compact_size(hash_writer, len(component))
        hash_writer.extend(component)

    try:
        signature = optiga.sign(optiga.DEVICE_ECC_KEY_INDEX, hash_writer.get_digest())
    except optiga.SigningInaccessible:
        raise wire.ProcessError("Signing inaccessible.")
    return signature
