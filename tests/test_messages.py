import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types

class TestMessages(common.TrezorTest):

    def test_message_sign(self):
        sig = self.client.sign_message([0], "This is an example of a signed message.")
        self.assertEqual(sig.address, '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e')
        self.assertEqual(binascii.hexlify(sig.signature), XXX)

    def test_message_verify(self):

        # uncompressed pubkey - OK
        res = self.client.verify_message(
            '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1ba77e01a9e17ba158b962cfef5f13dfed676ffc2b4bada24e58f784458b52b97421470d001d53d5880cf5e10e76f02be3e80bf21e18398cbd41e8c3b4af74c8c2'),
            'This is an example of a signed message.'
        )
        self.assertIsInstance(res, proto.Success)

        # uncompressed pubkey - FAIL
        res = self.client.verify_message(
            '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1ba77e01a9e17ba158b96200000000dfed676ffc2b4bada24e58f784458b52b97421470d001d53d5880cf5e10e76f02be3e80bf21e18398cbd41e8c3b4af74c8c2'),
            'This is an example of a signed message.'
        )
        self.assertIsInstance(res, proto.Failure)
        self.assertEqual(res.code, proto_types.Failure_InvalidSignature)

        # compressed pubkey - OK
        res = self.client.verify_message(
            '1C7zdTfnkzmr13HfA2vNm5SJYRK6nEKyq8',
            binascii.unhexlify('1f44e3e461f7ca9f57c472ce1a28214df1de1dadefb6551a32d1907b80c74d5a1fbfd6daaba12dd8cb06699ce3f6941fbe0f3957b5802d13076181046e741eaaaf'),
            'This is an example of a signed message.')
        self.assertIsInstance(res, proto.Success)

        # compressed pubkey - FAIL
        res = self.client.verify_message(
            '1C7zdTfnkzmr13HfA2vNm5SJYRK6nEKyq8',
            binascii.unhexlify('1f44e3e461f7ca9f57c472000000004df1de1dadefb6551a32d1907b80c74d5a1fbfd6daaba12dd8cb06699ce3f6941fbe0f3957b5802d13076181046e741eaaaf'),
            'This is an example of a signed message.'
        )
        self.assertIsInstance(res, proto.Failure)
        self.assertEqual(res.code, proto_types.Failure_InvalidSignature)

        # trezor pubkey - OK
        res = self.client.verify_message(
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify(XXX),
            'This is an example of a signed message.'
        )
        self.assertIsInstance(res, proto.Success)

        # trezor pubkey - FAIL
        res = self.client.verify_message(
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify(XXX__),
            'This is an example of a signed message.'
        )
        self.assertIsInstance(res, proto.Failure)
        self.assertEqual(res.code, proto_types.Failure_InvalidSignature)
