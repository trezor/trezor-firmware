# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import cache, cache_common
from trezor import config, wire
from trezor.crypto import bip39
from trezor.wire import context

from apps.common.keychain import with_slip44_keychain
from apps.common.paths import PATTERN_SEP5

if utils.USE_WARD:
    from apps.ward import WardApp, open_ward, with_ward
    from apps.ward.keys import derive_wallet_id
    from apps.ward.store import WardError, WardStore

if not utils.USE_THP:
    from storage import cache_codec

MNEMONIC = " ".join(["all"] * 12)
SEED = bip39.seed(MNEMONIC, "")
SEED_PASSPHRASE = bip39.seed(MNEMONIC, "TREZOR")
OTHER_APP = 2


@unittest.skipUnless(utils.USE_WARD, "WARD is not enabled")
class TestWard(TestCaseWithContext):
    def setUp(self):
        config.init()
        config.wipe()
        if not utils.USE_THP:
            cache_codec.start_session()
        self.set_seed(SEED)

    def tearDown(self):
        cache.clear_all()

    def set_seed(self, seed):
        """Switch the current passphrase wallet."""
        context.cache_set(cache_common.APP_COMMON_SEED, seed)

    def open(self, app=None):
        return await_result(open_ward(WardApp.BITCOIN if app is None else app))

    def entries(self, ward):
        async def collect():
            result = []
            async for entry in ward.entries():
                result.append(entry)
            return result

        return await_result(collect())

    def test_derive_wallet_id(self):
        # SLIP21(seed, [b"TREZOR", b"WARD", b"Wallet ID"]).key()
        self.assertEqual(
            await_result(derive_wallet_id()),
            bytes.fromhex(
                "513e17b7e2bd487aa07cedbe6bda05c609235f9d69e9d47201bdc1c603d96d11"
            ),
        )
        self.set_seed(SEED_PASSPHRASE)
        self.assertEqual(
            await_result(derive_wallet_id()),
            bytes.fromhex(
                "b6be487329524e4691ebd517236746dddbaa1af1e947dd12f1aa02edfae173ba"
            ),
        )

    def test_set(self):
        ward = self.open()
        self.assertIsNone(await_result(ward.get(b"key")))
        await_result(ward.set(b"key", b"value"))
        self.assertEqual(await_result(ward.get(b"key")), b"value")
        await_result(ward.set(b"key", b"other"))
        self.assertEqual(await_result(ward.get(b"key")), b"other")

    def test_delete(self):
        ward = self.open()
        self.assertFalse(await_result(ward.delete(b"key")))
        await_result(ward.set(b"key", b"value"))
        self.assertTrue(await_result(ward.delete(b"key")))
        self.assertIsNone(await_result(ward.get(b"key")))
        self.assertFalse(await_result(ward.delete(b"key")))

    def test_entries(self):
        ward = self.open()
        other = self.open(OTHER_APP)
        self.assertEqual(self.entries(ward), [])

        await_result(ward.set(b"a", b"1"))
        await_result(other.set(b"x", b""))
        await_result(ward.set(b"b", b"2"))
        self.assertEqual(self.entries(ward), [(b"a", b"1"), (b"b", b"2")])
        self.assertEqual(self.entries(other), [(b"x", b"")])

    def test_entries_exhausted(self):
        ward = self.open()
        entries = ward.entries()
        with self.assertRaises(StopAsyncIteration):
            await_result(entries.__anext__())
        await_result(ward.set(b"a", b"1"))
        with self.assertRaises(StopAsyncIteration):
            await_result(entries.__anext__())

    @unittest.skipUnless(__debug__, "debug builds only")
    def test_entries_modified(self):
        ward = self.open()
        await_result(ward.set(b"a", b"1"))
        await_result(ward.set(b"b", b"2"))

        async def read():
            async for key, _ in ward.entries():
                await ward.get(key)

        async def modify(modification):
            async for _ in ward.entries():
                await modification

        # reading during iteration is allowed
        await_result(read())

        # modifying any store is not
        for store in (ward, ward.subscope(b"sub"), self.open(OTHER_APP)):
            with self.assertRaises(RuntimeError):
                await_result(modify(store.set(b"c", b"3")))
        with self.assertRaises(RuntimeError):
            await_result(modify(ward.delete(b"a")))

    def test_isolation(self):
        wards = [self.open(), self.open(OTHER_APP)]
        self.set_seed(SEED_PASSPHRASE)
        wards.append(self.open())
        for i, ward in enumerate(wards):
            await_result(ward.set(b"key", bytes([i])))
        for i, ward in enumerate(wards):
            self.assertEqual(await_result(ward.get(b"key")), bytes([i]))
            self.assertEqual(self.entries(ward), [(b"key", bytes([i]))])

    def test_subscope(self):
        ward = self.open()
        wards = [
            ward,
            ward.subscope(b"Testnet"),
            ward.subscope(b"Testnet").subscope(b"Regtest"),
            # subscope names are length-prefixed, so these do not collide
            ward.subscope(b"ab").subscope(b"c"),
            ward.subscope(b"a").subscope(b"bc"),
            ward.subscope(b""),
        ]
        for i, w in enumerate(wards):
            await_result(w.set(b"key", bytes([i])))
        for i, w in enumerate(wards):
            self.assertEqual(await_result(w.get(b"key")), bytes([i]))
            self.assertEqual(self.entries(w), [(b"key", bytes([i]))])

        # the same subscope of another app is separate as well
        other = self.open(OTHER_APP).subscope(b"Testnet")
        self.assertIsNone(await_result(other.get(b"key")))

        with self.assertRaises(ValueError):
            ward.subscope(bytes(256))

    def test_errors(self):
        ward = self.open()
        with self.assertRaises(WardError):
            await_result(ward.set(b"key", bytes(3000)))

        await_result(ward.set(b"key", b"value"))
        config.lock()
        with self.assertRaises(WardError):
            await_result(ward.get(b"key"))

    def test_with_ward(self):
        @with_slip44_keychain(PATTERN_SEP5, slip44_id=42)
        @with_ward(WardApp.BITCOIN)
        async def handler(msg, keychain, *, ward):
            return msg, ward

        msg, ward = await_result(handler("msg"))
        self.assertEqual(msg, "msg")
        self.assertTrue(isinstance(ward, WardStore))
        self.assertEqual(ward._wallet_id, self.open()._wallet_id)

    def test_with_ward_error(self):
        @with_ward(WardApp.BITCOIN)
        async def handler(msg, *, ward):
            await ward.set(b"key", bytes(3000))

        with self.assertRaises(wire.ProcessError):
            await_result(handler("msg"))


    def _sealed_leaf(self, identifier, value, app_id="bitcoin"):
        """A leaf for (app_id, identifier) -> value sealed under this wallet's keys, and
        its entry_key."""
        from apps.ward import keys, leaf

        k_path = await_result(keys.derive_k_path())
        ek = keys.entry_key(k_path, app_id, identifier)
        id_part = leaf.encode_identity(
            await_result(keys.derive_k_ident("address")),
            ek,
            "address",
            identifier,
            app_id,
        )
        val_part = leaf.encode_content(
            await_result(keys.derive_k_data("address")), ek, "address", 1, value
        )
        return ek, id_part, val_part

    def test_cache_entry_stores_a_verified_leaf_in_its_apps_store(self):
        from storage import ward_head

        from apps.ward import cache, keys, leaf, service

        ek, id_part, val_part = self._sealed_leaf(b"bc1qcached", b"cached label")
        wallet_id = await_result(keys.get_wallet_id())
        # a one-leaf trie: the root is the leaf itself, the proof is empty
        ward_head.root_set(wallet_id, leaf.leaf_hash(ek, "address", id_part, val_part))

        replaced, _counter = await_result(
            service.cache_entry(ek, "address", id_part, val_part, [], False)
        )
        self.assertFalse(replaced)
        # filed under the service's fixed subscope, with its C_leaf and no sticky bit
        store = self.open().subscope(b"WARD")
        raw = await_result(store.get(cache.record_key("address", 0, b"bc1qcached")))
        self.assertEqual(cache.parse_value(raw), (0, 1, b"cached label"))

        replaced, _counter = await_result(
            service.cache_entry(ek, "address", id_part, val_part, [], False)
        )
        self.assertTrue(replaced)

    def test_cache_entry_stores_nothing_the_root_does_not_commit_to(self):
        from storage import ward_head

        from apps.ward import keys, service

        ek, id_part, val_part = self._sealed_leaf(b"bc1qcached", b"cached label")
        wallet_id = await_result(keys.get_wallet_id())
        ward_head.root_set(wallet_id, b"\x55" * 32)

        with self.assertRaises(wire.DataError):
            await_result(
                service.cache_entry(ek, "address", id_part, val_part, [], False)
            )
        self.assertEqual(self.entries(self.open().subscope(b"WARD")), [])


    def test_cache_backup_opens_only_for_the_same_wallet(self):
        from apps.ward import cache

        key = cache.record_key("address", 0, b"k")
        value = cache.record_value(1, 3, b"v")
        blob = await_result(cache.seal(b"bitcoin", key, value))
        self.assertEqual(await_result(cache.open_blob(blob)), (b"bitcoin", key, value))
        self.set_seed(SEED_PASSPHRASE)  # another (hidden) wallet of the same seed
        with self.assertRaises(wire.DataError):
            await_result(cache.open_blob(blob))


if __name__ == "__main__":
    unittest.main()
