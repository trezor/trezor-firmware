from common import *

from trezor.crypto import beam
from trezor.messages.BeamECCPoint import BeamECCPoint

from apps.beam.helpers import (
    bin_to_str,
)

class TestBeamGenerateKey(unittest.TestCase):
    mnemonic = "abc abc abc abc abc abc abc abc abc abc abc abc"
    seed = beam.from_mnemonic_beam(mnemonic)

    def test_generate_key(self):
        test_datasets = (
            (
                0, 0, 0, 0,
                "6a11f21ad47da59863e7f7d2fc952677f8342f4a2f89eb4c281f3b832dca8afc", 0,
            ),
            (
                0, 0, 0, 1,
                "ecf1258affe8c0b11c5c954e997e7fe1f9d2988db19b491b39537fea9506a47e", 0,
            ),
            (
                0, 0, 1, 0,
                "53cb716a7cb3777f4ba1a55a241eee45ddb184601155887f90d465975aa3a714", 0,
            ),
            (
                0, 0, 1, 1,
                "25c93e889ffe9548f611a27d30eae3f8c7d6a57cfeb9d3ca282fdaa3c37464c0", 0,
            ),
            (
                0, 1, 0, 0,
                "e16fabeadd8bcb2135f50f87eb076c4c43662ed9c55f846e49772e6945446d74", 0,
            ),
            (
                0, 2, 0, 0,
                "a836e2f146905f6b2763cbf013a3bd3f586944fa415a31897b040b2eb53cbd71", 1,
            ),
            (
                0, 2, 3, 0,
                "e94c437859c3ae14a6c46a3c71d1f423c6cc1622a28a09ba404c12459fe20632", 1,
            ),
            (
                1, 0, 0, 0,
                "e37f48af79d74ad8618fc060cff066c6a814aefd38687133b168a4474640072f", 1,
            ),
            (
                1, 2, 3, 4,
                "ad875e9a938661b7928cbbefe917b67a994b76fcf8c9af4e7d31c30b9965dfd3", 1,
            ),
            (
                4, 3, 2, 1,
                "23e0c0e7f683cc720061da846753702ab0f07effbeb27d91e12fc806c8e89b37", 1,
            ),
            (
                0, 0, 1, 5,
                "28ba82826c91026cf6464d288aa48a83c16c1147674509645fdead09a8ba5a21", 0,
            ),
        )

        is_coin_key = True

        for test_params in test_datasets:
            idx = test_params[0]
            type = test_params[1]
            sub_idx = test_params[2]
            value = test_params[3]
            expected_key_image_x = test_params[4]
            expected_key_image_y = test_params[5]

            key_image_x = bytearray(32)
            key_image_y = bytearray(1)
            beam.generate_key(idx, type, sub_idx, value,
                            is_coin_key, self.seed,
                            key_image_x, key_image_y)

            self.assertEqual(expected_key_image_x, bin_to_str(key_image_x))
            self.assertEqual(expected_key_image_y, key_image_y[0])


if __name__ == '__main__':
    unittest.main()

