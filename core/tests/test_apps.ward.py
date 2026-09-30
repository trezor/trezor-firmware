# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import MockAsync, patch
from storage import cache, cache_common
from trezor import config, wire
from trezor.crypto import bip39
from trezor.wire import context

from apps.common.keychain import with_slip44_keychain
from apps.common.paths import PATTERN_SEP5

if utils.USE_WARD:
    from apps.ward import WardApp, layout, open_ward, with_ward
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
        context.cache_set(cache_common.APP_COMMON_SEED, SEED)

    def tearDown(self):
        cache.clear_all()

    def open(self, app=None, seed=None):
        if seed is not None:
            context.cache_set(cache_common.APP_COMMON_SEED, seed)
        return await_result(open_ward(WardApp.BITCOIN if app is None else app))

    def test_derive_wallet_id(self):
        # SLIP21(seed, [b"ward", b"wallet_id"]).key()
        self.assertEqual(
            await_result(derive_wallet_id()),
            bytes.fromhex(
                "9cb4e6cc69b9ca91dcebde45f8f9c3351894bd0d7ca15c6c53253f9bf50f9137"
            ),
        )
        context.cache_set(cache_common.APP_COMMON_SEED, SEED_PASSPHRASE)
        self.assertEqual(
            await_result(derive_wallet_id()),
            bytes.fromhex(
                "60b5a691c719704bb187536840246db5697c0d0e6bb2d4d8841a0c0810a49e39"
            ),
        )

    def test_open_ward(self):
        ward = self.open()
        self.assertEqual(ward._wallet_id, await_result(derive_wallet_id()))
        self.assertEqual(ward._app, WardApp.BITCOIN)

    def test_set(self):
        ward = self.open()
        confirm = MockAsync()
        with patch(layout, "confirm_replace", confirm):
            self.assertIsNone(await_result(ward.get(b"key")))

            # creating and keeping a value does not need an approval
            await_result(ward.set(b"key", b"value", "Record"))
            await_result(ward.set(b"key", b"value", "Record"))
            self.assertEqual(await_result(ward.get(b"key")), b"value")
            self.assertEqual(confirm.calls, [])

            await_result(ward.set(b"key", b"other", "Record"))
            self.assertEqual(await_result(ward.get(b"key")), b"other")
            self.assertEqual(confirm.calls, [((WardApp.BITCOIN, "Record"), {})])

    def test_set_cancelled(self):
        ward = self.open()
        await_result(ward.set(b"key", b"value", "Record"))
        confirm = MockAsync(raises=wire.ActionCancelled())
        with patch(layout, "confirm_replace", confirm):
            with self.assertRaises(wire.ActionCancelled):
                await_result(ward.set(b"key", b"other", "Record"))
        self.assertEqual(await_result(ward.get(b"key")), b"value")

    def test_delete(self):
        ward = self.open()
        confirm = MockAsync()
        with patch(layout, "confirm_delete", confirm):
            self.assertFalse(await_result(ward.delete(b"key", "Record")))
            self.assertEqual(confirm.calls, [])

            await_result(ward.set(b"key", b"value", "Record"))
            self.assertTrue(await_result(ward.delete(b"key", "Record")))
            self.assertIsNone(await_result(ward.get(b"key")))
            self.assertEqual(confirm.calls, [((WardApp.BITCOIN, "Record"), {})])

    def test_delete_cancelled(self):
        ward = self.open()
        await_result(ward.set(b"key", b"value", "Record"))
        confirm = MockAsync(raises=wire.ActionCancelled())
        with patch(layout, "confirm_delete", confirm):
            with self.assertRaises(wire.ActionCancelled):
                await_result(ward.delete(b"key", "Record"))
        self.assertEqual(await_result(ward.get(b"key")), b"value")

    def test_entries(self):
        ward = self.open()
        other = self.open(OTHER_APP)
        self.assertEqual(list(ward.entries()), [])

        await_result(ward.set(b"a", b"1", "Record"))
        await_result(other.set(b"x", b"", "Record"))
        await_result(ward.set(b"b", b"2", "Record"))
        self.assertEqual(list(ward.entries()), [(b"a", b"1"), (b"b", b"2")])
        self.assertEqual(list(other.entries()), [(b"x", b"")])

    def test_isolation(self):
        wards = [
            self.open(),
            self.open(OTHER_APP),
            self.open(seed=SEED_PASSPHRASE),
        ]
        for i, ward in enumerate(wards):
            await_result(ward.set(b"key", bytes([i]), "Record"))
        for i, ward in enumerate(wards):
            self.assertEqual(await_result(ward.get(b"key")), bytes([i]))
            self.assertEqual(list(ward.entries()), [(b"key", bytes([i]))])

    def test_errors(self):
        ward = self.open()
        with self.assertRaises(WardError):
            await_result(ward.set(b"key", bytes(3000), "Record"))

        await_result(ward.set(b"key", b"value", "Record"))
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

    def test_with_ward_positional_args(self):
        # mimics the bitcoin `with_keychain`
        def with_keychain(func):
            async def wrapper(msg, auth=None):
                if auth is None:
                    return await func(msg, "keychain", "coin")
                return await func(msg, "keychain", "coin", auth)

            return wrapper

        @with_keychain
        @with_ward(WardApp.BITCOIN)
        async def handler(msg, keychain, coin, auth=None, *, ward):
            return msg, keychain, coin, auth, isinstance(ward, WardStore)

        self.assertEqual(
            await_result(handler("msg")), ("msg", "keychain", "coin", None, True)
        )
        self.assertEqual(
            await_result(handler("msg", "auth")),
            ("msg", "keychain", "coin", "auth", True),
        )

    def test_with_ward_error(self):
        @with_ward(WardApp.BITCOIN)
        async def handler(msg, *, ward):
            await ward.set(b"key", bytes(3000), "Record")

        with self.assertRaises(wire.ProcessError):
            await_result(handler("msg"))


if __name__ == "__main__":
    unittest.main()
