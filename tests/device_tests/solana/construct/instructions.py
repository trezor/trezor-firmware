# generated from __init__.py.mako
# do not edit manually!

from enum import IntEnum

from construct import (
    Byte,
    GreedyBytes,
    GreedyRange,
    Int32ul,
    Int64ul,
    Optional,
    Struct,
    Switch,
)

from .custom_constructs import (
    CompactArray,
    CompactStruct,
    HexStringAdapter,
    InstructionIdAdapter,
    Memo,
    PublicKey,
    String,
)


class Program:
    SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
    STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"
    COMPUTE_BUDGET_PROGRAM_ID = "ComputeBudget111111111111111111111111111111"
    TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
    ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
    MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
    MEMO_LEGACY_PROGRAM_ID = "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"


INSTRUCTION_ID_FORMATS = {
    Program.SYSTEM_PROGRAM_ID: {"length": 4, "is_included_if_zero": True},
    Program.STAKE_PROGRAM_ID: {"length": 4, "is_included_if_zero": True},
    Program.COMPUTE_BUDGET_PROGRAM_ID: {"length": 1, "is_included_if_zero": True},
    Program.TOKEN_PROGRAM_ID: {"length": 1, "is_included_if_zero": True},
    Program.TOKEN_2022_PROGRAM_ID: {"length": 1, "is_included_if_zero": True},
    Program.ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID: {
        "length": 1,
        "is_included_if_zero": False,
    },
    Program.MEMO_PROGRAM_ID: {"length": 0, "is_included_if_zero": False},
    Program.MEMO_LEGACY_PROGRAM_ID: {"length": 0, "is_included_if_zero": False},
}


# System Program begin


class SystemProgramInstruction(IntEnum):
    INS_CREATE_ACCOUNT = 0
    INS_ASSIGN = 1
    INS_TRANSFER = 2
    INS_CREATE_ACCOUNT_WITH_SEED = 3
    INS_ADVANCE_NONCE_ACCOUNT = 4
    INS_WITHDRAW_NONCE_ACCOUNT = 5
    INS_INITIALIZE_NONCE_ACCOUNT = 6
    INS_AUTHORIZE_NONCE_ACCOUNT = 7
    INS_ALLOCATE = 8
    INS_ALLOCATE_WITH_SEED = 9
    INS_ASSIGN_WITH_SEED = 10
    INS_TRANSFER_WITH_SEED = 11
    INS_UPGRADE_NONCE_ACCOUNT = 12


SystemProgram_CreateAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "new_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "lamports" / Int64ul,
        "space" / Int64ul,
        "owner" / PublicKey,
    ),
)

SystemProgram_Assign_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "assigned_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "owner" / PublicKey,
    ),
)

SystemProgram_Transfer_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "recipient_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "lamports" / Int64ul,
    ),
)

SystemProgram_CreateAccountWithSeed_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "created_account" / Byte,
        "base_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "base" / Int64ul,
        "seed" / String,
        "lamports" / Int64ul,
        "space" / Int64ul,
        "owner" / Int64ul,
    ),
)

SystemProgram_Advancenonceaccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
        "recent_blockhashes_sysvar" / Byte,
        "nonce_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

SystemProgram_Withdrawnonceaccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
        "recipient_account" / Byte,
        "recent_blockhashes_sysvar" / Byte,
        "rent_sysvar" / Byte,
        "nonce_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "lamports" / Int64ul,
    ),
)

SystemProgram_Initializenonceaccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
        "recent_blockhashes_sysvar" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "nonce_authority" / PublicKey,
    ),
)

SystemProgram_Authorizenonceaccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
        "nonce_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "nonce_authority" / PublicKey,
    ),
)

SystemProgram_Allocate_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "new_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "space" / Int64ul,
    ),
)

SystemProgram_AllocateWithSeed_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "allocated_account" / Byte,
        "base_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "base" / Int64ul,
        "seed" / String,
        "space" / Int64ul,
        "owner" / Int64ul,
    ),
)

