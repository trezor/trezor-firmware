# generated from __init__.py.mako
# do not edit manually!

from enum import IntEnum

from construct import Int32ul, Int64ul, Struct, Switch

from .custom_constructs import (
    AccountReference,
    Accounts,
    InstructionData,
    InstructionProgramId,
    PublicKey,
)


class Program:
    SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
    STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"


class SystemprogramInstruction(IntEnum):
    INS_CREATE_ACCOUNT = 0
    INS_ASSIGN = 1
    INS_TRANSFER = 2


class StakeprogramInstruction(IntEnum):
    INS_INITIALIZE = 0


_SYSTEM_PROGRAM_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        SystemprogramInstruction.INS_CREATE_ACCOUNT: Accounts(
            "funding_account" / AccountReference(),
            "new_account" / AccountReference(),
        ),
        SystemprogramInstruction.INS_ASSIGN: Accounts(
            "assigned_account" / AccountReference(),
        ),
        SystemprogramInstruction.INS_TRANSFER: Accounts(
            "funding_account" / AccountReference(),
            "recipient_account" / AccountReference(),
        ),
    },
)
_STAKE_PROGRAM_ACCOUNTS = Switch(
    lambda this: this.data["instruction_id"],
    {
        StakeprogramInstruction.INS_INITIALIZE: Accounts(
            "uninitialized_stake_account" / AccountReference(),
            "rent_sysvar" / AccountReference(),
        ),
    },
)

_SYSTEM_PROGRAM_PARAMETERS = InstructionData(
    "instruction_id" / Int32ul,
    "parameters"
    / Switch(
        lambda this: this.instruction_id,
        {
            SystemprogramInstruction.INS_CREATE_ACCOUNT: Struct(
                "lamports" / Int64ul,
                "space" / Int64ul,
                "owner" / PublicKey(),
            ),
            SystemprogramInstruction.INS_ASSIGN: Struct(
                "owner" / PublicKey(),
            ),
            SystemprogramInstruction.INS_TRANSFER: Struct(
                "lamports" / Int64ul,
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
            StakeprogramInstruction.INS_INITIALIZE: Struct(
                "staker" / PublicKey(),
                "withdrawer" / PublicKey(),
                "unix_timestamp" / Int64ul,
                "epoch" / Int64ul,
                "custodian" / PublicKey(),
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
        },
    ),
    "data"
    / Switch(
        lambda this: this.program_id,
        {
            Program.SYSTEM_PROGRAM_ID: _SYSTEM_PROGRAM_PARAMETERS,
            Program.STAKE_PROGRAM_ID: _STAKE_PROGRAM_PARAMETERS,
        },
    ),
)


def replace_account_placeholders(construct):
    for ins in construct["instructions"]:
        program_id = Program.__dict__[ins["program_id"]]
        if program_id == Program.SYSTEM_PROGRAM_ID:
            ins["data"]["instruction_id"] = SystemprogramInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value
        elif program_id == Program.STAKE_PROGRAM_ID:
            ins["data"]["instruction_id"] = StakeprogramInstruction.__dict__[
                ins["data"]["instruction_id"]
            ].value

        ins["program_id"] = program_id

    return construct
