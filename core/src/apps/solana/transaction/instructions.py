# generated from __init__.py.mako
# do not edit manually!
from typing import TYPE_CHECKING

from ..types import AccountTemplate, InstructionIdFormat, PropertyTemplate
from .instruction import Instruction

if TYPE_CHECKING:
    from typing import Any, Type, TypeGuard

    from ..types import Account

SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"
COMPUTE_BUDGET_PROGRAM_ID = "ComputeBudget111111111111111111111111111111"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
MEMO_LEGACY_PROGRAM_ID = "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"

SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT = 0
SYSTEM_PROGRAM_ID_INS_ASSIGN = 1
SYSTEM_PROGRAM_ID_INS_TRANSFER = 2
SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED = 3
SYSTEM_PROGRAM_ID_INS_ALLOCATE = 8
SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED = 9
SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED = 10
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
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE = 0
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT = 1
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED = 2
MEMO_PROGRAM_ID_INS_MEMO = 0
MEMO_LEGACY_PROGRAM_ID_INS_MEMO = 0


def __getattr__(name: str) -> Type[Instruction]:
    ids = {
        "SystemProgramCreateAccountInstruction": (
            "11111111111111111111111111111111",
            0,
        ),
        "SystemProgramAssignInstruction": ("11111111111111111111111111111111", 1),
        "SystemProgramTransferInstruction": ("11111111111111111111111111111111", 2),
        "SystemProgramCreateAccountWithSeedInstruction": (
            "11111111111111111111111111111111",
            3,
        ),
        "SystemProgramAllocateInstruction": ("11111111111111111111111111111111", 8),
        "SystemProgramAllocateWithSeedInstruction": (
            "11111111111111111111111111111111",
            9,
        ),
        "SystemProgramAssignWithSeedInstruction": (
            "11111111111111111111111111111111",
            10,
        ),
        "StakeProgramInitializeInstruction": (
            "Stake11111111111111111111111111111111111111",
            0,
        ),
        "StakeProgramAuthorizeInstruction": (
            "Stake11111111111111111111111111111111111111",
            1,
        ),
        "StakeProgramDelegateStakeInstruction": (
            "Stake11111111111111111111111111111111111111",
            2,
        ),
        "StakeProgramSplitInstruction": (
            "Stake11111111111111111111111111111111111111",
            3,
        ),
        "StakeProgramWithdrawInstruction": (
            "Stake11111111111111111111111111111111111111",
            4,
        ),
        "StakeProgramDeactivateInstruction": (
            "Stake11111111111111111111111111111111111111",
            5,
        ),
        "StakeProgramSetLockupInstruction": (
            "Stake11111111111111111111111111111111111111",
            6,
        ),
        "StakeProgramMergeInstruction": (
            "Stake11111111111111111111111111111111111111",
            7,
        ),
        "StakeProgramAuthorizeWithSeedInstruction": (
            "Stake11111111111111111111111111111111111111",
            8,
        ),
        "StakeProgramInitializeCheckedInstruction": (
            "Stake11111111111111111111111111111111111111",
            9,
        ),
        "StakeProgramAuthorizeCheckedInstruction": (
            "Stake11111111111111111111111111111111111111",
            10,
        ),
        "StakeProgramAuthorizeCheckedWithSeedInstruction": (
            "Stake11111111111111111111111111111111111111",
            11,
        ),
        "StakeProgramSetLockupCheckedInstruction": (
            "Stake11111111111111111111111111111111111111",
            12,
        ),
        "ComputeBudgetProgramRequestHeapFrameInstruction": (
            "ComputeBudget111111111111111111111111111111",
            1,
        ),
        "ComputeBudgetProgramSetComputeUnitLimitInstruction": (
            "ComputeBudget111111111111111111111111111111",
            2,
        ),
        "ComputeBudgetProgramSetComputeUnitPriceInstruction": (
            "ComputeBudget111111111111111111111111111111",
            3,
        ),
        "TokenProgramInitializeAccountInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            1,
        ),
        "TokenProgramInitializeMultisigInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            2,
        ),
        "TokenProgramTransferInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            3,
        ),
        "TokenProgramApproveInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            4,
        ),
        "TokenProgramRevokeInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            5,
        ),
        "TokenProgramSetAuthorityInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            6,
        ),
        "TokenProgramMinttoInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            7,
        ),
        "TokenProgramBurnInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            8,
        ),
        "TokenProgramCloseAccountInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            9,
        ),
        "TokenProgramFreezeAccountInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            10,
        ),
        "TokenProgramThawAccountInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            11,
        ),
        "TokenProgramTransferCheckedInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            12,
        ),
        "TokenProgramApproveCheckedInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            13,
        ),
        "TokenProgramMinttoCheckedInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            14,
        ),
        "TokenProgramBurnCheckedInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            15,
        ),
        "TokenProgramInitializeAccount2Instruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            16,
        ),
        "TokenProgramSyncNativeInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            17,
        ),
        "TokenProgramInitializeAccount3Instruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            18,
        ),
        "TokenProgramInitializeImmutableOwnerInstruction": (
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            22,
        ),
        "AssociatedTokenAccountProgramCreateInstruction": (
            "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
            0,
        ),
        "AssociatedTokenAccountProgramCreateIdempotentInstruction": (
            "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
            1,
        ),
        "AssociatedTokenAccountProgramRecoverNestedInstruction": (
            "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
            2,
        ),
        "MemoProgramMemoInstruction": (
            "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
            0,
        ),
        "MemoLegacyProgramMemoInstruction": (
            "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo",
            0,
        ),
    }
    id = ids[name]

    class FakeClass(Instruction):
        @classmethod
        def is_type_of(cls, ins: Any):
            return ins.program_id == id[0] and ins.instruction_id == id[1]

    return FakeClass


