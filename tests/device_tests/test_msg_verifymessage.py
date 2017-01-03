# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import common
import binascii
import base64

from trezorlib.client import CallException

class TestMsgVerifymessage(common.TrezorTest):

    def test_message_long(self):
        self.setup_mnemonic_nopin_nopassphrase()
        ret = self.client.verify_message(
            'Bitcoin',
            '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1bddc0aed9cf4e10dc9f57770934f4fb72a27c4510a0f4a81e09c163552416f799cd3f211ffeed0f411e9af9b927407d67115fb6d0ab1897137048efe33417fcc1'),
            "VeryLongMessage!" * 64
        )
        self.assertTrue(ret)

    def test_message_testnet(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = base64.b64decode('IFP/nvQalDo9lWCI7kScOzRkz/fiiScdkw7tFAKPoGbl6S8AY3wEws43s2gR57AfwZP8/8y7+F+wvGK9phQghN4=')
        ret = self.client.verify_message(
            'Testnet',
            'moRDikgmxcpouFtqnKnVVzLYgkDD2gQ3sk',
            sig,
            'Ahoj')
        self.assertTrue(ret)

    def test_message_verify(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # uncompressed pubkey - OK
        res = self.client.verify_message(
            'Bitcoin',
            '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1ba77e01a9e17ba158b962cfef5f13dfed676ffc2b4bada24e58f784458b52b97421470d001d53d5880cf5e10e76f02be3e80bf21e18398cbd41e8c3b4af74c8c2'),
            'This is an example of a signed message.'
        )
        self.assertTrue(res)

        # uncompressed pubkey - FAIL - wrong sig
        res = self.client.verify_message(
            'Bitcoin',
            '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1ba77e01a9e17ba158b96200000000dfed676ffc2b4bada24e58f784458b52b97421470d001d53d5880cf5e10e76f02be3e80bf21e18398cbd41e8c3b4af74c8c2'),
            'This is an example of a signed message.'
        )
        self.assertFalse(res)

        # uncompressed pubkey - FAIL - wrong msg
        res = self.client.verify_message(
            'Bitcoin',
            '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T',
            binascii.unhexlify('1ba77e01a9e17ba158b962cfef5f13dfed676ffc2b4bada24e58f784458b52b97421470d001d53d5880cf5e10e76f02be3e80bf21e18398cbd41e8c3b4af74c8c2'),
            'This is an example of a signed message!'
        )
        self.assertFalse(res)

        # compressed pubkey - OK
        res = self.client.verify_message(
            'Bitcoin',
            '1C7zdTfnkzmr13HfA2vNm5SJYRK6nEKyq8',
            binascii.unhexlify('1f44e3e461f7ca9f57c472ce1a28214df1de1dadefb6551a32d1907b80c74d5a1fbfd6daaba12dd8cb06699ce3f6941fbe0f3957b5802d13076181046e741eaaaf'),
            'This is an example of a signed message.')
        self.assertTrue(res)

        # compressed pubkey - FAIL - wrong sig
        res = self.client.verify_message(
            'Bitcoin',
            '1C7zdTfnkzmr13HfA2vNm5SJYRK6nEKyq8',
            binascii.unhexlify('1f44e3e461f7ca9f57c472000000004df1de1dadefb6551a32d1907b80c74d5a1fbfd6daaba12dd8cb06699ce3f6941fbe0f3957b5802d13076181046e741eaaaf'),
            'This is an example of a signed message.'
        )
        self.assertFalse(res)

        # compressed pubkey - FAIL - wrong msg
        res = self.client.verify_message(
            'Bitcoin',
            '1C7zdTfnkzmr13HfA2vNm5SJYRK6nEKyq8',
            binascii.unhexlify('1f44e3e461f7ca9f57c472ce1a28214df1de1dadefb6551a32d1907b80c74d5a1fbfd6daaba12dd8cb06699ce3f6941fbe0f3957b5802d13076181046e741eaaaf'),
            'This is an example of a signed message!')
        self.assertFalse(res)

        # trezor pubkey - OK
        res = self.client.verify_message(
            'Bitcoin',
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify('209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80'),
            'This is an example of a signed message.'
        )
        self.assertTrue(res)

        # trezor pubkey - FAIL - wrong sig
        res = self.client.verify_message(
            'Bitcoin',
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify('209e23edf0e4e47ff1de000002cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80'),
            'This is an example of a signed message.'
        )
        self.assertFalse(res)

        # trezor pubkey - FAIL - wrong msg
        res = self.client.verify_message(
            'Bitcoin',
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify('209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80'),
            'This is an example of a signed message!'
        )
        self.assertFalse(res)

    """
    def test_verify_bitcoind(self):
        self.setup_mnemonic_nopin_nopassphrase()

        res = self.client.verify_message(
            'Bitcoin',
            '1KzXE97kV7DrpxCViCN3HbGbiKhzzPM7TQ',
            binascii.unhexlify('1cc694f0f23901dfe3603789142f36a3fc582d0d5c0ec7215cf2ccd641e4e37228504f3d4dc3eea28bbdbf5da27c49d4635c097004d9f228750ccd836a8e1460c0'),
            u'\u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy'
        )

        self.assertTrue(res)

    def test_verify_utf(self):
        self.setup_mnemonic_nopin_nopassphrase()

        words_nfkd = u'Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a'
        words_nfc = u'P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f'

        res_nfkd = self.client.verify_message(
            'Bitcoin',
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify('1fd0ec02ed8da8df23e7fe9e680e7867cc290312fe1c970749d8306ddad1a1eda4e39588e4ec2b6a22dda4ec4f562f06e91129eea9a844a7193812de82d47c496b'),
            words_nfkd
        )

        res_nfc = self.client.verify_message(
            'Bitcoin',
            '14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e',
            binascii.unhexlify('1fd0ec02ed8da8df23e7fe9e680e7867cc290312fe1c970749d8306ddad1a1eda4e39588e4ec2b6a22dda4ec4f562f06e91129eea9a844a7193812de82d47c496b'),
            words_nfc
        )

        self.assertTrue(res_nfkd)
        self.assertTrue(res_nfc)
    """

if __name__ == '__main__':
    unittest.main()
