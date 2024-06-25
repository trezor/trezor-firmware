# generated from __init__.py.mako
# do not edit manually!

from enum import Enum

from construct import (
    Byte,
    Const,
    GreedyBytes,
    GreedyRange,
    Int32ul,
    Int64ul,
    Optional,
    Pass,
    Select,
    Struct,
)

from .custom_constructs import (
    CompactArray,
    CompactStruct,
    HexStringAdapter,
    Memo,
    OptionalParameter,
    PublicKey,
    String,
)


class Program(Enum):
    SYSTEM_PROGRAM = "11111111111111111111111111111111"
    STAKE_PROGRAM = "Stake11111111111111111111111111111111111111"
    COMPUTE_BUDGET_PROGRAM = "ComputeBudget111111111111111111111111111111"
    TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
    ASSOCIATED_TOKEN_ACCOUNT_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
    MEMO_PROGRAM = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
    MEMO_LEGACY_PROGRAM = "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"


# System Program begin


class SystemProgramInstruction(Enum):
    CREATE_ACCOUNT = 0
    ASSIGN = 1
    TRANSFER = 2
    CREATE_ACCOUNT_WITH_SEED = 3
    ADVANCE_NONCE_ACCOUNT = 4
    WITHDRAW_NONCE_ACCOUNT = 5
    INITIALIZE_NONCE_ACCOUNT = 6
    AUTHORIZE_NONCE_ACCOUNT = 7
    ALLOCATE = 8
    ALLOCATE_WITH_SEED = 9
    ASSIGN_WITH_SEED = 10
    TRANSFER_WITH_SEED = 11
    UPGRADE_NONCE_ACCOUNT = 12


SystemProgram_CreateAccount = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "new_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(0, Int32ul),
        "lamports" / Int64ul,
        "space" / Int64ul,
        "owner" / PublicKey,
    ),
)

SystemProgram_Assign = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "assigned_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(1, Int32ul),
        "owner" / PublicKey,
    ),
)

SystemProgram_Transfer = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "recipient_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(2, Int32ul),
        "lamports" / Int64ul,
    ),
)

SystemProgram_CreateAccountWithSeed = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "created_account" / Byte,
        "base_account" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(3, Int32ul),
        "base" / PublicKey,
        "seed" / String,
        "lamports" / Int64ul,
        "space" / Int64ul,
        "owner" / PublicKey,
    ),
)

SystemProgram_AdvanceNonceAccount = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
        "recent_blockhashes_sysvar" / Byte,
        "nonce_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(4, Int32ul),
    ),
)

SystemProgram_WithdrawNonceAccount = Struct(
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
        "instruction_id" / Const(5, Int32ul),
        "lamports" / Int64ul,
    ),
)

SystemProgram_InitializeNonceAccount = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
        "recent_blockhashes_sysvar" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(6, Int32ul),
        "nonce_authority" / PublicKey,
    ),
)

SystemProgram_AuthorizeNonceAccount = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
        "nonce_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(7, Int32ul),
        "nonce_authority" / PublicKey,
    ),
)

SystemProgram_Allocate = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "new_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(8, Int32ul),
        "space" / Int64ul,
    ),
)

SystemProgram_AllocateWithSeed = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "allocated_account" / Byte,
        "base_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(9, Int32ul),
        "base" / PublicKey,
        "seed" / String,
        "space" / Int64ul,
        "owner" / PublicKey,
    ),
)

SystemProgram_AssignWithSeed = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "assigned_account" / Byte,
        "base_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(10, Int32ul),
        "base" / PublicKey,
        "seed" / String,
        "owner" / PublicKey,
    ),
)

SystemProgram_TransferWithSeed = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "base_account" / Byte,
        "recipient_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(11, Int32ul),
        "lamports" / Int64ul,
        "from_seed" / String,
        "from_owner" / PublicKey,
    ),
)

SystemProgram_UpgradeNonceAccount = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "nonce_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(12, Int32ul),
    ),
)


