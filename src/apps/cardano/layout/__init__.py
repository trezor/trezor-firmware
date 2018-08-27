from micropython import const

from trezor import ui
from trezor.messages import ButtonRequestType, MessageType
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.confirm import CONFIRMED, ConfirmDialog
from trezor.ui.scroll import Scrollpage, animate_swipe, paginate
from trezor.ui.text import Text
from trezor.utils import chunks


async def confirm_with_pagination(
    ctx, content, title: str, icon=ui.ICON_RESET, icon_color=ui.ORANGE
):
    first_page = const(0)
    lines_per_page = const(4)

    if isinstance(content, (list, tuple)):
        lines = content
    else:
        lines = list(chunks(content, 17))
    pages = list(chunks(lines, lines_per_page))

    await ctx.call(ButtonRequest(code=ButtonRequestType.Other), MessageType.ButtonAck)

    paginator = paginate(
        show_text_page, len(pages), first_page, pages, title, icon, icon_color
    )
    return await ctx.wait(paginator) == CONFIRMED


@ui.layout
async def show_text_page(
    page: int,
    page_count: int,
    pages: list,
    title: str,
    icon=ui.ICON_RESET,
    icon_color=ui.ORANGE,
):
    if page_count == 1:
        page = 0

    lines = pages[page]
    content = Text(title, icon, icon_color=icon_color)
    content.mono(*lines)

    content = Scrollpage(content, page, page_count)

    if page + 1 >= page_count:
        return await ConfirmDialog(content)
    else:
        content.render()
        await animate_swipe()