SystemProgram_AssignWithSeed_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "assigned_account" / Byte,
        "base_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "base" / Int64ul,
        "seed" / String,
        "owner" / Int64ul,
    ),
)

SystemProgram_TransferWithSeed_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "base_account" / Byte,
        "recipient_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "lamports" / Int64ul,
        "from_seed" / String,
        "from_owner" / Int64ul,
    ),
)

SystemProgram_UpgradeNonceAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)


SystemProgram_Instruction = Switch(
    lambda this: this.instruction_id,
    {
        SystemProgramInstruction.INS_CREATE_ACCOUNT: SystemProgram_CreateAccount_Instruction,
        SystemProgramInstruction.INS_ASSIGN: SystemProgram_Assign_Instruction,
        SystemProgramInstruction.INS_TRANSFER: SystemProgram_Transfer_Instruction,
        SystemProgramInstruction.INS_CREATE_ACCOUNT_WITH_SEED: SystemProgram_CreateAccountWithSeed_Instruction,
        SystemProgramInstruction.INS_ADVANCE_NONCE_ACCOUNT: SystemProgram_Advancenonceaccount_Instruction,
        SystemProgramInstruction.INS_WITHDRAW_NONCE_ACCOUNT: SystemProgram_Withdrawnonceaccount_Instruction,
        SystemProgramInstruction.INS_INITIALIZE_NONCE_ACCOUNT: SystemProgram_Initializenonceaccount_Instruction,
        SystemProgramInstruction.INS_AUTHORIZE_NONCE_ACCOUNT: SystemProgram_Authorizenonceaccount_Instruction,
        SystemProgramInstruction.INS_ALLOCATE: SystemProgram_Allocate_Instruction,
        SystemProgramInstruction.INS_ALLOCATE_WITH_SEED: SystemProgram_AllocateWithSeed_Instruction,
        SystemProgramInstruction.INS_ASSIGN_WITH_SEED: SystemProgram_AssignWithSeed_Instruction,
        SystemProgramInstruction.INS_TRANSFER_WITH_SEED: SystemProgram_TransferWithSeed_Instruction,
        SystemProgramInstruction.INS_UPGRADE_NONCE_ACCOUNT: SystemProgram_UpgradeNonceAccount_Instruction,
    },
)

# System Program end

# Stake Program begin


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


StakeProgram_Initialize_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "uninitialized_stake_account" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "staker" / PublicKey,
        "withdrawer" / PublicKey,
        "unix_timestamp" / Int64ul,
        "epoch" / Int64ul,
        "custodian" / PublicKey,
    ),
)

StakeProgram_Authorize_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_or_withdraw_authority" / Byte,
        "lockup_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "pubkey" / Int64ul,
        "stake_authorize" / Int64ul,
    ),
)

StakeProgram_DelegateStake_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "initialized_stake_account" / Byte,
        "vote_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_history_sysvar" / Byte,
        "config_account" / Byte,
        "stake_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

StakeProgram_Split_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "uninitialized_stake_account" / Byte,
        "stake_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "lamports" / Int64ul,
    ),
)

StakeProgram_Withdraw_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "recipient_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_history_sysvar" / Byte,
        "withdrawal_authority" / Byte,
        "lockup_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "lamports" / Int64ul,
    ),
)

StakeProgram_Deactivate_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "delegated_stake_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

StakeProgram_SetLockup_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "initialized_stake_account" / Byte,
        "lockup_or_withdraw_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "unix_timestamp" / Int64ul,
        "epoch" / Int64ul,
        "custodian" / Int64ul,
    ),
)

StakeProgram_Merge_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "destination_stake_account" / Byte,
        "source_stake_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_history_sysvar" / Byte,
        "stake_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

StakeProgram_AuthorizeWithSeed_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "stake_or_withdraw_authority" / Byte,
        "clock_sysvar" / Byte,
        "lockup_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "new_authorized_pubkey" / Int64ul,
        "stake_authorize" / Int64ul,
        "authority_seed" / String,
        "authority_owner" / Int64ul,
    ),
)

