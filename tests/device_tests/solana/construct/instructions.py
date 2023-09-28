# generated from __init__.py.mako
# do not edit manually!

from enum import IntEnum

from construct import Int32ul, Int64ul, Struct, Switch

from .custom_constructs import (
    _STRING,
    AccountReference,
    Accounts,
    InstructionData,
    InstructionProgramId,
    PublicKey,
)


class Program:
    SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
    STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"
    COMPUTE_BUDGET_PROGRAM_ID = "ComputeBudget111111111111111111111111111111"
    TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
    MEMO_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
    MEMO_LEGACY_ID = "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"


class SystemProgramInstruction(IntEnum):
    INS_CREATE_ACCOUNT = 0
    INS_ASSIGN = 1
    INS_TRANSFER = 2
    INS_CREATE_ACCOUNT_WITH_SEED = 3
    INS_ALLOCATE = 8
    INS_ALLOCATE_WITH_SEED = 9
    INS_ASSIGN_WITH_SEED = 10


class StakeProgramInstruction(IntEnum):
    INS_INITIALIZE = 0
    INS_AUTHORIZE = 1
    INS_DELEGATE_STAKE = 2
    INS_SPLIT = 3
    INS_WITHDRAW = 4
    INS_DEACTIVATE = 5
    INS_SET_LOCKUP = 6
    INS_MERGE = 7
    INS_AUTHORIZE_WITH_SEED = 8
    INS_INITIALIZE_CHECKED = 9
    INS_AUTHORIZE_CHECKED = 10
    INS_AUTHORIZE_CHECKED_WITH_SEED = 11
    INS_SET_LOCKUP_CHECKED = 12


class ComputeBudgetProgramInstruction(IntEnum):
    INS_REQUEST_HEAP_FRAME = 1
    INS_SET_COMPUTE_UNIT_LIMIT = 2
    INS_SET_COMPUTE_UNIT_PRICE = 3


class TokenProgramInstruction(IntEnum):
    INS_INITIALIZE_ACCOUNT = 1
    INS_INITIALIZE_MULTISIG = 2
    INS_TRANSFER = 3
    INS_APPROVE = 4
    INS_REVOKE = 5
    INS_SET_AUTHORITY = 6
    INS_MINT_TO = 7
    INS_BURN = 8
    INS_CLOSE_ACCOUNT = 9
    INS_FREEZE_ACCOUNT = 10
    INS_THAW_ACCOUNT = 11
    INS_TRANSFER_CHECKED = 12
    INS_APPROVE_CHECKED = 13
    INS_MINT_TO_CHECKED = 14
    INS_BURN_CHECKED = 15
    INS_INITIALIZE_ACCOUNT_2 = 16
    INS_SYNC_NATIVE = 17
    INS_INITIALIZE_ACCOUNT_3 = 18
    INS_INITIALIZE_IMMUTABLE_OWNER = 22


class AssociatedTokenAccountProgramInstruction(IntEnum):
    INS_CREATE = 0
    INS_CREATE_IDEMPOTENT = 1
    INS_RECOVER_NESTED = 2


class MemoInstruction(IntEnum):
    INS_CREATE = 0


class MemoLegacyInstruction(IntEnum):
    INS_CREATE = 0


