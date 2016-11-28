import time
import unittest
import common

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as proto_types

class TestPing(common.TrezorTest):

    def test_ping(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses([proto.Success()])
            res = self.client.ping('random data')
            self.assertEqual(res, 'random data')

        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ProtectCall), proto.Success()])
            res = self.client.ping('random data', button_protection=True)
            self.assertEqual(res, 'random data')

        with self.client:
            self.client.set_expected_responses([proto.PinMatrixRequest(), proto.Success()])
            res = self.client.ping('random data', pin_protection=True)
            self.assertEqual(res, 'random data')

        with self.client:
            self.client.set_expected_responses([proto.PassphraseRequest(), proto.Success()])
            res = self.client.ping('random data', passphrase_protection=True)
            self.assertEqual(res, 'random data')

    def test_ping_caching(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ProtectCall), proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.Success()])
            res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
            self.assertEqual(res, 'random data')

        with self.client:
            # pin and passphrase are cached
            self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ProtectCall), proto.Success()])
            res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
            self.assertEqual(res, 'random data')

if __name__ == '__main__':
    unittest.main()
