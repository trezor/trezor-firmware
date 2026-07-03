from common import unittest

from mock_storage import mock_storage
from trezor.crypto.hashlib import sha256


# ---------------------------------------------------------------------------
# MPT primitives (must match lookup.py and authdb_tree.py)
# ---------------------------------------------------------------------------

def _sha256d(data):
    return sha256(data).digest()


def _addr_bit(addr_hash, bit):
    return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1


def _leaf_hash(address, value):
    return _sha256d(b"\x00" + address + value)


def _internal_hash(left, right):
    return _sha256d(b"\x01" + left + right)


# ---------------------------------------------------------------------------
# MPT builder — returns (root, proof) for target_address
# ---------------------------------------------------------------------------

def _find_split_bit(leaves, start_bit):
    for bit in range(start_bit, 256):
        b0 = _addr_bit(leaves[0][0], bit)
        if any(_addr_bit(l[0], bit) != b0 for l in leaves[1:]):
            return bit
    raise ValueError("duplicate address hashes")


def _build_mpt(leaves, start_bit):
    # leaf tuple: ("leaf", addr_hash, leaf_hash)
    # branch tuple: ("branch", bit, left_node, right_node)
    if len(leaves) == 1:
        return ("leaf", leaves[0][0], leaves[0][1])
    bit = _find_split_bit(leaves, start_bit)
    left = [l for l in leaves if _addr_bit(l[0], bit) == 0]
    right = [l for l in leaves if _addr_bit(l[0], bit) == 1]
    return ("branch", bit, _build_mpt(left, bit + 1), _build_mpt(right, bit + 1))


def _hash_mpt(node):
    if node[0] == "leaf":
        return node[2]
    return _internal_hash(_hash_mpt(node[2]), _hash_mpt(node[3]))


def build_mpt_root_and_proof(entries, target_address):
    """Build an MPT and return (root_hash, proof) for target_address.

    proof is in leaf-to-root order; each element is 33 bytes:
    1-byte bit-position + 32-byte sibling hash.
    """
    leaves = [(_sha256d(a), _leaf_hash(a, v)) for a, v in entries.items()]
    root_node = _build_mpt(leaves, 0)
    root_hash = _hash_mpt(root_node)

    target_hash = _sha256d(target_address)
    proof = []

    def walk(node):
        if node[0] == "leaf":
            return node[2]
        _, bit, left, right = node
        target_bit = _addr_bit(target_hash, bit)
        if target_bit == 0:
            left_hash = walk(left)
            right_hash = _hash_mpt(right)
            proof.append(bytes([bit]) + right_hash)
            return _internal_hash(left_hash, right_hash)
        else:
            left_hash = _hash_mpt(left)
            right_hash = walk(right)
            proof.append(bytes([bit]) + left_hash)
            return _internal_hash(left_hash, right_hash)

    walk(root_node)
    return root_hash, proof   # post-order walk → leaf-to-root order


def find_witness(entries, target_address):
    """Find the witness leaf for a non-membership proof (leaf occupying target's path)."""
    target_hash = _sha256d(target_address)
    leaves = [(_sha256d(a), a, v) for a, v in entries.items()]
    root_node = _build_mpt(
        [(ah, _leaf_hash(a, v)) for ah, a, v in leaves], 0
    )
    leaf_map = {ah: (a, v) for ah, a, v in leaves}

    def walk(node):
        if node[0] == "leaf":
            return node[1]  # addr_hash of witness leaf
        _, bit, left, right = node
        if _addr_bit(target_hash, bit) == 0:
            return walk(left)
        else:
            return walk(right)

    witness_addr_hash = walk(root_node)
    return leaf_map[witness_addr_hash]  # (witness_address, witness_value)


ENTRIES = {b"alice": b"data_alice", b"bob": b"data_bob",
           b"carol": b"data_carol", b"dave": b"data_dave"}


