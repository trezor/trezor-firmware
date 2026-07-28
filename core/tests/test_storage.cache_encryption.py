# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import AuthenticationError
from typing import Sequence

from storage import cache
from storage.cache import decrypt_cache, encrypt_cache
from storage.cache_common import (
    APP_COMMON_AUTHORIZATION_TYPE,
    CACHE_ENCRYPTED_KEYS_SEEDLESS,
    EncryptableDataCache,
)
from trezor import config, utils
from trezor.crypto import random

# The encryption logic lives entirely in `EncryptableDataCache`, shared by every
# concrete cache. So these tests operate on the pre-initialized cache instances
# directly (`_SESSIONS[i]` and the sessionless cache) instead of creating real
# protocol sessions/channels -- no wire interface or THP channel setup needed.
if utils.USE_THP:
    from storage import cache_thp as protocol_cache
    from storage.cache_common import CACHE_ENCRYPTED_KEYS_THP as PROTOCOL_KEYS
else:
    from storage import cache_codec as protocol_cache
    from storage.cache_common import CACHE_ENCRYPTED_KEYS_CODEC as PROTOCOL_KEYS


class TestStorageCacheEncryption(unittest.TestCase):

    KEYS = PROTOCOL_KEYS
    SESSIONLESS_KEYS = CACHE_ENCRYPTED_KEYS_SEEDLESS

    def setUp(self) -> None:
        # storage must be initialized/unlocked so `get_device_secret()` (which
        # derives the encryption key) can read/create the device secret.
        config.init()
        config.wipe()
        cache.clear_all()

    # --- helpers -----------------------------------------------------------

    def _session(self, index: int = 0) -> EncryptableDataCache:
        # a bare, pre-allocated protocol session cache (empty after clear_all)
        return protocol_cache._SESSIONS[index]

    def _fill(self, cache_instance: EncryptableDataCache, keys: Sequence[int]) -> dict:
        values = {}
        for key in keys:
            cache_instance.set(key, random.bytes(cache_instance._get_length(key)))
            values[key] = cache_instance.get(key)
            self.assertIsNotNone(values[key])
        return values

    def assert_encrypted(self, cache_instance: EncryptableDataCache) -> None:
        self.assertTrue(cache_instance.is_encrypted)
        # a live nonce+tag is present (not the zeroed/erased state)
        nonce, tag = cache_instance.nonce, cache_instance.authentication_tag
        self.assertNotEqual(bytes(nonce), bytes(len(nonce)))
        self.assertNotEqual(bytes(tag), bytes(len(tag)))

    def assert_plaintext(self, cache_instance: EncryptableDataCache) -> None:
        self.assertFalse(cache_instance.is_encrypted)
        # nonce+tag are preallocated buffers, erased (zeroed) when not in use
        nonce, tag = cache_instance.nonce, cache_instance.authentication_tag
        self.assertEqual(bytes(nonce), bytes(len(nonce)))
        self.assertEqual(bytes(tag), bytes(len(tag)))

    def _roundtrip(
        self, cache_instance: EncryptableDataCache, keys: Sequence[int]
    ) -> None:
        values = self._fill(cache_instance, keys)
        self.assert_plaintext(cache_instance)

        encrypt_cache()
        self.assert_encrypted(cache_instance)
        for key in keys:
            # fields are now ciphertext
            self.assertNotEqual(values[key], cache_instance.get(key))

        decrypt_cache()
        self.assert_plaintext(cache_instance)
        for key in keys:
            self.assertEqual(values[key], cache_instance.get(key))

    # --- round-trip --------------------------------------------------------

    def test_cache_encryption(self) -> None:
        self._roundtrip(self._session(), self.KEYS)

    def test_cache_encryption_sessionless(self) -> None:
        self._roundtrip(cache.get_sessionless_cache(), self.SESSIONLESS_KEYS)

    # --- skip conditions ---------------------------------------------------

    def test_cache_encryption_empty_session_skipped(self) -> None:
        # an empty session (no sensitive fields) must be left untouched
        session = self._session()
        encrypt_cache()
        self.assert_plaintext(session)

    def test_cache_encryption_preauthorized_skipped(self) -> None:
        # a preauthorized (coinjoin) session must keep its seed usable while
        # locked, so it must NOT be encrypted
        session = self._session()
        values = self._fill(session, self.KEYS)
        session.set(APP_COMMON_AUTHORIZATION_TYPE, b"\x01")

        encrypt_cache()

        self.assert_plaintext(session)
        for key in self.KEYS:
            self.assertEqual(values[key], session.get(key))

    # --- corruption: decrypt must fail and wipe the failed session ---------

    def _corrupt_and_expect_failure(self, session: EncryptableDataCache) -> None:
        with self.assertRaises(AuthenticationError):
            decrypt_cache()
        # decrypt_cache clears the failed session (fail-secure)
        for key in self.KEYS:
            self.assertIsNone(session.get(key))
        self.assert_plaintext(session)

    def test_cache_encryption_corrupted_nonce(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        self.assert_encrypted(session)  # nonce is populated before we corrupt it
        session.nonce[:] = random.bytes(len(session.nonce))
        self._corrupt_and_expect_failure(session)

    def test_cache_encryption_corrupted_authentication_tag(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        self.assert_encrypted(session)  # tag is populated before we corrupt it
        session.authentication_tag[:] = random.bytes(len(session.authentication_tag))
        self._corrupt_and_expect_failure(session)

    def test_cache_encryption_corrupted_data(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        key = self.KEYS[0]
        encrypted_value = session.get(key)
        assert encrypted_value is not None
        corrupted = bytearray(encrypted_value)
        corrupted[0] ^= 0xFF
        session.set(key, bytes(corrupted))
        self._corrupt_and_expect_failure(session)

    # --- idempotency -------------------------------------------------------

    def test_cache_encryption_double_encrypt(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        self.assert_encrypted(session)

        snapshot = {key: session.get(key) for key in self.KEYS}
        nonce = bytes(session.nonce)
        tag = bytes(session.authentication_tag)

        encrypt_cache()  # already encrypted -> no-op

        self.assert_encrypted(session)
        self.assertEqual(nonce, bytes(session.nonce))
        self.assertEqual(tag, bytes(session.authentication_tag))
        for key in self.KEYS:
            self.assertEqual(snapshot[key], session.get(key))

    def test_cache_encryption_double_decrypt(self) -> None:
        session = self._session()
        values = self._fill(session, self.KEYS)
        encrypt_cache()
        decrypt_cache()
        self.assert_plaintext(session)

        decrypt_cache()  # not encrypted -> no-op

        self.assert_plaintext(session)
        for key in self.KEYS:
            self.assertEqual(values[key], session.get(key))

    # --- multiple sessions -------------------------------------------------

    def test_cache_encryption_several_sessions(self) -> None:
        s1, s2 = self._session(0), self._session(1)
        v1 = self._fill(s1, self.KEYS)
        v2 = self._fill(s2, self.KEYS)

        encrypt_cache()
        self.assert_encrypted(s1)
        self.assert_encrypted(s2)
        self.assertNotEqual(s1.nonce, s2.nonce)
        for key in self.KEYS:
            self.assertNotEqual(v1[key], s1.get(key))
            self.assertNotEqual(v2[key], s2.get(key))

        decrypt_cache()
        self.assert_plaintext(s1)
        self.assert_plaintext(s2)
        for key in self.KEYS:
            self.assertEqual(v1[key], s1.get(key))
            self.assertEqual(v2[key], s2.get(key))

    def test_cache_encryption_decrypt_isolates_failure(self) -> None:
        # a single corrupt session must not prevent siblings from decrypting
        s1, s2 = self._session(0), self._session(1)
        self._fill(s1, self.KEYS)
        v2 = self._fill(s2, self.KEYS)

        encrypt_cache()
        self.assert_encrypted(s1)  # tag is populated before we corrupt it
        self.assert_encrypted(s2)
        s1.authentication_tag[:] = random.bytes(len(s1.authentication_tag))

        with self.assertRaises(AuthenticationError):
            decrypt_cache()

        # s1 failed -> cleared; s2 still decrypted correctly
        self.assert_plaintext(s1)
        self.assert_plaintext(s2)
        for key in self.KEYS:
            self.assertIsNone(s1.get(key))
            self.assertEqual(v2[key], s2.get(key))

    # --- eviction while encrypted ------------------------------------------

    def test_cache_encryption_clear_while_encrypted(self) -> None:
        # EndSession/Initialize/LRU eviction can clear a session while locked;
        # clear() must reset the encryption state so a later decrypt skips it
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        self.assert_encrypted(session)

        session.clear()

        self.assert_plaintext(session)
        for key in self.KEYS:
            self.assertIsNone(session.get(key))

    # --- known-answer / algorithm ------------------------------------------

    def test_cache_encryption_algorithm(self) -> None:
        from storage.device import get_device_secret
        from trezor.crypto import chacha20poly1305_decrypt

        from apps.common.seed import Slip21Node

        session = self._session()
        values = self._fill(session, self.KEYS)
        encrypt_cache()
        self.assert_encrypted(session)  # nonce and tag are populated

        # independently derive the key (cross-checks _get_slip21_key), then
        # decrypt with the stored per-cache nonce and verify the tag
        node = Slip21Node(seed=get_device_secret())
        node.derive_path([b"TREZOR", b"STORAGE", b"CACHE", b"encryption_key"])
        decryption_key = node.key()

        ctx = chacha20poly1305_decrypt(decryption_key, session.nonce)
        decrypted = {}
        for key in self.KEYS:
            encrypted_value = session.get(key)
            assert encrypted_value is not None
            decrypted[key] = ctx.decrypt(encrypted_value)
        ctx.finish(session.authentication_tag)  # raises if the tag is wrong

        for key in self.KEYS:
            self.assertEqual(values[key], decrypted[key])


if __name__ == "__main__":
    unittest.main()
