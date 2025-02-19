from typing import TYPE_CHECKING

from trezor.crypto import base58

from .transaction import Transaction
from .transaction.instructions import (
    AssociatedTokenAccountProgramCreateInstruction,
    Instruction,
    Token2022ProgramTransferCheckedInstruction,
    TokenProgramTransferCheckedInstruction,
)
from .types import StakeType

if TYPE_CHECKING:
    from trezor.messages import SolanaTxAdditionalInfo

    TransferTokenInstruction = (
        TokenProgramTransferCheckedInstruction
        | Token2022ProgramTransferCheckedInstruction
    )


def get_token_transfer_instructions(
    instructions: list[Instruction],
) -> list[TransferTokenInstruction]:
    return [
        instruction
        for instruction in instructions
        if TokenProgramTransferCheckedInstruction.is_type_of(instruction)
        or Token2022ProgramTransferCheckedInstruction.is_type_of(instruction)
    ]


def get_create_associated_token_account_instructions(
    instructions: list[Instruction],
) -> list[AssociatedTokenAccountProgramCreateInstruction]:
    return [
        instruction
        for instruction in instructions
        if AssociatedTokenAccountProgramCreateInstruction.is_type_of(instruction)
    ]


def is_transaction_staking(instructions: list[Instruction]) -> bool:
    from .transaction.instructions import (
        ComputeBudgetProgramSetComputeUnitPriceInstruction,
        StakeProgramDelegateStakeInstruction,
        StakeProgramInitializeInstruction,
        SystemProgramCreateAccountWithSeedInstruction,
    )

    return (
        len(instructions) == 4
        and ComputeBudgetProgramSetComputeUnitPriceInstruction.is_type_of(
            instructions[0]
        )
        and SystemProgramCreateAccountWithSeedInstruction.is_type_of(instructions[1])
        and StakeProgramInitializeInstruction.is_type_of(instructions[2])
        and StakeProgramDelegateStakeInstruction.is_type_of(instructions[3])
    )


def is_transaction_unstaking(instructions: list[Instruction]) -> bool:
    from .transaction.instructions import (
        ComputeBudgetProgramSetComputeUnitPriceInstruction,
        StakeProgramDeactivateInstruction,
    )

    return (
        len(instructions) == 2
        and ComputeBudgetProgramSetComputeUnitPriceInstruction.is_type_of(
            instructions[0]
        )
        and StakeProgramDeactivateInstruction.is_type_of(instructions[1])
    )


def is_transaction_claiming(instructions: list[Instruction]) -> bool:
    from .transaction.instructions import (
        ComputeBudgetProgramSetComputeUnitPriceInstruction,
        StakeProgramWithdrawInstruction,
    )

    return (
        len(instructions) == 2
        and ComputeBudgetProgramSetComputeUnitPriceInstruction.is_type_of(
            instructions[0]
        )
        and StakeProgramWithdrawInstruction.is_type_of(instructions[1])
    )


def get_transaction_stake_type(instructions: list[Instruction]) -> StakeType | None:
    if is_transaction_staking(instructions):
        return StakeType.Stake
    elif is_transaction_unstaking(instructions):
        return StakeType.Unstake
    elif is_transaction_claiming(instructions):
        return StakeType.Claim
    else:
        return None


