from micropython import const
from ubinascii import hexlify

from trezor import ui, wire
from trezor.enums import ButtonRequestType
from trezor.ui.container import Container
from trezor.ui.loader import LoaderDanger
from trezor.ui.popup import Popup
from trezor.ui.qr import Qr
from trezor.utils import chunks, chunks_intersperse

from ...components.common import break_path_to_lines
from ...components.common.confirm import (
    CONFIRMED,
    GO_BACK,
    SHOW_PAGINATED,
    is_confirmed,
    raise_if_cancelled,
)
from ...components.tt import passphrase, pin
from ...components.tt.button import ButtonCancel, ButtonDefault
from ...components.tt.confirm import Confirm, HoldToConfirm
from ...components.tt.scroll import (
    PAGEBREAK,
    AskPaginated,
    Paginated,
    paginate_paragraphs,
    paginate_text,
)
from ...components.tt.text import LINE_WIDTH_PAGINATED, Span, Text
from ...constants.tt import (
    MONO_ADDR_PER_LINE,
    MONO_HEX_PER_LINE,
    QR_SIZE_THRESHOLD,
    QR_X,
    QR_Y,
    TEXT_MAX_LINES,
)
from ..common import button_request, interact

if False:
    from typing import Awaitable, Iterable, Iterator, NoReturn, Sequence

    from ..common import PropertyType, ExceptionType


__all__ = (
    "confirm_action",
    "confirm_address",
    "confirm_text",
    "confirm_amount",
    "confirm_reset_device",
    "confirm_backup",
    "confirm_path_warning",
    "confirm_sign_identity",
    "confirm_signverify",
    "show_address",
    "show_error_and_raise",
    "show_pubkey",
    "show_success",
    "show_xpub",
    "show_warning",
    "confirm_output",
    "confirm_blob",
    "confirm_properties",
    "confirm_total",
    "confirm_joint_total",
    "confirm_metadata",
    "confirm_replacement",
    "confirm_modify_output",
    "confirm_modify_fee",
    "confirm_coinjoin",
    "show_popup",
    "draw_simple_text",
    "request_passphrase_on_device",
    "request_pin_on_device",
    "should_show_more",
)


