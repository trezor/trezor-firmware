from __future__ import print_function

import unittest
import common
import binascii
import base64

from trezorlib.client import CallException

# as described here: http://memwallet.info/btcmssgs.html

def test_ecies_backforth(cls, test_string):
    cls.setup_mnemonic_nopin_nopassphrase()

    pubkey = binascii.unhexlify('0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6')

    # encrypt without signature
    enc = cls.client.encrypt_message(pubkey, test_string, display_only=False, coin_name='Bitcoin', n=[])
    print('base64:', base64.b64encode(enc.nonce + enc.message + enc.hmac))
    dec = cls.client.decrypt_message([1], enc.nonce, enc.message, enc.hmac)
    cls.assertEqual(dec.message, test_string)
    cls.assertEqual(dec.address, '')

    # encrypt with signature
    enc = cls.client.encrypt_message(pubkey, test_string, display_only=False, coin_name='Bitcoin', n=[5])
    print('base64:', base64.b64encode(enc.nonce + enc.message + enc.hmac))
    dec = cls.client.decrypt_message([1], enc.nonce, enc.message, enc.hmac)
    cls.assertEqual(dec.message, test_string)
    cls.assertEqual(dec.address, '1Csf6LVPkv24FBs6bpj4ELPszE6mGf6jeV')

    # encrypt without signature, show only on display
    enc = cls.client.encrypt_message(pubkey, test_string, display_only=True, coin_name='Bitcoin', n=[])
    dec = cls.client.decrypt_message([1], enc.nonce, enc.message, enc.hmac)
    cls.assertEqual(dec.message, '')
    cls.assertEqual(dec.address, '')

    # encrypt with signature, show only on display
    enc = cls.client.encrypt_message(pubkey, test_string, display_only=True, coin_name='Bitcoin', n=[5])
    dec = cls.client.decrypt_message([1], enc.nonce, enc.message, enc.hmac)
    cls.assertEqual(dec.message, '')
    cls.assertEqual(dec.address, '')

class TestEcies(common.TrezorTest):

# index:   m/1
# address: 1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb
# pubkey:  0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6
# privkey: L5X3rf5hJfRt9ZjQzFopvSBGkpnSotn4jKGLL6ECJxcuT2JgGh65

