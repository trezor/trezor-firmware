from common import *

from trezor.crypto import beam

from apps.beam.helpers import (
    bin_to_str,
    get_beam_kdf,
    get_beam_pk,
    is_valid_beam_message,
)
from apps.beam.sign_message import message_digest
from trezor.messages.BeamECCPoint import BeamECCPoint
from trezor.messages.BeamSignature import BeamSignature

class TestBeamVerifyMessage(unittest.TestCase):
    mnemonic = "all all all all all all all all all all all all"

    def test_verify_message(self):
        test_datasets = (
            (
                "hello world",
                "94bb1f34c5e970136d4f1ff769e3332e4e5f430122ebe7e7720c754713adfab6", 0, "9f01b0eb202cd0780e35f0cf20c06cd930af8bb55db9c9c3e2146f34de1239d9",
                "88b528eecb5ee5ae81e56e2105aca06997761c9cd2e566b25eaee1951be26688", 1,
                True,
            ),
            (
                "hello world",
                "39e2014221f59c4f887be7158df22ef996ff061b7411a6d915ac91dc5a336d4b", 0, "a7b9447e39eb14e0c3167496ba53b3253918577c1c4bc0084fe8105ea6d520e5",
                "53839a38c1089e28e901279266cff2da921ca82ed39c6ac0261a039157754e40", 1,
                True,
            ),
            (
                "hello world",
                "39e2014221f59c4f887be7158df22ef996ff061b7411a6d915ac91dc5a336d4b", 0, "a7b9447e39eb14e0c3167496ba53b3253918577c1c4bc0084fe8105ea6d520e5",
                "53839a38c1089e28e901279266cff2da921ca82ed39c6ac0261a039157754e40", 0,
                False,
            ),
            (
                "hello world",
                "848824bb7e3ee53ecc0d9ecdbacd8e7015d80ebaa3f50a0147d65a92e8d61894", 0, "d6d4b41ba3c858d99bb454155b9e9d531c35fc8f1535807a38e9509cb7314a75",
                "269c9a18d3a8f5acf4036a711e41cf7c5071aceac1fe95666040369a3311ac71", 0,
                True,
            ),
            (
                "hello world",
                "9f315b9105225a0493d072d345b0e9a96e7c68395f004676c508259a16ade81e", 1, "3a303f731efb81d035cc98d835b66e109dd17921ec0e14091aecc72d64d7ab40",
                "88b528eecb5ee5ae81e56e2105aca06997761c9cd2e566b25eaee1951be26688", 1,
                True,
            ),
            (
                "hello from BEAM",
                "50d1f214d345a0f9cab5f7299f8e300ff1ee7c1201646bd67132203526593263", 0, "a49d590c6894f1675b5d6a43bb7845c9277d66d70c1114927a7870c6c6e95492",
                "54158bdbeef7292b96d5ea57b2eebc3ba6c8d4a16cfeb6cd75354e8497d009b8", 1,
                True,
            ),
            (
                "abcdefg",
                "ec088ee2b66fab3b3c43337e8ad992dcc81e69a55f40b36b181a6899fc08a0f8", 0, "177a773a6278a87f03606edb5237f83bd40ea2e2954649e20930c42eb4bd7f17",
                "e5c551250ccb2dfbd11b5d38eae670d0476909acb7d1955c78c53647dd5de3e9", 0,
                True,
            ),
            (
                "abcdefg",
                "ec088ee2b66fab3b3c43337e8ad992dcc81e69a55f40b36b181a6899fc08a0f8", 0, "177a773a6278a87f03606edb5237f83bd40ea2e2954649e20930c42eb4bd7f17",
                "f5c551250ccb2dfbd11b5d38eae670d0476909acb7d1955c78c53647dd5de3e9", 0,
                False,
            ),
        )

        kdf = get_beam_kdf(self.mnemonic)
        for test_params in test_datasets:
            message = test_params[0]
            nonce_pub_x = test_params[1]
            nonce_pub_y = test_params[2]
            sign_k = test_params[3]
            pub_key_x = test_params[4]
            pub_key_y = test_params[5]
            expected_is_valid = int(test_params[6])

            message = message_digest(message)
            signature = BeamSignature(
                nonce_pub=BeamECCPoint(x=unhexlify(nonce_pub_x), y=int(nonce_pub_y)),
                sign_k = unhexlify(sign_k))
            public_key = BeamECCPoint(x=unhexlify(pub_key_x), y=int(pub_key_y))

            is_valid = is_valid_beam_message(signature, public_key, message)

            self.assertEqual(is_valid, expected_is_valid)
            self.assertNotEqual(not is_valid, expected_is_valid)


if __name__ == '__main__':
    unittest.main()

