from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor import log
    from trezor.messages import AuthDbLookup, AuthDbLookupResponse


async def lookup(msg: AuthDbLookup) -> AuthDbLookupResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbLookupResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id

    membership_query = msg.witness_address is None and msg.value is not None

    wallet_id = await _get_wallet_id()
    stored_root = authdb.get_root(wallet_id)
    if stored_root is None:
        # Empty tree: membership is trivially false, non-membership is trivially true.
        counter = authdb.get_counter(wallet_id)
        return AuthDbLookupResponse(
            valid=not membership_query,
            counter=counter,
            membership=membership_query,
            wallet_id=wallet_id,
        )

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "lookup: address=%s proof_len=%d witness=%s membership_query=%s",
            msg.address,
            len(msg.proof),
            msg.witness_address if msg.witness_address else "none",
            membership_query,
        )

    if not membership_query:
        # Non-membership proof: prove witness is in tree, then verify address is absent
        if msg.witness_value is None:
            raise DataError("witness_value required for non-membership proof")
        valid = _verify_nonmembership(
            msg.address, msg.witness_address, msg.witness_value, msg.proof, stored_root
        )
        membership = False
    else:
        # Membership proof
        valid = _verify_proof(msg.address, msg.value, msg.proof, stored_root)
        membership = True

    if __debug__:
        from trezor import log
        log.debug(__name__, "lookup: result valid=%s membership=%s", valid, membership)

    counter = authdb.get_counter(wallet_id)
    return AuthDbLookupResponse(valid=valid, counter=counter, membership=membership, wallet_id=wallet_id)


def _verify_nonmembership(
    address: bytes,
    witness_address: bytes,
    witness_value: bytes,
    proof: list[bytes],
    expected_root: bytes,
) -> bool:
    """Verify that address is NOT in the tree.

    The caller supplies a witness leaf (witness_address, witness_value) that
    occupies address's path in the tree.  We verify:
      1. The witness is in the tree (membership proof against stored root).
      2. witness_address != address.
      3. witness_address and address share the same bit-value at every bit
         position that appears in the proof (they diverge only after the deepest
         branch, i.e. the witness is truly the closest leaf to address).
    """
    from trezor.crypto.hashlib import sha256

    def _sha256d(data: bytes) -> bytes:
        return sha256(data).digest()

    def _addr_bit(addr_hash: bytes, bit: int) -> int:
        return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1

    if witness_address == address:
        return False  # witness must differ from target

    addr_hash = _sha256d(address)
    witness_hash = _sha256d(witness_address)

    # Witness and target must share the same bit at every branch in the proof
    for elem in proof:
        bit = elem[0]
        if _addr_bit(addr_hash, bit) != _addr_bit(witness_hash, bit):
            return False

    # Membership proof for the witness
    return _verify_proof(witness_address, witness_value, proof, expected_root)


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