if TYPE_CHECKING:

    class SystemProgramCreateAccountInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT

        lamports: int
        space: int
        owner: Account

        funding_account: Account
        new_account: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["SystemProgramCreateAccountInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SystemProgramAssignInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = SYSTEM_PROGRAM_ID_INS_ASSIGN

        owner: Account

        assigned_account: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["SystemProgramAssignInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SystemProgramTransferInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = SYSTEM_PROGRAM_ID_INS_TRANSFER

        lamports: int

        funding_account: Account
        recipient_account: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["SystemProgramTransferInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SystemProgramCreateAccountWithSeedInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED

        base: int
        seed: str
        lamports: int
        space: int
        owner: int

        funding_account: Account
        created_account: Account
        base_account: Account | None

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["SystemProgramCreateAccountWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SystemProgramAllocateInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = SYSTEM_PROGRAM_ID_INS_ALLOCATE

        space: int

        new_account: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["SystemProgramAllocateInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SystemProgramAllocateWithSeedInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED

        base: int
        seed: str
        space: int
        owner: int

        allocated_account: Account
        base_account: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["SystemProgramAllocateWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SystemProgramAssignWithSeedInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED

        base: int
        seed: str
        owner: int

        assigned_account: Account
        base_account: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["SystemProgramAssignWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramInitializeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_INITIALIZE

        staker: Account
        withdrawer: Account
        unix_timestamp: int
        epoch: int
        custodian: Account

        uninitialized_stake_account: Account
        rent_sysvar: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["StakeProgramInitializeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramAuthorizeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_AUTHORIZE

        pubkey: int
        stake_authorize: int

        stake_account: Account
        clock_sysvar: Account
        stake_or_withdraw_authority: Account
        lockup_authority: Account | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["StakeProgramAuthorizeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramDelegateStakeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_DELEGATE_STAKE

        initialized_stake_account: Account
        vote_account: Account
        clock_sysvar: Account
        stake_history_sysvar: Account
        config_account: Account
        stake_authority: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["StakeProgramDelegateStakeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramSplitInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_SPLIT

        lamports: int

        stake_account: Account
        uninitialized_stake_account: Account
        stake_authority: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["StakeProgramSplitInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramWithdrawInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_WITHDRAW

        lamports: int

        stake_account: Account
        recipient_account: Account
        clock_sysvar: Account
        stake_history_sysvar: Account
        withdrawal_authority: Account
        lockup_authority: Account | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["StakeProgramWithdrawInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramDeactivateInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_DEACTIVATE

        delegated_stake_account: Account
        clock_sysvar: Account
        stake_authority: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["StakeProgramDeactivateInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramSetLockupInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_SET_LOCKUP

        unix_timestamp: int
        epoch: int
        custodian: int

        initialized_stake_account: Account
        lockup_or_withdraw_authority: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["StakeProgramSetLockupInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramMergeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_MERGE

        destination_stake_account: Account
        source_stake_account: Account
        clock_sysvar: Account
        stake_history_sysvar: Account
        stake_authority: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["StakeProgramMergeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramAuthorizeWithSeedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED

        new_authorized_pubkey: int
        stake_authorize: int
        authority_seed: str
        authority_owner: int

        stake_account: Account
        stake_or_withdraw_authority: Account
        clock_sysvar: Account
        lockup_authority: Account | None

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["StakeProgramAuthorizeWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramInitializeCheckedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED

        uninitialized_stake_account: Account
        rent_sysvar: Account
        stake_authority: Account
        withdrawal_authority: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["StakeProgramInitializeCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramAuthorizeCheckedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED

        stake_authorize: int

        stake_account: Account
        clock_sysvar: Account
        stake_or_withdraw_authority: Account
        new_stake_or_withdraw_authority: Account
        lockup_authority: Account | None

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["StakeProgramAuthorizeCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramAuthorizeCheckedWithSeedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED

        stake_authorize: int
        authority_seed: str
        authority_owner: int

        stake_account: Account
        stake_or_withdraw_authority: Account
        clock_sysvar: Account
        new_stake_or_withdraw_authority: Account
        lockup_authority: Account | None

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["StakeProgramAuthorizeCheckedWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class StakeProgramSetLockupCheckedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED

        unix_timestamp: int
        epoch: int

        stake_account: Account
        lockup_or_withdraw_authority: Account
        new_lockup_authority: Account | None

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["StakeProgramSetLockupCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class ComputeBudgetProgramRequestHeapFrameInstruction(Instruction):
        PROGRAM_ID = COMPUTE_BUDGET_PROGRAM_ID
        INSTRUCTION_ID = COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME

        bytes: int

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["ComputeBudgetProgramRequestHeapFrameInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class ComputeBudgetProgramSetComputeUnitLimitInstruction(Instruction):
        PROGRAM_ID = COMPUTE_BUDGET_PROGRAM_ID
        INSTRUCTION_ID = COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT

        units: int

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["ComputeBudgetProgramSetComputeUnitLimitInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class ComputeBudgetProgramSetComputeUnitPriceInstruction(Instruction):
        PROGRAM_ID = COMPUTE_BUDGET_PROGRAM_ID
        INSTRUCTION_ID = COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE

        lamports: int

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["ComputeBudgetProgramSetComputeUnitPriceInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramInitializeAccountInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT

        account_to_initialize: Account
        mint_account: Account
        owner: Account
        rent_sysvar: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramInitializeAccountInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramInitializeMultisigInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG

        number_of_signers: int

        multisig_account: Account
        rent_sysvar: Account
        signer_accounts: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramInitializeMultisigInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramTransferInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_TRANSFER

        amount: int

        source_account: Account
        destination_account: Account
        owner: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["TokenProgramTransferInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramApproveInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_APPROVE

        amount: int

        source_account: Account
        delegate_account: Account
        owner: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["TokenProgramApproveInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramRevokeInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_REVOKE

        source_account: Account
        owner: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["TokenProgramRevokeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramSetAuthorityInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_SET_AUTHORITY

        authority_type: int
        new_authority: int

        mint_account: Account
        current_authority: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramSetAuthorityInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramMinttoInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_MINT_TO

        amount: int

        mint: Account
        account_to_mint: Account
        minting_authority: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["TokenProgramMinttoInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramBurnInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_BURN

        amount: int

        account_to_burn_from: Account
        token_mint: Account
        owner: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["TokenProgramBurnInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramCloseAccountInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT

        account_to_close: Account
        destination_account: Account
        owner: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramCloseAccountInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramFreezeAccountInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT

        account_to_freeze: Account
        token_mint: Account
        freeze_authority: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramFreezeAccountInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramThawAccountInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT

        account_to_freeze: Account
        token_mint: Account
        freeze_authority: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramThawAccountInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramTransferCheckedInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED

        amount: int
        decimals: int

        source_account: Account
        token_mint: Account
        destination_account: Account
        owner: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramTransferCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramApproveCheckedInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED

        amount: int
        decimals: int

        source_account: Account
        token_mint: Account
        delegate: Account
        owner: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramApproveCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramMinttoCheckedInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED

        amount: int
        decimals: int

        mint: Account
        account_to_mint: Account
        minting_authority: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramMinttoCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramBurnCheckedInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_BURN_CHECKED

        amount: int
        decimals: int

        account_to_burn_from: Account
        token_mint: Account
        owner: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramBurnCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramInitializeAccount2Instruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2

        owner: int

        account_to_initialize: Account
        mint_account: Account
        rent_sysvar: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramInitializeAccount2Instruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramSyncNativeInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_SYNC_NATIVE

        token_account: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["TokenProgramSyncNativeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramInitializeAccount3Instruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3

        owner: int

        account_to_initialize: Account
        mint_account: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramInitializeAccount3Instruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TokenProgramInitializeImmutableOwnerInstruction(Instruction):
        PROGRAM_ID = TOKEN_PROGRAM_ID
        INSTRUCTION_ID = TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER

        account_to_initialize: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["TokenProgramInitializeImmutableOwnerInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AssociatedTokenAccountProgramCreateInstruction(Instruction):
        PROGRAM_ID = ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID
        INSTRUCTION_ID = ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE

        funding_account: Account
        associated_token_account: Account
        wallet_address: Account
        token_mint: Account
        system_program: Account
        spl_token: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["AssociatedTokenAccountProgramCreateInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AssociatedTokenAccountProgramCreateIdempotentInstruction(Instruction):
        PROGRAM_ID = ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID
        INSTRUCTION_ID = ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT

        funding_account: Account
        associated_token_account: Account
        wallet_address: Account
        token_mint: Account
        system_program: Account
        spl_token: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["AssociatedTokenAccountProgramCreateIdempotentInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AssociatedTokenAccountProgramRecoverNestedInstruction(Instruction):
        PROGRAM_ID = ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID
        INSTRUCTION_ID = ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED

        nested_account: Account
        token_mint_nested: Account
        associated_token_account: Account
        owner: Account
        token_mint_owner: Account
        wallet_address: Account
        spl_token: Account

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["AssociatedTokenAccountProgramRecoverNestedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class MemoProgramMemoInstruction(Instruction):
        PROGRAM_ID = MEMO_PROGRAM_ID
        INSTRUCTION_ID = MEMO_PROGRAM_ID_INS_MEMO

        memo: str

        signer_accounts: Account | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["MemoProgramMemoInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class MemoLegacyProgramMemoInstruction(Instruction):
        PROGRAM_ID = MEMO_LEGACY_PROGRAM_ID
        INSTRUCTION_ID = MEMO_LEGACY_PROGRAM_ID_INS_MEMO

        memo: str

        signer_accounts: Account | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["MemoLegacyProgramMemoInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )


def get_instruction_id_length(program_id: str) -> InstructionIdFormat:
    if program_id == SYSTEM_PROGRAM_ID:
        return InstructionIdFormat(4, True)
    if program_id == STAKE_PROGRAM_ID:
        return InstructionIdFormat(4, True)
    if program_id == COMPUTE_BUDGET_PROGRAM_ID:
        return InstructionIdFormat(1, True)
    if program_id == TOKEN_PROGRAM_ID:
        return InstructionIdFormat(1, True)
    if program_id == ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID:
        return InstructionIdFormat(1, False)
    if program_id == MEMO_PROGRAM_ID:
        return InstructionIdFormat(0, False)
    if program_id == MEMO_LEGACY_PROGRAM_ID:
        return InstructionIdFormat(0, False)

    return InstructionIdFormat(0, False)


def get_instruction(
    program_id: str,
    instruction_id: int,
    instruction_accounts: list[Account],
    instruction_data: bytes,
) -> Instruction:
    if program_id == SYSTEM_PROGRAM_ID:
        if instruction_id == SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT,
                [
                    PropertyTemplate(
                        "lamports",
                        "Lamports",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "space",
                        "Space",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "owner",
                        "Owner",
                        "authority",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "funding_account",
                        "Funding account",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "new_account",
                        "New account",
                        False,
                        False,
                    ),
                ],
                ["lamports", "space", "owner"],
                ["funding_account", "new_account"],
                "ui_confirm",
                "System Program: Create Account",
                True,
                True,
                False,
            )
        if instruction_id == SYSTEM_PROGRAM_ID_INS_ASSIGN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_ASSIGN,
                [
                    PropertyTemplate(
                        "owner",
                        "Owner",
                        "authority",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "assigned_account",
                        "Assigned account",
                        True,
                        False,
                    ),
                ],
                ["owner"],
                ["assigned_account"],
                "ui_confirm",
                "System Program: Assign",
                True,
                True,
                False,
            )
        if instruction_id == SYSTEM_PROGRAM_ID_INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_TRANSFER,
                [
                    PropertyTemplate(
                        "lamports",
                        "Lamports",
                        "u64",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "funding_account",
                        "Funding account",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "recipient_account",
                        "Recipient account",
                        False,
                        False,
                    ),
                ],
                ["lamports"],
                ["funding_account", "recipient_account"],
                "ui_confirm",
                "System Program: Transfer",
                True,
                True,
                False,
            )
        if instruction_id == SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED,
                [
                    PropertyTemplate(
                        "base",
                        "Base",
                        "pubkey",
                        False,
                    ),
                    PropertyTemplate(
                        "seed",
                        "Seed",
                        "string",
                        False,
                    ),
                    PropertyTemplate(
                        "lamports",
                        "Lamports",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "space",
                        "Space",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "owner",
                        "Owner",
                        "pubkey",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "funding_account",
                        "Funding account",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "created_account",
                        "Created account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "base_account",
                        "Base account",
                        True,
                        True,
                    ),
                ],
                ["base", "seed", "lamports", "space", "owner"],
                ["funding_account", "created_account", "base_account"],
                "ui_confirm",
                "System Program: Create Account With Seed",
                True,
                True,
                False,
            )
        if instruction_id == SYSTEM_PROGRAM_ID_INS_ALLOCATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_ALLOCATE,
                [
                    PropertyTemplate(
                        "space",
                        "Space",
                        "u64",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "new_account",
                        "New account",
                        True,
                        False,
                    ),
                ],
                ["space"],
                ["new_account"],
                "ui_confirm",
                "System Program: Allocate",
                True,
                True,
                False,
            )
        if instruction_id == SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED,
                [
                    PropertyTemplate(
                        "base",
                        "Base",
                        "pubkey",
                        False,
                    ),
                    PropertyTemplate(
                        "seed",
                        "Seed",
                        "string",
                        False,
                    ),
                    PropertyTemplate(
                        "space",
                        "Space",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "owner",
                        "Owner",
                        "pubkey",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "allocated_account",
                        "Allocated account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "base_account",
                        "Base account",
                        True,
                        False,
                    ),
                ],
                ["base", "seed", "space", "owner"],
                ["allocated_account", "base_account"],
                "ui_confirm",
                "System Program: Allocate With Seed",
                True,
                True,
                False,
            )
        if instruction_id == SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED,
                [
                    PropertyTemplate(
                        "base",
                        "Base",
                        "pubkey",
                        False,
                    ),
                    PropertyTemplate(
                        "seed",
                        "Seed",
                        "string",
                        False,
                    ),
                    PropertyTemplate(
                        "owner",
                        "Owner",
                        "pubkey",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "assigned_account",
                        "Assigned account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "base_account",
                        "Base account",
                        True,
                        False,
                    ),
                ],
                ["base", "seed", "owner"],
                ["assigned_account", "base_account"],
                "ui_confirm",
                "System Program: Assign With Seed",
                True,
                True,
                False,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            [],
            [],
            [],
            [],
            "ui_unsupported_instruction",
            "System Program",
            True,
            False,
            False,
        )
    if program_id == STAKE_PROGRAM_ID:
        if instruction_id == STAKE_PROGRAM_ID_INS_INITIALIZE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_INITIALIZE,
                [
                    PropertyTemplate(
                        "staker",
                        "Staker",
                        "authority",
                        False,
                    ),
                    PropertyTemplate(
                        "withdrawer",
                        "Withdrawer",
                        "authority",
                        False,
                    ),
                    PropertyTemplate(
                        "unix_timestamp",
                        "Unix timestamp",
                        "i64",
                        False,
                    ),
                    PropertyTemplate(
                        "epoch",
                        "Epoch",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "custodian",
                        "Custodian",
                        "authority",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "uninitialized_stake_account",
                        "Uninitialized stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "rent_sysvar",
                        "Rent sysvar",
                        False,
                        False,
                    ),
                ],
                ["staker", "withdrawer", "unix_timestamp", "epoch", "custodian"],
                ["uninitialized_stake_account", "rent_sysvar"],
                "ui_confirm",
                "Stake Program: Initialize",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_AUTHORIZE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_AUTHORIZE,
                [
                    PropertyTemplate(
                        "pubkey",
                        "Pubkey",
                        "pubkey",
                        False,
                    ),
                    PropertyTemplate(
                        "stake_authorize",
                        "Stake authorize",
                        "StakeAuthorize",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "stake_account",
                        "Stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "clock_sysvar",
                        "Clock sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_or_withdraw_authority",
                        "stake or withdraw authority",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "lockup_authority",
                        "Lockup authority",
                        True,
                        True,
                    ),
                ],
                ["pubkey", "stake_authorize"],
                [
                    "stake_account",
                    "clock_sysvar",
                    "stake_or_withdraw_authority",
                    "lockup_authority",
                ],
                "ui_confirm",
                "Stake Program: Authorize",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_DELEGATE_STAKE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_DELEGATE_STAKE,
                [],
                [
                    AccountTemplate(
                        "initialized_stake_account",
                        "Initialized stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "vote_account",
                        "Vote account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "clock_sysvar",
                        "Clock sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_history_sysvar",
                        "Stake history sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "config_account",
                        "Config account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_authority",
                        "Stake authority",
                        True,
                        False,
                    ),
                ],
                [],
                [
                    "initialized_stake_account",
                    "vote_account",
                    "clock_sysvar",
                    "stake_history_sysvar",
                    "config_account",
                    "stake_authority",
                ],
                "ui_confirm",
                "Stake Program: Delegate Stake",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_SPLIT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_SPLIT,
                [
                    PropertyTemplate(
                        "lamports",
                        "Lamports",
                        "u64",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "stake_account",
                        "Stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "uninitialized_stake_account",
                        "Uninitialized stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_authority",
                        "Stake authority",
                        True,
                        False,
                    ),
                ],
                ["lamports"],
                ["stake_account", "uninitialized_stake_account", "stake_authority"],
                "ui_confirm",
                "Stake Program: Split",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_WITHDRAW:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_WITHDRAW,
                [
                    PropertyTemplate(
                        "lamports",
                        "lamports",
                        "u64",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "stake_account",
                        "Stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "recipient_account",
                        "Recipient account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "clock_sysvar",
                        "Clock sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_history_sysvar",
                        "Stake history sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "withdrawal_authority",
                        "Withdraw authority",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "lockup_authority",
                        "Lockup authority",
                        True,
                        True,
                    ),
                ],
                ["lamports"],
                [
                    "stake_account",
                    "recipient_account",
                    "clock_sysvar",
                    "stake_history_sysvar",
                    "withdrawal_authority",
                    "lockup_authority",
                ],
                "ui_confirm",
                "Stake Program: Withdraw",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_DEACTIVATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_DEACTIVATE,
                [],
                [
                    AccountTemplate(
                        "delegated_stake_account",
                        "Delegated stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "clock_sysvar",
                        "Clock sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_authority",
                        "Stake authority",
                        True,
                        False,
                    ),
                ],
                [],
                ["delegated_stake_account", "clock_sysvar", "stake_authority"],
                "ui_confirm",
                "Stake Program: Deactivate",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_SET_LOCKUP:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_SET_LOCKUP,
                [
                    PropertyTemplate(
                        "unix_timestamp",
                        "Unix timestamp",
                        "i64",
                        True,
                    ),
                    PropertyTemplate(
                        "epoch",
                        "Epoch",
                        "u64",
                        True,
                    ),
                    PropertyTemplate(
                        "custodian",
                        "Custodian",
                        "pubkey",
                        True,
                    ),
                ],
                [
                    AccountTemplate(
                        "initialized_stake_account",
                        "Initialized stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "lockup_or_withdraw_authority",
                        "Lockup authority or withdraw authority",
                        True,
                        False,
                    ),
                ],
                ["unix_timestamp", "epoch", "custodian"],
                ["initialized_stake_account", "lockup_or_withdraw_authority"],
                "ui_confirm",
                "Stake Program: Set Lockup",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_MERGE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_MERGE,
                [],
                [
                    AccountTemplate(
                        "destination_stake_account",
                        "Destination stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "source_stake_account",
                        "Source stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "clock_sysvar",
                        "Clock sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_history_sysvar",
                        "Stake history sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_authority",
                        "Stake authority",
                        True,
                        False,
                    ),
                ],
                [],
                [
                    "destination_stake_account",
                    "source_stake_account",
                    "clock_sysvar",
                    "stake_history_sysvar",
                    "stake_authority",
                ],
                "ui_confirm",
                "Stake Program: Merge",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED,
                [
                    PropertyTemplate(
                        "new_authorized_pubkey",
                        "New authorized pubkey",
                        "pubkey",
                        False,
                    ),
                    PropertyTemplate(
                        "stake_authorize",
                        "Stake authorize",
                        "StakeAuthorize",
                        False,
                    ),
                    PropertyTemplate(
                        "authority_seed",
                        "Authority seed",
                        "string",
                        False,
                    ),
                    PropertyTemplate(
                        "authority_owner",
                        "Authority owner",
                        "pubkey",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "stake_account",
                        "Stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_or_withdraw_authority",
                        "stake or withdraw authority",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "clock_sysvar",
                        "Clock sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "lockup_authority",
                        "Lockup authority",
                        True,
                        True,
                    ),
                ],
                [
                    "new_authorized_pubkey",
                    "stake_authorize",
                    "authority_seed",
                    "authority_owner",
                ],
                [
                    "stake_account",
                    "stake_or_withdraw_authority",
                    "clock_sysvar",
                    "lockup_authority",
                ],
                "ui_confirm",
                "Stake Program: Authorize With Seed",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED,
                [],
                [
                    AccountTemplate(
                        "uninitialized_stake_account",
                        "Uninitialized stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "rent_sysvar",
                        "Rent sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_authority",
                        "stake authority",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "withdrawal_authority",
                        "withdraw authority",
                        True,
                        False,
                    ),
                ],
                [],
                [
                    "uninitialized_stake_account",
                    "rent_sysvar",
                    "stake_authority",
                    "withdrawal_authority",
                ],
                "ui_confirm",
                "Stake Program: Initialize Checked",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED,
                [
                    PropertyTemplate(
                        "stake_authorize",
                        "Stake authorize",
                        "StakeAuthorize",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "stake_account",
                        "Stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "clock_sysvar",
                        "Clock sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_or_withdraw_authority",
                        "stake or withdraw authority",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "new_stake_or_withdraw_authority",
                        "new stake or withdraw authority",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "lockup_authority",
                        "Lockup authority",
                        True,
                        True,
                    ),
                ],
                ["stake_authorize"],
                [
                    "stake_account",
                    "clock_sysvar",
                    "stake_or_withdraw_authority",
                    "new_stake_or_withdraw_authority",
                    "lockup_authority",
                ],
                "ui_confirm",
                "Stake Program: Authorize Checked",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED,
                [
                    PropertyTemplate(
                        "stake_authorize",
                        "Stake authorize",
                        "StakeAuthorize",
                        False,
                    ),
                    PropertyTemplate(
                        "authority_seed",
                        "Authority seed",
                        "string",
                        False,
                    ),
                    PropertyTemplate(
                        "authority_owner",
                        "Authority owner",
                        "pubkey",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "stake_account",
                        "Stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "stake_or_withdraw_authority",
                        "stake or withdraw authority",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "clock_sysvar",
                        "Clock sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "new_stake_or_withdraw_authority",
                        "new stake or withdraw authority",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "lockup_authority",
                        "Lockup authority",
                        True,
                        True,
                    ),
                ],
                ["stake_authorize", "authority_seed", "authority_owner"],
                [
                    "stake_account",
                    "stake_or_withdraw_authority",
                    "clock_sysvar",
                    "new_stake_or_withdraw_authority",
                    "lockup_authority",
                ],
                "ui_confirm",
                "Stake Program: Authorize Checked With Seed",
                True,
                True,
                False,
            )
        if instruction_id == STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED,
                [
                    PropertyTemplate(
                        "unix_timestamp",
                        "Unix timestamp",
                        "i64",
                        True,
                    ),
                    PropertyTemplate(
                        "epoch",
                        "Epoch",
                        "u64",
                        True,
                    ),
                ],
                [
                    AccountTemplate(
                        "stake_account",
                        "Stake account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "lockup_or_withdraw_authority",
                        "Lockup authority or withdraw authority",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "new_lockup_authority",
                        "New lockup authority",
                        True,
                        True,
                    ),
                ],
                ["unix_timestamp", "epoch"],
                [
                    "stake_account",
                    "lockup_or_withdraw_authority",
                    "new_lockup_authority",
                ],
                "ui_confirm",
                "Stake Program: Set Lockup Checked",
                True,
                True,
                False,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            [],
            [],
            [],
            [],
            "ui_unsupported_instruction",
            "Stake Program",
            True,
            False,
            False,
        )
    if program_id == COMPUTE_BUDGET_PROGRAM_ID:
        if instruction_id == COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME,
                [
                    PropertyTemplate(
                        "bytes",
                        "bytes",
                        "u32",
                        False,
                    ),
                ],
                [],
                ["bytes"],
                [],
                "ui_confirm",
                "Compute Budget Program: Request Heap Frame",
                True,
                True,
                False,
            )
        if instruction_id == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT,
                [
                    PropertyTemplate(
                        "units",
                        "units",
                        "u32",
                        False,
                    ),
                ],
                [],
                ["units"],
                [],
                "ui_confirm",
                "Compute Budget Program: Set Compute Unit Limit",
                True,
                True,
                False,
            )
        if instruction_id == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
                [
                    PropertyTemplate(
                        "lamports",
                        "lamports",
                        "u64",
                        False,
                    ),
                ],
                [],
                ["lamports"],
                [],
                "ui_confirm",
                "Compute Budget Program: Set Compute Unit Price",
                True,
                True,
                False,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            [],
            [],
            [],
            [],
            "ui_unsupported_instruction",
            "Compute Budget Program",
            True,
            False,
            False,
        )
    if program_id == TOKEN_PROGRAM_ID:
        if instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT,
                [],
                [
                    AccountTemplate(
                        "account_to_initialize",
                        "Account to initialize",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "mint_account",
                        "Mint account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "rent_sysvar",
                        "Rent sysvar",
                        False,
                        False,
                    ),
                ],
                [],
                ["account_to_initialize", "mint_account", "owner", "rent_sysvar"],
                "ui_confirm",
                "Token Program: Initialize Account",
                True,
                True,
                False,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG,
                [
                    PropertyTemplate(
                        "number_of_signers",
                        "Number of signers",
                        "u8",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "multisig_account",
                        "Multisig account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "rent_sysvar",
                        "Rent sysvar",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "signer_accounts",
                        "Signer accounts",
                        False,
                        False,
                    ),
                ],
                ["number_of_signers"],
                ["multisig_account", "rent_sysvar", "signer_accounts"],
                "ui_confirm",
                "Token Program: Initialize Multisig",
                True,
                True,
                False,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_TRANSFER,
                [
                    PropertyTemplate(
                        "amount",
                        "Amount",
                        "u64",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "source_account",
                        "Source account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "destination_account",
                        "Destination account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        True,
                        False,
                    ),
                ],
                ["amount"],
                ["source_account", "destination_account", "owner"],
                "ui_confirm",
                "Token Program: Transfer",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_APPROVE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_APPROVE,
                [
                    PropertyTemplate(
                        "amount",
                        "Amount",
                        "u64",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "source_account",
                        "Source account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "delegate_account",
                        "Delegate account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        True,
                        False,
                    ),
                ],
                ["amount"],
                ["source_account", "delegate_account", "owner"],
                "ui_confirm",
                "Token Program: Approve",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_REVOKE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_REVOKE,
                [],
                [
                    AccountTemplate(
                        "source_account",
                        "Source account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        True,
                        False,
                    ),
                ],
                [],
                ["source_account", "owner"],
                "ui_confirm",
                "Token Program: Revoke",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_SET_AUTHORITY:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_SET_AUTHORITY,
                [
                    PropertyTemplate(
                        "authority_type",
                        "Authority type",
                        "AuthorityType",
                        False,
                    ),
                    PropertyTemplate(
                        "new_authority",
                        "New authority",
                        "pubkey",
                        True,
                    ),
                ],
                [
                    AccountTemplate(
                        "mint_account",
                        "Mint or account to change",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "current_authority",
                        "Current authority",
                        True,
                        False,
                    ),
                ],
                ["authority_type", "new_authority"],
                ["mint_account", "current_authority"],
                "ui_confirm",
                "Token Program: Set Authority",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_MINT_TO:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_MINT_TO,
                [
                    PropertyTemplate(
                        "amount",
                        "Amount",
                        "u64",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "mint",
                        "The mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "account_to_mint",
                        "Account to mint tokens to",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "minting_authority",
                        "Minting authority",
                        True,
                        False,
                    ),
                ],
                ["amount"],
                ["mint", "account_to_mint", "minting_authority"],
                "ui_confirm",
                "Token Program: Mint to",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_BURN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_BURN,
                [
                    PropertyTemplate(
                        "amount",
                        "Amount",
                        "u64",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "account_to_burn_from",
                        "Account to burn from",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint",
                        "The token mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        True,
                        False,
                    ),
                ],
                ["amount"],
                ["account_to_burn_from", "token_mint", "owner"],
                "ui_confirm",
                "Token Program: Burn",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT,
                [],
                [
                    AccountTemplate(
                        "account_to_close",
                        "Account to close",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "destination_account",
                        "Destination account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        True,
                        False,
                    ),
                ],
                [],
                ["account_to_close", "destination_account", "owner"],
                "ui_confirm",
                "Token Program: Close Account",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT,
                [],
                [
                    AccountTemplate(
                        "account_to_freeze",
                        "Account to freeze",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint",
                        "The token mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "freeze_authority",
                        "Freeze authority",
                        True,
                        False,
                    ),
                ],
                [],
                ["account_to_freeze", "token_mint", "freeze_authority"],
                "ui_confirm",
                "Token Program: Freeze Account",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT,
                [],
                [
                    AccountTemplate(
                        "account_to_freeze",
                        "Account to freeze",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint",
                        "The token mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "freeze_authority",
                        "Freeze authority",
                        True,
                        False,
                    ),
                ],
                [],
                ["account_to_freeze", "token_mint", "freeze_authority"],
                "ui_confirm",
                "Token Program: Thaw Account",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED,
                [
                    PropertyTemplate(
                        "amount",
                        "Amount",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "decimals",
                        "Decimals",
                        "u8",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "source_account",
                        "Source account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint",
                        "The token mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "destination_account",
                        "Destination account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        True,
                        False,
                    ),
                ],
                ["amount", "decimals"],
                ["source_account", "token_mint", "destination_account", "owner"],
                "ui_confirm",
                "Token Program: Transfer Checked",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED,
                [
                    PropertyTemplate(
                        "amount",
                        "Amount",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "decimals",
                        "Decimals",
                        "u8",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "source_account",
                        "Source account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint",
                        "The token mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "delegate",
                        "The delegate",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        True,
                        False,
                    ),
                ],
                ["amount", "decimals"],
                ["source_account", "token_mint", "delegate", "owner"],
                "ui_confirm",
                "Token Program: Approve Checked",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED,
                [
                    PropertyTemplate(
                        "amount",
                        "Amount",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "decimals",
                        "Decimals",
                        "u8",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "mint",
                        "The mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "account_to_mint",
                        "Account to mint tokens to",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "minting_authority",
                        "Minting authority",
                        True,
                        False,
                    ),
                ],
                ["amount", "decimals"],
                ["mint", "account_to_mint", "minting_authority"],
                "ui_confirm",
                "Token Program: Mint to Checked",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_BURN_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_BURN_CHECKED,
                [
                    PropertyTemplate(
                        "amount",
                        "Amount",
                        "u64",
                        False,
                    ),
                    PropertyTemplate(
                        "decimals",
                        "Decimals",
                        "u8",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "account_to_burn_from",
                        "Account to burn from",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint",
                        "The token mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        True,
                        False,
                    ),
                ],
                ["amount", "decimals"],
                ["account_to_burn_from", "token_mint", "owner"],
                "ui_confirm",
                "Token Program: Burn Checked",
                True,
                True,
                True,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2,
                [
                    PropertyTemplate(
                        "owner",
                        "Owner",
                        "pubkey",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "account_to_initialize",
                        "Account to initialize",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "mint_account",
                        "Mint account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "rent_sysvar",
                        "Rent sysvar",
                        False,
                        False,
                    ),
                ],
                ["owner"],
                ["account_to_initialize", "mint_account", "rent_sysvar"],
                "ui_confirm",
                "Token Program: Initialize Account 2",
                True,
                True,
                False,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_SYNC_NATIVE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_SYNC_NATIVE,
                [],
                [
                    AccountTemplate(
                        "token_account",
                        "Native token account",
                        False,
                        False,
                    ),
                ],
                [],
                ["token_account"],
                "ui_confirm",
                "Token Program: Sync Native",
                True,
                True,
                False,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3,
                [
                    PropertyTemplate(
                        "owner",
                        "Owner",
                        "pubkey",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "account_to_initialize",
                        "Account to initialize",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "mint_account",
                        "Mint account",
                        False,
                        False,
                    ),
                ],
                ["owner"],
                ["account_to_initialize", "mint_account"],
                "ui_confirm",
                "Token Program: Initialize Account 3",
                True,
                True,
                False,
            )
        if instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER,
                [],
                [
                    AccountTemplate(
                        "account_to_initialize",
                        "Account to initialize",
                        False,
                        False,
                    ),
                ],
                [],
                ["account_to_initialize"],
                "ui_confirm",
                "Token Program: Initialize Immutable Owner",
                True,
                True,
                False,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            [],
            [],
            [],
            [],
            "ui_unsupported_instruction",
            "Token Program",
            True,
            False,
            False,
        )
    if program_id == ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID:
        if instruction_id == ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE,
                [],
                [
                    AccountTemplate(
                        "funding_account",
                        "Funding account",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "associated_token_account",
                        "Associated token account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "wallet_address",
                        "Wallet address",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint",
                        "The token mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "system_program",
                        "System program",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "spl_token",
                        "SPL token program",
                        False,
                        False,
                    ),
                ],
                [],
                [
                    "funding_account",
                    "associated_token_account",
                    "wallet_address",
                    "token_mint",
                    "system_program",
                    "spl_token",
                ],
                "ui_confirm",
                "Associated Token Account Program: Create",
                True,
                True,
                False,
            )
        if instruction_id == ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT,
                [],
                [
                    AccountTemplate(
                        "funding_account",
                        "Funding account",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "associated_token_account",
                        "Associated token account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "wallet_address",
                        "Wallet address",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint",
                        "The token mint",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "system_program",
                        "System program",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "spl_token",
                        "SPL token program",
                        False,
                        False,
                    ),
                ],
                [],
                [
                    "funding_account",
                    "associated_token_account",
                    "wallet_address",
                    "token_mint",
                    "system_program",
                    "spl_token",
                ],
                "ui_confirm",
                "Associated Token Account Program: Create Idempotent",
                True,
                True,
                False,
            )
        if instruction_id == ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED,
                [],
                [
                    AccountTemplate(
                        "nested_account",
                        "Nested associated token account",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint_nested",
                        "Token mint for the nested account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "associated_token_account",
                        "Associated token account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "owner",
                        "Owner",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "token_mint_owner",
                        "Token mint for the owner account",
                        False,
                        False,
                    ),
                    AccountTemplate(
                        "wallet_address",
                        "Wallet address",
                        True,
                        False,
                    ),
                    AccountTemplate(
                        "spl_token",
                        "SPL token program",
                        False,
                        False,
                    ),
                ],
                [],
                [
                    "nested_account",
                    "token_mint_nested",
                    "associated_token_account",
                    "owner",
                    "token_mint_owner",
                    "wallet_address",
                    "spl_token",
                ],
                "ui_confirm",
                "Associated Token Account Program: Recover Nested",
                True,
                True,
                False,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            [],
            [],
            [],
            [],
            "ui_unsupported_instruction",
            "Associated Token Account Program",
            True,
            False,
            False,
        )
    if program_id == MEMO_PROGRAM_ID:
        if instruction_id == MEMO_PROGRAM_ID_INS_MEMO:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                MEMO_PROGRAM_ID_INS_MEMO,
                [
                    PropertyTemplate(
                        "memo",
                        "Memo",
                        "memo",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "signer_accounts",
                        "Signer accounts",
                        True,
                        True,
                    ),
                ],
                ["memo"],
                ["signer_accounts"],
                "ui_confirm",
                "Memo Program: Memo",
                True,
                True,
                False,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            [],
            [],
            [],
            [],
            "ui_unsupported_instruction",
            "Memo Program",
            True,
            False,
            False,
        )
    if program_id == MEMO_LEGACY_PROGRAM_ID:
        if instruction_id == MEMO_LEGACY_PROGRAM_ID_INS_MEMO:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                MEMO_LEGACY_PROGRAM_ID_INS_MEMO,
                [
                    PropertyTemplate(
                        "memo",
                        "Memo",
                        "memo",
                        False,
                    ),
                ],
                [
                    AccountTemplate(
                        "signer_accounts",
                        "Signer accounts",
                        True,
                        True,
                    ),
                ],
                ["memo"],
                ["signer_accounts"],
                "ui_confirm",
                "Memo Legacy Program: Memo",
                True,
                True,
                False,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            [],
            [],
            [],
            [],
            "ui_unsupported_instruction",
            "Memo Legacy Program",
            True,
            False,
            False,
        )
    return Instruction(
        instruction_data,
        program_id,
        instruction_accounts,
        0,
        [],
        [],
        [],
        [],
        "ui_unsupported_program",
        "Unsupported program",
        False,
        False,
        False,
    )
