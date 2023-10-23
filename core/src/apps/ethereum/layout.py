from typing import TYPE_CHECKING

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_plural
from trezor.ui.layouts import (
    confirm_blob,
    confirm_ethereum_tx,
    confirm_text,
    should_show_more,
)

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
        to_str = "new contract?"
        chunkify = False

    total_amount = format_ethereum_amount(value, token, network)
    maximum_fee = format_ethereum_amount(gas_price * gas_limit, None, network)
    gas_limit_str = f"{gas_limit} units"
    gas_price_str = format_ethereum_amount(gas_price, None, network)

    items = (
        ("Gas limit:", gas_limit_str),
        ("Gas price:", gas_price_str),
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
        to_str = "new contract?"
        chunkify = False

    total_amount = format_ethereum_amount(value, token, network)
    maximum_fee = format_ethereum_amount(max_gas_fee * gas_limit, None, network)
    gas_limit_str = f"{gas_limit} units"
    max_gas_fee_str = format_ethereum_amount(max_gas_fee, None, network)
    max_priority_fee_str = format_ethereum_amount(max_priority_fee, None, network)

    items = (
        ("Gas limit:", gas_limit_str),
        ("Max gas price:", max_gas_fee_str),
        ("Priority fee:", max_priority_fee_str),
    )

    await confirm_ethereum_tx(
        to_str, total_amount, maximum_fee, items, chunkify=chunkify
    )


def require_confirm_unknown_token(address_bytes: bytes) -> Awaitable[None]:
    from ubinascii import hexlify

    from trezor.ui.layouts import confirm_address

    contract_address_hex = "0x" + hexlify(address_bytes).decode()
    return confirm_address(
        "Unknown token",
        contract_address_hex,
        "Contract:",
        "unknown_token",
        br_code=ButtonRequestType.SignTx,
    )


def require_confirm_address(address_bytes: bytes) -> Awaitable[None]:
    from ubinascii import hexlify

    from trezor.ui.layouts import confirm_address

    address_hex = "0x" + hexlify(address_bytes).decode()
    return confirm_address(
        "Signing address",
        address_hex,
        br_code=ButtonRequestType.SignTx,
    )


def require_confirm_data(data: bytes, data_total: int) -> Awaitable[None]:
    return confirm_blob(
        "confirm_data",
        "Confirm data",
        data,
        f"Size: {data_total} bytes",
        br_code=ButtonRequestType.SignTx,
        ask_pagination=True,
    )


async def confirm_typed_data_final() -> None:
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "confirm_typed_data_final",
        "Confirm typed data",
        "Really sign EIP-712 typed data?",
        verb="Hold to confirm",
        hold=True,
    )


def confirm_empty_typed_message() -> Awaitable[None]:
    return confirm_text(
        "confirm_empty_typed_message",
        "Confirm message",
        "",
        "No message field",
    )


async def should_show_domain(name: bytes, version: bytes) -> bool:
    domain_name = decode_typed_data(name, "string")
    domain_version = decode_typed_data(version, "string")

    para = (
        (ui.NORMAL, "Name and version"),
        (ui.DEMIBOLD, domain_name),
        (ui.DEMIBOLD, domain_version),
    )
    return await should_show_more(
        "Confirm domain",
        para,
        "Show full domain",
        "should_show_domain",
    )


async def should_show_struct(
    description: str,
    data_members: list[EthereumStructMember],
    title: str = "Confirm struct",
    button_text: str = "Show full struct",
) -> bool:
    para = (
        (ui.DEMIBOLD, description),
        (
            ui.NORMAL,
            format_plural("Contains {count} {plural}", len(data_members), "key"),
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
    para = ((ui.NORMAL, format_plural("Array of {count} {plural}", size, data_type)),)
    return await should_show_more(
        limit_str(".".join(parent_objects)),
        para,
        "Show full array",
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
) -> str:
    from trezor.strings import format_amount

    if token:
        suffix = token.symbol
        decimals = token.decimals
    else:
        suffix = network.symbol
        decimals = 18

    # Don't want to display wei values for tokens with small decimal numbers
    if decimals > 9 and value < 10 ** (decimals - 9):
        suffix = "Wei " + suffix
        decimals = 0

    return f"{format_amount(value, decimals)} {suffix}"


def limit_str(s: str, limit: int = 16) -> str:
    """Shortens string to show the last <limit> characters."""
    if len(s) <= limit + 2:
        return s

    return ".." + s[-limit:]
