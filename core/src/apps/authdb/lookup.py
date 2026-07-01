from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor import log
    from trezor.messages import AuthDbLookup, AuthDbLookupResponse


async def lookup(msg: AuthDbLookup) -> AuthDbLookupResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbLookupResponse
    from trezor.wire import DataError

    stored_root = authdb.get_root()
    if stored_root is None:
        raise DataError("No Merkle root stored on device")

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "lookup: address=%s proof_len=%d",
            msg.address,
            len(msg.proof),
        )

    valid = _verify_proof(msg.address, msg.value, msg.proof, stored_root)

    if __debug__:
        from trezor import log
        log.debug(__name__, "lookup: result valid=%s", valid)

    counter = authdb.get_counter()
    return AuthDbLookupResponse(valid=valid, counter=counter)


def _verify_proof(
    address: bytes,
    value: bytes,
    proof: list[bytes],
    expected_root: bytes,
) -> bool:
    """Verify an MPT (Merkle Patricia Trie) proof.

    Hashing scheme:
      leaf hash     : SHA-256(b"\\x00" + address + value)
      internal hash : SHA-256(b"\\x01" + left + right)  -- positional

    Proof format (leaf-to-root order):
      Each element is 33 bytes: 1-byte bit-position (0-255) + 32-byte sibling hash.
      Only actual branch points appear, so proof length is O(log N) for N entries.

    Mirrors evaluateProof() in merkletree.ts.
    """
    from trezor.crypto.hashlib import sha256

    def _sha256d(data: bytes) -> bytes:
        return sha256(data).digest()

    def _addr_bit(addr_hash: bytes, bit: int) -> int:
        return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1

    addr_hash = _sha256d(address)
    node = _sha256d(b"\x00" + address + value)   # leaf hash

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "_verify_proof: addr_hash=%s leaf_hash=%s proof_len=%d",
            addr_hash,
            node,
            len(proof),
        )

    for elem in proof:
        bit = elem[0]                            # bit position (0-255)
        sibling = bytes(elem[1:])                # 32-byte sibling hash
        target_bit = _addr_bit(addr_hash, bit)
        if target_bit == 0:
            node = _sha256d(b"\x01" + node + sibling)
        else:
            node = _sha256d(b"\x01" + sibling + node)

        if __debug__:
            from trezor import log
            log.debug(
                __name__,
                "  bit=%d target_bit=%d hash=%s",
                bit,
                target_bit,
                node,
            )

    match = node == expected_root
    if __debug__ and not match:
        from trezor import log
        log.debug(
            __name__,
            "_verify_proof: MISMATCH computed=%s expected=%s",
            node,
            expected_root,
        )
    return match
