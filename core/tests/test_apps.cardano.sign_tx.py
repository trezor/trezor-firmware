from common import *
from apps.common import HARDENED
from trezor.messages import CardanoTxInputType

if not utils.BITCOIN_ONLY:
    from apps.cardano.sign_tx import _should_hide_output


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoSignTransaction(unittest.TestCase):
    def test_should_show_outputs(self):
        outputs_to_hide = [
            # output is from the same address as input
            (
                [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                [[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0]],
            ),
            # output is from the same account but from different addresses
            (
                [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                [
                    [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                    [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 1],
                    [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 2],
                ],
            ),
            # both output and input are from account 2
            (
                [44 | HARDENED, 1815 | HARDENED, 2 | HARDENED, 0, 0],
                [
                    [44 | HARDENED, 1815 | HARDENED, 2 | HARDENED, 0, 0],
                    [44 | HARDENED, 1815 | HARDENED, 2 | HARDENED, 0, 1],
                    [44 | HARDENED, 1815 | HARDENED, 2 | HARDENED, 0, 2],
                ],
            ),
            # byron input and shelley output
            (
                [1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                [
                    [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                ],
            ),
            # mixed byron and shelley inputs
            (
                [1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                [
                    [1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                    [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                ],
            ),
        ]
        outputs_to_show = [
            # output is from different account
            (
                [44 | HARDENED, 1815 | HARDENED, 2 | HARDENED, 0, 0],
                [[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0]],
            ),
            # output path is not complete
            (
                [44 | HARDENED, 1815 | HARDENED],
                [[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0]],
            ),
            # output path is not complete
            (
                [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED],
                [[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0]],
            ),
            # one of the inputs has different account than output
            (
                [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                [
                    [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                    [44 | HARDENED, 1815 | HARDENED, 2 | HARDENED, 0, 0],
                ],
            ),
            # staking output path
            (
                [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0,],
                [[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0]],
            ),
            # output address too large
            (
                [44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 1000001],
                [[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0]],
            ),
            # max safe account number exceeded
            (
                [1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
                [
                    [1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0]
                ],
            ),
        ]

        for output_path, input_paths in outputs_to_hide:
            inputs = [
                CardanoTxInputType(address_n=input_path, prev_hash=b"", prev_index=0) for input_path in input_paths
            ]
            self.assertTrue(_should_hide_output(output_path, inputs))

        for output_path, input_paths in outputs_to_show:
            inputs = [
                CardanoTxInputType(address_n=input_path, prev_hash=b"", prev_index=0) for input_path in input_paths
            ]
            self.assertFalse(_should_hide_output(output_path, inputs))


if __name__ == "__main__":
    unittest.main()
