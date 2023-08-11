from typing import TYPE_CHECKING

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_blob,
    confirm_ethereum_tx,
    confirm_text,
    should_show_more,
)
from trezortranslate import TR

from .helpers import address_from_bytes, decode_typed_data

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
    gas_price: int,
    gas_limit: int,
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo | None,
    chunkify: bool,
) -> None:
    if to_bytes:
        to_str = address_from_bytes(to_bytes, network)
    else:
        to_str = TR.ethereum__new_contract
        chunkify = False

    total_amount = format_ethereum_amount(value, token, network)
    maximum_fee = format_ethereum_amount(gas_price * gas_limit, None, network)
    gas_limit_str = TR.ethereum__units_template.format(gas_limit)
    gas_price_str = format_ethereum_amount(
        gas_price, None, network, force_unit_gwei=True
    )

    items = (
        (TR.ethereum__gas_limit, gas_limit_str),
        (TR.ethereum__gas_price, gas_price_str),
    )

    await confirm_ethereum_tx(
        to_str, total_amount, maximum_fee, items, chunkify=chunkify
    )


async def require_confirm_tx_eip1559(
    to_bytes: bytes,
    value: int,
    max_gas_fee: int,
    max_priority_fee: int,
    gas_limit: int,
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo | None,
    chunkify: bool,
) -> None:
    if to_bytes:
        to_str = address_from_bytes(to_bytes, network)
    else:
        to_str = TR.ethereum__new_contract
        chunkify = False

    total_amount = format_ethereum_amount(value, token, network)
    maximum_fee = format_ethereum_amount(max_gas_fee * gas_limit, None, network)
    gas_limit_str = TR.ethereum__units_template.format(gas_limit)
    max_gas_fee_str = format_ethereum_amount(
        max_gas_fee, None, network, force_unit_gwei=True
    )
    max_priority_fee_str = format_ethereum_amount(
        max_priority_fee, None, network, force_unit_gwei=True
    )

    items: tuple[tuple[str, str], ...] = (
        (TR.ethereum__gas_limit, gas_limit_str),
        (TR.ethereum__max_gas_price, max_gas_fee_str),
        (TR.ethereum__priority_fee, max_priority_fee_str),
    )

    await confirm_ethereum_tx(
        to_str, total_amount, maximum_fee, items, chunkify=chunkify
    )


def require_confirm_unknown_token(address_bytes: bytes) -> Awaitable[None]:
    from ubinascii import hexlify

    from trezor.ui.layouts import confirm_address

    contract_address_hex = "0x" + hexlify(address_bytes).decode()
    return confirm_address(
        TR.ethereum__unknown_token,
        contract_address_hex,
        TR.ethereum__contract,
        "unknown_token",
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


def require_confirm_data(data: bytes, data_total: int) -> Awaitable[None]:
    return confirm_blob(
        "confirm_data",
        TR.ethereum__title_confirm_data,
        data,
        TR.ethereum__data_size_template.format(data_total),
        br_code=ButtonRequestType.SignTx,
        ask_pagination=True,
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
            ask_pagination=True,
        )
    else:
        await confirm_text(
            "confirm_typed_value",
            title,
            data,
            description,
        )


def format_ethereum_amount(
    value: int,
    token: EthereumTokenInfo | None,
    network: EthereumNetworkInfo,
    force_unit_gwei: bool = False,
) -> str:
    from trezor.strings import format_amount

    if token:
        suffix = token.symbol
        decimals = token.decimals
    else:
        suffix = network.symbol
        decimals = 18

    if force_unit_gwei:
        assert token is None
        assert decimals >= 9
        decimals = decimals - 9
        suffix = "Gwei"
    elif decimals > 9 and value < 10 ** (decimals - 9):
        # Don't want to display wei values for tokens with small decimal numbers
        suffix = "Wei " + suffix
        decimals = 0

    amount = format_amount(value, decimals)
    return f"{amount} {suffix}"


def limit_str(s: str, limit: int = 16) -> str:
    """Shortens string to show the last <limit> characters."""
    if len(s) <= limit + 2:
        return s

    return ".." + s[-limit:]
