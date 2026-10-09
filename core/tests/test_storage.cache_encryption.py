# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import AuthenticationError
from typing import TYPE_CHECKING

import storage
from mock import patch
from storage import cache
from storage.cache import decrypt_cache, encrypt_cache
from storage.cache_common import (
    APP_COMMON_AUTHORIZATION_TYPE,
    APP_COMMON_BUSY_DEADLINE_MS,
    CACHE_ENCRYPTED_KEYS_SEEDLESS,
    SESSIONLESS_FLAG,
    EncryptableDataCache,
)
from trezor import config, utils
from trezor.crypto import random

if TYPE_CHECKING:
    from collections.abc import Sequence

if utils.USE_THP:
    from storage import cache_thp as protocol_cache
    from storage.cache_common import CACHE_ENCRYPTED_KEYS_THP as PROTOCOL_KEYS
else:
    from storage import cache_codec as protocol_cache
    from storage.cache_common import CACHE_ENCRYPTED_KEYS_CODEC as PROTOCOL_KEYS


class HaltCalled(Exception):
    pass


def _fake_halt(msg: str | None = None) -> None:
    # the real `halt` ends the emulator, which would skip every remaining test
    raise HaltCalled(msg)


class TestStorageCacheEncryption(unittest.TestCase):
    KEYS = PROTOCOL_KEYS
    SESSIONLESS_KEYS = CACHE_ENCRYPTED_KEYS_SEEDLESS

    def setUp(self) -> None:
        config.init()
        config.wipe()
        cache.clear_all()
        self._halt_patch = patch(utils, "halt", _fake_halt)
        self._halt_patch.__enter__()

    def tearDown(self) -> None:
        self._halt_patch.__exit__(None, None, None)

    # --- helpers -----------------------------------------------------------

    def _session(self, index: int = 0) -> EncryptableDataCache:
        return protocol_cache._SESSIONS[index]

    def _fill(self, cache_instance: EncryptableDataCache, keys: Sequence[int]) -> dict:
        values = {}
        for key in keys:
            cache_instance.set(key, random.bytes(cache_instance._get_length(key)))
            values[key] = cache_instance.get(key)
            self.assertIsNotNone(values[key])
        return values

    def _ciphertext(self, cache_instance: EncryptableDataCache, key: int) -> bytes:
        # `get` refuses encrypted fields so read the buffer directly
        return bytes(cache_instance.data[key & ~SESSIONLESS_FLAG][1:])

    def assert_encrypted(self, cache_instance: EncryptableDataCache) -> None:
        self.assertTrue(cache_instance.is_encrypted)
        nonce, tag = cache_instance.nonce, cache_instance.authentication_tag
        self.assertTrue(any(nonce))
        self.assertTrue(any(tag))

    def assert_plaintext(self, cache_instance: EncryptableDataCache) -> None:
        self.assertFalse(cache_instance.is_encrypted)
        nonce, tag = cache_instance.nonce, cache_instance.authentication_tag
        self.assertFalse(any(nonce))
        self.assertFalse(any(tag))

    def _roundtrip(
        self, cache_instance: EncryptableDataCache, keys: Sequence[int]
    ) -> None:
        values = self._fill(cache_instance, keys)
        self.assert_plaintext(cache_instance)

        encrypt_cache()
        self.assert_encrypted(cache_instance)
        for key in keys:
            self.assertNotEqual(values[key], self._ciphertext(cache_instance, key))

        decrypt_cache()
        self.assert_plaintext(cache_instance)
        for key in keys:
            self.assertEqual(values[key], cache_instance.get(key))

    # --- round-trip --------------------------------------------------------

    def test_cache_encryption(self) -> None:
        self._roundtrip(self._session(), self.KEYS)

    def test_cache_encryption_sessionless(self) -> None:
        self._roundtrip(cache.get_sessionless_cache(), self.SESSIONLESS_KEYS)

    # --- partial fill ------------------------------------------------------

    def test_cache_encryption_seed_only(self) -> None:
        session = self._session()
        self._roundtrip(session, self.KEYS[:1])
        for key in self.KEYS[1:]:
            self.assertFalse(session.is_set(key))

    def test_cache_encryption_first_field_unset(self) -> None:
        # a leading unset field must be skipped, not end the loop
        session = self._session()
        self._roundtrip(session, self.KEYS[1:])
        self.assertFalse(session.is_set(self.KEYS[0]))

    # --- skip conditions ---------------------------------------------------

    def test_cache_encryption_empty_session_skipped(self) -> None:
        session = self._session()
        encrypt_cache()
        self.assert_plaintext(session)

    def test_cache_encryption_preauthorized_skipped(self) -> None:
        # coinjoin needs the seed while locked
        session = self._session()
        values = self._fill(session, self.KEYS)
        session.set(APP_COMMON_AUTHORIZATION_TYPE, b"\x01")

        encrypt_cache()

        self.assert_plaintext(session)
        for key in self.KEYS:
            self.assertEqual(values[key], session.get(key))

    # --- corruption --------------------------------------------------------

    def _assert_decrypt_fails(self, session: EncryptableDataCache) -> None:
        ciphertext = {key: self._ciphertext(session, key) for key in self.KEYS}
        # `decrypt_cache` would hide the `AuthenticationError` behind the halt
        with self.assertRaises(AuthenticationError):
            session.decrypt()
        # a failed decrypt must leave the fields guarded
        self.assert_encrypted(session)
        # unauthenticated plaintext must never be written back
        for key in self.KEYS:
            self.assertEqual(ciphertext[key], self._ciphertext(session, key))

    def test_cache_encryption_corrupted_nonce(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        session.nonce[0] ^= 0x01  # corrupt one bit
        self._assert_decrypt_fails(session)

    def test_cache_encryption_corrupted_authentication_tag(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        session.authentication_tag[0] ^= 0x01  # corrupt one bit
        self._assert_decrypt_fails(session)

    def test_cache_encryption_corrupted_data(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        # flip in place, `set` refuses encrypted fields, byte 0 is the "set" flag
        session.data[self.KEYS[0]][1] ^= 0xFF
        self._assert_decrypt_fails(session)

    # --- idempotency -------------------------------------------------------

    def test_cache_encryption_double_encrypt(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        self.assert_encrypted(session)

        snapshot = {key: self._ciphertext(session, key) for key in self.KEYS}
        nonce = bytes(session.nonce)
        tag = bytes(session.authentication_tag)

        encrypt_cache()

        self.assert_encrypted(session)
        self.assertEqual(nonce, bytes(session.nonce))
        self.assertEqual(tag, bytes(session.authentication_tag))
        for key in self.KEYS:
            self.assertEqual(snapshot[key], self._ciphertext(session, key))

    def test_cache_encryption_double_decrypt(self) -> None:
        session = self._session()
        values = self._fill(session, self.KEYS)
        encrypt_cache()
        decrypt_cache()
        self.assert_plaintext(session)

        decrypt_cache()

        self.assert_plaintext(session)
        for key in self.KEYS:
            self.assertEqual(values[key], session.get(key))

    # --- multiple sessions -------------------------------------------------

    def test_cache_encryption_several_sessions(self) -> None:
        session_1, session_2 = self._session(0), self._session(1)
        values_1 = self._fill(session_1, self.KEYS)
        values_2 = self._fill(session_2, self.KEYS)

        encrypt_cache()
        self.assert_encrypted(session_1)
        self.assert_encrypted(session_2)
        self.assertNotEqual(session_1.nonce, session_2.nonce)
        self.assertNotEqual(session_1.authentication_tag, session_2.authentication_tag)
        for key in self.KEYS:
            self.assertNotEqual(values_1[key], self._ciphertext(session_1, key))
            self.assertNotEqual(values_2[key], self._ciphertext(session_2, key))

        decrypt_cache()
        self.assert_plaintext(session_1)
        self.assert_plaintext(session_2)
        for key in self.KEYS:
            self.assertEqual(values_1[key], session_1.get(key))
            self.assertEqual(values_2[key], session_2.get(key))

    # --- nonce -------------------------------------------------------------

    def test_nonce_differs_between_lock_cycles(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        nonce = bytes(session.nonce)
        ciphertext = self._ciphertext(session, self.KEYS[0])

        decrypt_cache()
        encrypt_cache()

        self.assertNotEqual(nonce, bytes(session.nonce))
        self.assertNotEqual(ciphertext, self._ciphertext(session, self.KEYS[0]))

    # --- eviction while encrypted ------------------------------------------

    def test_cache_encryption_clear_while_encrypted(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        self.assert_encrypted(session)

        session.clear()

        self.assert_plaintext(session)
        for key in self.KEYS:
            self.assertIsNone(session.get(key))

    def test_was_preauthorized_cleared_on_clear(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        session.set(APP_COMMON_AUTHORIZATION_TYPE, b"\x01")
        encrypt_cache()
        self.assertTrue(session.was_preauthorized)

        session.clear()

        self.assertFalse(session.was_preauthorized)

    # --- known-answer / algorithm ------------------------------------------

    def test_cache_encryption_algorithm(self) -> None:
        from storage.device import get_device_secret
        from trezor.crypto import chacha20poly1305_decrypt

        from apps.common.seed import Slip21Node

        session = self._session()
        values = self._fill(session, self.KEYS)
        encrypt_cache()

        # derive the key independently of `_get_slip21_key`
        node = Slip21Node(seed=get_device_secret())
        node.derive_path([b"TREZOR", b"STORAGE", b"CACHE", b"encryption_key"])
        decryption_key = node.key()

        ctx = chacha20poly1305_decrypt(decryption_key, session.nonce)
        decrypted = {}
        for key in self.KEYS:
            decrypted[key] = ctx.decrypt(self._ciphertext(session, key))
        ctx.finish(session.authentication_tag)  # raises if the tag is wrong

        for key in self.KEYS:
            self.assertEqual(values[key], decrypted[key])

    # --- access while encrypted --------------------------------------------

    def assert_guarded(self, cache_instance: EncryptableDataCache, key: int) -> None:
        with self.assertRaises(RuntimeError):
            cache_instance.get(key)
        with self.assertRaises(RuntimeError):
            cache_instance.set(key, b"")
        with self.assertRaises(RuntimeError):
            cache_instance.delete(key)

    def test_encrypted_fields_guarded_while_encrypted(self) -> None:
        session = self._session()
        sessionless = cache.get_sessionless_cache()
        values = self._fill(session, self.KEYS)
        sessionless_values = self._fill(sessionless, self.SESSIONLESS_KEYS)
        encrypt_cache()

        for key in self.KEYS:
            self.assert_guarded(session, key)
        # the sessionless cache indexes without the flag, so it is checked separately
        for key in self.SESSIONLESS_KEYS:
            self.assert_guarded(sessionless, key)

        # the refused calls left the ciphertext intact
        decrypt_cache()
        for key in self.KEYS:
            self.assertEqual(values[key], session.get(key))
        for key in self.SESSIONLESS_KEYS:
            self.assertEqual(sessionless_values[key], sessionless.get(key))

    def test_metadata_accessible_while_encrypted(self) -> None:
        # what `Initialize` and `SetBusy` touch while locked must keep working
        session = self._session()
        sessionless = cache.get_sessionless_cache()
        self._fill(session, self.KEYS)
        self._fill(sessionless, self.SESSIONLESS_KEYS)
        encrypt_cache()

        for c, keys in ((session, self.KEYS), (sessionless, self.SESSIONLESS_KEYS)):
            self.assertTrue(c.has_secrets())
            for key in keys:
                self.assertTrue(c.is_set(key))
                self.assertEqual(c._get_length(key), len(self._ciphertext(c, key)))

        # fields outside the encrypted set stay readable and writable
        session.set(APP_COMMON_AUTHORIZATION_TYPE, b"\x01")
        self.assertEqual(b"\x01", session.get(APP_COMMON_AUTHORIZATION_TYPE))
        sessionless.set_int(APP_COMMON_BUSY_DEADLINE_MS, 1)
        self.assertEqual(1, sessionless.get_int(APP_COMMON_BUSY_DEADLINE_MS))

    # --- lock and unlock ---------------------------------------------------

    def test_unlock_wrong_pin_keeps_cache_encrypted(self) -> None:
        self.assertTrue(config.change_pin("1234", None))
        session = self._session()
        values = self._fill(session, self.KEYS)

        storage.lock()
        self.assert_encrypted(session)
        ciphertext = {key: self._ciphertext(session, key) for key in self.KEYS}

        self.assertFalse(storage.unlock("0000", None))
        self.assert_encrypted(session)
        for key in self.KEYS:
            self.assertEqual(ciphertext[key], self._ciphertext(session, key))

        self.assertTrue(storage.unlock("1234", None))
        self.assert_plaintext(session)
        for key in self.KEYS:
            self.assertEqual(values[key], session.get(key))

    # --- unlock self-check -------------------------------------------------

    def test_self_check_catches_skipped_encryption(self) -> None:
        self._fill(self._session(), self.KEYS)
        self.assertFalse(cache.no_unexpected_plaintext())
        encrypt_cache()
        self.assertTrue(cache.no_unexpected_plaintext())

    def test_self_check_accepts_spent_preauthorization(self) -> None:
        # a coinjoin spending its last round while locked leaves the seed plaintext
        session = self._session()
        self._fill(session, self.KEYS)
        session.set(APP_COMMON_AUTHORIZATION_TYPE, b"\x01")
        encrypt_cache()
        self.assertTrue(session.was_preauthorized)

        session.delete(APP_COMMON_AUTHORIZATION_TYPE)  # `authorization.clear()`
        self.assertTrue(cache.no_unexpected_plaintext())

        decrypt_cache()
        self.assertFalse(session.was_preauthorized)

    # --- halt policy -------------------------------------------------------

    def test_encrypt_cache_halts_on_failure(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        session.nonce[0] = 1  # a live nonce makes `encrypt` refuse
        with self.assertRaises(HaltCalled):
            encrypt_cache()

    def test_decrypt_cache_halts_on_failure(self) -> None:
        session = self._session()
        self._fill(session, self.KEYS)
        encrypt_cache()
        session.authentication_tag[0] ^= 0xFF
        with self.assertRaises(HaltCalled):
            decrypt_cache()

    # --- desync checks -----------------------------------------------------

    def test_encrypt_refuses_live_nonce_or_tag(self) -> None:
        # a live nonce/tag on a plaintext cache means an earlier call died part-way
        session = self._session()
        values = self._fill(session, self.KEYS)
        for buffer in (session.nonce, session.authentication_tag):
            buffer[0] = 1
            with self.assertRaises(RuntimeError):
                session.encrypt()
            buffer[0] = 0
        for key in self.KEYS:
            self.assertEqual(values[key], session.get(key))

    def test_decrypt_refuses_erased_nonce_or_tag(self) -> None:
        # an encrypted cache with an erased nonce/tag means a call died part-way
        session = self._session()
        for buffer in (session.nonce, session.authentication_tag):
            session.clear()
            self._fill(session, self.KEYS)
            encrypt_cache()
            buffer[:] = bytes(len(buffer))
            with self.assertRaises(RuntimeError):
                session.decrypt()


if __name__ == "__main__":
    unittest.main()
