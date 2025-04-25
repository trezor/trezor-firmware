# generated from test_apps.solana.predefined_transaction.py.mako
# do not edit manually!
from common import Any, unittest, utils  # isort:skip

from trezor.crypto import base58

from apps.solana.predefined_transaction import is_predefined_token_transfer
from apps.solana.transaction.instruction import Instruction

SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"
COMPUTE_BUDGET_PROGRAM_ID = "ComputeBudget111111111111111111111111111111"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
MEMO_LEGACY_PROGRAM_ID = "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"

SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT = 0
SYSTEM_PROGRAM_ID_INS_ASSIGN = 1
SYSTEM_PROGRAM_ID_INS_TRANSFER = 2
SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED = 3
SYSTEM_PROGRAM_ID_INS_ADVANCE_NONCE_ACCOUNT = 4
SYSTEM_PROGRAM_ID_INS_WITHDRAW_NONCE_ACCOUNT = 5
SYSTEM_PROGRAM_ID_INS_INITIALIZE_NONCE_ACCOUNT = 6
SYSTEM_PROGRAM_ID_INS_AUTHORIZE_NONCE_ACCOUNT = 7
SYSTEM_PROGRAM_ID_INS_ALLOCATE = 8
SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED = 9
SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED = 10
SYSTEM_PROGRAM_ID_INS_TRANSFER_WITH_SEED = 11
SYSTEM_PROGRAM_ID_INS_UPGRADE_NONCE_ACCOUNT = 12
STAKE_PROGRAM_ID_INS_INITIALIZE = 0
STAKE_PROGRAM_ID_INS_AUTHORIZE = 1
STAKE_PROGRAM_ID_INS_DELEGATE_STAKE = 2
STAKE_PROGRAM_ID_INS_SPLIT = 3
STAKE_PROGRAM_ID_INS_WITHDRAW = 4
STAKE_PROGRAM_ID_INS_DEACTIVATE = 5
STAKE_PROGRAM_ID_INS_SET_LOCKUP = 6
STAKE_PROGRAM_ID_INS_MERGE = 7
STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED = 8
STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED = 9
STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED = 10
STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED = 11
STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED = 12
COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME = 1
COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT = 2
COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE = 3
TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT = 1
TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG = 2
TOKEN_PROGRAM_ID_INS_TRANSFER = 3
TOKEN_PROGRAM_ID_INS_APPROVE = 4
TOKEN_PROGRAM_ID_INS_REVOKE = 5
TOKEN_PROGRAM_ID_INS_SET_AUTHORITY = 6
TOKEN_PROGRAM_ID_INS_MINT_TO = 7
TOKEN_PROGRAM_ID_INS_BURN = 8
TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT = 9
TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT = 10
TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT = 11
TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED = 12
TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED = 13
TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED = 14
TOKEN_PROGRAM_ID_INS_BURN_CHECKED = 15
TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2 = 16
TOKEN_PROGRAM_ID_INS_SYNC_NATIVE = 17
TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3 = 18
TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER = 22
TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT = 1
TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_MULTISIG = 2
TOKEN_2022_PROGRAM_ID_INS_TRANSFER = 3
TOKEN_2022_PROGRAM_ID_INS_APPROVE = 4
TOKEN_2022_PROGRAM_ID_INS_REVOKE = 5
TOKEN_2022_PROGRAM_ID_INS_SET_AUTHORITY = 6
TOKEN_2022_PROGRAM_ID_INS_MINT_TO = 7
TOKEN_2022_PROGRAM_ID_INS_BURN = 8
TOKEN_2022_PROGRAM_ID_INS_CLOSE_ACCOUNT = 9
TOKEN_2022_PROGRAM_ID_INS_FREEZE_ACCOUNT = 10
TOKEN_2022_PROGRAM_ID_INS_THAW_ACCOUNT = 11
TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED = 12
TOKEN_2022_PROGRAM_ID_INS_APPROVE_CHECKED = 13
TOKEN_2022_PROGRAM_ID_INS_MINT_TO_CHECKED = 14
TOKEN_2022_PROGRAM_ID_INS_BURN_CHECKED = 15
TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2 = 16
TOKEN_2022_PROGRAM_ID_INS_SYNC_NATIVE = 17
TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3 = 18
TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER = 22
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE = None
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT = 1
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED = 2
MEMO_PROGRAM_ID_INS_MEMO = None
MEMO_LEGACY_PROGRAM_ID_INS_MEMO = None


def create_mock_instruction(
    program_id: str, instruction_id: int, parsed_data: dict[str, Any]
):
    instruction = Instruction(
        instruction_data=b"",
        program_id=program_id,
        accounts=[],
        instruction_id=instruction_id,
        property_templates=[],
        accounts_required=0,
        account_templates=[],
        ui_properties=[],
        ui_name="",
        is_program_supported=True,
        is_instruction_supported=True,
        is_ui_hidden=False,
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
