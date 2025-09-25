def check_delegated_identity_proof(
    proposed_value: bytes, header: bytes, arguments: list[bytes] | None = None
) -> bool:
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256
    from trezor.utils import HashWriter, delegated_identity

    from apps.common.writers import write_compact_size

    private_key = delegated_identity()
    public_key = get_public_key_from_private_key(private_key)

    h = HashWriter(sha256())
    write_compact_size(h, len(header))
    h.extend(header)

    if arguments:
        for arg in arguments:
            write_compact_size(h, len(arg))
            h.extend(arg)

    return secp256k1.verify(
        public_key,
        proposed_value,
        h.get_digest(),
    )


def get_public_key_from_private_key(private_key: bytes) -> bytes:
    from trezor.crypto.curve import secp256k1

    public_key = secp256k1.publickey(private_key, False)
    return bytes(public_key)
