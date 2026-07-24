from common import await_result, unittest

from mock_storage import mock_storage
from trezor.crypto.hashlib import sha256


# ---------------------------------------------------------------------------
# MPT primitives (must match lookup.py and authdb_tree.py)
# ---------------------------------------------------------------------------

def _sha256d(data):
    return sha256(data).digest()


def _addr_bit(addr_hash, bit):
    return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1


def _leaf_hash(address, counter, value):
    return _sha256d(b"\x00" + address + counter.to_bytes(4, "big") + value)


def _internal_hash(left, right):
    return _sha256d(b"\x01" + left + right)


# ---------------------------------------------------------------------------
# MPT builder — returns (root, proof) for target_address
#
# Every entry in ENTRIES-style dicts here is a fresh, single insert, so the
# helpers below hard-code counter=1 for every leaf -- these fixtures don't
# model multi-write-per-address history (see TestAuthDbComputeNewRoot for
# tests that do, with explicit counters).
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
    """Build an MPT (every leaf at counter=1) and return (root_hash, proof)
    for target_address.

    proof is in leaf-to-root order; each element is 33 bytes:
    1-byte bit-position + 32-byte sibling hash.
    """
    leaves = [(_sha256d(a), _leaf_hash(a, 1, v)) for a, v in entries.items()]
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
    """Find the witness leaf for a non-membership proof (leaf occupying
    target's path). Returns (witness_address, witness_counter, witness_value);
    witness_counter is always 1, matching build_mpt_root_and_proof's fixtures."""
    target_hash = _sha256d(target_address)
    leaves = [(_sha256d(a), a, v) for a, v in entries.items()]
    root_node = _build_mpt(
        [(ah, _leaf_hash(a, 1, v)) for ah, a, v in leaves], 0
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
    w_addr, w_val = leaf_map[witness_addr_hash]
    return w_addr, 1, w_val


ENTRIES = {b"alice": b"data_alice", b"bob": b"data_bob",
           b"carol": b"data_carol", b"dave": b"data_dave"}


class TestAuthDbVerifyProof(unittest.TestCase):

    def setUp(self):
        from apps.ward.service import verify_proof as _verify_proof
        self._verify = _verify_proof

    def test_valid_proof_alice(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertTrue(self._verify(b"alice", 1, b"data_alice", proof, root))

    def test_valid_proof_bob(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"bob")
        self.assertTrue(self._verify(b"bob", 1, b"data_bob", proof, root))

    def test_valid_proof_carol(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"carol")
        self.assertTrue(self._verify(b"carol", 1, b"data_carol", proof, root))

    def test_invalid_wrong_value(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertFalse(self._verify(b"alice", 1, b"WRONG_VALUE", proof, root))

    def test_invalid_wrong_counter(self):
        # Same address/value, wrong counter -- must not validate: counter is
        # part of the leaf hash preimage, not just documentation.
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertFalse(self._verify(b"alice", 2, b"data_alice", proof, root))

    def test_invalid_wrong_address(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        # alice's proof applied with bob's address → wrong bit decisions
        self.assertFalse(self._verify(b"bob", 1, b"data_alice", proof, root))

    def test_invalid_tampered_sibling(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        tampered = list(proof)
        tampered[0] = bytes([tampered[0][0]]) + _sha256d(b"garbage")
        self.assertFalse(self._verify(b"alice", 1, b"data_alice", tampered, root))

    def test_invalid_wrong_root(self):
        _, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        wrong_root = _sha256d(b"not the root")
        self.assertFalse(self._verify(b"alice", 1, b"data_alice", proof, wrong_root))

    def test_single_entry_tree(self):
        root, proof = build_mpt_root_and_proof({b"solo": b"val"}, b"solo")
        self.assertTrue(self._verify(b"solo", 1, b"val", proof, root))
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
        self.assertFalse(self._verify(b"alice", 1, b"data_alice", tampered, root))

    def test_invalid_extra_proof_element(self):
        # Appending a bogus extra element must not still validate.
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        tampered = list(proof) + [bytes([0]) + _sha256d(b"bogus")]
        self.assertFalse(self._verify(b"alice", 1, b"data_alice", tampered, root))

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
        self.assertFalse(self._verify(b"alice", 1, b"data_alice", tampered, root))


class TestAuthDbNonMembership(unittest.TestCase):

    def setUp(self):
        from apps.ward.service import verify_nonmembership as _verify_nonmembership
        self._verify_nm = _verify_nonmembership

    def test_nonmember_valid(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"  # not in ENTRIES
        w_addr, w_counter, w_val = find_witness(ENTRIES, target)
        _, proof = build_mpt_root_and_proof(ENTRIES, w_addr)
        self.assertTrue(self._verify_nm(target, w_addr, w_counter, w_val, proof, root))

    def test_nonmember_wrong_witness_value(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"
        w_addr, w_counter, w_val = find_witness(ENTRIES, target)
        _, proof = build_mpt_root_and_proof(ENTRIES, w_addr)
        self.assertFalse(self._verify_nm(target, w_addr, w_counter, b"WRONG", proof, root))

    def test_nonmember_wrong_witness_counter(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"
        w_addr, w_counter, w_val = find_witness(ENTRIES, target)
        _, proof = build_mpt_root_and_proof(ENTRIES, w_addr)
        self.assertFalse(self._verify_nm(target, w_addr, w_counter + 1, w_val, proof, root))

    def test_nonmember_witness_equals_target_fails(self):
        # If witness_address == address, non-membership is false
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertFalse(self._verify_nm(b"alice", b"alice", 1, b"data_alice", proof, root))

    def test_nonmember_tampered_proof(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"
        w_addr, w_counter, w_val = find_witness(ENTRIES, target)
        _, proof = build_mpt_root_and_proof(ENTRIES, w_addr)
        if proof:
            tampered = list(proof)
            tampered[0] = bytes([tampered[0][0]]) + _sha256d(b"garbage")
            self.assertFalse(self._verify_nm(target, w_addr, w_counter, w_val, tampered, root))


class TestAuthDbStorageIsolation(unittest.TestCase):
    """Storage-level functional + adversarial coverage for core/src/storage/ward_store.py.

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
        import storage.ward_store as ward_store

        id_a, id_b = self._id(1), self._id(2)
        root_a, root_b = self._root(1), self._root(2)

        ward_store.set_root(id_a, root_a)
        ward_store.set_root(id_b, root_b)

        self.assertEqual(ward_store.get_root(id_a), root_a)
        self.assertEqual(ward_store.get_root(id_b), root_b)
        # Counters advance independently per wallet.
        self.assertEqual(ward_store.get_counter(id_a), 0)
        ward_store.increment_counter(id_a)
        self.assertEqual(ward_store.get_counter(id_a), 1)
        self.assertEqual(ward_store.get_counter(id_b), 0)

    @mock_storage
    def test_wallet_table_capacity_enforced(self):
        import storage.ward_store as ward_store

        for n in range(ward_store.MAX_WALLETS):
            ward_store.set_root(self._id(n), self._root(n))

        with self.assertRaises(ValueError):
            ward_store.set_root(self._id(ward_store.MAX_WALLETS), self._root(999))

        # Existing wallets remain intact after the rejected insert.
        self.assertEqual(ward_store.get_root(self._id(0)), self._root(0))

    @mock_storage
    def test_cache_capacity_enforced(self):
        import storage.ward_store as ward_store

        for n in range(ward_store.MAX_CACHE_ENTRIES):
            ward_store.set_cache_entry(b"addr-%d" % n, "label-%d" % n, None)

        with self.assertRaises(ValueError):
            ward_store.set_cache_entry(b"addr-overflow", "label-overflow", None)

        ward_store.wipe_cache()
        # After wiping, capacity is available again.
        ward_store.set_cache_entry(b"addr-overflow", "label-overflow", None)
        label, _mac = ward_store.get_cache_entry(b"addr-overflow")
        self.assertEqual(label, "label-overflow")

    @mock_storage
    def test_cache_not_isolated_per_wallet(self):
        """BUG regression test — cache is NOT scoped by wallet_id.

        Unlike `_ROOTS` (keyed table, see test_roots_isolated_per_wallet),
        `_CACHE` in core/src/storage/ward_store.py is a single flat blob with no
        wallet_id column at all. Switching wallet (as AuthDbSetDeviceId
        does) does not isolate offline-cache entries between wallets
        sharing one physical device. This asserts *today's* behavior; if the
        cache storage is fixed to be wallet-scoped, this test must be
        flipped to assertIsNone (see docs/ward_store.md and the sync-protocol
        review notes on cache isolation).
        """
        import storage.ward_store as ward_store

        # No device_id/wallet_id parameter exists on these calls at all —
        # that's the bug: cache entries have no wallet scoping.
        ward_store.set_cache_entry(b"shared-addr", "label-for-wallet-A", None)

        label, _mac = ward_store.get_cache_entry(b"shared-addr")
        # A "different wallet" (post AuthDbSetDeviceId switch) still sees
        # wallet A's cache entry — leakage across wallets.
        self.assertEqual(label, "label-for-wallet-A")


class TestAuthDbOfflineQueueStorage(unittest.TestCase):
    """Storage-level functional + adversarial coverage for the offline sync
    additions to core/src/storage/ward_store.py (queue + per-wallet sequencing).
    """

    def _id(self, n):
        return _sha256d(b"sync-identity-%d" % n)

    @mock_storage
    def test_sequence_derived_monotonic_per_wallet(self):
        """peek_next_sequence() is a pure derived read (no separate persisted
        counter, see storage/ward_store.py's comment on why that was removed):
        it only advances once an operation carrying that sequence is
        actually, durably appended."""
        import storage.ward_store as ward_store

        id_a, id_b = self._id(1), self._id(2)
        self.assertEqual(ward_store.peek_next_sequence(id_a), 1)

        for n in range(3):
            seq = ward_store.peek_next_sequence(id_a)
            self.assertEqual(seq, n + 1)
            ward_store.append_offline_operation(
                id_a, seq, b"addr-%d" % n, 0, b"", 1, b"val-%d" % n, b"\x00" * 32
            )

        # Independent per wallet.
        self.assertEqual(ward_store.peek_next_sequence(id_b), 1)
        self.assertEqual(ward_store.peek_next_sequence(id_a), 4)

    @mock_storage
    def test_queue_append_and_fifo_order(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        for n in range(3):
            seq = ward_store.peek_next_sequence(wallet_id)
            ward_store.append_offline_operation(
                wallet_id, seq, b"addr-%d" % n, 0, b"", 1, b"val-%d" % n, b"\x00" * 32
            )

        queue = ward_store.get_offline_queue(wallet_id)
        self.assertEqual([e[0] for e in queue], [1, 2, 3])
        self.assertEqual([e[1] for e in queue], [b"addr-0", b"addr-1", b"addr-2"])
        self.assertEqual([e[4] for e in queue], [1, 1, 1])  # new_counter

    @mock_storage
    def test_queue_isolated_per_wallet(self):
        """Unlike the offline *cache* (see test_cache_not_isolated_per_wallet),
        the offline *queue* is wallet_id-scoped from the start."""
        import storage.ward_store as ward_store

        id_a, id_b = self._id(1), self._id(2)
        seq_a = ward_store.peek_next_sequence(id_a)
        ward_store.append_offline_operation(id_a, seq_a, b"addr", 0, b"", 1, b"val-a", b"\x00" * 32)

        self.assertEqual(len(ward_store.get_offline_queue(id_a)), 1)
        self.assertEqual(ward_store.get_offline_queue(id_b), [])

    @mock_storage
    def test_queue_capacity_enforced_per_wallet(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        for n in range(ward_store.MAX_OFFLINE_QUEUE_ENTRIES):
            seq = ward_store.peek_next_sequence(wallet_id)
            ward_store.append_offline_operation(
                wallet_id, seq, b"addr-%d" % n, 0, b"", 1, b"val-%d" % n, b"\x00" * 32
            )

        overflow_seq = ward_store.peek_next_sequence(wallet_id)
        with self.assertRaises(ValueError):
            ward_store.append_offline_operation(
                wallet_id, overflow_seq, b"addr-overflow", 0, b"", 1, b"val", b"\x00" * 32
            )

        # A different wallet is unaffected by wallet A's full queue.
        other = self._id(2)
        other_seq = ward_store.peek_next_sequence(other)
        ward_store.append_offline_operation(other, other_seq, b"addr", 0, b"", 1, b"val", b"\x00" * 32)
        self.assertEqual(len(ward_store.get_offline_queue(other)), 1)

    @mock_storage
    def test_gc_only_deletes_upto_watermark(self):
        """Regression guard for the GC design: deleting must never remove a
        sequence above last_applied_sequence, even if the caller (mistakenly
        or maliciously) asks for more -- delete_offline_operations_upto only
        ever receives the device's OWN persisted watermark from the RPC
        handler, but the storage function itself must still honor whatever
        boundary it's given precisely, with no off-by-one drift."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        for n in range(5):
            seq = ward_store.peek_next_sequence(wallet_id)
            ward_store.append_offline_operation(
                wallet_id, seq, b"addr-%d" % n, 0, b"", 1, b"val-%d" % n, b"\x00" * 32
            )

        deleted = ward_store.delete_offline_operations_upto(wallet_id, 3)
        self.assertEqual(deleted, 3)
        remaining = ward_store.get_offline_queue(wallet_id)
        self.assertEqual([e[0] for e in remaining], [4, 5])

        # A second wallet's queue must be untouched.
        other = self._id(2)
        other_seq = ward_store.peek_next_sequence(other)
        ward_store.append_offline_operation(other, other_seq, b"addr", 0, b"", 1, b"val", b"\x00" * 32)
        deleted_none = ward_store.delete_offline_operations_upto(wallet_id, 0)
        self.assertEqual(deleted_none, 0)
        self.assertEqual(len(ward_store.get_offline_queue(other)), 1)

    @mock_storage
    def test_sequence_not_burned_by_crash_between_append_calls(self):
        """Regression guard for item 3's fix: peek_next_sequence() derives
        from durable queue contents + last_applied_sequence, so there is no
        separate reservation step whose completion could desync from what
        was actually appended -- simulate a "crash" by simply calling peek
        again without appending, and confirm it's still consistent."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        seq = ward_store.peek_next_sequence(wallet_id)
        self.assertEqual(seq, 1)
        # "Crash" before append: peeking again must still return 1, not 2 --
        # there is nothing to have reserved-and-lost.
        self.assertEqual(ward_store.peek_next_sequence(wallet_id), 1)

        ward_store.append_offline_operation(wallet_id, seq, b"addr", 0, b"", 1, b"val", b"\x00" * 32)
        self.assertEqual(ward_store.peek_next_sequence(wallet_id), 2)

    @mock_storage
    def test_last_applied_sequence_defaults_and_persists(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        self.assertEqual(ward_store.get_last_applied_sequence(wallet_id), 0)

        ward_store.set_last_applied_sequence(wallet_id, 7)
        self.assertEqual(ward_store.get_last_applied_sequence(wallet_id), 7)

        # last_applied_sequence lives in the same _ROOTS record as root/
        # counter (see commit_applied_operation()), but clear_root() only
        # ever sets the root field to the EMPTY_ROOT sentinel -- it no
        # longer deletes the record -- so clearing a root must not reset
        # sync bookkeeping.
        ward_store.set_root(wallet_id, _sha256d(b"some-root"))
        ward_store.clear_root(wallet_id)
        self.assertEqual(ward_store.get_last_applied_sequence(wallet_id), 7)
        self.assertIsNone(ward_store.get_root(wallet_id))

    @mock_storage
    def test_clear_root_preserves_counter_and_record(self):
        """clear_root() must not delete the wallet's storage record anymore
        (regression guard: it used to, which broke increment_counter() on
        the very next write -- see update_leaf.py/apply_offline_operations.py
        history). Counter must survive a clear, and re-adding a root for the
        same wallet_id must not consume a fresh MAX_WALLETS slot."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        ward_store.set_root(wallet_id, _sha256d(b"root-1"))
        ward_store.increment_counter(wallet_id)
        ward_store.increment_counter(wallet_id)
        self.assertEqual(ward_store.get_counter(wallet_id), 2)

        ward_store.clear_root(wallet_id)
        self.assertIsNone(ward_store.get_root(wallet_id))
        self.assertEqual(ward_store.get_counter(wallet_id), 2)  # survives the clear

        # Counter continues from where it left off, not reset to 0.
        ward_store.set_root(wallet_id, _sha256d(b"root-2"))
        self.assertEqual(ward_store.increment_counter(wallet_id), 3)

    @mock_storage
    def test_set_root_rejects_empty_root_sentinel(self):
        import storage.ward_store as ward_store

        with self.assertRaises(ValueError):
            ward_store.set_root(self._id(1), ward_store.EMPTY_ROOT)

    @mock_storage
    def test_commit_applied_operation_is_a_single_write(self):
        """The atomicity fix: root, counter, and last_applied_sequence must
        all update together via ONE call, and a delete-to-empty (new_root is
        None) must not lose the record the way the old clear_root()-deletes-
        everything behavior did."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)

        # First-ever INIT via commit_applied_operation itself (creates the record).
        counter = ward_store.commit_applied_operation(wallet_id, _sha256d(b"root-1"), 1)
        self.assertEqual(counter, 1)
        self.assertEqual(ward_store.get_root(wallet_id), _sha256d(b"root-1"))
        self.assertEqual(ward_store.get_last_applied_sequence(wallet_id), 1)

        # UPDATE
        counter = ward_store.commit_applied_operation(wallet_id, _sha256d(b"root-2"), 2)
        self.assertEqual(counter, 2)
        self.assertEqual(ward_store.get_root(wallet_id), _sha256d(b"root-2"))
        self.assertEqual(ward_store.get_last_applied_sequence(wallet_id), 2)

        # DELETE-to-empty: root clears, counter/sequence still advance, and
        # the record survives (unlike the old 3-separate-writes behavior).
        counter = ward_store.commit_applied_operation(wallet_id, None, 3)
        self.assertEqual(counter, 3)
        self.assertIsNone(ward_store.get_root(wallet_id))
        self.assertEqual(ward_store.get_last_applied_sequence(wallet_id), 3)
        self.assertEqual(ward_store.get_counter(wallet_id), 3)  # not reset by the delete

    @mock_storage
    def test_commit_root_and_counter_single_write(self):
        """update_leaf.py/set_root.py's atomicity primitive: root+counter
        move together, incrementing by exactly 1 each call."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        counter = ward_store.commit_root_and_counter(wallet_id, _sha256d(b"root-1"))
        self.assertEqual(counter, 1)
        counter = ward_store.commit_root_and_counter(wallet_id, _sha256d(b"root-2"))
        self.assertEqual(counter, 2)
        self.assertEqual(ward_store.get_root(wallet_id), _sha256d(b"root-2"))

    @mock_storage
    def test_commit_root_and_counter_value_jumps_directly(self):
        """fast_forward_root.py/set_root.py's verified-mac atomicity
        primitive: jumps straight to an attested counter, not +1."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        ward_store.commit_root_and_counter_value(wallet_id, _sha256d(b"root-1"), 42)
        self.assertEqual(ward_store.get_counter(wallet_id), 42)
        self.assertEqual(ward_store.get_root(wallet_id), _sha256d(b"root-1"))

    @mock_storage
    def test_set_counter_direct_write(self):
        """set_counter() (used by fast_forward_root.py) jumps straight to an
        arbitrary value, unlike increment_counter()'s +1-only semantics."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        ward_store.set_root(wallet_id, _sha256d(b"root"))
        self.assertEqual(ward_store.get_counter(wallet_id), 0)

        ward_store.set_counter(wallet_id, 42)
        self.assertEqual(ward_store.get_counter(wallet_id), 42)

        # A subsequent increment continues from the jumped-to value.
        ward_store.increment_counter(wallet_id)
        self.assertEqual(ward_store.get_counter(wallet_id), 43)

        # A second wallet's counter is untouched.
        other = self._id(2)
        ward_store.set_root(other, _sha256d(b"other-root"))
        self.assertEqual(ward_store.get_counter(other), 0)

    @mock_storage
    def test_set_counter_requires_existing_record(self):
        import storage.ward_store as ward_store

        with self.assertRaises(ValueError):
            ward_store.set_counter(self._id(1), 5)


class TestAuthDbMpt(unittest.TestCase):
    """Cross-check apps.ward.service's extracted primitives against the same
    MPT fixtures used by TestAuthDbVerifyProof/TestAuthDbNonMembership above,
    to guarantee the extraction from update_leaf.py/lookup.py is
    behavior-preserving."""

    def setUp(self):
        from apps.ward import service as _mpt
        self.mpt = _mpt

    def test_leaf_and_internal_hash_match_local_helpers(self):
        self.assertEqual(
            self.mpt.leaf_hash(b"alice", 1, b"data"), _leaf_hash(b"alice", 1, b"data")
        )
        self.assertEqual(
            self.mpt.internal_hash(b"L" * 32, b"R" * 32),
            _internal_hash(b"L" * 32, b"R" * 32),
        )

    def test_verify_proof_matches_lookup_wrapper(self):
        from apps.ward.service import verify_proof as _verify_proof

        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertEqual(
            self.mpt.verify_proof(b"alice", 1, b"data_alice", proof, root),
            _verify_proof(b"alice", 1, b"data_alice", proof, root),
        )
        self.assertTrue(self.mpt.verify_proof(b"alice", 1, b"data_alice", proof, root))
        self.assertFalse(self.mpt.verify_proof(b"alice", 1, b"WRONG", proof, root))

    def test_verify_nonmembership_matches_lookup_wrapper(self):
        from apps.ward.service import verify_nonmembership as _verify_nonmembership

        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"
        w_addr, w_counter, w_val = find_witness(ENTRIES, target)
        _, proof = build_mpt_root_and_proof(ENTRIES, w_addr)
        self.assertEqual(
            self.mpt.verify_nonmembership(target, w_addr, w_counter, w_val, proof, root),
            _verify_nonmembership(target, w_addr, w_counter, w_val, proof, root),
        )
        self.assertTrue(self.mpt.verify_nonmembership(target, w_addr, w_counter, w_val, proof, root))


class TestAuthDbComputeNewRoot(unittest.TestCase):
    """Functional coverage for apps.ward.service.compute_new_root(), the
    single shared INIT/INSERT/UPDATE/DELETE state machine used by both
    update_leaf.py and apply_offline_operations.py.

    compute_new_root's positional signature is:
        (address, old_counter, old_value, new_counter, new_value, proof,
         stored_root, witness_address=None, witness_counter=None, witness_value=None)
    """

    def setUp(self):
        from apps.ward import service as _mpt
        self.mpt = _mpt

    def test_init_on_empty_tree(self):
        new_root = self.mpt.compute_new_root(b"alice", 0, b"", 1, b"data_alice", [], None)
        self.assertEqual(new_root, self.mpt.leaf_hash(b"alice", 1, b"data_alice"))

    def test_init_rejects_wrong_new_counter(self):
        with self.assertRaises(ValueError):
            self.mpt.compute_new_root(b"alice", 0, b"", 2, b"data_alice", [], None)

    def test_insert_into_existing_tree(self):
        entries = {b"alice": b"data_alice"}
        root, _ = build_mpt_root_and_proof(entries, b"alice")
        w_addr, w_counter, w_val = find_witness(entries, b"bob")
        _, proof = build_mpt_root_and_proof(entries, w_addr)

        new_root = self.mpt.compute_new_root(
            b"bob", 0, b"", 1, b"data_bob", proof, root,
            witness_address=w_addr, witness_counter=w_counter, witness_value=w_val,
        )

        expected_root, _ = build_mpt_root_and_proof(
            {b"alice": b"data_alice", b"bob": b"data_bob"}, b"alice"
        )
        self.assertEqual(new_root, expected_root)

    def test_update_existing_leaf(self):
        entries = {b"alice": b"data_alice", b"bob": b"data_bob"}
        root, proof = build_mpt_root_and_proof(entries, b"alice")

        new_root = self.mpt.compute_new_root(
            b"alice", 1, b"data_alice", 2, b"NEW_VAL", proof, root
        )

        # expected_root can't be built via build_mpt_root_and_proof (it
        # hard-codes counter=1 for every entry); reconstruct with the real
        # counter-2 leaf for alice directly.
        alice_leaf = self.mpt.leaf_hash(b"alice", 2, b"NEW_VAL")
        bob_leaf = self.mpt.leaf_hash(b"bob", 1, b"data_bob")
        # Same two-leaf tree shape build_mpt_root_and_proof would produce;
        # reuse its internal split-bit logic by rebuilding the addr-hash pair.
        from trezor.crypto.hashlib import sha256
        ah_alice, ah_bob = sha256(b"alice").digest(), sha256(b"bob").digest()
        bit = next(b for b in range(256) if _addr_bit(ah_alice, b) != _addr_bit(ah_bob, b))
        if _addr_bit(ah_alice, bit) == 0:
            expected_root = _internal_hash(alice_leaf, bob_leaf)
        else:
            expected_root = _internal_hash(bob_leaf, alice_leaf)
        self.assertEqual(new_root, expected_root)

    def test_update_rejects_wrong_new_counter(self):
        entries = {b"alice": b"data_alice", b"bob": b"data_bob"}
        root, proof = build_mpt_root_and_proof(entries, b"alice")
        with self.assertRaises(ValueError):
            # Skips from 1 straight to 3 -- must be old_counter+1 == 2.
            self.mpt.compute_new_root(b"alice", 1, b"data_alice", 3, b"NEW_VAL", proof, root)

    def test_delete_to_single_leaf_then_to_empty(self):
        entries = {b"alice": b"data_alice", b"bob": b"data_bob"}
        root, proof = build_mpt_root_and_proof(entries, b"bob")

        root_after_delete_bob = self.mpt.compute_new_root(
            b"bob", 1, b"data_bob", 0, b"", proof, root
        )
        self.assertEqual(root_after_delete_bob, self.mpt.leaf_hash(b"alice", 1, b"data_alice"))

        root_after_delete_alice = self.mpt.compute_new_root(
            b"alice", 1, b"data_alice", 0, b"", [], root_after_delete_bob
        )
        self.assertIsNone(root_after_delete_alice)

    def test_rejects_invalid_old_value_proof(self):
        entries = {b"alice": b"data_alice", b"bob": b"data_bob"}
        root, proof = build_mpt_root_and_proof(entries, b"bob")

        with self.assertRaises(ValueError):
            self.mpt.compute_new_root(b"bob", 1, b"WRONG_OLD", 0, b"", proof, root)

    def test_rejects_both_values_empty(self):
        with self.assertRaises(ValueError):
            self.mpt.compute_new_root(b"alice", 0, b"", 0, b"", [], None)

    def test_insert_into_empty_tree_with_witness_is_rejected(self):
        """Deliberately stricter than the original inline update_leaf.py logic
        (which only checked `stored_root is not None` before raising, so an
        empty tree silently skipped the witness-membership check entirely).
        compute_new_root() rejects unconditionally on any witness/stored_root
        mismatch, including this malformed-input edge case."""
        with self.assertRaises(ValueError):
            self.mpt.compute_new_root(
                b"bob", 0, b"", 1, b"data_bob", [bytes([0]) + b"S" * 32], None,
                witness_address=b"alice", witness_counter=1, witness_value=b"data_alice",
            )


class TestWardQueueStorage(unittest.TestCase):
    """Storage-level coverage for the WARD pending-candidate queue and the
    finalize commit (core/src/storage/ward_store.py: queue_* + commit_finalize)."""

    def _id(self, n):
        # wallet_id is a 20-byte BIP32 Hash160.
        return _sha256d(b"ward-wallet-%d" % n)[:20]

    @mock_storage
    def test_put_get_roundtrip(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        root = _sha256d(b"root-T")
        mac = _sha256d(b"mac-T")
        ward_store.queue_put(wallet_id, 5, root, mac, b"alice")

        rec = ward_store.queue_get(wallet_id)
        self.assertIsNotNone(rec)
        counter, got_root, got_mac, state, address = rec
        self.assertEqual(counter, 5)
        self.assertEqual(got_root, root)
        self.assertEqual(got_mac, mac)
        self.assertEqual(state, ward_store.QUEUE_PENDING)
        self.assertEqual(address, b"alice")

    @mock_storage
    def test_get_is_wallet_scoped(self):
        import storage.ward_store as ward_store

        ward_store.queue_put(self._id(1), 1, _sha256d(b"r"), _sha256d(b"m"), b"x")
        # A different wallet sees no candidate (single-record, wallet-tagged).
        self.assertIsNone(ward_store.queue_get(self._id(2)))

    @mock_storage
    def test_set_committed_and_drop(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        ward_store.queue_put(wallet_id, 1, _sha256d(b"r"), _sha256d(b"m"), b"x")
        ward_store.queue_set_committed(wallet_id)
        _c, _r, _m, state, _a = ward_store.queue_get(wallet_id)
        self.assertEqual(state, ward_store.QUEUE_COMMITTED)

        ward_store.queue_drop()
        self.assertIsNone(ward_store.queue_get(wallet_id))

    @mock_storage
    def test_set_committed_rejects_foreign_wallet(self):
        import storage.ward_store as ward_store

        ward_store.queue_put(self._id(1), 1, _sha256d(b"r"), _sha256d(b"m"), b"x")
        with self.assertRaises(ValueError):
            ward_store.queue_set_committed(self._id(2))

    @mock_storage
    def test_empty_candidate_roundtrip(self):
        """A DELETE-to-empty candidate stores EMPTY_ROOT and reads back as
        (counter, None, None, state, address)."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        ward_store.queue_put(wallet_id, 9, None, None, b"bob")
        counter, root, mac, _state, address = ward_store.queue_get(wallet_id)
        self.assertEqual(counter, 9)
        self.assertIsNone(root)
        self.assertIsNone(mac)
        self.assertEqual(address, b"bob")

    @mock_storage
    def test_commit_finalize_installs_and_advances_qm(self):
        """commit_finalize installs (root, counter) AND raises qm_last_counter
        to counter in one write -- WARDConfirmCommit's atomic advance."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        # Bootstrap a qm ceiling at 6 (fresh wallet, no root).
        ward_store.commit_init(wallet_id, 6, None, None)
        self.assertEqual(ward_store.get_qm_counter(wallet_id), 6)
        self.assertEqual(ward_store.get_counter(wallet_id), 0)

        root = _sha256d(b"final-root")
        ward_store.commit_finalize(wallet_id, root, 7)
        self.assertEqual(ward_store.get_counter(wallet_id), 7)
        self.assertEqual(ward_store.get_qm_counter(wallet_id), 7)  # ceiling advanced
        self.assertEqual(ward_store.get_root(wallet_id), root)

    @mock_storage
    def test_commit_finalize_empty_tree(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        ward_store.commit_finalize(wallet_id, None, 1)
        self.assertEqual(ward_store.get_counter(wallet_id), 1)
        self.assertIsNone(ward_store.get_root(wallet_id))


class TestWardCoreCapability(unittest.TestCase):
    """The Core (apps.common.ward) appId capability boundary that gates on-device
    Trezor App -> WARD calls. The verify path itself is covered by TestAuthDbMpt /
    the device test; here we cover only the capability check, which runs before any
    seed/root access."""

    def test_capability_map(self):
        from apps.common import ward as ward_core

        self.assertIn("lookup", ward_core._CAPABILITIES["bitcoin"])
        self.assertIn("lookup", ward_core._CAPABILITIES["ethereum"])
        # An app with no grant is absent from the map entirely.
        self.assertNotIn("wallet", ward_core._CAPABILITIES)

    def test_unauthorized_app_rejected(self):
        from apps.common import ward as ward_core
        from trezor.wire import DataError

        with self.assertRaises(DataError):
            await_result(ward_core.lookup_label("wallet", b"addr", b"v", [], 0))

    def test_unauthorized_capability_rejected(self):
        """bitcoin holds 'lookup' but not 'set_entry' -- the gate must reject the
        capability it wasn't granted (before hitting NotImplementedError)."""
        from apps.common import ward as ward_core
        from trezor.wire import DataError

        with self.assertRaises(DataError):
            await_result(ward_core.set_entry("bitcoin"))


class TestWardSyncStorage(unittest.TestCase):
    """The WARD sync-round context (_SYNC): nonce + attested checkpoint."""

    def _id(self, n):
        return _sha256d(b"ward-wallet-%d" % n)[:20]

    @mock_storage
    def test_begin_then_get(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        nonce = _sha256d(b"nonce-1")  # 32 bytes
        ward_store.sync_begin(wallet_id, nonce)
        got = ward_store.sync_get(wallet_id)
        self.assertIsNotNone(got)
        n, state, counter, mac = got
        self.assertEqual(n, nonce)
        self.assertEqual(state, ward_store.SYNC_NONCE)
        self.assertEqual(counter, 0)
        self.assertIsNone(mac)

    @mock_storage
    def test_set_attested(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        ward_store.sync_begin(wallet_id, _sha256d(b"nonce"))
        mac = _sha256d(b"mac-ext")
        ward_store.sync_set_attested(wallet_id, 7, mac)
        _n, state, counter, got_mac = ward_store.sync_get(wallet_id)
        self.assertEqual(state, ward_store.SYNC_ATTESTED)
        self.assertEqual(counter, 7)
        self.assertEqual(got_mac, mac)

    @mock_storage
    def test_attested_empty_tree_mac_is_none(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        ward_store.sync_begin(wallet_id, _sha256d(b"nonce"))
        ward_store.sync_set_attested(wallet_id, 3, None)  # empty tree
        _n, _state, counter, mac = ward_store.sync_get(wallet_id)
        self.assertEqual(counter, 3)
        self.assertIsNone(mac)

    @mock_storage
    def test_wallet_scoped_and_clear(self):
        import storage.ward_store as ward_store

        ward_store.sync_begin(self._id(1), _sha256d(b"nonce"))
        self.assertIsNone(ward_store.sync_get(self._id(2)))
        ward_store.sync_clear()
        self.assertIsNone(ward_store.sync_get(self._id(1)))

    @mock_storage
    def test_set_attested_requires_round(self):
        import storage.ward_store as ward_store

        with self.assertRaises(ValueError):
            ward_store.sync_set_attested(self._id(1), 1, None)


class TestWardAttestation(unittest.TestCase):
    """verify_wm_attestation against the debug WM key (available under __debug__)."""

    def _id(self, n):
        return _sha256d(b"ward-wallet-%d" % n)[:20]

    def _preimage(self, nonce, wallet_id, counter, mac):
        return (
            b"WARD ATTEST v1" + bytes([1]) + nonce + wallet_id
            + counter.to_bytes(4, "big") + mac
        )

    def test_valid_attestation_accepted(self):
        from trezor.crypto.curve import ed25519
        from apps.ward.service import verify_wm_attestation

        seed = b"AUTHDB QM DEBUG KEY SEED v1 ...."  # 32 bytes, matches _WM_PUBKEY_DEBUG
        wallet_id = self._id(1)
        nonce = _sha256d(b"nonce")
        mac = _sha256d(b"mac")
        counter = 5
        sig = ed25519.sign(seed, self._preimage(nonce, wallet_id, counter, mac))
        self.assertTrue(verify_wm_attestation(wallet_id, nonce, counter, mac, sig))

    def test_tampered_counter_rejected(self):
        from trezor.crypto.curve import ed25519
        from apps.ward.service import verify_wm_attestation

        seed = b"AUTHDB QM DEBUG KEY SEED v1 ...."
        wallet_id = self._id(1)
        nonce = _sha256d(b"nonce")
        mac = _sha256d(b"mac")
        sig = ed25519.sign(seed, self._preimage(nonce, wallet_id, 5, mac))
        # verify against a different counter -> preimage mismatch -> rejected
        self.assertFalse(verify_wm_attestation(wallet_id, nonce, 6, mac, sig))


if __name__ == "__main__":
    unittest.main()
