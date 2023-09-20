# generated from __init__.py.mako
# do not edit manually!
from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.wire import ProcessError

from .instruction import Instruction

if TYPE_CHECKING:
    from typing import Any, Type, TypeGuard
    from ..types import Account

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
    program_id: bytes,
    instruction_id: int,
    instruction_accounts: list[Account],
    instruction_data: bytes,
) -> Instruction:
    if base58.encode(program_id) == SYSTEM_PROGRAM_ID:
        if instruction_id == INS_CREATE_ACCOUNT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_CREATE_ACCOUNT,
                [
                    {"name": "lamports", "type": "u64", "optional": False},
                    {"name": "space", "type": "u64", "optional": False},
                    {"name": "owner", "type": "pubkey", "optional": False},
                ],
                [
                    {
                        "name": "Funding account",
                        "access": "w",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "New account",
                        "access": "w",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [0, 2],
                [0],
                "ui_confirm",
                "Create Account",
            )
        elif instruction_id == INS_ASSIGN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_ASSIGN,
                [{"name": "owner", "type": "pubkey", "optional": False}],
                [
                    {
                        "name": "Assigned account",
                        "access": "w",
                        "signer": True,
                        "optional": False,
                    }
                ],
                [0],
                [0],
                "ui_confirm",
                "Assign",
            )
        elif instruction_id == INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_TRANSFER,
                [{"name": "lamports", "type": "u64", "optional": False}],
                [
                    {
                        "name": "Funding account",
                        "access": "w",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "Recipient account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                ],
                [0],
                [0, 1],
                "ui_confirm",
                "Transfer",
            )
        elif instruction_id == INS_CREATE_ACCOUNT_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_CREATE_ACCOUNT_WITH_SEED,
                [
                    {"name": "base", "type": "pubkey", "optional": False},
                    {"name": "seed", "type": "string", "optional": False},
                    {"name": "lamports", "type": "u64", "optional": False},
                    {"name": "space", "type": "u64", "optional": False},
                    {"name": "owner", "type": "pubkey", "optional": False},
                ],
                [
                    {
                        "name": "Funding account",
                        "access": "w",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "Created account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Base account",
                        "access": "",
                        "signer": True,
                        "optional": True,
                    },
                ],
                [0, 2, 3],
                [0, 2],
                "ui_confirm",
                "Create Account With Seed",
            )
        elif instruction_id == INS_ALLOCATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_ALLOCATE,
                [{"name": "space", "type": "u64", "optional": False}],
                [
                    {
                        "name": "New account",
                        "access": "w",
                        "signer": True,
                        "optional": False,
                    }
                ],
                [0],
                [0],
                "ui_confirm",
                "Allocate",
            )
        elif instruction_id == INS_ALLOCATE_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_ALLOCATE_WITH_SEED,
                [
                    {"name": "base", "type": "pubkey", "optional": False},
                    {"name": "seed", "type": "string", "optional": False},
                    {"name": "space", "type": "u64", "optional": False},
                    {"name": "owner", "type": "pubkey", "optional": False},
                ],
                [
                    {
                        "name": "Allocated account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Base account",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [0, 2],
                [0, 1],
                "ui_confirm",
                "Allocate With Seed",
            )
        elif instruction_id == INS_ASSIGN_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_ASSIGN_WITH_SEED,
                [
                    {"name": "base", "type": "pubkey", "optional": False},
                    {"name": "seed", "type": "string", "optional": False},
                    {"name": "owner", "type": "pubkey", "optional": False},
                ],
                [
                    {
                        "name": "Assigned account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Base account",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [0, 2],
                [0, 1],
                "ui_confirm",
                "Assign With Seed",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} {instruction_id}"
            )
    if base58.encode(program_id) == STAKE_PROGRAM_ID:
        if instruction_id == INS_INITIALIZE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_INITIALIZE,
                [
                    {"name": "staker", "type": "pubkey", "optional": False},
                    {"name": "withdrawer", "type": "pubkey", "optional": False},
                    {"name": "unix_timestamp", "type": "i64", "optional": False},
                    {"name": "epoch", "type": "u64", "optional": False},
                    {"name": "custodian", "type": "pubkey", "optional": False},
                ],
                [
                    {
                        "name": "Uninitialized stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Rent sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                ],
                [0, 2, 3, 4],
                [0, 1],
                "ui_confirm",
                "Initialize",
            )
        elif instruction_id == INS_AUTHORIZE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_AUTHORIZE,
                [
                    {"name": "pubkey", "type": "pubkey", "optional": False},
                    {
                        "name": "stakeauthorize",
                        "type": "StakeAuthorize",
                        "optional": False,
                    },
                ],
                [
                    {
                        "name": "Stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Clock sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "stake or withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "Lockup authority",
                        "access": "",
                        "signer": True,
                        "optional": True,
                    },
                ],
                [0],
                [0, 1, 2, 3],
                "ui_confirm",
                "Authorize",
            )
        elif instruction_id == INS_DELEGATE_STAKE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_DELEGATE_STAKE,
                [],
                [
                    {
                        "name": "Initialized stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Vote account",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Clock sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Stake history sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "config account",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Stake authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [],
                [0, 2, 3, 4, 5],
                "ui_confirm",
                "Delegate Stake",
            )
        elif instruction_id == INS_SPLIT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_SPLIT,
                [{"name": "lamports", "type": "u64", "optional": False}],
                [
                    {
                        "name": "Stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Uninitialized stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Stake authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [0],
                [2],
                "ui_confirm",
                "Split",
            )
        elif instruction_id == INS_WITHDRAW:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_WITHDRAW,
                [{"name": "lamports", "type": "u64", "optional": False}],
                [
                    {
                        "name": "Stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Recipient account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Clock sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Stake history sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "Lockup authority",
                        "access": "",
                        "signer": True,
                        "optional": True,
                    },
                ],
                [0],
                [0, 1],
                "ui_confirm",
                "Withdraw",
            )
        elif instruction_id == INS_DEACTIVATE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_DEACTIVATE,
                [],
                [
                    {
                        "name": "Delegated stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Clock sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Stake authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [],
                [0, 1, 2],
                "ui_confirm",
                "Deactivate",
            )
        elif instruction_id == INS_SET_LOCKUP:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_SET_LOCKUP,
                [
                    {"name": "unix_timestamp", "type": "i64", "optional": True},
                    {"name": "epoch", "type": "u64", "optional": True},
                    {"name": "custodian", "type": "pubkey", "optional": True},
                ],
                [
                    {
                        "name": "Initialized stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Lockup authority or withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [0, 2],
                [0],
                "ui_confirm",
                "Set Lockup",
            )
        elif instruction_id == INS_MERGE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_MERGE,
                [],
                [
                    {
                        "name": "Destination stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Source stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Clock sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Stake history sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Stake authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [],
                [0],
                "ui_confirm",
                "Merge",
            )
        elif instruction_id == INS_AUTHORIZE_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_AUTHORIZE_WITH_SEED,
                [
                    {
                        "name": "new_authorized_pubkey",
                        "type": "pubkey",
                        "optional": False,
                    },
                    {
                        "name": "stake_authorize",
                        "type": "StakeAuthorize",
                        "optional": False,
                    },
                    {"name": "authority_seed", "type": "string", "optional": False},
                    {"name": "authority_owner", "type": "pubkey", "optional": False},
                ],
                [
                    {
                        "name": "Stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "stake or withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "Clock sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Lockup authority",
                        "access": "",
                        "signer": True,
                        "optional": True,
                    },
                ],
                [0, 2],
                [0],
                "ui_confirm",
                "Authorize With Seed",
            )
        elif instruction_id == INS_INITIALIZE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_INITIALIZE_CHECKED,
                [],
                [
                    {
                        "name": "Uninitialized stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Rent sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "stake authority",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                ],
                [],
                [0, 1, 2, 3],
                "ui_confirm",
                "Initialize Checked",
            )
        elif instruction_id == INS_AUTHORIZE_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_AUTHORIZE_CHECKED,
                [
                    {
                        "name": "stakeauthorize",
                        "type": "StakeAuthorize",
                        "optional": False,
                    }
                ],
                [
                    {
                        "name": "Stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Clock sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "stake or withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "new stake or withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "Lockup authority",
                        "access": "",
                        "signer": True,
                        "optional": True,
                    },
                ],
                [0],
                [0, 1, 2],
                "ui_confirm",
                "Authorize Checked",
            )
        elif instruction_id == INS_AUTHORIZE_CHECKED_WITH_SEED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_AUTHORIZE_CHECKED_WITH_SEED,
                [
                    {
                        "name": "stake_authorize",
                        "type": "StakeAuthorize",
                        "optional": False,
                    },
                    {"name": "authority_seed", "type": "string", "optional": False},
                    {"name": "authority_owner", "type": "pubkey", "optional": False},
                ],
                [
                    {
                        "name": "Stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "stake or withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "Clock sysvar",
                        "access": "",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "new stake or withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "Lockup authority",
                        "access": "",
                        "signer": True,
                        "optional": True,
                    },
                ],
                [0, 2],
                [0],
                "ui_confirm",
                "Authorize Checked With Seed",
            )
        elif instruction_id == INS_SET_LOCKUP_CHECKED:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_SET_LOCKUP_CHECKED,
                [
                    {"name": "unix_timestamp", "type": "i64", "optional": True},
                    {"name": "epoch", "type": "u64", "optional": True},
                ],
                [
                    {
                        "name": "stake account",
                        "access": "w",
                        "signer": False,
                        "optional": False,
                    },
                    {
                        "name": "Lockup authority or withdraw authority",
                        "access": "",
                        "signer": True,
                        "optional": False,
                    },
                    {
                        "name": "New lockup authority",
                        "access": "",
                        "signer": True,
                        "optional": True,
                    },
                ],
                [0, 1],
                [0],
                "ui_confirm",
                "Set Lockup Checked",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} {instruction_id}"
            )
    if base58.encode(program_id) == COMPUTE_BUDGET_PROGRAM_ID:
        if instruction_id == INS_REQUEST_HEAP_FRAME:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_REQUEST_HEAP_FRAME,
                [{"name": "bytes", "type": "u32", "optional": False}],
                [],
                [0],
                [],
                "ui_confirm",
                "Request Heap Frame",
            )
        elif instruction_id == INS_SET_COMPUTE_UNIT_LIMIT:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_SET_COMPUTE_UNIT_LIMIT,
                [{"name": "units", "type": "u32", "optional": False}],
                [],
                [0],
                [],
                "ui_confirm",
                "Set Compute Unit Limit",
            )
        elif instruction_id == INS_SET_COMPUTE_UNIT_PRICE:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_SET_COMPUTE_UNIT_PRICE,
                [{"name": "lamports", "type": "u64", "optional": False}],
                [],
                [0],
                [],
                "ui_confirm",
                "Set Compute Unit Price",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} {instruction_id}"
            )
    else:
        raise ProcessError(f"Unknown instruction type: {program_id} {instruction_id}")
