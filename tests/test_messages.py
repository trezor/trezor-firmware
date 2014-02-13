import unittest
import common
import binascii
import base64

from trezorlib.client import CallException

class TestMessages(common.TrezorTest):

    def test_message_sign(self):
        sig = self.client.sign_message([0], "This is an example of a signed message.")
        self.assertEqual(sig.address, '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e')
        self.assertEqual(binascii.hexlify(sig.signature), '209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80')

    def test_too_long(self):
        # Message cannot be longer than 255 bytes
        self.assertRaises(CallException, self.client.sign_message, [0], '1' * 256)
        
        ret = self.client.verify_message('1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1ba77e01a9e17ba158b962cfef5f13dfed676ffc2b4bada24e58f784458b52b97421470d001d53d5880cf5e10e76f02be3e80bf21e18398cbd41e8c3b4af74c8c2'),
            '1' * 256
        )
        self.assertFalse(ret)

    def test_message_testnet(self):
        sig = base64.b64decode('IFP/nvQalDo9lWCI7kScOzRkz/fiiScdkw7tFAKPoGbl6S8AY3wEws43s2gR57AfwZP8/8y7+F+wvGK9phQghN4=')
        ret = self.client.verify_message('moRDikgmxcpouFtqnKnVVzLYgkDD2gQ3sk', sig, 'Ahoj')

        self.assertTrue(ret)
        
        
    def test_message_verify(self):

        # uncompressed pubkey - OK
        res = self.client.verify_message(
            '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1ba77e01a9e17ba158b962cfef5f13dfed676ffc2b4bada24e58f784458b52b97421470d001d53d5880cf5e10e76f02be3e80bf21e18398cbd41e8c3b4af74c8c2'),
            'This is an example of a signed message.'
        )
        self.assertTrue(res)

        # uncompressed pubkey - FAIL
        res = self.client.verify_message(
            '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1ba77e01a9e17ba158b96200000000dfed676ffc2b4bada24e58f784458b52b97421470d001d53d5880cf5e10e76f02be3e80bf21e18398cbd41e8c3b4af74c8c2'),
            'This is an example of a signed message.'
        )
        self.assertFalse(res)

        # compressed pubkey - OK
        res = self.client.verify_message(
            '1C7zdTfnkzmr13HfA2vNm5SJYRK6nEKyq8',
            binascii.unhexlify('1f44e3e461f7ca9f57c472ce1a28214df1de1dadefb6551a32d1907b80c74d5a1fbfd6daaba12dd8cb06699ce3f6941fbe0f3957b5802d13076181046e741eaaaf'),
            'This is an example of a signed message.')
        self.assertTrue(res)

        # compressed pubkey - FAIL
        res = self.client.verify_message(
            '1C7zdTfnkzmr13HfA2vNm5SJYRK6nEKyq8',
            binascii.unhexlify('1f44e3e461f7ca9f57c472000000004df1de1dadefb6551a32d1907b80c74d5a1fbfd6daaba12dd8cb06699ce3f6941fbe0f3957b5802d13076181046e741eaaaf'),
            'This is an example of a signed message.'
        )
        self.assertFalse(res)

        # trezor pubkey - OK
        res = self.client.verify_message(
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify('209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80'),
            'This is an example of a signed message.'
        )
        self.assertTrue(res)

        # trezor pubkey - FAIL
        res = self.client.verify_message(
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify('209e23edf0e4e47ff1de000002cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80'),
            'This is an example of a signed message.'
        )
        self.assertFalse(res)

if __name__ == '__main__':
    unittest.main()

