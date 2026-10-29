# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import SecretOwner, _secret_owner_activate, secbytes

from storage.cache_common import (
    APP_COMMON_SEED,
    APP_COMMON_SEED_WITHOUT_PASSPHRASE,
    SessionlessCache,
)


class TestCacheFramework(VaultTestCase):
    def test_protected_slot_and_replacement(self):
        cache = context.get_context().cache
        key = APP_COMMON_SEED
        self.assertEqual(cache.fields[key], 64)
        slot = cache.data[key]
        self.assertIsNone(cache.get_secret(key))
        source = secbytes(b"a" * 64, secbytes.SEED)
        cache.take_secret(key, source)
        self.assertTrue(source.empty())
        self.assertIs(cache.get_secret(key), slot)
        cache.take_secret(key, slot)  # self-assignment preserves the value
        self.assertFalse(slot.empty())
        self.assertTrue(cache.is_set(key))
        with self.assertRaises(TypeError):
            cache.get(key)
        with self.assertRaises(TypeError):
            cache.set(key, b"x" * 64)
        cache.take_secret(key, secbytes(b"b" * 64, secbytes.SEED))
        self.assertIs(cache.get_secret(key), slot)
        cache.delete_secret(key)
        self.assertIsNone(cache.get_secret(key))
        self.assertIs(cache.data[key], slot)

    @unittest.skipUnless(not utils.BITCOIN_ONLY, "FIDO seed slots")
    def test_private_context_routing_uses_current_owner(self):
        cache = context.get_context().cache
        key = APP_COMMON_SEED_WITHOUT_PASSPHRASE
        context.cache_take_secret(key, secbytes(b"a" * 64, secbytes.SEED))
        self.assertIs(context.cache_get_secret(key), cache.get_secret(key))
        context.cache_delete_secret(key)
        self.assertIsNone(cache.get_secret(key))

    def test_cross_cache_insertion_is_rejected(self):
        target = SessionlessCache()
        value = secbytes(b"a" * 64, secbytes.SEED)
        with self.assertRaises(ValueError):
            target.take_secret(APP_COMMON_SEED_WITHOUT_PASSPHRASE, value)
        self.assertFalse(value.empty())
        self.assertIsNone(target.get_secret(APP_COMMON_SEED_WITHOUT_PASSPHRASE))
        target.clear()

    def test_revocation_renews_without_reallocation(self):
        cache = context.get_context().cache
        cache.take_secret(APP_COMMON_SEED, secbytes(b"a" * 64, secbytes.SEED))
        slot = cache.data[APP_COMMON_SEED]
        cache._secret_owner.destroy()
        self.assertIsNone(cache.get_secret(APP_COMMON_SEED))
        self.assertIs(cache.data[APP_COMMON_SEED], slot)
        # Rebind a fresh request to the renewed owner before writing again.
        request = SecretOwner(cache.get_secret_owner())
        _secret_owner_activate(request)
        try:
            cache.take_secret(APP_COMMON_SEED, secbytes(b"b" * 64, secbytes.SEED))
            self.assertIs(cache.get_secret(APP_COMMON_SEED), slot)
            cache.clear()
            self.assertTrue(slot.empty())
        finally:
            request.destroy()

    def test_only_declared_holders_are_allocated(self):
        cache = context.get_context().cache
        self.assertEqual(
            len(cache.data), len(cache.fields) + (0 if utils.BITCOIN_ONLY else 1)
        )
        self.assertEqual(
            sum(isinstance(v, secbytes) for v in cache.data),
            1 if utils.BITCOIN_ONLY else 4,
        )
        sessionless = SessionlessCache()
        self.assertEqual(len(sessionless.data), len(sessionless.fields))
        self.assertEqual(sum(isinstance(v, secbytes) for v in sessionless.data), 1)
        self.assertFalse(hasattr(sessionless, "vault_seed"))
        self.assertFalse(hasattr(sessionless, "cardano_secrets"))
        sessionless.clear()


if __name__ == "__main__":
    unittest.main()
