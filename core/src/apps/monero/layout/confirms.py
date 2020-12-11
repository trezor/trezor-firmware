from ubinascii import hexlify

from trezor import ui, wire
from trezor.messages import ButtonRequestType
from trezor.ui.components.tt.text import Text
from trezor.ui.popup import Popup
from trezor.utils import chunks

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.monero.layout import common

DUMMY_PAYMENT_ID = b"\x00\x00\x00\x00\x00\x00\x00\x00"


if False:
    from typing import Optional
    from apps.monero.signing.state import State
    from trezor.messages.MoneroTransactionData import MoneroTransactionData
    from trezor.messages.MoneroTransactionDestinationEntry import (
        MoneroTransactionDestinationEntry,
    )


async def require_confirm_watchkey(ctx):
    content = Text("Confirm export", ui.ICON_SEND, ui.GREEN)
    content.normal("Do you really want to", "export watch-only", "credentials?")
    await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_keyimage_sync(ctx):
    content = Text("Confirm ki sync", ui.ICON_SEND, ui.GREEN)
    content.normal("Do you really want to", "sync key images?")
    await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_live_refresh(ctx):
    content = Text("Confirm refresh", ui.ICON_SEND, ui.GREEN)
    content.normal("Do you really want to", "start refresh?")
    await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_tx_key(ctx, export_key=False):
    content = Text("Confirm export", ui.ICON_SEND, ui.GREEN)
    txt = ["Do you really want to"]
    if export_key:
        txt.append("export tx_key?")
    else:
        txt.append("export tx_der")
        txt.append("for tx_proof?")

    content.normal(*txt)
    await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_transaction(
    ctx, state: State, tsx_data: MoneroTransactionData, network_type: int
):
    """
    Ask for confirmation from user.
    """
    from apps.monero.xmr.addresses import get_change_addr_idx

    outputs = tsx_data.outputs
    change_idx = get_change_addr_idx(outputs, tsx_data.change_dts)
    has_integrated = bool(tsx_data.integrated_indices)
    has_payment = bool(tsx_data.payment_id)

    if tsx_data.unlock_time != 0:
        await _require_confirm_unlock_time(ctx, tsx_data.unlock_time)

    for idx, dst in enumerate(outputs):
        is_change = change_idx is not None and idx == change_idx
        if is_change:
            continue  # Change output does not need confirmation
        is_dummy = change_idx is None and dst.amount == 0 and len(outputs) == 2
        if is_dummy:
            continue  # Dummy output does not need confirmation
        if has_integrated and idx in tsx_data.integrated_indices:
            cur_payment = tsx_data.payment_id
        else:
            cur_payment = None
        await _require_confirm_output(ctx, dst, network_type, cur_payment)

    if has_payment and not has_integrated and tsx_data.payment_id != DUMMY_PAYMENT_ID:
        await _require_confirm_payment_id(ctx, tsx_data.payment_id)

    await _require_confirm_fee(ctx, tsx_data.fee)
    await transaction_step(state, 0)


async def _require_confirm_output(
    ctx, dst: MoneroTransactionDestinationEntry, network_type: int, payment_id: bytes
):
    """
    Single transaction destination confirmation
    """
    from apps.monero.xmr.addresses import encode_addr
    from apps.monero.xmr.networks import net_version

    version = net_version(network_type, dst.is_subaddress, payment_id is not None)
    addr = encode_addr(
        version, dst.addr.spend_public_key, dst.addr.view_public_key, payment_id
    )

    text_addr = common.split_address(addr.decode())
    text_amount = common.format_amount(dst.amount)

    if not await common.naive_pagination(
        ctx,
        [ui.BOLD, text_amount, ui.MONO] + list(text_addr),
        "Confirm send",
        ui.ICON_SEND,
        ui.GREEN,
        4,
    ):
        raise wire.ActionCancelled


async def _require_confirm_payment_id(ctx, payment_id: bytes):
    if not await common.naive_pagination(
        ctx,
        [ui.MONO] + list(chunks(hexlify(payment_id).decode(), 16)),
        "Payment ID",
        ui.ICON_SEND,
        ui.GREEN,
    ):
        raise wire.ActionCancelled


