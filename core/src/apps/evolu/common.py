def check_delegated_identity_proof(
    provided_proof: bytes, header: bytes, arguments: list[bytes] | None = None
) -> bool:
    from trezorutils import delegated_identity

    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256
    from trezor.utils import HashWriter

    from apps.common.writers import write_compact_size

    private_key = delegated_identity()
    public_key = get_public_key_from_private_key(private_key)

    hash_writer = HashWriter(sha256())
    write_compact_size(hash_writer, len(header))
    hash_writer.extend(header)

    if arguments:
        for arg in arguments:
            write_compact_size(hash_writer, len(arg))
            hash_writer.extend(arg)

    return secp256k1.verify(
        public_key,
        provided_proof,
        hash_writer.get_digest(),
    )


def get_public_key_from_private_key(private_key: bytes) -> bytes:
    from trezor.crypto.curve import secp256k1

    public_key = secp256k1.publickey(private_key, False)
    return public_key


def get_delegated_identity_key() -> bytes:
    from trezorutils import delegated_identity

    key = delegated_identity()
    return key
