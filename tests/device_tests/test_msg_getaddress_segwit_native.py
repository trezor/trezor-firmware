import unittest
import common
import trezorlib.ckd_public as bip32
from trezorlib import messages as proto


class TestMsgGetaddressSegwitNative(common.TrezorTest):

    def test_show_segwit(self):
        self.setup_mnemonic_allallall()
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("49'/1'/0'/0/0"),
                                                 True, None, script_type=proto.InputScriptType.SPENDWITNESS),
                         'tb1qqzv60m9ajw8drqulta4ld4gfx0rdh82un5s65s')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("49'/1'/0'/1/0"),
                                                 False, None, script_type=proto.InputScriptType.SPENDWITNESS),
                         'tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("44'/1'/0'/0/0"),
                                                 False, None, script_type=proto.InputScriptType.SPENDWITNESS),
                         'tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc')
        self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("44'/1'/0'/0/0"),
                                                 False, None, script_type=proto.InputScriptType.SPENDADDRESS),
                         'mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q')

    def test_show_multisig_3(self):
        self.setup_mnemonic_allallall()
        nodes = [self.client.get_public_node(self.client.expand_path("999'/1'/%d'" % index)) for index in range(1, 4)]
        multisig1 = proto.MultisigRedeemScriptType(
            pubkeys=list(map(lambda n: proto.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2, 0]), nodes)),
            signatures=[b'', b'', b''],
            m=2,
        )
        multisig2 = proto.MultisigRedeemScriptType(
            pubkeys=list(map(lambda n: proto.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2, 1]), nodes)),
            signatures=[b'', b'', b''],
            m=2,
        )
        for i in [1, 2, 3]:
            self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("999'/1'/%d'/2/1" % i),
                                                     False, multisig2, script_type=proto.InputScriptType.SPENDWITNESS),
                             'tb1qch62pf820spe9mlq49ns5uexfnl6jzcezp7d328fw58lj0rhlhasge9hzy')
            self.assertEqual(self.client.get_address("Testnet", self.client.expand_path("999'/1'/%d'/2/0" % i),
                                                     False, multisig1, script_type=proto.InputScriptType.SPENDWITNESS),
                             'tb1qr6xa5v60zyt3ry9nmfew2fk5g9y3gerkjeu6xxdz7qga5kknz2ssld9z2z')
