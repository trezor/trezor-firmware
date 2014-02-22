import time
import unittest
import common

from trezorlib import messages_pb2 as proto

class TestMsgApplysettings(common.TrezorTest):
    def test_apply_settings(self):
        self.setup_mnemonic_pin_passphrase()
        self.assertEqual(self.client.features.label, 'test')

        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(),
                                                proto.PinMatrixRequest(),
                                                proto.Success(),
                                                proto.Features()])
            self.client.apply_settings('new label', 'english')

        self.assertEqual(self.client.features.label, 'new label')

    def test_invalid_language(self):
        self.setup_mnemonic_pin_passphrase()
        self.assertEqual(self.client.features.language, 'english')

        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(),
                                                proto.PinMatrixRequest(),
                                                proto.Success(),
                                                proto.Features()])
            self.client.apply_settings('new label', 'nonexistent')

        self.assertEqual(self.client.features.language, 'english')

if __name__ == '__main__':
    unittest.main()
