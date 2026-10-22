# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import SecretOwner, _secret_owner_activate, revoke_secrets, secbytes

import storage.device
from storage.cache_common import APP_COMMON_SEED
from trezor import config
from trezor.crypto import bip32, bip39
from trezor.wire import context

from apps.common import mnemonic, seed


class TestProtectedCommonSeed(unittest.TestCase):
    MNEMONIC = "all all all all all all all all all all all all"

    def setUp(self):
        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        revoke_secrets()
        config.set(1, 0x0E, b"\x00")
        storage.device.store_mnemonic_secret(self.MNEMONIC.encode())
        if utils.USE_THP:
            from storage.cache_thp import SessionThpCache

            cache = SessionThpCache()
        else:
            from storage.cache_codec import SessionCache

            cache = SessionCache()

        class Context:
            pass

        self.ctx = Context()
        self.ctx.cache = cache
        self.previous_context = context.CURRENT_CONTEXT
        context.CURRENT_CONTEXT = self.ctx
        self.owner = SecretOwner(cache.get_secret_owner())
        _secret_owner_activate(self.owner)
        self.prompts = 0

        async def passphrase(*args):
            self.prompts += 1
            return "TREZOR"

        def no_python_seed(*args, **kwargs):
            raise AssertionError("Mnemonic/seed read through Python")

        self.original_mnemonic = mnemonic.get_seed
        mnemonic.get_seed = no_python_seed
        if utils.USE_THP:
            self.original_passphrase = seed.get_passphrase
            seed.get_passphrase = passphrase
        else:
            self.original_passphrase = seed.get_passphrase_legacy
            seed.get_passphrase_legacy = passphrase

    def tearDown(self):
        mnemonic.get_seed = self.original_mnemonic
        if utils.USE_THP:
            seed.get_passphrase = self.original_passphrase
        else:
            seed.get_passphrase_legacy = self.original_passphrase
        self.ctx.cache.clear()
        context.CURRENT_CONTEXT = self.previous_context
        revoke_secrets()

    def derive(self, cardano=False):
        if utils.USE_THP:
            from trezor.messages import ThpCreateNewSession

            msg = ThpCreateNewSession(derive_cardano=cardano)
            await_result(seed.derive_and_store_roots(self.ctx, msg))
        else:
            if not utils.BITCOIN_ONLY:
                from storage.cache_common import APP_COMMON_DERIVE_CARDANO

                self.ctx.cache.set_bool(APP_COMMON_DERIVE_CARDANO, cardano)
            await_result(seed.derive_and_store_roots_legacy())
        return await_result(seed.get_seed())

    def test_protected_seed_cache_and_request_reuse(self):
        value = self.derive()
        self.assertIsInstance(value, secbytes)
        self.assertIs(value, self.ctx.cache.vault_seed)
        self.assertEqual(self.prompts, 1)
        self.assertEqual(self.ctx.cache.fields[APP_COMMON_SEED], 0)
        self.assertIsNone(self.ctx.cache.get(APP_COMMON_SEED))
        self.assertIsNone(config.get(1, 2))
        for curve in ("secp256k1", "nist256p1", "ed25519"):
            actual = bip32.from_seed(value, curve)
            expected = bip32.from_seed(bip39.seed(self.MNEMONIC, "TREZOR"), curve)
            actual.derive(0x80000001)
            expected.derive(0x80000001)
            self.assertEqual(actual.public_key(), expected.public_key())
        self.owner.destroy()
        self.owner = SecretOwner(self.ctx.cache.get_secret_owner())
        _secret_owner_activate(self.owner)
        self.assertIs(await_result(seed.get_seed()), value)
        self.assertEqual(self.prompts, 1)
        self.assertTrue(bip32.from_seed(value, "ed25519").public_key())
        with self.assertRaises(TypeError):
            bytes(value)
        self.ctx.cache.clear()
        self.assertTrue(value.empty())
        self.assertFalse(self.owner.valid())

    def test_failed_derivation_leaves_empty_holder(self):
        config.set(1, 0x0E, b"\x01")
        with self.assertRaises(ValueError):
            self.derive()
        self.assertTrue(self.ctx.cache.vault_seed.empty())
        self.assertIsNone(self.ctx.cache.get(APP_COMMON_SEED))

    @unittest.skipUnless(not utils.BITCOIN_ONLY, "full-coin setup")
    def test_cardano_fails_explicitly_without_python_seed(self):
        from trezor.wire.errors import ProcessError

        with self.assertRaises(ProcessError):
            self.derive(cardano=True)
        self.assertEqual(self.prompts, 0)
        self.assertTrue(self.ctx.cache.vault_seed.empty())


if __name__ == "__main__":
    unittest.main()
