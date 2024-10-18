from typing import TYPE_CHECKING

from trezor import TR, ui
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_blob,
    confirm_blob_with_optional_pagination,
    confirm_ethereum_staking_tx,
    confirm_text,
    should_show_more,
)

from .helpers import (
    address_from_bytes,
    decode_typed_data,
    format_ethereum_amount,
    get_account_and_path,
)

if TYPE_CHECKING:
    from typing import Awaitable, Iterable

    from trezor.messages import (
        EthereumFieldType,
        EthereumNetworkInfo,
        EthereumStructMember,
        EthereumTokenInfo,
    )


async def require_confirm_tx(
    to_bytes: bytes,
    value: int,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[tuple[str, str]],
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo | None,
    is_contract_interaction: bool,
    chunkify: bool,
) -> None:
    from trezor.ui.layouts import confirm_ethereum_tx

    to_str = address_from_bytes(to_bytes, network) if to_bytes else None
    total_amount = format_ethereum_amount(value, token, network)
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_tx(
        to_str,
        total_amount,
        account,
        account_path,
        maximum_fee,
        fee_info_items,
        is_contract_interaction,
        chunkify=chunkify,
    )


async def require_confirm_stake(
    addr_bytes: bytes,
    value: int,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[tuple[str, str]],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:

    addr_str = address_from_bytes(addr_bytes, network)
    total_amount = format_ethereum_amount(value, None, network)
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_staking_tx(
        TR.ethereum__staking_stake,  # title
        TR.ethereum__staking_stake_intro,  # intro_question
        TR.ethereum__staking_stake,  # verb
        total_amount,
        account,
        account_path,
        maximum_fee,
        addr_str,  # address
        TR.ethereum__staking_stake_address,  # address_title
        fee_info_items,  # info_items
        chunkify=chunkify,
    )


async def require_confirm_unstake(
    addr_bytes: bytes,
    value: int,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[tuple[str, str]],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:

    addr_str = address_from_bytes(addr_bytes, network)
    total_amount = format_ethereum_amount(value, None, network)
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_staking_tx(
        TR.ethereum__staking_unstake,  # title
        TR.ethereum__staking_unstake_intro,  # intro_question
        TR.ethereum__staking_unstake,  # verb
        total_amount,
        account,
        account_path,
        maximum_fee,
        addr_str,  # address
        TR.ethereum__staking_stake_address,  # address_title
        fee_info_items,  # info_items
        chunkify=chunkify,
    )


async def require_confirm_claim(
    addr_bytes: bytes,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[tuple[str, str]],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:

    addr_str = address_from_bytes(addr_bytes, network)
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_staking_tx(
        TR.ethereum__staking_claim,  # title
        TR.ethereum__staking_claim_intro,  # intro_question
        TR.ethereum__staking_claim,  # verb
        "",  # total_amount
        account,
        account_path,
        maximum_fee,
        addr_str,  # address
        TR.ethereum__staking_claim_address,  # address_title
        fee_info_items,  # info_items
        chunkify=chunkify,
    )


async def require_confirm_unknown_token(address_bytes: bytes):
    from ubinascii import hexlify

    from trezor.ui.layouts import confirm_address, show_warning

    await show_warning(
        "unknown_contract_warning",
        TR.ethereum__unknown_contract_address,
        default_cancel=True,
        verb_cancel=TR.send__cancel_sign,
        br_code=ButtonRequestType.Other,
    )

    contract_address_hex = "0x" + hexlify(address_bytes).decode()
    await confirm_address(
        TR.words__address,
        contract_address_hex,
        subtitle=TR.ethereum__token_contract,
        verb=TR.buttons__continue,
        br_name="unknown_token",
        br_code=ButtonRequestType.SignTx,
    )


def require_confirm_address(address_bytes: bytes) -> Awaitable[None]:
    from ubinascii import hexlify

    from trezor.ui.layouts import confirm_address

    address_hex = "0x" + hexlify(address_bytes).decode()
    return confirm_address(
        TR.ethereum__title_signing_address,
        address_hex,
        br_code=ButtonRequestType.SignTx,
    )


def require_confirm_other_data(data: bytes, data_total: int) -> Awaitable[None]:
    return confirm_blob_with_optional_pagination(
        "confirm_data",
        TR.ethereum__title_input_data,
        data,
        subtitle=TR.ethereum__data_size_template.format(data_total),
        verb=TR.buttons__confirm,
        verb_cancel=TR.send__cancel_sign,
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_typed_data_final() -> None:
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "confirm_typed_data_final",
        TR.ethereum__title_confirm_typed_data,
        TR.ethereum__sign_eip712,
        verb=TR.buttons__hold_to_confirm,
        hold=True,
    )


def confirm_empty_typed_message() -> Awaitable[None]:
    return confirm_text(
        "confirm_empty_typed_message",
        TR.ethereum__title_confirm_message,
        "",
        TR.ethereum__no_message_field,
    )


async def should_show_domain(name: bytes, version: bytes) -> bool:
    domain_name = decode_typed_data(name, "string")
    domain_version = decode_typed_data(version, "string")

    para = (
        (ui.NORMAL, TR.ethereum__name_and_version),
        (ui.DEMIBOLD, domain_name),
        (ui.DEMIBOLD, domain_version),
    )
    return await should_show_more(
        TR.ethereum__title_confirm_domain,
        para,
        TR.ethereum__show_full_domain,
        "should_show_domain",
    )


async def should_show_struct(
    description: str,
    data_members: list[EthereumStructMember],
    title: str | None = None,
    button_text: str | None = None,
) -> bool:
    from trezor.strings import format_plural

    title = title or TR.ethereum__title_confirm_struct  # def_arg
    button_text = button_text or TR.ethereum__show_full_struct  # def_arg

    plural = format_plural(
        "{count} {plural}", len(data_members), TR.plurals__contains_x_keys
    )
    contains_plural = f"{TR.words__contains} {plural}"

    para = (
        (ui.DEMIBOLD, description),
        (
            ui.NORMAL,
            contains_plural,
        ),
        (ui.NORMAL, ", ".join(field.name for field in data_members)),
    )
    return await should_show_more(
        title,
        para,
        button_text,
        "should_show_struct",
    )


async def should_show_array(
    parent_objects: Iterable[str],
    data_type: str,
    size: int,
) -> bool:
    from trezor.strings import format_plural_english

    # Leaving english plural form because of dynamic noun - data_type
    plural = format_plural_english("{count} {plural}", size, data_type)
    array_of_plural = f"{TR.words__array_of} {plural}"
    para = ((ui.NORMAL, array_of_plural),)
    return await should_show_more(
        limit_str(".".join(parent_objects)),
        para,
        TR.ethereum__show_full_array,
        "should_show_array",
    )


async def confirm_typed_value(
    name: str,
    value: bytes,
    parent_objects: list[str],
    field: EthereumFieldType,
    array_index: int | None = None,
) -> None:
    from trezor.enums import EthereumDataType

    from .helpers import get_type_name

    type_name = get_type_name(field)

    if array_index is not None:
        title = limit_str(".".join(parent_objects + [name]))
        description = f"[{array_index}] ({type_name})"
    else:
        title = limit_str(".".join(parent_objects))
        description = f"{name} ({type_name})"

    data = decode_typed_data(value, type_name)

    if field.data_type in (EthereumDataType.ADDRESS, EthereumDataType.BYTES):
        await confirm_blob(
            "confirm_typed_value",
            title,
            data,
            description,
        )
    else:
        await confirm_text(
            "confirm_typed_value",
            title,
            data,
            description,
        )


def limit_str(s: str, limit: int = 16) -> str:
    """Shortens string to show the last <limit> characters."""
    if len(s) <= limit + 2:
        return s

    return ".." + s[-limit:]