_SYSTEM_PROGRAM_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        SystemProgramInstruction.INS_CREATE_ACCOUNT: Accounts(
            "funding_account" / AccountReference(),
            "new_account" / AccountReference(),
        ),
        SystemProgramInstruction.INS_ASSIGN: Accounts(
            "assigned_account" / AccountReference(),
        ),
        SystemProgramInstruction.INS_TRANSFER: Accounts(
            "funding_account" / AccountReference(),
            "recipient_account" / AccountReference(),
        ),
        SystemProgramInstruction.INS_CREATE_ACCOUNT_WITH_SEED: Accounts(
            "funding_account" / AccountReference(),
            "created_account" / AccountReference(),
            "base_account" / AccountReference(),
        ),
        SystemProgramInstruction.INS_ALLOCATE: Accounts(
            "new_account" / AccountReference(),
        ),
        SystemProgramInstruction.INS_ALLOCATE_WITH_SEED: Accounts(
            "allocated_account" / AccountReference(),
            "base_account" / AccountReference(),
        ),
        SystemProgramInstruction.INS_ASSIGN_WITH_SEED: Accounts(
            "assigned_account" / AccountReference(),
            "base_account" / AccountReference(),
        ),
    },
)
_STAKE_PROGRAM_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        StakeProgramInstruction.INS_INITIALIZE: Accounts(
            "uninitialized_stake_account" / AccountReference(),
            "rent_sysvar" / AccountReference(),
        ),
        StakeProgramInstruction.INS_AUTHORIZE: Accounts(
            "stake_account" / AccountReference(),
            "clock_sysvar" / AccountReference(),
            "stake_or_withdraw_authority" / AccountReference(),
            "lockup_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_DELEGATE_STAKE: Accounts(
            "initialized_stake_account" / AccountReference(),
            "vote_account" / AccountReference(),
            "clock_sysvar" / AccountReference(),
            "stake_history_sysvar" / AccountReference(),
            "config_account" / AccountReference(),
            "stake_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_SPLIT: Accounts(
            "stake_account" / AccountReference(),
            "uninitialized_stake_account" / AccountReference(),
            "stake_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_WITHDRAW: Accounts(
            "stake_account" / AccountReference(),
            "recipient_account" / AccountReference(),
            "clock_sysvar" / AccountReference(),
            "stake_history_sysvar" / AccountReference(),
            "withdrawal_authority" / AccountReference(),
            "lockup_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_DEACTIVATE: Accounts(
            "delegated_stake_account" / AccountReference(),
            "clock_sysvar" / AccountReference(),
            "stake_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_SET_LOCKUP: Accounts(
            "initialized_stake_account" / AccountReference(),
            "lockup_or_withdraw_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_MERGE: Accounts(
            "destination_stake_account" / AccountReference(),
            "source_stake_account" / AccountReference(),
            "clock_sysvar" / AccountReference(),
            "stake_history_sysvar" / AccountReference(),
            "stake_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_AUTHORIZE_WITH_SEED: Accounts(
            "stake_account" / AccountReference(),
            "stake_or_withdraw_authority" / AccountReference(),
            "clock_sysvar" / AccountReference(),
            "lockup_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_INITIALIZE_CHECKED: Accounts(
            "uninitialized_stake_account" / AccountReference(),
            "rent_sysvar" / AccountReference(),
            "stake_authority" / AccountReference(),
            "withdrawal_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_AUTHORIZE_CHECKED: Accounts(
            "stake_account" / AccountReference(),
            "clock_sysvar" / AccountReference(),
            "stake_or_withdraw_authority" / AccountReference(),
            "new_stake_or_withdraw_authority" / AccountReference(),
            "lockup_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_AUTHORIZE_CHECKED_WITH_SEED: Accounts(
            "stake_account" / AccountReference(),
            "stake_or_withdraw_authority" / AccountReference(),
            "clock_sysvar" / AccountReference(),
            "new_stake_or_withdraw_authority" / AccountReference(),
            "lockup_authority" / AccountReference(),
        ),
        StakeProgramInstruction.INS_SET_LOCKUP_CHECKED: Accounts(
            "stake_account" / AccountReference(),
            "lockup_or_withdraw_authority" / AccountReference(),
            "new_lockup_authority" / AccountReference(),
        ),
    },
)
_COMPUTE_BUDGET_PROGRAM_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        ComputeBudgetProgramInstruction.INS_REQUEST_HEAP_FRAME: Accounts(),
        ComputeBudgetProgramInstruction.INS_SET_COMPUTE_UNIT_LIMIT: Accounts(),
        ComputeBudgetProgramInstruction.INS_SET_COMPUTE_UNIT_PRICE: Accounts(),
    },
)
_TOKEN_PROGRAM_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        TokenProgramInstruction.INS_INITIALIZE_ACCOUNT: Accounts(
            "account_to_initialize" / AccountReference(),
            "mint_account" / AccountReference(),
            "owner" / AccountReference(),
            "rent_sysvar" / AccountReference(),
        ),
        TokenProgramInstruction.INS_INITIALIZE_MULTISIG: Accounts(
            "multisig_account" / AccountReference(),
            "rent_sysvar" / AccountReference(),
            "signer_accounts" / AccountReference(),
        ),
        TokenProgramInstruction.INS_TRANSFER: Accounts(
            "source_account" / AccountReference(),
            "destination_account" / AccountReference(),
            "owner" / AccountReference(),
        ),
        TokenProgramInstruction.INS_APPROVE: Accounts(
            "source_account" / AccountReference(),
            "delegate_account" / AccountReference(),
            "owner" / AccountReference(),
        ),
        TokenProgramInstruction.INS_REVOKE: Accounts(
            "source_account" / AccountReference(),
            "owner" / AccountReference(),
        ),
        TokenProgramInstruction.INS_SET_AUTHORITY: Accounts(
            "mint_account" / AccountReference(),
            "current_authority" / AccountReference(),
        ),
        TokenProgramInstruction.INS_MINT_TO: Accounts(
            "mint" / AccountReference(),
            "account_to_mint" / AccountReference(),
            "minting_authority" / AccountReference(),
        ),
        TokenProgramInstruction.INS_BURN: Accounts(
            "account_to_burn_from" / AccountReference(),
            "token_mint" / AccountReference(),
            "owner" / AccountReference(),
        ),
        TokenProgramInstruction.INS_CLOSE_ACCOUNT: Accounts(
            "account_to_close" / AccountReference(),
            "destination_account" / AccountReference(),
            "owner" / AccountReference(),
        ),
        TokenProgramInstruction.INS_FREEZE_ACCOUNT: Accounts(
            "account_to_freeze" / AccountReference(),
            "token_mint" / AccountReference(),
            "freeze_authority" / AccountReference(),
        ),
        TokenProgramInstruction.INS_THAW_ACCOUNT: Accounts(
            "account_to_freeze" / AccountReference(),
            "token_mint" / AccountReference(),
            "freeze_authority" / AccountReference(),
        ),
        TokenProgramInstruction.INS_TRANSFER_CHECKED: Accounts(
            "source_account" / AccountReference(),
            "token_mint" / AccountReference(),
            "destination_account" / AccountReference(),
            "owner" / AccountReference(),
        ),
        TokenProgramInstruction.INS_APPROVE_CHECKED: Accounts(
            "source_account" / AccountReference(),
            "token_mint" / AccountReference(),
            "delegate" / AccountReference(),
            "owner" / AccountReference(),
        ),
        TokenProgramInstruction.INS_MINT_TO_CHECKED: Accounts(
            "mint" / AccountReference(),
            "account_to_mint" / AccountReference(),
            "minting_authority" / AccountReference(),
        ),
        TokenProgramInstruction.INS_BURN_CHECKED: Accounts(
            "account_to_burn_from" / AccountReference(),
            "token_mint" / AccountReference(),
            "owner" / AccountReference(),
        ),
        TokenProgramInstruction.INS_INITIALIZE_ACCOUNT_2: Accounts(
            "account_to_initialize" / AccountReference(),
            "mint_account" / AccountReference(),
            "rent_sysvar" / AccountReference(),
        ),
        TokenProgramInstruction.INS_SYNC_NATIVE: Accounts(
            "token_account" / AccountReference(),
        ),
        TokenProgramInstruction.INS_INITIALIZE_ACCOUNT_3: Accounts(
            "account_to_initialize" / AccountReference(),
            "mint_account" / AccountReference(),
        ),
        TokenProgramInstruction.INS_INITIALIZE_IMMUTABLE_OWNER: Accounts(
            "account_to_initialize" / AccountReference(),
        ),
    },
)
_ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        AssociatedTokenAccountProgramInstruction.INS_CREATE: Accounts(
            "funding_account" / AccountReference(),
            "associated_token_account" / AccountReference(),
            "wallet_address" / AccountReference(),
            "token_mint" / AccountReference(),
            "system_program" / AccountReference(),
            "spl_token" / AccountReference(),
        ),
        AssociatedTokenAccountProgramInstruction.INS_CREATE_IDEMPOTENT: Accounts(
            "funding_account" / AccountReference(),
            "associated_token_account" / AccountReference(),
            "wallet_address" / AccountReference(),
            "token_mint" / AccountReference(),
            "system_program" / AccountReference(),
            "spl_token" / AccountReference(),
        ),
        AssociatedTokenAccountProgramInstruction.INS_RECOVER_NESTED: Accounts(
            "nested_account" / AccountReference(),
            "token_mint_nested" / AccountReference(),
            "associated_token_account" / AccountReference(),
            "owner" / AccountReference(),
            "token_mint_owner" / AccountReference(),
            "wallet_address" / AccountReference(),
            "spl_token" / AccountReference(),
        ),
    },
)
_MEMO_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        MemoInstruction.INS_CREATE: Accounts(
            "signer_accounts" / AccountReference(),
        ),
    },
)
_MEMO_LEGACY_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        MemoLegacyInstruction.INS_CREATE: Accounts(
            "signer_accounts" / AccountReference(),
        ),
    },
)

