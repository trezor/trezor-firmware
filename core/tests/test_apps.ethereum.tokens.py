from common import *

if not utils.BITCOIN_ONLY:
    from apps.ethereum import tokens


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumTokens(unittest.TestCase):

    def test_token_by_chain_address(self):

        token = tokens.token_by_chain_address(1, b'\x7d\xd7\xf5\x6d\x69\x7c\xc0\xf2\xb5\x2b\xd5\x5c\x05\x7f\x37\x8f\x1f\xe6\xab\x4b')
        self.assertEqual(token[2], '$TEAK')

        token = tokens.token_by_chain_address(1, b'\x59\x41\x6a\x25\x62\x8a\x76\xb4\x73\x0e\xc5\x14\x86\x11\x4c\x32\xe0\xb5\x82\xa1')
        self.assertEqual(token[2], 'PLASMA')
        self.assertEqual(token[3], 6)

        token = tokens.token_by_chain_address(4, b'\x0a\x05\x7a\x87\xce\x9c\x56\xd7\xe3\x36\xb4\x17\xc7\x9c\xf3\x0e\x8d\x27\x86\x0b')
        self.assertEqual(token[2], 'WALL')
        self.assertEqual(token[3], 15)

        token = tokens.token_by_chain_address(8, b'\x4b\x48\x99\xa1\x0f\x3e\x50\x7d\xb2\x07\xb0\xee\x24\x26\x02\x9e\xfa\x16\x8a\x67')
        self.assertEqual(token[2], 'QWARK')

        # invalid adress, invalid chain
        token = tokens.token_by_chain_address(999, b'\x00\xFF')
        self.assertIs(token, tokens.UNKNOWN_TOKEN)


if __name__ == '__main__':
    unittest.main()