# index:   m/5
# address: 1Csf6LVPkv24FBs6bpj4ELPszE6mGf6jeV
# pubkey:  0234716c01c2dd03fa7ee302705e2b8fbd1311895d94b1dca15e62eedea9b0968f
# privkey: L4uKPRgaZqL9iGmge3UBSLGTQC7gDFrLRhC1vM4LmGyrzNUBb1Zs

    def test_ecies_backforth_short(self):
        test_ecies_backforth(self, 'testing message!')

    def test_ecies_backforth_long(self):
        test_ecies_backforth(self, 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin elementum libero in tortor condimentum malesuada. Quisque gravida semper sapien, ut ultrices dolor pharetra nec. Nulla hendrerit metus imperdiet, feugiat sapien eu, fermentum mauris. Suspendisse nec bibendum urna. Vivamus augue libero, mollis vel augue at, venenatis vestibulum nunc. Curabitur condimentum quam non nibh volutpat, at congue libero rutrum. Morbi at sollicitudin lectus. Donec commodo rutrum sollicitudin. Vivamus condimentum massa id ligula iaculis, et aliquet orci condimentum. Nullam non ex sit amet nisi porta suscipit.')

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

    def test_ecies_crosscheck_long(self):
        self.setup_mnemonic_nopin_nopassphrase()

        lipsum = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin elementum libero in tortor condimentum malesuada. Quisque gravida semper sapien, ut ultrices dolor pharetra nec. Nulla hendrerit metus imperdiet, feugiat sapien eu, fermentum mauris. Suspendisse nec bibendum urna. Vivamus augue libero, mollis vel augue at, venenatis vestibulum nunc. Curabitur condimentum quam non nibh volutpat, at congue libero rutrum. Morbi at sollicitudin lectus. Donec commodo rutrum sollicitudin. Vivamus condimentum massa id ligula iaculis, et aliquet orci condimentum. Nullam non ex sit amet nisi porta suscipit.'

        # decrypt message without signature
        payload = 'AhnOXSv+7mI3Tvw0ekCxvEoMvophrWOGAwLT2IpyxaCd+zgftijj2uQoGtSktFwch8oABstTqwBjokH4AllH7PaL/8dWwOELwEVIXlbktf8nktUITBkJ0Abih8Imq451Bwrt8ZMt0tzoDBWeRLtZGHPduHnykGjq1O3A8Qjd4k8W+PkPBum+rNKlPOUqoNpSvOcPD9L6APkMByPKMmTq5K9nSeLKyXjOtWcx4BLRqRe9qgvG+SWFHsJ/90O76XZIB6GXDqGnCNR5rV/8Ho4bfagRL/tQPbeQ4iYWAyqdRlKuwnUrrZSJCdrsQJt1Ye5LcltE0YhJBKRmxob2/P+ziyceZk6cU3hS9k4B1GKlEeGxipvMswfbrEIy/5NYiGXEDwC3dHwM3g1Opz5oXbEKZ3NG/eEh5UxJFjfyx1qumQeSaIo5XFOf81A4dhH1vAT8MMEQN7bXXwCb1fxDC9wblCP9iVR1aey5FUFMNE7wfXYdrMxwzxrgJfSa8/vQgMmZI205OCBxAsmBYOTIy6kqcRn7+Ad6WEYvp2DRwcGN//9XFJi2DuJzA0ymeoSxnZg4GDytpvVFVyQvIDkPHrmVfaZot02XCCqTq/ZDgZLnnutWfP9dB1ckSpzXOM/pEgMBj6DcC1HbgHZaKhoNjsk8ITTYMnP5kFBoZdtPbNJB5rZOYtLHHDxfvk2d3USTxtbPiIE9w6JbBll18lKFMN8gvQuKcHyKwVNQGOVuBGtXv4hCBFF/VNRJ5GE8BX1ajHwldFiuTII9dcdSrZhL+Ds8Ui0siZ5Ai+KHjKZi8FciNQ+8q3tXUOiN1hONCN6iy5XjFd2I7NAqg+o4TnkGKSPMQSE3z2vY'
        payload = base64.b64decode(payload)
        nonce, msg, hmac = payload[:33], payload[33:-8], payload[-8:]
        dec = self.client.decrypt_message([1], nonce, msg, hmac)
        self.assertEqual(dec.message, lipsum)
        self.assertEqual(dec.address, '')

        # decrypt message without signature (same message, different nonce)
        payload = 'A2bVIKzpPVYJlPP6WMiwhpabJfJAHH927StDsUyRL2h3xc/aMPVN6rYA9GwcsPSDiZpPZdjCVYM4uDwFQ/kBNA1p5XlDs6IBGtGGgbR7P5wHgJaxcw1zWZ+TsWTIWVj3psy0CFg7zCfqeV2y0OzIvJc/p+ONdVb1f9TmTICPoVGJ9AVXdnfdqdIn+wLYScUklTp10ldfUCmt5iAsJJR1p+h+xa+wwUdyCxpvnxOZDxA0EFmxQskBhcDbLL2nmQkLm5RnLQgpefMCEJrdz5g9htC5y65eod2SFBV8oJrN1ryh4PdRn5+JyVcwWhQeCHTK3m6vOIwwht5lm2uCLpcEttDoxo5k3LcBPE4rlPVYCf8qja6sRKq/WYiLdwXnooX/qmmLQ7Lo2DBs4hB6VQGgPSSTH/3/rUb11bL2Ieyq73ZICeIbHCIvjFqhd/atkNvQTnCrNmFybyxdMqE/4Yrv7b//hJVkgI21AVGcSYF+Kp9pZ6XJVunDTS4XX7tjkXTFu7qbIv6q7mGgXV2/7udR9GF/lG/Us+wYsU1wmCEaUJ5Mx1yr4eLJ8cp6XPCMivEwKJ6CeHz2d/FYEeHE3YTy3VQT/+BJ5nS2+wDTD57wW9ZxUXn0cqPUhH0XveeRDOKEz1tgu6ChPrSyuu9E+pxDA2OA95NRt5j+UMdhZf6R0qgwfuDOcTs+0EuF9pQ5znPnmg4JqF6AkLlwE6txm1YTTjID8689yY4UsEc7CYJb1N3JvNxIHety5B5KWWAgnK1l9g9xnuKdGC4M7F+ajrbRqbw0qfTUvruD7GaYoqsyrdtDkEpEDXhZ0p56LALTUhL4+QVmeXvkH8cmBqdB6flZ48mlTgfy'
        payload = base64.b64decode(payload)
        nonce, msg, hmac = payload[:33], payload[33:-8], payload[-8:]
        dec = self.client.decrypt_message([1], nonce, msg, hmac)
        self.assertEqual(dec.message, lipsum)
        self.assertEqual(dec.address, '')

        # decrypt message with signature
        payload = 'ArJoHqnmLY22QiCePXk9yNQSK6g8BMGLkKkj72p35hCW1gxVajIZyptgbBp4A0LV8Fshe6MKnHO5PGw2BPQ6yTES5Q+7c8ZjC4m8JCKOOU8l7et4AcftPElxBdKimEv5B5egQmzSYds6dfB73VsWi2k9J/1RpckB2WDvXSrF1915XA4tMTMefB/DhzdrG9gkVTBqaROTgxlXWJhqdFag4aghVcXS5Ru6CQH0cLoxmZWf8mx/pK4liXyH1Gm+7fl8cd9iDkNTJEapzn/Ohh7JYxJrV/i4p0xE9L5CONL+UIL8DtGB8SgAWtd5cHdpLhMywRFxjDvho20nE3VyGREhqiv9i3ywXRox/zd6OFBkxSA3kuWNRrkDRBx4Q+2j49V5iQquuu5horUuRRYN1HVvoOYjVkfEJV70yvVg3xR2MeJouUa1aP7WF9JPo8vor252/ZU6L15mveE0JZH1HtoierC1Q5YDSFCYJ4hWJbWZEMwXvRBQL+FoZ5x6CSkrfTOYoP+uD/VnsMepI+0NgsssacU9h2PdDVy3pYnB0m04YpOftVnAARaun+nE9ti1FUFfnwSmD2vB2TfWEkFGQ3S6W6sjpX/gN+It6GViiNQO6yT9e3HO/4+JiS5yldOI7ryAlzNM598RANDdpI3kBy9IWKD5dENy/82TD/DAWoeRAz/LvvZaQBtpxZNEkRqqgbpBT7aJzjZudVMzZHPduF67eC994WB0EJHbKncXElbBVKXKMyoPruw9wwFP7VfeAAp4SLAmcs6YFkJ8lOeYO0bnPhvlrYV9XAkSpsHxBtita3WuyeoBHugHYEPzbNOdCoLRUgCS+4esrVV9aE1irlBzTmU+t8cWX5BQGsqnEuBKqPri7XWLrg57Up4ILkPFojgw/fIIkUNVCY2iqgFQCQZPM8dbE0wKK5ujd5YQwp8i/OrsXccin/TRjKXLtIkiEVg/Gl7aCRuXzGR0pfc='
        payload = base64.b64decode(payload)
        nonce, msg, hmac = payload[:33], payload[33:-8], payload[-8:]
        dec = self.client.decrypt_message([1], nonce, msg, hmac)
        self.assertEqual(dec.message, lipsum)
        self.assertEqual(dec.address, '1Csf6LVPkv24FBs6bpj4ELPszE6mGf6jeV')

        # decrypt message with signature (same message, different nonce)
        payload = 'AjFarEh66x2DZ9S3T/n8/xnYZQRwnuugxCDfIIEDPKkdfgwYPjGhtg3k/9ryj42MDgmey71ZvDhUdj+igcBKaPiKAS7p88kQxl6R6sFkL/wKwTdXPboA/n63BnHrtNNDIp12Dlgn2m0nSCLOchlh2maIBqB68qIqy21tT10ZrMpTfPd+4MI4NOzs42BQJAOLy19rMTKoCXGWIsgEERG0qCm38onYVUmj5UvtQIdDLIZ/ta4WD+FqM3Y9pJsU648qV72l/xM27BjIxVqUsw6MHLrAUNTmmd+D7dPAIjL66Gr5hEHCTcHP8oCIkeC+MK2JVcHN12F1Rx+8iwNf4nsixUcZJ/RX9JOTxJj3CdxuTH3b0lDNdFwQQddYhHd6cv4t1cZ3wOWAVh1g+gmB/igmvJD200EfhQudHp/w+9BIFFfxFwAmf4/tlidJ0knIaPjNx5kBSkklhxWdBfen5kgkGFtcQdBkguADcV/bfAxCRpqVa9lgN4ja2na0fUMZaAnVjR+sk4MWTbSObw5FBos3B7awAgRxQx6L8p3PUwGc2B9oVf1zcw3c0mlVUpaVEc7tXipVX6LAtKF9jx+EeMHvWlUic7s4vaGa7VxNuU8Of65Ba3RmxAX9zxwTKHMBAhm2efaqBIxGUSO8ncDSdp2nO6tJUkUoyNK0nasXWF2Ras22We0Ma0yGv0MQRVWeksYQn116I7ahv+lvAzaJnhiYGCM36Vg051VZEmBh23U5HdqrLRT7w8u1DJZyCxo0KmiZ5c3sOiJPxcC/8hpnQ0Zc7ipEdi97hZG2X2HOtmEIFivF2yI26rieEDyebbg95CnhUFx1LEuiEApU8fVAuYoyEQGVVwQPEQlBrqkF4oE/cItesBqxIdoZlsvoYBvxa1huT6jsc/Uci1WRpwKmPxeHUkxZrwLG8+kUNGFn13s8HrPTncaCQU3fnu3KOKkfLdnpVnF3JfYlrruMWV4='
        payload = base64.b64decode(payload)
        nonce, msg, hmac = payload[:33], payload[33:-8], payload[-8:]
        dec = self.client.decrypt_message([1], nonce, msg, hmac)
        self.assertEqual(dec.message, lipsum)
        self.assertEqual(dec.address, '1Csf6LVPkv24FBs6bpj4ELPszE6mGf6jeV')

if __name__ == '__main__':
    unittest.main()
