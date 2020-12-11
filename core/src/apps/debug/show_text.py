import trezor.messages.DebugLinkShowTextStyle as S
from trezor import ui, wire
from trezor.messages.DebugLinkShowText import DebugLinkShowText
from trezor.messages.Success import Success
from trezor.ui import style, text
from trezor.ui.components.tt.text import Text

from apps.common.confirm import confirm

STYLES = {
    S.NORMAL: ui.NORMAL,
    S.BOLD: ui.BOLD,
    S.MONO: ui.MONO,
    S.BR: text.BR,
    S.BR_HALF: text.BR_HALF,
}


async def show_text(ctx: wire.Context, msg: DebugLinkShowText) -> Success:
    if msg.header_icon is not None:
        icon_name = "ICON_" + msg.header_icon
        icon = getattr(style, icon_name)
        if not isinstance(icon, str):
            raise wire.DataError("Invalid icon name: {}".format(msg.header_icon))
    else:
        icon = style.ICON_DEFAULT

    if msg.icon_color is not None:
        color = getattr(style, msg.icon_color)
        if not isinstance(color, int):
            raise wire.DataError("Invalid color name: {}".format(msg.icon_color))
    else:
        color = style.ORANGE_ICON

    dlg = Text(msg.header_text, icon, color, new_lines=False)
    for item in msg.body_text:
        if item.style in STYLES:
            dlg.content.append(STYLES[item.style])
        elif item.style == S.SET_COLOR:
            color = getattr(style, item.content)
            if not isinstance(color, int):
                raise wire.DataError("Invalid color name: {}".format(item.content))
            dlg.content.append(color)

        elif item.content is not None:
            dlg.content.append(item.content)

    await confirm(ctx, dlg)
    return Success("text shown")
