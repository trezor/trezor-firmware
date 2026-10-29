# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import device
from trezor import config


class TestConfig(unittest.TestCase):
    def setUp(self):
        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))

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
            import trezorthp

            public1 = trezorthp.static_public_key(secret1)
            secret2 = device.get_device_secret()
            self.assertEqual(public1, trezorthp.static_public_key(secret2))
            config.wipe()
            self.assertTrue(config.unlock("", None))
            secret3 = device.get_device_secret()
            self.assertNotEqual(public1, trezorthp.static_public_key(secret3))


if __name__ == "__main__":
    unittest.main()
