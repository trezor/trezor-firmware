# generated from __init__.py.mako
# do not edit manually!
from typing import TYPE_CHECKING

from trezor.wire import ProcessError

from .instruction import Instruction

if TYPE_CHECKING:
    from typing import Any, Type, TypeGuard

    from ..types import Account

SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"
COMPUTE_BUDGET_PROGRAM_ID = "ComputeBudget111111111111111111111111111111"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
MEMO_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
MEMO_LEGACY_ID = "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"

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
MEMO_ID_INS_CREATE = 0
MEMO_LEGACY_ID_INS_CREATE = 0


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
        "MemoCreateInstruction": ("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr", 0),
        "MemoLegacyCreateInstruction": (
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

    class MemoCreateInstruction(Instruction):
        PROGRAM_ID = MEMO_ID
        INSTRUCTION_ID = MEMO_ID_INS_CREATE

        memo: str

        signer_accounts: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["MemoCreateInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class MemoLegacyCreateInstruction(Instruction):
        PROGRAM_ID = MEMO_LEGACY_ID
        INSTRUCTION_ID = MEMO_LEGACY_ID_INS_CREATE

        memo: str

        signer_accounts: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["MemoLegacyCreateInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )


def get_instruction_id_length(program_id: str) -> int:
    if program_id == SYSTEM_PROGRAM_ID:
        return 4
    if program_id == STAKE_PROGRAM_ID:
        return 4
    if program_id == COMPUTE_BUDGET_PROGRAM_ID:
        return 4
    if program_id == TOKEN_PROGRAM_ID:
        return 1
    if program_id == ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID:
        return 1
    if program_id == MEMO_ID:
        return 0
    if program_id == MEMO_LEGACY_ID:
        return 0

    raise ValueError(f"Unknown program id: {program_id}")


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
                    {
                        "name": "lamports",
                        "ui_name": "Lamports",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "space",
                        "ui_name": "Space",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "type": "authority",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "funding_account",
                        "ui_name": "Funding account",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "new_account",
                        "ui_name": "New account",
                        "is_authority": False,
                        "optional": False,
                    },
                ],
                ["lamports", "space", "owner"],
                ["funding_account", "new_account"],
                "ui_confirm",
                "Create Account",
            )
        elif instruction_id == SYSTEM_PROGRAM_ID_INS_ASSIGN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_ASSIGN,
                [
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "type": "authority",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "assigned_account",
                        "ui_name": "Assigned account",
                        "is_authority": True,
                        "optional": False,
                    }
                ],
                ["owner"],
                ["assigned_account"],
                "ui_confirm",
                "Assign",
            )
        elif instruction_id == SYSTEM_PROGRAM_ID_INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_TRANSFER,
                [
                    {
                        "name": "lamports",
                        "ui_name": "Lamports",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "funding_account",
                        "ui_name": "Funding account",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "recipient_account",
                        "ui_name": "Recipient account",
                        "is_authority": False,
                        "optional": False,
                    },
                ],
                ["lamports"],
                ["funding_account", "recipient_account"],
                "ui_confirm",
                "Transfer",
            )
        elif instruction_id == SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED,
                [
                    {
                        "name": "base",
                        "ui_name": "Base",
                        "type": "pubkey",
                        "optional": False,
                    },
                    {
                        "name": "seed",
                        "ui_name": "Seed",
                        "type": "string",
                        "optional": False,
                    },
                    {
                        "name": "lamports",
                        "ui_name": "Lamports",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "space",
                        "ui_name": "Space",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "type": "pubkey",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "funding_account",
                        "ui_name": "Funding account",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "created_account",
                        "ui_name": "Created account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "base_account",
                        "ui_name": "Base account",
                        "is_authority": True,
                        "optional": True,
                    },
                ],
                ["base", "seed", "lamports", "space", "owner"],
                ["funding_account", "created_account", "base_account"],
                "ui_confirm",
                "Create Account With Seed",
            )
        elif instruction_id == SYSTEM_PROGRAM_ID_INS_ALLOCATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_ALLOCATE,
                [
                    {
                        "name": "space",
                        "ui_name": "Space",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "new_account",
                        "ui_name": "New account",
                        "is_authority": True,
                        "optional": False,
                    }
                ],
                ["space"],
                ["new_account"],
                "ui_confirm",
                "Allocate",
            )
        elif instruction_id == SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED,
                [
                    {
                        "name": "base",
                        "ui_name": "Base",
                        "type": "pubkey",
                        "optional": False,
                    },
                    {
                        "name": "seed",
                        "ui_name": "Seed",
                        "type": "string",
                        "optional": False,
                    },
                    {
                        "name": "space",
                        "ui_name": "Space",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "type": "pubkey",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "allocated_account",
                        "ui_name": "Allocated account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "base_account",
                        "ui_name": "Base account",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["base", "seed", "space", "owner"],
                ["allocated_account", "base_account"],
                "ui_confirm",
                "Allocate With Seed",
            )
        elif instruction_id == SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED,
                [
                    {
                        "name": "base",
                        "ui_name": "Base",
                        "type": "pubkey",
                        "optional": False,
                    },
                    {
                        "name": "seed",
                        "ui_name": "Seed",
                        "type": "string",
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "type": "pubkey",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "assigned_account",
                        "ui_name": "Assigned account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "base_account",
                        "ui_name": "Base account",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["base", "seed", "owner"],
                ["assigned_account", "base_account"],
                "ui_confirm",
                "Assign With Seed",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} - {instruction_id}"
            )
    if program_id == STAKE_PROGRAM_ID:
        if instruction_id == STAKE_PROGRAM_ID_INS_INITIALIZE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_INITIALIZE,
                [
                    {
                        "name": "staker",
                        "ui_name": "Staker",
                        "type": "authority",
                        "optional": False,
                    },
                    {
                        "name": "withdrawer",
                        "ui_name": "Withdrawer",
                        "type": "authority",
                        "optional": False,
                    },
                    {
                        "name": "unix_timestamp",
                        "ui_name": "Unix timestamp",
                        "type": "i64",
                        "optional": False,
                    },
                    {
                        "name": "epoch",
                        "ui_name": "Epoch",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "custodian",
                        "ui_name": "Custodian",
                        "type": "authority",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "uninitialized_stake_account",
                        "ui_name": "Uninitialized stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "rent_sysvar",
                        "ui_name": "Rent sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                ],
                ["staker", "withdrawer", "unix_timestamp", "epoch", "custodian"],
                ["uninitialized_stake_account", "rent_sysvar"],
                "ui_confirm",
                "Initialize",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_AUTHORIZE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_AUTHORIZE,
                [
                    {
                        "name": "pubkey",
                        "ui_name": "Pubkey",
                        "type": "pubkey",
                        "optional": False,
                    },
                    {
                        "name": "stake_authorize",
                        "ui_name": "Stake authorize",
                        "type": "StakeAuthorize",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "stake_account",
                        "ui_name": "Stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "clock_sysvar",
                        "ui_name": "Clock sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_or_withdraw_authority",
                        "ui_name": "stake or withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "lockup_authority",
                        "ui_name": "Lockup authority",
                        "is_authority": True,
                        "optional": True,
                    },
                ],
                ["pubkey", "stake_authorize"],
                [
                    "stake_account",
                    "clock_sysvar",
                    "stake_or_withdraw_authority",
                    "lockup_authority",
                ],
                "ui_confirm",
                "Authorize",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_DELEGATE_STAKE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_DELEGATE_STAKE,
                [],
                [
                    {
                        "name": "initialized_stake_account",
                        "ui_name": "Initialized stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "vote_account",
                        "ui_name": "Vote account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "clock_sysvar",
                        "ui_name": "Clock sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_history_sysvar",
                        "ui_name": "Stake history sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "config_account",
                        "ui_name": "Config account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_authority",
                        "ui_name": "Stake authority",
                        "is_authority": True,
                        "optional": False,
                    },
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
                "Delegate Stake",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_SPLIT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_SPLIT,
                [
                    {
                        "name": "lamports",
                        "ui_name": "Lamports",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "stake_account",
                        "ui_name": "Stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "uninitialized_stake_account",
                        "ui_name": "Uninitialized stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_authority",
                        "ui_name": "Stake authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["lamports"],
                ["stake_account", "uninitialized_stake_account", "stake_authority"],
                "ui_confirm",
                "Split",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_WITHDRAW:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_WITHDRAW,
                [
                    {
                        "name": "lamports",
                        "ui_name": "lamports",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "stake_account",
                        "ui_name": "Stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "recipient_account",
                        "ui_name": "Recipient account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "clock_sysvar",
                        "ui_name": "Clock sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_history_sysvar",
                        "ui_name": "Stake history sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "withdrawal_authority",
                        "ui_name": "Withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "lockup_authority",
                        "ui_name": "Lockup authority",
                        "is_authority": True,
                        "optional": True,
                    },
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
                "Withdraw",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_DEACTIVATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_DEACTIVATE,
                [],
                [
                    {
                        "name": "delegated_stake_account",
                        "ui_name": "Delegated stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "clock_sysvar",
                        "ui_name": "Clock sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_authority",
                        "ui_name": "Stake authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                [],
                ["delegated_stake_account", "clock_sysvar", "stake_authority"],
                "ui_confirm",
                "Deactivate",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_SET_LOCKUP:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_SET_LOCKUP,
                [
                    {
                        "name": "unix_timestamp",
                        "ui_name": "Unix timestamp",
                        "type": "i64",
                        "optional": True,
                    },
                    {
                        "name": "epoch",
                        "ui_name": "Epoch",
                        "type": "u64",
                        "optional": True,
                    },
                    {
                        "name": "custodian",
                        "ui_name": "Custodian",
                        "type": "pubkey",
                        "optional": True,
                    },
                ],
                [
                    {
                        "name": "initialized_stake_account",
                        "ui_name": "Initialized stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "lockup_or_withdraw_authority",
                        "ui_name": "Lockup authority or withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["unix_timestamp", "epoch", "custodian"],
                ["initialized_stake_account", "lockup_or_withdraw_authority"],
                "ui_confirm",
                "Set Lockup",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_MERGE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_MERGE,
                [],
                [
                    {
                        "name": "destination_stake_account",
                        "ui_name": "Destination stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "source_stake_account",
                        "ui_name": "Source stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "clock_sysvar",
                        "ui_name": "Clock sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_history_sysvar",
                        "ui_name": "Stake history sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_authority",
                        "ui_name": "Stake authority",
                        "is_authority": True,
                        "optional": False,
                    },
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
                "Merge",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED,
                [
                    {
                        "name": "new_authorized_pubkey",
                        "ui_name": "New authorized pubkey",
                        "type": "pubkey",
                        "optional": False,
                    },
                    {
                        "name": "stake_authorize",
                        "ui_name": "Stake authorize",
                        "type": "StakeAuthorize",
                        "optional": False,
                    },
                    {
                        "name": "authority_seed",
                        "ui_name": "Authority seed",
                        "type": "string",
                        "optional": False,
                    },
                    {
                        "name": "authority_owner",
                        "ui_name": "Authority owner",
                        "type": "pubkey",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "stake_account",
                        "ui_name": "Stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_or_withdraw_authority",
                        "ui_name": "stake or withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "clock_sysvar",
                        "ui_name": "Clock sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "lockup_authority",
                        "ui_name": "Lockup authority",
                        "is_authority": True,
                        "optional": True,
                    },
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
                "Authorize With Seed",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED,
                [],
                [
                    {
                        "name": "uninitialized_stake_account",
                        "ui_name": "Uninitialized stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "rent_sysvar",
                        "ui_name": "Rent sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_authority",
                        "ui_name": "stake authority",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "withdrawal_authority",
                        "ui_name": "withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                [],
                [
                    "uninitialized_stake_account",
                    "rent_sysvar",
                    "stake_authority",
                    "withdrawal_authority",
                ],
                "ui_confirm",
                "Initialize Checked",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED,
                [
                    {
                        "name": "stake_authorize",
                        "ui_name": "Stake authorize",
                        "type": "StakeAuthorize",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "stake_account",
                        "ui_name": "Stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "clock_sysvar",
                        "ui_name": "Clock sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_or_withdraw_authority",
                        "ui_name": "stake or withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "new_stake_or_withdraw_authority",
                        "ui_name": "new stake or withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "lockup_authority",
                        "ui_name": "Lockup authority",
                        "is_authority": True,
                        "optional": True,
                    },
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
                "Authorize Checked",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED,
                [
                    {
                        "name": "stake_authorize",
                        "ui_name": "Stake authorize",
                        "type": "StakeAuthorize",
                        "optional": False,
                    },
                    {
                        "name": "authority_seed",
                        "ui_name": "Authority seed",
                        "type": "string",
                        "optional": False,
                    },
                    {
                        "name": "authority_owner",
                        "ui_name": "Authority owner",
                        "type": "pubkey",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "stake_account",
                        "ui_name": "Stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "stake_or_withdraw_authority",
                        "ui_name": "stake or withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "clock_sysvar",
                        "ui_name": "Clock sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "new_stake_or_withdraw_authority",
                        "ui_name": "new stake or withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "lockup_authority",
                        "ui_name": "Lockup authority",
                        "is_authority": True,
                        "optional": True,
                    },
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
                "Authorize Checked With Seed",
            )
        elif instruction_id == STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED,
                [
                    {
                        "name": "unix_timestamp",
                        "ui_name": "Unix timestamp",
                        "type": "i64",
                        "optional": True,
                    },
                    {
                        "name": "epoch",
                        "ui_name": "Epoch",
                        "type": "u64",
                        "optional": True,
                    },
                ],
                [
                    {
                        "name": "stake_account",
                        "ui_name": "Stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "lockup_or_withdraw_authority",
                        "ui_name": "Lockup authority or withdraw authority",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "new_lockup_authority",
                        "ui_name": "New lockup authority",
                        "is_authority": True,
                        "optional": True,
                    },
                ],
                ["unix_timestamp", "epoch"],
                [
                    "stake_account",
                    "lockup_or_withdraw_authority",
                    "new_lockup_authority",
                ],
                "ui_confirm",
                "Set Lockup Checked",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} - {instruction_id}"
            )
    if program_id == COMPUTE_BUDGET_PROGRAM_ID:
        if instruction_id == COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME,
                [
                    {
                        "name": "bytes",
                        "ui_name": "bytes",
                        "type": "u32",
                        "optional": False,
                    }
                ],
                [],
                ["bytes"],
                [],
                "ui_confirm",
                "Request Heap Frame",
            )
        elif instruction_id == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT,
                [
                    {
                        "name": "units",
                        "ui_name": "units",
                        "type": "u32",
                        "optional": False,
                    }
                ],
                [],
                ["units"],
                [],
                "ui_confirm",
                "Set Compute Unit Limit",
            )
        elif instruction_id == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
                [
                    {
                        "name": "lamports",
                        "ui_name": "lamports",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [],
                ["lamports"],
                [],
                "ui_confirm",
                "Set Compute Unit Price",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} - {instruction_id}"
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
                    {
                        "name": "account_to_initialize",
                        "ui_name": "Account to initialize",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "mint_account",
                        "ui_name": "Mint account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "rent_sysvar",
                        "ui_name": "Rent sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                ],
                [],
                ["account_to_initialize", "mint_account", "owner", "rent_sysvar"],
                "ui_confirm",
                "Initialize Account",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG,
                [
                    {
                        "name": "number_of_signers",
                        "ui_name": "Number of signers",
                        "type": "u8",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "multisig_account",
                        "ui_name": "Multisig account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "rent_sysvar",
                        "ui_name": "Rent sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "signer_accounts",
                        "ui_name": "Signer accounts",
                        "is_authority": False,
                        "optional": False,
                    },
                ],
                ["number_of_signers"],
                ["multisig_account", "rent_sysvar", "signer_accounts"],
                "ui_confirm",
                "Initialize Multisig",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_TRANSFER,
                [
                    {
                        "name": "amount",
                        "ui_name": "Amount",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "source_account",
                        "ui_name": "Source account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "destination_account",
                        "ui_name": "Destination account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["amount"],
                ["source_account", "destination_account", "owner"],
                "ui_confirm",
                "Transfer",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_APPROVE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_APPROVE,
                [
                    {
                        "name": "amount",
                        "ui_name": "Amount",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "source_account",
                        "ui_name": "Source account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "delegate_account",
                        "ui_name": "Delegate account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["amount"],
                ["source_account", "delegate_account", "owner"],
                "ui_confirm",
                "Approve",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_REVOKE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_REVOKE,
                [],
                [
                    {
                        "name": "source_account",
                        "ui_name": "Source account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                [],
                ["source_account", "owner"],
                "ui_confirm",
                "Revoke",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_SET_AUTHORITY:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_SET_AUTHORITY,
                [
                    {
                        "name": "authority_type",
                        "ui_name": "Authority type",
                        "type": "AuthorityType",
                        "optional": False,
                    },
                    {
                        "name": "new_authority",
                        "ui_name": "New authority",
                        "type": "pubkey",
                        "optional": True,
                    },
                ],
                [
                    {
                        "name": "mint_account",
                        "ui_name": "Mint or account to change",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "current_authority",
                        "ui_name": "Current authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["authority_type", "new_authority"],
                ["mint_account", "current_authority"],
                "ui_confirm",
                "Set Authority",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_MINT_TO:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_MINT_TO,
                [
                    {
                        "name": "amount",
                        "ui_name": "Amount",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "mint",
                        "ui_name": "The mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "account_to_mint",
                        "ui_name": "Account to mint tokens to",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "minting_authority",
                        "ui_name": "Minting authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["amount"],
                ["mint", "account_to_mint", "minting_authority"],
                "ui_confirm",
                "Mint to",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_BURN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_BURN,
                [
                    {
                        "name": "amount",
                        "ui_name": "Amount",
                        "type": "u64",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "account_to_burn_from",
                        "ui_name": "Account to burn from",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint",
                        "ui_name": "The token mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["amount"],
                ["account_to_burn_from", "token_mint", "owner"],
                "ui_confirm",
                "Burn",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT,
                [],
                [
                    {
                        "name": "account_to_close",
                        "ui_name": "Account to close",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "destination_account",
                        "ui_name": "Destination account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                [],
                ["account_to_close", "destination_account", "owner"],
                "ui_confirm",
                "Close Account",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT,
                [],
                [
                    {
                        "name": "account_to_freeze",
                        "ui_name": "Account to freeze",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint",
                        "ui_name": "The token mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "freeze_authority",
                        "ui_name": "Freeze authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                [],
                ["account_to_freeze", "token_mint", "freeze_authority"],
                "ui_confirm",
                "Freeze Account",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT,
                [],
                [
                    {
                        "name": "account_to_freeze",
                        "ui_name": "Account to freeze",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint",
                        "ui_name": "The token mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "freeze_authority",
                        "ui_name": "Freeze authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                [],
                ["account_to_freeze", "token_mint", "freeze_authority"],
                "ui_confirm",
                "Thaw Account",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED,
                [
                    {
                        "name": "amount",
                        "ui_name": "Amount",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "decimals",
                        "ui_name": "Decimals",
                        "type": "u8",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "source_account",
                        "ui_name": "Source account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint",
                        "ui_name": "The token mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "destination_account",
                        "ui_name": "Destination account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["amount", "decimals"],
                ["source_account", "token_mint", "destination_account", "owner"],
                "ui_confirm",
                "Transfer Checked",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED,
                [
                    {
                        "name": "amount",
                        "ui_name": "Amount",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "decimals",
                        "ui_name": "Decimals",
                        "type": "u8",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "source_account",
                        "ui_name": "Source account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint",
                        "ui_name": "The token mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "delegate",
                        "ui_name": "The delegate",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["amount", "decimals"],
                ["source_account", "token_mint", "delegate", "owner"],
                "ui_confirm",
                "Approve Checked",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED,
                [
                    {
                        "name": "amount",
                        "ui_name": "Amount",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "decimals",
                        "ui_name": "Decimals",
                        "type": "u8",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "mint",
                        "ui_name": "The mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "account_to_mint",
                        "ui_name": "Account to mint tokens to",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "minting_authority",
                        "ui_name": "Minting authority",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["amount", "decimals"],
                ["mint", "account_to_mint", "minting_authority"],
                "ui_confirm",
                "Mint to Checked",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_BURN_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_BURN_CHECKED,
                [
                    {
                        "name": "amount",
                        "ui_name": "Amount",
                        "type": "u64",
                        "optional": False,
                    },
                    {
                        "name": "decimals",
                        "ui_name": "Decimals",
                        "type": "u8",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "account_to_burn_from",
                        "ui_name": "Account to burn from",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint",
                        "ui_name": "The token mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": True,
                        "optional": False,
                    },
                ],
                ["amount", "decimals"],
                ["account_to_burn_from", "token_mint", "owner"],
                "ui_confirm",
                "Burn Checked",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2,
                [
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "type": "pubkey",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "account_to_initialize",
                        "ui_name": "Account to initialize",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "mint_account",
                        "ui_name": "Mint account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "rent_sysvar",
                        "ui_name": "Rent sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                ],
                ["owner"],
                ["account_to_initialize", "mint_account", "rent_sysvar"],
                "ui_confirm",
                "Initialize Account 2",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_SYNC_NATIVE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_SYNC_NATIVE,
                [],
                [
                    {
                        "name": "token_account",
                        "ui_name": "Native token account",
                        "is_authority": False,
                        "optional": False,
                    }
                ],
                [],
                ["token_account"],
                "ui_confirm",
                "Sync Native",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3,
                [
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "type": "pubkey",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "account_to_initialize",
                        "ui_name": "Account to initialize",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "mint_account",
                        "ui_name": "Mint account",
                        "is_authority": False,
                        "optional": False,
                    },
                ],
                ["owner"],
                ["account_to_initialize", "mint_account"],
                "ui_confirm",
                "Initialize Account 3",
            )
        elif instruction_id == TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER,
                [],
                [
                    {
                        "name": "account_to_initialize",
                        "ui_name": "Account to initialize",
                        "is_authority": False,
                        "optional": False,
                    }
                ],
                [],
                ["account_to_initialize"],
                "ui_confirm",
                "Initialize Immutable Owner",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} - {instruction_id}"
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
                    {
                        "name": "funding_account",
                        "ui_name": "Funding account",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "associated_token_account",
                        "ui_name": "Associated token account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "wallet_address",
                        "ui_name": "Wallet address",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint",
                        "ui_name": "The token mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "system_program",
                        "ui_name": "System program",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "spl_token",
                        "ui_name": "SPL token program",
                        "is_authority": False,
                        "optional": False,
                    },
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
                "Create",
            )
        elif (
            instruction_id == ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT
        ):
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT,
                [],
                [
                    {
                        "name": "funding_account",
                        "ui_name": "Funding account",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "associated_token_account",
                        "ui_name": "Associated token account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "wallet_address",
                        "ui_name": "Wallet address",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint",
                        "ui_name": "The token mint",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "system_program",
                        "ui_name": "System program",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "spl_token",
                        "ui_name": "SPL token program",
                        "is_authority": False,
                        "optional": False,
                    },
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
                "Create Idempotent",
            )
        elif instruction_id == ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED,
                [],
                [
                    {
                        "name": "nested_account",
                        "ui_name": "Nested associated token account",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "token_mint_nested",
                        "ui_name": "Token mint for the nested account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "associated_token_account",
                        "ui_name": "Associated token account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "owner",
                        "ui_name": "Owner",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "token_mint_owner",
                        "ui_name": "Token mint for the owner account",
                        "is_authority": False,
                        "optional": False,
                    },
                    {
                        "name": "wallet_address",
                        "ui_name": "Wallet address",
                        "is_authority": True,
                        "optional": False,
                    },
                    {
                        "name": "spl_token",
                        "ui_name": "SPL token program",
                        "is_authority": False,
                        "optional": False,
                    },
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
                "Recover Nested",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} - {instruction_id}"
            )
    if program_id == MEMO_ID:
        if instruction_id == MEMO_ID_INS_CREATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                MEMO_ID_INS_CREATE,
                [
                    {
                        "name": "memo",
                        "ui_name": "Memo",
                        "type": "memo",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "signer_accounts",
                        "ui_name": "Signer accounts",
                        "is_authority": True,
                        "optional": False,
                    }
                ],
                ["memo"],
                ["signer_accounts"],
                "ui_confirm",
                "Create",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} - {instruction_id}"
            )
    if program_id == MEMO_LEGACY_ID:
        if instruction_id == MEMO_LEGACY_ID_INS_CREATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                MEMO_LEGACY_ID_INS_CREATE,
                [
                    {
                        "name": "memo",
                        "ui_name": "Memo",
                        "type": "memo",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "signer_accounts",
                        "ui_name": "Signer accounts",
                        "is_authority": True,
                        "optional": False,
                    }
                ],
                ["memo"],
                ["signer_accounts"],
                "ui_confirm",
                "Create",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} - {instruction_id}"
            )
    else:
        raise ProcessError(f"Unknown program type: {program_id} - {instruction_id}")
