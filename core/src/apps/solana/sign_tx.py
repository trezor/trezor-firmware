from typing import TYPE_CHECKING

from trezor.wire import DataError

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID
from .definitions import Definitions
from .transaction import Transaction
from .types import AdditionalTxInfo

if TYPE_CHECKING:
    from trezor.messages import SolanaSignTx, SolanaTxSignature

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(
    msg: SolanaSignTx,
    keychain: Keychain,
) -> SolanaTxSignature:
    from trezor import TR
    from trezor.crypto.curve import ed25519
    from trezor.enums import ButtonRequestType
    from trezor.messages import SolanaTxSignature
    from trezor.ui.layouts import confirm_metadata, show_warning

    from apps.common import seed

    from .layout import confirm_transaction
    from .predefined_transaction import try_confirm_predefined_transaction

    address_n = msg.address_n  # local_cache_attribute
    serialized_tx = msg.serialized_tx  # local_cache_attribute

    node = keychain.derive(address_n)
    signer_public_key = seed.remove_ed25519_prefix(node.public_key())

    try:
        transaction: Transaction = Transaction(serialized_tx)
    except Exception:
        raise DataError("Invalid transaction")

    if transaction.blind_signing:
        await show_warning(
            "warning_blind_signing",
            TR.solana__transaction_contains_unknown_instructions,
        )

    if transaction.required_signers_count > 1:
        await confirm_metadata(
            "multiple_signers",
            TR.solana__multiple_signers,
            TR.solana__transaction_requires_x_signers_template.format(
                transaction.required_signers_count
            ),
            br_code=ButtonRequestType.Other,
        )

    fee = calculate_fee(transaction)

    additional_tx_info = AdditionalTxInfo.from_solana_tx_additional_info(
        msg.additional_info
    )

    if not await try_confirm_predefined_transaction(
        transaction, fee, address_n, transaction.blockhash, additional_tx_info
    ):
        await confirm_instructions(
            address_n, signer_public_key, transaction, additional_tx_info
        )
        await confirm_transaction(
            address_n,
            transaction.blockhash,
            calculate_fee(transaction),
        )

    signature = ed25519.sign(node.private_key(), serialized_tx)

    return SolanaTxSignature(signature=signature)


async def confirm_instructions(
    signer_path: list[int],
    signer_public_key: bytes,
    transaction: Transaction,
    additional_info: AdditionalTxInfo | None,
) -> None:
    definitions: Definitions | None = (
        additional_info.definitions if additional_info else None
    )

    visible_instructions = transaction.get_visible_instructions()
    instructions_count = len(visible_instructions)
    for instruction_index, instruction in enumerate(visible_instructions, 1):
        if not instruction.is_program_supported:
            from .layout import confirm_unsupported_program_confirm

            await confirm_unsupported_program_confirm(
                instruction,
                instructions_count,
                instruction_index,
                signer_path,
                signer_public_key,
            )
        elif not instruction.is_instruction_supported:
            from .layout import confirm_unsupported_instruction_confirm

            await confirm_unsupported_instruction_confirm(
                instruction,
                instructions_count,
                instruction_index,
                signer_path,
                signer_public_key,
            )
        else:
            from .layout import confirm_instruction

            await confirm_instruction(
                instruction,
                instructions_count,
                instruction_index,
                signer_path,
                signer_public_key,
                definitions,
            )


def calculate_fee(transaction: Transaction) -> int:
    import math

    from .constants import SOLANA_BASE_FEE_LAMPORTS, SOLANA_COMPUTE_UNIT_LIMIT
    from .transaction.instructions import (
        COMPUTE_BUDGET_PROGRAM_ID,
        COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT,
        COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE,
    )
    from .types import AddressType

    number_of_signers = 0
    for address in transaction.addresses:
        if address[1] == AddressType.AddressSig:
            number_of_signers += 1

    base_fee = SOLANA_BASE_FEE_LAMPORTS * number_of_signers

    unit_price = 0
    is_unit_price_set = False
    unit_limit = SOLANA_COMPUTE_UNIT_LIMIT
    is_unit_limit_set = False

    for instruction in transaction.instructions:
        if instruction.program_id == COMPUTE_BUDGET_PROGRAM_ID:
            if (
                instruction.instruction_id
                == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_LIMIT
                and not is_unit_limit_set
            ):
                unit_limit = instruction.units
                is_unit_limit_set = True
            elif (
                instruction.instruction_id
                == COMPUTE_BUDGET_PROGRAM_ID_INS_SET_COMPUTE_UNIT_PRICE
                and not is_unit_price_set
            ):
                unit_price = instruction.lamports
                is_unit_price_set = True

    return int(base_fee + math.ceil(unit_price * unit_limit / 1000000))
