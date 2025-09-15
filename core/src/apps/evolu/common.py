def check_delegated_identity_key(
    proposed_value: bytes, header: bytes, arguments: list[bytes] | None = None
) -> bool:
    return compute_proof_value(header, arguments) == proposed_value


def compute_proof_value(header: bytes, arguments: list[bytes] | None = None) -> bytes:
    from trezor.crypto import hmac
    from trezor.utils import delegated_identity

    private_key = delegated_identity()
    message = header
    if arguments:
        for arg in arguments:
            message += b"\x00" + arg
    mac = hmac(hmac.SHA256, private_key, message).digest()
    return mac
