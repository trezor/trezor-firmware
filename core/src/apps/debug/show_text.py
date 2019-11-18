from trezor import ui, wire
from trezor.messages import DebugShowTextIcon
from trezor.messages.DebugShowText import DebugShowText
from trezor.messages.Success import Success
from trezor.ui.text import Text

from apps.common.confirm import require_confirm


async def show_text(ctx: wire.Context, msg: DebugShowText):
    icons = {
        DebugShowTextIcon.CONFIRM: ui.ICON_CONFIRM,
        DebugShowTextIcon.CONFIG: ui.ICON_CONFIG,
        DebugShowTextIcon.RESET: ui.ICON_RESET,
        DebugShowTextIcon.WIPE: ui.ICON_WIPE,
        DebugShowTextIcon.RECOVERY: ui.ICON_RECOVERY,
        DebugShowTextIcon.NOCOPY: ui.ICON_NOCOPY,
        DebugShowTextIcon.WRONG: ui.ICON_WRONG,
        DebugShowTextIcon.RECEIVE: ui.ICON_RECEIVE,
        DebugShowTextIcon.SEND: ui.ICON_SEND,
        DebugShowTextIcon.CANCEL: ui.ICON_CANCEL,
        DebugShowTextIcon.LOCK: ui.ICON_LOCK,
        DebugShowTextIcon.CLICK: ui.ICON_CLICK,
        DebugShowTextIcon.SWIPE: ui.ICON_SWIPE,
        DebugShowTextIcon.SWIPE_LEFT: ui.ICON_SWIPE_LEFT,
        DebugShowTextIcon.SWIPE_RIGHT: ui.ICON_SWIPE_RIGHT,
        DebugShowTextIcon.BACK: ui.ICON_BACK,
        DebugShowTextIcon.CHECK: ui.ICON_CHECK,
        DebugShowTextIcon.SPACE: ui.ICON_SPACE,
    }
    text = Text(msg.header_text, icons[msg.icon], ui.GREEN)
    text.bold(msg.body_text)
    await require_confirm(ctx, text)
    return Success(message="Text shown")
