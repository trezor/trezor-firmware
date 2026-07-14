# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import device
from trezor import config
from trezor.enums import BackupType


class TestConfig(unittest.TestCase):

    def setUp(self):
        config.init()
        config.wipe()

    def test_u2f_counter(self):
        for i in range(150):
            self.assertEqual(device.next_u2f_counter(), i)
        device.set_u2f_counter(350)
        for i in range(351, 500):
            self.assertEqual(device.next_u2f_counter(), i)
        device.set_u2f_counter(0)
        self.assertEqual(device.next_u2f_counter(), 1)

    if utils.USE_THP:

        def test_cred_auth_key_counter(self):
            rounds = 200
            for i in range(rounds):
                self.assertEqual(
                    device.get_cred_auth_key_counter(), i.to_bytes(4, "big")
                )
                device.increment_cred_auth_key_counter()

            # Test get_cred_auth_key_counter does not change the counter value
            self.assertEqual(
                device.get_cred_auth_key_counter(), rounds.to_bytes(4, "big")
            )
            self.assertEqual(
                device.get_cred_auth_key_counter(), rounds.to_bytes(4, "big")
            )

        def test_cred_auth_key_counter_overflow(self):
            from storage import common
            from storage.device import _NAMESPACE, CRED_AUTH_KEY_COUNTER

            common.set(_NAMESPACE, CRED_AUTH_KEY_COUNTER, b"\xff\xff\xff\xfe")
            device.increment_cred_auth_key_counter()
            self.assertEqual(device.get_cred_auth_key_counter(), b"\xff\xff\xff\xff")
            with self.assertRaises(AssertionError) as e:
                device.increment_cred_auth_key_counter()
            self.assertEqual(e.value.value, "Overflow of cred_auth_key_counter")

        def test_device_secret(self):
            secret1 = device.get_device_secret()
            self.assertEqual(len(secret1), 16)
            secret2 = device.get_device_secret()
            self.assertEqual(secret1, secret2)
            config.wipe()
            secret3 = device.get_device_secret()
            self.assertEqual(len(secret3), 16)
            self.assertNotEqual(secret1, secret3)


class TestPermanentPassphrase(unittest.TestCase):
    """Tests for the permanent-passphrase storage helpers."""

    def setUp(self):
        config.init()
        config.wipe()

    def test_store_raw_seed_secret(self):
        """RawSeed mode overwrites the secret and clears metadata."""
        from storage import common

        raw_seed = b"\xab" * 64
        # Set up a normal BIP-39 wallet with SLIP-39 metadata present.
        device.store_mnemonic_secret(
            b"word " * 12, allow_derivation_fail=True
        )
        device.set_backup_type(BackupType.Bip39)
        common.set(device._NAMESPACE, device._SLIP39_IDENTIFIER, b"\x01\x02")
        common.set_uint8(device._NAMESPACE, device._SLIP39_ITERATION_EXPONENT, 2)
        if not utils.BITCOIN_ONLY:
            common.set(device._NAMESPACE, device._BINARY_MNEMONIC, b"\x00binary")

        device.store_raw_seed_secret(raw_seed)

        self.assertEqual(device.get_mnemonic_secret(), raw_seed)
        self.assertEqual(device.get_backup_type(), BackupType.RawSeed)
        self.assertTrue(device.no_backup())
        self.assertIsNone(
            common.get(device._NAMESPACE, device._SLIP39_IDENTIFIER)
        )
        self.assertIsNone(
            common.get(device._NAMESPACE, device._SLIP39_ITERATION_EXPONENT)
        )
        if not utils.BITCOIN_ONLY:
            self.assertIsNone(
                common.get(device._NAMESPACE, device._BINARY_MNEMONIC)
            )

    def test_store_raw_seed_secret_wrong_length(self):
        """Only a 64-byte seed is accepted for RawSeed storage."""
        with self.assertRaises(ValueError):
            device.store_raw_seed_secret(b"\xab" * 32)

    def test_get_seed_raw_seed_ignores_passphrase(self):
        """In RawSeed mode get_seed returns the stored seed unchanged."""
        from apps.common import mnemonic

        raw_seed = b"\xcd" * 64
        device.store_raw_seed_secret(raw_seed)

        self.assertEqual(
            mnemonic.get_seed(passphrase="", progress_bar=False),
            raw_seed,
        )
        self.assertEqual(
            mnemonic.get_seed(passphrase="different", progress_bar=False),
            raw_seed,
        )


if __name__ == "__main__":
    unittest.main()
