from common import *

from apps.wallet.sign_tx.scripts import script_replay_protection_bip115

class TestSigntxScripts(unittest.TestCase):
    # pylint: disable=C0301

    def test_script_replay_protection_bip115(self):
        vectors=[
            ('206ec9b310745775c20cbe5bae8751daeb7f086cf913399d4f7634ef2a0000000003122005b4', '6ec9b310745775c20cbe5bae8751daeb7f086cf913399d4f7634ef2a00000000', 335890),
            ('20caaa71b60cf893c1604b38e5af1bdc322dbb31818239088647272d1400000000030e2005b4', 'caaa71b60cf893c1604b38e5af1bdc322dbb31818239088647272d1400000000', 335886),
        ]
        for out, hsh, height in vectors:
            hsh = unhexlify(hsh)
            res = hexlify(script_replay_protection_bip115(hsh, height)).decode()
            self.assertEqual(out, res)


if __name__ == '__main__':
    unittest.main()
