import time
import unittest
import common

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as proto_types

class TestPing(common.TrezorTest):

    def test_ping(self):
        self.client.wipe_device()
        self.client.load_device_by_mnemonic(
            mnemonic=self.mnemonic1,
            pin=self.pin1,
            passphrase_protection=True,
            label='test',
            language='english',
        )

        self.client.set_expected_responses([proto.Success()])
        res = self.client.ping('random data')
        self.assertEqual(res, 'random data')

        self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_Other),proto.Success()])
        res = self.client.ping('random data', button_protection=True)
        self.assertEqual(res, 'random data')

        self.client.set_expected_responses([proto.PinMatrixRequest(),proto.Success()])
        res = self.client.ping('random data', pin_protection=True)
        self.assertEqual(res, 'random data')

        self.client.set_expected_responses([proto.PassphraseRequest(),proto.Success()])
        res = self.client.ping('random data', passphrase_protection=True)
        self.assertEqual(res, 'random data')

    def test_ping_caching(self):
        self.client.wipe_device()
        self.client.load_device_by_mnemonic(
            mnemonic=self.mnemonic1,
            pin=self.pin1,
            passphrase_protection=True,
            label='test',
            language='english',
        )

        self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_Other),proto.PinMatrixRequest(),proto.PassphraseRequest(),proto.Success()])
        res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
        self.assertEqual(res, 'random data')

        # pin and passphrase are cached
        self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_Other)])
        res = self.client.ping('random data', button_protection=True, pin_protection=True, passphrase_protection=True)
        self.assertEqual(res, 'random data')

if __name__ == '__main__':
    unittest.main()
