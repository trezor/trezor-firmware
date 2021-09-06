from ubinascii import hexlify

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_metadata,
    confirm_output,
    confirm_text,
    confirm_total,
    show_pubkey,
)
from trezor.utils import chunks

from .helpers import (
    format_coin_amount,
    get_multisig_tx_text,
    get_unlock_tx_text,
    get_vote_tx_text,
)


async def require_confirm_tx(ctx, to, value):
    await confirm_output(
        ctx,
        address=to,
        amount=format_coin_amount(value),
        font_amount=ui.BOLD,
        to_str="\nto\n",
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_data(ctx, data: str):
    await confirm_text(ctx, "confirm_data", title="Data field", data=data)


async def require_confirm_delegate_registration(ctx, username):
    await confirm_metadata(
        ctx,
        "confirm_delegate",
        title="Confirm delegate",
        content="Do you really want to register a delegate?\n{}",
        param="\n".join(chunks(username, 20)),
        param_font=ui.BOLD,
        hide_continue=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_vote_tx(ctx, votes):
    await confirm_metadata(
        ctx,
        "confirm_vote",
        title="Confirm vote",
        content="\n".join(get_vote_tx_text(votes)),
        hide_continue=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_unlock_tx(ctx, unlockObjects):
    await confirm_metadata(
        ctx,
        "confirm_unlock",
        title="Confirm unlock",
        content=get_unlock_tx_text(unlockObjects),
        hide_continue=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_reclaim_tx(ctx, amount):
    await confirm_metadata(
        ctx,
        "confirm_reclaim",
        title="Confirm reclaim",
        content="Reclaim: %s" % format_coin_amount(amount),
        hide_continue=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_public_key(ctx, public_key):
    return await show_pubkey(ctx, hexlify(public_key).decode())


async def require_confirm_multisig_tx(ctx, asset):
    await confirm_metadata(
        ctx,
        "confirm_multisig",
        title="Confirm multisig",
        content=get_multisig_tx_text(asset),
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
