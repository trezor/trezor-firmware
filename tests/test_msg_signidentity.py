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
        self.assertEqual(sig.address, '1G24md2ep5kjFGNT8Fe4RtZG2JE9GR1Xqe')
        self.assertEqual(binascii.hexlify(sig.public_key), '0284efcc0a291c6ce86d016456a3c87f832f63c3266fd202a0785d3c10b02ef245')
        self.assertEqual(binascii.hexlify(sig.signature), '1f66f1c8ef5ec104ea29b8270e4c5a622eb75fc51d40c81ce08176a0d3a1e197d9952b002b4bc278e7affabad3ff238e68c589f5b1a23990e019c20ac1d4269596')

        identity = proto_types.IdentityType(proto='ftp', user='satoshi', host='bitcoin.org', port='2323', path='/pub', index=3)
        sig = self.client.sign_identity(identity, binascii.unhexlify('531c4dd0a92caff62817eaec3065b65d'), '2015/02/20 16:50')
        self.assertEqual(sig.address, '14p4LLCkw5HcqM55hA3ueZvZGYkePNeZaU')
        self.assertEqual(binascii.hexlify(sig.public_key), '0333ea41759da347f4f4f487be0c396a0f88d36218598697fba9560fdb235e1442')
        self.assertEqual(binascii.hexlify(sig.signature), '1fd6e658e3e806f3a28af1b665cf1a6ada8bb2e892e8bb2770cf1a32b81552bbbb68f5f12b7d18a94fac054d30984b7e08700091f89020a78184f039d28ace2da0')

        identity = proto_types.IdentityType(proto='ssh', user='satoshi', host='bitcoin.org', port='', path='', index=47)
        sig = self.client.sign_identity(identity, binascii.unhexlify('531c4dd0a92caff62817eaec3065b65d'), '2015/02/20 16:50')
        self.assertEqual(sig.address, '1P3qCVo8nw8kBGp7DrYros22mKeWUkcdXw')
        self.assertEqual(binascii.hexlify(sig.public_key), '02c7a59992fa91b380da753b9f725a7803d86c4ec97123b3b5158d8fb395d552d7')
        self.assertEqual(binascii.hexlify(sig.signature), '1fb2ff582d156c830da4dabd5ec6bf65c65198ebf871b8cafd461b7c4aca823f0bee0a46e7f7059774b0f2a3066a705612303ae485c5e8330cc46ad6b3c85886c9')

if __name__ == '__main__':
    unittest.main()
