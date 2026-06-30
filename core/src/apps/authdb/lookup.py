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

    valid = _verify_proof(msg.address, msg.value, msg.proof, stored_root)
    counter = authdb.get_counter()

    return AuthDbLookupResponse(valid=valid, counter=counter)


def _verify_proof(
    address: bytes,
    value: bytes,
    proof: list[bytes],
    expected_root: bytes,
) -> bool:
    """Verify a Sparse Merkle Tree proof.

    Path routing: bit i of SHA-256(address) (MSB first) determines left (0) / right (1)
    at tree level i from the root.
    Leaf hash:     SHA-256(b"\\x00" + address + value)
    Internal hash: SHA-256(b"\\x01" + left + right)  -- positional, no min/max

    proof is in leaf-to-root order (proof[0] = sibling nearest leaf).
    """
    from trezor.crypto.hashlib import sha256

    addr_hash = sha256(address).digest()
    current = sha256(b"\x00" + address + value).digest()
    depth = len(proof)

    for i, sibling in enumerate(proof):
        level = depth - 1 - i          # 0 = root level, depth-1 = leaf level
        byte_idx = level // 8
        bit = (addr_hash[byte_idx] >> (7 - level % 8)) & 1
        if bit == 0:
            current = sha256(b"\x01" + current + sibling).digest()
        else:
            current = sha256(b"\x01" + sibling + current).digest()

    return current == expected_root