StakeProgram_InitializeChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "uninitialized_stake_account" / Byte,
        "rent_sysvar" / Byte,
        "stake_authority" / Byte,
        "withdrawal_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

StakeProgram_AuthorizeChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_or_withdraw_authority" / Byte,
        "new_stake_or_withdraw_authority" / Byte,
        "lockup_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "stake_authorize" / Int64ul,
    ),
)

StakeProgram_AuthorizeCheckedWithSeed_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "stake_or_withdraw_authority" / Byte,
        "clock_sysvar" / Byte,
        "new_stake_or_withdraw_authority" / Byte,
        "lockup_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "stake_authorize" / Int64ul,
        "authority_seed" / String,
        "authority_owner" / Int64ul,
    ),
)

StakeProgram_SetLockupChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "lockup_or_withdraw_authority" / Byte,
        "new_lockup_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "unix_timestamp" / Int64ul,
        "epoch" / Int64ul,
    ),
)


StakeProgram_Instruction = Switch(
    lambda this: this.instruction_id,
    {
        StakeProgramInstruction.INS_INITIALIZE: StakeProgram_Initialize_Instruction,
        StakeProgramInstruction.INS_AUTHORIZE: StakeProgram_Authorize_Instruction,
        StakeProgramInstruction.INS_DELEGATE_STAKE: StakeProgram_DelegateStake_Instruction,
        StakeProgramInstruction.INS_SPLIT: StakeProgram_Split_Instruction,
        StakeProgramInstruction.INS_WITHDRAW: StakeProgram_Withdraw_Instruction,
        StakeProgramInstruction.INS_DEACTIVATE: StakeProgram_Deactivate_Instruction,
        StakeProgramInstruction.INS_SET_LOCKUP: StakeProgram_SetLockup_Instruction,
        StakeProgramInstruction.INS_MERGE: StakeProgram_Merge_Instruction,
        StakeProgramInstruction.INS_AUTHORIZE_WITH_SEED: StakeProgram_AuthorizeWithSeed_Instruction,
        StakeProgramInstruction.INS_INITIALIZE_CHECKED: StakeProgram_InitializeChecked_Instruction,
        StakeProgramInstruction.INS_AUTHORIZE_CHECKED: StakeProgram_AuthorizeChecked_Instruction,
        StakeProgramInstruction.INS_AUTHORIZE_CHECKED_WITH_SEED: StakeProgram_AuthorizeCheckedWithSeed_Instruction,
        StakeProgramInstruction.INS_SET_LOCKUP_CHECKED: StakeProgram_SetLockupChecked_Instruction,
    },
)

# Stake Program end

# Compute Budget Program begin


class ComputeBudgetProgramInstruction(IntEnum):
    INS_REQUEST_HEAP_FRAME = 1
    INS_SET_COMPUTE_UNIT_LIMIT = 2
    INS_SET_COMPUTE_UNIT_PRICE = 3


ComputeBudgetProgram_RequestHeapFrame_Instruction = Struct(
    "program_index" / Byte,
    "accounts" / CompactStruct(),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "bytes" / Int32ul,
    ),
)

ComputeBudgetProgram_SetComputeUnitLimit_Instruction = Struct(
    "program_index" / Byte,
    "accounts" / CompactStruct(),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "units" / Int32ul,
    ),
)

ComputeBudgetProgram_SetComputeUnitPrice_Instruction = Struct(
    "program_index" / Byte,
    "accounts" / CompactStruct(),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "lamports" / Int64ul,
    ),
)


ComputeBudgetProgram_Instruction = Switch(
    lambda this: this.instruction_id,
    {
        ComputeBudgetProgramInstruction.INS_REQUEST_HEAP_FRAME: ComputeBudgetProgram_RequestHeapFrame_Instruction,
        ComputeBudgetProgramInstruction.INS_SET_COMPUTE_UNIT_LIMIT: ComputeBudgetProgram_SetComputeUnitLimit_Instruction,
        ComputeBudgetProgramInstruction.INS_SET_COMPUTE_UNIT_PRICE: ComputeBudgetProgram_SetComputeUnitPrice_Instruction,
    },
)

