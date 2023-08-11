from typing import TYPE_CHECKING

from trezor import TR
from trezor.crypto import base58
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_metadata,
    confirm_properties,
    confirm_solana_tx,
    confirm_value,
)

from apps.common.paths import address_n_to_str

from .types import AddressType

if TYPE_CHECKING:
    from .transaction.instructions import Instruction, SystemProgramTransferInstruction
    from .types import AddressReference


def _format_path(path: list[int]) -> str:
    from micropython import const

    from apps.common.paths import unharden

    if len(path) < 4:
        return address_n_to_str(path)

    ACCOUNT_PATH_INDEX = const(3)
    account_index = path[ACCOUNT_PATH_INDEX]
    return f"Solana #{unharden(account_index) + 1}"


def _get_address_reference_props(address: AddressReference, display_name: str):
    return (
        (TR.solana__is_provided_via_lookup_table_template.format(display_name), ""),
        (f"{TR.solana__lookup_table_address}:", base58.encode(address[0])),
        (f"{TR.solana__account_index}:", f"{address[1]}"),
    )


async def confirm_instruction(
    instruction: Instruction,
    instructions_count: int,
    instruction_index: int,
    signer_path: list[int],
    signer_public_key: bytes,
) -> None:
    instruction_title = (
        f"{instruction_index}/{instructions_count}: {instruction.ui_name}"
    )

    if instruction.is_deprecated_warning is not None:
        await confirm_metadata(
            "confirm_deprecated_warning",
            instruction_title,
            instruction.is_deprecated_warning,
            br_code=ButtonRequestType.Other,
        )

    if instruction.multisig_signers:
        await confirm_metadata(
            "confirm_multisig",
            TR.solana__confirm_multisig,
            TR.solana__instruction_is_multisig,
            br_code=ButtonRequestType.Other,
        )

    for ui_property in instruction.ui_properties:
        if ui_property.parameter is not None:
            property_template = instruction.get_property_template(ui_property.parameter)
            value = instruction.parsed_data[ui_property.parameter]

            if property_template.is_authority and signer_public_key == value:
                continue

            if property_template.is_optional and value is None:
                continue

            if ui_property.default_value_to_hide == value:
                continue

            await confirm_properties(
                "confirm_instruction",
                f"{instruction_index}/{instructions_count}: {instruction.ui_name}",
                (
                    (
                        ui_property.display_name,
                        property_template.format(instruction, value),
                    ),
                ),
            )
        elif ui_property.account is not None:
            account_template = instruction.get_account_template(ui_property.account)

            # optional account, skip if not present
            if ui_property.account not in instruction.parsed_accounts:
                continue

            account_value = instruction.parsed_accounts[ui_property.account]

            if account_template.is_authority:
                if signer_public_key == account_value[0]:
                    continue

            account_data: list[tuple[str, str]] = []
            if len(account_value) == 2:
                signer_suffix = ""
                if account_value[0] == signer_public_key:
                    signer_suffix = f" ({TR.words__signer})"

                account_data.append(
                    (
                        ui_property.display_name,
                        f"{base58.encode(account_value[0])}{signer_suffix}",
                    )
                )
            elif len(account_value) == 3:
                account_data += _get_address_reference_props(
                    account_value, ui_property.display_name
                )
            else:
                raise ValueError  # Invalid account value

            await confirm_properties(
                "confirm_instruction",
                f"{instruction_index}/{instructions_count}: {instruction.ui_name}",
                account_data,
            )
        else:
            raise ValueError  # Invalid ui property

    if instruction.multisig_signers:
        signers: list[tuple[str, str]] = []
        for i, multisig_signer in enumerate(instruction.multisig_signers, 1):
            multisig_signer_public_key = multisig_signer[0]

            path_str = ""
            if multisig_signer_public_key == signer_public_key:
                path_str = f" ({address_n_to_str(signer_path)})"

            signers.append(
                (
                    f"{TR.words__signer} {i}{path_str}:",
                    base58.encode(multisig_signer[0]),
                )
            )

        await confirm_properties(
            "confirm_instruction",
            f"{instruction_index}/{instructions_count}: {instruction.ui_name}",
            signers,
        )


def get_address_type(address_type: AddressType) -> str:
    if address_type == AddressType.AddressSig:
        return f"({TR.words__writable}, {TR.words__signer})"
    if address_type == AddressType.AddressSigReadOnly:
        return f"({TR.words__signer})"
    if address_type == AddressType.AddressReadOnly:
        return ""
    if address_type == AddressType.AddressRw:
        return f"({TR.words__writable})"
    raise ValueError  # Invalid address type