class TestAuthDbVerifyProof(unittest.TestCase):

    def setUp(self):
        from apps.authdb.lookup import _verify_proof
        self._verify = _verify_proof

    def test_valid_proof_alice(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertTrue(self._verify(b"alice", b"data_alice", proof, root))

    def test_valid_proof_bob(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"bob")
        self.assertTrue(self._verify(b"bob", b"data_bob", proof, root))

    def test_valid_proof_carol(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"carol")
        self.assertTrue(self._verify(b"carol", b"data_carol", proof, root))

    def test_invalid_wrong_value(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertFalse(self._verify(b"alice", b"WRONG_VALUE", proof, root))

    def test_invalid_wrong_address(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        # alice's proof applied with bob's address → wrong bit decisions
        self.assertFalse(self._verify(b"bob", b"data_alice", proof, root))

    def test_invalid_tampered_sibling(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        tampered = list(proof)
        tampered[0] = bytes([tampered[0][0]]) + _sha256d(b"garbage")
        self.assertFalse(self._verify(b"alice", b"data_alice", tampered, root))

    def test_invalid_wrong_root(self):
        _, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        wrong_root = _sha256d(b"not the root")
        self.assertFalse(self._verify(b"alice", b"data_alice", proof, wrong_root))

    def test_single_entry_tree(self):
        root, proof = build_mpt_root_and_proof({b"solo": b"val"}, b"solo")
        self.assertTrue(self._verify(b"solo", b"val", proof, root))
        # single-entry MPT has no branch nodes → empty proof
        self.assertEqual(proof, [])

    def test_invalid_tampered_bit_position(self):
        # The bit-position byte only matters insofar as it selects which side
        # (left/right) the sibling goes on for hashing; picking a *different*
        # bit number that happens to carry the same 0/1 value for this
        # address is a no-op for the verifier (order is unchanged), so a
        # meaningful tamper must pick a bit position whose value differs from
        # the original, forcing the L/R order — and therefore the resulting
        # hash — to change.
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        if not proof:
            return  # nothing to tamper with on a single-branch-less tree
        addr_hash = _sha256d(b"alice")
        tampered = list(proof)
        orig_bit, sibling = tampered[0][0], tampered[0][1:]
        orig_value = _addr_bit(addr_hash, orig_bit)
        flipped_bit = next(
            b for b in range(256) if _addr_bit(addr_hash, b) != orig_value
        )
        tampered[0] = bytes([flipped_bit]) + sibling
        self.assertFalse(self._verify(b"alice", b"data_alice", tampered, root))

    def test_invalid_extra_proof_element(self):
        # Appending a bogus extra element must not still validate.
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        tampered = list(proof) + [bytes([0]) + _sha256d(b"bogus")]
        self.assertFalse(self._verify(b"alice", b"data_alice", tampered, root))

    def test_invalid_reordered_proof(self):
        # Swapping two valid elements (when there are at least two) must not
        # still validate — order encodes the leaf-to-root path.
        root, proof = build_mpt_root_and_proof(
            {b"alice": b"data_alice", b"bob": b"data_bob",
             b"carol": b"data_carol", b"dave": b"data_dave",
             b"eve": b"data_eve", b"frank": b"data_frank"},
            b"alice",
        )
        if len(proof) < 2:
            return
        tampered = list(proof)
        tampered[0], tampered[1] = tampered[1], tampered[0]
        self.assertFalse(self._verify(b"alice", b"data_alice", tampered, root))


class TestAuthDbNonMembership(unittest.TestCase):

    def setUp(self):
        from apps.authdb.lookup import _verify_nonmembership
        self._verify_nm = _verify_nonmembership

    def test_nonmember_valid(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"  # not in ENTRIES
        w_addr, w_val = find_witness(ENTRIES, target)
        _, proof = build_mpt_root_and_proof(ENTRIES, w_addr)
        self.assertTrue(self._verify_nm(target, w_addr, w_val, proof, root))

    def test_nonmember_wrong_witness_value(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"
        w_addr, w_val = find_witness(ENTRIES, target)
        _, proof = build_mpt_root_and_proof(ENTRIES, w_addr)
        self.assertFalse(self._verify_nm(target, w_addr, b"WRONG", proof, root))

    def test_nonmember_witness_equals_target_fails(self):
        # If witness_address == address, non-membership is false
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertFalse(self._verify_nm(b"alice", b"alice", b"data_alice", proof, root))

    def test_nonmember_tampered_proof(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"
        w_addr, w_val = find_witness(ENTRIES, target)
        _, proof = build_mpt_root_and_proof(ENTRIES, w_addr)
        if proof:
            tampered = list(proof)
            tampered[0] = bytes([tampered[0][0]]) + _sha256d(b"garbage")
            self.assertFalse(self._verify_nm(target, w_addr, w_val, tampered, root))


class TestAuthDbStorageIsolation(unittest.TestCase):
    """Storage-level functional + adversarial coverage for core/src/storage/authdb.py.

    Uses AuthDbSetDeviceId-style wallet_id switching (here done directly at
    the storage layer) to emulate multiple devices/wallets sharing one
    physical flash, the same trick the device tests use via the debug-only
    AuthDbSetDeviceId RPC.
    """

    def _id(self, n):
        return _sha256d(b"identity-%d" % n)

    def _root(self, n):
        return _sha256d(b"root-%d" % n)

    @mock_storage
    def test_roots_isolated_per_wallet(self):
        import storage.authdb as authdb

        id_a, id_b = self._id(1), self._id(2)
        root_a, root_b = self._root(1), self._root(2)

        authdb.set_root(id_a, root_a)
        authdb.set_root(id_b, root_b)

        self.assertEqual(authdb.get_root(id_a), root_a)
        self.assertEqual(authdb.get_root(id_b), root_b)
        # Counters advance independently per wallet.
        self.assertEqual(authdb.get_counter(id_a), 0)
        authdb.increment_counter(id_a)
        self.assertEqual(authdb.get_counter(id_a), 1)
        self.assertEqual(authdb.get_counter(id_b), 0)

    @mock_storage
    def test_wallet_table_capacity_enforced(self):
        import storage.authdb as authdb

        for n in range(authdb.MAX_WALLETS):
            authdb.set_root(self._id(n), self._root(n))

        with self.assertRaises(ValueError):
            authdb.set_root(self._id(authdb.MAX_WALLETS), self._root(999))

        # Existing wallets remain intact after the rejected insert.
        self.assertEqual(authdb.get_root(self._id(0)), self._root(0))

    @mock_storage
    def test_cache_capacity_enforced(self):
        import storage.authdb as authdb

        for n in range(authdb.MAX_CACHE_ENTRIES):
            authdb.set_cache_entry(b"addr-%d" % n, "label-%d" % n, None)

        with self.assertRaises(ValueError):
            authdb.set_cache_entry(b"addr-overflow", "label-overflow", None)

        authdb.wipe_cache()
        # After wiping, capacity is available again.
        authdb.set_cache_entry(b"addr-overflow", "label-overflow", None)
        label, _mac = authdb.get_cache_entry(b"addr-overflow")
        self.assertEqual(label, "label-overflow")

    @mock_storage
    def test_cache_not_isolated_per_wallet(self):
        """BUG regression test — cache is NOT scoped by wallet_id.

        Unlike `_ROOTS` (keyed table, see test_roots_isolated_per_wallet),
        `_CACHE` in core/src/storage/authdb.py is a single flat blob with no
        wallet_id column at all. Switching wallet (as AuthDbSetDeviceId
        does) does not isolate offline-cache entries between wallets
        sharing one physical device. This asserts *today's* behavior; if the
        cache storage is fixed to be wallet-scoped, this test must be
        flipped to assertIsNone (see docs/authdb.md and the sync-protocol
        review notes on cache isolation).
        """
        import storage.authdb as authdb

        # No device_id/wallet_id parameter exists on these calls at all —
        # that's the bug: cache entries have no wallet scoping.
        authdb.set_cache_entry(b"shared-addr", "label-for-wallet-A", None)

        label, _mac = authdb.get_cache_entry(b"shared-addr")
        # A "different wallet" (post AuthDbSetDeviceId switch) still sees
        # wallet A's cache entry — leakage across wallets.
        self.assertEqual(label, "label-for-wallet-A")


class TestAuthDbOfflineQueueStorage(unittest.TestCase):
    """Storage-level functional + adversarial coverage for the offline sync
    additions to core/src/storage/authdb.py (queue + per-wallet counters).
    """

    def _id(self, n):
        return _sha256d(b"sync-identity-%d" % n)

    @mock_storage
    def test_sequence_assignment_monotonic_per_wallet(self):
        import storage.authdb as authdb

        id_a, id_b = self._id(1), self._id(2)
        self.assertEqual(authdb.get_next_sequence(id_a), 1)

        self.assertEqual(authdb.take_next_sequence(id_a), 1)
        self.assertEqual(authdb.take_next_sequence(id_a), 2)
        self.assertEqual(authdb.take_next_sequence(id_a), 3)

        # Independent per wallet.
        self.assertEqual(authdb.take_next_sequence(id_b), 1)
        self.assertEqual(authdb.get_next_sequence(id_a), 4)

    @mock_storage
    def test_queue_append_and_fifo_order(self):
        import storage.authdb as authdb

        wallet_id = self._id(1)
        for n in range(3):
            seq = authdb.take_next_sequence(wallet_id)
            authdb.append_offline_operation(
                wallet_id, seq, b"addr-%d" % n, b"", b"val-%d" % n, b"\x00" * 32
            )

        queue = authdb.get_offline_queue(wallet_id)
        self.assertEqual([e[0] for e in queue], [1, 2, 3])
        self.assertEqual([e[1] for e in queue], [b"addr-0", b"addr-1", b"addr-2"])

    @mock_storage
    def test_queue_isolated_per_wallet(self):
        """Unlike the offline *cache* (see test_cache_not_isolated_per_wallet),
        the offline *queue* is wallet_id-scoped from the start."""
        import storage.authdb as authdb

        id_a, id_b = self._id(1), self._id(2)
        seq_a = authdb.take_next_sequence(id_a)
        authdb.append_offline_operation(id_a, seq_a, b"addr", b"", b"val-a", b"\x00" * 32)

        self.assertEqual(len(authdb.get_offline_queue(id_a)), 1)
        self.assertEqual(authdb.get_offline_queue(id_b), [])

    @mock_storage
    def test_queue_capacity_enforced_per_wallet(self):
        import storage.authdb as authdb

        wallet_id = self._id(1)
        for n in range(authdb.MAX_OFFLINE_QUEUE_ENTRIES):
            seq = authdb.take_next_sequence(wallet_id)
            authdb.append_offline_operation(
                wallet_id, seq, b"addr-%d" % n, b"", b"val-%d" % n, b"\x00" * 32
            )

        overflow_seq = authdb.take_next_sequence(wallet_id)
        with self.assertRaises(ValueError):
            authdb.append_offline_operation(
                wallet_id, overflow_seq, b"addr-overflow", b"", b"val", b"\x00" * 32
            )

        # A different wallet is unaffected by wallet A's full queue.
        other = self._id(2)
        other_seq = authdb.take_next_sequence(other)
        authdb.append_offline_operation(other, other_seq, b"addr", b"", b"val", b"\x00" * 32)
        self.assertEqual(len(authdb.get_offline_queue(other)), 1)

    @mock_storage
    def test_gc_only_deletes_upto_watermark(self):
        """Regression guard for the GC design: deleting must never remove a
        sequence above last_applied_sequence, even if the caller (mistakenly
        or maliciously) asks for more -- delete_offline_operations_upto only
        ever receives the device's OWN persisted watermark from the RPC
        handler, but the storage function itself must still honor whatever
        boundary it's given precisely, with no off-by-one drift."""
        import storage.authdb as authdb

        wallet_id = self._id(1)
        for n in range(5):
            seq = authdb.take_next_sequence(wallet_id)
            authdb.append_offline_operation(
                wallet_id, seq, b"addr-%d" % n, b"", b"val-%d" % n, b"\x00" * 32
            )

        deleted = authdb.delete_offline_operations_upto(wallet_id, 3)
        self.assertEqual(deleted, 3)
        remaining = authdb.get_offline_queue(wallet_id)
        self.assertEqual([e[0] for e in remaining], [4, 5])

        # A second wallet's queue must be untouched.
        other = self._id(2)
        other_seq = authdb.take_next_sequence(other)
        authdb.append_offline_operation(other, other_seq, b"addr", b"", b"val", b"\x00" * 32)
        deleted_none = authdb.delete_offline_operations_upto(wallet_id, 0)
        self.assertEqual(deleted_none, 0)
        self.assertEqual(len(authdb.get_offline_queue(other)), 1)

    @mock_storage
    def test_last_applied_sequence_defaults_and_persists(self):
        import storage.authdb as authdb

        wallet_id = self._id(1)
        self.assertEqual(authdb.get_last_applied_sequence(wallet_id), 0)

        authdb.set_last_applied_sequence(wallet_id, 7)
        self.assertEqual(authdb.get_last_applied_sequence(wallet_id), 7)

        # Unrelated to the root/counter table: clearing a (hypothetical) root
        # for this wallet_id must not reset sync bookkeeping, since they are
        # deliberately stored in separate namespaces (_ROOTS vs _SYNC).
        authdb.set_root(wallet_id, _sha256d(b"some-root"))
        authdb.clear_root(wallet_id)
        self.assertEqual(authdb.get_last_applied_sequence(wallet_id), 7)

    @mock_storage
    def test_sync_wallet_table_capacity_enforced(self):
        import storage.authdb as authdb

        for n in range(authdb.MAX_SYNC_WALLETS):
            authdb.take_next_sequence(self._id(100 + n))

        with self.assertRaises(ValueError):
            authdb.take_next_sequence(self._id(999))


if __name__ == "__main__":
    unittest.main()
