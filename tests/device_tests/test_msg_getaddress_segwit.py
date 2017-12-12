import unittest
import common
import trezorlib.ckd_public as bip32
from trezorlib import messages as proto


class TestMsgGetaddressSegwit(common.TrezorTest):

    def test_show_segwit(self):
        self.setup_mnemonic_allallall()
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("49'/1'/0'/1/0"),
                                                 True, None, script_type=proto.InputScriptType.SPENDP2SHWITNESS),
                         '2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("49'/1'/0'/0/0"),
                                                 False, None, script_type=proto.InputScriptType.SPENDP2SHWITNESS),
                         '2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("44'/1'/0'/0/0"),
                                                 False, None, script_type=proto.InputScriptType.SPENDP2SHWITNESS),
                         '2N6UeBoqYEEnybg4cReFYDammpsyDw8R2Mc')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("44'/1'/0'/0/0"),
                                                 False, None, script_type=proto.InputScriptType.SPENDADDRESS),
                         'mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q')

    def test_show_multisig_3(self):
        self.setup_mnemonic_allallall()
        nodes = map(lambda index: self.client.get_public_node(self.client.expand_path("999'/1'/%d'" % index)), range(1, 4))
        multisig1 = proto.MultisigRedeemScriptType(
            pubkeys=list(map(lambda n: proto.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2, 0]), nodes)),
            signatures=[b'', b'', b''],
            m=2,
        )
        # multisig2 = proto.MultisigRedeemScriptType(
        #     pubkeys=map(lambda n: proto.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2, 1]), nodes),
        #     signatures=[b'', b'', b''],
        #     m=2,
        # )
        for i in [1, 2, 3]:
            self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("999'/1'/%d'/2/0" % i),
                                                     False, multisig1, script_type=proto.InputScriptType.SPENDP2SHWITNESS),
                             '2N2MxyAfifVhb3AMagisxaj3uij8bfXqf4Y')
