import unittest
import common
import binascii
import base64

from trezorlib.client import CallException

# as described here: http://memwallet.info/btcmssgs.html

class TestEcies(common.TrezorTest):

# index:   m/1
# address: 1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb
# pubkey:  0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6
# privkey: L5X3rf5hJfRt9ZjQzFopvSBGkpnSotn4jKGLL6ECJxcuT2JgGh65

# index:   m/5
# address: 1Csf6LVPkv24FBs6bpj4ELPszE6mGf6jeV
# pubkey:  0234716c01c2dd03fa7ee302705e2b8fbd1311895d94b1dca15e62eedea9b0968f
# privkey: L4uKPRgaZqL9iGmge3UBSLGTQC7gDFrLRhC1vM4LmGyrzNUBb1Zs

    def test_ecies(self):
        self.setup_mnemonic_nopin_nopassphrase()

        pubkey = binascii.unhexlify('0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6')

        # encrypt without signature
        enc = self.client.encrypt_message(pubkey, 'testing message!', display_only=False, coin_name='Bitcoin', n=[])
        print 'base64:', base64.b64encode(enc.nonce + enc.message + enc.hmac)
        dec = self.client.decrypt_message([1], enc.nonce, enc.message, enc.hmac)
        self.assertEqual(dec.message, 'testing message!')
        self.assertEqual(dec.address, '')

        # encrypt with signature
        enc = self.client.encrypt_message(pubkey, 'testing message!', display_only=False, coin_name='Bitcoin', n=[5])
        print 'base64:', base64.b64encode(enc.nonce + enc.message + enc.hmac)
        dec = self.client.decrypt_message([1], enc.nonce, enc.message, enc.hmac)
        self.assertEqual(dec.message, 'testing message!')
        self.assertEqual(dec.address, '1Csf6LVPkv24FBs6bpj4ELPszE6mGf6jeV')

        # encrypt without signature, show only on display
        enc = self.client.encrypt_message(pubkey, 'testing message!', display_only=True, coin_name='Bitcoin', n=[])
        dec = self.client.decrypt_message([1], enc.nonce, enc.message, enc.hmac)
        self.assertEqual(dec.message, '')
        self.assertEqual(dec.address, '')

        # encrypt with signature, show only on display
        enc = self.client.encrypt_message(pubkey, 'testing message!', display_only=True, coin_name='Bitcoin', n=[5])
        dec = self.client.decrypt_message([1], enc.nonce, enc.message, enc.hmac)
        self.assertEqual(dec.message, '')
        self.assertEqual(dec.address, '')

    def test_ecies_crosscheck(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # decrypt message without signature
        payload = 'AhA1yCZStrmtuGSgliJ7K02eD8xWRoyRU1ryPu9kBloODFv9hATpqukL0YSzISfrQGygYVai5OirxU0='
        payload = base64.b64decode(payload)
        nonce, msg, hmac = payload[:33], payload[33:-8], payload[-8:]
        dec = self.client.decrypt_message([1], nonce, msg, hmac)
        self.assertEqual(dec.message, 'testing message!')
        self.assertEqual(dec.address, '')

        # decrypt message without signature (same message, different nonce)
        payload = 'A9ragu6UTXisBWw6bTCcM/SeR7fmlQp6Qzg9mpJ5qKBv9BIgWX/v/u+OhdlKLZTx6C0Xooz5aIvWrqw='
        payload = base64.b64decode(payload)
        nonce, msg, hmac = payload[:33], payload[33:-8], payload[-8:]
        dec = self.client.decrypt_message([1], nonce, msg, hmac)
        self.assertEqual(dec.message, 'testing message!')
        self.assertEqual(dec.address, '')

        # decrypt message with signature
        payload = 'A90Awe+vrQvmzFvm0hh8Ver7jcBbqiCxV4RGU9knKf6F3vvG1N45Q3kc+N1sd4inzXZnW/5KH74CXaCPGAKr/a0n4BUhADVfS2Ic9Luwcs6/cuYHSzJKKLSPUYC6N4hu1K0q1vR/02BJ+iZ0pfvChoGDmpOOO7NaIEoyiKAnZFNsHr6Ffplg3YVGJAAG7GgfSQ=='
        payload = base64.b64decode(payload)
        nonce, msg, hmac = payload[:33], payload[33:-8], payload[-8:]
        dec = self.client.decrypt_message([1], nonce, msg, hmac)
        self.assertEqual(dec.message, 'testing message!')
        self.assertEqual(dec.address, '1Csf6LVPkv24FBs6bpj4ELPszE6mGf6jeV')

        # decrypt message with signature (same message, different nonce)
        payload = 'AyeglkkBSc3VLNrXETiNtiS+t2nIKeEVGMVfF7KlVM+plBuX3yc+2kf+Yo6L1NKoqEjSlRXn71OTOEWfB2zmtasIX9dQBfyGluEivbeUfqbwneepEzv9/i0XI3ywfSa2HSdic8B68nZ3D6Mms4qOpzk6AEPt/yI7fl8aUsN0lxT8nVBfMmmg10oydvH/86cWYA=='
        payload = base64.b64decode(payload)
        nonce, msg, hmac = payload[:33], payload[33:-8], payload[-8:]
        dec = self.client.decrypt_message([1], nonce, msg, hmac)
        self.assertEqual(dec.message, 'testing message!')
        self.assertEqual(dec.address, '1Csf6LVPkv24FBs6bpj4ELPszE6mGf6jeV')

if __name__ == '__main__':
    unittest.main()
