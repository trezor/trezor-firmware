from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluRegistrationRequest, EvoluSignRegistrationRequest
    from buffer_types import AnyBytes


async def evolu_sign_registration_request(
    msg: EvoluSignRegistrationRequest,
) -> EvoluRegistrationRequest:
    """
    Signs a registration request for this device to register `msg.size_to_acquire` megabytes of data on the Gate server.
    The request is signed using the device's delegated identity key. The Gate server will receive the corresponding public key
    alongside this request and store it as an identifier for this device.

    This function only works if the bootloader is locked.

    On devices with Optiga, we require a proof of delegated identity to be provided. It proves that the `delegated_identity_key`
    has already been issued to this Suite. For instructions how to construct the proof, inspect `core/src/apps/evolu/common.py`.
    For devices without Optiga, this function does not make sense, as they are not allowed any space at the Gate server anyway.

    Returns the signature and the device certificate chain which are to be sent to the Gate server alongside the registration request.

    Args:
        msg (EvoluSignRegistrationRequest): The protobuf message containing the proof of delegated identity,
            the challenge from the Gate server, and the size to acquire.
    Returns:
        EvoluRegistrationRequest: The signature of the registration request and the device certificate chain.
    Raises:
        wire.ProcessError: If the bootloader is unlocked or signing is inaccessible.
        RuntimeError: If Optiga is not available.
        ValueError: If the delegated identity proof is invalid.

    """
    from trezor import utils, wire
    from trezor.messages import EvoluRegistrationRequest
    from trezor.utils import bootloader_locked

    from .common import (
        check_delegated_identity_proof,
    )

    if not bootloader_locked():
        raise wire.ProcessError(
            "Cannot sign registration request since bootloader is unlocked."
        )

    if utils.USE_OPTIGA:
        from trezor.crypto import optiga
    else:
        raise RuntimeError("Optiga is not available")

    challenge_bytes, size_bytes = _check_data(
        msg.challenge_from_server, msg.size_to_acquire
    )

    if not check_delegated_identity_proof(
        provided_proof=bytes(msg.proof_of_delegated_identity),
        header=b"EvoluSignRegistrationRequest",
        arguments=[
            challenge_bytes,
            size_bytes,
        ],
    ):
        raise ValueError("Invalid proof")

    signature = _get_signature(challenge_bytes, size_bytes)
    certificates = _get_certificates()

    return EvoluRegistrationRequest(
        certificate_chain=certificates,
        signature=signature,
    )


def _check_data(challenge: bytes, size: int) -> tuple[bytes, bytes]:
    from trezor import wire

    if not (1 <= len(challenge) <= 255):
        raise wire.DataError("Invalid challenge length")
    if size < 0 or size > 256**4 - 1:
        raise wire.DataError("Invalid size_to_acquire")

    size_to_acquire_bytes = size.to_bytes(4, "big")

    return challenge, size_to_acquire_bytes


def _get_certificates() -> list[AnyBytes]:
    from trezor.utils import BufferReader
    from trezor.crypto.der import read_length
    from trezor.crypto import optiga
    from trezor import wire

    certificates = []
    r = BufferReader(optiga.get_certificate(optiga.DEVICE_CERT_INDEX))
    while r.remaining_count() > 0:
        cert_begin = r.offset
        if r.get() != 0x30:
            wire.FirmwareError("Device certificate is corrupted.")
        n = read_length(r)
        cert_len = r.offset - cert_begin + n
        r.seek(cert_begin)
        certificates.append(r.read_memoryview(cert_len))
    return certificates


def _get_signature(challenge_bytes: bytes, size_bytes: bytes) -> bytes:
    from trezor import utils, wire
    from trezor.crypto.hashlib import sha256
    from trezor.crypto import optiga

    from apps.common.writers import write_compact_size

    from .common import (
        get_delegated_identity_key,
        get_public_key_from_private_key,
    )

    private_key = get_delegated_identity_key()
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
