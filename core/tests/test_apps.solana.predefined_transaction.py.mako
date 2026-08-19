# generated from test_apps.solana.predefined_transaction.py.mako
# do not edit manually!
<%def name="getProgramId(program)">${"_".join(program["name"].upper().split(" ") + ["ID"])}</%def>\
<%def name="getInstructionIdText(program, instruction)">${"_".join([getProgramId(program)] + ["INS"] + instruction["name"].upper().split(" "))}</%def>\
from common import Any, unittest, utils  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.crypto import base58

    from apps.solana.predefined_transaction import (
        _is_predefined_claim,
        _is_predefined_stake,
        _is_predefined_unstake,
        is_predefined_token_transfer,
    )
    from apps.solana.transaction.instruction import Instruction
    from apps.solana.types import AddressType

% for program in programs["programs"]:
${getProgramId(program)} = "${program["id"]}"
% endfor

% for program in programs["programs"]:
    % for instruction in program["instructions"]:
${getInstructionIdText(program, instruction)} = ${instruction["id"]}
    % endfor
% endfor

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


def create_account(address, is_reference=False):
    # direct address: (pubkey, type); ALT reference: (table_address, index, type)
    if is_reference:
        return (base58.decode(address), 0, AddressType.AddressRw)
    return (base58.decode(address), AddressType.AddressRw)


