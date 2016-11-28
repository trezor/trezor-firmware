import time
import unittest
import common

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as proto_types

class TestMsgClearsession(common.TrezorTest):

    def test_clearsession(self):
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

        self.client.clear_session()

        # session cache is cleared
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
