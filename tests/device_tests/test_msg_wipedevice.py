import unittest
import common

from trezorlib import messages_pb2 as proto

class TestDeviceWipe(common.TrezorTest):
    def test_wipe_device(self):
        self.setup_mnemonic_pin_passphrase()
        features = self.client.call_raw(proto.Initialize())

        self.assertEqual(features.initialized, True)
        self.assertEqual(features.pin_protection, True)
        self.assertEqual(features.passphrase_protection, True)
        device_id = features.device_id

        self.client.wipe_device()
        features = self.client.call_raw(proto.Initialize())

        self.assertEqual(features.initialized, False)
        self.assertEqual(features.pin_protection, False)
        self.assertEqual(features.passphrase_protection, False)
        self.assertNotEqual(features.device_id, device_id)

if __name__ == '__main__':
    unittest.main()
