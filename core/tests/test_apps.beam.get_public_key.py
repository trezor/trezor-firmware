from common import *

from apps.beam.get_public_key import get_public_key
from trezor.messages.BeamECCPoint import BeamECCPoint

from apps.beam.helpers import (
    bin_to_str,
    get_beam_kdf,
    get_beam_pk,
)

class TestBeamGetPublicKey(unittest.TestCase):
    def test_get_public_key(self):
        mnemonic = "all all all all all all all all all all all all"
        kdf = get_beam_kdf(mnemonic)
        test_datasets = (
            (0, 0, "88b528eecb5ee5ae81e56e2105aca06997761c9cd2e566b25eaee1951be26688", 1),
            (0, 1, "53839a38c1089e28e901279266cff2da921ca82ed39c6ac0261a039157754e40", 1),
            (0, 8, "a3378664f9ada1a32cf860076ec6110621c7430d9b04316a20b56ced6fd73546", 1),
            (1, 1, "da2d246d99860617bd37755605f0584de6094b437efb4931ec20cf85b62631a5", 0),
            (1, 8, "54158bdbeef7292b96d5ea57b2eebc3ba6c8d4a16cfeb6cd75354e8497d009b8", 1),
            (2, 8, "bfb3e6e6eb8ee2b686aaa6a056fa2670a5c49d76583eb05fb84d9c5ab7227c71", 0),
            (3, 0, "22e6e269fb26638d8501583d5a7c0c8051315f9576174cc6f64dacfe9a01ef7f", 0),
            (3, 3, "392b73f534c490f614c36a3ad738a10b2cc4b08543e6250a2b2927d1c5ffa4ba", 1),
            (4, 4, "e5c551250ccb2dfbd11b5d38eae670d0476909acb7d1955c78c53647dd5de3e9", 0),
            (5, 2, "269c9a18d3a8f5acf4036a711e41cf7c5071aceac1fe95666040369a3311ac71", 0),
            (10, 3, "706bc1d21de9d4fdf4daef73b7774cb7e869e454a7776d8116c0ce86f9427577", 0),
        )

        for test_params in test_datasets:
            kid_idx = test_params[0]
            kid_sub_idx = test_params[1]
            expected_public_key_x = test_params[2]
            expected_public_key_y = test_params[3]

            pk = get_beam_pk(kid_idx, kid_sub_idx, kdf)
            self.assertEqual(bin_to_str(pk[0]), expected_public_key_x)
            self.assertEqual(pk[1], expected_public_key_y)

    def test_get_public_key_another_mnemonic(self):
        mnemonic = "abc abc abc abc abc abc abc abc abc abc abc abc"
        kdf = get_beam_kdf(mnemonic)
        test_datasets = (
            (0, 0, "119a034ddd950028e45ee1d0c9b26efba0fb28af83e7f2ba83a5c0fa7ae2daee", 0),
            (0, 1, "2a4c57b74f1cc0ee995ceab14ae9e9bc581da8ccb290564d15b9079858635604", 1),
            (0, 8, "418ec586d5ff80c1d82b25892c64a45243d9630fec255580cb2f0ac95b614415", 1),
            (1, 1, "f3632a997e42ff854d8d450113e8bea6f47e2ef069ed6cf36188343a1c7df013", 0),
            (2, 8, "a135d3ddcbce9cc76e46c2c8374ab084e88e01d81eb8a9588bd19cb997a41f91", 1),
            (3, 0, "19812e15f636ae0df35cc158d3496dd33999cf8f18df939588248d3f8ff86bd7", 0),
            (3, 3, "9e2b9fb5178fb4e71a8242b658c249e0aceb7ac576fc20a034a67c8c4f5b1c61", 0),
            (4, 4, "d320b5f0fcdcbfe2d005bff93d0fec1e1ac33abeebe51b2c9322176f820252cf", 1),
            (5, 2, "3206c52f75f777b230f64e0d6dff6eb6c2a1566b3b887943939beb0d3a6444f1", 1),
            (10, 3, "ff33f03af33b4b062e69479327d1fc02c13a22354dcd9a3bc7162ad3b2768f1c", 1),
        )

        for test_params in test_datasets:
            kid_idx = test_params[0]
            kid_sub_idx = test_params[1]
            expected_public_key_x = test_params[2]
            expected_public_key_y = test_params[3]

            pk = get_beam_pk(kid_idx, kid_sub_idx, kdf)
            self.assertEqual(bin_to_str(pk[0]), expected_public_key_x)
            self.assertEqual(pk[1], expected_public_key_y)


if __name__ == '__main__':
    unittest.main()

