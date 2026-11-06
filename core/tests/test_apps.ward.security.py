# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import cache, ward_head, ward_store
from trezor import config, wire
from trezor.crypto.curve import ed25519

from apps.ward import service
from apps.ward.caller import (
    ADDRESS_LABELS,
    DISPLAY_ADDRESS,
    WardCaller,
    extapp_caller,
    host_caller,
)
from apps.ward.keys import entry_key

DEBUG_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."


class TestWardSecurity(TestCaseWithSeed):
    def setUp(self):
        config.init()
        config.wipe()
        cache.clear_all()

    def attest(self, counter, mac, timestamp=1700000000, head_nonce=b"h" * 32):
        nonce, _, _, ward_id = await_result(service.sync())
        message = (
            b"WARD ATTEST v2\x02"
            + nonce
            + ward_id
            + counter.to_bytes(4, "big")
            + mac
            + timestamp.to_bytes(8, "big")
            + head_nonce
        )
        signature = ed25519.sign(DEBUG_SEED, message)
        return await_result(
            service.ingest(counter, mac, signature, timestamp, head_nonce)
        )

    def test_positive_empty_head_requires_wallet_mac(self):
        with self.assertRaises(wire.DataError):
            self.attest(1, bytes(32))
        wallet = await_result(service.get_wallet_id())
        self.assertEqual(ward_store.get_counter(wallet), 0)

    def test_authenticated_empty_head_can_be_adopted(self):
        wallet = await_result(service.get_wallet_id())
        key = await_result(service.derive_mac_key(b"root_mac"))
        mac = service.compute_mac(
            key, wallet, (1).to_bytes(4, "big"), service.EMPTY_ROOT_HASH
        )
        self.attest(1, mac)
        result = await_result(service.reconcile(None))
        self.assertEqual(result[0], 1)
        self.assertIsNone(result[1])

    def test_trusted_anchor_survives_cache_reset(self):
        wallet = await_result(service.get_wallet_id())
        root = b"r" * 32
        ward_head.root_set(wallet, root)
        ward_store.commit_counter(wallet, 4)
        cache.clear_all()
        self.assertEqual(ward_store.get_counter(wallet), 4)
        self.assertEqual(ward_head.root_get(wallet), (True, root))

    def test_capacity_never_evicts_a_rollback_floor(self):
        for index in range(ward_store.MAX_WALLETS):
            wallet = bytes([index]) * ward_store.WALLET_ID_LENGTH
            ward_head.root_set(wallet, bytes([index + 1]) * 32)
            ward_store.commit_counter(wallet, 7)
        with self.assertRaises(ValueError):
            ward_store.commit_counter(b"x" * ward_store.WALLET_ID_LENGTH, 1)
        for index in range(ward_store.MAX_WALLETS):
            self.assertEqual(
                ward_store.get_counter(bytes([index]) * ward_store.WALLET_ID_LENGTH), 7
            )

    def test_same_counter_cannot_switch_roots(self):
        wallet = await_result(service.get_wallet_id())
        ward_head.root_set(wallet, b"a" * 32)
        ward_store.commit_counter(wallet, 1)
        key = await_result(service.derive_mac_key(b"root_mac"))
        mac = service.compute_mac(key, wallet, (1).to_bytes(4, "big"), b"b" * 32)
        self.attest(1, mac)
        with self.assertRaises(wire.DataError):
            await_result(service.reconcile(b"b" * 32))
        self.assertEqual(ward_head.root_get(wallet), (True, b"a" * 32))

    def test_non_membership_requires_both_witness_hashes(self):
        wallet = await_result(service.get_wallet_id())
        ward_head.root_set(wallet, b"r" * 32)
        for witness_key, witness_commit in ((None, b"c" * 32), (b"k" * 32, None)):
            with self.assertRaises(wire.DataError):
                await_result(
                    service.lookup(
                        ADDRESS_LABELS,
                        b"address",
                        None,
                        None,
                        [],
                        witness_entry_key=witness_key,
                        witness_commit=witness_commit,
                    )
                )
        self.assertEqual(ward_head.root_get(wallet), (True, b"r" * 32))
        self.assertEqual(ward_store.get_counter(wallet), 0)

    def test_partial_pushed_proof_is_not_treated_as_a_pull(self):
        from trezor.messages import WARDLookup

        from apps.ward.lookup import lookup

        wallet = await_result(service.get_wallet_id())
        ward_head.root_set(wallet, b"r" * 32)
        message = WARDLookup(
            address=b"address", app_id="bitcoin", proof=[], witness_commit=b"c" * 32
        )
        with self.assertRaises(wire.DataError):
            await_result(lookup(message))

    def test_malformed_membership_proof_returns_a_protocol_error(self):
        from apps.ward.leaf import encode_content, encode_identity, leaf_hash

        wallet = await_result(service.get_wallet_id())
        path_key = await_result(service.derive_k_path())
        entry = entry_key(path_key, "bitcoin", b"address")
        identity = encode_identity(
            await_result(service.derive_k_ident("address")),
            entry,
            "address",
            b"address",
            "bitcoin",
            0,
        )
        content = encode_content(
            await_result(service.derive_k_data("address")),
            entry,
            "address",
            1,
            b"value",
        )
        root = leaf_hash(entry, "address", identity, content)
        ward_head.root_set(wallet, root)
        ward_store.commit_counter(wallet, 1)
        for proof in ([b"short"], [(256).to_bytes(2, "big") + b"s" * 32]):
            with self.assertRaises(wire.DataError):
                await_result(
                    service.lookup(ADDRESS_LABELS, b"address", identity, content, proof)
                )
            self.assertEqual(ward_head.root_get(wallet), (True, root))
            self.assertEqual(ward_store.get_counter(wallet), 1)
        valid, counter, member, _, _ = await_result(
            service.lookup(ADDRESS_LABELS, b"address", identity, content, [])
        )
        self.assertTrue(valid and member)
        self.assertEqual(counter, 1)

    def test_revert_link_is_authenticated_in_chain(self):
        key, wallet = b"k" * 32, b"w" * 32
        authorization = service.auth_revert(key, wallet, 2, b"b" * 32, 3, b"a" * 32)
        link = (2, b"b" * 32, 3, b"a" * 32, authorization)
        self.assertEqual(
            service.verify_chain_step(key, wallet, 2, b"b" * 32, link), (3, b"a" * 32)
        )
        with self.assertRaises(ValueError):
            service.verify_chain_step(b"x" * 32, wallet, 2, b"b" * 32, link)

    def test_identity_encoding_is_unambiguous(self):
        key = b"k" * 32
        self.assertNotEqual(
            entry_key(key, b"a", b"id", "b\x00c"), entry_key(key, b"a\x00b", b"id", "c")
        )
        for device in (-1, 256):
            with self.assertRaises(ValueError):
                entry_key(key, b"app", b"id", device_id=device)

    def test_empty_set_and_delete_are_distinct_persistent_intents(self):
        wallet = await_result(service.get_wallet_id())
        ward_store.queue_put(wallet, 1, 0, b"entry", b"", b"app", delete=False)
        ward_store.queue_put(wallet, 2, 0, b"entry", b"", b"app", delete=True)
        self.assertFalse(ward_store.queue_is_delete(wallet, 1))
        self.assertTrue(ward_store.queue_is_delete(wallet, 2))
        cache.clear_all()
        self.assertFalse(ward_store.queue_is_delete(wallet, 1))
        self.assertTrue(ward_store.queue_is_delete(wallet, 2))

    def test_empty_value_has_authenticated_content(self):
        from apps.ward.leaf import decode_content, encode_content

        key, entry = b"k" * 32, b"e" * 32
        content = encode_content(key, entry, "address", 7, b"")
        self.assertTrue(len(content[3]) > 0)
        self.assertEqual(decode_content(key, entry, "address", content), (7, b""))

    def test_timestamp_floor_survives_restart_and_cannot_drift_backwards(self):
        wallet = await_result(service.get_wallet_id())
        self.attest(0, bytes(32), timestamp=1700001000)
        await_result(service.reconcile(None))
        cache.clear_all()
        self.assertEqual(ward_head.root_metadata(wallet), (1700001000, b"h" * 32))
        with self.assertRaises(wire.DataError):
            self.attest(0, bytes(32), timestamp=1700000699)
        self.attest(0, bytes(32), timestamp=1700000701)
        await_result(service.reconcile(None))
        self.assertEqual(ward_head.root_metadata(wallet)[0], 1700001000)

    def test_the_service_not_the_caller_fills_the_scope(self):
        # the host may only omit the scope fields or repeat the service's own values
        self.assertIs(host_caller(None, None, None), ADDRESS_LABELS)
        self.assertIs(host_caller("bitcoin", "address", 0), ADDRESS_LABELS)
        for args in (("ethereum", None, None), (None, "label", None), (None, None, 1)):
            with self.assertRaises(wire.DataError):
                host_caller(*args)
        # a device slot other than 0x00 is for core apps only, and must fit one byte
        self.assertEqual(ADDRESS_LABELS.device_slot(0), 0)
        self.assertEqual(DISPLAY_ADDRESS.device_slot(7), 7)
        for caller, slot in ((ADDRESS_LABELS, 1), (extapp_caller(b"x"), 1)):
            with self.assertRaises(wire.DataError):
                caller.device_slot(slot)
        with self.assertRaises(wire.DataError):
            DISPLAY_ADDRESS.device_slot(256)
        # third-party apps live in their own namespace, which no core app can claim
        self.assertEqual(extapp_caller(b"bitcoin").app_id, b"ext:bitcoin")
        with self.assertRaises(ValueError):
            WardCaller(b"ext:bitcoin", core=True)

    def test_queue_refuses_a_slot_the_caller_may_not_use(self):
        with self.assertRaises(wire.DataError):
            await_result(service.queue(ADDRESS_LABELS, b"addr", b"v", device_id=1))
        with self.assertRaises(wire.DataError):
            await_result(service.queue(extapp_caller(b"a"), b"addr", b"v", device_id=3))

    def test_display_is_unambiguous(self):
        row = service.display_property
        self.assertEqual(row("Key", b"bc1qalice"), ("Key", "bc1qalice", True))
        # text is never mangled, even when it looks like hex
        self.assertEqual(row("Key", b"0xdave"), ("Key", "0xdave", True))
        self.assertEqual(row("Key", b"fffe"), ("Key", "fffe", True))
        # non-text is hex, and the LABEL says so: it cannot pass for the text "fffe"
        self.assertEqual(row("Key", b"\xff\xfe"), ("Key (hex)", "fffe", True))
        self.assertEqual(row("Value", b""), ("Value (empty)", "-", False))
        # never raw: edge spaces, control, newline, non-ASCII, bidi override
        for value in (
            b" alice",
            b"alice ",
            b"ali\x00ce",
            b"alice\nValue: x",
            "\u0160usil".encode(),
            "\u202ealice".encode(),
        ):
            self.assertIsNone(service.display_text(value))
            self.assertEqual(row("Key", value), ("Key (hex)", value.hex(), True))

    def test_provisioned_manager_public_key_verifies_its_own_signatures(self):
        key, other = b"p" * 32, b"q" * 32
        saved = service._WM_PUBKEY
        try:
            service._WM_PUBKEY = ed25519.publickey(key)
            self.assertTrue(
                service._verify(b"production key", ed25519.sign(key, b"production key"))
            )
            self.assertFalse(
                service._verify(
                    b"production key", ed25519.sign(other, b"production key")
                )
            )
        finally:
            service._WM_PUBKEY = saved


if __name__ == "__main__":
    unittest.main()