SystemProgram_Instruction = Select(
    SystemProgram_CreateAccount,
    SystemProgram_Assign,
    SystemProgram_Transfer,
    SystemProgram_CreateAccountWithSeed,
    SystemProgram_AdvanceNonceAccount,
    SystemProgram_WithdrawNonceAccount,
    SystemProgram_InitializeNonceAccount,
    SystemProgram_AuthorizeNonceAccount,
    SystemProgram_Allocate,
    SystemProgram_AllocateWithSeed,
    SystemProgram_AssignWithSeed,
    SystemProgram_TransferWithSeed,
    SystemProgram_UpgradeNonceAccount,
)

# System Program end

# Stake Program begin


class StakeProgramInstruction(Enum):
    INITIALIZE = 0
    AUTHORIZE = 1
    DELEGATE_STAKE = 2
    SPLIT = 3
    WITHDRAW = 4
    DEACTIVATE = 5
    SET_LOCKUP = 6
    MERGE = 7
    AUTHORIZE_WITH_SEED = 8
    INITIALIZE_CHECKED = 9
    AUTHORIZE_CHECKED = 10
    AUTHORIZE_CHECKED_WITH_SEED = 11
    SET_LOCKUP_CHECKED = 12


StakeProgram_Initialize = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "uninitialized_stake_account" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(0, Int32ul),
        "staker" / PublicKey,
        "withdrawer" / PublicKey,
        "unix_timestamp" / Int64ul,
        "epoch" / Int64ul,
        "custodian" / PublicKey,
    ),
)

StakeProgram_Authorize = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_or_withdraw_authority" / Byte,
        "lockup_authority" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(1, Int32ul),
        "pubkey" / PublicKey,
        "stake_authorize" / Int32ul,
    ),
)

StakeProgram_DelegateStake = Struct(
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
        "instruction_id" / Const(2, Int32ul),
    ),
)

StakeProgram_Split = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "uninitialized_stake_account" / Byte,
        "stake_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(3, Int32ul),
        "lamports" / Int64ul,
    ),
)

StakeProgram_Withdraw = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "recipient_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_history_sysvar" / Byte,
        "withdrawal_authority" / Byte,
        "lockup_authority" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(4, Int32ul),
        "lamports" / Int64ul,
    ),
)

StakeProgram_Deactivate = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "delegated_stake_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(5, Int32ul),
    ),
)

StakeProgram_SetLockup = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "initialized_stake_account" / Byte,
        "lockup_or_withdraw_authority" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(6, Int32ul),
        "unix_timestamp" / OptionalParameter(Int64ul),
        "epoch" / OptionalParameter(Int64ul),
        "custodian" / OptionalParameter(PublicKey),
    ),
)

StakeProgram_Merge = Struct(
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
        "instruction_id" / Const(7, Int32ul),
    ),
)

StakeProgram_AuthorizeWithSeed = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "stake_or_withdraw_authority" / Byte,
        "clock_sysvar" / Byte,
        "lockup_authority" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(8, Int32ul),
        "new_authorized_pubkey" / PublicKey,
        "stake_authorize" / Int32ul,
        "authority_seed" / String,
        "authority_owner" / PublicKey,
    ),
)

StakeProgram_InitializeChecked = Struct(
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
        "instruction_id" / Const(9, Int32ul),
    ),
)

StakeProgram_AuthorizeChecked = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "clock_sysvar" / Byte,
        "stake_or_withdraw_authority" / Byte,
        "new_stake_or_withdraw_authority" / Byte,
        "lockup_authority" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(10, Int32ul),
        "stake_authorize" / Int32ul,
    ),
)

StakeProgram_AuthorizeCheckedWithSeed = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "stake_or_withdraw_authority" / Byte,
        "clock_sysvar" / Byte,
        "new_stake_or_withdraw_authority" / Byte,
        "lockup_authority" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(11, Int32ul),
        "stake_authorize" / Int32ul,
        "authority_seed" / String,
        "authority_owner" / PublicKey,
    ),
)

StakeProgram_SetLockupChecked = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "stake_account" / Byte,
        "lockup_or_withdraw_authority" / Byte,
        "new_lockup_authority" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(12, Int32ul),
        "unix_timestamp" / OptionalParameter(Int64ul),
        "epoch" / OptionalParameter(Int64ul),
    ),
)