_SYSTEM_PROGRAM_PARAMETERS = InstructionData(
    "instruction_id" / Int32ul,
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
            SystemProgramInstruction.INS_CREATE_ACCOUNT: Struct(
                "lamports" / Int64ul,
                "space" / Int64ul,
                "owner" / PublicKey(),
            ),
            SystemProgramInstruction.INS_ASSIGN: Struct(
                "owner" / PublicKey(),
            ),
            SystemProgramInstruction.INS_TRANSFER: Struct(
                "lamports" / Int64ul,
            ),
            SystemProgramInstruction.INS_CREATE_ACCOUNT_WITH_SEED: Struct(
                "base" / Int64ul,
                "seed" / _STRING,
                "lamports" / Int64ul,
                "space" / Int64ul,
                "owner" / Int64ul,
            ),
            SystemProgramInstruction.INS_ALLOCATE: Struct(
                "space" / Int64ul,
            ),
            SystemProgramInstruction.INS_ALLOCATE_WITH_SEED: Struct(
                "base" / Int64ul,
                "seed" / _STRING,
                "space" / Int64ul,
                "owner" / Int64ul,
            ),
            SystemProgramInstruction.INS_ASSIGN_WITH_SEED: Struct(
                "base" / Int64ul,
                "seed" / _STRING,
                "owner" / Int64ul,
            ),
        },
    ),
)
_STAKE_PROGRAM_PARAMETERS = InstructionData(
    "instruction_id" / Int32ul,
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
            StakeProgramInstruction.INS_INITIALIZE: Struct(
                "staker" / PublicKey(),
                "withdrawer" / PublicKey(),
                "unix_timestamp" / Int64ul,
                "epoch" / Int64ul,
                "custodian" / PublicKey(),
            ),
            StakeProgramInstruction.INS_AUTHORIZE: Struct(
                "pubkey" / Int64ul,
                "stake_authorize" / Int64ul,
            ),
            StakeProgramInstruction.INS_DELEGATE_STAKE: Struct(),
            StakeProgramInstruction.INS_SPLIT: Struct(
                "lamports" / Int64ul,
            ),
            StakeProgramInstruction.INS_WITHDRAW: Struct(
                "lamports" / Int64ul,
            ),
            StakeProgramInstruction.INS_DEACTIVATE: Struct(),
            StakeProgramInstruction.INS_SET_LOCKUP: Struct(
                "unix_timestamp" / Int64ul,
                "epoch" / Int64ul,
                "custodian" / Int64ul,
            ),
            StakeProgramInstruction.INS_MERGE: Struct(),
            StakeProgramInstruction.INS_AUTHORIZE_WITH_SEED: Struct(
                "new_authorized_pubkey" / Int64ul,
                "stake_authorize" / Int64ul,
                "authority_seed" / _STRING,
                "authority_owner" / Int64ul,
            ),
            StakeProgramInstruction.INS_INITIALIZE_CHECKED: Struct(),
            StakeProgramInstruction.INS_AUTHORIZE_CHECKED: Struct(
                "stake_authorize" / Int64ul,
            ),
            StakeProgramInstruction.INS_AUTHORIZE_CHECKED_WITH_SEED: Struct(
                "stake_authorize" / Int64ul,
                "authority_seed" / _STRING,
                "authority_owner" / Int64ul,
            ),
            StakeProgramInstruction.INS_SET_LOCKUP_CHECKED: Struct(
                "unix_timestamp" / Int64ul,
                "epoch" / Int64ul,
            ),
        },
    ),
)
_COMPUTE_BUDGET_PROGRAM_PARAMETERS = InstructionData(
    "instruction_id" / Int32ul,
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
            ComputeBudgetProgramInstruction.INS_REQUEST_HEAP_FRAME: Struct(
                "bytes" / Int64ul,
            ),
            ComputeBudgetProgramInstruction.INS_SET_COMPUTE_UNIT_LIMIT: Struct(
                "units" / Int64ul,
            ),
            ComputeBudgetProgramInstruction.INS_SET_COMPUTE_UNIT_PRICE: Struct(
                "lamports" / Int64ul,
            ),
        },
    ),
)
_TOKEN_PROGRAM_PARAMETERS = InstructionData(
    "instruction_id" / Int32ul,
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
            TokenProgramInstruction.INS_INITIALIZE_ACCOUNT: Struct(),
            TokenProgramInstruction.INS_INITIALIZE_MULTISIG: Struct(
                "number_of_signers" / Int64ul,
            ),
            TokenProgramInstruction.INS_TRANSFER: Struct(
                "amount" / Int64ul,
            ),
            TokenProgramInstruction.INS_APPROVE: Struct(
                "amount" / Int64ul,
            ),
            TokenProgramInstruction.INS_REVOKE: Struct(),
            TokenProgramInstruction.INS_SET_AUTHORITY: Struct(
                "authority_type" / Int64ul,
                "new_authority" / Int64ul,
            ),
            TokenProgramInstruction.INS_MINT_TO: Struct(
                "amount" / Int64ul,
            ),
            TokenProgramInstruction.INS_BURN: Struct(
                "amount" / Int64ul,
            ),
            TokenProgramInstruction.INS_CLOSE_ACCOUNT: Struct(),
            TokenProgramInstruction.INS_FREEZE_ACCOUNT: Struct(),
            TokenProgramInstruction.INS_THAW_ACCOUNT: Struct(),
            TokenProgramInstruction.INS_TRANSFER_CHECKED: Struct(
                "amount" / Int64ul,
                "decimals" / Int64ul,
            ),
            TokenProgramInstruction.INS_APPROVE_CHECKED: Struct(
                "amount" / Int64ul,
                "decimals" / Int64ul,
            ),
            TokenProgramInstruction.INS_MINT_TO_CHECKED: Struct(
                "amount" / Int64ul,
                "decimals" / Int64ul,
            ),
            TokenProgramInstruction.INS_BURN_CHECKED: Struct(
                "amount" / Int64ul,
                "decimals" / Int64ul,
            ),
            TokenProgramInstruction.INS_INITIALIZE_ACCOUNT_2: Struct(
                "owner" / Int64ul,
            ),
            TokenProgramInstruction.INS_SYNC_NATIVE: Struct(),
            TokenProgramInstruction.INS_INITIALIZE_ACCOUNT_3: Struct(
                "owner" / Int64ul,
            ),
            TokenProgramInstruction.INS_INITIALIZE_IMMUTABLE_OWNER: Struct(),
        },
    ),
)
_ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_PARAMETERS = InstructionData(
    "instruction_id" / Int32ul,
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
            AssociatedTokenAccountProgramInstruction.INS_CREATE: Struct(),
            AssociatedTokenAccountProgramInstruction.INS_CREATE_IDEMPOTENT: Struct(),
            AssociatedTokenAccountProgramInstruction.INS_RECOVER_NESTED: Struct(),
        },
    ),
)
_MEMO_PARAMETERS = InstructionData(
    "instruction_id" / Int32ul,
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
            MemoInstruction.INS_CREATE: Struct(
                "memo" / _STRING,
            ),
        },
    ),
)
_MEMO_LEGACY_PARAMETERS = InstructionData(
    "instruction_id" / Int32ul,
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
            MemoLegacyInstruction.INS_CREATE: Struct(
                "memo" / _STRING,
            ),
        },
    ),
)

