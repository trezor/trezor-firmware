from common import *

from trezor.crypto import beam

from apps.beam.helpers import (
    bin_to_str,
    get_beam_kdf,
    get_beam_sk,
)
from apps.beam.sign_message import message_digest

class TestBeamSignMessage(unittest.TestCase):
    mnemonic = "all all all all all all all all all all all all"

    def test_message_digest(self):
        test_datasets = (
            (
                "Hello, world!",
                "1ab8816c3a4ba40c0857eb039445303126f103db4c3b848806a77ce61e860ab2",
            ),
            (
                "abc",
                "6ed020d642e731d9d79da2dfa5b57c9c1ed148d00c9e23591459e563b10f23f2",
            ),
            (
                "ABC",
                "6af3829a33662dd58ae51ee4bd23d1a718bb319f9b6cbd2048bc6ba27f18ba7e",
            ),
            (
                "beam",
                "e21df0f5518a2ba06a122b54b09f33960e158bbd5269cd9477531a5301e18d14",
            ),
            (
                "BEAM",
                "fe7634347119cb94bd374db7575cfd0ed7057e0615c99ae7e3bbd97b8a95c363",
            ),
            (
                "beam beam beam",
                "e914080bb4e2c1591036c2181d5f0cb13dd6ceedc777b3e5f754e5fb8075b8a7",
            ),
            (
                "beam,beam,beam",
                "0ddba34f96272d6d1690abdb0f1ee29cd18e61a33c6db592c54707b24955168d",
            ),
            (
                "beam trezor integration",
                "1c956a830ce1602a47a843dbb664d28a164bbf9935de1d4002ef7d81449247ea",
            ),
        )
        for test_params in test_datasets:
            message = test_params[0]
            expected_digest = test_params[1]

            msg_digest = message_digest(message)
            self.assertEqual(bin_to_str(msg_digest), expected_digest)

    def test_sign_message(self):
        test_datasets = (
            (
                0, 0,
                "hello world",
                "94bb1f34c5e970136d4f1ff769e3332e4e5f430122ebe7e7720c754713adfab6", 0, "9f01b0eb202cd0780e35f0cf20c06cd930af8bb55db9c9c3e2146f34de1239d9",
            ),
            (
                0, 1,
                "hello world",
                "39e2014221f59c4f887be7158df22ef996ff061b7411a6d915ac91dc5a336d4b", 0, "a7b9447e39eb14e0c3167496ba53b3253918577c1c4bc0084fe8105ea6d520e5",
            ),
            (
                5, 2,
                "hello world",
                "848824bb7e3ee53ecc0d9ecdbacd8e7015d80ebaa3f50a0147d65a92e8d61894", 0, "d6d4b41ba3c858d99bb454155b9e9d531c35fc8f1535807a38e9509cb7314a75",
            ),
            (
                0, 0,
                "hello world",
                "9f315b9105225a0493d072d345b0e9a96e7c68395f004676c508259a16ade81e", 1, "3a303f731efb81d035cc98d835b66e109dd17921ec0e14091aecc72d64d7ab40",
            ),
            (
                1, 8,
                "hello from BEAM",
                "50d1f214d345a0f9cab5f7299f8e300ff1ee7c1201646bd67132203526593263", 0, "a49d590c6894f1675b5d6a43bb7845c9277d66d70c1114927a7870c6c6e95492",
            ),
            (
                4, 4,
                "abcdefg",
                "ec088ee2b66fab3b3c43337e8ad992dcc81e69a55f40b36b181a6899fc08a0f8", 0, "177a773a6278a87f03606edb5237f83bd40ea2e2954649e20930c42eb4bd7f17",
            ),
        )

        print()
        for test_params in test_datasets:
            kdf = get_beam_kdf(self.mnemonic)
            kid_idx = test_params[0]
            kid_sub_idx = test_params[1]
            message = test_params[2]
            expected_nonce_pub_x = test_params[3]
            expected_nonce_pub_y = test_params[4]
            expected_sign_k = test_params[5]


            sign_nonce_pub_x = bytearray(32)
            sign_nonce_pub_y = bytearray(1)
            sign_k = bytearray(32)

            sk = get_beam_sk(kid_idx, kid_sub_idx, kdf)
            digest = message_digest(message)
            beam.signature_sign(digest, sk, sign_nonce_pub_x, sign_nonce_pub_y, sign_k)
            #print("Idx: {}; Sub idx: {}, message: {}".format(kid_idx, kid_sub_idx, message))
            #print("Digest: {}; Sk: {}".format(bin_to_str(digest), bin_to_str(sk)))
            #print("X: {}, y: {}, k: {}".format(bin_to_str(sign_nonce_pub_x), sign_nonce_pub_y[0], bin_to_str(sign_k)))

            self.assertEqual(bin_to_str(sign_nonce_pub_x), expected_nonce_pub_x)
            self.assertEqual(sign_nonce_pub_y[0], expected_nonce_pub_y)
            self.assertEqual(bin_to_str(sign_k), expected_sign_k)


if __name__ == '__main__':
    unittest.main()

