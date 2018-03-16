from common import *

from apps.nem.sign_tx import *
from trezor.crypto import hashlib


class TestNemTransactionTransfer(unittest.TestCase):

    def test_create_transfer(self):

        # http://bob.nem.ninja:8765/#/transfer/0acbf8df91e6a65dc56c56c43d65f31ff2a6a48d06fc66e78c7f3436faf3e74f
        t = nem_transaction_create_transfer(NEM_NETWORK_TESTNET,
                                            0,
                                            unhexlify('e59ef184a612d4c3c4d89b5950eb57262c69862b2f96e59c5043bf41765c482f'),
                                            0,
                                            0,
                                            'TBGIMRE4SBFRUJXMH7DVF2IBY36L2EDWZ37GVSC4',
                                            50000000000000)

        self.assertEqual(t, unhexlify('01010000010000980000000020000000e59ef184a612d4c3c4d89b5950eb57262c69862b2f96e59c5043bf41765c482f00000000000000000000000028000000544247494d52453453424652554a584d48374456463249425933364c324544575a3337475653433400203d88792d000000000000'))
        self.assertEqual(hashlib.sha3_256(t).digest(True), unhexlify('0acbf8df91e6a65dc56c56c43d65f31ff2a6a48d06fc66e78c7f3436faf3e74f'))

    def test_create_transfer_with_payload(self):

        # http://chain.nem.ninja/#/transfer/e90e98614c7598fbfa4db5411db1b331d157c2f86b558fb7c943d013ed9f71cb
        t = nem_transaction_create_transfer(NEM_NETWORK_MAINNET,
                                            0,
                                            unhexlify(
                                                '8d07f90fb4bbe7715fa327c926770166a11be2e494a970605f2e12557f66c9b9'),
                                            0,
                                            0,
                                            'NBT3WHA2YXG2IR4PWKFFMO772JWOITTD2V4PECSB',
                                            5175000000000,
                                            bytearray('Good luck!'))

        self.assertEqual(hashlib.sha3_256(t).digest(True), unhexlify('e90e98614c7598fbfa4db5411db1b331d157c2f86b558fb7c943d013ed9f71cb'))

    def test_create_transfer_with_mosaic(self):

        # http://bob.nem.ninja:8765/#/transfer/3409d9ece28d6296d6d5e220a7e3cb8641a3fb235ffcbd20c95da64f003ace6c
        t = nem_transaction_create_transfer(NEM_NETWORK_TESTNET,
                                            14072100,
                                            unhexlify('994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd324'),
                                            194000000,
                                            14075700,
                                            'TBLOODPLWOWMZ2TARX4RFPOSOWLULHXMROBN2WXI',
                                            3000000,
                                            bytearray('sending you 3 pairs of paddles\n'),
                                            False,
                                            2)
        self.assertEqual(t, unhexlify('010100000200009824b9d60020000000994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd3248034900b0000000034c7d6002800000054424c4f4f44504c574f574d5a3254415258345246504f534f574c554c48584d524f424e32575849c0c62d000000000027000000010000001f00000073656e64696e6720796f752033207061697273206f6620706164646c65730a02000000'))

        nem_transaction_write_mosaic(t, 'gimre.games.pong', 'paddles', 2)
        nem_transaction_write_mosaic(t, 'nem', 'xem', 44000000)

        self.assertEqual(hashlib.sha3_256(t).digest(True), unhexlify('3409d9ece28d6296d6d5e220a7e3cb8641a3fb235ffcbd20c95da64f003ace6c'))

        # http://chain.nem.ninja/#/transfer/882dca18dcbe075e15e0ec5a1d7e6ccd69cc0f1309ffd3fde227bfbc107b3f6e
        t = nem_transaction_create_transfer(NEM_NETWORK_MAINNET,
                                            26730750,
                                            unhexlify(
                                                'f85ab43dad059b9d2331ddacc384ad925d3467f03207182e01296bacfb242d01'),
                                            179500000,
                                            26734350,
                                            'NBE223WPKEBHQPCYUC4U4CDUQCRRFMPZLOQLB5OP',
                                            1000000,
                                            bytearray('enjoy! :)'),
                                            False,
                                            1)
        nem_transaction_write_mosaic(t, 'imre.g', 'tokens', 1)

        self.assertEqual(hashlib.sha3_256(t).digest(True), unhexlify('882dca18dcbe075e15e0ec5a1d7e6ccd69cc0f1309ffd3fde227bfbc107b3f6e'))

    def test_create_transfer_with_encrypted_payload(self):

        # http://chain.nem.ninja/#/transfer/40e89160e6f83d37f7c82defc0afe2c1605ae8c919134570a51dd27ea1bb516c

        t = nem_transaction_create_transfer(NEM_NETWORK_MAINNET,
                                            77229,
                                            unhexlify('f85ab43dad059b9d2331ddacc384ad925d3467f03207182e01296bacfb242d01'),
                                            30000000,
                                            80829,
                                            'NALICEPFLZQRZGPRIJTMJOCPWDNECXTNNG7QLSG3',
                                            30000000,
                                            unhexlify('4d9dcf9186967d30be93d6d5404ded22812dbbae7c3f0de501bcd7228cba45bded13000eec7b4c6215fc4d3588168c9218167cec98e6977359153a4132e050f594548e61e0dc61c153f0f53c5e65c595239c9eb7c4e7d48e0f4bb8b1dd2f5ddc'),
                                            True)

        self.assertEqual(hashlib.sha3_256(t).digest(True), unhexlify('40e89160e6f83d37f7c82defc0afe2c1605ae8c919134570a51dd27ea1bb516c'))


if __name__ == '__main__':
    unittest.main()
