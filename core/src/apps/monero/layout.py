from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (  # noqa: F401
    confirm_action,
    confirm_metadata,
    monero_keyimage_sync_progress,
    monero_live_refresh_progress,
    monero_transaction_progress_inner,
)

DUMMY_PAYMENT_ID = b"\x00\x00\x00\x00\x00\x00\x00\x00"


if TYPE_CHECKING:
    from trezor.enums import MoneroNetworkType
    from trezor.messages import (
        MoneroTransactionData,
        MoneroTransactionDestinationEntry,
    )
    from trezor.wire import Context

    from .signing.state import State


BRT_SignTx = ButtonRequestType.SignTx  # global_import_cache


class MoneroTransactionProgress:
    def __init__(self) -> None:
        self.inner = None

    def step(self, state: State, step: int, sub_step: int = 0) -> None:
        if step == 0 or self.inner is None:
            self.inner = monero_transaction_progress_inner()
            info = "Signing..."
        elif step == state.STEP_INP:
            info = f"Processing inputs\n{sub_step + 1}/{state.input_count}"
        elif step == state.STEP_VINI:
            info = f"Hashing inputs\n{sub_step + 1}/{state.input_count}"
        elif step == state.STEP_ALL_IN:
            info = "Processing..."
        elif step == state.STEP_OUT:
            info = f"Processing outputs\n{sub_step + 1}/{state.output_count}"
        elif step == state.STEP_ALL_OUT:
            info = "Postprocessing..."
        elif step == state.STEP_SIGN:
            info = f"Signing inputs\n{sub_step + 1}/{state.input_count}"
        else:
            info = "Processing..."

        state.progress_cur += 1

        p = 1000 * state.progress_cur // state.progress_total
        self.inner.report(p, info)


def _format_amount(value: int) -> str:
    from trezor import strings

    return f"{strings.format_amount(value, 12)} XMR"


async def require_confirm_watchkey(ctx: Context) -> None:
    await confirm_action(
        ctx,
        "get_watchkey",
        "Confirm export",
        description="Do you really want to export watch-only credentials?",
        br_code=BRT_SignTx,
    )


async def require_confirm_keyimage_sync(ctx: Context) -> None:
    await confirm_action(
        ctx,
        "key_image_sync",
        "Confirm ki sync",
        description="Do you really want to\nsync key images?",
        br_code=BRT_SignTx,
    )


async def require_confirm_live_refresh(ctx: Context) -> None:
    await confirm_action(
        ctx,
        "live_refresh",
        "Confirm refresh",
        description="Do you really want to\nstart refresh?",
        br_code=BRT_SignTx,
    )


async def require_confirm_tx_key(ctx: Context, export_key: bool = False) -> None:
    description = (
        "Do you really want to export tx_key?"
        if export_key
        else "Do you really want to export tx_der\nfor tx_proof?"
    )
    await confirm_action(
        ctx,
        "export_tx_key",
        "Confirm export",
        description=description,
        br_code=BRT_SignTx,
    )


async def require_confirm_transaction(
    ctx: Context,
    state: State,
    tsx_data: MoneroTransactionData,
    network_type: MoneroNetworkType,
    progress: MoneroTransactionProgress,
) -> None:
    """
    Ask for confirmation from user.
    """
    from apps.monero.xmr.addresses import get_change_addr_idx

    outputs = tsx_data.outputs
    change_idx = get_change_addr_idx(outputs, tsx_data.change_dts)
    payment_id = tsx_data.payment_id  # local_cache_attribute

    if tsx_data.unlock_time != 0:
        await _require_confirm_unlock_time(ctx, tsx_data.unlock_time)

    for idx, dst in enumerate(outputs):
        is_change = change_idx is not None and idx == change_idx
        if is_change:
            continue  # Change output does not need confirmation
        is_dummy = change_idx is None and dst.amount == 0 and len(outputs) == 2
        if is_dummy:
            continue  # Dummy output does not need confirmation
        if tsx_data.integrated_indices and idx in tsx_data.integrated_indices:
            cur_payment = payment_id
        else:
            cur_payment = None
        await _require_confirm_output(ctx, dst, network_type, cur_payment)

    if (
        payment_id
        and not tsx_data.integrated_indices
        and payment_id != DUMMY_PAYMENT_ID
    ):
        await _require_confirm_payment_id(ctx, payment_id)

    await _require_confirm_fee(ctx, tsx_data.fee)
    progress.step(state, 0)


async def _require_confirm_output(
    ctx: Context,
    dst: MoneroTransactionDestinationEntry,
    network_type: MoneroNetworkType,
    payment_id: bytes | None,
) -> None:
    """
    Single transaction destination confirmation
    """
    from apps.monero.xmr.addresses import encode_addr
    from apps.monero.xmr.networks import net_version
    from trezor.ui.layouts import confirm_output

    version = net_version(network_type, dst.is_subaddress, payment_id is not None)
    addr = encode_addr(
        version, dst.addr.spend_public_key, dst.addr.view_public_key, payment_id
    )

    await confirm_output(
        ctx,
        addr,
        _format_amount(dst.amount),
        br_code=BRT_SignTx,
    )


async def _require_confirm_payment_id(ctx: Context, payment_id: bytes) -> None:
    from trezor.ui.layouts import confirm_blob

    await confirm_blob(
        ctx,
        "confirm_payment_id",
        "Payment ID",
        payment_id,
        br_code=BRT_SignTx,
    )


async def _require_confirm_fee(ctx: Context, fee: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_final",
        "Confirm fee",
        "{}",
        _format_amount(fee),
        hold=True,
    )


async def _require_confirm_unlock_time(ctx: Context, unlock_time: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_locktime",
        "Confirm unlock time",
        "Unlock time for this transaction is set to {}",
        str(unlock_time),
        BRT_SignTx,
    )
