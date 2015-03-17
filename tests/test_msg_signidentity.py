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
        self.assertEqual(binascii.hexlify(sig.signature), '1fe5abeb9ed3926229a4c7d6936cf58c7357180c90a0e9565133b8578e118c5b2c7c4b6902afe81ce46f3b77e8f91a7cdae30e433ce2706166bf27ff111fc9734a')

        identity = proto_types.IdentityType(proto='ftp', user='satoshi', host='bitcoin.org', port='2323', path='/pub', index=3)
        sig = self.client.sign_identity(identity, binascii.unhexlify('531c4dd0a92caff62817eaec3065b65d'), '2015/02/20 16:50')
        self.assertEqual(sig.address, '1KAr6r5qF2kADL8bAaRQBjGKYEGxn9WrbS')
        self.assertEqual(binascii.hexlify(sig.public_key), '0266cf12d2ba381c5fd797da0d64f59c07a6f1b034ad276cca6bf2729e92b20d9c')
        self.assertEqual(binascii.hexlify(sig.signature), '1fda9910ed2c8cb5a79558c4f50d5030454cc4115931eac8e6307eb4f6ef87490b484beeff76369fa2f46e0677eb535bd78f35d0f987043ce14f25f9c610cb9c3a')

        identity = proto_types.IdentityType(proto='ssh', user='satoshi', host='bitcoin.org', port='', path='', index=47)
        sig = self.client.sign_identity(identity, binascii.unhexlify('531c4dd0a92caff62817eaec3065b65d'), '2015/02/20 16:50')
        self.assertEqual(sig.address, '16MMzfyr5LPBNZ359NhjCthi2scrMufTAM')
        self.assertEqual(binascii.hexlify(sig.public_key), '03cebfae5359d6c48b8dcf9da22b2113096548407ce21da8ab28a886f750f217f4')
        self.assertEqual(binascii.hexlify(sig.signature), '20a645c1bfa9629d92c9ec5e21350264b806c44042597d77b635e89e3c8ea1a0230662df667b3d427a2c232d41b173b86a5492caf22d317820d7e5112186e0a933')

if __name__ == '__main__':
    unittest.main()
