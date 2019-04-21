from ubinascii import hexlify

from trezor import ui, wire
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.monero.layout import common

DUMMY_PAYMENT_ID = b"\x00" * 8


async def require_confirm_watchkey(ctx):
    content = Text("Confirm export", ui.ICON_SEND, icon_color=ui.GREEN)
    content.normal("Do you really want to", "export watch-only", "credentials?")
    return await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_keyimage_sync(ctx):
    content = Text("Confirm ki sync", ui.ICON_SEND, icon_color=ui.GREEN)
    content.normal("Do you really want to", "sync key images?")
    return await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_live_refresh(ctx):
    content = Text("Confirm refresh", ui.ICON_SEND, icon_color=ui.GREEN)
    content.normal("Do you really want to", "start refresh?")
    return await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_tx_key(ctx, export_key=False):
    content = Text("Confirm export", ui.ICON_SEND, icon_color=ui.GREEN)
    txt = ["Do you really want to"]
    if export_key:
        txt.append("export tx_key?")
    else:
        txt.append("export tx_der")
        txt.append("for tx_proof?")

    content.normal(*txt)
    return await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_transaction(ctx, state, tsx_data, network_type):
    """
    Ask for confirmation from user.
    """
    from apps.monero.xmr.addresses import get_change_addr_idx

    outputs = tsx_data.outputs
    change_idx = get_change_addr_idx(outputs, tsx_data.change_dts)
    has_integrated = bool(tsx_data.integrated_indices)
    has_payment = bool(tsx_data.payment_id)

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


async def _require_confirm_output(ctx, dst, network_type, payment_id):
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
        raise wire.ActionCancelled("Cancelled")


async def _require_confirm_payment_id(ctx, payment_id):
    if not await common.naive_pagination(
        ctx,
        [ui.MONO] + list(chunks(hexlify((payment_id)), 16)),
        "Payment ID",
        ui.ICON_SEND,
        ui.GREEN,
    ):
        raise wire.ActionCancelled("Cancelled")


async def _require_confirm_fee(ctx, fee):
    content = Text("Confirm fee", ui.ICON_SEND, icon_color=ui.GREEN)
    content.bold(common.format_amount(fee))
    await require_hold_to_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


@ui.layout_no_slide
async def transaction_step(state, step, sub_step=None):
    info = []
    if step == 0:
        info = ["Signing..."]
    elif step == 100:
        info = ["Processing inputs", "%d/%d" % (sub_step + 1, state.input_count)]
    elif step == 200:
        info = ["Sorting..."]
    elif step == 300:
        info = ["Hashing inputs", "%d/%d" % (sub_step + 1, state.input_count)]
    elif step == 350:
        info = ["Processing..."]
    elif step == 400:
        info = ["Processing outputs", "%d/%d" % (sub_step + 1, state.output_count)]
    elif step == 500:
        info = ["Postprocessing..."]
    elif step == 600:
        info = ["Signing inputs", "%d/%d" % (sub_step + 1, state.input_count)]
    else:
        info = ["Processing..."]

    state.progress_cur += 1

    ui.display.clear()
    text = Text("Signing transaction", ui.ICON_SEND, icon_color=ui.BLUE)
    text.render()

    p = int(1000.0 * state.progress_cur / state.progress_total)
    ui.display.loader(p, -4, ui.WHITE, ui.BG)
    ui.display.text_center(ui.WIDTH // 2, 210, info[0], ui.NORMAL, ui.FG, ui.BG)
    if len(info) > 1:
        ui.display.text_center(ui.WIDTH // 2, 235, info[1], ui.NORMAL, ui.FG, ui.BG)
    ui.display.refresh()


@ui.layout_no_slide
async def keyimage_sync_step(ctx, current, total_num):
    if current is None:
        return
    ui.display.clear()
    text = Text("Syncing", ui.ICON_SEND, icon_color=ui.BLUE)
    text.render()

    p = (int(1000.0 * (current + 1) / total_num)) if total_num > 0 else 0
    ui.display.loader(p, 18, ui.WHITE, ui.BG)
    ui.display.refresh()


@ui.layout_no_slide
async def live_refresh_step(ctx, current):
    if current is None:
        return
    ui.display.clear()
    text = Text("Refreshing", ui.ICON_SEND, icon_color=ui.BLUE)
    text.normal("%d" % current)
    text.render()
