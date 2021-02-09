from micropython import const
from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.button import ButtonDefault
from trezor.ui.container import Container
from trezor.ui.qr import Qr
from trezor.ui.scroll import Paginated
from trezor.ui.text import TEXT_MAX_LINES, Span, Text, calculate_text_pages
from trezor.utils import chunks

from apps.common import HARDENED
from apps.common.confirm import confirm, require_confirm

if False:
    from typing import Iterable, Iterator, List, Union
    from trezor import wire


async def show_address(
    ctx: wire.Context,
    address: str,
    desc: str = "Confirm address",
    cancel: str = "QR",
    network: str = None,
) -> bool:
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
    if network is not None:
        text.normal("%s network" % network)
    text.mono(*split_address(address))

    return await confirm(
        ctx,
        text,
        code=ButtonRequestType.Address,
        cancel=cancel,
        cancel_style=ButtonDefault,
    )


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


async def show_pubkey(ctx: wire.Context, pubkey: bytes) -> None:
    lines = chunks(hexlify(pubkey).decode(), 18)
    text = Text("Confirm public key", ui.ICON_RECEIVE, ui.GREEN)
    text.mono(*lines)
    await require_confirm(ctx, text, ButtonRequestType.PublicKey)


async def show_xpub(ctx: wire.Context, xpub: str, desc: str, cancel: str) -> bool:
    pages: List[ui.Component] = []
    for lines in chunks(list(chunks(xpub, 16)), 5):
        text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
        text.mono(*lines)
        pages.append(text)

    return await confirm(
        ctx,
        Paginated(pages),
        code=ButtonRequestType.PublicKey,
        cancel=cancel,
        cancel_style=ButtonDefault,
    )


def split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)


def address_n_to_str(address_n: list) -> str:
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
   
    page_breaks = calculate_text_pages(
        items=items,
        new_lines=False,
        break_words=break_words,
        line_width=204,
    )

    if len(page_breaks) == 1:
        text = Text(
            header,
            header_icon=header_icon,
            icon_color=icon_color,
            break_words=break_words,
            new_lines=False,
            line_width=204,
            render_page_overflow=False,
        )
        text.content = items
        return text

    else:
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
