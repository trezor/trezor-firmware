from common import *  # isort:skip

from trezor.crypto import base58

from apps.solana.predefined_transaction import is_predefined_token_transfer
from apps.solana.transaction.instruction import Instruction
from apps.solana.transaction.instructions import (
    ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
    ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE,
    SYSTEM_PROGRAM_ID,
    SYSTEM_PROGRAM_ID_INS_TRANSFER,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED,
    TOKEN_PROGRAM_ID,
    TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED,
)


def create_mock_instruction(
    program_id: str, instruction_id: int, parsed_data: dict[str, Any]
):
    instruction = Instruction(
        instruction_data=b"",
        program_id=program_id,
        accounts=[],
        instruction_id=instruction_id,
        property_templates=[],
        accounts_template=[],
        ui_properties=[],
        ui_name="",
        is_program_supported=True,
        is_instruction_supported=True,
        supports_multisig=False,
        is_deprecated_warning=None,
    )

    instruction.parsed_data = parsed_data
    return instruction


def create_transfer_token_instruction(
    program_id=TOKEN_PROGRAM_ID,
    instruction_id=TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED,
    token_mint="GHArwcWCuk9WkUG4XKUbt935rKfmBmywbEWyFxdH3mou",
    destination_account="92YgwqTtTWB7qY92JT6mbL2WCmhAs7LPZL4jLcizNfwx",
    owner="14CCvQzQzHCVgZM3j9soPnXuJXh1RmCfwLVUcdfbZVBS",
):
    return create_mock_instruction(
        program_id,
        instruction_id,
        {
            "token_mint": (base58.decode(token_mint),),
            "destination_account": (base58.decode(destination_account),),
            "owner": (base58.decode(owner),),
        },
    )


def create_create_token_account_instruction(
    token_mint="GHArwcWCuk9WkUG4XKUbt935rKfmBmywbEWyFxdH3mou",
    associated_token_account="92YgwqTtTWB7qY92JT6mbL2WCmhAs7LPZL4jLcizNfwx",
    spl_token=TOKEN_PROGRAM_ID,
):
    return create_mock_instruction(
        ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
        ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE,
        {
            "token_mint": (base58.decode(token_mint),),
            "associated_token_account": (base58.decode(associated_token_account),),
            "spl_token": (base58.decode(spl_token),),
        },
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSolanaPredefinedTransactions(unittest.TestCase):
    def test_is_predefined_token_transfer(self):
        # note: if there are multiple transfer instructions they are the same
        # in the tests because that's the info the test cares about. In reality
        # the instructions can differ in the destination account and amount.
        valid_test_cases = [
            [create_transfer_token_instruction()],
            [create_transfer_token_instruction(), create_transfer_token_instruction()],
            [
                create_create_token_account_instruction(),
                create_transfer_token_instruction(),
            ],
            [
                create_create_token_account_instruction(),
                create_transfer_token_instruction(),
                create_transfer_token_instruction(),
            ],
            [
                create_create_token_account_instruction(
                    spl_token=TOKEN_2022_PROGRAM_ID
                ),
                create_transfer_token_instruction(
                    program_id=TOKEN_2022_PROGRAM_ID,
                    instruction_id=TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED,
                ),
                create_transfer_token_instruction(
                    program_id=TOKEN_2022_PROGRAM_ID,
                    instruction_id=TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED,
                ),
            ],
        ]

        invalid_test_cases = [
            # only create account
            [
                create_create_token_account_instruction(),
            ],
            # there are other instructions
            [
                create_transfer_token_instruction(),
                create_mock_instruction(
                    SYSTEM_PROGRAM_ID, SYSTEM_PROGRAM_ID_INS_TRANSFER, {}
                ),
            ],
            # multiple create account instructions
            [
                create_create_token_account_instruction(),
                create_create_token_account_instruction(),
                create_transfer_token_instruction(),
            ],
            # transfer instructions program_id mismatch
            [
                create_transfer_token_instruction(
                    program_id=TOKEN_PROGRAM_ID,
                    instruction_id=TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED,
                ),
                create_transfer_token_instruction(
                    program_id=TOKEN_2022_PROGRAM_ID,
                    instruction_id=TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED,
                ),
            ],
            # transfer instructions token_mint mismatch
            [
                create_transfer_token_instruction(
                    token_mint="GHArwcWCuk9WkUG4XKUbt935rKfmBmywbEWyFxdH3mou"
                ),
                create_transfer_token_instruction(
                    token_mint="GZDphoFQJ9m7uRU7TdS8cVDGFvsiQbcaY3n5mdoQHmDj"
                ),
            ],
            # transfer instructions destination mismatch
            [
                create_transfer_token_instruction(
                    destination_account="92YgwqTtTWB7qY92JT6mbL2WCmhAs7LPZL4jLcizNfwx"
                ),
                create_transfer_token_instruction(
                    destination_account="74pZnim7gywyschy4MGkW6eZURv1DBXqwHTCqLRk63wz"
                ),
            ],
            # transfer instructions owner mismatch
            [
                create_transfer_token_instruction(
                    owner="14CCvQzQzHCVgZM3j9soPnXuJXh1RmCfwLVUcdfbZVBS"
                ),
                create_transfer_token_instruction(
                    owner="BVRFH6vt5bNXub6WnnFRgaHFTcbkjBrf7x1troU1izGg"
                ),
            ],
            # token program mismatch
            [
                create_create_token_account_instruction(
                    spl_token=TOKEN_2022_PROGRAM_ID
                ),
                create_transfer_token_instruction(
                    program_id=TOKEN_PROGRAM_ID,
                ),
            ],
            # create account token_mint mismatch
            [
                create_create_token_account_instruction(
                    token_mint="GZDphoFQJ9m7uRU7TdS8cVDGFvsiQbcaY3n5mdoQHmDj"
                ),
                create_transfer_token_instruction(
                    token_mint="GHArwcWCuk9WkUG4XKUbt935rKfmBmywbEWyFxdH3mou",
                ),
            ],
            # create account associated_token_account mismatch
            [
                create_create_token_account_instruction(
                    associated_token_account="74pZnim7gywyschy4MGkW6eZURv1DBXqwHTCqLRk63wz"
                ),
                create_transfer_token_instruction(
                    destination_account="92YgwqTtTWB7qY92JT6mbL2WCmhAs7LPZL4jLcizNfwx",
                ),
            ],
            # create account is not first
            [
                create_transfer_token_instruction(),
                create_create_token_account_instruction(),
            ],
        ]

        for instructions in valid_test_cases:
            self.assertTrue(is_predefined_token_transfer(instructions))

        for instructions in invalid_test_cases:
            self.assertFalse(is_predefined_token_transfer(instructions))


if __name__ == "__main__":
    unittest.main()
