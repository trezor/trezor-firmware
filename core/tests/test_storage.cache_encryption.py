# flake8: noqa: F403,F405
from typing import Sequence

from trezor import utils
from trezor.crypto import random

from common import *  # isort:skip

if utils.USE_THP:
    import thp_common
    from mock_wire_interface import MockHID
    from storage import cache_thp
    from storage.cache_common import (
        CACHE_ENCRYPTED_KEYS_CHANNEL,
        CACHE_ENCRYPTED_KEYS_SESSION_THP,
    )
else:
    from storage import cache_codec
    from storage.cache_common import CACHE_ENCRYPTED_KEYS_CODEC

from storage import cache
from storage.cache import (
    CACHE_ENCRYPTION_AUTHENTIZATION_TAG,
    CACHE_ENCRYPTION_NONCE,
    decrypt_cache,
    encrypt_cache,
)
from storage.cache_common import CACHE_ENCRYPTED_KEYS_SEEDLESS, EncryptableDataCache
from trezor import config


class TestStorageCacheEncryption(unittest.TestCase):

    if utils.USE_THP:
        keys = CACHE_ENCRYPTED_KEYS_SESSION_THP
        protocol_cache = cache_thp
        counter = 1
        channel_keys = CACHE_ENCRYPTED_KEYS_CHANNEL
    else:
        keys = CACHE_ENCRYPTED_KEYS_CODEC
        protocol_cache = cache_codec
    sessionless_keys = CACHE_ENCRYPTED_KEYS_SEEDLESS

    if utils.USE_THP:

        def setUpClass(self):
            super().__init__()

    def setUp(self):
        if utils.USE_THP:
            self.interface = MockHID()
            self.counter = 1

        config.init()
        config.wipe()
        cache.clear_all()
        if utils.USE_THP:
            self.channel = thp_common.get_new_channel(self.interface)

    def get_session(self) -> EncryptableDataCache:
        if utils.USE_THP:
            session = cache_thp.create_or_replace_session(
                self.channel.channel_cache, self.counter.to_bytes(1, "big")
            )
            self.counter += 1
        else:
            self.protocol_cache.start_session()
            session = self.protocol_cache.get_active_session()
            self.assertIsNotNone(session)
        self.assertIsInstance(session, EncryptableDataCache)
        return session

    def nonce_and_tag_set(self) -> bool:
        return CACHE_ENCRYPTION_NONCE != b"\x00" * len(
            CACHE_ENCRYPTION_NONCE
        ) and CACHE_ENCRYPTION_AUTHENTIZATION_TAG != b"\x00" * len(
            CACHE_ENCRYPTION_AUTHENTIZATION_TAG
        )

    def nonce_and_tag_not_set(self) -> bool:
        return CACHE_ENCRYPTION_NONCE == b"\x00" * len(
            CACHE_ENCRYPTION_NONCE
        ) and CACHE_ENCRYPTION_AUTHENTIZATION_TAG == b"\x00" * len(
            CACHE_ENCRYPTION_AUTHENTIZATION_TAG
        )

    def fill_encrypt_and_test(
        self, cache_instance: EncryptableDataCache, keys: Sequence[int]
    ) -> None:
        # fill the cache with random data and store the values for later comparison
        values = {}
        for key in keys:
            cache_instance.set(key, random.bytes(cache_instance._get_length(key)))
            values[key] = cache_instance.get(key)
            self.assertIsNotNone(values[key])

        # check that nonce and authentication tag are not set before encryption
        self.assertTrue(self.nonce_and_tag_not_set())

        encrypt_cache()

        # check that nonce and authentication tag are set after encryption
        self.assertTrue(self.nonce_and_tag_set())

        # check that values changed retrieved during encryption
        for key in keys:
            self.assertNotEqual(values[key], cache_instance.get(key))

        decrypt_cache()

        # check that nonce and authentication tag are not set before encryption
        self.assertTrue(self.nonce_and_tag_not_set())

        # check that values are the same after decryption
        for key in keys:
            self.assertEqual(values[key], cache_instance.get(key))

    def test_cache_encryption(self):
        session = self.get_session()
        self.fill_encrypt_and_test(session, self.keys)

    def test_cache_encryption_sessionless(self):
        sessionless_cache = cache._SESSIONLESS_CACHE
        self.assertIsNotNone(sessionless_cache)
        self.fill_encrypt_and_test(sessionless_cache, self.sessionless_keys)

    def test_cache_encryption_corrupted_nonce(self):
        session = self.get_session()
        for key in self.keys:
            session.set(key, random.bytes(session._get_length(key)))

        self.assertTrue(self.nonce_and_tag_not_set())

        encrypt_cache()

        self.assertTrue(self.nonce_and_tag_set())

        # Corrupt the nonce and check that decryption fails
        CACHE_ENCRYPTION_NONCE[:] = random.bytes(len(CACHE_ENCRYPTION_NONCE))

        with self.assertRaises(ValueError):
            decrypt_cache()

        for key in self.keys:
            self.assertIsNone(session.get(key))
        self.assertTrue(self.nonce_and_tag_not_set())

    def test_cache_encryption_corrupted_authentication_tag(self):
        session = self.get_session()
        for key in self.keys:
            session.set(key, random.bytes(session._get_length(key)))

        self.assertTrue(self.nonce_and_tag_not_set())

        encrypt_cache()

        self.assertTrue(self.nonce_and_tag_set())

        # Corrupt the authentication tag and check that decryption fails
        CACHE_ENCRYPTION_AUTHENTIZATION_TAG[:] = random.bytes(
            len(CACHE_ENCRYPTION_AUTHENTIZATION_TAG)
        )

        with self.assertRaises(ValueError):
            decrypt_cache()

        for key in self.keys:
            self.assertIsNone(session.get(key))
        self.assertTrue(self.nonce_and_tag_not_set())

    def test_cache_encryption_corrupted_data(self):
        session = self.get_session()
        for key in self.keys:
            session.set(key, random.bytes(session._get_length(key)))

        self.assertTrue(self.nonce_and_tag_not_set())

        encrypt_cache()

        self.assertTrue(self.nonce_and_tag_set())

        # Corrupt the encrypted data and check that decryption fails
        key = self.keys[0]
        encrypted_value = session.get(key)

        self.assertIsNotNone(encrypted_value)
        corrupted_value = bytearray(encrypted_value)
        corrupted_value[0] ^= 0xFF  # Flip some bits to corrupt the data
        session.set(key, bytes(corrupted_value))

        with self.assertRaises(ValueError):
            decrypt_cache()

        for key in self.keys:
            self.assertIsNone(session.get(key))
        self.assertTrue(self.nonce_and_tag_not_set())

    def test_cache_encryption_double_encrypt(self):
        session = self.get_session()
        for key in self.keys:
            session.set(key, random.bytes(session._get_length(key)))

        self.assertTrue(self.nonce_and_tag_not_set())

        encrypt_cache()

        self.assertTrue(self.nonce_and_tag_set())

        values = {}
        for key in self.keys:
            values[key] = session.get(key)
            self.assertIsNotNone(values[key])

        encrypt_cache()

        self.assertTrue(self.nonce_and_tag_set())

        for key in self.keys:
            self.assertEqual(values[key], session.get(key))

    def test_cache_encryption_double_decrypt(self):
        session = self.get_session()
        for key in self.keys:
            session.set(key, random.bytes(session._get_length(key)))

        self.assertTrue(self.nonce_and_tag_not_set())

        encrypt_cache()

        self.assertTrue(self.nonce_and_tag_set())

        decrypt_cache()

        self.assertTrue(self.nonce_and_tag_not_set())

        values = {}
        for key in self.keys:
            values[key] = session.get(key)
            self.assertIsNotNone(values[key])

        decrypt_cache()

        self.assertTrue(self.nonce_and_tag_not_set())

        for key in self.keys:
            self.assertEqual(values[key], session.get(key))

    def test_cache_encryption_several_sessions(self):
        session1 = self.get_session()
        values1 = {}
        for key in self.keys:
            session1.set(key, random.bytes(session1._get_length(key)))
            values1[key] = session1.get(key)
            self.assertIsNotNone(values1[key])

        session2 = self.get_session()
        values2 = {}
        for key in self.keys:
            session2.set(key, random.bytes(session2._get_length(key)))
            values2[key] = session2.get(key)
            self.assertIsNotNone(values2[key])

        encrypt_cache()

        self.assertTrue(self.nonce_and_tag_set())

        for key in self.keys:
            self.assertNotEqual(values1[key], session1.get(key))
            self.assertNotEqual(values2[key], session2.get(key))

        decrypt_cache()

        for key in self.keys:
            self.assertEqual(values1[key], session1.get(key))
            self.assertEqual(values2[key], session2.get(key))

        self.assertTrue(self.nonce_and_tag_not_set())

    # if utils.USE_THP:

    #     def test_cache_encryption_thp_channel(self):
    #         channel_cache = self.channel.channel_cache
    #         self.fill_encrypt_and_test(channel_cache, self.channel_keys)

    def test_cache_encryption_algorithm(self):
        from storage.device import get_device_secret
        from trezor.crypto import chacha20poly1305

        from apps.common.seed import Slip21Node

        # This test ensures that the encryption algorithm used in the cache is correct and consistent.
        session = self.get_session()
        values = {}
        for key in self.keys:
            session.set(key, random.bytes(session._get_length(key)))
            values[key] = session.get(key)
            self.assertIsNotNone(values[key])
        encrypt_cache()

        # Decrypt the data manually using the same algorithm and parameters to verify correctness

        device_secret = get_device_secret()
        label = b"Cache encryption key"
        node = Slip21Node(seed=device_secret)
        node.derive_path([label])
        decryption_key = node.key()

        nonce = bytes(CACHE_ENCRYPTION_NONCE)
        ctx = chacha20poly1305(decryption_key, nonce)
        for key in self.keys:
            encrypted_value = session.get(key, b"")
            self.assertNotEqual(encrypted_value, b"")
            decrypted_value = ctx.decrypt(encrypted_value)
            self.assertEqual(values[key], decrypted_value)


if __name__ == "__main__":
    unittest.main()
