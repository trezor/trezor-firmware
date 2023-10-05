from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID
from .transaction import Transaction

if TYPE_CHECKING:
    from trezor.messages import SolanaSignTx, SolanaTxSignature

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(
    msg: SolanaSignTx,
    keychain: Keychain,
) -> SolanaTxSignature:
    from trezor.crypto.curve import ed25519
    from trezor.messages import SolanaTxSignature
    from trezor.utils import BufferReader
    from trezor.ui.layouts import show_warning
    from trezor.ui.layouts import confirm_signverify
    from .ui import show_final_confirmation

    address_n = msg.address_n
    serialized_tx = msg.serialized_tx

    node = keychain.derive(address_n)

    transaction: Transaction = Transaction(BufferReader(serialized_tx))

    if transaction.blind_signing:
        await show_warning(
            "warning_blind_signing",
            "Unsupported instructions.",
            "Do you want to blindly sing the message?"
        )

    await show_instructions(node.public_key(), transaction)

    await show_final_confirmation(transaction.blockhash, calculate_fee(transaction))

    signature = ed25519.sign(node.private_key(), serialized_tx)

    return SolanaTxSignature(signature=signature)


async def show_instructions(public_key: bytes, transaction: Transaction) -> None:
    from apps.common import seed

    num_instructions = len(transaction.instructions)
    for i, instruction in enumerate(transaction.instructions):
        # Check template id. Template id is derived from program.json
        if instruction.ui_identifier == "ui_confirm":
            from .ui import show_confirm

            await show_confirm(
                (num_instructions, i + 1),
                instruction,
                seed.remove_ed25519_prefix(public_key),
            )
        elif instruction.ui_identifier == "ui_unsupported_instruction":
            from .ui import show_unsupported_instruction_confirm

            await show_unsupported_instruction_confirm(
                (num_instructions, i + 1),
                instruction,
                seed.remove_ed25519_prefix(public_key),
            )
        elif instruction.ui_identifier == "ui_unsupported_program":
            from .ui import show_unsupported_program_confirm

            await show_unsupported_program_confirm(
                (num_instructions, i + 1),
                instruction,
                seed.remove_ed25519_prefix(public_key),
            )
        else:
            # TODO SOL: handle other UI templates
            pass

def calculate_fee(transaction: Transaction) -> int:
    from .constants import SOLANA_BASE_FEE_LAMPORTS, SOLANA_CU_LIMIT, ADDRESS_READ_ONLY
    from .transaction.instructions import (
        COMPUTE_BUDGET_PROGRAM_ID, 
        COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT, 
        COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE
    )

    number_of_signers = 0
    for address in transaction.addresses:
        if address[1] < ADDRESS_READ_ONLY:
            number_of_signers += 1
    
    base_fee = SOLANA_BASE_FEE_LAMPORTS * number_of_signers

    unit_price: int | None = None
    unit_limit: int = SOLANA_CU_LIMIT

    for instruction in transaction.instructions:
        if instruction.program_id == COMPUTE_BUDGET_PROGRAM_ID:
            if instruction.instruction_id == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT:
                unit_limit = instruction.units
            elif instruction.instruction_id == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE:
                unit_price = instruction.lamports

    if unit_price is None:
        return base_fee
    
    return int(base_fee + unit_price * unit_limit / 1000000)