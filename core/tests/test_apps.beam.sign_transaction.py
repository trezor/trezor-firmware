from common import *

from trezor import config
from trezor.crypto import beam
from trezor.pin import pin_to_int

from trezor.messages.BeamSignedTransaction import BeamSignedTransaction

from apps.beam.helpers import (
    bin_to_str,
)
from apps.beam.sign_transaction import (
    sign_tx_part_1,
    sign_tx_part_2,
)
from apps.beam.nonce import create_master_nonce

class KIDV_Test:
    idx = 0
    type = 0
    sub_idx = 0
    value = 0

    @staticmethod
    def from_list(kidv_as_list):
        return KIDV_Test(kidv_as_list[0], kidv_as_list[1], kidv_as_list[2], kidv_as_list[3])

    def __init__(self, idx, type, sub_idx, value):
        self.idx = idx
        self.type = type
        self.sub_idx = sub_idx
        self.value = value


def create_kidv_list_from(list_kidv):
    return list(map(lambda element: KIDV_Test.from_list(element), list_kidv))

class TestBeamSignTransaction(unittest.TestCase):
    mnemonic = "all all all all all all all all all all all all"
    seed = beam.from_mnemonic_beam(mnemonic)

    def test_sign_transaction(self):
        test_datasets = (
            (
                # Inputs:
                [
                    # KIDV:
                    # idx, type, sub_idx, value
                    [1, 1, 1, 2],
                    [2, 2, 2, 5],
                ],
                # Outputs:
                [
                    # KIDV:
                    # idx, type, sub_idx, value
                    [3, 3, 3, 3],
                ],
                # Nonce slot:
                2,
                # Kernel params:
                # fee, min_height, max_height,
                # commitment_x, commitment_y,
                # multisig_nonce_x, multisig_nonce_y,
                # offset_sk
                # expected_signature, expected_is_signed
                1, 1, 5,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef", 0,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef", 0,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
                "614856ca69245fd9c6e8db15a256c050ca078e79a6f49e61e24688fdcad73bf6", True
            ),
            (
                [
                    [1, 0, 1, 8],
                    [2, 0, 0, 5],
                ],
                [
                    [1, 0, 1, 4],
                ],
                2,
                1, 1, 5,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef", 0,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef", 0,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
                "7c4fe694451b28159e5407714072acd1eae4da18aef1dfd42bb165405f529a04", True
            ),
            (
                [
                    [0, 0, 0, 40],
                ],
                [
                    [0, 0, 0, 16],
                    [0, 0, 0, 24],
                ],
                1,
                0, 25000, 27500,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef", 0,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef", 0,
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
                "60e3e9d87bd264bdcac4518284bd4f850561c3bb251bd758bb1349a44188a28c", True
            ),
        )

        config.init()
        config.wipe()
        config.unlock(pin_to_int(''))
        create_master_nonce(self.seed)

        for test_params in test_datasets:
            inputs = create_kidv_list_from(test_params[0])
            outputs = create_kidv_list_from(test_params[1])
            nonce_slot = test_params[2]
            fee = test_params[3]
            min_height = test_params[4]
            max_height = test_params[5]
            commitment_x = test_params[6]
            commitment_y = test_params[7]
            multisig_nonce_x = test_params[8]
            multisig_nonce_y = test_params[9]
            offset_sk = test_params[10]
            expected_signature = test_params[11]
            expected_is_signed = test_params[12]

            tm = beam.TransactionMaker()

            sk_total, value_transferred = sign_tx_part_1(
                tm,
                self.mnemonic,
                inputs, outputs,
                fee,
                min_height, max_height,
                commitment_x, commitment_y,
                multisig_nonce_x, multisig_nonce_y,
                nonce_slot,
                offset_sk)

            signature, is_signed = sign_tx_part_2(tm, sk_total, nonce_slot)

            self.assertEqual(bin_to_str(signature), expected_signature)
            self.assertEqual(is_signed, expected_is_signed)


if __name__ == '__main__':
    unittest.main()

