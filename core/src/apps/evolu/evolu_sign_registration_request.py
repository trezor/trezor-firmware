from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluRegistrationRequest, EvoluSignRegistrationRequest


async def evolu_sign_registration_request(
    msg: EvoluSignRegistrationRequest,
) -> EvoluRegistrationRequest:
    from ubinascii import hexlify

    from trezor import utils, wire
    from trezor.crypto.der import read_length
    from trezor.crypto.hashlib import sha256
    from trezor.messages import EvoluRegistrationRequest
    from trezor.utils import BufferReader, bootloader_locked

    from apps.common.writers import write_compact_size

    from .common import check_delegated_identity_key

    if not bootloader_locked():
        raise wire.ProcessError(
            "Cannot sign registration request since bootloader is unlocked."
        )

    if utils.USE_OPTIGA:
        from trezor.crypto import optiga
    else:
        raise RuntimeError("Optiga is not available")

    if not check_delegated_identity_key(
        proposed_value=msg.proof,
        header=b"EvoluSignRegistrationRequest",
        arguments=[msg.challenge.to_bytes(16, "big"), msg.size.to_bytes(16, "big")],
    ):
        raise ValueError("Invalid proof")

    private_key = get_delegated_identity_key()
    public_key = get_public_key_from_private_key(private_key)

    registration_request = {
        "public_key": hexlify(public_key).decode(),  # device identifier
        "challenge": str(msg.challenge),
        "size": str(msg.size),
    }
    registration_request_str = (
        "{" + ",".join(f"{k}:{v}" for k, v in registration_request.items()) + "}"
    )

    header = b"EvoluSignRegistrationRequest:"  # tady bude verze
    h = utils.HashWriter(sha256())
    write_compact_size(h, len(header))
    h.extend(header)
    write_compact_size(h, len(registration_request_str))
    h.extend(registration_request_str.encode())

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
        registration_request=registration_request_str,
        certificates=certificates,
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
