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

    def test_derive_wallet_id(self):
        # SLIP21(seed, [b"ward", b"wallet_id"]).key()
        self.assertEqual(
            await_result(derive_wallet_id()),
            bytes.fromhex(
                "9cb4e6cc69b9ca91dcebde45f8f9c3351894bd0d7ca15c6c53253f9bf50f9137"
            ),
        )
        self.set_seed(SEED_PASSPHRASE)
        self.assertEqual(
            await_result(derive_wallet_id()),
            bytes.fromhex(
                "60b5a691c719704bb187536840246db5697c0d0e6bb2d4d8841a0c0810a49e39"
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
        self.assertEqual(list(ward.entries()), [])

        await_result(ward.set(b"a", b"1"))
        await_result(other.set(b"x", b""))
        await_result(ward.set(b"b", b"2"))
        self.assertEqual(list(ward.entries()), [(b"a", b"1"), (b"b", b"2")])
        self.assertEqual(list(other.entries()), [(b"x", b"")])

    def test_isolation(self):
        wards = [self.open(), self.open(OTHER_APP)]
        self.set_seed(SEED_PASSPHRASE)
        wards.append(self.open())
        for i, ward in enumerate(wards):
            await_result(ward.set(b"key", bytes([i])))
        for i, ward in enumerate(wards):
            self.assertEqual(await_result(ward.get(b"key")), bytes([i]))
            self.assertEqual(list(ward.entries()), [(b"key", bytes([i]))])

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
