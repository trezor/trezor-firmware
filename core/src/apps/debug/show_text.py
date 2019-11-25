from trezor import ui, wire
from trezor.messages import DebugLinkShowTextIcon
from trezor.messages.DebugLinkShowText import DebugLinkShowText
from trezor.messages.Success import Success
from trezor.ui.text import Text

from apps.common.confirm import require_confirm


async def show_text(ctx: wire.Context, msg: DebugLinkShowText):
    icons = {
        DebugLinkShowTextIcon.CONFIRM: ui.ICON_CONFIRM,
        DebugLinkShowTextIcon.CONFIG: ui.ICON_CONFIG,
        DebugLinkShowTextIcon.RESET: ui.ICON_RESET,
        DebugLinkShowTextIcon.WIPE: ui.ICON_WIPE,
        DebugLinkShowTextIcon.RECOVERY: ui.ICON_RECOVERY,
        DebugLinkShowTextIcon.NOCOPY: ui.ICON_NOCOPY,
        DebugLinkShowTextIcon.WRONG: ui.ICON_WRONG,
        DebugLinkShowTextIcon.RECEIVE: ui.ICON_RECEIVE,
        DebugLinkShowTextIcon.SEND: ui.ICON_SEND,
        DebugLinkShowTextIcon.CANCEL: ui.ICON_CANCEL,
        DebugLinkShowTextIcon.LOCK: ui.ICON_LOCK,
        DebugLinkShowTextIcon.CLICK: ui.ICON_CLICK,
        DebugLinkShowTextIcon.SWIPE: ui.ICON_SWIPE,
        DebugLinkShowTextIcon.SWIPE_LEFT: ui.ICON_SWIPE_LEFT,
        DebugLinkShowTextIcon.SWIPE_RIGHT: ui.ICON_SWIPE_RIGHT,
        DebugLinkShowTextIcon.BACK: ui.ICON_BACK,
        DebugLinkShowTextIcon.CHECK: ui.ICON_CHECK,
        DebugLinkShowTextIcon.SPACE: ui.ICON_SPACE,
    }
    text = Text(msg.header_text, icons[msg.icon], ui.GREEN)
    text.bold(msg.body_text)
    await require_confirm(ctx, text)
    return Success(message="Text shown")
