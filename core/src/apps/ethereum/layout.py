from ubinascii import hexlify

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_address,
    confirm_amount,
    confirm_blob,
    confirm_output,
)
from trezor.ui.layouts.tt.altcoin import confirm_total_ethereum

from . import networks, tokens
from .address import address_from_bytes


async def require_confirm_tx(ctx, to_bytes, value, chain_id, token=None):
    if to_bytes:
        to_str = address_from_bytes(to_bytes, networks.by_chain_id(chain_id))
    else:
        to_str = "new contract?"
    await confirm_output(
        ctx,
        address=to_str,
        amount=format_ethereum_amount(value, token, chain_id),
        font_amount=ui.BOLD,
        color_to=ui.GREY,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_fee(
    ctx, spending, gas_price, gas_limit, chain_id, token=None
):
    await confirm_total_ethereum(
        ctx,
        format_ethereum_amount(spending, token, chain_id),
        format_ethereum_amount(gas_price, None, chain_id),
        format_ethereum_amount(gas_price * gas_limit, None, chain_id),
    )


async def require_confirm_eip1559_fee(
    ctx, max_priority_fee, max_gas_fee, gas_limit, chain_id
):
    await confirm_amount(
        ctx,
        title="Confirm fee",
        description="Maximum fee per gas",
        amount=format_ethereum_amount(max_gas_fee, None, chain_id),
    )
    await confirm_amount(
        ctx,
        title="Confirm fee",
        description="Priority fee per gas",
        amount=format_ethereum_amount(max_priority_fee, None, chain_id),
    )
    await confirm_amount(
        ctx,
        title="Confirm fee",
        description="Maximum fee",
        amount=format_ethereum_amount(max_gas_fee * gas_limit, None, chain_id),
    )


async def require_confirm_unknown_token(ctx, address_bytes):
    contract_address_hex = "0x" + hexlify(address_bytes).decode()
    await confirm_address(
        ctx,
        "Unknown token",
        contract_address_hex,
        description="Contract:",
        br_type="unknown_token",
        icon_color=ui.ORANGE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_data(ctx, data, data_total):
    await confirm_blob(
        ctx,
        "confirm_data",
        title="Confirm data",
        description="Size: %d bytes" % data_total,
        data=data,
        br_code=ButtonRequestType.SignTx,
    )


def format_ethereum_amount(value: int, token, chain_id: int):
    if token is tokens.UNKNOWN_TOKEN:
        suffix = "Wei UNKN"
        decimals = 0
    elif token:
        suffix = token[2]
        decimals = token[3]
    else:
        suffix = networks.shortcut_by_chain_id(chain_id)
        decimals = 18

    # Don't want to display wei values for tokens with small decimal numbers
    if decimals > 9 and value < 10 ** (decimals - 9):
        suffix = "Wei " + suffix
        decimals = 0

    return "%s %s" % (format_amount(value, decimals), suffix)
