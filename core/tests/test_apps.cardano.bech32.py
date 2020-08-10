from common import *

from apps.cardano.helpers import bech32

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoBech32(unittest.TestCase):
    def test_decode_and_encode(self):
        expected_bechs = [
            # human readable part, bech32
            ("a", "a12uel5l"),
            ("an83characterlonghumanreadablepartthatcontainsthenumber1andtheexcludedcharactersbio",
                "an83characterlonghumanreadablepartthatcontainsthenumber1andtheexcludedcharactersbio1tt5tgs"),
            ("abcdef", "abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw"),
            ("1", "11qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqc8247j"),
            ("split", "split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w"),
            ("addr", "addr1qzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92sj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfmsw8ezsk"),
            ("addr_test", "addr_test1qzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92sj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfmsu8d9w5")
        ]

        for expected_human_readable_part, expected_bech in expected_bechs:
            decoded = bech32.decode(expected_human_readable_part, expected_bech)
            actual_bech = bech32.encode(expected_human_readable_part, decoded)

            self.assertEqual(actual_bech, expected_bech)


if __name__ == "__main__":
    unittest.main()
