# generated from instructions.py.mako
# (by running `make solana_templates` in root)
# do not edit manually!

from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import DataError

from apps.common.readers import read_uint32_le, read_uint64_le

from ..format import (
    format_identity,
    format_int,
    format_lamports,
    format_pubkey,
    format_token_amount,
    format_unix_timestamp,
)
from ..types import PropertyTemplate, UIProperty
from .instruction import Instruction
from .parse import parse_byte, parse_memo, parse_pubkey, parse_string

if TYPE_CHECKING:
    from typing import Any, Type, TypeGuard

    from ..types import Account, InstructionData, InstructionId

_SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
_STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"
_COMPUTE_BUDGET_PROGRAM_ID = "ComputeBudget111111111111111111111111111111"
_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
_TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
_ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
_MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
_MEMO_LEGACY_PROGRAM_ID = "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"

_SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT = const(0)
_SYSTEM_PROGRAM_ID_INS_ASSIGN = const(1)
_SYSTEM_PROGRAM_ID_INS_TRANSFER = const(2)
_SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED = const(3)
_SYSTEM_PROGRAM_ID_INS_ADVANCE_NONCE_ACCOUNT = const(4)
_SYSTEM_PROGRAM_ID_INS_WITHDRAW_NONCE_ACCOUNT = const(5)
_SYSTEM_PROGRAM_ID_INS_INITIALIZE_NONCE_ACCOUNT = const(6)
_SYSTEM_PROGRAM_ID_INS_AUTHORIZE_NONCE_ACCOUNT = const(7)
_SYSTEM_PROGRAM_ID_INS_ALLOCATE = const(8)
_SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED = const(9)
_SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED = const(10)
_SYSTEM_PROGRAM_ID_INS_TRANSFER_WITH_SEED = const(11)
_SYSTEM_PROGRAM_ID_INS_UPGRADE_NONCE_ACCOUNT = const(12)
_STAKE_PROGRAM_ID_INS_INITIALIZE = const(0)
_STAKE_PROGRAM_ID_INS_AUTHORIZE = const(1)
_STAKE_PROGRAM_ID_INS_DELEGATE_STAKE = const(2)
_STAKE_PROGRAM_ID_INS_SPLIT = const(3)
_STAKE_PROGRAM_ID_INS_WITHDRAW = const(4)
_STAKE_PROGRAM_ID_INS_DEACTIVATE = const(5)
_STAKE_PROGRAM_ID_INS_SET_LOCKUP = const(6)
_STAKE_PROGRAM_ID_INS_MERGE = const(7)
_STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED = const(8)
_STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED = const(9)
_STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED = const(10)
_STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED = const(11)
_STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED = const(12)
_COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME = const(1)
_COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT = const(2)
_COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE = const(3)
_TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT = const(1)
_TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG = const(2)
_TOKEN_PROGRAM_ID_INS_TRANSFER = const(3)
_TOKEN_PROGRAM_ID_INS_APPROVE = const(4)
_TOKEN_PROGRAM_ID_INS_REVOKE = const(5)
_TOKEN_PROGRAM_ID_INS_SET_AUTHORITY = const(6)
_TOKEN_PROGRAM_ID_INS_MINT_TO = const(7)
_TOKEN_PROGRAM_ID_INS_BURN = const(8)
_TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT = const(9)
_TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT = const(10)
_TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT = const(11)
_TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED = const(12)
_TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED = const(13)
_TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED = const(14)
_TOKEN_PROGRAM_ID_INS_BURN_CHECKED = const(15)
_TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2 = const(16)
_TOKEN_PROGRAM_ID_INS_SYNC_NATIVE = const(17)
_TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3 = const(18)
_TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER = const(22)
_TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT = const(1)
_TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_MULTISIG = const(2)
_TOKEN_2022_PROGRAM_ID_INS_TRANSFER = const(3)
_TOKEN_2022_PROGRAM_ID_INS_APPROVE = const(4)
_TOKEN_2022_PROGRAM_ID_INS_REVOKE = const(5)
_TOKEN_2022_PROGRAM_ID_INS_SET_AUTHORITY = const(6)
_TOKEN_2022_PROGRAM_ID_INS_MINT_TO = const(7)
_TOKEN_2022_PROGRAM_ID_INS_BURN = const(8)
_TOKEN_2022_PROGRAM_ID_INS_CLOSE_ACCOUNT = const(9)
_TOKEN_2022_PROGRAM_ID_INS_FREEZE_ACCOUNT = const(10)
_TOKEN_2022_PROGRAM_ID_INS_THAW_ACCOUNT = const(11)
_TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED = const(12)
_TOKEN_2022_PROGRAM_ID_INS_APPROVE_CHECKED = const(13)
_TOKEN_2022_PROGRAM_ID_INS_MINT_TO_CHECKED = const(14)
_TOKEN_2022_PROGRAM_ID_INS_BURN_CHECKED = const(15)
_TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2 = const(16)
_TOKEN_2022_PROGRAM_ID_INS_SYNC_NATIVE = const(17)
_TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3 = const(18)
_TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER = const(22)
_ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE = None
_ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT = const(1)
_ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED = const(2)
_MEMO_PROGRAM_ID_INS_MEMO = None
_MEMO_LEGACY_PROGRAM_ID_INS_MEMO = None

COMPUTE_BUDGET_PROGRAM_ID = _COMPUTE_BUDGET_PROGRAM_ID
COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT = (
    _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT
)
COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE = (
    _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE
)


def is_system_program_account_creation(instruction: Instruction) -> bool:
    return (
        instruction.program_id == _SYSTEM_PROGRAM_ID
        and instruction.instruction_id
        in (
            _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT,
            _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED,
            _SYSTEM_PROGRAM_ID_INS_ALLOCATE,
            _SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED,
        )
    )


def is_atap_account_creation(instruction: Instruction) -> bool:
    return (
        instruction.program_id == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID
        and instruction.instruction_id
        in (
            _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE,
            _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT,
        )
    )


