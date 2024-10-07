from micropython import const
from typing import TYPE_CHECKING

from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui import layouts
from trezor.ui.layouts import confirm_metadata

from apps.common.paths import address_n_to_str

from .. import addresses
from ..common import (
    BIP32_WALLET_DEPTH,
    CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES,
    format_fee_rate,
)
from ..keychain import address_n_to_name

if TYPE_CHECKING:
    from trezor.enums import AmountUnit
    from trezor.messages import TxAckPaymentRequest, TxOutput
    from trezor.ui.layouts import LayoutType

    from apps.common.coininfo import CoinInfo
    from apps.common.paths import Bip32Path

_LOCKTIME_TIMESTAMP_MIN_VALUE = const(500_000_000)


def format_coin_amount(amount: int, coin: CoinInfo, amount_unit: AmountUnit) -> str:
    from trezor.enums import AmountUnit

    decimals, shortcut = coin.decimals, coin.coin_shortcut
    if amount_unit == AmountUnit.SATOSHI:
        decimals = 0
        shortcut = "sat"
        if coin.coin_shortcut != "BTC":
            shortcut += " " + coin.coin_shortcut
    elif amount_unit == AmountUnit.MICROBITCOIN and decimals >= 6:
        decimals -= 6
        shortcut = "u" + shortcut
    elif amount_unit == AmountUnit.MILLIBITCOIN and decimals >= 3:
        decimals -= 3
        shortcut = "m" + shortcut
    # we don't need to do anything for AmountUnit.BITCOIN
    return f"{format_amount(amount, decimals)} {shortcut}"


def account_label(coin: CoinInfo, address_n: Bip32Path | None) -> str:
    return (
        TR.bitcoin__multiple_accounts
        if address_n is None
        else address_n_to_name(coin, list(address_n) + [0] * BIP32_WALLET_DEPTH)
        or f"Path {address_n_to_str(address_n)}"
    )


async def confirm_output(
    output: TxOutput,
    coin: CoinInfo,
    amount_unit: AmountUnit,
    output_index: int,
    chunkify: bool,
    address_n: Bip32Path | None,
) -> None:
    from trezor.enums import OutputScriptType

    from . import omni

    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        data = output.op_return_data
        assert data is not None
        if omni.is_valid(data):
            # OMNI transaction
            layout: LayoutType = confirm_metadata(
                "omni_transaction",
                "OMNI transaction",
                omni.parse(data),
                verb=TR.buttons__confirm,
                br_code=ButtonRequestType.ConfirmOutput,
            )
        else:
            # generic OP_RETURN
            layout = layouts.confirm_blob(
                "op_return",
                "OP_RETURN",
                data,
                br_code=ButtonRequestType.ConfirmOutput,
            )
    else:
        assert output.address is not None
        address_short = addresses.address_short(coin, output.address)
        if output.payment_req_index is not None:
            title = TR.bitcoin__title_confirm_details
        else:
            title = None

        address_label = None
        if output.address_n and not output.multisig:
            from trezor import utils

            # Showing the account string only for model_tr layout
            # TODO expose layout_type so that we can check for it, instead of listing
            # all models that use the layout?
            show_account_str = (
                # pylint: disable-next=consider-using-in
                utils.INTERNAL_MODEL == "T2B1"
                or utils.INTERNAL_MODEL == "T3B1"
            )
            script_type = CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES[output.script_type]
            address_label = (
                address_n_to_name(
                    coin,
                    output.address_n,
                    script_type,
                    show_account_str=show_account_str,
                )
                or f"{TR.send__address_path} {address_n_to_str(output.address_n)}"
            )

        layout = layouts.confirm_output(
            address_short,
            format_coin_amount(output.amount, coin, amount_unit),
            title=title,
            address_label=address_label,
            output_index=output_index,
            chunkify=chunkify,
            source_account=account_label(coin, address_n),
            source_account_path=address_n_to_str(address_n) if address_n else None,
        )

    await layout


async def confirm_decred_sstx_submission(
    output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit
) -> None:
    assert output.address is not None
    address_short = addresses.address_short(coin, output.address)
    amount = format_coin_amount(output.amount, coin, amount_unit)

    await layouts.confirm_value(
        TR.bitcoin__title_purchase_ticket,
        amount,
        TR.bitcoin__ticket_amount,
        "confirm_decred_sstx_submission",
        ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__confirm,
    )

    await layouts.confirm_value(
        TR.bitcoin__title_purchase_ticket,
        address_short,
        TR.bitcoin__voting_rights,
        "confirm_decred_sstx_submission",
        ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__purchase,
    )


