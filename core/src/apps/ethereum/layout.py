from ubinascii import hexlify

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_hex, confirm_output, confirm_total_ethereum

from . import networks, tokens
from .address import address_from_bytes


async def require_confirm_tx(ctx, to_bytes, value, chain_id, token=None, tx_type=None):
    if to_bytes:
        to_str = address_from_bytes(to_bytes, networks.by_chain_id(chain_id))
    else:
        to_str = "new contract?"
    await confirm_output(
        ctx,
        address=to_str,
        amount=format_ethereum_amount(value, token, chain_id, tx_type),
        font_amount=ui.BOLD,
        color_to=ui.GREY,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_fee(
    ctx, spending, gas_price, gas_limit, chain_id, token=None, tx_type=None
):
    await confirm_total_ethereum(
        ctx,
        format_ethereum_amount(spending, token, chain_id, tx_type),
        format_ethereum_amount(gas_price, None, chain_id, tx_type),
        format_ethereum_amount(gas_price * gas_limit, None, chain_id, tx_type),
    )


async def require_confirm_unknown_token(ctx, address_bytes):
    contract_address_hex = "0x" + hexlify(address_bytes).decode()
    await confirm_hex(
        ctx,
        "confirm_unknown",
        title="Unknown token",
        data=contract_address_hex,
        truncate=True,
        description="Contract:",
        color_description=ui.GREY,
        icon_color=ui.ORANGE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_data(ctx, data, data_total):
    data_str = hexlify(data[:36]).decode()
    if data_total > 36:
        data_str = data_str[:-2] + ".."
    await confirm_hex(
        ctx,
        "confirm_data",
        title="Confirm data",
        data=data_str,
        truncate=True,
        subtitle="Size: %d bytes" % data_total,
        br_code=ButtonRequestType.SignTx,
    )


def format_ethereum_amount(value: int, token, chain_id: int, tx_type=None):
    if token is tokens.UNKNOWN_TOKEN:
        suffix = "Wei UNKN"
        decimals = 0
    elif token:
        suffix = token[2]
        decimals = token[3]
    else:
        suffix = networks.shortcut_by_chain_id(chain_id, tx_type)
        decimals = 18

    # Don't want to display wei values for tokens with small decimal numbers
    if decimals > 9 and value < 10 ** (decimals - 9):
        suffix = "Wei " + suffix
        decimals = 0

    return "%s %s" % (format_amount(value, decimals), suffix)
