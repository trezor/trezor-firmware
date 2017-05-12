import unittest
import common
import trezorlib.ckd_public as bip32
import trezorlib.types_pb2 as proto_types
import binascii

class TestMsgGetaddressSegwitNative(common.TrezorTest):

    def test_show_segwit(self):
        self.setup_mnemonic_allallall()
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("49'/1'/0'/0/0"),
                                                 True, None, script_type=proto_types.SPENDWITNESS),
                         'QWywnqNMsMNavbCgMYiQLa91ApvsVRoaqt1i')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("49'/1'/0'/1/0"),
                                                 False, None, script_type=proto_types.SPENDWITNESS),
                         'QWzGpyMkAEvmkSVprBzRRVQMP6UPp17q4kQn')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("44'/1'/0'/0/0"),
                                                 False, None, script_type=proto_types.SPENDWITNESS),
                         'QWzCpc1NeTN7hNDzK9sQQ9yrTQP8zh5Hef5J')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("44'/1'/0'/0/0"),
                                                 False, None, script_type=proto_types.SPENDADDRESS),
                         'mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q')

    def test_show_multisig_3(self):
        self.setup_mnemonic_allallall()
        nodes = map(lambda index : self.client.get_public_node(self.client.expand_path("999'/1'/%d'" % index)), range(1,4))
        multisig1 = proto_types.MultisigRedeemScriptType(
            pubkeys=map(lambda n : proto_types.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2,0]), nodes),
            signatures=[b'', b'', b''],
            m=2,
        )
        multisig2 = proto_types.MultisigRedeemScriptType(
            pubkeys=map(lambda n : proto_types.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2,1]), nodes),
            signatures=[b'', b'', b''],
            m=2,
        )
        for i in [1, 2, 3]:
            self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("999'/1'/%d'/2/1" % i),
                                                     False, multisig2, script_type=proto_types.SPENDWITNESS),
                             'T7nZJt6QbGJy6Hok4EF2LqtJPcT7z7VFSrSysGS3tEqCfDPwizqy4')
            self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("999'/1'/%d'/2/0" % i),
                                                     False, multisig1, script_type=proto_types.SPENDWITNESS),
                             'T7nY3A3kewpDKumsdhonP4TBDfTXFSc2RNhZxkqmeeszRDHjM5yUn')


if __name__ == '__main__':
    unittest.main()