def __getattr__(name: str) -> Type[Instruction]:
    def get_id(name: str) -> tuple[str, InstructionId]:
        if name == "SystemProgramCreateAccountInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT)
        if name == "SystemProgramAssignInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_ASSIGN)
        if name == "SystemProgramTransferInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_TRANSFER)
        if name == "SystemProgramCreateAccountWithSeedInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED)
        if name == "SystemProgramAdvanceNonceAccountInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_ADVANCE_NONCE_ACCOUNT)
        if name == "SystemProgramWithdrawNonceAccountInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_WITHDRAW_NONCE_ACCOUNT)
        if name == "SystemProgramInitializeNonceAccountInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_INITIALIZE_NONCE_ACCOUNT)
        if name == "SystemProgramAuthorizeNonceAccountInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_AUTHORIZE_NONCE_ACCOUNT)
        if name == "SystemProgramAllocateInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_ALLOCATE)
        if name == "SystemProgramAllocateWithSeedInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED)
        if name == "SystemProgramAssignWithSeedInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED)
        if name == "SystemProgramTransferWithSeedInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_TRANSFER_WITH_SEED)
        if name == "SystemProgramUpgradeNonceAccountInstruction":
            return (_SYSTEM_PROGRAM_ID, _SYSTEM_PROGRAM_ID_INS_UPGRADE_NONCE_ACCOUNT)
        if name == "StakeProgramInitializeInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_INITIALIZE)
        if name == "StakeProgramAuthorizeInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_AUTHORIZE)
        if name == "StakeProgramDelegateStakeInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_DELEGATE_STAKE)
        if name == "StakeProgramSplitInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_SPLIT)
        if name == "StakeProgramWithdrawInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_WITHDRAW)
        if name == "StakeProgramDeactivateInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_DEACTIVATE)
        if name == "StakeProgramSetLockupInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_SET_LOCKUP)
        if name == "StakeProgramMergeInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_MERGE)
        if name == "StakeProgramAuthorizeWithSeedInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED)
        if name == "StakeProgramInitializeCheckedInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED)
        if name == "StakeProgramAuthorizeCheckedInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED)
        if name == "StakeProgramAuthorizeCheckedWithSeedInstruction":
            return (
                _STAKE_PROGRAM_ID,
                _STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED,
            )
        if name == "StakeProgramSetLockupCheckedInstruction":
            return (_STAKE_PROGRAM_ID, _STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED)
        if name == "ComputeBudgetProgramRequestHeapFrameInstruction":
            return (
                _COMPUTE_BUDGET_PROGRAM_ID,
                _COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME,
            )
        if name == "ComputeBudgetProgramSetComputeUnitLimitInstruction":
            return (
                _COMPUTE_BUDGET_PROGRAM_ID,
                _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT,
            )
        if name == "ComputeBudgetProgramSetComputeUnitPriceInstruction":
            return (
                _COMPUTE_BUDGET_PROGRAM_ID,
                _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
            )
        if name == "TokenProgramInitializeAccountInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT)
        if name == "TokenProgramInitializeMultisigInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG)
        if name == "TokenProgramTransferInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_TRANSFER)
        if name == "TokenProgramApproveInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_APPROVE)
        if name == "TokenProgramRevokeInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_REVOKE)
        if name == "TokenProgramSetAuthorityInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_SET_AUTHORITY)
        if name == "TokenProgramMintToInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_MINT_TO)
        if name == "TokenProgramBurnInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_BURN)
        if name == "TokenProgramCloseAccountInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT)
        if name == "TokenProgramFreezeAccountInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT)
        if name == "TokenProgramThawAccountInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT)
        if name == "TokenProgramTransferCheckedInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED)
        if name == "TokenProgramApproveCheckedInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED)
        if name == "TokenProgramMinttoCheckedInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED)
        if name == "TokenProgramBurnCheckedInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_BURN_CHECKED)
        if name == "TokenProgramInitializeAccount2Instruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2)
        if name == "TokenProgramSyncNativeInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_SYNC_NATIVE)
        if name == "TokenProgramInitializeAccount3Instruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3)
        if name == "TokenProgramInitializeImmutableOwnerInstruction":
            return (_TOKEN_PROGRAM_ID, _TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER)
        if name == "Token2022ProgramInitializeAccountInstruction":
            return (
                _TOKEN_2022_PROGRAM_ID,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT,
            )
        if name == "Token2022ProgramInitializeMultisigInstruction":
            return (
                _TOKEN_2022_PROGRAM_ID,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_MULTISIG,
            )
        if name == "Token2022ProgramTransferInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_TRANSFER)
        if name == "Token2022ProgramApproveInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_APPROVE)
        if name == "Token2022ProgramRevokeInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_REVOKE)
        if name == "Token2022ProgramSetAuthorityInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_SET_AUTHORITY)
        if name == "Token2022ProgramMinttoInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_MINT_TO)
        if name == "Token2022ProgramBurnInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_BURN)
        if name == "Token2022ProgramCloseAccountInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_CLOSE_ACCOUNT)
        if name == "Token2022ProgramFreezeAccountInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_FREEZE_ACCOUNT)
        if name == "Token2022ProgramThawAccountInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_THAW_ACCOUNT)
        if name == "Token2022ProgramTransferCheckedInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED)
        if name == "Token2022ProgramApproveCheckedInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_APPROVE_CHECKED)
        if name == "Token2022ProgramMinttoCheckedInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_MINT_TO_CHECKED)
        if name == "Token2022ProgramBurnCheckedInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_BURN_CHECKED)
        if name == "Token2022ProgramInitializeAccount2Instruction":
            return (
                _TOKEN_2022_PROGRAM_ID,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2,
            )
        if name == "Token2022ProgramSyncNativeInstruction":
            return (_TOKEN_2022_PROGRAM_ID, _TOKEN_2022_PROGRAM_ID_INS_SYNC_NATIVE)
        if name == "Token2022ProgramInitializeAccount3Instruction":
            return (
                _TOKEN_2022_PROGRAM_ID,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3,
            )
        if name == "Token2022ProgramInitializeImmutableOwnerInstruction":
            return (
                _TOKEN_2022_PROGRAM_ID,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER,
            )
        if name == "AssociatedTokenAccountProgramCreateInstruction":
            return (
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE,
            )
        if name == "AssociatedTokenAccountProgramCreateIdempotentInstruction":
            return (
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT,
            )
        if name == "AssociatedTokenAccountProgramRecoverNestedInstruction":
            return (
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED,
            )
        if name == "MemoProgramMemoInstruction":
            return (_MEMO_PROGRAM_ID, _MEMO_PROGRAM_ID_INS_MEMO)
        if name == "MemoLegacyProgramMemoInstruction":
            return (_MEMO_LEGACY_PROGRAM_ID, _MEMO_LEGACY_PROGRAM_ID_INS_MEMO)
        raise AttributeError  # Unknown instruction

    id = get_id(name)

    class FakeClass(Instruction):
        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard[Instruction]:
            return ins.program_id == id[0] and ins.instruction_id == id[1]

    return FakeClass


