# generated from __init__.py.mako
# do not edit manually!
from typing import TYPE_CHECKING

from trezor.wire import ProcessError

from ..constants import (
    ADDRESS_READ_ONLY,
    ADDRESS_RW,
    ADDRESS_SIG,
    ADDRESS_SIG_READ_ONLY,
)
from . import Instruction

if TYPE_CHECKING:
    from typing import Any, Type, TypeGuard
    from ..types import RawInstruction


def __getattr__(name: str) -> Type[Instruction]:
    ids = {
        "CreateAccountInstruction": ("11111111111111111111111111111111", 0),
        "AssignInstruction": ("11111111111111111111111111111111", 1),
        "TransferInstruction": ("11111111111111111111111111111111", 2),
        "CreateAccountWithSeedInstruction": ("11111111111111111111111111111111", 3),
        "AllocateInstruction": ("11111111111111111111111111111111", 8),
        "AllocateWithSeedInstruction": ("11111111111111111111111111111111", 9),
        "AssignWithSeedInstruction": ("11111111111111111111111111111111", 10),
        "InitializeInstruction": ("Stake11111111111111111111111111111111111111", 0),
        "AuthorizeInstruction": ("Stake11111111111111111111111111111111111111", 1),
        "DelegateStakeInstruction": ("Stake11111111111111111111111111111111111111", 2),
        "SplitInstruction": ("Stake11111111111111111111111111111111111111", 3),
        "WithdrawInstruction": ("Stake11111111111111111111111111111111111111", 4),
        "DeactivateInstruction": ("Stake11111111111111111111111111111111111111", 5),
        "SetLockupInstruction": ("Stake11111111111111111111111111111111111111", 6),
        "MergeInstruction": ("Stake11111111111111111111111111111111111111", 7),
        "AuthorizeWithSeedInstruction": (
            "Stake11111111111111111111111111111111111111",
            8,
        ),
        "InitializeCheckedInstruction": (
            "Stake11111111111111111111111111111111111111",
            9,
        ),
        "AuthorizeCheckedInstruction": (
            "Stake11111111111111111111111111111111111111",
            10,
        ),
        "AuthorizeCheckedWithSeedInstruction": (
            "Stake11111111111111111111111111111111111111",
            11,
        ),
        "SetLockupCheckedInstruction": (
            "Stake11111111111111111111111111111111111111",
            12,
        ),
        "RequestHeapFrameInstruction": (
            "ComputeBudget111111111111111111111111111111",
            1,
        ),
        "SetComputeUnitLimitInstruction": (
            "ComputeBudget111111111111111111111111111111",
            2,
        ),
        "SetComputeUnitPriceInstruction": (
            "ComputeBudget111111111111111111111111111111",
            3,
        ),
    }
    id = ids[name]

    class FakeClass(Instruction):
        @classmethod
        def is_type_of(cls, ins: Any):
            return ins.program_id == id[0] and ins.instruction_id == id[1]

    return FakeClass


SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"
COMPUTE_BUDGET_PROGRAM_ID = "ComputeBudget111111111111111111111111111111"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

INS_CREATE_ACCOUNT = 0
INS_ASSIGN = 1
INS_TRANSFER = 2
INS_CREATE_ACCOUNT_WITH_SEED = 3
INS_ALLOCATE = 8
INS_ALLOCATE_WITH_SEED = 9
INS_ASSIGN_WITH_SEED = 10
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
INS_REQUEST_HEAP_FRAME = 1
INS_SET_COMPUTE_UNIT_LIMIT = 2
INS_SET_COMPUTE_UNIT_PRICE = 3

