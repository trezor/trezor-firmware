import unittest
import common

from trezorlib import messages_pb2 as messages

class TestDeviceLoad(common.TrezorTest):

    def test_load_device_1(self):
        self.setup_mnemonic_nopin_nopassphrase()

        mnemonic = self.client.debug.read_mnemonic()
        self.assertEqual(mnemonic, self.mnemonic12)

        pin = self.client.debug.read_pin()[0]
        self.assertEqual(pin, '')

        passphrase_protection = self.client.debug.read_passphrase_protection()
        self.assertEqual(passphrase_protection, False)

    def test_load_device_2(self):
        self.setup_mnemonic_pin_passphrase()

        mnemonic = self.client.debug.read_mnemonic()
        self.assertEqual(mnemonic, self.mnemonic12)

        pin = self.client.debug.read_pin()[0]
        self.assertEqual(pin, self.pin4)

        passphrase_protection = self.client.debug.read_passphrase_protection()
        self.assertEqual(passphrase_protection, True)


if __name__ == '__main__':
    unittest.main()
