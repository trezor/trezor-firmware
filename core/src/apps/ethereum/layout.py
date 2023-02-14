from typing import TYPE_CHECKING

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_plural
from trezor.ui.layouts import (
    confirm_amount,
    confirm_blob,
    confirm_text,
    confirm_total,
    should_show_more,
)

from . import networks
from .helpers import decode_typed_data

if TYPE_CHECKING:
    from typing import Awaitable, Iterable

    from trezor.messages import EthereumFieldType, EthereumStructMember
    from trezor.wire import Context
    from . import tokens


def require_confirm_tx(
    ctx: Context,
    to_bytes: bytes,
    value: int,
    chain_id: int,
    token: tokens.TokenInfo | None = None,
) -> Awaitable[None]:
    from .helpers import address_from_bytes
    from trezor.ui.layouts import confirm_output

    if to_bytes:
        to_str = address_from_bytes(to_bytes, networks.by_chain_id(chain_id))
    else:
        to_str = "new contract?"
    return confirm_output(
        ctx,
        to_str,
        format_ethereum_amount(value, token, chain_id),
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_fee(
    ctx: Context,
    spending: int,
    gas_price: int,
    gas_limit: int,
    chain_id: int,
    token: tokens.TokenInfo | None = None,
) -> None:
    await confirm_amount(
        ctx,
        title="Confirm fee",
        description="Gas price:",
        amount=format_ethereum_amount(gas_price, None, chain_id),
    )
    await confirm_total(
        ctx,
        total_amount=format_ethereum_amount(spending, token, chain_id),
        fee_amount=format_ethereum_amount(gas_price * gas_limit, None, chain_id),
        total_label="Amount sent:",
        fee_label="Maximum fee:",
    )


async def require_confirm_eip1559_fee(
    ctx: Context,
    spending: int,
    max_priority_fee: int,
    max_gas_fee: int,
    gas_limit: int,
    chain_id: int,
    token: tokens.TokenInfo | None = None,
) -> None:
    await confirm_amount(
        ctx,
        "Confirm fee",
        format_ethereum_amount(max_gas_fee, None, chain_id),
        "Maximum fee per gas",
    )
    await confirm_amount(
        ctx,
        "Confirm fee",
        format_ethereum_amount(max_priority_fee, None, chain_id),
        "Priority fee per gas",
    )
    await confirm_total(
        ctx,
        format_ethereum_amount(spending, token, chain_id),
        format_ethereum_amount(max_gas_fee * gas_limit, None, chain_id),
        total_label="Amount sent:",
        fee_label="Maximum fee:",
    )


def require_confirm_unknown_token(
    ctx: Context, address_bytes: bytes
) -> Awaitable[None]:
    from ubinascii import hexlify
    from trezor.ui.layouts import confirm_address

    contract_address_hex = "0x" + hexlify(address_bytes).decode()
    return confirm_address(
        ctx,
        "Unknown token",
        contract_address_hex,
        "Contract:",
        "unknown_token",
        br_code=ButtonRequestType.SignTx,
    )


def require_confirm_address(ctx: Context, address_bytes: bytes) -> Awaitable[None]:
    from ubinascii import hexlify
    from trezor.ui.layouts import confirm_address

    address_hex = "0x" + hexlify(address_bytes).decode()
    return confirm_address(
        ctx,
        "Signing address",
        address_hex,
        br_code=ButtonRequestType.SignTx,
    )


def require_confirm_data(ctx: Context, data: bytes, data_total: int) -> Awaitable[None]:
    return confirm_blob(
        ctx,
        "confirm_data",
        "Confirm data",
        data,
        f"Size: {data_total} bytes",
        br_code=ButtonRequestType.SignTx,
        ask_pagination=True,
    )


async def confirm_typed_data_final(ctx: Context) -> None:
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        ctx,
        "confirm_typed_data_final",
        "Confirm typed data",
        "Really sign EIP-712 typed data?",
        verb="Hold to confirm",
        hold=True,
    )


def confirm_empty_typed_message(ctx: Context) -> Awaitable[None]:
    return confirm_text(
        ctx,
        "confirm_empty_typed_message",
        "Confirm message",
        "",
        "No message field",
    )


async def should_show_domain(ctx: Context, name: bytes, version: bytes) -> bool:
    domain_name = decode_typed_data(name, "string")
    domain_version = decode_typed_data(version, "string")

    para = (
        (ui.NORMAL, "Name and version"),
        (ui.BOLD, domain_name),
        (ui.BOLD, domain_version),
    )
    return await should_show_more(
        ctx,
        "Confirm domain",
        para,
        "Show full domain",
        "should_show_domain",
    )


async def should_show_struct(
    ctx: Context,
    description: str,
    data_members: list[EthereumStructMember],
    title: str = "Confirm struct",
    button_text: str = "Show full struct",
) -> bool:
    para = (
        (ui.BOLD, description),
        (
            ui.NORMAL,
            format_plural("Contains {count} {plural}", len(data_members), "key"),
        ),
        (ui.NORMAL, ", ".join(field.name for field in data_members)),
    )
    return await should_show_more(
        ctx,
        title,
        para,
        button_text,
        "should_show_struct",
    )


async def should_show_array(
    ctx: Context,
    parent_objects: Iterable[str],
    data_type: str,
    size: int,
) -> bool:
    para = ((ui.NORMAL, format_plural("Array of {count} {plural}", size, data_type)),)
    return await should_show_more(
        ctx,
        limit_str(".".join(parent_objects)),
        para,
        "Show full array",
        "should_show_array",
    )


async def confirm_typed_value(
    ctx: Context,
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
            ctx,
            "confirm_typed_value",
            title,
            data,
            description,
            ask_pagination=True,
        )
    else:
        await confirm_text(
            ctx,
            "confirm_typed_value",
            title,
            data,
            description,
        )


def format_ethereum_amount(
    value: int, token: tokens.TokenInfo | None, chain_id: int
) -> str:
    from trezor.strings import format_amount

    if token:
        suffix = token.symbol
        decimals = token.decimals
    else:
        suffix = networks.shortcut_by_chain_id(chain_id)
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