StakeProgram_Instruction = Select(
    StakeProgram_Initialize,
    StakeProgram_Authorize,
    StakeProgram_DelegateStake,
    StakeProgram_Split,
    StakeProgram_Withdraw,
    StakeProgram_Deactivate,
    StakeProgram_SetLockup,
    StakeProgram_Merge,
    StakeProgram_AuthorizeWithSeed,
    StakeProgram_InitializeChecked,
    StakeProgram_AuthorizeChecked,
    StakeProgram_AuthorizeCheckedWithSeed,
    StakeProgram_SetLockupChecked,
)

# Stake Program end

# Compute Budget Program begin


class ComputeBudgetProgramInstruction(Enum):
    REQUEST_HEAP_FRAME = 1
    SET_COMPUTE_UNIT_LIMIT = 2
    SET_COMPUTE_UNIT_PRICE = 3


ComputeBudgetProgram_RequestHeapFrame = Struct(
    "program_index" / Byte,
    "accounts" / CompactStruct(),
    "data"
    / CompactStruct(
        "instruction_id" / Const(1, Byte),
        "bytes" / Int32ul,
    ),
)

ComputeBudgetProgram_SetComputeUnitLimit = Struct(
    "program_index" / Byte,
    "accounts" / CompactStruct(),
    "data"
    / CompactStruct(
        "instruction_id" / Const(2, Byte),
        "units" / Int32ul,
    ),
)

ComputeBudgetProgram_SetComputeUnitPrice = Struct(
    "program_index" / Byte,
    "accounts" / CompactStruct(),
    "data"
    / CompactStruct(
        "instruction_id" / Const(3, Byte),
        "lamports" / Int64ul,
    ),
)


ComputeBudgetProgram_Instruction = Select(
    ComputeBudgetProgram_RequestHeapFrame,
    ComputeBudgetProgram_SetComputeUnitLimit,
    ComputeBudgetProgram_SetComputeUnitPrice,
)

# Compute Budget Program end

# Token Program begin


class TokenProgramInstruction(Enum):
    INITIALIZE_ACCOUNT = 1
    INITIALIZE_MULTISIG = 2
    TRANSFER = 3
    APPROVE = 4
    REVOKE = 5
    SET_AUTHORITY = 6
    MINT_TO = 7
    BURN = 8
    CLOSE_ACCOUNT = 9
    FREEZE_ACCOUNT = 10
    THAW_ACCOUNT = 11
    TRANSFER_CHECKED = 12
    APPROVE_CHECKED = 13
    MINT_TO_CHECKED = 14
    BURN_CHECKED = 15
    INITIALIZE_ACCOUNT_2 = 16
    SYNC_NATIVE = 17
    INITIALIZE_ACCOUNT_3 = 18
    INITIALIZE_IMMUTABLE_OWNER = 22


TokenProgram_InitializeAccount = Struct(
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
        "instruction_id" / Const(1, Byte),
    ),
)

TokenProgram_InitializeMultisig = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "multisig_account" / Byte,
        "rent_sysvar" / Byte,
        "signer_accounts" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(2, Byte),
        "number_of_signers" / Byte,
    ),
)

TokenProgram_Transfer = Struct(
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
        "instruction_id" / Const(3, Byte),
        "amount" / Int64ul,
    ),
)

TokenProgram_Approve = Struct(
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
        "instruction_id" / Const(4, Byte),
        "amount" / Int64ul,
    ),
)

TokenProgram_Revoke = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(5, Byte),
    ),
)

TokenProgram_SetAuthority = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "mint_account" / Byte,
        "current_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(6, Byte),
        "authority_type" / Byte,
        "new_authority" / OptionalParameter(PublicKey),
    ),
)

TokenProgram_MintTo = Struct(
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
        "instruction_id" / Const(7, Byte),
        "amount" / Int64ul,
    ),
)

TokenProgram_Burn = Struct(
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
        "instruction_id" / Const(8, Byte),
        "amount" / Int64ul,
    ),
)

TokenProgram_CloseAccount = Struct(
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
        "instruction_id" / Const(9, Byte),
    ),
)

TokenProgram_FreezeAccount = Struct(
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
        "instruction_id" / Const(10, Byte),
    ),
)

TokenProgram_ThawAccount = Struct(
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
        "instruction_id" / Const(11, Byte),
    ),
)

