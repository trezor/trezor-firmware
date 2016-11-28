import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types

from rlp.utils import int_to_big_endian

class TestMsgEthereumSigntx(common.TrezorTest):

    def test_ethereum_signtx_nodata(self):
        self.setup_mnemonic_nopin_nopassphrase()

        sig_v, sig_r, sig_s = self.client.ethereum_sign_tx(
            n=[0, 0],
            nonce=0,
            gas_price=20,
            gas_limit=20,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=10)
        self.assertEqual(sig_v, 27)
        self.assertEqual(binascii.hexlify(sig_r), '9b61192a161d056c66cfbbd331edb2d783a0193bd4f65f49ee965f791d898f72')
        self.assertEqual(binascii.hexlify(sig_s), '49c0bbe35131592c6ed5c871ac457feeb16a1493f64237387fab9b83c1a202f7')

        sig_v, sig_r, sig_s = self.client.ethereum_sign_tx(
            n=[0, 0],
            nonce=123456,
            gas_price=20000,
            gas_limit=20000,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=12345678901234567890)
        self.assertEqual(sig_v, 28)
        self.assertEqual(binascii.hexlify(sig_r), '6de597b8ec1b46501e5b159676e132c1aa78a95bd5892ef23560a9867528975a')
        self.assertEqual(binascii.hexlify(sig_s), '6e33c4230b1ecf96a8dbb514b4aec0a6d6ba53f8991c8143f77812aa6daa993f')

    def test_ethereum_signtx_data(self):
        self.setup_mnemonic_nopin_nopassphrase()

        sig_v, sig_r, sig_s = self.client.ethereum_sign_tx(
            n=[0, 0],
            nonce=0,
            gas_price=20,
            gas_limit=20,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=10,
            data='abcdefghijklmnop' * 16)
        self.assertEqual(sig_v, 28)
        self.assertEqual(binascii.hexlify(sig_r), '6da89ed8627a491bedc9e0382f37707ac4e5102e25e7a1234cb697cedb7cd2c0')
        self.assertEqual(binascii.hexlify(sig_s), '691f73b145647623e2d115b208a7c3455a6a8a83e3b4db5b9c6d9bc75825038a')

        sig_v, sig_r, sig_s = self.client.ethereum_sign_tx(
            n=[0, 0],
            nonce=123456,
            gas_price=20000,
            gas_limit=20000,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=12345678901234567890,
            data='ABCDEFGHIJKLMNOP' * 256 + '!!!')
        self.assertEqual(sig_v, 28)
        self.assertEqual(binascii.hexlify(sig_r), '4e90b13c45c6a9bf4aaad0e5427c3e62d76692b36eb727c78d332441b7400404')
        self.assertEqual(binascii.hexlify(sig_s), '3ff236e7d05f0f9b1ee3d70599bb4200638f28388a8faf6bb36db9e04dc544be')

    def test_ethereum_signtx_message(self):
        self.setup_mnemonic_nopin_nopassphrase()

        sig_v, sig_r, sig_s = self.client.ethereum_sign_tx(
            n=[0, 0],
            nonce=0,
            gas_price=20000,
            gas_limit=20000,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=0,
            data='ABCDEFGHIJKLMNOP' * 256 + '!!!')
        self.assertEqual(sig_v, 28)
        self.assertEqual(binascii.hexlify(sig_r), '070e9dafda4d9e733fa7b6747a75f8a4916459560efb85e3e73cd39f31aa160d')
        self.assertEqual(binascii.hexlify(sig_s), '7842db33ef15c27049ed52741db41fe3238a6fa3a6a0888fcfb74d6917600e41')


    def test_ethereum_signtx_newcontract(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # contract creation without data should fail.
        self.assertRaises(Exception, self.client.ethereum_sign_tx,
            n=[0, 0],
            nonce=123456,
            gas_price=20000,
            gas_limit=20000,
            to='',
            value=12345678901234567890)

        sig_v, sig_r, sig_s = self.client.ethereum_sign_tx(
            n=[0, 0],
            nonce=0,
            gas_price=20000,
            gas_limit=20000,
            to='',
            value=12345678901234567890,
            data='ABCDEFGHIJKLMNOP' * 256 + '!!!')
        self.assertEqual(sig_v, 28)
        self.assertEqual(binascii.hexlify(sig_r), 'b401884c10ae435a2e792303b5fc257a09f94403b2883ad8c0ac7a7282f5f1f9')
        self.assertEqual(binascii.hexlify(sig_s), '4742fc9e6a5fa8db3db15c2d856914a7f3daab21603a6c1ce9e9927482f8352e')

    def test_ethereum_sanity_checks(self):
        # gas overflow
        self.assertRaises(Exception, self.client.ethereum_sign_tx,
            n=[0, 0],
            nonce=123456,
            gas_price=0xffffffffffffffffffffffffffffffff,
            gas_limit=0xffffffffffffffffffffffffffffff,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=12345678901234567890)

        # no gas price
        self.assertRaises(Exception, self.client.ethereum_sign_tx,
            n=[0, 0],
            nonce=123456,
            gas_limit=10000,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=12345678901234567890)

        # no gas limit
        self.assertRaises(Exception, self.client.ethereum_sign_tx,
            n=[0, 0],
            nonce=123456,
            gas_price=10000,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=12345678901234567890)

        # no nonce
        self.assertRaises(Exception, self.client.ethereum_sign_tx,
            n=[0, 0],
            gas_price=10000,
            gas_limit=123456,
            to=binascii.unhexlify('1d1c328764a41bda0492b66baa30c4a339ff85ef'),
            value=12345678901234567890)

if __name__ == '__main__':
    unittest.main()
