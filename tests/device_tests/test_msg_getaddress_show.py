import unittest
import common
import trezorlib.ckd_public as bip32
import trezorlib.types_pb2 as proto_types
import binascii

class TestMsgGetaddress(common.TrezorTest):

    def test_show(self):
        self.setup_mnemonic_nopin_nopassphrase()
        self.assertEqual(self.client.get_address('Bitcoin', [1], show_display=True), '1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb')
        self.assertEqual(self.client.get_address('Bitcoin', [2], show_display=True), '15AeAhtNJNKyowK8qPHwgpXkhsokzLtUpG')
        self.assertEqual(self.client.get_address('Bitcoin', [3], show_display=True), '1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5')

    def test_show_multisig_3(self):
        self.setup_mnemonic_nopin_nopassphrase()

        node = bip32.deserialize('xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy')
        multisig = proto_types.MultisigRedeemScriptType(
                            pubkeys=[proto_types.HDNodePathType(node=node, address_n=[1]),
                                     proto_types.HDNodePathType(node=node, address_n=[2]),
                                     proto_types.HDNodePathType(node=node, address_n=[3])],
                            signatures=[b'', b'', b''],
                            m=2,
                            )

        for i in [1, 2, 3]:
            self.assertEqual(self.client.get_address('Bitcoin', [i], show_display=True, multisig=multisig), '3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz')

    def test_show_multisig_15(self):
        self.setup_mnemonic_nopin_nopassphrase()

        node = bip32.deserialize('xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy')

        pubs = []
        for x in range(15):
            pubs.append(proto_types.HDNodePathType(node=node, address_n=[x]))

        multisig = proto_types.MultisigRedeemScriptType(
                        pubkeys=pubs,
                        signatures=[b''] * 15,
                        m=15,
                        )

        for i in range(15):
            self.assertEqual(self.client.get_address('Bitcoin', [i], show_display=True, multisig=multisig), '3QaKF8zobqcqY8aS6nxCD5ZYdiRfL3RCmU')

if __name__ == '__main__':
    unittest.main()