_INSTRUCTION = Struct(
    "program_id" / InstructionProgramId(),
    "instruction_accounts"
    / Switch(
        lambda this: this.program_id,
        {
            Program.SYSTEM_PROGRAM_ID: _SYSTEM_PROGRAM_ACCOUNTS,
            Program.STAKE_PROGRAM_ID: _STAKE_PROGRAM_ACCOUNTS,
            Program.COMPUTE_BUDGET_PROGRAM_ID: _COMPUTE_BUDGET_PROGRAM_ACCOUNTS,
            Program.TOKEN_PROGRAM_ID: _TOKEN_PROGRAM_ACCOUNTS,
            Program.ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID: _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ACCOUNTS,
            Program.MEMO_ID: _MEMO_ACCOUNTS,
            Program.MEMO_LEGACY_ID: _MEMO_LEGACY_ACCOUNTS,
        },
    ),
    "data"
    / Switch(
        lambda this: this.program_id,
        {
            Program.SYSTEM_PROGRAM_ID: _SYSTEM_PROGRAM_PARAMETERS,
            Program.STAKE_PROGRAM_ID: _STAKE_PROGRAM_PARAMETERS,
            Program.COMPUTE_BUDGET_PROGRAM_ID: _COMPUTE_BUDGET_PROGRAM_PARAMETERS,
            Program.TOKEN_PROGRAM_ID: _TOKEN_PROGRAM_PARAMETERS,
            Program.ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID: _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_PARAMETERS,
            Program.MEMO_ID: _MEMO_PARAMETERS,
            Program.MEMO_LEGACY_ID: _MEMO_LEGACY_PARAMETERS,
        },
    ),
)


def replace_account_placeholders(construct):
    for ins in construct["instructions"]:
        program_id = Program.__dict__[ins["program_id"]]
        if program_id == Program.SYSTEM_PROGRAM_ID:
            ins["data"]["instruction_id"] = SystemProgramInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value
        elif program_id == Program.STAKE_PROGRAM_ID:
            ins["data"]["instruction_id"] = StakeProgramInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value
        elif program_id == Program.COMPUTE_BUDGET_PROGRAM_ID:
            ins["data"]["instruction_id"] = ComputeBudgetProgramInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value
        elif program_id == Program.TOKEN_PROGRAM_ID:
            ins["data"]["instruction_id"] = TokenProgramInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value
        elif program_id == Program.ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID:
            ins["data"][
                "instruction_id"
            ] = AssociatedTokenAccountProgramInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value
        elif program_id == Program.MEMO_ID:
            ins["data"]["instruction_id"] = MemoInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value
        elif program_id == Program.MEMO_LEGACY_ID:
            ins["data"]["instruction_id"] = MemoLegacyInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value

        ins["program_id"] = program_id

    return construct
