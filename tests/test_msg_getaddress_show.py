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

    def test_show_multisig(self):
        self.setup_mnemonic_nopin_nopassphrase()

        multisig = proto_types.MultisigRedeemScriptType(
                            pubkeys=[binascii.unhexlify('0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6'),
                                     binascii.unhexlify('038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3'),
                                     binascii.unhexlify('03477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a7902')],
                            signatures=['', '', ''],
                            m=2,
                            )

        self.assertEqual(self.client.get_address('Bitcoin', [1], show_display=True, multisig=multisig), '3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz')
        self.assertEqual(self.client.get_address('Bitcoin', [2], show_display=True, multisig=multisig), '3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz')
        self.assertEqual(self.client.get_address('Bitcoin', [3], show_display=True, multisig=multisig), '3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz')

if __name__ == '__main__':
    unittest.main()