TokenProgram_TransferChecked = Struct(
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
        "instruction_id" / Const(12, Byte),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

TokenProgram_ApproveChecked = Struct(
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
        "instruction_id" / Const(13, Byte),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

TokenProgram_MintToChecked = Struct(
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
        "instruction_id" / Const(14, Byte),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

TokenProgram_BurnChecked = Struct(
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
        "instruction_id" / Const(15, Byte),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

TokenProgram_InitializeAccount2 = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(16, Byte),
        "owner" / PublicKey,
    ),
)

TokenProgram_SyncNative = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "token_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(17, Byte),
    ),
)

TokenProgram_InitializeAccount3 = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(18, Byte),
        "owner" / PublicKey,
    ),
)

TokenProgram_InitializeImmutableOwner = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(22, Byte),
    ),
)


TokenProgram_Instruction = Select(
    TokenProgram_InitializeAccount,
    TokenProgram_InitializeMultisig,
    TokenProgram_Transfer,
    TokenProgram_Approve,
    TokenProgram_Revoke,
    TokenProgram_SetAuthority,
    TokenProgram_MintTo,
    TokenProgram_Burn,
    TokenProgram_CloseAccount,
    TokenProgram_FreezeAccount,
    TokenProgram_ThawAccount,
    TokenProgram_TransferChecked,
    TokenProgram_ApproveChecked,
    TokenProgram_MintToChecked,
    TokenProgram_BurnChecked,
    TokenProgram_InitializeAccount2,
    TokenProgram_SyncNative,
    TokenProgram_InitializeAccount3,
    TokenProgram_InitializeImmutableOwner,
)

# Token Program end

# Token 2022 Program begin


class Token2022ProgramInstruction(Enum):
    INITIALIZE_ACCOUNT = 1
    INITIALIZE_MULTISIG = 2
    TRANSFER = 3
    APPROVE = 4
    REVOKE = 5
    SET_AUTHORITY = 6
    MINT_TO = 7
    BURN = 8
    CLOSE_ACCOUNT = 9
    FREEZE_ACCOUNT = 10
    THAW_ACCOUNT = 11
    TRANSFER_CHECKED = 12
    APPROVE_CHECKED = 13
    MINT_TO_CHECKED = 14
    BURN_CHECKED = 15
    INITIALIZE_ACCOUNT_2 = 16
    SYNC_NATIVE = 17
    INITIALIZE_ACCOUNT_3 = 18
    INITIALIZE_IMMUTABLE_OWNER = 22


Token2022Program_InitializeAccount = Struct(
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
        "instruction_id" / Const(1, Byte),
    ),
)

Token2022Program_InitializeMultisig = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "multisig_account" / Byte,
        "rent_sysvar" / Byte,
        "signer_accounts" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(2, Byte),
        "number_of_signers" / Byte,
    ),
)

Token2022Program_Transfer = Struct(
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
        "instruction_id" / Const(3, Byte),
        "amount" / Int64ul,
    ),
)

Token2022Program_Approve = Struct(
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
        "instruction_id" / Const(4, Byte),
        "amount" / Int64ul,
    ),
)

Token2022Program_Revoke = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "source_account" / Byte,
        "owner" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(5, Byte),
    ),
)

Token2022Program_SetAuthority = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "mint_account" / Byte,
        "current_authority" / Byte,
        "multisig_signers" / Optional(GreedyRange(Byte)),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(6, Byte),
        "authority_type" / Byte,
        "new_authority" / OptionalParameter(PublicKey),
    ),
)

Token2022Program_MintTo = Struct(
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
        "instruction_id" / Const(7, Byte),
        "amount" / Int64ul,
    ),
)

Token2022Program_Burn = Struct(
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
        "instruction_id" / Const(8, Byte),
        "amount" / Int64ul,
    ),
)

Token2022Program_CloseAccount = Struct(
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
        "instruction_id" / Const(9, Byte),
    ),
)

Token2022Program_FreezeAccount = Struct(
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
        "instruction_id" / Const(10, Byte),
    ),
)

Token2022Program_ThawAccount = Struct(
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
        "instruction_id" / Const(11, Byte),
    ),
)

