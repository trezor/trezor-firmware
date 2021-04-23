from micropython import const

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.components.tt.button import ButtonDefault
from trezor.ui.components.tt.text import Text
from trezor.ui.container import Container
from trezor.ui.qr import Qr
from trezor.ui.scroll import Paginated
from trezor.ui.text import TEXT_MAX_LINES, Span, Text, calculate_text_pages
from trezor.utils import chunks

from apps.common import HARDENED
from apps.common.confirm import confirm

if False:
    from typing import Iterable, Iterator
    from trezor import wire


async def show_qr(
    ctx: wire.Context,
    address: str,
    desc: str = "Confirm address",
    cancel: str = "Address",
) -> bool:
    QR_X = const(120)
    QR_Y = const(115)
    QR_SIZE_THRESHOLD = const(63)
    QR_COEF = const(4) if len(address) < QR_SIZE_THRESHOLD else const(3)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
    content = Container(qr, text)

    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel=cancel,
        cancel_style=ButtonDefault,
    )


def split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)


def address_n_to_str(address_n: Iterable[int]) -> str:
    def path_item(i: int) -> str:
        if i & HARDENED:
            return str(i ^ HARDENED) + "'"
        else:
            return str(i)

    if not address_n:
        return "m"

    return "m/" + "/".join([path_item(i) for i in address_n])


async def show_warning(
    ctx: wire.GenericContext,
    content: Iterable[str],
    subheader: Iterable[str] = [],
    button: str = "Try again",
) -> None:
    text = Text("Warning", ui.ICON_WRONG, ui.RED)
    if subheader:
        for row in subheader:
            text.bold(row)
        text.br_half()
    for row in content:
        text.normal(row)
    await require_confirm(
        ctx, text, ButtonRequestType.Warning, confirm=button, cancel=None
    )


async def show_success(
    ctx: wire.GenericContext,
    content: Iterable[str] = [],
    subheader: Iterable[str] = [],
    button: str = "Continue",
) -> None:
    text = Text("Success", ui.ICON_CONFIRM, ui.GREEN)
    if subheader:
        for row in subheader:
            text.bold(row)
        text.br_half()
    for row in content:
        text.normal(row)
    await require_confirm(
        ctx, text, ButtonRequestType.Success, confirm=button, cancel=None
    )


def paginate_text(
    text: str,
    header: str,
    font: int = ui.NORMAL,
    header_icon: str = ui.ICON_DEFAULT,
    icon_color: int = ui.ORANGE_ICON,
    break_words: bool = False,
) -> Union[Text, Paginated]:
    items = [font, text]

    # Try to fit the text into one page, with full width.
    page_breaks = calculate_text_pages(
        items=items,
        break_words=break_words,
        new_lines=False,
    )
    if len(page_breaks) == 1:
        # Text fits, return just one text component.
        text = Text(
            header,
            header_icon=header_icon,
            icon_color=icon_color,
            break_words=break_words,
            new_lines=False,
            render_page_overflow=False,
        )
        text.content = items
        return text
    else:
        # Text doesn't fit, we need to paginate it. We also need to leave space for
        # the pagination dots, so let's break it again with shorter `line_width`.
        page_breaks = calculate_text_pages(
            items=items,
            break_words=break_words,
            new_lines=False,
            line_width=204,
        )
        pages: List[ui.Component] = []
        for item_offset, char_offset in page_breaks:
            page = Text(
                header,
                header_icon=header_icon,
                icon_color=icon_color,
                break_words=break_words,
                new_lines=False,
                line_width=204,
                content_offset=item_offset,
                char_offset=char_offset,
                render_page_overflow=False,
            )
            page.content = items
            pages.append(page)
        return Paginated(pages)
