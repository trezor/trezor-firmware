from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluRegistrationRequest, EvoluSignRegistrationRequest


async def evolu_sign_registration_request(
    msg: EvoluSignRegistrationRequest,
) -> EvoluRegistrationRequest:
    from trezor import utils, wire
    from trezor.crypto.der import read_length
    from trezor.crypto.hashlib import sha256
    from trezor.messages import EvoluRegistrationRequest
    from trezor.utils import BufferReader, bootloader_locked

    from apps.common.writers import write_compact_size

    from .common import check_delegated_identity_proof

    if not bootloader_locked():
        raise wire.ProcessError(
            "Cannot sign registration request since bootloader is unlocked."
        )

    if utils.USE_OPTIGA:
        from trezor.crypto import optiga
    else:
        raise RuntimeError("Optiga is not available")

    if not check_delegated_identity_proof(
        proposed_value=bytes(msg.proof_of_delegated_identity),
        header=b"EvoluSignRegistrationRequest",
        arguments=[
            bytes(msg.challenge_from_server),
            msg.size_to_acquire.to_bytes(4, "big"),
        ],
    ):
        raise ValueError("Invalid proof")

    private_key = get_delegated_identity_key()
    public_key = get_public_key_from_private_key(private_key)

    header = b"EvoluSignRegistrationRequestV1:"
    components = [
        header,
        public_key,
        msg.challenge_from_server,
        msg.size_to_acquire.to_bytes(4, "big"),
    ]
    h = utils.HashWriter(sha256())
    for component in components:
        write_compact_size(h, len(component))
        h.extend(component)

    try:
        signature = optiga.sign(optiga.DEVICE_ECC_KEY_INDEX, h.get_digest())
    except optiga.SigningInaccessible:
        raise wire.ProcessError("Signing inaccessible.")

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

    return EvoluRegistrationRequest(
        certificate_chain=certificates,
        signature=signature,
    )


def get_delegated_identity_key() -> bytes:
    from trezor.utils import delegated_identity

    key = delegated_identity()
    return bytes(key)


def get_public_key_from_private_key(private_key: bytes) -> bytes:
    from trezor.crypto.curve import secp256k1

    public_key = secp256k1.publickey(private_key, False)
    return bytes(public_key)