Token2022Program_TransferChecked = Struct(
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
        "instruction_id" / Const(12, Byte),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

Token2022Program_ApproveChecked = Struct(
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
        "instruction_id" / Const(13, Byte),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

Token2022Program_MintToChecked = Struct(
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
        "instruction_id" / Const(14, Byte),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

Token2022Program_BurnChecked = Struct(
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
        "instruction_id" / Const(15, Byte),
        "amount" / Int64ul,
        "decimals" / Byte,
    ),
)

Token2022Program_InitializeAccount2 = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
        "rent_sysvar" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(16, Byte),
        "owner" / PublicKey,
    ),
)

Token2022Program_SyncNative = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "token_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(17, Byte),
    ),
)

Token2022Program_InitializeAccount3 = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
        "mint_account" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(18, Byte),
        "owner" / PublicKey,
    ),
)

Token2022Program_InitializeImmutableOwner = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "account_to_initialize" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(22, Byte),
    ),
)


Token2022Program_Instruction = Select(
    Token2022Program_InitializeAccount,
    Token2022Program_InitializeMultisig,
    Token2022Program_Transfer,
    Token2022Program_Approve,
    Token2022Program_Revoke,
    Token2022Program_SetAuthority,
    Token2022Program_MintTo,
    Token2022Program_Burn,
    Token2022Program_CloseAccount,
    Token2022Program_FreezeAccount,
    Token2022Program_ThawAccount,
    Token2022Program_TransferChecked,
    Token2022Program_ApproveChecked,
    Token2022Program_MintToChecked,
    Token2022Program_BurnChecked,
    Token2022Program_InitializeAccount2,
    Token2022Program_SyncNative,
    Token2022Program_InitializeAccount3,
    Token2022Program_InitializeImmutableOwner,
)

# Token 2022 Program end

# Associated Token Account Program begin


class AssociatedTokenAccountProgramInstruction(Enum):
    CREATE = None
    CREATE_IDEMPOTENT = 1
    RECOVER_NESTED = 2


AssociatedTokenAccountProgram_Create = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "associated_token_account" / Byte,
        "wallet_address" / Byte,
        "token_mint" / Byte,
        "system_program" / Byte,
        "spl_token" / Byte,
        "rent_sysvar" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Pass,
    ),
)

AssociatedTokenAccountProgram_CreateIdempotent = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "funding_account" / Byte,
        "associated_token_account" / Byte,
        "wallet_addr" / Byte,
        "token_mint" / Byte,
        "system_program" / Byte,
        "spl_token" / Byte,
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Const(1, Byte),
    ),
)

AssociatedTokenAccountProgram_RecoverNested = Struct(
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
        "instruction_id" / Const(2, Byte),
    ),
)


AssociatedTokenAccountProgram_Instruction = Select(
    AssociatedTokenAccountProgram_Create,
    AssociatedTokenAccountProgram_CreateIdempotent,
    AssociatedTokenAccountProgram_RecoverNested,
)

# Associated Token Account Program end

# Memo Program begin


class MemoProgramInstruction(Enum):
    MEMO = None


MemoProgram_Memo = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "signer_accounts" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Pass,
        "memo" / Memo,
    ),
)


MemoProgram_Instruction = Select(
    MemoProgram_Memo,
)

# Memo Program end

# Memo Legacy Program begin


class MemoLegacyProgramInstruction(Enum):
    MEMO = None


MemoLegacyProgram_Memo = Struct(
    "program_index" / Byte,
    "accounts"
    / CompactStruct(
        "signer_accounts" / Optional(Byte),
    ),
    "data"
    / CompactStruct(
        "instruction_id" / Pass,
        "memo" / Memo,
    ),
)


MemoLegacyProgram_Instruction = Select(
    MemoLegacyProgram_Memo,
)

# Memo Legacy Program end

PROGRAMS = {
    "11111111111111111111111111111111": SystemProgram_Instruction,
    "Stake11111111111111111111111111111111111111": StakeProgram_Instruction,
    "ComputeBudget111111111111111111111111111111": ComputeBudgetProgram_Instruction,
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": TokenProgram_Instruction,
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb": Token2022Program_Instruction,
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": AssociatedTokenAccountProgram_Instruction,
    "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr": MemoProgram_Instruction,
    "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo": MemoLegacyProgram_Instruction,
}

UnknownInstruction = Struct(
    "program_index" / Byte,
    "accounts" / CompactArray(Byte),
    "data" / HexStringAdapter(GreedyBytes),
)