async def confirm_action(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    description_param_font: int = ui.BOLD,
    verb: str | bytes | None = Confirm.DEFAULT_CONFIRM,
    verb_cancel: str | bytes | None = Confirm.DEFAULT_CANCEL,
    hold: bool = False,
    hold_danger: bool = False,
    icon: str | None = None,  # TODO cleanup @ redesign
    icon_color: int | None = None,  # TODO cleanup @ redesign
    reverse: bool = False,  # TODO cleanup @ redesign
    larger_vspace: bool = False,  # TODO cleanup @ redesign
    exc: ExceptionType = wire.ActionCancelled,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    text = Text(
        title,
        icon if icon is not None else ui.ICON_DEFAULT,
        icon_color if icon_color is not None else ui.ORANGE_ICON,
        new_lines=False,
    )

    if reverse and description is not None:
        text.format_parametrized(
            description,
            description_param if description_param is not None else "",
            param_font=description_param_font,
        )
    elif action is not None:
        text.bold(action)

    if action is not None and description is not None:
        text.br()
        if larger_vspace:
            text.br_half()

    if reverse and action is not None:
        text.bold(action)
    elif description is not None:
        text.format_parametrized(
            description,
            description_param if description_param is not None else "",
            param_font=description_param_font,
        )

    cls = HoldToConfirm if hold else Confirm
    kwargs = {}
    if hold_danger:
        kwargs = {"loader_style": LoaderDanger, "confirm_style": ButtonCancel}
    await raise_if_cancelled(
        interact(
            ctx,
            cls(text, confirm=verb, cancel=verb_cancel, **kwargs),
            br_type,
            br_code,
        ),
        exc,
    )


async def confirm_reset_device(
    ctx: wire.GenericContext, prompt: str, recovery: bool = False
) -> None:
    if recovery:
        text = Text("Recovery mode", ui.ICON_RECOVERY, new_lines=False)
    else:
        text = Text("Create new wallet", ui.ICON_RESET, new_lines=False)
    text.bold(prompt)
    text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to ")
    text.bold("https://trezor.io/tos")
    await raise_if_cancelled(
        interact(
            ctx,
            Confirm(text, major_confirm=not recovery),
            "recover_device" if recovery else "setup_device",
            ButtonRequestType.ProtectCall
            if recovery
            else ButtonRequestType.ResetDevice,
        )
    )


# TODO cleanup @ redesign
async def confirm_backup(ctx: wire.GenericContext) -> bool:
    text1 = Text("Success", ui.ICON_CONFIRM, ui.GREEN, new_lines=False)
    text1.bold("New wallet created successfully!\n")
    text1.br_half()
    text1.normal("You should back up your new wallet right now.")

    text2 = Text("Warning", ui.ICON_WRONG, ui.RED, new_lines=False)
    text2.bold("Are you sure you want to skip the backup?\n")
    text2.br_half()
    text2.normal("You can back up your Trezor once, at any time.")

    if is_confirmed(
        await interact(
            ctx,
            Confirm(text1, cancel="Skip", confirm="Back up", major_confirm=True),
            "backup_device",
            ButtonRequestType.ResetDevice,
        )
    ):
        return True

    confirmed = is_confirmed(
        await interact(
            ctx,
            Confirm(text2, cancel="Skip", confirm="Back up", major_confirm=True),
            "backup_device",
            ButtonRequestType.ResetDevice,
        )
    )
    return confirmed


async def confirm_path_warning(
    ctx: wire.GenericContext, path: str, path_type: str = "Path"
) -> None:
    text = Text("Confirm path", ui.ICON_WRONG, ui.RED)
    text.normal(path_type)
    text.mono(*break_path_to_lines(path, MONO_ADDR_PER_LINE))
    text.normal("is unknown.", "Are you sure?")
    await raise_if_cancelled(
        interact(
            ctx,
            Confirm(text),
            "path_warning",
            ButtonRequestType.UnknownDerivationPath,
        )
    )


def _show_qr(
    address: str,
    title: str,
    cancel: str = "Address",
) -> Confirm:
    QR_COEF = const(4) if len(address) < QR_SIZE_THRESHOLD else const(3)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)
    text = Text(title, ui.ICON_RECEIVE, ui.GREEN)

    return Confirm(Container(qr, text), cancel=cancel, cancel_style=ButtonDefault)