async def should_show_payment_request_details(
    msg: TxAckPaymentRequest,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> bool:
    from trezor import wire

    memo_texts: list[str] = []
    for m in msg.memos:
        if m.text_memo is not None:
            memo_texts.append(m.text_memo.text)
        elif m.refund_memo is not None:
            pass
        elif m.coin_purchase_memo is not None:
            memo_texts.append(f"{TR.words__buying} {m.coin_purchase_memo.amount}.")
        else:
            raise wire.DataError("Unrecognized memo type in payment request memo.")

    assert msg.amount is not None

    return await layouts.should_show_payment_request_details(
        msg.recipient_name,
        format_coin_amount(msg.amount, coin, amount_unit),
        memo_texts,
    )


async def confirm_replacement(title: str, txid: bytes) -> None:
    from ubinascii import hexlify

    await layouts.confirm_replacement(
        title,
        hexlify(txid).decode(),
    )


async def confirm_modify_output(
    txo: TxOutput,
    orig_txo: TxOutput,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> None:
    assert txo.address is not None
    address_short = addresses.address_short(coin, txo.address)
    amount_change = txo.amount - orig_txo.amount
    await layouts.confirm_modify_output(
        address_short,
        amount_change,
        format_coin_amount(abs(amount_change), coin, amount_unit),
        format_coin_amount(txo.amount, coin, amount_unit),
    )


async def confirm_modify_fee(
    title: str,
    user_fee_change: int,
    total_fee_new: int,
    fee_rate: float,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> None:
    await layouts.confirm_modify_fee(
        title,
        user_fee_change,
        format_coin_amount(abs(user_fee_change), coin, amount_unit),
        format_coin_amount(total_fee_new, coin, amount_unit),
        fee_rate_amount=format_fee_rate(fee_rate, coin) if fee_rate >= 0 else None,
    )


async def confirm_joint_total(
    spending: int,
    total: int,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> None:
    await layouts.confirm_joint_total(
        spending_amount=format_coin_amount(spending, coin, amount_unit),
        total_amount=format_coin_amount(total, coin, amount_unit),
    )


async def confirm_total(
    spending: int,
    fee: int,
    fee_rate: float,
    coin: CoinInfo,
    amount_unit: AmountUnit,
    address_n: Bip32Path | None,
) -> None:

    await layouts.confirm_total(
        format_coin_amount(spending, coin, amount_unit),
        format_coin_amount(fee, coin, amount_unit),
        fee_rate_amount=format_fee_rate(fee_rate, coin) if fee_rate >= 0 else None,
        source_account=account_label(coin, address_n),
        source_account_path=address_n_to_str(address_n) if address_n else None,
    )


async def confirm_feeoverthreshold(
    fee: int, coin: CoinInfo, amount_unit: AmountUnit
) -> None:
    fee_amount = format_coin_amount(fee, coin, amount_unit)
    await layouts.show_warning(
        "fee_over_threshold",
        TR.bitcoin__unusually_high_fee,
        fee_amount,
        br_code=ButtonRequestType.FeeOverThreshold,
    )


async def confirm_change_count_over_threshold(change_count: int) -> None:
    await layouts.show_warning(
        "change_count_over_threshold",
        TR.bitcoin__lot_of_change_outputs,
        f"{str(change_count)} {TR.words__outputs}",
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_unverified_external_input() -> None:
    await layouts.show_warning(
        "unverified_external_input",
        TR.bitcoin__unverified_external_inputs,
        TR.words__continue_anyway_question,
        button=TR.buttons__continue,
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_multiple_accounts() -> None:
    await layouts.show_warning(
        "sending_from_multiple_accounts",
        TR.send__from_multiple_accounts,
        TR.words__continue_anyway_question,
        button=TR.buttons__continue,
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_nondefault_locktime(lock_time: int, lock_time_disabled: bool) -> None:
    from trezor.strings import format_timestamp

    if lock_time_disabled:
        await layouts.show_warning(
            "nondefault_locktime",
            TR.bitcoin__locktime_no_effect,
            TR.words__continue_anyway_question,
            button=TR.buttons__continue,
            br_code=ButtonRequestType.SignTx,
        )
    else:
        if lock_time < _LOCKTIME_TIMESTAMP_MIN_VALUE:
            text = TR.bitcoin__locktime_set_to_blockheight
            value = str(lock_time)
        else:
            text = TR.bitcoin__locktime_set_to
            value = format_timestamp(lock_time)
        await layouts.confirm_value(
            TR.bitcoin__confirm_locktime,
            value,
            text,
            "nondefault_locktime",
            br_code=ButtonRequestType.SignTx,
            verb=TR.buttons__confirm,
        )
