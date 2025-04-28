from typing import TYPE_CHECKING

from trezor import TR
from trezor.crypto import base58
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_address,
    confirm_metadata,
    confirm_properties,
    confirm_solana_recipient,
    confirm_solana_tx,
    confirm_value,
    show_danger,
    show_warning,
)

from apps.common.paths import address_n_to_str

from .types import AddressType

if TYPE_CHECKING:
    from typing import Sequence

    from trezor.messages import SolanaTokenInfo

    from .definitions import Definitions
    from .transaction import Fee
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


def _get_address_reference_props(
    address: AddressReference, display_name: str
) -> Sequence[tuple[str, str]]:
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
    definitions: Definitions,
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

            if property_template.optional and value is None:
                continue

            if ui_property.default_value_to_hide == value:
                continue

            if (
                property_template.is_pubkey()
                and ui_property.default_value_to_hide == "signer"
                and signer_public_key == value
            ):
                continue

            args = []
            for arg in property_template.args:
                if arg == "#definitions":
                    args.append(definitions)
                elif arg in instruction.parsed_data:
                    args.append(instruction.parsed_data[arg])
                elif arg in instruction.parsed_accounts:
                    args.append(instruction.parsed_accounts[arg][0])
                else:
                    raise ValueError  # Invalid property template

            await confirm_properties(
                "confirm_instruction",
                f"{instruction_index}/{instructions_count}: {instruction.ui_name}",
                (
                    (
                        ui_property.display_name,
                        property_template.format(value, *args),
                    ),
                ),
            )
        elif ui_property.account is not None:
            # optional account, skip if not present
            if ui_property.account not in instruction.parsed_accounts:
                continue

            account_value = instruction.parsed_accounts[ui_property.account]

            if (
                ui_property.default_value_to_hide == "signer"
                and signer_public_key == account_value[0]
            ):
                continue

            account_data: list[tuple[str, str]] = []
            # account included in the transaction directly
            if len(account_value) == 2:
                account_description = f"{base58.encode(account_value[0])}"
                if definitions.has_token(account_value[0]):
                    token = definitions.get_token(account_value[0])
                    account_description = f"{token.name}\n{account_description}"
                elif account_value[0] == signer_public_key:
                    account_description = f"{account_description} ({TR.words__signer})"

                account_data.append((ui_property.display_name, account_description))
            # lookup table address reference
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
    from trezor.ui.layouts import confirm_properties, should_show_more

    should_show_instruction_details = await should_show_more(
        title,
        (
            (
                TR.solana__instruction_accounts_template.format(
                    len(instruction.accounts), len(instruction.instruction_data)
                ),
                False,
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
    fee: Fee,
    blockhash: bytes,
) -> None:
    await confirm_solana_recipient(
        recipient=base58.encode(transfer_instruction.recipient_account[0]),
        title=TR.words__recipient,
    )

    await confirm_custom_transaction(
        transfer_instruction.lamports, 9, "SOL", fee, blockhash
    )


async def confirm_token_transfer(
    destination_account: bytes,
    token_account: bytes,
    token: SolanaTokenInfo,
    amount: int,
    decimals: int,
    fee: Fee,
    blockhash: bytes,
) -> None:
    items = []
    if token_account != destination_account:
        items.append(
            (f"{TR.solana__associated_token_account}:", base58.encode(token_account))
        )

    await confirm_solana_recipient(
        recipient=base58.encode(destination_account),
        title=TR.words__recipient,
        items=items,
    )

    value = token.name + "\n" + base58.encode(token.mint)

    await confirm_value(
        title=TR.solana__title_token,
        value=value,
        description="",
        br_name="confirm_token_address",
        br_code=ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__continue,
    )

    await confirm_custom_transaction(amount, decimals, token.symbol, fee, blockhash)


def _fee_ui_info(
    has_unsupported_instructions: bool, fee: Fee
) -> tuple[str, str, list[tuple[str, str]]]:
    fee_items: list[tuple[str, str]] = []
    if has_unsupported_instructions:
        fee_title = f"{TR.solana__max_fees_rent}:"
        fee_str = TR.words__unknown
    else:
        fee_str = f"{format_amount(fee.total, 9)} SOL"
        base_fee_str = f"{format_amount(fee.base, 9)} SOL"
        fee_items.append((TR.solana__base_fee, base_fee_str))
        if fee.priority:
            priority_fee_str = f"{format_amount(fee.priority, 9)} SOL"
            fee_items.append((TR.solana__priority_fee, priority_fee_str))
        if fee.rent:
            fee_title = f"{TR.solana__max_fees_rent}:"
            rent_str = f"{format_amount(fee.rent, 9)} SOL"
            fee_items.append((TR.solana__max_rent_fee, rent_str))
        else:
            fee_title = f"{TR.solana__transaction_fee}:"
    return fee_title, fee_str, fee_items


async def confirm_custom_transaction(
    amount: int,
    decimals: int,
    unit: str,
    fee: Fee,
    blockhash: bytes,
) -> None:
    fee_title, fee_str, fee_items = _fee_ui_info(False, fee)
    fee_items.append((TR.words__blockhash, base58.encode(blockhash)))
    await confirm_solana_tx(
        amount=f"{format_amount(amount, decimals)} {unit}",
        fee=fee_str,
        fee_title=fee_title,
        items=fee_items,
    )


async def confirm_stake_withdrawer(withdrawer_account: bytes) -> None:
    await show_danger(
        title=TR.words__important,
        content=TR.solana__stake_withdrawal_warning,
        verb_cancel=TR.words__cancel_and_exit,
        br_name="confirm_stake_warning",
    )
    await confirm_address(
        title=TR.solana__stake_withdrawal_warning_title,
        address=base58.encode(withdrawer_account),
        br_name="confirm_stake_warning_address",
    )


async def confirm_claim_recipient(recipient_account: bytes) -> None:
    await show_warning(
        content=TR.solana__claim_recipient_warning,
        br_name="confirm_claim_warning",
    )
    await confirm_address(
        title=TR.address_details__title_receive_address,
        address=base58.encode(recipient_account),
        br_name="confirm_claim_warning_address",
    )


async def confirm_stake_transaction(
    fee: Fee,
    signer_path: list[int],
    blockhash: bytes,
    create: Instruction,
    delegate: Instruction,
) -> None:
    from trezor.ui.layouts import confirm_solana_staking_tx

    vote_account = base58.encode(delegate.vote_account[0])
    KNOWN_ACCOUNTS = {
        "9QU2QSxhb24FUX3Tu2FpczXjpK3VYrvRudywSZaM29mF": "Everstake",
    }
    vote_account_label = KNOWN_ACCOUNTS.get(vote_account)
    if vote_account_label is None:
        description = TR.solana__stake_question
        vote_account_label = vote_account
    else:
        description = TR.solana__stake_on_question.format(vote_account_label)
        vote_account_label = ""

    fee_title, fee_str, fee_items = _fee_ui_info(False, fee)

    await confirm_solana_staking_tx(
        title=TR.solana__stake,
        description=description,
        account=_format_path(signer_path),
        account_path=address_n_to_str(signer_path),
        vote_account=vote_account_label,
        stake_item=(
            TR.solana__stake_account,
            base58.encode(delegate.initialized_stake_account[0]),
        ),
        amount_item=(
            f"{TR.words__amount}:",
            f"{format_amount(create.lamports, 9)} SOL",
        ),
        fee_item=(fee_title, fee_str),
        fee_details=fee_items,
        blockhash_item=(TR.words__blockhash, base58.encode(blockhash)),
    )


async def confirm_unstake_transaction(
    fee: Fee,
    signer_path: list[int],
    blockhash: bytes,
) -> None:
    from trezor.ui.layouts import confirm_solana_staking_tx

    fee_title, fee_str, fee_items = _fee_ui_info(False, fee)

    await confirm_solana_staking_tx(
        title=TR.solana__unstake,
        description=TR.solana__unstake_question,
        account=_format_path(signer_path),
        account_path=address_n_to_str(signer_path),
        vote_account="",
        stake_item=None,
        amount_item=None,
        fee_item=(fee_title, fee_str),
        fee_details=fee_items,
        blockhash_item=(TR.words__blockhash, base58.encode(blockhash)),
    )


async def confirm_claim_transaction(
    fee: Fee,
    signer_path: list[int],
    blockhash: bytes,
    total_amount: int,
) -> None:
    from trezor.ui.layouts import confirm_solana_staking_tx

    fee_title, fee_str, fee_items = _fee_ui_info(False, fee)
    await confirm_solana_staking_tx(
        title=TR.solana__claim,
        description=TR.solana__claim_question,
        account=_format_path(signer_path),
        account_path=address_n_to_str(signer_path),
        vote_account="",
        stake_item=None,
        amount_item=(
            f"{TR.words__amount}:",
            f"{format_amount(total_amount, 9)} SOL",
        ),
        fee_item=(fee_title, fee_str),
        fee_details=fee_items,
        blockhash_item=(TR.words__blockhash, base58.encode(blockhash)),
    )


async def confirm_transaction(
    blockhash: bytes,
    fee: Fee,
    has_unsupported_instructions: bool,
) -> None:
    fee_title, fee_str, fee_items = _fee_ui_info(has_unsupported_instructions, fee)
    fee_items.append((TR.words__blockhash, base58.encode(blockhash)))
    await confirm_solana_tx(
        amount="",
        amount_title="",
        fee=fee_str,
        fee_title=fee_title,
        items=fee_items,
    )
