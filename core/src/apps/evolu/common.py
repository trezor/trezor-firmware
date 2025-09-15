def check_delegetad_identity_key(
    proposed_value: bytes, header: bytes, arguments: list[bytes] = []
) -> bool:
    return compute_proof_sought_value(header, arguments) == proposed_value


def compute_proof_sought_value(header: bytes, arguments: list[bytes] = []) -> bytes:
    from trezor.utils import delegated_identity
    from trezor import utils
    from trezor.crypto.hashlib import sha256

    private_key = delegated_identity()
    h = utils.HashWriter(sha256())
    h.extend(header)
    h.extend(b"|")
    h.extend(private_key)
    if arguments:
        for arg in arguments:
            h.extend(b"|")
            h.extend(arg)
    return h.get_digest()