def _truncate_hex(
    hex_data: str,
    lines: int = TEXT_MAX_LINES,
    width: int = MONO_HEX_PER_LINE,
    middle: bool = False,
    ellipsis: str = "...",  # TODO: cleanup @ redesign
) -> Iterator[str]:
    ell_len = len(ellipsis)
    if len(hex_data) > width * lines:
        if middle:
            hex_data = (
                hex_data[: lines * width // 2 - (ell_len // 2)]
                + ellipsis
                + hex_data[-lines * width // 2 + (ell_len - ell_len // 2) :]
            )
        else:
            hex_data = hex_data[: (width * lines - ell_len)] + ellipsis
    return chunks_intersperse(hex_data, width)


def _show_address(
    address: str,
    title: str,
    network: str | None = None,
    extra: str | None = None,
) -> ui.Layout:
    para = [(ui.NORMAL, f"{network} network")] if network is not None else []
    if extra is not None:
        para.append((ui.BOLD, extra))
    para.extend(
        (ui.MONO, address_line) for address_line in chunks(address, MONO_ADDR_PER_LINE)
    )
    return paginate_paragraphs(
        para,
        header=title,
        header_icon=ui.ICON_RECEIVE,
        icon_color=ui.GREEN,
        confirm=lambda content: Confirm(
            content, cancel="QR", cancel_style=ButtonDefault
        ),
    )


def _show_xpub(xpub: str, title: str, cancel: str) -> Paginated:
    pages: list[ui.Component] = []
    for lines in chunks(list(chunks_intersperse(xpub, 16)), TEXT_MAX_LINES * 2):
        text = Text(title, ui.ICON_RECEIVE, ui.GREEN, new_lines=False)
        text.mono(*lines)
        pages.append(text)

    content = Paginated(pages)

    content.pages[-1] = Confirm(
        content.pages[-1],
        cancel=cancel,
        cancel_style=ButtonDefault,
    )

    return content


async def show_xpub(
    ctx: wire.GenericContext, xpub: str, title: str, cancel: str
) -> None:
    await raise_if_cancelled(
        interact(
            ctx,
            _show_xpub(xpub, title, cancel),
            "show_xpub",
            ButtonRequestType.PublicKey,
        )
    )


async def show_address(
    ctx: wire.GenericContext,
    address: str,
    address_qr: str | None = None,
    title: str = "Confirm address",
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
    address_extra: str | None = None,
    title_qr: str | None = None,
) -> None:
    is_multisig = len(xpubs) > 0
    while True:
        if is_confirmed(
            await interact(
                ctx,
                _show_address(
                    address,
                    title,
                    network,
                    extra=address_extra,
                ),
                "show_address",
                ButtonRequestType.Address,
            )
        ):
            break
        if is_confirmed(
            await interact(
                ctx,
                _show_qr(
                    address if address_qr is None else address_qr,
                    title if title_qr is None else title_qr,
                    cancel="XPUBs" if is_multisig else "Address",
                ),
                "show_qr",
                ButtonRequestType.Address,
            )
        ):
            break

        if is_multisig:
            for i, xpub in enumerate(xpubs):
                cancel = "Next" if i < len(xpubs) - 1 else "Address"
                title_xpub = f"XPUB #{i + 1}"
                title_xpub += " (yours)" if i == multisig_index else " (cosigner)"
                if is_confirmed(
                    await interact(
                        ctx,
                        _show_xpub(xpub, title=title_xpub, cancel=cancel),
                        "show_xpub",
                        ButtonRequestType.PublicKey,
                    )
                ):
                    return


def show_pubkey(
    ctx: wire.Context, pubkey: str, title: str = "Confirm public key"
) -> Awaitable[None]:
    return confirm_blob(
        ctx,
        br_type="show_pubkey",
        title="Confirm public key",
        data=pubkey,
        br_code=ButtonRequestType.PublicKey,
        icon=ui.ICON_RECEIVE,
    )


async def _show_modal(
    ctx: wire.GenericContext,
    br_type: str,
    br_code: ButtonRequestType,
    header: str,
    subheader: str | None,
    content: str,
    button_confirm: str | None,
    button_cancel: str | None,
    icon: str,
    icon_color: int,
    exc: ExceptionType = wire.ActionCancelled,
) -> None:
    text = Text(header, icon, icon_color, new_lines=False)
    if subheader:
        text.bold(subheader)
        text.br()
        text.br_half()
    text.normal(content)
    await raise_if_cancelled(
        interact(
            ctx,
            Confirm(text, confirm=button_confirm, cancel=button_cancel),
            br_type,
            br_code,
        ),
        exc,
    )


async def show_error_and_raise(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    header: str = "Error",
    subheader: str | None = None,
    button: str = "Close",
    red: bool = False,
    exc: ExceptionType = wire.ActionCancelled,
) -> NoReturn:
    await _show_modal(
        ctx,
        br_type=br_type,
        br_code=ButtonRequestType.Other,
        header=header,
        subheader=subheader,
        content=content,
        button_confirm=None,
        button_cancel=button,
        icon=ui.ICON_WRONG,
        icon_color=ui.RED if red else ui.ORANGE_ICON,
        exc=exc,
    )
    raise exc


def show_warning(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    header: str = "Warning",
    subheader: str | None = None,
    button: str = "Try again",
    br_code: ButtonRequestType = ButtonRequestType.Warning,
    icon: str = ui.ICON_WRONG,
    icon_color: int = ui.RED,
) -> Awaitable[None]:
    return _show_modal(
        ctx,
        br_type=br_type,
        br_code=br_code,
        header=header,
        subheader=subheader,
        content=content,
        button_confirm=button,
        button_cancel=None,
        icon=icon,
        icon_color=icon_color,
    )


def show_success(
    ctx: wire.GenericContext,
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "Continue",
) -> Awaitable[None]:
    return _show_modal(
        ctx,
        br_type=br_type,
        br_code=ButtonRequestType.Success,
        header="Success",
        subheader=subheader,
        content=content,
        button_confirm=button,
        button_cancel=None,
        icon=ui.ICON_CONFIRM,
        icon_color=ui.GREEN,
    )


async def confirm_output(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
    font_amount: int = ui.NORMAL,  # TODO cleanup @ redesign
    title: str = "Confirm sending",
    subtitle: str | None = None,  # TODO cleanup @ redesign
    color_to: int = ui.FG,  # TODO cleanup @ redesign
    to_str: str = " to\n",  # TODO cleanup @ redesign
    to_paginated: bool = False,  # TODO cleanup @ redesign
    width: int = MONO_ADDR_PER_LINE,
    width_paginated: int = MONO_ADDR_PER_LINE - 1,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> None:
    header_lines = to_str.count("\n") + int(subtitle is not None)
    if len(address) > (TEXT_MAX_LINES - header_lines) * width:
        para = []
        if subtitle is not None:
            para.append((ui.NORMAL, subtitle))
        para.append((font_amount, amount))
        if to_paginated:
            para.append((ui.NORMAL, "to"))
        para.extend((ui.MONO, line) for line in chunks(address, width_paginated))
        content: ui.Layout = paginate_paragraphs(para, title, ui.ICON_SEND, ui.GREEN)
    else:
        text = Text(title, ui.ICON_SEND, ui.GREEN, new_lines=False)
        if subtitle is not None:
            text.normal(subtitle, "\n")
        text.content = [font_amount, amount, ui.NORMAL, color_to, to_str, ui.FG]
        text.mono(*chunks_intersperse(address, width))
        content = Confirm(text)

    await raise_if_cancelled(interact(ctx, content, "confirm_output", br_code))


async def should_show_more(
    ctx: wire.GenericContext,
    title: str,
    para: Iterable[tuple[int, str]],
    button_text: str = "Show all",
    br_type: str = "should_show_more",
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_DEFAULT,
    icon_color: int = ui.ORANGE_ICON,
) -> bool:
    """Return True if the user wants to show more (they click a special button)
    and False when the user wants to continue without showing details.

    Raises ActionCancelled if the user cancels.
    """
    page = Text(
        title,
        header_icon=icon,
        icon_color=icon_color,
        new_lines=False,
        max_lines=TEXT_MAX_LINES - 2,
    )
    for font, text in para:
        page.content.extend((font, text, "\n"))
    ask_dialog = Confirm(AskPaginated(page, button_text))

    result = await raise_if_cancelled(interact(ctx, ask_dialog, br_type, br_code))
    assert result in (SHOW_PAGINATED, CONFIRMED)

    return result is SHOW_PAGINATED


async def _confirm_ask_pagination(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    para: Iterable[tuple[int, str]],
    para_truncated: Iterable[tuple[int, str]],
    br_code: ButtonRequestType,
    icon: str,
    icon_color: int,
) -> None:
    paginated: ui.Layout | None = None
    while True:
        if not await should_show_more(
            ctx,
            title,
            para=para_truncated,
            br_type=br_type,
            br_code=br_code,
            icon=icon,
            icon_color=icon_color,
        ):
            return

        if paginated is None:
            paginated = paginate_paragraphs(
                para,
                header=None,
                back_button=True,
                confirm=lambda content: Confirm(
                    content, cancel=None, confirm="Close", confirm_style=ButtonDefault
                ),
            )
        result = await interact(ctx, paginated, br_type, br_code)
        assert result in (CONFIRMED, GO_BACK)

    assert False


async def confirm_blob(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    data: bytes | str,
    description: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
    ask_pagination: bool = False,
) -> None:
    """Confirm data blob.

    Applicable for public keys, signatures, hashes. In general, any kind of
    data that is not human-readable, and can be wrapped at any character.

    For addresses, use `confirm_address`.

    Displays in monospace font. Paginates automatically.
    If data is provided as bytes or bytearray, it is converted to hex.
    """
    if isinstance(data, (bytes, bytearray)):
        data_str = hexlify(data).decode()
    else:
        data_str = data

    span = Span()
    lines = 0
    if description is not None:
        span.reset(description, 0, ui.NORMAL)
        lines += span.count_lines()
    data_lines = (len(data_str) + MONO_HEX_PER_LINE - 1) // MONO_HEX_PER_LINE
    lines += data_lines

    if lines <= TEXT_MAX_LINES:
        text = Text(title, icon, icon_color, new_lines=False)
        if description is not None:
            text.normal(description)
            text.br()

        # special case:
        if len(data_str) % 16 == 0:
            # sanity checks:
            # (a) we must not exceed MONO_HEX_PER_LINE
            assert MONO_HEX_PER_LINE > 16
            # (b) we must not increase number of lines
            assert (len(data_str) // 16) <= data_lines
            # the above holds true for MONO_HEX_PER_LINE == 18 and TEXT_MAX_LINES == 5
            per_line = 16

        else:
            per_line = MONO_HEX_PER_LINE
        text.mono(ui.FG, *chunks_intersperse(data_str, per_line))
        content: ui.Layout = HoldToConfirm(text) if hold else Confirm(text)
        return await raise_if_cancelled(interact(ctx, content, br_type, br_code))

    elif ask_pagination:
        para = [(ui.MONO, line) for line in chunks(data_str, MONO_HEX_PER_LINE - 2)]

        para_truncated = []
        if description is not None:
            para_truncated.append((ui.NORMAL, description))
        para_truncated.extend(para[:TEXT_MAX_LINES])

        return await _confirm_ask_pagination(
            ctx, br_type, title, para, para_truncated, br_code, icon, icon_color
        )

    else:
        para = []
        if description is not None:
            para.append((ui.NORMAL, description))
        para.extend((ui.MONO, line) for line in chunks(data_str, MONO_HEX_PER_LINE - 2))

        paginated = paginate_paragraphs(
            para, title, icon, icon_color, confirm=HoldToConfirm if hold else Confirm
        )
        return await raise_if_cancelled(interact(ctx, paginated, br_type, br_code))


def confirm_address(
    ctx: wire.GenericContext,
    title: str,
    address: str,
    description: str | None = "Address:",
    br_type: str = "confirm_address",
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
) -> Awaitable[None]:
    # TODO clarify API - this should be pretty limited to support mainly confirming
    # destinations and similar
    return confirm_blob(
        ctx,
        br_type=br_type,
        title=title,
        data=address,
        description=description,
        br_code=br_code,
        icon=icon,
        icon_color=icon_color,
    )


async def confirm_text(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
) -> None:
    """Confirm textual data.

    Applicable for human-readable strings, numbers, date/time values etc.

    For amounts, use `confirm_amount`.

    Displays in bold font. Paginates automatically.
    """
    span = Span()
    lines = 0
    if description is not None:
        span.reset(description, 0, ui.NORMAL)
        lines += span.count_lines()
    span.reset(data, 0, ui.BOLD)
    lines += span.count_lines()

    if lines <= TEXT_MAX_LINES:
        text = Text(title, icon, icon_color, new_lines=False)
        if description is not None:
            text.normal(description)
            text.br()
        text.bold(data)
        content: ui.Layout = Confirm(text)

    else:
        para = []
        if description is not None:
            para.append((ui.NORMAL, description))
        para.append((ui.BOLD, data))
        content = paginate_paragraphs(para, title, icon, icon_color)
    await raise_if_cancelled(interact(ctx, content, br_type, br_code))


def confirm_amount(
    ctx: wire.GenericContext,
    title: str,
    amount: str,
    description: str = "Amount:",
    br_type: str = "confirm_amount",
    br_code: ButtonRequestType = ButtonRequestType.Other,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
) -> Awaitable[None]:
    """Confirm amount."""
    # TODO clarify API - this should be pretty limited to support mainly confirming
    # destinations and similar
    return confirm_text(
        ctx,
        br_type=br_type,
        title=title,
        data=amount,
        description=description,
        br_code=br_code,
        icon=icon,
        icon_color=icon_color,
    )


_SCREEN_FULL_THRESHOLD = const(2)


# TODO keep name and value on the same page if possible
async def confirm_properties(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    props: Sequence[PropertyType],
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> None:
    span = Span()
    para = []
    used_lines = 0
    for key, val in props:
        span.reset(key or "", 0, ui.NORMAL, line_width=LINE_WIDTH_PAGINATED)
        key_lines = span.count_lines()

        if isinstance(val, str):
            span.reset(val, 0, ui.BOLD, line_width=LINE_WIDTH_PAGINATED)
            val_lines = span.count_lines()
        elif isinstance(val, bytes):
            val_lines = (len(val) * 2 + MONO_HEX_PER_LINE - 1) // MONO_HEX_PER_LINE
        else:
            val_lines = 0

        remaining_lines = TEXT_MAX_LINES - used_lines
        used_lines = (used_lines + key_lines + val_lines) % TEXT_MAX_LINES

        if key_lines + val_lines > remaining_lines:
            if remaining_lines <= _SCREEN_FULL_THRESHOLD:
                # there are only 2 remaining lines, don't try to fit and put everything
                # on next page
                para.append(PAGEBREAK)
                used_lines = (key_lines + val_lines) % TEXT_MAX_LINES

            elif val_lines > 0 and key_lines >= remaining_lines:
                # more than 2 remaining lines so try to fit something -- but won't fit
                # at least one line of value
                para.append(PAGEBREAK)
                used_lines = (key_lines + val_lines) % TEXT_MAX_LINES

            elif key_lines + val_lines <= TEXT_MAX_LINES:
                # Whole property won't fit to the page, but it will fit on a page
                # by itself
                para.append(PAGEBREAK)
                used_lines = (key_lines + val_lines) % TEXT_MAX_LINES

            # else:
            # None of the above. Continue fitting on the same page.

        if key:
            para.append((ui.NORMAL, key))
        if isinstance(val, bytes):
            para.extend(
                (ui.MONO, line)
                for line in chunks(hexlify(val).decode(), MONO_HEX_PER_LINE - 2)
            )
        elif isinstance(val, str):
            para.append((ui.BOLD, val))
    content = paginate_paragraphs(
        para, title, icon, icon_color, confirm=HoldToConfirm if hold else Confirm
    )
    await raise_if_cancelled(interact(ctx, content, br_type, br_code))


async def confirm_total(
    ctx: wire.GenericContext,
    total_amount: str,
    fee_amount: str,
    title: str = "Confirm transaction",
    total_label: str = "Total amount:\n",
    fee_label: str = "\nincluding fee:\n",
    icon_color: int = ui.GREEN,
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    text = Text(title, ui.ICON_SEND, icon_color, new_lines=False)
    text.normal(total_label)
    text.bold(total_amount)
    text.normal(fee_label)
    text.bold(fee_amount)
    await raise_if_cancelled(interact(ctx, HoldToConfirm(text), br_type, br_code))


async def confirm_joint_total(
    ctx: wire.GenericContext, spending_amount: str, total_amount: str
) -> None:
    text = Text("Joint transaction", ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.normal("You are contributing:\n")
    text.bold(spending_amount)
    text.normal("\nto the total amount:\n")
    text.bold(total_amount)
    await raise_if_cancelled(
        interact(
            ctx, HoldToConfirm(text), "confirm_joint_total", ButtonRequestType.SignTx
        )
    )


async def confirm_metadata(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    content: str,
    param: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    hide_continue: bool = False,
    hold: bool = False,
    param_font: int = ui.BOLD,
    icon: str = ui.ICON_SEND,  # TODO cleanup @ redesign
    icon_color: int = ui.GREEN,  # TODO cleanup @ redesign
    larger_vspace: bool = False,  # TODO cleanup @ redesign
) -> None:
    text = Text(title, icon, icon_color, new_lines=False)
    text.format_parametrized(
        content, param if param is not None else "", param_font=param_font
    )

    if not hide_continue:
        text.br()
        if larger_vspace:
            text.br_half()
        text.normal("Continue?")

    cls = HoldToConfirm if hold else Confirm

    await raise_if_cancelled(interact(ctx, cls(text), br_type, br_code))


async def confirm_replacement(
    ctx: wire.GenericContext, description: str, txid: str
) -> None:
    text = Text(description, ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.normal("Confirm transaction ID:\n")
    text.mono(*_truncate_hex(txid, TEXT_MAX_LINES - 1))
    await raise_if_cancelled(
        interact(ctx, Confirm(text), "confirm_replacement", ButtonRequestType.SignTx)
    )


async def confirm_modify_output(
    ctx: wire.GenericContext,
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    page1 = Text("Modify amount", ui.ICON_SEND, ui.GREEN, new_lines=False)
    page1.normal("Address:\n")
    page1.br_half()
    page1.mono(*chunks_intersperse(address, MONO_ADDR_PER_LINE))

    page2 = Text("Modify amount", ui.ICON_SEND, ui.GREEN, new_lines=False)
    if sign < 0:
        page2.normal("Decrease amount by:\n")
    else:
        page2.normal("Increase amount by:\n")
    page2.bold(amount_change)
    page2.br_half()
    page2.normal("\nNew amount:\n")
    page2.bold(amount_new)

    await raise_if_cancelled(
        interact(
            ctx,
            Paginated([page1, Confirm(page2)]),
            "modify_output",
            ButtonRequestType.ConfirmOutput,
        )
    )


async def confirm_modify_fee(
    ctx: wire.GenericContext,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
) -> None:
    text = Text("Modify fee", ui.ICON_SEND, ui.GREEN, new_lines=False)
    if sign == 0:
        text.normal("Your fee did not change.\n")
    else:
        if sign < 0:
            text.normal("Decrease your fee by:\n")
        else:
            text.normal("Increase your fee by:\n")
        text.bold(user_fee_change)
        text.br()
    text.br_half()
    text.normal("Transaction fee:\n")
    text.bold(total_fee_new)
    await raise_if_cancelled(
        interact(ctx, HoldToConfirm(text), "modify_fee", ButtonRequestType.SignTx)
    )


async def confirm_coinjoin(
    ctx: wire.GenericContext, fee_per_anonymity: str | None, total_fee: str
) -> None:
    text = Text("Authorize CoinJoin", ui.ICON_RECOVERY, new_lines=False)
    if fee_per_anonymity is not None:
        text.normal("Fee per anonymity set:\n")
        text.bold(f"{fee_per_anonymity} %\n")
    text.normal("Maximum total fees:\n")
    text.bold(total_fee)
    await raise_if_cancelled(
        interact(ctx, HoldToConfirm(text), "coinjoin_final", ButtonRequestType.Other)
    )


# TODO cleanup @ redesign
async def confirm_sign_identity(
    ctx: wire.GenericContext, proto: str, identity: str, challenge_visual: str | None
) -> None:
    text = Text(f"Sign {proto}", new_lines=False)
    if challenge_visual:
        text.normal(challenge_visual)
        text.br()
    text.mono(*chunks_intersperse(identity, 18))
    await raise_if_cancelled(
        interact(ctx, Confirm(text), "sign_identity", ButtonRequestType.Other)
    )


async def confirm_signverify(
    ctx: wire.GenericContext, coin: str, message: str, address: str, verify: bool
) -> None:
    if verify:
        header = f"Verify {coin} message"
        font = ui.MONO
        br_type = "verify_message"
    else:
        header = f"Sign {coin} message"
        font = ui.NORMAL
        br_type = "sign_message"

    text = Text(header, new_lines=False)
    text.bold("Confirm address:\n")
    text.mono(*chunks_intersperse(address, MONO_ADDR_PER_LINE))
    await raise_if_cancelled(
        interact(ctx, Confirm(text), br_type, ButtonRequestType.Other)
    )

    await raise_if_cancelled(
        interact(
            ctx,
            paginate_text(message, header, font=font),
            br_type,
            ButtonRequestType.Other,
        )
    )


async def show_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    timeout_ms: int = 3000,
) -> None:
    text = Text(title, ui.ICON_WRONG, ui.RED)
    if subtitle is not None:
        text.bold(subtitle)
        text.br_half()
    text.format_parametrized(description, description_param)
    await Popup(text, timeout_ms)


def draw_simple_text(title: str, description: str = "") -> None:
    text = Text(title, ui.ICON_CONFIG, new_lines=False)
    text.normal(description)
    ui.draw_simple(text)


async def request_passphrase_on_device(ctx: wire.GenericContext, max_len: int) -> str:
    await button_request(
        ctx, "passphrase_device", code=ButtonRequestType.PassphraseEntry
    )

    keyboard = passphrase.PassphraseKeyboard("Enter passphrase", max_len)
    result = await ctx.wait(keyboard)
    if result is passphrase.CANCELLED:
        raise wire.ActionCancelled("Passphrase entry cancelled")

    assert isinstance(result, str)
    return result


async def request_pin_on_device(
    ctx: wire.GenericContext,
    prompt: str,
    attempts_remaining: int | None,
    allow_cancel: bool,
) -> str:
    await button_request(ctx, "pin_device", code=ButtonRequestType.PinEntry)

    if attempts_remaining is None:
        subprompt = None
    elif attempts_remaining == 1:
        subprompt = "This is your last attempt"
    else:
        subprompt = f"{attempts_remaining} attempts remaining"

    dialog = pin.PinDialog(prompt, subprompt, allow_cancel)
    while True:
        result = await ctx.wait(dialog)
        if result is pin.CANCELLED:
            raise wire.PinCancelled
        assert isinstance(result, str)
        return result
