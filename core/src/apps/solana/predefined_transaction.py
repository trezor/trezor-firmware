from typing import TYPE_CHECKING

from trezor.crypto import base58

from .transaction import Transaction
from .transaction.instructions import (
    _SYSTEM_PROGRAM_ID,
    AssociatedTokenAccountProgramCreateInstruction,
    Instruction,
    Token2022ProgramTransferCheckedInstruction,
    TokenProgramTransferCheckedInstruction,
)

if TYPE_CHECKING:
    from typing import Type

    from .transaction import Fee
    from .types import AdditionalTxInfo

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
    fee: Fee,
    signer_path: list[int],
    blockhash: bytes,
    additional_info: AdditionalTxInfo,
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

    base_address = try_get_token_account_base_address(
        token_account,
        token_program,
        token_mint,
        additional_info.token_accounts_infos,
    )

    total_token_amount = sum(
        [
            transfer_token_instruction.amount
            for transfer_token_instruction in transfer_token_instructions
        ]
    )

    token = additional_info.definitions.get_token(token_mint)
    await confirm_token_transfer(
        token_account if base_address is None else base_address,
        token_account,
        token,
        total_token_amount,
        transfer_token_instructions[0].decimals,
        fee,
        blockhash,
    )
    return True


async def try_confirm_predefined_transaction(
    transaction: Transaction,
    fee: Fee,
    signer_path: list[int],
    signer_public_key: bytes,
    blockhash: bytes,
    additional_info: AdditionalTxInfo,
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
            await confirm_system_transfer(instructions[0], fee, blockhash)
            return True

    if await try_confirm_staking_transaction(
        transaction,
        fee,
        signer_path,
        signer_public_key,
        blockhash,
    ):
        return True

    return await try_confirm_token_transfer_transaction(
        transaction,
        fee,
        signer_path,
        blockhash,
        additional_info,
    )


async def try_confirm_staking_transaction(
    transaction: Transaction,
    fee: Fee,
    signer_path: list[int],
    signer_public_key: bytes,
    blockhash: bytes,
) -> bool:
    from .transaction.instructions import (
        StakeProgramDeactivateInstruction,
        StakeProgramDelegateStakeInstruction,
        StakeProgramInitializeInstruction,
        StakeProgramWithdrawInstruction,
        SystemProgramCreateAccountWithSeedInstruction,
    )

    instructions = transaction.get_visible_instructions()
    if not instructions:
        return False

    def _match_instructions(*expected_types: Type[Instruction]) -> bool:
        if len(instructions) != len(expected_types):
            return False
        return all(
            expected_type.is_type_of(instruction)
            for instruction, expected_type in zip(instructions, expected_types)
        )

    if _match_instructions(
        SystemProgramCreateAccountWithSeedInstruction,
        StakeProgramInitializeInstruction,
        StakeProgramDelegateStakeInstruction,
    ):
        from .layout import confirm_stake_transaction, confirm_stake_withdrawer

        create, init, delegate = instructions
        if signer_public_key != create.funding_account[0]:
            return False
        if signer_public_key != create.base:
            return False
        if signer_public_key != init.withdrawer:
            await confirm_stake_withdrawer(init.withdrawer)
        if signer_public_key != init.staker:
            return False
        if signer_public_key != delegate.stake_authority[0]:
            return False

        if base58.encode(init.custodian) != _SYSTEM_PROGRAM_ID:
            return False

        stake_account = create.created_account[0]
        if stake_account != init.uninitialized_stake_account[0]:
            return False
        if stake_account != delegate.initialized_stake_account[0]:
            return False

        await confirm_stake_transaction(
            fee=fee,
            signer_path=signer_path,
            blockhash=blockhash,
            create=create,
            delegate=delegate,
        )
        return True

    if all(map(StakeProgramDeactivateInstruction.is_type_of, instructions)):
        from .layout import confirm_unstake_transaction

        for deactivate in instructions:
            if signer_public_key != deactivate.stake_authority[0]:
                return False

        await confirm_unstake_transaction(
            fee=fee, signer_path=signer_path, blockhash=blockhash
        )
        return True

    if all(map(StakeProgramWithdrawInstruction.is_type_of, instructions)):
        from .layout import confirm_claim_recipient, confirm_claim_transaction

        total_amount = 0
        for withdraw in instructions:
            if signer_public_key != withdraw.withdrawal_authority[0]:
                return False
            if signer_public_key != withdraw.recipient_account[0]:
                await confirm_claim_recipient(withdraw.recipient_account[0])
            total_amount += withdraw.lamports

        await confirm_claim_transaction(
            fee=fee,
            signer_path=signer_path,
            blockhash=blockhash,
            total_amount=total_amount,
        )

        return True

    # not a staking transaction
    return False
