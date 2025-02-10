from typing import TYPE_CHECKING

from trezor.crypto import base58
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

    base_fee, priority_fee = calculate_fee(transaction)
    rent = calculate_rent(transaction)

    additional_tx_info = AdditionalTxInfo.from_solana_tx_additional_info(
        msg.additional_info
    )

    if not await try_confirm_predefined_transaction(
        transaction,
        base_fee,
        priority_fee,
        rent,
        address_n,
        transaction.blockhash,
        additional_tx_info,
    ):
        await confirm_instructions(
            address_n, signer_public_key, transaction, additional_tx_info
        )
        await confirm_transaction(
            address_n,
            transaction.blockhash,
            base_fee,
            priority_fee,
            rent,
            _has_unsupported_instructions(transaction),
        )

    signature = ed25519.sign(node.private_key(), serialized_tx)

    return SolanaTxSignature(signature=signature)


def _has_unsupported_instructions(transaction: Transaction) -> bool:
    visible_instructions = transaction.get_visible_instructions()
    for instruction in visible_instructions:
        if not (
            instruction.is_program_supported and instruction.is_instruction_supported
        ):
            return True
    return False


async def confirm_instructions(
    signer_path: list[int],
    signer_public_key: bytes,
    transaction: Transaction,
    additional_info: AdditionalTxInfo | None,
):
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


def calculate_fee(transaction: Transaction) -> tuple[int, int]:
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

    priority_fee = math.ceil(unit_price * unit_limit / 1000000)
    return base_fee, priority_fee


def calculate_rent(transaction: Transaction) -> int:
    """
    Returns max rent exemption in lamports.

    To estimate rent exemption from a transaction we need to go over the instructions.
    When new accounts are created, space must be allocated for them, rent exemption value depends on that space.

    There are a handful of instruction that allocate space:
    - System program create account instruction (the space data parameter)
    - System program create account with seed instruction (the space data parameter)
    - System program allocate instruction (the space data parameter)
    - System program allocate with seed instruction (the space data parameter)
    - Associated token account program create instruction (165 bytes for Token, ??? for Token22)
    - Associated token account program create idempotent instruction (165 bytes for Token, ??? for Token22, might not allocate)
    """
    from .constants import (
        SOLANA_ACCOUNT_METADATA_SIZE,
        SOLANA_ASSOCIATED_TOKEN_ACCOUNT_SIZE,
        SOLANA_RENT_EXEMPTION_MULTIPLIER,
        SOLANA_RENT_PER_BYTE_EPOCH,
    )
    from .transaction.instructions import (
        _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
        _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE,
        _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT,
        _SYSTEM_PROGRAM_ID,
        _SYSTEM_PROGRAM_ID_INS_ALLOCATE,
        _SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED,
        _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT,
        _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED,
        _TOKEN_PROGRAM_ID,
    )

    allocation_estimate = 0
    for instruction in transaction.instructions:
        if instruction.program_id == _SYSTEM_PROGRAM_ID and (
            instruction.instruction_id == _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT
            or instruction.instruction_id
            == _SYSTEM_PROGRAM_ID_INS_CREATE_ACCOUNT_WITH_SEED
            or instruction.instruction_id == _SYSTEM_PROGRAM_ID_INS_ALLOCATE
            or instruction.instruction_id == _SYSTEM_PROGRAM_ID_INS_ALLOCATE_WITH_SEED
        ):
            allocation_estimate += (
                instruction.parsed_data["space"] + SOLANA_ACCOUNT_METADATA_SIZE
            )
        elif instruction.program_id == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID and (
            instruction.instruction_id
            == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE
            or instruction.instruction_id
            == _ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID_INS_CREATE_IDEMPOTENT
        ):
            # REVIEW: What do I do with AddressReferences here?
            spl_token_account = instruction.parsed_accounts["spl_token"]
            if len(spl_token_account) == 2 and spl_token_account[0] == base58.decode(
                _TOKEN_PROGRAM_ID
            ):
                allocation_estimate += (
                    SOLANA_ASSOCIATED_TOKEN_ACCOUNT_SIZE + SOLANA_ACCOUNT_METADATA_SIZE
                )
            else:
                # TODO: come up with a max space for Token22
                ...

    rent_exemption_estimate = (
        allocation_estimate
        * SOLANA_RENT_PER_BYTE_EPOCH
        * SOLANA_RENT_EXEMPTION_MULTIPLIER
    )
    return rent_exemption_estimate
