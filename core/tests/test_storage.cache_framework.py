# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage.cache_common import (
    APP_COMMON_SEED,
    APP_COMMON_SEED_WITHOUT_PASSPHRASE,
    SessionlessCache,
)

if utils.USE_THP:
    from storage import cache_thp
else:
    from storage import cache_codec


class TestCacheFramework(TestCaseWithContext):
    def test_plain_slot_parity(self):
        cache = (
            cache_thp.SessionThpCache() if utils.USE_THP else cache_codec.SessionCache()
        )
        key = APP_COMMON_SEED
        self.assertEqual(cache.fields[key], 64)
        self.assertIsNone(cache.get_secret(key))
        value = b"a" * 64
        cache.take_secret(key, value)
        self.assertEqual(cache.get_secret(key), value)
        self.assertEqual(cache.get(key), value)
        cache.take_secret(key, b"b" * 64)
        self.assertEqual(cache.get_secret(key), b"b" * 64)
        cache.delete_secret(key)
        self.assertIsNone(cache.get_secret(key))
        self.assertFalse(cache.is_set(key))
        with self.assertRaises(AssertionError):
            cache.take_secret(key, b"x" * 65)

    def test_sessionless_routing_and_clear(self):
        cache = SessionlessCache()
        key = APP_COMMON_SEED_WITHOUT_PASSPHRASE
        self.assertEqual(len(cache.data), len(cache.fields))
        cache.take_secret(key, b"x" * 64)
        self.assertEqual(cache.get_secret(key), b"x" * 64)
        self.assertTrue(cache.is_set(key))
        cache.clear()
        self.assertIsNone(cache.get_secret(key))
        self.assertFalse(cache.is_set(key))
        with self.assertRaises(AssertionError):
            cache.get_secret(key + 1)


if __name__ == "__main__":
    unittest.main()
