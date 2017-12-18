from common import *
from apps.ethereum import tokens


class TestEthereumTokens(unittest.TestCase):

    def test_token_by_chain_address(self):

        token = tokens.token_by_chain_address(1, b'\x7d\xd7\xf5\x6d\x69\x7c\xc0\xf2\xb5\x2b\xd5\x5c\x05\x7f\x37\x8f\x1f\xe6\xab\x4b')
        self.assertEqual(token['symbol'], '$TEAK')
        token = tokens.token_by_chain_address(1, b'\x59\x41\x6a\x25\x62\x8a\x76\xb4\x73\x0e\xc5\x14\x86\x11\x4c\x32\xe0\xb5\x82\xa1')
        self.assertEqual(token['symbol'], 'PLASMA')
        self.assertEqual(token['decimal'], 6)
        token = tokens.token_by_chain_address(3, b'\x95\xd7\x32\x1e\xdc\xe5\x19\x41\x9b\xa1\xdb\xc6\x0a\x89\xba\xfb\xf5\x5e\xac\x0d')
        self.assertEqual(token['symbol'], 'PLASMA')
        self.assertEqual(token['decimal'], 6)
        token = tokens.token_by_chain_address(8, b'\x4b\x48\x99\xa1\x0f\x3e\x50\x7d\xb2\x07\xb0\xee\x24\x26\x02\x9e\xfa\x16\x8a\x67')
        self.assertEqual(token['symbol'], 'QWARK')

        # invalid adress, invalid chain
        token = tokens.token_by_chain_address(999, b'\x00\xFF')
        self.assertEqual(token, None)


if __name__ == '__main__':
    unittest.main()
