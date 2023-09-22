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

INS_CREATE_ACCOUNT = 0
INS_ASSIGN = 1
INS_TRANSFER = 2
INS_INITIALIZE = 0


def __getattr__(name: str) -> Type[Instruction]:
    ids = {
        "CreateAccountInstruction": ("11111111111111111111111111111111", 0),
        "AssignInstruction": ("11111111111111111111111111111111", 1),
        "TransferInstruction": ("11111111111111111111111111111111", 2),
        "InitializeInstruction": ("Stake11111111111111111111111111111111111111", 0),
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
        owner: Account

        funding_account: Account
        new_account: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["CreateAccountInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class AssignInstruction(Instruction):
        PROGRAM_ID = SYSTEM_PROGRAM_ID
        INSTRUCTION_ID = INS_ASSIGN

        owner: Account

        assigned_account: Account

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

        funding_account: Account
        recipient_account: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["TransferInstruction"]:
            return (
                ins.program_id == cls.PROGRAM_ID
                and ins.instruction_id == cls.INSTRUCTION_ID
            )

    class InitializeInstruction(Instruction):
        PROGRAM_ID = STAKE_PROGRAM_ID
        INSTRUCTION_ID = INS_INITIALIZE

        staker: Account
        withdrawer: Account
        unix_timestamp: int
        epoch: int
        custodian: Account

        uninitialized_stake_account: Account
        rent_sysvar: Account

        @classmethod
        def is_type_of(cls, ins: Any) -> TypeGuard["InitializeInstruction"]:
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
                {
                    "lamports": {
                        "ui_name": "Lamports",
                        "type": "u64",
                        "optional": False,
                    },
                    "space": {"ui_name": "Space", "type": "u64", "optional": False},
                    "owner": {
                        "ui_name": "Owner",
                        "type": "authority",
                        "optional": False,
                    },
                },
                {
                    "funding_account": {
                        "ui_name": "Funding account",
                        "is_authority": True,
                        "optional": False,
                    },
                    "new_account": {
                        "ui_name": "New account",
                        "is_authority": False,
                        "optional": False,
                    },
                },
                ["lamports", "owner"],
                ["funding_account"],
                "ui_confirm",
                "Create Account",
            )
        elif instruction_id == INS_ASSIGN:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_ASSIGN,
                {"owner": {"ui_name": "Owner", "type": "authority", "optional": False}},
                {
                    "assigned_account": {
                        "ui_name": "Assigned account",
                        "is_authority": True,
                        "optional": False,
                    }
                },
                ["owner"],
                ["assigned_account"],
                "ui_confirm",
                "Assign",
            )
        elif instruction_id == INS_TRANSFER:
            return Instruction(
                instruction_data,
                program_id,
                instruction_accounts,
                INS_TRANSFER,
                {"lamports": {"ui_name": "Lamports", "type": "u64", "optional": False}},
                {
                    "funding_account": {
                        "ui_name": "Funding account",
                        "is_authority": True,
                        "optional": False,
                    },
                    "recipient_account": {
                        "ui_name": "Recipient account",
                        "is_authority": False,
                        "optional": False,
                    },
                },
                ["lamports"],
                ["funding_account", "recipient_account"],
                "ui_confirm",
                "Transfer",
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
                {
                    "staker": {
                        "ui_name": "Staker",
                        "type": "authority",
                        "optional": False,
                    },
                    "withdrawer": {
                        "ui_name": "Withdrawer",
                        "type": "authority",
                        "optional": False,
                    },
                    "unix_timestamp": {
                        "ui_name": "Unix timestamp",
                        "type": "i64",
                        "optional": False,
                    },
                    "epoch": {"ui_name": "Epoch", "type": "u64", "optional": False},
                    "custodian": {
                        "ui_name": "Custodian",
                        "type": "authority",
                        "optional": False,
                    },
                },
                {
                    "uninitialized_stake_account": {
                        "ui_name": "Uninitialized stake account",
                        "is_authority": False,
                        "optional": False,
                    },
                    "rent_sysvar": {
                        "ui_name": "Rent sysvar",
                        "is_authority": False,
                        "optional": False,
                    },
                },
                ["staker", "unix_timestamp", "epoch", "custodian"],
                ["uninitialized_stake_account", "rent_sysvar"],
                "ui_confirm",
                "Initialize",
            )
        else:
            raise ProcessError(
                f"Unknown instruction type: {program_id} {instruction_id}"
            )
    else:
        raise ProcessError(f"Unknown instruction type: {program_id} {instruction_id}")
