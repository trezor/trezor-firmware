from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import SolanaSignTx, SolanaTxSignature
    from apps.common.keychain import Keychain
    from .instructions import Instruction
    from .types import RawInstruction


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(
    msg: SolanaSignTx,
    keychain: Keychain,
) -> SolanaTxSignature:
    from trezor.crypto.curve import ed25519
    from trezor.messages import SolanaTxSignature
    from .parsing.parse import parse
    from trezor.utils import BufferReader

    address_n = msg.address_n
    serialized_tx = msg.serialized_tx

    node = keychain.derive(address_n)

    signature = ed25519.sign(node.private_key(), serialized_tx)

    _, _, instructions = parse(BufferReader(serialized_tx))

    # signer_pub_key = seed.remove_ed25519_prefix(node.public_key())
    await _handle_instructions(instructions)

    # TODO SOL: final confirmation screen, include blockhash

    # TODO SOL: only one signature per request?
    return SolanaTxSignature(signature=signature)


async def _handle_instructions(instructions: list[RawInstruction]) -> None:
    from trezor.crypto import base58
    from trezor.ui.layouts import confirm_output
    from trezor.strings import format_amount
    from .instructions.instruction import get_instruction
    from .instructions.parse_template import (
        parse_accounts_template,
        parse_data_template,
    )
    from .instructions.instruction import TransferInstruction

    for raw_instruction in instructions:
        program_id, _, data = raw_instruction

        encoded_program_id = base58.encode(program_id)

        assert data.remaining_count() >= 4
        instruction_id = int.from_bytes(data.read(4), "little")
        data.seek(0)

        instruction = get_instruction(
            encoded_program_id, instruction_id, raw_instruction
        )

        parse_data_template(instruction)
        parse_accounts_template(instruction)

        if TransferInstruction.is_type_of(instruction):
            await confirm_output(
                base58.encode(instruction.recipient_account),
                f"{format_amount(instruction.lamports, 8)} SOL",
            )
        else:
            await _show_instruction(instruction)


async def _show_instruction(instruction: Instruction) -> None:
    from trezor.ui.layouts import confirm_properties

    # assertions for pyright
    assert instruction.parsed_data is not None
    assert instruction.parsed_accounts is not None

    datas = [
        (data[0], instruction.parsed_data[data[0]])
        for data in instruction.data_template
    ]
    accounts = []
    for account in instruction.accounts_template:
        account_value = instruction.parsed_accounts[account[0]]
        if account_value is not None:
            accounts.append((account[1], account_value))

    props = datas + accounts

    return await confirm_properties(
        instruction.ui_identifier, instruction.ui_name, props
    )