def create_transfer_token_instruction(
    program_id=TOKEN_PROGRAM_ID,
    instruction_id=TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED,
    token_mint="GHArwcWCuk9WkUG4XKUbt935rKfmBmywbEWyFxdH3mou",
    destination_account="92YgwqTtTWB7qY92JT6mbL2WCmhAs7LPZL4jLcizNfwx",
    owner="14CCvQzQzHCVgZM3j9soPnXuJXh1RmCfwLVUcdfbZVBS",
    mint_is_reference=False,
    destination_is_reference=False,
    owner_is_reference=False,
):
    return create_mock_instruction(
        program_id,
        instruction_id,
        {
            "token_mint": create_account(token_mint, mint_is_reference),
            "destination_account": create_account(
                destination_account, destination_is_reference
            ),
            "owner": create_account(owner, owner_is_reference),
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
            "token_mint": create_account(token_mint),
            "associated_token_account": create_account(associated_token_account),
            "spl_token": create_account(spl_token),
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
            # ALT-referenced destination, can't be resolved on-device
            [
                create_transfer_token_instruction(destination_is_reference=True),
            ],
            # one direct and one ALT-referenced destination
            [
                create_transfer_token_instruction(),
                create_transfer_token_instruction(destination_is_reference=True),
            ],
            # ALT-referenced token mint, can't be resolved on-device
            [
                create_transfer_token_instruction(mint_is_reference=True),
            ],
            # one direct and one ALT-referenced token mint
            [
                create_transfer_token_instruction(),
                create_transfer_token_instruction(mint_is_reference=True),
            ],
            # ALT-referenced owner, can't be resolved on-device
            [
                create_transfer_token_instruction(owner_is_reference=True),
            ],
            # one direct and one ALT-referenced owner
            [
                create_transfer_token_instruction(),
                create_transfer_token_instruction(owner_is_reference=True),
            ],
        ]

        for instructions in valid_test_cases:
            self.assertTrue(is_predefined_token_transfer(instructions))

        for instructions in invalid_test_cases:
            self.assertFalse(is_predefined_token_transfer(instructions))


# derived using m/44'/501'/0'/0' from the "all all ..." seed
SIGNER = "14CCvQzQzHCVgZM3j9soPnXuJXh1RmCfwLVUcdfbZVBS"
STAKE_ACCOUNT = "ATFXMD5cYiw9yHkvexgx3nf9LNSouEViB5BZBsgwunAv"
VOTE_ACCOUNT = "ETxHeBBcuw9Yu4dGuP3oXrD12V5RECvmi8ogQ9PkjyVF"
FOREIGN_ACCOUNT = "AeDJ1BqA7ruBbd6mEcS1QNxFbT8FQbiBVuN9NqK94Taq"


def create_staking_instructions(
    unix_timestamp=0,
    epoch=0,
    custodian=SYSTEM_PROGRAM_ID,
    funding_account=SIGNER,
    staker=SIGNER,
    withdrawer=SIGNER,
    delegate_stake_account=STAKE_ACCOUNT,
    vote_account_is_reference=False,
):
    create = create_mock_instruction(
        SYSTEM_PROGRAM_ID,
        SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED,
        {
            "funding_account": create_account(funding_account),
            "created_account": create_account(STAKE_ACCOUNT),
            "base": base58.decode(SIGNER),
            "owner": base58.decode(STAKE_PROGRAM_ID),
        },
    )
    init = create_mock_instruction(
        STAKE_PROGRAM_ID,
        STAKE_PROGRAM_ID_INS_INITIALIZE,
        {
            "uninitialized_stake_account": create_account(STAKE_ACCOUNT),
            "staker": base58.decode(staker),
            "withdrawer": base58.decode(withdrawer),
            "unix_timestamp": unix_timestamp,
            "epoch": epoch,
            "custodian": base58.decode(custodian),
        },
    )
    delegate = create_mock_instruction(
        STAKE_PROGRAM_ID,
        STAKE_PROGRAM_ID_INS_DELEGATE_STAKE,
        {
            "initialized_stake_account": create_account(delegate_stake_account),
            "vote_account": create_account(VOTE_ACCOUNT, vote_account_is_reference),
            "stake_authority": create_account(SIGNER),
        },
    )
    return [create, init, delegate]


def create_deactivate_instruction(stake_authority=SIGNER):
    return create_mock_instruction(
        STAKE_PROGRAM_ID,
        STAKE_PROGRAM_ID_INS_DEACTIVATE,
        {
            "delegated_stake_account": create_account(STAKE_ACCOUNT),
            "stake_authority": create_account(stake_authority),
        },
    )


def create_withdraw_instruction(
    withdrawal_authority=SIGNER,
    recipient_account=SIGNER,
    recipient_is_reference=False,
):
    return create_mock_instruction(
        STAKE_PROGRAM_ID,
        STAKE_PROGRAM_ID_INS_WITHDRAW,
        {
            "stake_account": create_account(STAKE_ACCOUNT),
            "recipient_account": create_account(
                recipient_account, recipient_is_reference
            ),
            "withdrawal_authority": create_account(withdrawal_authority),
        },
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSolanaStakingTransactions(unittest.TestCase):
    def test_is_predefined_stake(self):
        signer = base58.decode(SIGNER)

        valid_test_cases = [
            # no lockup
            create_staking_instructions(),
            # foreign withdrawer, it only triggers an extra confirmation screen
            create_staking_instructions(withdrawer=FOREIGN_ACCOUNT),
        ]

        invalid_test_cases = [
            # empty transaction
            [],
            # missing delegate instruction
            create_staking_instructions()[:2],
            # lockup time set
            create_staking_instructions(unix_timestamp=4102444800),
            # lockup epoch set
            create_staking_instructions(epoch=1000),
            # lockup custodian set
            create_staking_instructions(custodian=FOREIGN_ACCOUNT),
            # funding account is not the signer
            create_staking_instructions(funding_account=FOREIGN_ACCOUNT),
            # staker is not the signer
            create_staking_instructions(staker=FOREIGN_ACCOUNT),
            # delegate operates on a different stake account
            create_staking_instructions(delegate_stake_account=FOREIGN_ACCOUNT),
            # ALT-referenced vote account
            create_staking_instructions(vote_account_is_reference=True),
        ]

        for instructions in valid_test_cases:
            self.assertTrue(_is_predefined_stake(instructions, signer))

        for instructions in invalid_test_cases:
            self.assertFalse(_is_predefined_stake(instructions, signer))

    def test_is_predefined_unstake(self):
        signer = base58.decode(SIGNER)

        valid_test_cases = [
            [create_deactivate_instruction()],
            [create_deactivate_instruction(), create_deactivate_instruction()],
        ]

        invalid_test_cases = [
            # empty transaction
            [],
            # stake authority is not the signer
            [create_deactivate_instruction(stake_authority=FOREIGN_ACCOUNT)],
            # other instruction types present
            [create_deactivate_instruction(), create_withdraw_instruction()],
        ]

        for instructions in valid_test_cases:
            self.assertTrue(_is_predefined_unstake(instructions, signer))

        for instructions in invalid_test_cases:
            self.assertFalse(_is_predefined_unstake(instructions, signer))

    def test_is_predefined_claim(self):
        signer = base58.decode(SIGNER)

        valid_test_cases = [
            [create_withdraw_instruction()],
            [create_withdraw_instruction(), create_withdraw_instruction()],
            # foreign recipient, it only triggers an extra confirmation screen
            [create_withdraw_instruction(recipient_account=FOREIGN_ACCOUNT)],
        ]

        invalid_test_cases = [
            # empty transaction
            [],
            # withdrawal authority is not the signer
            [create_withdraw_instruction(withdrawal_authority=FOREIGN_ACCOUNT)],
            # ALT-referenced recipient
            [create_withdraw_instruction(recipient_is_reference=True)],
            # recipient mismatch
            [
                create_withdraw_instruction(),
                create_withdraw_instruction(recipient_account=FOREIGN_ACCOUNT),
            ],
            # other instruction types present
            [create_withdraw_instruction(), create_deactivate_instruction()],
        ]

        for instructions in valid_test_cases:
            self.assertTrue(_is_predefined_claim(instructions, signer))

        for instructions in invalid_test_cases:
            self.assertFalse(_is_predefined_claim(instructions, signer))


if __name__ == "__main__":
    unittest.main()
