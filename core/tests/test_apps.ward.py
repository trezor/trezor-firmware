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


if __name__ == "__main__":
    unittest.main()
