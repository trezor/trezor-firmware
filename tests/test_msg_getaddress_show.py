import unittest
import common
import trezorlib.ckd_public as bip32

class TestMsgGetaddress(common.TrezorTest):

    def test_show(self):
        self.setup_mnemonic_nopin_nopassphrase()
        self.assertEqual(self.client.get_address('Bitcoin', [1], show_display=True), '1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb')
        self.assertEqual(self.client.get_address('Bitcoin', [2], show_display=True), '15AeAhtNJNKyowK8qPHwgpXkhsokzLtUpG')
        self.assertEqual(self.client.get_address('Bitcoin', [3], show_display=True), '1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5')

if __name__ == '__main__':
    unittest.main()
