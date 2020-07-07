from ubinascii import unhexlify

from common import *

from apps.cardano.helpers.bech32 import bech32_encode


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoBech32(unittest.TestCase):
    def test_decode_and_encode(self):
        expected_bechs = [
            # human readable part, data, expected bech32
            ("a", "", "a12uel5l"),
            (
                "an83characterlonghumanreadablepartthatcontainsthenumber1andtheexcludedcharactersbio",
                "",
                "an83characterlonghumanreadablepartthatcontainsthenumber1andtheexcludedcharactersbio1tt5tgs",
            ),
            (
                "abcdef",
                "00443214c74254b635cf84653a56d7c675be77df",
                "abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw",
            ),
            (
                "1",
                "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
                "11qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqc8247j",
            ),
            (
                "split",
                "c5f38b70305f519bf66d85fb6cf03058f3dde463ecd7918f2dc743918f2d",
                "split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w",
            ),
            (
                "addr",
                "0080f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277",
                "addr1qzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92sj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfmsw8ezsk",
            ),
        ]

        for human_readable_part, data, expected_bech in expected_bechs:
            actual_bech = bech32_encode(human_readable_part, unhexlify(data))
            self.assertEqual(actual_bech, expected_bech)


if __name__ == "__main__":
    unittest.main()
