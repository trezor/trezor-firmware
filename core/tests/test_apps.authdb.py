from common import await_result, unittest

from mock_storage import mock_storage
from trezor.crypto.hashlib import sha256


# ---------------------------------------------------------------------------
# WARD storage + core-capability + attestation unit tests.
#
# The MPT/proof algorithm and the keyed encrypted-leaf model are covered by the
# trezorlib crypto tests (python/tests/test_ward_crypto.py), the device tests
# (tests/device_tests/misc/test_ward*.py), and the CPython self-check
# (tools/ward_batch_selfcheck.py). This module covers the on-device storage
# (pending queue, batch envelope, sync context), the Core capability gate, and WM
# attestation verification.
# ---------------------------------------------------------------------------

def _sha256d(data):
    return sha256(data).digest()


class TestWardQueueStorage(unittest.TestCase):
    """Storage-level coverage for the WARD pending-candidate queue and the in-flight
    batch envelope (core/src/storage/ward_store.py: queue_* + batch_*)."""

    def _id(self, n):
        # wallet_id is a 20-byte BIP32 Hash160.
        return _sha256d(b"ward-wallet-%d" % n)[:20]

    @mock_storage
    def test_put_get_roundtrip(self):
        """An intent is stored PENDING with counter/address/old/new and NO root/mac
        (pull model: root/mac are computed later at perform)."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(wallet_id, pid, 5, b"alice", b"old_a", b"new_a", b"bitcoin")

        rec = ward_store.queue_get(wallet_id, pid)
        self.assertIsNotNone(rec)
        counter, state, address, ov, nv, root, mac, _aid, kt, did = rec
        # A default-scope intent frames key_type/device_id ("address"/0).
        self.assertEqual(kt, b"address")
        self.assertEqual(did, 0)
        self.assertEqual(counter, 5)
        self.assertEqual(state, ward_store.QUEUE_PENDING)
        self.assertEqual(address, b"alice")
        self.assertEqual(ov, b"old_a")
        self.assertEqual(nv, b"new_a")
        self.assertIsNone(root)  # not computed until perform
        self.assertIsNone(mac)

    @mock_storage
    def test_get_is_wallet_scoped(self):
        import storage.ward_store as ward_store

        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(self._id(1), pid, 1, b"x", b"o", b"n")
        # A different wallet does not see this pending_id's intent.
        self.assertIsNone(ward_store.queue_get(self._id(2), pid))

    @mock_storage
    def test_alloc_id_is_monotonic_and_unique(self):
        import storage.ward_store as ward_store

        ids = [ward_store.queue_alloc_id() for _ in range(4)]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(set(ids)), len(ids))

    @mock_storage
    def test_multi_slot_coexist(self):
        """Several intents coexist under distinct pending_ids for one wallet,
        each retrievable and independently droppable."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        p1 = ward_store.queue_alloc_id()
        p2 = ward_store.queue_alloc_id()
        ward_store.queue_put(wallet_id, p1, 5, b"alice", b"o1", b"n1", b"bitcoin")
        ward_store.queue_put(wallet_id, p2, 5, b"bob", b"o2", b"n2", b"bitcoin")

        self.assertEqual(ward_store.queue_count(wallet_id), 2)
        self.assertEqual(
            ward_store.queue_list(wallet_id), [(p1, b"alice"), (p2, b"bob")]
        )

        # Dropping one leaves the other intact.
        self.assertTrue(ward_store.queue_drop(wallet_id, p1))
        self.assertIsNone(ward_store.queue_get(wallet_id, p1))
        self.assertIsNotNone(ward_store.queue_get(wallet_id, p2))
        self.assertEqual(ward_store.queue_count(wallet_id), 1)

    @mock_storage
    def test_put_replaces_same_pending_id(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(wallet_id, pid, 5, b"alice", b"o1", b"n1", b"bitcoin")
        ward_store.queue_put(wallet_id, pid, 6, b"alice2", b"o2", b"n2", b"bitcoin")
        self.assertEqual(ward_store.queue_count(wallet_id), 1)
        counter, _s, address, ov, nv, _r, _m, _aid, _kt, _did = ward_store.queue_get(
            wallet_id, pid
        )
        self.assertEqual(counter, 6)
        self.assertEqual(address, b"alice2")
        self.assertEqual((ov, nv), (b"o2", b"n2"))

    @mock_storage
    def test_key_type_device_id_roundtrip(self):
        """Gap 6: a non-default key_type/device_id are framed at queue time and read
        back verbatim (they scope the entry_key the candidate lands on)."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(
            wallet_id, pid, 5, b"alice", b"o", b"n", b"bitcoin", b"eth_addr", 3
        )
        _c, _s, address, _ov, _nv, _r, _m, app_id, kt, did = ward_store.queue_get(
            wallet_id, pid
        )
        self.assertEqual(app_id, b"bitcoin")
        self.assertEqual(kt, b"eth_addr")
        self.assertEqual(did, 3)
        self.assertEqual(address, b"alice")

    @mock_storage
    def test_key_type_device_id_survive_set_computed(self):
        """The scope tail is preserved across the PENDING -> COMMITTED re-encode."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(
            wallet_id, pid, 0, b"alice", b"o", b"n", b"bitcoin", b"eth_addr", 3
        )
        ward_store.queue_set_computed(wallet_id, pid, 4, _sha256d(b"r"), _sha256d(b"m"))
        _c, state, _a, _ov, _nv, _r, _m, app_id, kt, did = ward_store.queue_get(
            wallet_id, pid
        )
        self.assertEqual(state, ward_store.QUEUE_COMMITTED)
        self.assertEqual(app_id, b"bitcoin")
        self.assertEqual(kt, b"eth_addr")
        self.assertEqual(did, 3)

    @mock_storage
    def test_legacy_record_without_scope_decodes_to_defaults(self):
        """Gap 6 backward-compat: a record framed before key_type/device_id existed
        (body ends at app_id) reads its scope tail past-end as (b"", 0)."""
        import storage.ward_store as ward_store

        # A pre-Gap6 body: prefix + LV(address)+LV(old)+LV(new)+LV(app_id), no scope tail.
        legacy = (
            (1).to_bytes(4, "big")  # pending_id
            + self._id(1)  # wallet_id (20B)
            + (7).to_bytes(4, "big")  # counter
            + bytes([ward_store.QUEUE_COMMITTED])  # state
            + _sha256d(b"root")  # root (32B, != EMPTY_ROOT)
            + _sha256d(b"mac")  # mac (32B)
            + len(b"alice").to_bytes(2, "big")
            + b"alice"
            + len(b"o").to_bytes(2, "big")
            + b"o"
            + len(b"n").to_bytes(2, "big")
            + b"n"
            + len(b"bitcoin").to_bytes(2, "big")
            + b"bitcoin"
        )
        counter, _s, address, ov, nv, _r, _m, app_id, kt, did = ward_store._parse_body(
            legacy
        )
        self.assertEqual(counter, 7)
        self.assertEqual((address, ov, nv), (b"alice", b"o", b"n"))
        self.assertEqual(app_id, b"bitcoin")
        self.assertEqual(kt, b"")  # scope tail read past end -> empty
        self.assertEqual(did, 0)

    @mock_storage
    def test_batch_envelope_roundtrip(self):
        """batch-update: the in-flight committed batch envelope round-trips its
        transition, MACs, optional signature and pending-id set."""
        import storage.ward_store as ward_store

        wid = self._id(1)
        fr, tr = _sha256d(b"from"), _sha256d(b"to")
        mac, hm, ac = _sha256d(b"mac"), _sha256d(b"headmac"), _sha256d(b"authcommit")
        sig = _sha256d(b"sigA") + _sha256d(b"sigB")  # 64B
        ward_store.batch_put(wid, 4, 5, fr, tr, mac, hm, ac, sig, [10, 20, 30])

        e = ward_store.batch_get(wid)
        self.assertEqual((e["from_counter"], e["to_counter"]), (4, 5))
        self.assertEqual((e["from_root"], e["to_root"]), (fr, tr))
        self.assertEqual((e["mac"], e["head_mac"], e["auth_commit"]), (mac, hm, ac))
        self.assertEqual(e["sig"], sig)
        self.assertEqual(e["pending_ids"], [10, 20, 30])

    @mock_storage
    def test_batch_envelope_empty_sig_and_wallet_isolation(self):
        import storage.ward_store as ward_store

        w1, w2 = self._id(1), self._id(2)
        fr, tr = _sha256d(b"from"), _sha256d(b"to")
        z = b"\x00" * 32
        ward_store.batch_put(w1, 4, 5, fr, tr, z, z, z, _sha256d(b"s") * 2, [1])
        # WARD_KSIG off => empty signature; single pending_id.
        ward_store.batch_put(w2, 0, 1, fr, tr, z, z, z, b"", [7])
        self.assertEqual(ward_store.batch_get(w2)["sig"], b"")
        # w1 is untouched by the w2 write (one envelope per wallet).
        self.assertEqual(ward_store.batch_get(w1)["pending_ids"], [1])
        self.assertIsNone(ward_store.batch_get(self._id(3)))

    @mock_storage
    def test_batch_envelope_replace_and_clear(self):
        import storage.ward_store as ward_store

        wid = self._id(1)
        fr, tr = _sha256d(b"from"), _sha256d(b"to")
        z = b"\x00" * 32
        ward_store.batch_put(wid, 4, 5, fr, tr, z, z, z, b"", [10])
        # A new perform_batch replaces the wallet's in-flight envelope.
        ward_store.batch_put(wid, 5, 6, tr, fr, z, z, z, b"", [99])
        self.assertEqual(ward_store.batch_get(wid)["pending_ids"], [99])
        self.assertTrue(ward_store.batch_clear(wid))
        self.assertIsNone(ward_store.batch_get(wid))
        self.assertFalse(ward_store.batch_clear(wid))  # idempotent

    @mock_storage
    def test_batch_envelope_rejects_bad_field_length(self):
        import storage.ward_store as ward_store

        z = b"\x00" * 32
        with self.assertRaises(ValueError):
            ward_store.batch_put(
                self._id(1), 0, 1, b"\x00" * 31, z, z, z, z, b"", [1]
            )

    @mock_storage
    def test_batch_envelope_kind_commit_vs_revert(self):
        """A commit envelope reports BATCH_COMMIT (default) and a rollback envelope
        BATCH_REVERT (empty pending set, AuthRevert in the auth_commit slot)."""
        import storage.ward_store as ward_store

        wid = self._id(1)
        fr, tr = _sha256d(b"from"), _sha256d(b"to")
        z = b"\x00" * 32
        ward_store.batch_put(wid, 4, 5, fr, tr, z, z, _sha256d(b"ac"), b"", [10])
        self.assertEqual(ward_store.batch_get(wid)["kind"], ward_store.BATCH_COMMIT)
        # A one-step rollback replaces it: from stuck (5) forward to 6, root back to fr.
        ward_store.batch_put(
            wid, 5, 6, tr, fr, z, z, _sha256d(b"ar"), b"", [], ward_store.BATCH_REVERT
        )
        e = ward_store.batch_get(wid)
        self.assertEqual(e["kind"], ward_store.BATCH_REVERT)
        self.assertEqual(e["pending_ids"], [])
        self.assertEqual((e["from_counter"], e["to_counter"]), (5, 6))  # forward +1
        self.assertEqual((e["from_root"], e["to_root"]), (tr, fr))  # root demoted

    @mock_storage
    def test_put_enforces_per_wallet_cap(self):
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        for _ in range(ward_store.MAX_PENDING):
            pid = ward_store.queue_alloc_id()
            ward_store.queue_put(wallet_id, pid, 1, b"x", b"o", b"n", b"bitcoin")
        with self.assertRaises(ValueError):
            pid = ward_store.queue_alloc_id()
            ward_store.queue_put(wallet_id, pid, 1, b"y", b"o", b"n", b"bitcoin")

    @mock_storage
    def test_set_computed_and_drop(self):
        """perform fills (root, mac) and flips PENDING -> COMMITTED; intent fields
        are preserved."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        root = _sha256d(b"root-T")
        mac = _sha256d(b"mac-T")
        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(wallet_id, pid, 1, b"x", b"o", b"n", b"bitcoin")
        ward_store.queue_set_computed(wallet_id, pid, 1, root, mac)

        counter, state, address, ov, nv, got_root, got_mac, _aid, _kt, _did = (
            ward_store.queue_get(wallet_id, pid)
        )
        self.assertEqual(state, ward_store.QUEUE_COMMITTED)
        self.assertEqual(got_root, root)
        self.assertEqual(got_mac, mac)
        self.assertEqual((address, ov, nv), (b"x", b"o", b"n"))

        self.assertTrue(ward_store.queue_drop(wallet_id, pid))
        self.assertIsNone(ward_store.queue_get(wallet_id, pid))

    @mock_storage
    def test_set_computed_rejects_foreign_wallet(self):
        import storage.ward_store as ward_store

        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(self._id(1), pid, 1, b"x", b"o", b"n")
        with self.assertRaises(ValueError):
            ward_store.queue_set_computed(
                self._id(2), pid, 1, _sha256d(b"r"), _sha256d(b"m")
            )

    @mock_storage
    def test_perform_to_empty_tree(self):
        """A DELETE-to-empty candidate stores EMPTY_ROOT and reads back root/mac
        None after perform."""
        import storage.ward_store as ward_store

        wallet_id = self._id(1)
        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(wallet_id, pid, 9, b"bob", b"old_b", b"", b"bitcoin")
        ward_store.queue_set_computed(wallet_id, pid, 9, None, None)
        counter, state, address, ov, nv, root, mac, _aid, _kt, _did = (
            ward_store.queue_get(wallet_id, pid)
        )
        self.assertEqual(counter, 9)
        self.assertEqual(state, ward_store.QUEUE_COMMITTED)
        self.assertIsNone(root)
        self.assertIsNone(mac)
        self.assertEqual(address, b"bob")

    @mock_storage
    def test_service_queue_discard_drops_candidate(self):
        """service.queue_discard() abandons the queued candidate (the internal
        primitive behind WARDDiscardPending)."""
        import storage.ward_store as ward_store
        from apps.ward import service

        wallet_id = self._id(1)
        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(wallet_id, pid, 3, b"alice", b"o", b"n", b"bitcoin")
        self.assertIsNotNone(ward_store.queue_get(wallet_id, pid))

        service.queue_discard(wallet_id, pid)
        self.assertIsNone(ward_store.queue_get(wallet_id, pid))

    @mock_storage
    def test_discard_works_regardless_of_state(self):
        """A discard must clear a COMMITTED candidate too (the stuck-finalize case
        that motivates WARDDiscardPending), not just a PENDING one."""
        import storage.ward_store as ward_store
        from apps.ward import service

        wallet_id = self._id(1)
        pid = ward_store.queue_alloc_id()
        ward_store.queue_put(wallet_id, pid, 1, b"x", b"o", b"n", b"bitcoin")
        ward_store.queue_set_computed(wallet_id, pid, 1, _sha256d(b"r"), _sha256d(b"m"))
        _c, state, _a, _ov, _nv, _r, _m, _aid, _kt, _did = ward_store.queue_get(
            wallet_id, pid
        )
        self.assertEqual(state, ward_store.QUEUE_COMMITTED)

        service.queue_discard(wallet_id, pid)
        self.assertIsNone(ward_store.queue_get(wallet_id, pid))


class TestWardCoreCapability(unittest.TestCase):
    """The Core (apps.common.ward) appId capability boundary that gates on-device
    Trezor App -> WARD calls. The verify path itself is covered by the trezorlib
    crypto tests / the device test; here we cover only the capability check, which
    runs before any seed/root access."""

    def test_capability_map(self):
        from apps.common import ward as ward_core

        self.assertIn("lookup", ward_core._CAPABILITIES["bitcoin"])
        self.assertIn("lookup", ward_core._CAPABILITIES["ethereum"])
        # An app with no grant is absent from the map entirely.
        self.assertTrue("wallet" not in ward_core._CAPABILITIES)

    def test_unauthorized_app_rejected(self):
        from apps.common import ward as ward_core
        from trezor.wire import DataError

        with self.assertRaises(DataError):
            await_result(ward_core.lookup_label("wallet", b"addr", b"n", b"t", b"c", []))


class TestWardSyncStorage(unittest.TestCase):
    """The WARD sync-round context (_SYNC): nonce + attested checkpoint."""

    def _id(self, n):
        return _sha256d(b"ward-wallet-%d" % n)[:20]

    @mock_storage
    def test_begin_then_get(self):
        import storage.ward_head as ward_store

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
        import storage.ward_head as ward_store

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
        import storage.ward_head as ward_store

        wallet_id = self._id(1)
        ward_store.sync_begin(wallet_id, _sha256d(b"nonce"))
        ward_store.sync_set_attested(wallet_id, 3, None)  # empty tree
        _n, _state, counter, mac = ward_store.sync_get(wallet_id)
        self.assertEqual(counter, 3)
        self.assertIsNone(mac)

    @mock_storage
    def test_wallet_scoped_and_clear(self):
        import storage.ward_head as ward_store

        ward_store.sync_begin(self._id(1), _sha256d(b"nonce"))
        self.assertIsNone(ward_store.sync_get(self._id(2)))
        ward_store.sync_clear()
        self.assertIsNone(ward_store.sync_get(self._id(1)))

    @mock_storage
    def test_set_attested_requires_round(self):
        import storage.ward_head as ward_store

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


class TestWardProofSoundness(unittest.TestCase):
    """Proof-level checks for the hardened WARD trie verifier."""

    def _proof_elem(self, split_bit, skiplen, sibling):
        return split_bit.to_bytes(2, "big") + skiplen.to_bytes(2, "big") + sibling

    def test_nonmembership_rejects_relabelled_witness_path(self):
        from apps.ward import service

        target = bytes([0x40]) + b"\x00" * 31   # 0100....
        witness = bytes([0x60]) + b"\x00" * 31  # 0110....
        other = bytes([0x80]) + b"\x00" * 31    # 1000....

        target_commit = b"T" * 32
        witness_commit = b"W" * 32
        other_commit = b"B" * 32

        target_leaf = service.leaf_hash_of(target, target_commit)
        witness_leaf = service.leaf_hash_of(witness, witness_commit)
        other_leaf = service.leaf_hash_of(other, other_commit)

        left = service.internal_hash(2, 1, target_leaf, witness_leaf)
        root = service.internal_hash(0, 0, left, other_leaf)

        honest_proof = [
            self._proof_elem(2, 1, target_leaf),
            self._proof_elem(0, 0, other_leaf),
        ]
        self.assertFalse(
            service.verify_nonmembership(target, witness, witness_commit, honest_proof, root)
        )

        forged_proof = [
            self._proof_elem(1, 0, target_leaf),
            self._proof_elem(0, 0, other_leaf),
        ]
        self.assertFalse(
            service.verify_nonmembership(target, witness, witness_commit, forged_proof, root)
        )

    def test_insert_rejects_forged_nonmembership_witness(self):
        from apps.ward import service

        target = bytes([0x40]) + b"\x00" * 31   # actually present in the tree
        witness = bytes([0x60]) + b"\x00" * 31
        other = bytes([0x80]) + b"\x00" * 31

        target_commit = b"T" * 32
        witness_commit = b"W" * 32
        other_commit = b"B" * 32

        target_leaf = service.leaf_hash_of(target, target_commit)
        witness_leaf = service.leaf_hash_of(witness, witness_commit)
        other_leaf = service.leaf_hash_of(other, other_commit)

        left = service.internal_hash(2, 1, target_leaf, witness_leaf)
        root = service.internal_hash(0, 0, left, other_leaf)

        forged_proof = [
            self._proof_elem(1, 0, target_leaf),
            self._proof_elem(0, 0, other_leaf),
        ]

        new_leaf = (b"N" * 12, b"G" * 16, b"ciphertext")
        with self.assertRaises(ValueError):
            service.compute_new_root(
                target,
                None,
                new_leaf,
                forged_proof,
                root,
                witness_entry_key=witness,
                witness_commit=witness_commit,
            )


if __name__ == "__main__":
    unittest.main()
