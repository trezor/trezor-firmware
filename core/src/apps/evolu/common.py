from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Sequence


def check_delegated_identity_proof(
    provided_proof: AnyBytes,
    delegated_identity_rotation_index: int,
    header: AnyBytes,
    arguments: Sequence[AnyBytes] | None = None,
) -> bool:
    from trezorutils import delegated_identity

    from trezor.crypto.curve import nist256p1
    from trezor.crypto.hashlib import sha256
    from trezor.utils import HashWriter

    from apps.common.writers import write_compact_size

    private_key = delegated_identity(delegated_identity_rotation_index)
    public_key = get_public_key_from_private_key(private_key)

    hash_writer = HashWriter(sha256())
    write_compact_size(hash_writer, len(header))
    hash_writer.extend(header)

    if arguments:
        for arg in arguments:
            write_compact_size(hash_writer, len(arg))
            hash_writer.extend(arg)

    return nist256p1.verify(
        public_key,
        provided_proof,
        hash_writer.get_digest(),
    )


def get_public_key_from_private_key(private_key: AnyBytes) -> bytes:
    from trezor.crypto.curve import nist256p1

    public_key = nist256p1.publickey(private_key, False)
    return public_key
