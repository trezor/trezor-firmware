from common import *  # isort:skip

from storage import device
from trezor import config, utils
from trezor.enums import ThpPairingMethod

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
            from storage.device import _NAMESPACE, _CRED_AUTH_KEY_COUNTER

            common.set(_NAMESPACE, _CRED_AUTH_KEY_COUNTER, b"\xff\xff\xff\xfe")
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

        def test_enabled_pairing_methods(self):
            stored = device.get_enabled_pairing_methods()
            self.assertEqual(stored, [])
            device.enable_pairing_method(ThpPairingMethod.CodeEntry)
            device.enable_pairing_method(ThpPairingMethod.QrCode)
            stored = device.get_enabled_pairing_methods()
            self.assertEqual(
                stored, [ThpPairingMethod.CodeEntry, ThpPairingMethod.QrCode]
            )
            device.disable_pairing_method(ThpPairingMethod.CodeEntry)
            stored = device.get_enabled_pairing_methods()
            self.assertTrue(ThpPairingMethod.CodeEntry not in stored)
            self.assertEqual(stored, [ThpPairingMethod.QrCode])

            # invalid values can be stored in the storage but will be ignored
            # when calling device.get_enabled_pairing_methods()
            with self.assertRaises(AssertionError) as e:
                device.enable_pairing_method(6)
            self.assertEqual(e.value.value, "Invalid pairing method")
            with self.assertRaises(AssertionError) as e:
                device.enable_pairing_method(0)
            self.assertEqual(e.value.value, "Invalid pairing method")
            with self.assertRaises(AssertionError) as e:
                device.disable_pairing_method(5)
            self.assertEqual(e.value.value, "Invalid pairing method")

            stored = device.get_enabled_pairing_methods()
            self.assertEqual(stored, [ThpPairingMethod.QrCode])


if __name__ == "__main__":
    unittest.main()