# Compute Budget Program end

# Token Program begin


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


TokenProgram_InitializeAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
        "owner" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

TokenProgram_InitializeMultisig_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "multisig_account" / Byte,
        "rent_sysvar" / Byte,
        "signer_accounts" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "number_of_signers" / Byte,
    ),
)

TokenProgram_Transfer_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "destination_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
    ),
)

TokenProgram_Approve_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "delegate_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
    ),
)

TokenProgram_Revoke_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

TokenProgram_SetAuthority_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "mint_account" / Byte,
        "current_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "authority_type" / Int64ul,
        "new_authority" / PublicKey,
    ),
)

TokenProgram_Mintto_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "mint" / Byte,
        "account_to_mint" / Byte,
        "minting_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
    ),
)

TokenProgram_Burn_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_burn_from" / Byte,
        "token_mint" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
    ),
)

TokenProgram_CloseAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_close" / Byte,
        "destination_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

TokenProgram_FreezeAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_freeze" / Byte,
        "token_mint" / Byte,
        "freeze_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

TokenProgram_ThawAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_freeze" / Byte,
        "token_mint" / Byte,
        "freeze_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

TokenProgram_TransferChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "token_mint" / Byte,
        "destination_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

TokenProgram_ApproveChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "token_mint" / Byte,
        "delegate" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

TokenProgram_MinttoChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "mint" / Byte,
        "account_to_mint" / Byte,
        "minting_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

TokenProgram_BurnChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_burn_from" / Byte,
        "token_mint" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

TokenProgram_InitializeAccount2_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "owner" / Int64ul,
    ),
)

TokenProgram_SyncNative_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "token_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

TokenProgram_InitializeAccount3_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "owner" / Int64ul,
    ),
)

TokenProgram_InitializeImmutableOwner_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)


TokenProgram_Instruction = Switch(
    lambda this: this.instruction_id,
    {
        TokenProgramInstruction.INS_INITIALIZE_ACCOUNT: TokenProgram_InitializeAccount_Instruction,
        TokenProgramInstruction.INS_INITIALIZE_MULTISIG: TokenProgram_InitializeMultisig_Instruction,
        TokenProgramInstruction.INS_TRANSFER: TokenProgram_Transfer_Instruction,
        TokenProgramInstruction.INS_APPROVE: TokenProgram_Approve_Instruction,
        TokenProgramInstruction.INS_REVOKE: TokenProgram_Revoke_Instruction,
        TokenProgramInstruction.INS_SET_AUTHORITY: TokenProgram_SetAuthority_Instruction,
        TokenProgramInstruction.INS_MINT_TO: TokenProgram_Mintto_Instruction,
        TokenProgramInstruction.INS_BURN: TokenProgram_Burn_Instruction,
        TokenProgramInstruction.INS_CLOSE_ACCOUNT: TokenProgram_CloseAccount_Instruction,
        TokenProgramInstruction.INS_FREEZE_ACCOUNT: TokenProgram_FreezeAccount_Instruction,
        TokenProgramInstruction.INS_THAW_ACCOUNT: TokenProgram_ThawAccount_Instruction,
        TokenProgramInstruction.INS_TRANSFER_CHECKED: TokenProgram_TransferChecked_Instruction,
        TokenProgramInstruction.INS_APPROVE_CHECKED: TokenProgram_ApproveChecked_Instruction,
        TokenProgramInstruction.INS_MINT_TO_CHECKED: TokenProgram_MinttoChecked_Instruction,
        TokenProgramInstruction.INS_BURN_CHECKED: TokenProgram_BurnChecked_Instruction,
        TokenProgramInstruction.INS_INITIALIZE_ACCOUNT_2: TokenProgram_InitializeAccount2_Instruction,
        TokenProgramInstruction.INS_SYNC_NATIVE: TokenProgram_SyncNative_Instruction,
        TokenProgramInstruction.INS_INITIALIZE_ACCOUNT_3: TokenProgram_InitializeAccount3_Instruction,
        TokenProgramInstruction.INS_INITIALIZE_IMMUTABLE_OWNER: TokenProgram_InitializeImmutableOwner_Instruction,
    },
)

