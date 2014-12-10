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

        multisig = proto_types.MultisigRedeemScriptType(
                            pubkeys=[binascii.unhexlify('0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6'),
                                     binascii.unhexlify('038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3'),
                                     binascii.unhexlify('03477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a7902')],
                            signatures=['', '', ''],
                            m=2,
                            )

        for i in [1, 2, 3]:
            self.assertEqual(self.client.get_address('Bitcoin', [i], show_display=True, multisig=multisig), '3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz')

    def test_show_multisig_15(self):
        self.setup_mnemonic_nopin_nopassphrase()

        pubs = ['023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43d',
                '0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6',
                '038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3',
                '03477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a7902',
                '03fe91eca10602d7dad4c9dab2b2a0858f71e25a219a6940749ce7a48118480dae',
                '0234716c01c2dd03fa7ee302705e2b8fbd1311895d94b1dca15e62eedea9b0968f',
                '0341fb2ead334952cf60f4481ba435c4693d0be649be01d2cfe9b02018e483e7bd',
                '02dad8b2bce360a705c16e74a50a36459b4f8f4b78f9cd67def29d54ef6f7c7cf9',
                '0222dbe3f5f197a34a1d50e2cbe2a1085cac2d605c9e176f9a240e0fd0c669330d',
                '03fb41afab56c9cdb013fda63d777d4938ddc3cb2ad939712da688e3ed333f9598',
                '02435f177646bdc717cb3211bf46656ca7e8d642726144778c9ce816b8b8c36ccf',
                '02158d8e20095364031d923c7e9f7f08a14b1be1ddee21fe1a5431168e31345e55',
                '026259794892428ca0818c8fb61d2d459ddfe20e57f50803c7295e6f4e2f558665',
                '02815f910a8689151db627e6e262e0a2075ad5ec2993a6bc1b876a9d420923d681',
                '0318f54647f645ff01bd49fedc0219343a6a22d3ea3180a3c3d3097e4b888a8db4']

        multisig = proto_types.MultisigRedeemScriptType(
                        pubkeys=[binascii.unhexlify(p) for p in pubs],
                        signatures=[''] * 15,
                        m=15,
                        )

        for i in range(15):
            self.assertEqual(self.client.get_address('Bitcoin', [i], show_display=True, multisig=multisig), '3QaKF8zobqcqY8aS6nxCD5ZYdiRfL3RCmU')

if __name__ == '__main__':
    unittest.main()