if TYPE_CHECKING:

    class SystemProgramCreateAccountInstruction(Instruction):
        lamports: int
        space: int
        owner: Account

        funding_account: Account
        new_account: Account

    class SystemProgramAssignInstruction(Instruction):
        owner: Account

        assigned_account: Account

    class SystemProgramTransferInstruction(Instruction):
        lamports: int

        funding_account: Account
        recipient_account: Account

    class SystemProgramCreateAccountWithSeedInstruction(Instruction):
        base: Account
        seed: str
        lamports: int
        space: int
        owner: Account

        funding_account: Account
        created_account: Account
        base_account: Account | None

    class SystemProgramAdvanceNonceAccountInstruction(Instruction):

        nonce_account: Account
        recent_blockhashes_sysvar: Account
        nonce_authority: Account

    class SystemProgramWithdrawNonceAccountInstruction(Instruction):
        lamports: int

        nonce_account: Account
        recipient_account: Account
        recent_blockhashes_sysvar: Account
        rent_sysvar: Account
        nonce_authority: Account

    class SystemProgramInitializeNonceAccountInstruction(Instruction):
        nonce_authority: Account

        nonce_account: Account
        recent_blockhashes_sysvar: Account
        rent_sysvar: Account

    class SystemProgramAuthorizeNonceAccountInstruction(Instruction):
        nonce_authority: Account

        nonce_account: Account
        nonce_authority: Account

    class SystemProgramAllocateInstruction(Instruction):
        space: int

        new_account: Account

    class SystemProgramAllocateWithSeedInstruction(Instruction):
        base: Account
        seed: str
        space: int
        owner: Account

        allocated_account: Account
        base_account: Account

    class SystemProgramAssignWithSeedInstruction(Instruction):
        base: Account
        seed: str
        owner: Account

        assigned_account: Account
        base_account: Account

    class SystemProgramTransferWithSeedInstruction(Instruction):
        lamports: int
        from_seed: str
        from_owner: Account

        funding_account: Account
        base_account: Account
        recipient_account: Account

    class SystemProgramUpgradeNonceAccountInstruction(Instruction):

        nonce_account: Account

    class StakeProgramInitializeInstruction(Instruction):
        staker: Account
        withdrawer: Account
        unix_timestamp: int
        epoch: int
        custodian: Account

        uninitialized_stake_account: Account
        rent_sysvar: Account

    class StakeProgramAuthorizeInstruction(Instruction):
        pubkey: Account
        stake_authorize: int

        stake_account: Account
        clock_sysvar: Account
        stake_or_withdraw_authority: Account
        lockup_authority: Account | None

    class StakeProgramDelegateStakeInstruction(Instruction):

        initialized_stake_account: Account
        vote_account: Account
        clock_sysvar: Account
        stake_history_sysvar: Account
        config_account: Account
        stake_authority: Account

    class StakeProgramSplitInstruction(Instruction):
        lamports: int

        stake_account: Account
        uninitialized_stake_account: Account
        stake_authority: Account

    class StakeProgramWithdrawInstruction(Instruction):
        lamports: int

        stake_account: Account
        recipient_account: Account
        clock_sysvar: Account
        stake_history_sysvar: Account
        withdrawal_authority: Account
        lockup_authority: Account | None

    class StakeProgramDeactivateInstruction(Instruction):

        delegated_stake_account: Account
        clock_sysvar: Account
        stake_authority: Account

    class StakeProgramSetLockupInstruction(Instruction):
        unix_timestamp: int
        epoch: int
        custodian: Account

        initialized_stake_account: Account
        lockup_or_withdraw_authority: Account

    class StakeProgramMergeInstruction(Instruction):

        destination_stake_account: Account
        source_stake_account: Account
        clock_sysvar: Account
        stake_history_sysvar: Account
        stake_authority: Account

    class StakeProgramAuthorizeWithSeedInstruction(Instruction):
        new_authorized_pubkey: Account
        stake_authorize: int
        authority_seed: str
        authority_owner: Account

        stake_account: Account
        stake_or_withdraw_authority: Account
        clock_sysvar: Account
        lockup_authority: Account | None

    class StakeProgramInitializeCheckedInstruction(Instruction):

        uninitialized_stake_account: Account
        rent_sysvar: Account
        stake_authority: Account
        withdrawal_authority: Account

    class StakeProgramAuthorizeCheckedInstruction(Instruction):
        stake_authorize: int

        stake_account: Account
        clock_sysvar: Account
        stake_or_withdraw_authority: Account
        new_stake_or_withdraw_authority: Account
        lockup_authority: Account | None

    class StakeProgramAuthorizeCheckedWithSeedInstruction(Instruction):
        stake_authorize: int
        authority_seed: str
        authority_owner: Account

        stake_account: Account
        stake_or_withdraw_authority: Account
        clock_sysvar: Account
        new_stake_or_withdraw_authority: Account
        lockup_authority: Account | None

    class StakeProgramSetLockupCheckedInstruction(Instruction):
        unix_timestamp: int
        epoch: int

        stake_account: Account
        lockup_or_withdraw_authority: Account
        new_lockup_authority: Account | None

    class ComputeBudgetProgramRequestHeapFrameInstruction(Instruction):
        bytes: int

    class ComputeBudgetProgramSetComputeUnitLimitInstruction(Instruction):
        units: int

    class ComputeBudgetProgramSetComputeUnitPriceInstruction(Instruction):
        lamports: int

    class TokenProgramInitializeAccountInstruction(Instruction):

        account_to_initialize: Account
        mint_account: Account
        owner: Account
        rent_sysvar: Account

    class TokenProgramInitializeMultisigInstruction(Instruction):
        number_of_signers: int

        multisig_account: Account
        rent_sysvar: Account
        signer_accounts: Account

    class TokenProgramTransferInstruction(Instruction):
        amount: int

        source_account: Account
        destination_account: Account
        owner: Account

    class TokenProgramApproveInstruction(Instruction):
        amount: int

        source_account: Account
        delegate_account: Account
        owner: Account

    class TokenProgramRevokeInstruction(Instruction):

        source_account: Account
        owner: Account

    class TokenProgramSetAuthorityInstruction(Instruction):
        authority_type: int
        new_authority: Account

        mint_account: Account
        current_authority: Account

    class TokenProgramMintToInstruction(Instruction):
        amount: int

        mint: Account
        account_to_mint: Account
        minting_authority: Account

    class TokenProgramBurnInstruction(Instruction):
        amount: int

        account_to_burn_from: Account
        token_mint: Account
        owner: Account

    class TokenProgramCloseAccountInstruction(Instruction):

        account_to_close: Account
        destination_account: Account
        owner: Account

    class TokenProgramFreezeAccountInstruction(Instruction):

        account_to_freeze: Account
        token_mint: Account
        freeze_authority: Account

    class TokenProgramThawAccountInstruction(Instruction):

        account_to_freeze: Account
        token_mint: Account
        freeze_authority: Account

    class TokenProgramTransferCheckedInstruction(Instruction):
        amount: int
        decimals: int

        source_account: Account
        token_mint: Account
        destination_account: Account
        owner: Account

    class TokenProgramApproveCheckedInstruction(Instruction):
        amount: int
        decimals: int

        source_account: Account
        token_mint: Account
        delegate: Account
        owner: Account

    class TokenProgramMinttoCheckedInstruction(Instruction):
        amount: int
        decimals: int

        mint: Account
        account_to_mint: Account
        minting_authority: Account

    class TokenProgramBurnCheckedInstruction(Instruction):
        amount: int
        decimals: int

        account_to_burn_from: Account
        token_mint: Account
        owner: Account

    class TokenProgramInitializeAccount2Instruction(Instruction):
        owner: Account

        account_to_initialize: Account
        mint_account: Account
        rent_sysvar: Account

    class TokenProgramSyncNativeInstruction(Instruction):

        token_account: Account

    class TokenProgramInitializeAccount3Instruction(Instruction):
        owner: Account

        account_to_initialize: Account
        mint_account: Account

    class TokenProgramInitializeImmutableOwnerInstruction(Instruction):

        account_to_initialize: Account

    class Token2022ProgramInitializeAccountInstruction(Instruction):

        account_to_initialize: Account
        mint_account: Account
        owner: Account
        rent_sysvar: Account

    class Token2022ProgramInitializeMultisigInstruction(Instruction):
        number_of_signers: int

        multisig_account: Account
        rent_sysvar: Account
        signer_accounts: Account

    class Token2022ProgramTransferInstruction(Instruction):
        amount: int

        source_account: Account
        destination_account: Account
        owner: Account

    class Token2022ProgramApproveInstruction(Instruction):
        amount: int

        source_account: Account
        delegate_account: Account
        owner: Account

    class Token2022ProgramRevokeInstruction(Instruction):

        source_account: Account
        owner: Account

    class Token2022ProgramSetAuthorityInstruction(Instruction):
        authority_type: int
        new_authority: Account

        mint_account: Account
        current_authority: Account

    class Token2022ProgramMinttoInstruction(Instruction):
        amount: int

        mint: Account
        account_to_mint: Account
        minting_authority: Account

    class Token2022ProgramBurnInstruction(Instruction):
        amount: int

        account_to_burn_from: Account
        token_mint: Account
        owner: Account

    class Token2022ProgramCloseAccountInstruction(Instruction):

        account_to_close: Account
        destination_account: Account
        owner: Account

    class Token2022ProgramFreezeAccountInstruction(Instruction):

        account_to_freeze: Account
        token_mint: Account
        freeze_authority: Account

    class Token2022ProgramThawAccountInstruction(Instruction):

        account_to_freeze: Account
        token_mint: Account
        freeze_authority: Account

    class Token2022ProgramTransferCheckedInstruction(Instruction):
        amount: int
        decimals: int

        source_account: Account
        token_mint: Account
        destination_account: Account
        owner: Account

    class Token2022ProgramApproveCheckedInstruction(Instruction):
        amount: int
        decimals: int

        source_account: Account
        token_mint: Account
        delegate: Account
        owner: Account

    class Token2022ProgramMinttoCheckedInstruction(Instruction):
        amount: int
        decimals: int

        mint: Account
        account_to_mint: Account
        minting_authority: Account

    class Token2022ProgramBurnCheckedInstruction(Instruction):
        amount: int
        decimals: int

        account_to_burn_from: Account
        token_mint: Account
        owner: Account

    class Token2022ProgramInitializeAccount2Instruction(Instruction):
        owner: Account

        account_to_initialize: Account
        mint_account: Account
        rent_sysvar: Account

    class Token2022ProgramSyncNativeInstruction(Instruction):

        token_account: Account

    class Token2022ProgramInitializeAccount3Instruction(Instruction):
        owner: Account

        account_to_initialize: Account
        mint_account: Account

    class Token2022ProgramInitializeImmutableOwnerInstruction(Instruction):

        account_to_initialize: Account

    class AssociatedTokenAccountProgramCreateInstruction(Instruction):

        funding_account: Account
        associated_token_account: Account
        wallet_address: Account
        token_mint: Account
        system_program: Account
        spl_token: Account
        rent_sysvar: Account | None

    class AssociatedTokenAccountProgramCreateIdempotentInstruction(Instruction):

        funding_account: Account
        associated_token_account: Account
        wallet_addr: Account
        token_mint: Account
        system_program: Account
        spl_token: Account

    class AssociatedTokenAccountProgramRecoverNestedInstruction(Instruction):

        nested_account: Account
        token_mint_nested: Account
        associated_token_account: Account
        owner: Account
        token_mint_owner: Account
        wallet_address: Account
        spl_token: Account

    class MemoProgramMemoInstruction(Instruction):
        memo: str

        signer_accounts: Account | None

    class MemoLegacyProgramMemoInstruction(Instruction):
        memo: str

        signer_accounts: Account | None