async def confirm_unsupported_instruction_details(
    instruction: Instruction,
    title: str,
    signer_path: list[int],
    signer_public_key: bytes,
) -> None:
    from trezor.ui import NORMAL
    from trezor.ui.layouts import confirm_properties, should_show_more

    should_show_instruction_details = await should_show_more(
        title,
        (
            (
                NORMAL,
                TR.solana__instruction_accounts_template.format(
                    len(instruction.accounts), len(instruction.instruction_data)
                ),
            ),
        ),
        TR.buttons__show_details,
        confirm=TR.buttons__continue,
    )

    if should_show_instruction_details:
        await confirm_properties(
            "instruction_data",
            title,
            ((f"{TR.solana__instruction_data}:", bytes(instruction.instruction_data)),),
        )

        accounts = []
        for i, account in enumerate(instruction.accounts, 1):
            if len(account) == 2:
                account_public_key = account[0]
                address_type = get_address_type(account[1])

                path_str = ""
                if account_public_key == signer_public_key:
                    path_str = f" ({address_n_to_str(signer_path)})"

                accounts.append(
                    (
                        f"{TR.words__account} {i}{path_str} {address_type}:",
                        base58.encode(account_public_key),
                    )
                )
            elif len(account) == 3:
                address_type = get_address_type(account[2])
                accounts += _get_address_reference_props(
                    account, f"{TR.words__account} {i} {address_type}"
                )
            else:
                raise ValueError  # Invalid account value

        await confirm_properties(
            "accounts",
            title,
            accounts,
        )


async def confirm_unsupported_instruction_confirm(
    instruction: Instruction,
    instructions_count: int,
    instruction_index: int,
    signer_path: list[int],
    signer_public_key: bytes,
) -> None:
    formatted_instruction_id = (
        instruction.instruction_id if instruction.instruction_id is not None else "N/A"
    )
    title = f"{instruction_index}/{instructions_count}: {instruction.ui_name}: instruction id ({formatted_instruction_id})"

    return await confirm_unsupported_instruction_details(
        instruction, title, signer_path, signer_public_key
    )


async def confirm_unsupported_program_confirm(
    instruction: Instruction,
    instructions_count: int,
    instruction_index: int,
    signer_path: list[int],
    signer_public_key: bytes,
) -> None:
    title = f"{instruction_index}/{instructions_count}: {instruction.ui_name}"

    return await confirm_unsupported_instruction_details(
        instruction, title, signer_path, signer_public_key
    )


async def confirm_system_transfer(
    transfer_instruction: SystemProgramTransferInstruction,
    fee: int,
    signer_path: list[int],
    blockhash: bytes,
) -> None:
    await confirm_value(
        title=TR.words__recipient,
        value=base58.encode(transfer_instruction.recipient_account[0]),
        description="",
        br_type="confirm_recipient",
        br_code=ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__continue,
    )

    await confirm_custom_transaction(
        transfer_instruction.lamports,
        9,
        "SOL",
        fee,
        signer_path,
        blockhash,
    )


async def confirm_token_transfer(
    destination_account: bytes,
    token_account: bytes,
    token_mint: bytes,
    amount: int,
    decimals: int,
    fee: int,
    signer_path: list[int],
    blockhash: bytes,
):
    await confirm_value(
        title=TR.words__recipient,
        value=base58.encode(destination_account),
        description="",
        br_type="confirm_recipient",
        br_code=ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__continue,
        info_items=(
            (f"{TR.solana__associated_token_account}:", base58.encode(token_account)),
        )
        if token_account != destination_account
        else None,
    )

    await confirm_value(
        title=TR.solana__token_address,
        value=base58.encode(token_mint),
        description="",
        br_type="confirm_token_address",
        br_code=ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__continue,
    )

    await confirm_custom_transaction(
        amount,
        decimals,
        "[TOKEN]",
        fee,
        signer_path,
        blockhash,
    )


async def confirm_custom_transaction(
    amount: int,
    decimals: int,
    unit: str,
    fee: int,
    signer_path: list[int],
    blockhash: bytes,
) -> None:
    await confirm_solana_tx(
        amount=f"{format_amount(amount, decimals)} {unit}",
        fee=f"{format_amount(fee, 9)} SOL",
        fee_title=f"{TR.solana__expected_fee}:",
        items=(
            (f"{TR.words__account}:", _format_path(signer_path)),
            (f"{TR.words__blockhash}:", base58.encode(blockhash)),
        ),
    )


async def confirm_transaction(
    signer_path: list[int], blockhash: bytes, fee: int
) -> None:
    await confirm_solana_tx(
        amount="",
        amount_title="",
        fee=f"{format_amount(fee, 9)} SOL",
        fee_title=f"{TR.solana__expected_fee}:",
        items=(
            (f"{TR.words__account}:", _format_path(signer_path)),
            (f"{TR.words__blockhash}:", base58.encode(blockhash)),
        ),
    )