# Token Program end

# Token 2022 Program begin


class Token2022ProgramInstruction(IntEnum):
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


Token2022Program_InitializeAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
        "owner" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

Token2022Program_InitializeMultisig_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "multisig_account" / Byte,
        "rent_sysvar" / Byte,
        "signer_accounts" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "number_of_signers" / Byte,
    ),
)

Token2022Program_Transfer_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "destination_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
    ),
)

Token2022Program_Approve_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "delegate_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
    ),
)

Token2022Program_Revoke_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

Token2022Program_SetAuthority_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "mint_account" / Byte,
        "current_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "authority_type" / Int64ul,
        "new_authority" / PublicKey,
    ),
)

Token2022Program_Mintto_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "mint" / Byte,
        "account_to_mint" / Byte,
        "minting_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
    ),
)

Token2022Program_Burn_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_burn_from" / Byte,
        "token_mint" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
    ),
)

Token2022Program_CloseAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_close" / Byte,
        "destination_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

Token2022Program_FreezeAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_freeze" / Byte,
        "token_mint" / Byte,
        "freeze_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

Token2022Program_ThawAccount_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_freeze" / Byte,
        "token_mint" / Byte,
        "freeze_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

Token2022Program_TransferChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "token_mint" / Byte,
        "destination_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

Token2022Program_ApproveChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "token_mint" / Byte,
        "delegate" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

Token2022Program_MinttoChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "mint" / Byte,
        "account_to_mint" / Byte,
        "minting_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

Token2022Program_BurnChecked_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_burn_from" / Byte,
        "token_mint" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

Token2022Program_InitializeAccount2_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "owner" / Int64ul,
    ),
)

Token2022Program_SyncNative_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "token_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

Token2022Program_InitializeAccount3_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "owner" / Int64ul,
    ),
)

Token2022Program_InitializeImmutableOwner_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)


Token2022Program_Instruction = Switch(
    lambda this: this.instruction_id,
    {
        Token2022ProgramInstruction.INS_INITIALIZE_ACCOUNT: Token2022Program_InitializeAccount_Instruction,
        Token2022ProgramInstruction.INS_INITIALIZE_MULTISIG: Token2022Program_InitializeMultisig_Instruction,
        Token2022ProgramInstruction.INS_TRANSFER: Token2022Program_Transfer_Instruction,
        Token2022ProgramInstruction.INS_APPROVE: Token2022Program_Approve_Instruction,
        Token2022ProgramInstruction.INS_REVOKE: Token2022Program_Revoke_Instruction,
        Token2022ProgramInstruction.INS_SET_AUTHORITY: Token2022Program_SetAuthority_Instruction,
        Token2022ProgramInstruction.INS_MINT_TO: Token2022Program_Mintto_Instruction,
        Token2022ProgramInstruction.INS_BURN: Token2022Program_Burn_Instruction,
        Token2022ProgramInstruction.INS_CLOSE_ACCOUNT: Token2022Program_CloseAccount_Instruction,
        Token2022ProgramInstruction.INS_FREEZE_ACCOUNT: Token2022Program_FreezeAccount_Instruction,
        Token2022ProgramInstruction.INS_THAW_ACCOUNT: Token2022Program_ThawAccount_Instruction,
        Token2022ProgramInstruction.INS_TRANSFER_CHECKED: Token2022Program_TransferChecked_Instruction,
        Token2022ProgramInstruction.INS_APPROVE_CHECKED: Token2022Program_ApproveChecked_Instruction,
        Token2022ProgramInstruction.INS_MINT_TO_CHECKED: Token2022Program_MinttoChecked_Instruction,
        Token2022ProgramInstruction.INS_BURN_CHECKED: Token2022Program_BurnChecked_Instruction,
        Token2022ProgramInstruction.INS_INITIALIZE_ACCOUNT_2: Token2022Program_InitializeAccount2_Instruction,
        Token2022ProgramInstruction.INS_SYNC_NATIVE: Token2022Program_SyncNative_Instruction,
        Token2022ProgramInstruction.INS_INITIALIZE_ACCOUNT_3: Token2022Program_InitializeAccount3_Instruction,
        Token2022ProgramInstruction.INS_INITIALIZE_IMMUTABLE_OWNER: Token2022Program_InitializeImmutableOwner_Instruction,
    },
)