async def _require_confirm_fee(ctx, fee):
    content = Text("Confirm fee", ui.ICON_SEND, ui.GREEN)
    content.bold(common.format_amount(fee))
    await require_hold_to_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def _require_confirm_unlock_time(ctx, unlock_time):
    content = Text("Confirm unlock time", ui.ICON_SEND, ui.GREEN)
    content.normal("Unlock time for this transaction is set to")
    content.bold(str(unlock_time))
    content.normal("Continue?")
    await require_confirm(ctx, content, ButtonRequestType.SignTx)


class TransactionStep(ui.Component):
    def __init__(self, state, info):
        super().__init__()
        self.state = state
        self.info = info

    def on_render(self):
        state = self.state
        info = self.info
        ui.header("Signing transaction", ui.ICON_SEND, ui.TITLE_GREY, ui.BG, ui.BLUE)
        p = 1000 * state.progress_cur // state.progress_total
        ui.display.loader(p, False, -4, ui.WHITE, ui.BG)
        ui.display.text_center(ui.WIDTH // 2, 210, info[0], ui.NORMAL, ui.FG, ui.BG)
        if len(info) > 1:
            ui.display.text_center(ui.WIDTH // 2, 235, info[1], ui.NORMAL, ui.FG, ui.BG)


class KeyImageSyncStep(ui.Component):
    def __init__(self, current, total_num):
        super().__init__()
        self.current = current
        self.total_num = total_num

    def on_render(self):
        current = self.current
        total_num = self.total_num
        ui.header("Syncing", ui.ICON_SEND, ui.TITLE_GREY, ui.BG, ui.BLUE)
        p = (1000 * (current + 1) // total_num) if total_num > 0 else 0
        ui.display.loader(p, False, 18, ui.WHITE, ui.BG)


class LiveRefreshStep(ui.Component):
    def __init__(self, current):
        super().__init__()
        self.current = current

    def on_render(self):
        current = self.current
        ui.header("Refreshing", ui.ICON_SEND, ui.TITLE_GREY, ui.BG, ui.BLUE)
        p = (1000 * current // 8) % 1000
        ui.display.loader(p, True, 18, ui.WHITE, ui.BG)
        ui.display.text_center(
            ui.WIDTH // 2, 145, "%d" % current, ui.NORMAL, ui.FG, ui.BG
        )


async def transaction_step(state: State, step: int, sub_step: Optional[int] = None):
    if step == 0:
        info = ["Signing..."]
    elif step == state.STEP_INP:
        info = ["Processing inputs", "%d/%d" % (sub_step + 1, state.input_count)]
    elif step == state.STEP_PERM:
        info = ["Sorting..."]
    elif step == state.STEP_VINI:
        info = ["Hashing inputs", "%d/%d" % (sub_step + 1, state.input_count)]
    elif step == state.STEP_ALL_IN:
        info = ["Processing..."]
    elif step == state.STEP_OUT:
        info = ["Processing outputs", "%d/%d" % (sub_step + 1, state.output_count)]
    elif step == state.STEP_ALL_OUT:
        info = ["Postprocessing..."]
    elif step == state.STEP_SIGN:
        info = ["Signing inputs", "%d/%d" % (sub_step + 1, state.input_count)]
    else:
        info = ["Processing..."]

    state.progress_cur += 1
    await Popup(TransactionStep(state, info))


async def keyimage_sync_step(ctx, current, total_num):
    if current is None:
        return
    await Popup(KeyImageSyncStep(current, total_num))


async def live_refresh_step(ctx, current):
    if current is None:
        return
    await Popup(LiveRefreshStep(current))


async def show_address(
    ctx, address: str, desc: str = "Confirm address", network: str = None
):
    from apps.common.confirm import confirm
    from trezor.messages import ButtonRequestType
    from trezor.ui.components.tt.button import ButtonDefault
    from trezor.ui.components.tt.scroll import Paginated

    pages = []
    for lines in common.paginate_lines(common.split_address(address), 5):
        text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
        if network is not None:
            text.normal("%s network" % network)
        text.mono(*lines)
        pages.append(text)

    return await confirm(
        ctx,
        Paginated(pages),
        code=ButtonRequestType.Address,
        cancel="QR",
        cancel_style=ButtonDefault,
    )
