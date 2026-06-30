from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbLookup, AuthDbLookupResponse


async def lookup(msg: AuthDbLookup) -> AuthDbLookupResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbLookupResponse
    from trezor.wire import DataError

    stored_root = authdb.get_root()
    if stored_root is None:
        raise DataError("No Merkle root stored on device")

    valid = _verify_proof(msg.leaf_hash, msg.proof, stored_root)
    counter = authdb.get_counter()

    return AuthDbLookupResponse(valid=valid, counter=counter)


def _verify_proof(
    leaf_hash: bytes,
    proof: list[bytes],
    expected_root: bytes,
) -> bool:
    """Verify a Merkle proof using sorted internal hashing.

    Each level: hash = SHA-256(b"\\x01" + min(current, sibling) + max(current, sibling))
    This matches trezorlib.merkle_tree.evaluate_proof.
    """
    from trezor.crypto.hashlib import sha256

    current = leaf_hash
    for sibling in proof:
        a, b = (current, sibling) if current <= sibling else (sibling, current)
        current = sha256(b"\x01" + a + b).digest()

    return current == expected_root
