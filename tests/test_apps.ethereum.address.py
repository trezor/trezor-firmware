from common import *
from apps.common.paths import HARDENED
from apps.ethereum.address import ethereum_address_hex, validate_full_path
from apps.ethereum.networks import NetworkInfo


class TestEthereumGetAddress(unittest.TestCase):

    def test_ethereum_address_hex_eip55(self):
        # https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
        eip55 = [
            '0x52908400098527886E0F7030069857D2E4169EE7',
            '0x8617E340B3D01FA5F11F306F4090FD50E238070D',
            '0xde709f2102306220921060314715629080e2fb77',
            '0x27b1fdb04752bbc536007a920d24acb045561c26',
            '0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed',
            '0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359',
            '0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB',
            '0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb',
        ]
        for s in eip55:
            s = s[2:]
            b = bytes([int(s[i:i + 2], 16) for i in range(0, len(s), 2)])
            h = ethereum_address_hex(b)
            self.assertEqual(h, '0x' + s)

    def test_ethereum_address_hex_rskip60(self):
        # https://github.com/rsksmart/RSKIPs/blob/master/IPs/RSKIP60.md
        rskip60_chain_30 = [
            '0x5aaEB6053f3e94c9b9a09f33669435E7ef1bEAeD',
            '0xFb6916095cA1Df60bb79ce92cE3EA74c37c5d359',
            '0xDBF03B407c01E7CD3cBea99509D93F8Dddc8C6FB',
            '0xD1220A0Cf47c7B9BE7a2e6ba89F429762E7B9adB'
        ]
        rskip60_chain_31 = [
            '0x5aAeb6053F3e94c9b9A09F33669435E7EF1BEaEd',
            '0xFb6916095CA1dF60bb79CE92ce3Ea74C37c5D359',
            '0xdbF03B407C01E7cd3cbEa99509D93f8dDDc8C6fB',
            '0xd1220a0CF47c7B9Be7A2E6Ba89f429762E7b9adB'
        ]
        n = NetworkInfo(chain_id=30, slip44=1, shortcut='T', name='T', rskip60=True)
        for s in rskip60_chain_30:
            s = s[2:]
            b = bytes([int(s[i:i + 2], 16) for i in range(0, len(s), 2)])
            h = ethereum_address_hex(b, n)
            self.assertEqual(h, '0x' + s)
        n.chain_id = 31
        for s in rskip60_chain_31:
            s = s[2:]
            b = bytes([int(s[i:i + 2], 16) for i in range(0, len(s), 2)])
            h = ethereum_address_hex(b, n)
            self.assertEqual(h, '0x' + s)

    def test_paths(self):
        # 44'/60'/0'/0/i is correct
        incorrect_paths = [
            [44 | HARDENED],
            [44 | HARDENED, 60 | HARDENED],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 0, 0],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 1, 0],
            [44 | HARDENED, 60 | HARDENED, 1 | HARDENED, 0, 0],
            [44 | HARDENED, 160 | HARDENED, 0 | HARDENED, 0, 0],
        ]
        correct_paths = [
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 9],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 9999],
        ]

        for path in incorrect_paths:
            self.assertFalse(validate_full_path(path))

        for path in correct_paths:
            self.assertTrue(validate_full_path(path))


if __name__ == '__main__':
    unittest.main()
