from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.wire import DataError

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID
from .transaction import Transaction
from .types import AdditionalTxInfo

if TYPE_CHECKING:
    from trezor.messages import SolanaSignTx, SolanaTxSignature

    from apps.common.keychain import Keychain as Slip21Keychain


@with_slip44_keychain(
    *PATTERNS, slip44_id=SLIP44_ID, curve=CURVE, slip21_namespaces=[[b"SLIP-0024"]]
)
async def sign_tx(
    msg: SolanaSignTx,
    keychain: Slip21Keychain,
) -> SolanaTxSignature:
    from trezor import TR
    from trezor.crypto.curve import ed25519
    from trezor.enums import ButtonRequestType
    from trezor.messages import SolanaTxSignature
    from trezor.ui.layouts import confirm_metadata, show_continue_in_app, show_warning

    from apps.common import seed

    from .layout import confirm_transaction
    from .predefined_transaction import (
        get_token_transfer_instructions,
        try_confirm_predefined_transaction,
    )

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

    if _has_unsupported_instructions(transaction):
        fee = None
    else:
        fee = transaction.calculate_fee()

    additional_tx_info = AdditionalTxInfo.from_solana_tx_additional_info(
        msg.additional_info
    )

    if msg.payment_req:
        from apps.common.payment_request import PaymentRequestVerifier

        transfer_token_instructions = get_token_transfer_instructions(
            transaction.get_visible_instructions()
        )
        verifier = PaymentRequestVerifier(msg.payment_req, SLIP44_ID, keychain)
        for transfer_token_instruction in transfer_token_instructions:
            verifier.add_output(
                transfer_token_instruction.amount,
                base58.encode(transfer_token_instruction.destination_account[0]),
            )
        verifier.verify()

    if not await try_confirm_predefined_transaction(
        transaction,
        fee,
        address_n,
        signer_public_key,
        transaction.blockhash,
        additional_tx_info,
        msg.payment_req,
    ):
        await confirm_instructions(
            address_n, signer_public_key, transaction, additional_tx_info
        )
        await confirm_transaction(transaction.blockhash, fee)

    signature = ed25519.sign(node.private_key(), serialized_tx)
    show_continue_in_app(TR.send__transaction_signed)
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
    additional_info: AdditionalTxInfo,
) -> None:
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
                additional_info.definitions,
            )