def get_instruction_id_length(program_id: str) -> int:
    if program_id == _SYSTEM_PROGRAM_ID:
        return 4
    if program_id == _STAKE_PROGRAM_ID:
        return 4
    if program_id == _COMPUTE_BUDGET_PROGRAM_ID:
        return 1
    if program_id == _TOKEN_PROGRAM_ID:
        return 1
    if program_id == _TOKEN_2022_PROGRAM_ID:
        return 1
    if program_id == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID:
        return 1
    if program_id == _MEMO_PROGRAM_ID:
        return 0
    if program_id == _MEMO_LEGACY_PROGRAM_ID:
        return 0

    return 0


def format_StakeAuthorize(value: int) -> str:
    if value == 0:
        return "Stake"
    if value == 1:
        return "Withdraw"
    raise DataError("Unknown value")


def format_AuthorityType(value: int) -> str:
    if value == 0:
        return "Mint tokens"
    if value == 1:
        return "Freeze account"
    if value == 2:
        return "Account owner"
    if value == 3:
        return "Close account"
    raise DataError("Unknown value")


def get_instruction(
    program_id: str,
    instruction_id: InstructionId,
    instruction_accounts: list[Account],
    instruction_data: InstructionData,
) -> Instruction:
    if program_id == _SYSTEM_PROGRAM_ID:
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT,
                (
                    PropertyTemplate(
                        "lamports",
                        False,
                        read_uint64_le,
                        format_lamports,
                        (),
                    ),
                    PropertyTemplate(
                        "space",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("funding_account", "new_account"),
                (
                    UIProperty(
                        None,
                        "new_account",
                        "Create account",
                        None,
                    ),
                    UIProperty(
                        "lamports",
                        None,
                        "Deposit",
                        None,
                    ),
                    UIProperty(
                        None,
                        "funding_account",
                        "From",
                        "signer",
                    ),
                ),
                "System Program: Create Account",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_ASSIGN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_ASSIGN,
                (
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                1,
                ("assigned_account",),
                (
                    UIProperty(
                        None,
                        "assigned_account",
                        "Assign account",
                        "signer",
                    ),
                    UIProperty(
                        "owner",
                        None,
                        "Assign account to program",
                        "signer",
                    ),
                ),
                "System Program: Assign",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_TRANSFER,
                (
                    PropertyTemplate(
                        "lamports",
                        False,
                        read_uint64_le,
                        format_lamports,
                        (),
                    ),
                ),
                2,
                ("funding_account", "recipient_account"),
                (
                    UIProperty(
                        None,
                        "recipient_account",
                        "Recipient",
                        None,
                    ),
                    UIProperty(
                        "lamports",
                        None,
                        "Amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "funding_account",
                        "Sender",
                        "signer",
                    ),
                ),
                "System Program: Transfer",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED,
                (
                    PropertyTemplate(
                        "base",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                    PropertyTemplate(
                        "seed",
                        False,
                        parse_string,
                        format_identity,
                        (),
                    ),
                    PropertyTemplate(
                        "lamports",
                        False,
                        read_uint64_le,
                        format_lamports,
                        (),
                    ),
                    PropertyTemplate(
                        "space",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("funding_account", "created_account", "base_account"),
                (
                    UIProperty(
                        None,
                        "created_account",
                        "Create account",
                        None,
                    ),
                    UIProperty(
                        "lamports",
                        None,
                        "Deposit",
                        None,
                    ),
                    UIProperty(
                        None,
                        "funding_account",
                        "From",
                        "signer",
                    ),
                ),
                "System Program: Create Account With Seed",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_ADVANCE_NONCE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_ADVANCE_NONCE_ACCOUNT,
                (),
                3,
                ("nonce_account", "recent_blockhashes_sysvar", "nonce_authority"),
                (
                    UIProperty(
                        None,
                        "nonce_account",
                        "Advance nonce",
                        None,
                    ),
                    UIProperty(
                        None,
                        "nonce_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "System Program: Advance Nonce Account",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_WITHDRAW_NONCE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_WITHDRAW_NONCE_ACCOUNT,
                (
                    PropertyTemplate(
                        "lamports",
                        False,
                        read_uint64_le,
                        format_lamports,
                        (),
                    ),
                ),
                5,
                (
                    "nonce_account",
                    "recipient_account",
                    "recent_blockhashes_sysvar",
                    "rent_sysvar",
                    "nonce_authority",
                ),
                (
                    UIProperty(
                        "lamports",
                        None,
                        "Nonce withdraw",
                        None,
                    ),
                    UIProperty(
                        None,
                        "nonce_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "recipient_account",
                        "To",
                        None,
                    ),
                    UIProperty(
                        None,
                        "nonce_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "System Program: Withdraw Nonce Account",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_INITIALIZE_NONCE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_INITIALIZE_NONCE_ACCOUNT,
                (
                    PropertyTemplate(
                        "nonce_authority",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                3,
                ("nonce_account", "recent_blockhashes_sysvar", "rent_sysvar"),
                (
                    UIProperty(
                        None,
                        "nonce_account",
                        "Initialize nonce account",
                        None,
                    ),
                    UIProperty(
                        "nonce_authority",
                        None,
                        "New authority",
                        "signer",
                    ),
                ),
                "System Program: Initialize Nonce Account",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_AUTHORIZE_NONCE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_AUTHORIZE_NONCE_ACCOUNT,
                (
                    PropertyTemplate(
                        "nonce_authority",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("nonce_account", "nonce_authority"),
                (
                    UIProperty(
                        None,
                        "nonce_account",
                        "Set nonce authority",
                        None,
                    ),
                    UIProperty(
                        "nonce_authority",
                        None,
                        "New authority",
                        "signer",
                    ),
                    UIProperty(
                        None,
                        "nonce_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "System Program: Authorize Nonce Account",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_ALLOCATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_ALLOCATE,
                (
                    PropertyTemplate(
                        "space",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                1,
                ("new_account",),
                (
                    UIProperty(
                        None,
                        "new_account",
                        "Allocate account",
                        "signer",
                    ),
                    UIProperty(
                        "space",
                        None,
                        "Data size",
                        None,
                    ),
                ),
                "System Program: Allocate",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED,
                (
                    PropertyTemplate(
                        "base",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                    PropertyTemplate(
                        "seed",
                        False,
                        parse_string,
                        format_identity,
                        (),
                    ),
                    PropertyTemplate(
                        "space",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("allocated_account", "base_account"),
                (
                    UIProperty(
                        None,
                        "allocated_account",
                        "Allocate data for account",
                        None,
                    ),
                    UIProperty(
                        "space",
                        None,
                        "Data size",
                        None,
                    ),
                ),
                "System Program: Allocate With Seed",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_ASSIGN_WITH_SEED,
                (
                    PropertyTemplate(
                        "base",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                    PropertyTemplate(
                        "seed",
                        False,
                        parse_string,
                        format_identity,
                        (),
                    ),
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("assigned_account", "base_account"),
                (
                    UIProperty(
                        None,
                        "assigned_account",
                        "Assign account",
                        None,
                    ),
                    UIProperty(
                        "owner",
                        None,
                        "Assign account to program",
                        None,
                    ),
                ),
                "System Program: Assign With Seed",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_TRANSFER_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_TRANSFER_WITH_SEED,
                (
                    PropertyTemplate(
                        "lamports",
                        False,
                        read_uint64_le,
                        format_lamports,
                        (),
                    ),
                    PropertyTemplate(
                        "from_seed",
                        False,
                        parse_string,
                        format_identity,
                        (),
                    ),
                    PropertyTemplate(
                        "from_owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                3,
                ("funding_account", "base_account", "recipient_account"),
                (
                    UIProperty(
                        None,
                        "recipient_account",
                        "Recipient",
                        None,
                    ),
                    UIProperty(
                        "lamports",
                        None,
                        "Amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "funding_account",
                        "Sender",
                        None,
                    ),
                ),
                "System Program: Transfer With Seed",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _SYSTEM_PROGRAM_ID_INS_UPGRADE_NONCE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _SYSTEM_PROGRAM_ID_INS_UPGRADE_NONCE_ACCOUNT,
                (),
                1,
                ("nonce_account",),
                (
                    UIProperty(
                        None,
                        "nonce_account",
                        "Upgrade nonce account",
                        None,
                    ),
                ),
                "System Program: Upgrade Nonce Account",
                True,
                True,
                False,
                False,
                None,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "System Program",
            True,
            False,
            False,
            False,
        )
    if program_id == _STAKE_PROGRAM_ID:
        if instruction_id == _STAKE_PROGRAM_ID_INS_INITIALIZE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_INITIALIZE,
                (
                    PropertyTemplate(
                        "staker",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                    PropertyTemplate(
                        "withdrawer",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                    PropertyTemplate(
                        "unix_timestamp",
                        False,
                        read_uint64_le,
                        format_unix_timestamp,
                        (),
                    ),
                    PropertyTemplate(
                        "epoch",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                    PropertyTemplate(
                        "custodian",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("uninitialized_stake_account", "rent_sysvar"),
                (
                    UIProperty(
                        None,
                        "uninitialized_stake_account",
                        "Initialize stake account",
                        None,
                    ),
                    UIProperty(
                        "staker",
                        None,
                        "New stake authority",
                        "signer",
                    ),
                    UIProperty(
                        "withdrawer",
                        None,
                        "New withdraw authority",
                        "signer",
                    ),
                    UIProperty(
                        "unix_timestamp",
                        None,
                        "Lockup time",
                        0,
                    ),
                    UIProperty(
                        "epoch",
                        None,
                        "Lockup epoch",
                        0,
                    ),
                    UIProperty(
                        "custodian",
                        None,
                        "Lockup authority",
                        "signer",
                    ),
                ),
                "Stake Program: Initialize",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_AUTHORIZE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_AUTHORIZE,
                (
                    PropertyTemplate(
                        "pubkey",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                    PropertyTemplate(
                        "stake_authorize",
                        False,
                        read_uint32_le,
                        format_StakeAuthorize,
                        (),
                    ),
                ),
                3,
                (
                    "stake_account",
                    "clock_sysvar",
                    "stake_or_withdraw_authority",
                    "lockup_authority",
                ),
                (
                    UIProperty(
                        None,
                        "stake_account",
                        "Set authority for",
                        None,
                    ),
                    UIProperty(
                        "pubkey",
                        None,
                        "New authority",
                        None,
                    ),
                    UIProperty(
                        "stake_authorize",
                        None,
                        "Authority type",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_or_withdraw_authority",
                        "Authorized by",
                        "signer",
                    ),
                    UIProperty(
                        None,
                        "lockup_authority",
                        "Custodian",
                        "signer",
                    ),
                ),
                "Stake Program: Authorize",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_DELEGATE_STAKE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_DELEGATE_STAKE,
                (),
                6,
                (
                    "initialized_stake_account",
                    "vote_account",
                    "clock_sysvar",
                    "stake_history_sysvar",
                    "config_account",
                    "stake_authority",
                ),
                (
                    UIProperty(
                        None,
                        "initialized_stake_account",
                        "Delegate from",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_authority",
                        "Authorized by",
                        "signer",
                    ),
                    UIProperty(
                        None,
                        "vote_account",
                        "Vote account",
                        None,
                    ),
                ),
                "Stake Program: Delegate Stake",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_SPLIT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_SPLIT,
                (
                    PropertyTemplate(
                        "lamports",
                        False,
                        read_uint64_le,
                        format_lamports,
                        (),
                    ),
                ),
                3,
                ("stake_account", "uninitialized_stake_account", "stake_authority"),
                (
                    UIProperty(
                        "lamports",
                        None,
                        "Split stake",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "uninitialized_stake_account",
                        "To",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "Stake Program: Split",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_WITHDRAW:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_WITHDRAW,
                (
                    PropertyTemplate(
                        "lamports",
                        False,
                        read_uint64_le,
                        format_lamports,
                        (),
                    ),
                ),
                5,
                (
                    "stake_account",
                    "recipient_account",
                    "clock_sysvar",
                    "stake_history_sysvar",
                    "withdrawal_authority",
                    "lockup_authority",
                ),
                (
                    UIProperty(
                        "lamports",
                        None,
                        "Withdraw stake",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "recipient_account",
                        "To",
                        None,
                    ),
                    UIProperty(
                        None,
                        "withdrawal_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "Stake Program: Withdraw",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_DEACTIVATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_DEACTIVATE,
                (),
                3,
                ("delegated_stake_account", "clock_sysvar", "stake_authority"),
                (
                    UIProperty(
                        None,
                        "delegated_stake_account",
                        "Deactivate stake account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "Stake Program: Deactivate",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_SET_LOCKUP:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_SET_LOCKUP,
                (
                    PropertyTemplate(
                        "unix_timestamp",
                        True,
                        read_uint64_le,
                        format_unix_timestamp,
                        (),
                    ),
                    PropertyTemplate(
                        "epoch",
                        True,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                    PropertyTemplate(
                        "custodian",
                        True,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("initialized_stake_account", "lockup_or_withdraw_authority"),
                (
                    UIProperty(
                        None,
                        "initialized_stake_account",
                        "Set lockup for account",
                        None,
                    ),
                    UIProperty(
                        "unix_timestamp",
                        None,
                        "Time",
                        0,
                    ),
                    UIProperty(
                        "epoch",
                        None,
                        "Epoch",
                        0,
                    ),
                    UIProperty(
                        "custodian",
                        None,
                        "New lockup authority",
                        None,
                    ),
                    UIProperty(
                        None,
                        "lockup_or_withdraw_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "Stake Program: Set Lockup",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_MERGE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_MERGE,
                (),
                5,
                (
                    "destination_stake_account",
                    "source_stake_account",
                    "clock_sysvar",
                    "stake_history_sysvar",
                    "stake_authority",
                ),
                (
                    UIProperty(
                        None,
                        "source_stake_account",
                        "Merge stake account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "destination_stake_account",
                        "Into",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "Stake Program: Merge",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_AUTHORIZE_WITH_SEED,
                (
                    PropertyTemplate(
                        "new_authorized_pubkey",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                    PropertyTemplate(
                        "stake_authorize",
                        False,
                        read_uint32_le,
                        format_StakeAuthorize,
                        (),
                    ),
                    PropertyTemplate(
                        "authority_seed",
                        False,
                        parse_string,
                        format_identity,
                        (),
                    ),
                    PropertyTemplate(
                        "authority_owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                3,
                (
                    "stake_account",
                    "stake_or_withdraw_authority",
                    "clock_sysvar",
                    "lockup_authority",
                ),
                (
                    UIProperty(
                        None,
                        "stake_account",
                        "Set authority for",
                        None,
                    ),
                    UIProperty(
                        "new_authorized_pubkey",
                        None,
                        "New authority",
                        None,
                    ),
                    UIProperty(
                        "stake_authorize",
                        None,
                        "Authority type",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_or_withdraw_authority",
                        "Authorized by",
                        "signer",
                    ),
                    UIProperty(
                        None,
                        "lockup_authority",
                        "Custodian",
                        "signer",
                    ),
                ),
                "Stake Program: Authorize With Seed",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_INITIALIZE_CHECKED,
                (),
                4,
                (
                    "uninitialized_stake_account",
                    "rent_sysvar",
                    "stake_authority",
                    "withdrawal_authority",
                ),
                (
                    UIProperty(
                        None,
                        "uninitialized_stake_account",
                        "Uninitialized stake account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_authority",
                        "New stake authority",
                        None,
                    ),
                    UIProperty(
                        None,
                        "withdrawal_authority",
                        "New withdraw authority",
                        "signer",
                    ),
                ),
                "Stake Program: Initialize Checked",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED,
                (
                    PropertyTemplate(
                        "stake_authorize",
                        False,
                        read_uint32_le,
                        format_StakeAuthorize,
                        (),
                    ),
                ),
                4,
                (
                    "stake_account",
                    "clock_sysvar",
                    "stake_or_withdraw_authority",
                    "new_stake_or_withdraw_authority",
                    "lockup_authority",
                ),
                (
                    UIProperty(
                        None,
                        "stake_account",
                        "Set authority for",
                        None,
                    ),
                    UIProperty(
                        None,
                        "new_stake_or_withdraw_authority",
                        "New authority",
                        "signer",
                    ),
                    UIProperty(
                        "stake_authorize",
                        None,
                        "Authority type",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_or_withdraw_authority",
                        "Authorized by",
                        "signer",
                    ),
                    UIProperty(
                        None,
                        "lockup_authority",
                        "Custodian",
                        "signer",
                    ),
                ),
                "Stake Program: Authorize Checked",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_AUTHORIZE_CHECKED_WITH_SEED,
                (
                    PropertyTemplate(
                        "stake_authorize",
                        False,
                        read_uint32_le,
                        format_StakeAuthorize,
                        (),
                    ),
                    PropertyTemplate(
                        "authority_seed",
                        False,
                        parse_string,
                        format_identity,
                        (),
                    ),
                    PropertyTemplate(
                        "authority_owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                4,
                (
                    "stake_account",
                    "stake_or_withdraw_authority",
                    "clock_sysvar",
                    "new_stake_or_withdraw_authority",
                    "lockup_authority",
                ),
                (
                    UIProperty(
                        None,
                        "stake_account",
                        "Set authority for",
                        None,
                    ),
                    UIProperty(
                        None,
                        "new_stake_or_withdraw_authority",
                        "New authority",
                        "signer",
                    ),
                    UIProperty(
                        "stake_authorize",
                        None,
                        "Authority type",
                        None,
                    ),
                    UIProperty(
                        None,
                        "stake_or_withdraw_authority",
                        "Authorized by",
                        "signer",
                    ),
                    UIProperty(
                        None,
                        "lockup_authority",
                        "Custodian",
                        "signer",
                    ),
                ),
                "Stake Program: Authorize Checked With Seed",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _STAKE_PROGRAM_ID_INS_SET_LOCKUP_CHECKED,
                (
                    PropertyTemplate(
                        "unix_timestamp",
                        True,
                        read_uint64_le,
                        format_unix_timestamp,
                        (),
                    ),
                    PropertyTemplate(
                        "epoch",
                        True,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                2,
                (
                    "stake_account",
                    "lockup_or_withdraw_authority",
                    "new_lockup_authority",
                ),
                (
                    UIProperty(
                        None,
                        "stake_account",
                        "Set lockup for stake account",
                        None,
                    ),
                    UIProperty(
                        "unix_timestamp",
                        None,
                        "Time",
                        0,
                    ),
                    UIProperty(
                        "epoch",
                        None,
                        "Epoch",
                        0,
                    ),
                    UIProperty(
                        None,
                        "new_lockup_authority",
                        "New lockup authority",
                        "signer",
                    ),
                    UIProperty(
                        None,
                        "lockup_or_withdraw_authority",
                        "Authorized by",
                        "signer",
                    ),
                ),
                "Stake Program: Set Lockup Checked",
                True,
                True,
                False,
                False,
                None,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "Stake Program",
            True,
            False,
            False,
            False,
        )
    if program_id == _COMPUTE_BUDGET_PROGRAM_ID:
        if instruction_id == _COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _COMPUTE_BUDGET_PROGRAM_ID_INS_REQUEST_HEAP_FRAME,
                (
                    PropertyTemplate(
                        "bytes",
                        False,
                        read_uint32_le,
                        format_int,
                        (),
                    ),
                ),
                0,
                (),
                (
                    UIProperty(
                        "bytes",
                        None,
                        "Bytes",
                        None,
                    ),
                ),
                "Compute Budget Program: Request Heap Frame",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT,
                (
                    PropertyTemplate(
                        "units",
                        False,
                        read_uint32_le,
                        format_int,
                        (),
                    ),
                ),
                0,
                (),
                (
                    UIProperty(
                        "units",
                        None,
                        "Units",
                        None,
                    ),
                ),
                "Compute Budget Program: Set Compute Unit Limit",
                True,
                True,
                True,
                False,
                None,
            )
        if instruction_id == _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
                (
                    PropertyTemplate(
                        "lamports",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                0,
                (),
                (
                    UIProperty(
                        "lamports",
                        None,
                        "Compute unit price",
                        None,
                    ),
                ),
                "Compute Budget Program: Set Compute Unit Price",
                True,
                True,
                True,
                False,
                None,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "Compute Budget Program",
            True,
            False,
            False,
            False,
        )
    if program_id == _TOKEN_PROGRAM_ID:
        if instruction_id == _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT,
                (),
                4,
                ("account_to_initialize", "mint_account", "owner", "rent_sysvar"),
                (
                    UIProperty(
                        None,
                        "account_to_initialize",
                        "Initialize account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        None,
                    ),
                    UIProperty(
                        None,
                        "mint_account",
                        "For token",
                        None,
                    ),
                ),
                "Token Program: Initialize Account",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_INITIALIZE_MULTISIG,
                (
                    PropertyTemplate(
                        "number_of_signers",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("multisig_account", "rent_sysvar", "signer_accounts"),
                (
                    UIProperty(
                        None,
                        "multisig_account",
                        "Initialize multisig",
                        None,
                    ),
                    UIProperty(
                        None,
                        "signer_accounts",
                        "Required signers",
                        None,
                    ),
                ),
                "Token Program: Initialize Multisig",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_TRANSFER,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("source_account", "destination_account", "owner"),
                (
                    UIProperty(
                        None,
                        "destination_account",
                        "Recipient",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "source_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Transfer",
                True,
                True,
                False,
                True,
                "Warning: Instruction is deprecated. Token decimals unknown.",
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_APPROVE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_APPROVE,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("source_account", "delegate_account", "owner"),
                (
                    UIProperty(
                        None,
                        "delegate_account",
                        "Approve delegate",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Allowance",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Approve",
                True,
                True,
                False,
                True,
                "Warning: Instruction is deprecated. Token decimals unknown.",
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_REVOKE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_REVOKE,
                (),
                2,
                ("source_account", "owner"),
                (
                    UIProperty(
                        None,
                        "source_account",
                        "Revoke delegate",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Revoke",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_SET_AUTHORITY:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_SET_AUTHORITY,
                (
                    PropertyTemplate(
                        "authority_type",
                        False,
                        parse_byte,
                        format_AuthorityType,
                        (),
                    ),
                    PropertyTemplate(
                        "new_authority",
                        True,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("mint_account", "current_authority"),
                (
                    UIProperty(
                        None,
                        "mint_account",
                        "Set authority for",
                        None,
                    ),
                    UIProperty(
                        "new_authority",
                        None,
                        "New authority",
                        "signer",
                    ),
                    UIProperty(
                        "authority_type",
                        None,
                        "Authority type",
                        None,
                    ),
                    UIProperty(
                        None,
                        "current_authority",
                        "Current authority",
                        "signer",
                    ),
                ),
                "Token Program: Set Authority",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_MINT_TO:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_MINT_TO,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("mint", "account_to_mint", "minting_authority"),
                (
                    UIProperty(
                        None,
                        "mint",
                        "Mint token",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Mint amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "account_to_mint",
                        "To",
                        None,
                    ),
                    UIProperty(
                        None,
                        "minting_authority",
                        "Mint authority",
                        "signer",
                    ),
                ),
                "Token Program: Mint To",
                True,
                True,
                False,
                True,
                "Warning: Instruction is deprecated. Token decimals unknown.",
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_BURN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_BURN,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("account_to_burn_from", "token_mint", "owner"),
                (
                    UIProperty(
                        None,
                        "token_mint",
                        "Burn token",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Burn amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "account_to_burn_from",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Mint authority",
                        "signer",
                    ),
                ),
                "Token Program: Burn",
                True,
                True,
                False,
                True,
                "Warning: Instruction is deprecated. Token decimals unknown.",
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_CLOSE_ACCOUNT,
                (),
                3,
                ("account_to_close", "destination_account", "owner"),
                (
                    UIProperty(
                        None,
                        "account_to_close",
                        "Close account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "destination_account",
                        "Withdraw to",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Close Account",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_FREEZE_ACCOUNT,
                (),
                3,
                ("account_to_freeze", "token_mint", "freeze_authority"),
                (
                    UIProperty(
                        None,
                        "account_to_freeze",
                        "Freeze account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "token_mint",
                        "Token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "freeze_authority",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Freeze Account",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_THAW_ACCOUNT,
                (),
                3,
                ("account_to_freeze", "token_mint", "freeze_authority"),
                (
                    UIProperty(
                        None,
                        "account_to_freeze",
                        "Thaw account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "token_mint",
                        "Token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "freeze_authority",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Thaw Account",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_TRANSFER_CHECKED,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_token_amount,
                        ("#definitions", "decimals", "token_mint"),
                    ),
                    PropertyTemplate(
                        "decimals",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                4,
                ("source_account", "token_mint", "destination_account", "owner"),
                (
                    UIProperty(
                        None,
                        "token_mint",
                        "Token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "destination_account",
                        "Recipient",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "source_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Transfer Checked",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_APPROVE_CHECKED,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_token_amount,
                        ("#definitions", "decimals", "token_mint"),
                    ),
                    PropertyTemplate(
                        "decimals",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                4,
                ("source_account", "token_mint", "delegate", "owner"),
                (
                    UIProperty(
                        None,
                        "token_mint",
                        "Approve token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "delegate",
                        "Approve delegate",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Allowance",
                        None,
                    ),
                    UIProperty(
                        None,
                        "source_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Approve Checked",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_MINT_TO_CHECKED,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_token_amount,
                        ("#definitions", "decimals", "mint"),
                    ),
                    PropertyTemplate(
                        "decimals",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("mint", "account_to_mint", "minting_authority"),
                (
                    UIProperty(
                        None,
                        "mint",
                        "Mint token",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Mint amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "account_to_mint",
                        "To",
                        None,
                    ),
                    UIProperty(
                        None,
                        "minting_authority",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Mint to Checked",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_BURN_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_BURN_CHECKED,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_token_amount,
                        ("#definitions", "decimals", "token_mint"),
                    ),
                    PropertyTemplate(
                        "decimals",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("account_to_burn_from", "token_mint", "owner"),
                (
                    UIProperty(
                        None,
                        "token_mint",
                        "Burn token",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Burn amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "account_to_burn_from",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token Program: Burn Checked",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2,
                (
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                3,
                ("account_to_initialize", "mint_account", "rent_sysvar"),
                (
                    UIProperty(
                        None,
                        "account_to_initialize",
                        "Initialize account",
                        None,
                    ),
                    UIProperty(
                        "owner",
                        None,
                        "Owner",
                        None,
                    ),
                    UIProperty(
                        None,
                        "mint_account",
                        "For token",
                        None,
                    ),
                ),
                "Token Program: Initialize Account 2",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_SYNC_NATIVE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_SYNC_NATIVE,
                (),
                1,
                ("token_account",),
                (
                    UIProperty(
                        None,
                        "token_account",
                        "Sync native account",
                        None,
                    ),
                ),
                "Token Program: Sync Native",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3,
                (
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("account_to_initialize", "mint_account"),
                (
                    UIProperty(
                        None,
                        "account_to_initialize",
                        "Initialize account",
                        None,
                    ),
                    UIProperty(
                        "owner",
                        None,
                        "Owner",
                        None,
                    ),
                    UIProperty(
                        None,
                        "mint_account",
                        "For token",
                        None,
                    ),
                ),
                "Token Program: Initialize Account 3",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER,
                (),
                1,
                ("account_to_initialize",),
                (
                    UIProperty(
                        None,
                        "account_to_initialize",
                        "Init account",
                        None,
                    ),
                ),
                "Token Program: Initialize Immutable Owner",
                True,
                True,
                False,
                False,
                None,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "Token Program",
            True,
            False,
            False,
            False,
        )
    if program_id == _TOKEN_2022_PROGRAM_ID:
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT,
                (),
                4,
                ("account_to_initialize", "mint_account", "owner", "rent_sysvar"),
                (
                    UIProperty(
                        None,
                        "account_to_initialize",
                        "Initialize account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        None,
                    ),
                    UIProperty(
                        None,
                        "mint_account",
                        "For token",
                        None,
                    ),
                ),
                "Token 2022 Program: Initialize Account",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_MULTISIG:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_MULTISIG,
                (
                    PropertyTemplate(
                        "number_of_signers",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("multisig_account", "rent_sysvar", "signer_accounts"),
                (
                    UIProperty(
                        None,
                        "multisig_account",
                        "Init multisig",
                        None,
                    ),
                    UIProperty(
                        None,
                        "signer_accounts",
                        "Required signers",
                        None,
                    ),
                ),
                "Token 2022 Program: Initialize Multisig",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_TRANSFER,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("source_account", "destination_account", "owner"),
                (
                    UIProperty(
                        None,
                        "destination_account",
                        "Recipient",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "source_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Transfer",
                True,
                True,
                False,
                True,
                "Warning: Instruction is deprecated. Token decimals unknown.",
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_APPROVE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_APPROVE,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("source_account", "delegate_account", "owner"),
                (
                    UIProperty(
                        None,
                        "delegate_account",
                        "Approve delegate",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Allowance",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Approve",
                True,
                True,
                False,
                True,
                "Warning: Instruction is deprecated. Token decimals unknown.",
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_REVOKE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_REVOKE,
                (),
                2,
                ("source_account", "owner"),
                (
                    UIProperty(
                        None,
                        "source_account",
                        "Rewoke delegate",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Revoke",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_SET_AUTHORITY:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_SET_AUTHORITY,
                (
                    PropertyTemplate(
                        "authority_type",
                        False,
                        parse_byte,
                        format_AuthorityType,
                        (),
                    ),
                    PropertyTemplate(
                        "new_authority",
                        True,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("mint_account", "current_authority"),
                (
                    UIProperty(
                        None,
                        "mint_account",
                        "Set authority for",
                        None,
                    ),
                    UIProperty(
                        "new_authority",
                        None,
                        "New authority",
                        "signer",
                    ),
                    UIProperty(
                        "authority_type",
                        None,
                        "Authority type",
                        None,
                    ),
                    UIProperty(
                        None,
                        "current_authority",
                        "Current authority",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Set Authority",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_MINT_TO:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_MINT_TO,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("mint", "account_to_mint", "minting_authority"),
                (
                    UIProperty(
                        None,
                        "mint",
                        "Mint token",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Mint amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "account_to_mint",
                        "To",
                        None,
                    ),
                    UIProperty(
                        None,
                        "minting_authority",
                        "Mint authority",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Mint to",
                True,
                True,
                False,
                True,
                "Warning: Instruction is deprecated. Token decimals unknown.",
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_BURN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_BURN,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("account_to_burn_from", "token_mint", "owner"),
                (
                    UIProperty(
                        None,
                        "token_mint",
                        "Burn token",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Burn amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "account_to_burn_from",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Mint authority",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Burn",
                True,
                True,
                False,
                True,
                "Warning: Instruction is deprecated. Token decimals unknown.",
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_CLOSE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_CLOSE_ACCOUNT,
                (),
                3,
                ("account_to_close", "destination_account", "owner"),
                (
                    UIProperty(
                        None,
                        "account_to_close",
                        "Close account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "destination_account",
                        "Withdraw to",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Close Account",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_FREEZE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_FREEZE_ACCOUNT,
                (),
                3,
                ("account_to_freeze", "token_mint", "freeze_authority"),
                (
                    UIProperty(
                        None,
                        "account_to_freeze",
                        "Freeze account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "token_mint",
                        "Token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "freeze_authority",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Freeze Account",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_THAW_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_THAW_ACCOUNT,
                (),
                3,
                ("account_to_freeze", "token_mint", "freeze_authority"),
                (
                    UIProperty(
                        None,
                        "account_to_freeze",
                        "Thaw account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "token_mint",
                        "Token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "freeze_authority",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Thaw Account",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_TRANSFER_CHECKED,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_token_amount,
                        ("#definitions", "decimals", "token_mint"),
                    ),
                    PropertyTemplate(
                        "decimals",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                4,
                ("source_account", "token_mint", "destination_account", "owner"),
                (
                    UIProperty(
                        None,
                        "token_mint",
                        "Token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "destination_account",
                        "Recipient",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "source_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Transfer Checked",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_APPROVE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_APPROVE_CHECKED,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_token_amount,
                        ("#definitions", "decimals", "token_mint"),
                    ),
                    PropertyTemplate(
                        "decimals",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                4,
                ("source_account", "token_mint", "delegate", "owner"),
                (
                    UIProperty(
                        None,
                        "token_mint",
                        "Approve token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "delegate",
                        "Approve delegate",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Allowance",
                        None,
                    ),
                    UIProperty(
                        None,
                        "source_account",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Approve Checked",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_MINT_TO_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_MINT_TO_CHECKED,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_token_amount,
                        ("#definitions", "decimals", "mint"),
                    ),
                    PropertyTemplate(
                        "decimals",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("mint", "account_to_mint", "minting_authority"),
                (
                    UIProperty(
                        None,
                        "mint",
                        "Mint token",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Mint amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "account_to_mint",
                        "To",
                        None,
                    ),
                    UIProperty(
                        None,
                        "minting_authority",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Mint to Checked",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_BURN_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_BURN_CHECKED,
                (
                    PropertyTemplate(
                        "amount",
                        False,
                        read_uint64_le,
                        format_token_amount,
                        ("#definitions", "decimals", "token_mint"),
                    ),
                    PropertyTemplate(
                        "decimals",
                        False,
                        parse_byte,
                        format_int,
                        (),
                    ),
                ),
                3,
                ("account_to_burn_from", "token_mint", "owner"),
                (
                    UIProperty(
                        None,
                        "token_mint",
                        "Burn token",
                        None,
                    ),
                    UIProperty(
                        "amount",
                        None,
                        "Burn amount",
                        None,
                    ),
                    UIProperty(
                        None,
                        "account_to_burn_from",
                        "From",
                        None,
                    ),
                    UIProperty(
                        None,
                        "owner",
                        "Owner",
                        "signer",
                    ),
                ),
                "Token 2022 Program: Burn Checked",
                True,
                True,
                False,
                True,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_2,
                (
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                3,
                ("account_to_initialize", "mint_account", "rent_sysvar"),
                (
                    UIProperty(
                        None,
                        "account_to_initialize",
                        "Initialize account",
                        None,
                    ),
                    UIProperty(
                        "owner",
                        None,
                        "Owner",
                        None,
                    ),
                    UIProperty(
                        None,
                        "mint_account",
                        "For token",
                        None,
                    ),
                ),
                "Token 2022 Program: Initialize Account 2",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_SYNC_NATIVE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_SYNC_NATIVE,
                (),
                1,
                ("token_account",),
                (
                    UIProperty(
                        None,
                        "token_account",
                        "Sync native account",
                        None,
                    ),
                ),
                "Token 2022 Program: Sync Native",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_ACCOUNT_3,
                (
                    PropertyTemplate(
                        "owner",
                        False,
                        parse_pubkey,
                        format_pubkey,
                        (),
                    ),
                ),
                2,
                ("account_to_initialize", "mint_account"),
                (
                    UIProperty(
                        None,
                        "account_to_initialize",
                        "Initialize account",
                        None,
                    ),
                    UIProperty(
                        "owner",
                        None,
                        "Owner",
                        None,
                    ),
                    UIProperty(
                        None,
                        "mint_account",
                        "For token",
                        None,
                    ),
                ),
                "Token 2022 Program: Initialize Account 3",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _TOKEN_2022_PROGRAM_ID_INS_INITIALIZE_IMMUTABLE_OWNER,
                (),
                1,
                ("account_to_initialize",),
                (
                    UIProperty(
                        None,
                        "account_to_initialize",
                        "Initialize immutable owner extension for account",
                        None,
                    ),
                ),
                "Token 2022 Program: Initialize Immutable Owner",
                True,
                True,
                False,
                False,
                None,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "Token 2022 Program",
            True,
            False,
            False,
            False,
        )
    if program_id == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID:
        if instruction_id == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE,
                (),
                6,
                (
                    "funding_account",
                    "associated_token_account",
                    "wallet_address",
                    "token_mint",
                    "system_program",
                    "spl_token",
                    "rent_sysvar",
                ),
                (
                    UIProperty(
                        None,
                        "associated_token_account",
                        "Create token account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "token_mint",
                        "For token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "wallet_address",
                        "Owned by",
                        None,
                    ),
                    UIProperty(
                        None,
                        "funding_account",
                        "Funded by",
                        "signer",
                    ),
                ),
                "Associated Token Account Program: Create",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT,
                (),
                6,
                (
                    "funding_account",
                    "associated_token_account",
                    "wallet_addr",
                    "token_mint",
                    "system_program",
                    "spl_token",
                ),
                (
                    UIProperty(
                        None,
                        "associated_token_account",
                        "Create token account",
                        None,
                    ),
                    UIProperty(
                        None,
                        "token_mint",
                        "For token",
                        None,
                    ),
                    UIProperty(
                        None,
                        "wallet_addr",
                        "Owned by",
                        None,
                    ),
                    UIProperty(
                        None,
                        "funding_account",
                        "Funded by",
                        "signer",
                    ),
                ),
                "Associated Token Account Program: Create Idempotent",
                True,
                True,
                False,
                False,
                None,
            )
        if instruction_id == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_RECOVER_NESTED,
                (),
                7,
                (
                    "nested_account",
                    "token_mint_nested",
                    "associated_token_account",
                    "owner",
                    "token_mint_owner",
                    "wallet_address",
                    "spl_token",
                ),
                (
                    UIProperty(
                        None,
                        "nested_account",
                        "Recover nested token account",
                        "signer",
                    ),
                    UIProperty(
                        None,
                        "associated_token_account",
                        "Transfer recovered tokens to",
                        None,
                    ),
                    UIProperty(
                        None,
                        "wallet_address",
                        "Transfer recovered SOL to",
                        "signer",
                    ),
                ),
                "Associated Token Account Program: Recover Nested",
                True,
                True,
                False,
                False,
                None,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "Associated Token Account Program",
            True,
            False,
            False,
            False,
        )
    if program_id == _MEMO_PROGRAM_ID:
        if instruction_id == _MEMO_PROGRAM_ID_INS_MEMO:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _MEMO_PROGRAM_ID_INS_MEMO,
                (
                    PropertyTemplate(
                        "memo",
                        False,
                        parse_memo,
                        format_identity,
                        (),
                    ),
                ),
                0,
                ("signer_accounts",),
                (
                    UIProperty(
                        "memo",
                        None,
                        "Memo",
                        None,
                    ),
                    UIProperty(
                        None,
                        "signer_accounts",
                        "Signer accounts",
                        "signer",
                    ),
                ),
                "Memo Program: Memo",
                True,
                True,
                False,
                False,
                None,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "Memo Program",
            True,
            False,
            False,
            False,
        )
    if program_id == _MEMO_LEGACY_PROGRAM_ID:
        if instruction_id == _MEMO_LEGACY_PROGRAM_ID_INS_MEMO:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                _MEMO_LEGACY_PROGRAM_ID_INS_MEMO,
                (
                    PropertyTemplate(
                        "memo",
                        False,
                        parse_memo,
                        format_identity,
                        (),
                    ),
                ),
                0,
                ("signer_accounts",),
                (
                    UIProperty(
                        "memo",
                        None,
                        "Memo",
                        None,
                    ),
                    UIProperty(
                        None,
                        "signer_accounts",
                        "Signer accounts",
                        "signer",
                    ),
                ),
                "Memo Legacy Program: Memo",
                True,
                True,
                False,
                False,
                None,
            )
        return Instruction(
            instruction_data,
            program_id,
            instruction_accounts,
            instruction_id,
            (),
            0,
            (),
            (),
            "Memo Legacy Program",
            True,
            False,
            False,
            False,
        )
    return Instruction(
        instruction_data,
        program_id,
        instruction_accounts,
        0,
        (),
        0,
        (),
        (),
        "Unsupported program",
        False,
        False,
        False,
        False,
    )
