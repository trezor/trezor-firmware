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
    APP_COMMON_SEED,
    APP_COMMON_SEED_WITHOUT_PASSPHRASE,
    SESSIONLESS_FLAG,
    DataCache,
    get_cache_encryption_key,
)
from trezor import config, utils
from trezor.crypto import random

if TYPE_CHECKING:
    from collections.abc import Sequence

if utils.USE_THP:
    from storage import cache_thp as protocol_cache
else:
    from storage import cache_codec as protocol_cache


class HaltCalled(Exception):
    pass


def _fake_halt(msg: str | None = None) -> None:
    # the real `halt` ends the emulator, which would skip every remaining test
    raise HaltCalled(msg)


def _failing_device_secret() -> bytes:
    raise RuntimeError


def _encrypted_keys(cache_instance: DataCache, flag: int = 0) -> tuple[int, ...]:
    return tuple(
        key | flag
        for key in range(cache_instance.encrypted_count)
        if cache_instance.field_sizes[key]
    )


class TestStorageCacheEncryption(unittest.TestCase):
    ENCRYPTED_KEYS = _encrypted_keys(protocol_cache._SESSIONS[0])
    SESSIONLESS_ENCRYPTED_KEYS = _encrypted_keys(
        cache.get_sessionless_cache(), SESSIONLESS_FLAG
    )

    def setUp(self) -> None:
        config.init()
        config.wipe()
        cache.clear_all()
        self._halt_patch = patch(utils, "halt", _fake_halt)
        self._halt_patch.__enter__()

    def tearDown(self) -> None:
        self._halt_patch.__exit__(None, None, None)

    # --- helpers -----------------------------------------------------------

    def _session(self, index: int = 0) -> DataCache:
        return protocol_cache._SESSIONS[index]

    def _fill(self, cache_instance: DataCache, keys: Sequence[int]) -> dict:
        values = {}
        for key in keys:
            cache_instance.set(key, random.bytes(cache_instance._get_field_size(key)))
            values[key] = cache_instance.get(key)
            self.assertIsNotNone(values[key])
        return values

    def _ciphertext(self, cache_instance: DataCache, key: int) -> bytes:
        # `get` refuses encrypted fields so read the buffer directly
        start = cache_instance._field_start(key)
        length = cache_instance.value_lengths[key & ~SESSIONLESS_FLAG] - 1
        return bytes(cache_instance.data[start : start + length])

    def _encrypted_region(self, cache_instance: DataCache) -> bytes:
        end = cache_instance._field_start(cache_instance.encrypted_count)
        return bytes(cache_instance.data[:end])

    def assert_encrypted(self, cache_instance: DataCache) -> None:
        self.assertTrue(cache_instance.is_encrypted)
        nonce, tag = cache_instance.nonce, cache_instance.authentication_tag
        self.assertTrue(any(nonce))
        self.assertTrue(any(tag))

    def assert_plaintext(self, cache_instance: DataCache) -> None:
        self.assertFalse(cache_instance.is_encrypted)
        nonce, tag = cache_instance.nonce, cache_instance.authentication_tag
        self.assertFalse(any(nonce))
        self.assertFalse(any(tag))

    def _roundtrip(self, cache_instance: DataCache, keys: Sequence[int]) -> None:
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
        self._roundtrip(self._session(), self.ENCRYPTED_KEYS)

    def test_cache_encryption_sessionless(self) -> None:
        self._roundtrip(cache.get_sessionless_cache(), self.SESSIONLESS_ENCRYPTED_KEYS)

    # --- partial fill ------------------------------------------------------

    def test_cache_encryption_seed_only(self) -> None:
        session = self._session()
        self._roundtrip(session, self.ENCRYPTED_KEYS[:1])
        for key in self.ENCRYPTED_KEYS[1:]:
            self.assertFalse(session.is_set(key))

    def test_cache_encryption_first_field_unset(self) -> None:
        # encryption must happen even though the first field is unset
        session = self._session()
        self._roundtrip(session, self.ENCRYPTED_KEYS[1:])
        self.assertFalse(session.is_set(self.ENCRYPTED_KEYS[0]))

    def test_cache_encryption_short_seed(self) -> None:
        # SLIP-39 seeds are 16 or 32 bytes in the 64-byte seed fields
        session = self._session()
        sessionless = cache.get_sessionless_cache()
        seed = random.bytes(32)
        session.set(APP_COMMON_SEED, seed)
        sessionless.set(APP_COMMON_SEED_WITHOUT_PASSPHRASE, seed)

        encrypt_cache()
        self.assert_encrypted(session)
        self.assert_encrypted(sessionless)
        self.assertNotEqual(seed, self._ciphertext(session, APP_COMMON_SEED))
        self.assertNotEqual(
            seed, self._ciphertext(sessionless, APP_COMMON_SEED_WITHOUT_PASSPHRASE)
        )

        decrypt_cache()
        self.assertEqual(seed, session.get(APP_COMMON_SEED))
        self.assertEqual(seed, sessionless.get(APP_COMMON_SEED_WITHOUT_PASSPHRASE))

    # --- skip conditions ---------------------------------------------------

    def test_cache_encryption_empty_session_skipped(self) -> None:
        session = self._session()
        encrypt_cache()
        self.assert_plaintext(session)

    def test_cache_encryption_preauthorized_skipped(self) -> None:
        # coinjoin needs the seed while locked
        session = self._session()
        values = self._fill(session, self.ENCRYPTED_KEYS)
        session.set(APP_COMMON_AUTHORIZATION_TYPE, b"\x01")

        encrypt_cache()

        self.assert_plaintext(session)
        for key in self.ENCRYPTED_KEYS:
            self.assertEqual(values[key], session.get(key))

    # --- corruption --------------------------------------------------------

    def _assert_decrypt_fails(self, session: DataCache) -> None:
        ciphertext = self._encrypted_region(session)
        # `decrypt_cache` would hide the `AuthenticationError` behind the halt
        with self.assertRaises(AuthenticationError):
            session.decrypt(get_cache_encryption_key())
        # a failed decrypt must leave the fields guarded
        self.assert_encrypted(session)
        # unauthenticated plaintext must never be written back
        self.assertEqual(ciphertext, self._encrypted_region(session))

    def test_cache_encryption_corrupted_nonce(self) -> None:
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        encrypt_cache()
        session.nonce[0] ^= 0x01  # corrupt one bit
        self._assert_decrypt_fails(session)

    def test_cache_encryption_corrupted_authentication_tag(self) -> None:
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        encrypt_cache()
        session.authentication_tag[0] ^= 0x01  # corrupt one bit
        self._assert_decrypt_fails(session)

    def test_cache_encryption_corrupted_data(self) -> None:
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        encrypt_cache()
        # flip in place, `set` refuses encrypted fields
        session.data[0] ^= 0xFF
        self._assert_decrypt_fails(session)

    def test_cache_encryption_corrupted_value_lengths(self) -> None:
        # every encrypted field's length is covered by the tag
        session = self._session()
        for key in self.ENCRYPTED_KEYS:
            session.clear()
            self._fill(session, self.ENCRYPTED_KEYS)
            encrypt_cache()
            session.value_lengths[key] ^= 0x01  # corrupt one bit
            self._assert_decrypt_fails(session)

    # --- idempotency -------------------------------------------------------

    def test_cache_encryption_double_encrypt(self) -> None:
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        encrypt_cache()
        self.assert_encrypted(session)

        snapshot = self._encrypted_region(session)
        nonce = bytes(session.nonce)
        tag = bytes(session.authentication_tag)

        encrypt_cache()

        self.assert_encrypted(session)
        self.assertEqual(nonce, bytes(session.nonce))
        self.assertEqual(tag, bytes(session.authentication_tag))
        self.assertEqual(snapshot, self._encrypted_region(session))

    def test_cache_encryption_double_decrypt(self) -> None:
        session = self._session()
        values = self._fill(session, self.ENCRYPTED_KEYS)
        encrypt_cache()
        decrypt_cache()
        self.assert_plaintext(session)

        decrypt_cache()

        self.assert_plaintext(session)
        for key in self.ENCRYPTED_KEYS:
            self.assertEqual(values[key], session.get(key))

    # --- multiple sessions -------------------------------------------------

    def test_cache_encryption_several_sessions(self) -> None:
        session_1, session_2 = self._session(0), self._session(1)
        values_1 = self._fill(session_1, self.ENCRYPTED_KEYS)
        values_2 = self._fill(session_2, self.ENCRYPTED_KEYS)

        encrypt_cache()
        self.assert_encrypted(session_1)
        self.assert_encrypted(session_2)
        self.assertNotEqual(session_1.nonce, session_2.nonce)
        self.assertNotEqual(session_1.authentication_tag, session_2.authentication_tag)
        for key in self.ENCRYPTED_KEYS:
            self.assertNotEqual(values_1[key], self._ciphertext(session_1, key))
            self.assertNotEqual(values_2[key], self._ciphertext(session_2, key))

        decrypt_cache()
        self.assert_plaintext(session_1)
        self.assert_plaintext(session_2)
        for key in self.ENCRYPTED_KEYS:
            self.assertEqual(values_1[key], session_1.get(key))
            self.assertEqual(values_2[key], session_2.get(key))

    # --- nonce -------------------------------------------------------------

    def test_nonce_differs_between_lock_cycles(self) -> None:
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        encrypt_cache()
        nonce = bytes(session.nonce)
        ciphertext = self._encrypted_region(session)

        decrypt_cache()
        encrypt_cache()

        self.assertNotEqual(nonce, bytes(session.nonce))
        self.assertNotEqual(ciphertext, self._encrypted_region(session))

    # --- eviction while encrypted ------------------------------------------

    def test_cache_encryption_clear_while_encrypted(self) -> None:
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        encrypt_cache()
        self.assert_encrypted(session)

        session.clear()

        self.assert_plaintext(session)
        for key in self.ENCRYPTED_KEYS:
            self.assertIsNone(session.get(key))

    def test_was_preauthorized_cleared_on_clear(self) -> None:
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        session.set(APP_COMMON_AUTHORIZATION_TYPE, b"\x01")
        encrypt_cache()
        self.assertTrue(session.was_preauthorized)

        session.clear()

        self.assertFalse(session.was_preauthorized)

    # --- known-answer / algorithm ------------------------------------------

    def test_cache_encryption_algorithm(self) -> None:
        from storage.device import get_device_secret
        from trezor.crypto import chacha20poly1305_decrypt
        from trezor.crypto.slip21 import Slip21Node

        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        plaintext = self._encrypted_region(session)
        encrypt_cache()

        # derive the key independently of `get_cache_encryption_key`
        node = Slip21Node(seed=get_device_secret())
        node.derive_path([b"TREZOR", b"Storage cache encryption key"])
        decryption_key = node.key()

        ctx = chacha20poly1305_decrypt(decryption_key, session.nonce)
        ctx.auth(session.value_lengths[: session.encrypted_count])
        decrypted = ctx.decrypt(self._encrypted_region(session))
        ctx.finish(session.authentication_tag)  # raises if the tag is wrong

        self.assertEqual(plaintext, decrypted)

    # --- access while encrypted --------------------------------------------

    def assert_guarded(self, cache_instance: DataCache, key: int) -> None:
        with self.assertRaises(RuntimeError):
            cache_instance.get(key)
        with self.assertRaises(RuntimeError):
            cache_instance.set(key, b"")
        with self.assertRaises(RuntimeError):
            cache_instance.delete(key)

    def test_encrypted_fields_guarded_while_encrypted(self) -> None:
        session = self._session()
        sessionless = cache.get_sessionless_cache()
        values = self._fill(session, self.ENCRYPTED_KEYS)
        sessionless_values = self._fill(sessionless, self.SESSIONLESS_ENCRYPTED_KEYS)
        encrypt_cache()

        for key in self.ENCRYPTED_KEYS:
            self.assert_guarded(session, key)
        for key in self.SESSIONLESS_ENCRYPTED_KEYS:
            self.assert_guarded(sessionless, key)

        # the refused calls left the ciphertext intact
        decrypt_cache()
        for key in self.ENCRYPTED_KEYS:
            self.assertEqual(values[key], session.get(key))
        for key in self.SESSIONLESS_ENCRYPTED_KEYS:
            self.assertEqual(sessionless_values[key], sessionless.get(key))

    def test_metadata_accessible_while_encrypted(self) -> None:
        # what runs while locked (`Initialize`, `SetBusy`, Coinjoin) must keep working
        session = self._session()
        sessionless = cache.get_sessionless_cache()
        values = self._fill(session, self.ENCRYPTED_KEYS)
        sessionless_values = self._fill(sessionless, self.SESSIONLESS_ENCRYPTED_KEYS)
        encrypt_cache()

        for c, keys in (
            (session, self.ENCRYPTED_KEYS),
            (sessionless, self.SESSIONLESS_ENCRYPTED_KEYS),
        ):
            self.assertTrue(c.has_secrets())
            for key in keys:
                self.assertTrue(c.is_set(key))

        # fields used while locked must stay outside the encrypted set
        session.set(APP_COMMON_AUTHORIZATION_TYPE, b"\x01")  # coinjoin authorization
        self.assertEqual(b"\x01", session.get(APP_COMMON_AUTHORIZATION_TYPE))
        sessionless.set_int(APP_COMMON_BUSY_DEADLINE_MS, 1)  # `SetBusy`
        self.assertEqual(1, sessionless.get_int(APP_COMMON_BUSY_DEADLINE_MS))
        # the guard must end exactly at `encrypted_count`
        for c, flag in ((session, 0), (sessionless, SESSIONLESS_FLAG)):
            key = c.encrypted_count | flag
            c.set(key, b"\xa5")  # arbitrary, different value from other set() calls
            self.assertEqual(b"\xa5", c.get(key))

        # the writes while locked left the ciphertext and tag intact
        decrypt_cache()
        for key in self.ENCRYPTED_KEYS:
            self.assertEqual(values[key], session.get(key))
        for key in self.SESSIONLESS_ENCRYPTED_KEYS:
            self.assertEqual(sessionless_values[key], sessionless.get(key))

    # --- lock and unlock ---------------------------------------------------

    def test_unlock_wrong_pin_keeps_cache_encrypted(self) -> None:
        self.assertTrue(config.change_pin("1234", None))
        session = self._session()
        values = self._fill(session, self.ENCRYPTED_KEYS)

        storage.lock()
        self.assert_encrypted(session)
        ciphertext = self._encrypted_region(session)

        self.assertFalse(storage.unlock("0000", None))
        self.assert_encrypted(session)
        self.assertEqual(ciphertext, self._encrypted_region(session))

        self.assertTrue(storage.unlock("1234", None))
        self.assert_plaintext(session)
        for key in self.ENCRYPTED_KEYS:
            self.assertEqual(values[key], session.get(key))

    # --- unlock self-check -------------------------------------------------

    def test_self_check_catches_skipped_encryption(self) -> None:
        self._fill(self._session(), self.ENCRYPTED_KEYS)
        self.assertFalse(cache.no_unexpected_plaintext())
        encrypt_cache()
        self.assertTrue(cache.no_unexpected_plaintext())

    def test_self_check_accepts_spent_preauthorization(self) -> None:
        # a coinjoin spending its last round while locked leaves the seed plaintext
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
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
        self._fill(session, self.ENCRYPTED_KEYS)
        session.nonce[0] = 1  # a live nonce makes `encrypt` refuse
        with self.assertRaises(HaltCalled):
            encrypt_cache()

    def test_decrypt_cache_halts_on_failure(self) -> None:
        session = self._session()
        self._fill(session, self.ENCRYPTED_KEYS)
        encrypt_cache()
        session.authentication_tag[0] ^= 0xFF
        with self.assertRaises(HaltCalled):
            decrypt_cache()

    def test_encrypt_cache_halts_on_key_failure(self) -> None:
        self._fill(self._session(), self.ENCRYPTED_KEYS)
        with patch(storage.device, "get_device_secret", _failing_device_secret):
            with self.assertRaises(HaltCalled):
                encrypt_cache()

    def test_decrypt_cache_halts_on_key_failure(self) -> None:
        self._fill(self._session(), self.ENCRYPTED_KEYS)
        encrypt_cache()
        with patch(storage.device, "get_device_secret", _failing_device_secret):
            with self.assertRaises(HaltCalled):
                decrypt_cache()

    # --- desync checks -----------------------------------------------------

    def test_encrypt_refuses_live_nonce_or_tag(self) -> None:
        # a live nonce/tag on a plaintext cache means an earlier call died part-way
        session = self._session()
        values = self._fill(session, self.ENCRYPTED_KEYS)
        for buffer in (session.nonce, session.authentication_tag):
            buffer[0] = 1
            with self.assertRaises(RuntimeError):
                session.encrypt(get_cache_encryption_key())
            buffer[0] = 0
        for key in self.ENCRYPTED_KEYS:
            self.assertEqual(values[key], session.get(key))

    def test_decrypt_refuses_erased_nonce_or_tag(self) -> None:
        # an encrypted cache with an erased nonce/tag means a call died part-way
        session = self._session()
        for buffer in (session.nonce, session.authentication_tag):
            session.clear()
            self._fill(session, self.ENCRYPTED_KEYS)
            encrypt_cache()
            buffer[:] = bytes(len(buffer))
            with self.assertRaises(RuntimeError):
                session.decrypt(get_cache_encryption_key())


if __name__ == "__main__":
    unittest.main()
