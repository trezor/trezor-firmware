from common import *
from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from apps.cardano.sign_tx import _should_hide_output


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoSignTransaction(unittest.TestCase):
    def test_should_show_outputs(self):
        outputs_to_hide = [
            # byron path
            [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            # shelley path
            [1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            # path account is 2
            [1852 | HARDENED, 1815 | HARDENED, 2 | HARDENED, 0, 0],
            # path index is 2
            [1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 2],
        ]
        outputs_to_show = [
            # path is not complete
            [1852 | HARDENED, 1815 | HARDENED],
            # path is not complete
            [1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED],
            # staking output path
            [1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0,],
            # max safe account number exceeded
            [1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
            # output address too large
            [1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 1000001],
        ]

        for output_path in outputs_to_hide:
            self.assertTrue(_should_hide_output(output_path))

        for output_path in outputs_to_show:
            self.assertFalse(_should_hide_output(output_path))


if __name__ == "__main__":
    unittest.main()
