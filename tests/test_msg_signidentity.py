import unittest
import common
import binascii

from trezorlib.client import CallException
import trezorlib.types_pb2 as proto_types

class TestMsgSignidentity(common.TrezorTest):

    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()

        identity = proto_types.IdentityType(proto='https', user='satoshi', host='bitcoin.org', port='', path='/login', index=0)
        sig = self.client.sign_identity(identity, binascii.unhexlify('531c4dd0a92caff62817eaec3065b65d'), '2015/02/20 16:50')
        self.assertEqual(sig.address, '17F17smBTX9VTZA9Mj8LM5QGYNZnmziCjL')
        self.assertEqual(binascii.hexlify(sig.public_key), '023a472219ad3327b07c18273717bb3a40b39b743756bf287fbd5fa9d263237f45')
        self.assertEqual(binascii.hexlify(sig.signature), '208e131a2ee1b9b5108b899f21f167a9e17d2daaba4e33724838ab692e28a512047ee322fe86d3e9b8624b28741de8e2595ea2d6af4487729711b72cb05f766fc0')

        identity = proto_types.IdentityType(proto='ftp', user='satoshi', host='bitcoin.org', port='2323', path='/pub', index=3)
        sig = self.client.sign_identity(identity, binascii.unhexlify('531c4dd0a92caff62817eaec3065b65d'), '2015/02/20 16:50')
        self.assertEqual(sig.address, '1KAr6r5qF2kADL8bAaRQBjGKYEGxn9WrbS')
        self.assertEqual(binascii.hexlify(sig.public_key), '0266cf12d2ba381c5fd797da0d64f59c07a6f1b034ad276cca6bf2729e92b20d9c')
        self.assertEqual(binascii.hexlify(sig.signature), '20d24fff632767928a997af046ca22bf56662559a9619af38d972e45fa806c55a403c26157d27aa21d2380bb39792278b063df082793c99b450501aa40a7c31d53')

        identity = proto_types.IdentityType(proto='ssh', user='satoshi', host='bitcoin.org', port='', path='', index=47)
        sig = self.client.sign_identity(identity, binascii.unhexlify('531c4dd0a92caff62817eaec3065b65d'), '2015/02/20 16:50')
        self.assertEqual(sig.address, '16MMzfyr5LPBNZ359NhjCthi2scrMufTAM')
        self.assertEqual(binascii.hexlify(sig.public_key), '03cebfae5359d6c48b8dcf9da22b2113096548407ce21da8ab28a886f750f217f4')
        self.assertEqual(binascii.hexlify(sig.signature), '1f888a4b2b719d06b951799527eb753ec79a850b85c81b36b66caa2f3779a5e73827a2db77b8a1d2e51bb57d681b16ee12dc4af781aba80dfb956ede94b985e393')

if __name__ == '__main__':
    unittest.main()
