from typing import TYPE_CHECKING

from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_action, confirm_metadata  # noqa: F401
from trezor.ui.layouts.progress import (  # noqa: F401
    monero_keyimage_sync_progress,
    monero_live_refresh_progress,
    monero_transaction_progress_inner,
)

DUMMY_PAYMENT_ID = b"\x00\x00\x00\x00\x00\x00\x00\x00"


if TYPE_CHECKING:
    from trezor.enums import MoneroNetworkType
    from trezor.messages import MoneroTransactionData, MoneroTransactionDestinationEntry

    from .signing.state import State


BRT_SignTx = ButtonRequestType.SignTx  # global_import_cache


class MoneroTransactionProgress:
    def __init__(self) -> None:
        self.inner = None

    def step(self, state: State, step: int, sub_step: int = 0) -> None:
        if step == 0 or self.inner is None:
            self.inner = monero_transaction_progress_inner()
            info = TR.monero__signing
        elif step == state.STEP_INP:
            info = f"{TR.monero__processing_inputs}\n{sub_step + 1}/{state.input_count}"
        elif step == state.STEP_VINI:
            info = f"{TR.monero__hashing_inputs}n{sub_step + 1}/{state.input_count}"
        elif step == state.STEP_ALL_IN:
            info = TR.monero__processing
        elif step == state.STEP_OUT:
            info = (
                f"{TR.monero__processing_outputs}\n{sub_step + 1}/{state.output_count}"
            )
        elif step == state.STEP_ALL_OUT:
            info = TR.monero__postprocessing
        elif step == state.STEP_SIGN:
            info = f"{TR.monero__signing_inputs}\n{sub_step + 1}/{state.input_count}"
        else:
            info = TR.monero__processing

        state.progress_cur += 1

        p = 1000 * state.progress_cur // state.progress_total
        self.inner.report(p, info)


def _format_amount(value: int) -> str:
    from trezor import strings

    return f"{strings.format_amount(value, 12)} XMR"


async def require_confirm_watchkey() -> None:
    await confirm_action(
        "get_watchkey",
        TR.monero__confirm_export,
        description=TR.monero__wanna_export_watchkey,
        br_code=BRT_SignTx,
    )


async def require_confirm_keyimage_sync() -> None:
    await confirm_action(
        "key_image_sync",
        TR.monero__confirm_ki_sync,
        description=TR.monero__wanna_sync_key_images,
        br_code=BRT_SignTx,
    )


async def require_confirm_live_refresh() -> None:
    await confirm_action(
        "live_refresh",
        TR.monero__confirm_refresh,
        description=TR.monero__wanna_start_refresh,
        br_code=BRT_SignTx,
    )


async def require_confirm_tx_key(export_key: bool = False) -> None:
    description = (
        TR.monero__wanna_export_tx_key if export_key else TR.monero__wanna_export_tx_der
    )
    await confirm_action(
        "export_tx_key",
        TR.monero__confirm_export,
        description=description,
        br_code=BRT_SignTx,
    )


async def require_confirm_transaction(
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
        await _require_confirm_unlock_time(tsx_data.unlock_time)

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
        await _require_confirm_output(
            dst, network_type, cur_payment, chunkify=bool(tsx_data.chunkify)
        )

    if (
        payment_id
        and not tsx_data.integrated_indices
        and payment_id != DUMMY_PAYMENT_ID
    ):
        await _require_confirm_payment_id(payment_id)

    await _require_confirm_fee(tsx_data.fee)
    progress.step(state, 0)


async def _require_confirm_output(
    dst: MoneroTransactionDestinationEntry,
    network_type: MoneroNetworkType,
    payment_id: bytes | None,
    chunkify: bool,
) -> None:
    """
    Single transaction destination confirmation
    """
    from trezor.ui.layouts import confirm_output

    from apps.monero.xmr.addresses import encode_addr
    from apps.monero.xmr.networks import net_version

    version = net_version(network_type, dst.is_subaddress, payment_id is not None)
    addr = encode_addr(
        version, dst.addr.spend_public_key, dst.addr.view_public_key, payment_id
    )

    await confirm_output(
        addr,
        _format_amount(dst.amount),
        br_code=BRT_SignTx,
        chunkify=chunkify,
    )


async def _require_confirm_payment_id(payment_id: bytes) -> None:
    from trezor.ui.layouts import confirm_blob

    await confirm_blob(
        "confirm_payment_id",
        TR.monero__payment_id,
        payment_id,
        br_code=BRT_SignTx,
    )


async def _require_confirm_fee(fee: int) -> None:
    await confirm_metadata(
        "confirm_final",
        TR.words__confirm_fee,
        "{}",
        _format_amount(fee),
        hold=True,
    )


async def _require_confirm_unlock_time(unlock_time: int) -> None:
    await confirm_metadata(
        "confirm_locktime",
        TR.monero__confirm_unlock_time,
        TR.monero__unlock_time_set_template,
        str(unlock_time),
        BRT_SignTx,
    )