# Token 2022 Program end

# Associated Token Account Program begin


class AssociatedTokenAccountProgramInstruction(IntEnum):
    INS_CREATE = 0
    INS_CREATE_IDEMPOTENT = 1
    INS_RECOVER_NESTED = 2


AssociatedTokenAccountProgram_Create_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "associated_token_account" / Byte,
        "wallet_address" / Byte,
        "token_mint" / Byte,
        "system_program" / Byte,
        "spl_token" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

AssociatedTokenAccountProgram_CreateIdempotent_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "associated_token_account" / Byte,
        "wallet_address" / Byte,
        "token_mint" / Byte,
        "system_program" / Byte,
        "spl_token" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)

AssociatedTokenAccountProgram_RecoverNested_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nested_account" / Byte,
        "token_mint_nested" / Byte,
        "associated_token_account" / Byte,
        "owner" / Byte,
        "token_mint_owner" / Byte,
        "wallet_address" / Byte,
        "spl_token" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
    ),
)


AssociatedTokenAccountProgram_Instruction = Switch(
    lambda this: this.instruction_id,
    {
        AssociatedTokenAccountProgramInstruction.INS_CREATE: AssociatedTokenAccountProgram_Create_Instruction,
        AssociatedTokenAccountProgramInstruction.INS_CREATE_IDEMPOTENT: AssociatedTokenAccountProgram_CreateIdempotent_Instruction,
        AssociatedTokenAccountProgramInstruction.INS_RECOVER_NESTED: AssociatedTokenAccountProgram_RecoverNested_Instruction,
    },
)

# Associated Token Account Program end

# Memo Program begin


class MemoProgramInstruction(IntEnum):
    INS_MEMO = 0


MemoProgram_Memo_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "signer_accounts" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "memo" / Memo,
    ),
)


MemoProgram_Instruction = Switch(
    lambda this: this.instruction_id,
    {
        MemoProgramInstruction.INS_MEMO: MemoProgram_Memo_Instruction,
    },
)

# Memo Program end

# Memo Legacy Program begin


class MemoLegacyProgramInstruction(IntEnum):
    INS_MEMO = 0


MemoLegacyProgram_Memo_Instruction = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "signer_accounts" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / InstructionIdAdapter(GreedyBytes),
        "memo" / Memo,
    ),
)


MemoLegacyProgram_Instruction = Switch(
    lambda this: this.instruction_id,
    {
        MemoLegacyProgramInstruction.INS_MEMO: MemoLegacyProgram_Memo_Instruction,
    },
)

# Memo Legacy Program end

Instruction = Switch(
    lambda this: this.program_id,
    {
        Program.SYSTEM_PROGRAM_ID: SystemProgram_Instruction,
        Program.STAKE_PROGRAM_ID: StakeProgram_Instruction,
        Program.COMPUTE_BUDGET_PROGRAM_ID: ComputeBudgetProgram_Instruction,
        Program.TOKEN_PROGRAM_ID: TokenProgram_Instruction,
        Program.TOKEN_2022_PROGRAM_ID: Token2022Program_Instruction,
        Program.ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID: AssociatedTokenAccountProgram_Instruction,
        Program.MEMO_PROGRAM_ID: MemoProgram_Instruction,
        Program.MEMO_LEGACY_PROGRAM_ID: MemoLegacyProgram_Instruction,
    },
    # unknown instruction
    Struct(
        "program_index" / Byte,
        "accounts" / CompactArray(Byte),
        "data" / HexStringAdapter(GreedyBytes),
    ),
)
