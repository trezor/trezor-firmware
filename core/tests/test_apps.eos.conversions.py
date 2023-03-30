from common import *

if not utils.BITCOIN_ONLY:
    from apps.eos import helpers
    from trezor.messages import EosAsset


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEosConversions(unittest.TestCase):
    def test_eos_name_to_string(self):
        names_in = [
            10639447606881920736,
            614251623682315968,
            614251535012020768,
            7754926748989239168,
            14895601873759291472,
            595056260442243600,
        ]
        names_out = [
            'miniminimini',
            '12345abcdefg',
            '123451234512',
            'hijklmnopqrs',
            'tuvwxyz12345',
            '111111111111',
        ]
        for i, o in zip(names_in, names_out):
            self.assertEqual(helpers.eos_name_to_string(i), o)

    def test_eos_asset_to_string(self):
        asset_in = [
            EosAsset(
              amount=10000,
              symbol=1397703940,
            ),
            EosAsset(
              amount=200000,
              symbol=1397703940,
            ),
            EosAsset(
              amount=255000,
              symbol=1397703940,
            ),
            EosAsset(
              amount=999999,
              symbol=1397703939,
            ),
            EosAsset(
              amount=1,
              symbol=1397703940,
            ),
            EosAsset(
              amount=999,
              symbol=1397703939,
            ),
        ]
        asset_out = [
            '1.0000 EOS',
            '20.0000 EOS',
            '25.5000 EOS',
            '999.999 EOS',
            '0.0001 EOS',
            '0.999 EOS',
        ]
        for i, o in zip(asset_in, asset_out):
            self.assertEqual(helpers.eos_asset_to_string(i), o)

if __name__ == '__main__':
    unittest.main()
