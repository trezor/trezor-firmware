import unittest
import common
import binascii

from trezorlib.client import CallException

class TestEcies(common.TrezorTest):

    def test_ecies(self):
        self.setup_mnemonic_nopin_nopassphrase()

        pubkey = self.client.get_public_node([1]).node.public_key

        # encrypt without signature
        enc = self.client.encrypt_message(pubkey, 'testing message!', display_only=False, coin_name='Bitcoin', n=[])
        dec = self.client.decrypt_message([1], enc)
        self.assertEqual(dec, 'testing message!')

        # encrypt with signature
        enc = self.client.encrypt_message(pubkey, 'testing message!', display_only=False, coin_name='Bitcoin', n=[2])
        dec = self.client.decrypt_message([1], enc)
        self.assertEqual(dec, 'testing message!')

        # encrypt without signature, show only on display
        enc = self.client.encrypt_message(pubkey, 'testing message!', display_only=True, coin_name='Bitcoin', n=[])
        dec = self.client.decrypt_message([1], enc)
        self.assertEqual(dec, '')

        # encrypt with signature, show only on display
        enc = self.client.encrypt_message(pubkey, 'testing message!', display_only=True, coin_name='Bitcoin', n=[2])
        dec = self.client.decrypt_message([1], enc)
        self.assertEqual(dec, '')


if __name__ == '__main__':
    unittest.main()