def is_predefined_token_transfer(
    instructions: list[Instruction],
) -> bool:
    """
    Checks that the transaction consists of one or zero create token account instructions
    and one or more transfer token instructions. Also checks that the token program, token mint
    and destination in the instructions are the same. I.e. valid instructions can be:

    [transfer]
    [transfer, *transfer]
    [create account, transfer]
    [create account, transfer, *transfer]
    """
    create_token_account_instructions = (
        get_create_associated_token_account_instructions(instructions)
    )
    transfer_token_instructions = get_token_transfer_instructions(instructions)

    if len(create_token_account_instructions) + len(transfer_token_instructions) != len(
        instructions
    ):
        # there are also other instructions
        return False

    if len(create_token_account_instructions) > 1:
        # there is more than one create token account instruction
        return False

    if (
        len(create_token_account_instructions) == 1
        and instructions[0] != create_token_account_instructions[0]
    ):
        # create account instruction has to be the first instruction
        return False

    if len(transfer_token_instructions) == 0:
        # there are no transfer token instructions
        return False

    token_program = transfer_token_instructions[0].program_id
    token_mint = transfer_token_instructions[0].token_mint[0]
    token_account = transfer_token_instructions[0].destination_account[0]
    owner = transfer_token_instructions[0].owner[0]

    for transfer_token_instruction in transfer_token_instructions:
        if (
            transfer_token_instruction.program_id != token_program
            or transfer_token_instruction.token_mint[0] != token_mint
            or transfer_token_instruction.destination_account[0] != token_account
            or transfer_token_instruction.owner[0] != owner
        ):
            # there are different token accounts, don't handle as predefined
            return False

    # at this point there can only be zero or one create token account instructions
    create_token_account_instruction = (
        create_token_account_instructions[0]
        if len(create_token_account_instructions) == 1
        else None
    )

    if create_token_account_instruction is not None and (
        create_token_account_instruction.spl_token[0] != base58.decode(token_program)
        or create_token_account_instruction.token_mint[0] != token_mint
        or create_token_account_instruction.associated_token_account[0] != token_account
    ):
        # there are different token accounts, don't handle as predefined
        return False

    return True


async def try_confirm_token_transfer_transaction(
    transaction: Transaction,
    fee: int,
    signer_path: list[int],
    blockhash: bytes,
    additional_info: SolanaTxAdditionalInfo | None = None,
) -> bool:
    from .layout import confirm_token_transfer
    from .token_account import try_get_token_account_base_address

    visible_instructions = transaction.get_visible_instructions()
    if not is_predefined_token_transfer(
        visible_instructions,
    ):
        return False

    transfer_token_instructions = get_token_transfer_instructions(visible_instructions)

    # in is_predefined_token_transfer we made sure that these values are the same
    # for all the transfer token instructions
    token_program = base58.decode(transfer_token_instructions[0].program_id)
    token_mint = transfer_token_instructions[0].token_mint[0]
    token_account = transfer_token_instructions[0].destination_account[0]

    base_address = (
        try_get_token_account_base_address(
            token_account,
            token_program,
            token_mint,
            additional_info.token_accounts_infos,
        )
        if additional_info is not None
        else None
    )

    total_token_amount = sum(
        [
            transfer_token_instruction.amount
            for transfer_token_instruction in transfer_token_instructions
        ]
    )

    await confirm_token_transfer(
        token_account if base_address is None else base_address,
        token_account,
        token_mint,
        total_token_amount,
        transfer_token_instructions[0].decimals,
        fee,
        signer_path,
        blockhash,
    )
    return True


async def try_confirm_predefined_transaction(
    transaction: Transaction,
    fee: int,
    signer_path: list[int],
    blockhash: bytes,
    additional_info: SolanaTxAdditionalInfo | None = None,
) -> bool:
    from .layout import confirm_system_transfer
    from .transaction.instructions import SystemProgramTransferInstruction

    instructions = transaction.get_visible_instructions()
    instructions_count = len(instructions)

    for instruction in instructions:
        if instruction.multisig_signers:
            return False

    if instructions_count == 1:
        if SystemProgramTransferInstruction.is_type_of(instructions[0]):
            await confirm_system_transfer(instructions[0], fee, signer_path, blockhash)
            return True

    stake_type = get_transaction_stake_type(transaction.instructions)
    if stake_type is not None:
        await confirm_stake_type_transaction(transaction, stake_type)
        return True

    return await try_confirm_token_transfer_transaction(
        transaction, fee, signer_path, blockhash, additional_info
    )


async def confirm_stake_type_transaction(
    transaction: Transaction, stake_type: StakeType
) -> None:
    from .layout import (
        confirm_claim_transaction,
        confirm_stake_transaction,
        confirm_unstake_transaction,
    )

    # TODO: extract and pass proper info to layout functions
    if stake_type == StakeType.Stake:
        await confirm_stake_transaction()
    elif stake_type == StakeType.Unstake:
        await confirm_unstake_transaction()
    elif stake_type == StakeType.Claim:
        await confirm_claim_transaction()
    else:
        raise ValueError("Invalid stake type")  # TODO
