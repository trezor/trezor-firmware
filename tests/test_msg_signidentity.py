import unittest
import common
import binascii

from trezorlib.client import CallException
import trezorlib.types_pb2 as proto_types

class TestMsgSignidentity(common.TrezorTest):

    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()

        hidden = binascii.unhexlify('cd8552569d6e4509266ef137584d1e62c7579b5b8ed69bbafa4b864c6521e7c2')
        visual = '2015-03-23 17:39:22'

        identity = proto_types.IdentityType(proto='https', user='satoshi', host='bitcoin.org', port='', path='/login', index=0)
        sig = self.client.sign_identity(identity, hidden, visual)
        self.assertEqual(sig.address, '17F17smBTX9VTZA9Mj8LM5QGYNZnmziCjL')
        self.assertEqual(binascii.hexlify(sig.public_key), '023a472219ad3327b07c18273717bb3a40b39b743756bf287fbd5fa9d263237f45')
        self.assertEqual(binascii.hexlify(sig.signature), '20f2d1a42d08c3a362be49275c3ffeeaa415fc040971985548b9f910812237bb41770bf2c8d488428799fbb7e52c11f1a3404011375e4080e077e0e42ab7a5ba02')

        identity = proto_types.IdentityType(proto='ftp', user='satoshi', host='bitcoin.org', port='2323', path='/pub', index=3)
        sig = self.client.sign_identity(identity, hidden, visual)
        self.assertEqual(sig.address, '1KAr6r5qF2kADL8bAaRQBjGKYEGxn9WrbS')
        self.assertEqual(binascii.hexlify(sig.public_key), '0266cf12d2ba381c5fd797da0d64f59c07a6f1b034ad276cca6bf2729e92b20d9c')
        self.assertEqual(binascii.hexlify(sig.signature), '20bbd12dc657d534fc0f7e40186e22c447e0866a016f654f380adffa9a84e9faf412a1bb0ae908296537838cf91145e77da08681c63d07b7dca40728b9e6cb17cf')

        identity = proto_types.IdentityType(proto='ssh', user='satoshi', host='bitcoin.org', port='', path='', index=47)
        sig = self.client.sign_identity(identity, hidden, visual)
        self.assertEqual(sig.address, '')
        self.assertEqual(binascii.hexlify(sig.public_key), '03cebfae5359d6c48b8dcf9da22b2113096548407ce21da8ab28a886f750f217f4')
        self.assertEqual(binascii.hexlify(sig.signature), '00122463a8430b74b5d8c41d7c9bacc65f0eb51ceda71b9fec112e76bf2e56d8a64a66b8e019678315dc08e3be96905ea7718ec3b731e8e57e1613671ee91d1706')

if __name__ == '__main__':
    unittest.main()