if TYPE_CHECKING:

    class CreateAccountInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = INS_CREATE_ACCOUNT

        lamports: int
        space: int
        owner: bytes

        funding_account: bytes
        new_account: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["CreateAccountInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AssignInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = INS_ASSIGN

        owner: bytes

        assigned_account: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["AssignInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class TransferInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = INS_TRANSFER

        lamports: int

        funding_account: bytes
        recipient_account: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["TransferInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class CreateAccountWithSeedInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = INS_CREATE_ACCOUNT_WITH_SEED

        base: bytes
        seed: str
        lamports: int
        space: int
        owner: bytes

        funding_account: bytes
        created_account: bytes
        base_account: bytes | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["CreateAccountWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AllocateInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = INS_ALLOCATE

        space: int

        new_account: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["AllocateInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AllocateWithSeedInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = INS_ALLOCATE_WITH_SEED

        base: bytes
        seed: str
        space: int
        owner: bytes

        allocated_account: bytes
        base_account: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["AllocateWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AssignWithSeedInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = INS_ASSIGN_WITH_SEED

        base: bytes
        seed: str
        owner: bytes

        assigned_account: bytes
        base_account: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["AssignWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class InitializeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_INITIALIZE

        staker: bytes
        withdrawer: bytes
        unix_timestamp: int
        epoch: int
        custodian: bytes

        uninitialized_stake_account: bytes
        rent_sysvar: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["InitializeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AuthorizeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_AUTHORIZE

        pubkey: bytes
        stakeauthorize: int

        stake_account: bytes
        clock_sysvar: bytes
        stake_or_withdraw_authority: bytes
        lockup_authority: bytes | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["AuthorizeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class DelegateStakeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_DELEGATE_STAKE

        initialized_stake_account: bytes
        vote_account: bytes
        clock_sysvar: bytes
        stake_history_sysvar: bytes
        config_account: bytes
        stake_authority: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["DelegateStakeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SplitInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_SPLIT

        lamports: int

        stake_account: bytes
        uninitialized_stake_account: bytes
        stake_authority: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["SplitInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class WithdrawInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_WITHDRAW

        lamports: int

        stake_account: bytes
        recipient_account: bytes
        clock_sysvar: bytes
        stake_history_sysvar: bytes
        withdraw_authority: bytes
        lockup_authority: bytes | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["WithdrawInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class DeactivateInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_DEACTIVATE

        delegated_stake_account: bytes
        clock_sysvar: bytes
        stake_authority: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["DeactivateInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SetLockupInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_SET_LOCKUP

        unix_timestamp: int
        epoch: int
        custodian: bytes

        initialized_stake_account: bytes
        lockup_authority_or_withdraw_authority: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["SetLockupInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class MergeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_MERGE

        destination_stake_account: bytes
        source_stake_account: bytes
        clock_sysvar: bytes
        stake_history_sysvar: bytes
        stake_authority: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["MergeInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AuthorizeWithSeedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_AUTHORIZE_WITH_SEED

        new_authorized_pubkey: bytes
        stake_authorize: int
        authority_seed: str
        authority_owner: bytes

        stake_account: bytes
        stake_or_withdraw_authority: bytes
        clock_sysvar: bytes
        lockup_authority: bytes | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["AuthorizeWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class InitializeCheckedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_INITIALIZE_CHECKED

        uninitialized_stake_account: bytes
        rent_sysvar: bytes
        stake_authority: bytes
        withdraw_authority: bytes

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["InitializeCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AuthorizeCheckedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_AUTHORIZE_CHECKED

        stakeauthorize: int

        stake_account: bytes
        clock_sysvar: bytes
        stake_or_withdraw_authority: bytes
        new_stake_or_withdraw_authority: bytes
        lockup_authority: bytes | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["AuthorizeCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AuthorizeCheckedWithSeedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_AUTHORIZE_CHECKED_WITH_SEED

        stake_authorize: int
        authority_seed: str
        authority_owner: bytes

        stake_account: bytes
        stake_or_withdraw_authority: bytes
        clock_sysvar: bytes
        new_stake_or_withdraw_authority: bytes
        lockup_authority: bytes | None

        @classmethod
        def is_type_of(
            cls, ins: Any
        ) -> TypeGuard["AuthorizeCheckedWithSeedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SetLockupCheckedInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_SET_LOCKUP_CHECKED

        unix_timestamp: int
        epoch: int

        stake_account: bytes
        lockup_authority_or_withdraw_authority: bytes
        new_lockup_authority: bytes | None

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["SetLockupCheckedInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class RequestHeapFrameInstruction(Instruction):
        PROGRAM_ID = COMPUTE_BUDGET_PROGRAM_ID
        INSTRUCTION_ID = INS_REQUEST_HEAP_FRAME

        bytes: int

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["RequestHeapFrameInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SetComputeUnitLimitInstruction(Instruction):
        PROGRAM_ID = COMPUTE_BUDGET_PROGRAM_ID
        INSTRUCTION_ID = INS_SET_COMPUTE_UNIT_LIMIT

        units: int

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["SetComputeUnitLimitInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class SetComputeUnitPriceInstruction(Instruction):
        PROGRAM_ID = COMPUTE_BUDGET_PROGRAM_ID
        INSTRUCTION_ID = INS_SET_COMPUTE_UNIT_PRICE

        lamports: int

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["SetComputeUnitPriceInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )


def get_instruction(
    encoded_program_id: str, instruction_id: int, raw_instruction: RawInstruction
) -> Instruction:
    if encoded_program_id == SYSTEM_PROGRAM_ID:
        if instruction_id == INS_CREATE_ACCOUNT:
            return Instruction(
                raw_instruction,
                INS_CREATE_ACCOUNT,
                [
                    ("lamports", "u64"),
                    ("space", "u64"),
                    ("owner", "pubkey"),
                ],
                [
                    ("funding_account", "Funding account", ADDRESS_SIG),
                    ("new_account", "New account", ADDRESS_SIG),
                ],
                "create_account",
                "Create Account",
            )
        elif instruction_id == INS_ASSIGN:
            return Instruction(
                raw_instruction,
                INS_ASSIGN,
                [
                    ("owner", "pubkey"),
                ],
                [
                    ("assigned_account", "Assigned account", ADDRESS_SIG),
                ],
                "assign",
                "Assign",
            )
        elif instruction_id == INS_TRANSFER:
            return Instruction(
                raw_instruction,
                INS_TRANSFER,
                [
                    ("lamports", "u64"),
                ],
                [
                    ("funding_account", "Funding account", ADDRESS_SIG),
                    ("recipient_account", "Recipient account", ADDRESS_RW),
                ],
                "transfer",
                "Transfer",
            )
        elif instruction_id == INS_CREATE_ACCOUNT_WITH_SEED:
            return Instruction(
                raw_instruction,
                INS_CREATE_ACCOUNT_WITH_SEED,
                [
                    ("base", "pubkey"),
                    ("seed", "string"),
                    ("lamports", "u64"),
                    ("space", "u64"),
                    ("owner", "pubkey"),
                ],
                [
                    ("funding_account", "Funding account", ADDRESS_SIG),
                    ("created_account", "Created account", ADDRESS_RW),
                    ("base_account", "Base account", ADDRESS_SIG_READ_ONLY, True),
                ],
                "create_account_with_seed",
                "Create Account With Seed",
            )
        elif instruction_id == INS_ALLOCATE:
            return Instruction(
                raw_instruction,
                INS_ALLOCATE,
                [
                    ("space", "u64"),
                ],
                [
                    ("new_account", "New account", ADDRESS_SIG),
                ],
                "allocate",
                "Allocate",
            )
        elif instruction_id == INS_ALLOCATE_WITH_SEED:
            return Instruction(
                raw_instruction,
                INS_ALLOCATE_WITH_SEED,
                [
                    ("base", "pubkey"),
                    ("seed", "string"),
                    ("space", "u64"),
                    ("owner", "pubkey"),
                ],
                [
                    ("allocated_account", "Allocated account", ADDRESS_RW),
                    ("base_account", "Base account", ADDRESS_SIG_READ_ONLY),
                ],
                "allocate_with_seed",
                "Allocate With Seed",
            )
        elif instruction_id == INS_ASSIGN_WITH_SEED:
            return Instruction(
                raw_instruction,
                INS_ASSIGN_WITH_SEED,
                [
                    ("base", "pubkey"),
                    ("seed", "string"),
                    ("owner", "pubkey"),
                ],
                [
                    ("assigned_account", "Assigned account", ADDRESS_RW),
                    ("base_account", "Base account", ADDRESS_SIG_READ_ONLY),
                ],
                "assign_with_seed",
                "Assign With Seed",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {encoded_program_id} {instruction_id}"
            )
    if encoded_program_id == STAKE_PROGRAM_ID:
        if instruction_id == INS_INITIALIZE:
            return Instruction(
                raw_instruction,
                INS_INITIALIZE,
                [
                    ("staker", "pubkey"),
                    ("withdrawer", "pubkey"),
                    ("unix_timestamp", "i64"),
                    ("epoch", "u64"),
                    ("custodian", "pubkey"),
                ],
                [
                    (
                        "uninitialized_stake_account",
                        "Uninitialized stake account",
                        ADDRESS_RW,
                    ),
                    ("rent_sysvar", "Rent sysvar", ADDRESS_READ_ONLY),
                ],
                "initialize",
                "Initialize",
            )
        elif instruction_id == INS_AUTHORIZE:
            return Instruction(
                raw_instruction,
                INS_AUTHORIZE,
                [
                    ("pubkey", "pubkey"),
                    ("stakeauthorize", "stakeauthorize"),
                ],
                [
                    ("stake_account", "Stake account", ADDRESS_RW),
                    ("clock_sysvar", "Clock sysvar", ADDRESS_READ_ONLY),
                    (
                        "stake_or_withdraw_authority",
                        "stake or withdraw authority",
                        ADDRESS_SIG_READ_ONLY,
                    ),
                    (
                        "lockup_authority",
                        "Lockup authority",
                        ADDRESS_SIG_READ_ONLY,
                        True,
                    ),
                ],
                "authorize",
                "Authorize",
            )
        elif instruction_id == INS_DELEGATE_STAKE:
            return Instruction(
                raw_instruction,
                INS_DELEGATE_STAKE,
                [],
                [
                    (
                        "initialized_stake_account",
                        "Initialized stake account",
                        ADDRESS_RW,
                    ),
                    ("vote_account", "Vote account", ADDRESS_READ_ONLY),
                    ("clock_sysvar", "Clock sysvar", ADDRESS_READ_ONLY),
                    ("stake_history_sysvar", "Stake history sysvar", ADDRESS_READ_ONLY),
                    ("config_account", "config account", ADDRESS_READ_ONLY),
                    ("stake_authority", "Stake authority", ADDRESS_SIG_READ_ONLY),
                ],
                "delegate_stake",
                "Delegate Stake",
            )
        elif instruction_id == INS_SPLIT:
            return Instruction(
                raw_instruction,
                INS_SPLIT,
                [
                    ("lamports", "u64"),
                ],
                [
                    ("stake_account", "Stake account", ADDRESS_RW),
                    (
                        "uninitialized_stake_account",
                        "Uninitialized stake account",
                        ADDRESS_RW,
                    ),
                    ("stake_authority", "Stake authority", ADDRESS_SIG_READ_ONLY),
                ],
                "split",
                "Split",
            )
        elif instruction_id == INS_WITHDRAW:
            return Instruction(
                raw_instruction,
                INS_WITHDRAW,
                [
                    ("lamports", "u64"),
                ],
                [
                    ("stake_account", "Stake account", ADDRESS_RW),
                    ("recipient_account", "Recipient account", ADDRESS_RW),
                    ("clock_sysvar", "Clock sysvar", ADDRESS_READ_ONLY),
                    ("stake_history_sysvar", "Stake history sysvar", ADDRESS_READ_ONLY),
                    ("withdraw_authority", "Withdraw authority", ADDRESS_SIG_READ_ONLY),
                    (
                        "lockup_authority",
                        "Lockup authority",
                        ADDRESS_SIG_READ_ONLY,
                        True,
                    ),
                ],
                "withdraw",
                "Withdraw",
            )
        elif instruction_id == INS_DEACTIVATE:
            return Instruction(
                raw_instruction,
                INS_DEACTIVATE,
                [],
                [
                    ("delegated_stake_account", "Delegated stake account", ADDRESS_RW),
                    ("clock_sysvar", "Clock sysvar", ADDRESS_READ_ONLY),
                    ("stake_authority", "Stake authority", ADDRESS_SIG_READ_ONLY),
                ],
                "deactivate",
                "Deactivate",
            )
        elif instruction_id == INS_SET_LOCKUP:
            return Instruction(
                raw_instruction,
                INS_SET_LOCKUP,
                [
                    ("unix_timestamp", "i64"),
                    ("epoch", "u64"),
                    ("custodian", "pubkey"),
                ],
                [
                    (
                        "initialized_stake_account",
                        "Initialized stake account",
                        ADDRESS_RW,
                    ),
                    (
                        "lockup_authority_or_withdraw_authority",
                        "Lockup authority or withdraw authority",
                        ADDRESS_SIG_READ_ONLY,
                    ),
                ],
                "set_lockup",
                "Set Lockup",
            )
        elif instruction_id == INS_MERGE:
            return Instruction(
                raw_instruction,
                INS_MERGE,
                [],
                [
                    (
                        "destination_stake_account",
                        "Destination stake account",
                        ADDRESS_RW,
                    ),
                    ("source_stake_account", "Source stake account", ADDRESS_RW),
                    ("clock_sysvar", "Clock sysvar", ADDRESS_READ_ONLY),
                    ("stake_history_sysvar", "Stake history sysvar", ADDRESS_READ_ONLY),
                    ("stake_authority", "Stake authority", ADDRESS_SIG_READ_ONLY),
                ],
                "merge",
                "Merge",
            )
        elif instruction_id == INS_AUTHORIZE_WITH_SEED:
            return Instruction(
                raw_instruction,
                INS_AUTHORIZE_WITH_SEED,
                [
                    ("new_authorized_pubkey", "pubkey"),
                    ("stake_authorize", "stakeauthorize"),
                    ("authority_seed", "string"),
                    ("authority_owner", "pubkey"),
                ],
                [
                    ("stake_account", "Stake account", ADDRESS_RW),
                    (
                        "stake_or_withdraw_authority",
                        "stake or withdraw authority",
                        ADDRESS_SIG_READ_ONLY,
                    ),
                    ("clock_sysvar", "Clock sysvar", ADDRESS_READ_ONLY),
                    (
                        "lockup_authority",
                        "Lockup authority",
                        ADDRESS_SIG_READ_ONLY,
                        True,
                    ),
                ],
                "authorize_with_seed",
                "Authorize With Seed",
            )
        elif instruction_id == INS_INITIALIZE_CHECKED:
            return Instruction(
                raw_instruction,
                INS_INITIALIZE_CHECKED,
                [],
                [
                    (
                        "uninitialized_stake_account",
                        "Uninitialized stake account",
                        ADDRESS_RW,
                    ),
                    ("rent_sysvar", "Rent sysvar", ADDRESS_READ_ONLY),
                    ("stake_authority", "stake authority", ADDRESS_READ_ONLY),
                    ("withdraw_authority", "withdraw authority", ADDRESS_SIG_READ_ONLY),
                ],
                "initialize_checked",
                "Initialize Checked",
            )
        elif instruction_id == INS_AUTHORIZE_CHECKED:
            return Instruction(
                raw_instruction,
                INS_AUTHORIZE_CHECKED,
                [
                    ("stakeauthorize", "stakeauthorize"),
                ],
                [
                    ("stake_account", "Stake account", ADDRESS_RW),
                    ("clock_sysvar", "Clock sysvar", ADDRESS_READ_ONLY),
                    (
                        "stake_or_withdraw_authority",
                        "stake or withdraw authority",
                        ADDRESS_SIG_READ_ONLY,
                    ),
                    (
                        "new_stake_or_withdraw_authority",
                        "new stake or withdraw authority",
                        ADDRESS_SIG_READ_ONLY,
                    ),
                    (
                        "lockup_authority",
                        "Lockup authority",
                        ADDRESS_SIG_READ_ONLY,
                        True,
                    ),
                ],
                "authorize_checked",
                "Authorize Checked",
            )
        elif instruction_id == INS_AUTHORIZE_CHECKED_WITH_SEED:
            return Instruction(
                raw_instruction,
                INS_AUTHORIZE_CHECKED_WITH_SEED,
                [
                    ("stake_authorize", "stakeauthorize"),
                    ("authority_seed", "string"),
                    ("authority_owner", "pubkey"),
                ],
                [
                    ("stake_account", "Stake account", ADDRESS_RW),
                    (
                        "stake_or_withdraw_authority",
                        "stake or withdraw authority",
                        ADDRESS_SIG_READ_ONLY,
                    ),
                    ("clock_sysvar", "Clock sysvar", ADDRESS_READ_ONLY),
                    (
                        "new_stake_or_withdraw_authority",
                        "new stake or withdraw authority",
                        ADDRESS_SIG_READ_ONLY,
                    ),
                    (
                        "lockup_authority",
                        "Lockup authority",
                        ADDRESS_SIG_READ_ONLY,
                        True,
                    ),
                ],
                "authorize_checked_with_seed",
                "Authorize Checked With Seed",
            )
        elif instruction_id == INS_SET_LOCKUP_CHECKED:
            return Instruction(
                raw_instruction,
                INS_SET_LOCKUP_CHECKED,
                [
                    ("unix_timestamp", "i64"),
                    ("epoch", "u64"),
                ],
                [
                    ("stake_account", "stake account", ADDRESS_RW),
                    (
                        "lockup_authority_or_withdraw_authority",
                        "Lockup authority or withdraw authority",
                        ADDRESS_SIG_READ_ONLY,
                    ),
                    (
                        "new_lockup_authority",
                        "New lockup authority",
                        ADDRESS_SIG_READ_ONLY,
                        True,
                    ),
                ],
                "set_lockup_checked",
                "Set Lockup Checked",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {encoded_program_id} {instruction_id}"
            )
    if encoded_program_id == COMPUTE_BUDGET_PROGRAM_ID:
        if instruction_id == INS_REQUEST_HEAP_FRAME:
            return Instruction(
                raw_instruction,
                INS_REQUEST_HEAP_FRAME,
                [
                    ("bytes", "u32"),
                ],
                [],
                "request_heap_frame",
                "Request Heap Frame",
            )
        elif instruction_id == INS_SET_COMPUTE_UNIT_LIMIT:
            return Instruction(
                raw_instruction,
                INS_SET_COMPUTE_UNIT_LIMIT,
                [
                    ("units", "u32"),
                ],
                [],
                "set_compute_unit_limit",
                "Set Compute Unit Limit",
            )
        elif instruction_id == INS_SET_COMPUTE_UNIT_PRICE:
            return Instruction(
                raw_instruction,
                INS_SET_COMPUTE_UNIT_PRICE,
                [
                    ("lamports", "u64"),
                ],
                [],
                "set_compute_unit_price",
                "Set Compute Unit Price",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {encoded_program_id} {instruction_id}"
            )
    else:
        raise ProcessError(
            f"Unknown instruction type: {encoded_program_id} {instruction_id}"
        )
