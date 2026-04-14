from common import unittest, utils  # isort:skip

from apps.solana.constants import SOLANA_COMPUTE_UNIT_LIMIT
from apps.solana.transaction import (
    COMPUTE_BUDGET_PROGRAM_ID,
    COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT,
    COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
    ED25519_PROGRAM_ID,
    SECP256K1_PROGRAM_ID,
    SECP256R1_PROGRAM_ID,
    Transaction,
)


class MockInstruction:
    def __init__(
        self,
        program_id,
        instruction_id=None,
        instruction_data=b"",
        units=0,
        lamports=0,
    ):
        self.program_id = program_id
        self.instruction_id = instruction_id
        self.instruction_data = instruction_data
        self.units = units
        self.lamports = lamports
        self.is_ui_hidden = False


def make_transaction(instructions, required_signers_count):
    transaction = Transaction.__new__(Transaction)
    transaction.instructions = instructions
    transaction.required_signers_count = required_signers_count
    transaction.calculate_rent = lambda: 0
    return transaction


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSolanaTransactionFee(unittest.TestCase):
    def test_calculate_fee_includes_precompile_signatures(self):
        transaction = make_transaction(
            [
                MockInstruction(ED25519_PROGRAM_ID, instruction_data=b"\x02"),
                MockInstruction(SECP256K1_PROGRAM_ID, instruction_data=b"\x03"),
                MockInstruction(SECP256R1_PROGRAM_ID, instruction_data=b"\x01"),
            ],
            required_signers_count=1,
        )

        fee = transaction.calculate_fee()

        self.assertIsNotNone(fee)
        self.assertEqual(fee.base, 35_000)
        self.assertEqual(fee.priority, 0)
        self.assertEqual(fee.rent, 0)
        self.assertEqual(fee.total, 35_000)

    def test_calculate_fee_ignores_missing_precompile_count(self):
        transaction = make_transaction(
            [
                MockInstruction(ED25519_PROGRAM_ID),
                MockInstruction(SECP256K1_PROGRAM_ID, instruction_data=b"\x00"),
            ],
            required_signers_count=1,
        )

        fee = transaction.calculate_fee()

        self.assertIsNotNone(fee)
        self.assertEqual(fee.base, 5_000)

    def test_calculate_fee_keeps_priority_fee_with_precompiles(self):
        transaction = make_transaction(
            [
                MockInstruction(ED25519_PROGRAM_ID, instruction_data=b"\x02"),
                MockInstruction(
                    COMPUTE_BUDGET_PROGRAM_ID,
                    instruction_id=COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT,
                    units=3,
                ),
                MockInstruction(
                    COMPUTE_BUDGET_PROGRAM_ID,
                    instruction_id=COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
                    lamports=1_000_000,
                ),
            ],
            required_signers_count=1,
        )

        fee = transaction.calculate_fee()

        self.assertIsNotNone(fee)
        self.assertEqual(fee.base, 15_000)
        self.assertEqual(fee.priority, 3)
        self.assertEqual(fee.rent, 0)
        self.assertEqual(fee.total, 15_003)

    def test_calculate_fee_uses_default_unit_limit_for_non_compute_budget_txs(self):
        transaction = make_transaction(
            [
                MockInstruction(
                    COMPUTE_BUDGET_PROGRAM_ID,
                    instruction_id=COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
                    lamports=1,
                ),
                MockInstruction("11111111111111111111111111111111"),
                MockInstruction("Stake11111111111111111111111111111111111111"),
            ],
            required_signers_count=1,
        )

        fee = transaction.calculate_fee()

        self.assertIsNotNone(fee)
        self.assertEqual(fee.base, 5_000)
        self.assertEqual(fee.priority, (2 * SOLANA_COMPUTE_UNIT_LIMIT + 999_999) // 1_000_000)
        self.assertEqual(fee.rent, 0)
        self.assertEqual(fee.total, fee.base + fee.priority)
