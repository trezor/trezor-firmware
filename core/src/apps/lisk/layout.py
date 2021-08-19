from ubinascii import hexlify

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_metadata,
    confirm_output,
    confirm_total,
    show_pubkey,
)
from trezor.utils import chunks

from .helpers import get_vote_tx_text


async def require_confirm_tx(ctx, to, value):
    await confirm_output(
        ctx,
        to,
        format_coin_amount(value),
        font_amount=ui.BOLD,
        to_str="\nto\n",
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_delegate_registration(ctx, delegate_name):
    await confirm_metadata(
        ctx,
        "confirm_delegate",
        title="Confirm transaction",
        content="Do you really want to register a delegate?\n{}",
        param="\n".join(chunks(delegate_name, 20)),
        param_font=ui.BOLD,
        hide_continue=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_vote_tx(ctx, votes):
    await confirm_metadata(
        ctx,
        "confirm_vote",
        title="Confirm transaction",
        content="\n".join(get_vote_tx_text(votes)),
        hide_continue=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_public_key(ctx, public_key):
    return await show_pubkey(ctx, hexlify(public_key).decode())


async def require_confirm_multisig(ctx, multisignature):
    content = "Keys group length: %s\nLife time: %s\nMin: %s" % (
        len(multisignature.keys_group),
        multisignature.life_time,
        multisignature.min,
    )
    await confirm_metadata(
        ctx,
        "confirm_multisig",
        title="Confirm transaction",
        content=content,
        hide_continue=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_fee(ctx, value, fee):
    await confirm_total(
        ctx,
        total_amount=format_coin_amount(value),
        total_label="",
        fee_amount=format_coin_amount(fee),
        fee_label="\nfee:\n",
        br_code=ButtonRequestType.ConfirmOutput,
    )


def format_coin_amount(value):
    return "%s LSK" % format_amount(value, 8)
