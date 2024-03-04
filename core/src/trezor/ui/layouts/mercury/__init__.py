from typing import TYPE_CHECKING

import trezorui2
from trezor import TR, io, loop, ui
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled
from trezor.wire.context import wait as ctx_wait

from ..common import button_request, interact

if TYPE_CHECKING:
    from typing import Any, Awaitable, Iterable, NoReturn, Sequence, TypeVar

    from ..common import ExceptionType, PropertyType

    T = TypeVar("T")


BR_TYPE_OTHER = ButtonRequestType.Other  # global_import_cache

CONFIRMED = trezorui2.CONFIRMED
CANCELLED = trezorui2.CANCELLED
INFO = trezorui2.INFO


if __debug__:
    from trezor.utils import DISABLE_ANIMATION

    trezorui2.disable_animation(bool(DISABLE_ANIMATION))


class RustLayout(ui.Layout):
    BACKLIGHT_LEVEL = ui.style.BACKLIGHT_NORMAL

    # pylint: disable=super-init-not-called
    def __init__(self, layout: Any):
        self.layout = layout
        self.timer = loop.Timer()
        self.layout.attach_timer_fn(self.set_timer)

    def set_timer(self, token: int, deadline: int) -> None:
        self.timer.schedule(deadline, token)

    def request_complete_repaint(self) -> None:
        msg = self.layout.request_complete_repaint()
        assert msg is None

    def _paint(self) -> None:
        import storage.cache as storage_cache

        painted = self.layout.paint()

        ui.refresh()
        if storage_cache.homescreen_shown is not None and painted:
            storage_cache.homescreen_shown = None

    if __debug__:

        def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
            return (
                self.handle_timers(),
                self.handle_input_and_rendering(),
                self.handle_swipe(),
                self.handle_click_signal(),
                self.handle_result_signal(),
            )

        async def handle_result_signal(self) -> None:
            """Enables sending arbitrary input - ui.Result.

            Waits for `result_signal` and carries it out.
            """
            from storage import debug as debug_storage

            from apps.debug import result_signal

            while True:
                event_id, result = await result_signal()
                debug_storage.new_layout_event_id = event_id
                raise ui.Result(result)

        def read_content_into(self, content_store: list[str]) -> None:
            """Reads all the strings/tokens received from Rust into given list."""

            def callback(*args: Any) -> None:
                for arg in args:
                    content_store.append(str(arg))

            content_store.clear()
            self.layout.trace(callback)

        async def handle_swipe(self):
            from trezor.enums import DebugSwipeDirection

            from apps.debug import notify_layout_change, swipe_signal

            while True:
                event_id, direction = await swipe_signal()
                orig_x = orig_y = 120
                off_x, off_y = {
                    DebugSwipeDirection.UP: (0, -30),
                    DebugSwipeDirection.DOWN: (0, 30),
                    DebugSwipeDirection.LEFT: (-30, 0),
                    DebugSwipeDirection.RIGHT: (30, 0),
                }[direction]

                for event, x, y in (
                    (io.TOUCH_START, orig_x, orig_y),
                    (io.TOUCH_MOVE, orig_x + 1 * off_x, orig_y + 1 * off_y),
                    (io.TOUCH_END, orig_x + 2 * off_x, orig_y + 2 * off_y),
                ):
                    msg = self.layout.touch_event(event, x, y)
                    self._paint()
                    if msg is not None:
                        raise ui.Result(msg)

                notify_layout_change(self, event_id)

        async def _click(
            self,
            event_id: int | None,
            x: int,
            y: int,
            hold_ms: int | None,
        ) -> Any:
            from storage import debug as debug_storage
            from trezor import workflow

            from apps.debug import notify_layout_change

            self.layout.touch_event(io.TOUCH_START, x, y)
            self._paint()
            if hold_ms is not None:
                await loop.sleep(hold_ms)
            msg = self.layout.touch_event(io.TOUCH_END, x, y)

            if msg is not None:
                debug_storage.new_layout_event_id = event_id
                raise ui.Result(msg)

            # So that these presses will keep trezor awake
            # (it will not be locked after auto_lock_delay_ms)
            workflow.idle_timer.touch()

            self._paint()
            notify_layout_change(self, event_id)

        async def handle_click_signal(self) -> None:
            """Enables clicking somewhere on the screen.

            Waits for `click_signal` and carries it out.
            """
            from apps.debug import click_signal

            while True:
                event_id, x, y, hold_ms = await click_signal()
                await self._click(event_id, x, y, hold_ms)

    else:

        def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
            return self.handle_timers(), self.handle_input_and_rendering()

    def _first_paint(self) -> None:
        ui.backlight_fade(ui.style.BACKLIGHT_NONE)
        self._paint()

        if __debug__ and self.should_notify_layout_change:
            from storage import debug as debug_storage

            from apps.debug import notify_layout_change

            # notify about change and do not notify again until next await.
            # (handle_rendering might be called multiple times in a single await,
            # because of the endless loop in __iter__)
            self.should_notify_layout_change = False

            # Possibly there is an event ID that caused the layout change,
            # so notifying with this ID.
            event_id = None
            if debug_storage.new_layout_event_id is not None:
                event_id = debug_storage.new_layout_event_id
                debug_storage.new_layout_event_id = None

            notify_layout_change(self, event_id)

        # Turn the brightness on again.
        ui.backlight_fade(self.BACKLIGHT_LEVEL)

    def handle_input_and_rendering(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        from trezor import workflow

        touch = loop.wait(io.TOUCH)
        self._first_paint()
        while True:
            # Using `yield` instead of `await` to avoid allocations.
            event, x, y = yield touch
            workflow.idle_timer.touch()
            msg = None
            if event in (io.TOUCH_START, io.TOUCH_MOVE, io.TOUCH_END):
                msg = self.layout.touch_event(event, x, y)
            if msg is not None:
                raise ui.Result(msg)
            self._paint()

    def handle_timers(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        while True:
            # Using `yield` instead of `await` to avoid allocations.
            token = yield self.timer
            msg = self.layout.timer(token)
            if msg is not None:
                raise ui.Result(msg)
            self._paint()

    def page_count(self) -> int:
        return self.layout.page_count()


def draw_simple(layout: Any) -> None:
    # Simple drawing not supported for layouts that set timers.
    def dummy_set_timer(token: int, deadline: int) -> None:
        raise RuntimeError

    layout.attach_timer_fn(dummy_set_timer)
    ui.backlight_fade(ui.style.BACKLIGHT_DIM)
    layout.paint()
    ui.refresh()
    ui.backlight_fade(ui.style.BACKLIGHT_NORMAL)


async def raise_if_not_confirmed(a: Awaitable[T], exc: Any = ActionCancelled) -> T:
    result = await a
    if result is not CONFIRMED:
        raise exc
    return result


async def confirm_action(
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    hold_danger: bool = False,
    reverse: bool = False,
    exc: ExceptionType = ActionCancelled,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    if verb is not None:
        verb = verb.upper()
    if verb_cancel is not None:
        verb_cancel = verb_cancel.upper()

    if description is not None and description_param is not None:
        description = description.format(description_param)

    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_action(
                    title=title.upper(),
                    action=action,
                    description=description,
                    verb=verb,
                    verb_cancel=verb_cancel,
                    hold=hold,
                    hold_danger=hold_danger,
                    reverse=reverse,
                )
            ),
            br_type,
            br_code,
        ),
        exc,
    )


async def confirm_single(
    br_type: str,
    title: str,
    description: str,
    description_param: str | None = None,
    verb: str | None = None,
) -> None:
    if verb is not None:
        verb = verb.upper()
    description_param = description_param or ""

    # Placeholders are coming from translations in form of {0}
    template_str = "{0}"
    if template_str not in description:
        template_str = "{}"

    begin, _separator, end = description.partition(template_str)
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_emphasized(
                    title=title.upper(),
                    items=(begin, (True, description_param), end),
                    verb=verb,
                )
            ),
            br_type,
            ButtonRequestType.ProtectCall,
        )
    )


async def confirm_reset_device(title: str, recovery: bool = False) -> None:
    if recovery:
        button = TR.reset__button_recover
    else:
        button = TR.reset__button_create

    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_reset_device(
                    title=title.upper(),
                    button=button,
                )
            ),
            "recover_device" if recovery else "setup_device",
            (
                ButtonRequestType.ProtectCall
                if recovery
                else ButtonRequestType.ResetDevice
            ),
        )
    )


# TODO cleanup @ redesign
async def prompt_backup() -> bool:
    result = await interact(
        RustLayout(
            trezorui2.confirm_action(
                title=TR.words__title_success,
                action=TR.backup__new_wallet_successfully_created,
                description=TR.backup__it_should_be_backed_up,
                verb=TR.buttons__back_up,
                verb_cancel=TR.buttons__skip,
            )
        ),
        "backup_device",
        ButtonRequestType.ResetDevice,
    )
    if result is CONFIRMED:
        return True

    result = await interact(
        RustLayout(
            trezorui2.confirm_action(
                title=TR.words__warning.upper(),
                action=TR.backup__want_to_skip,
                description=TR.backup__can_back_up_anytime,
                verb=TR.buttons__back_up,
                verb_cancel=TR.buttons__skip,
            )
        ),
        "backup_device",
        ButtonRequestType.ResetDevice,
    )
    return result is CONFIRMED


async def confirm_path_warning(
    path: str,
    path_type: str | None = None,
) -> None:
    title = (
        TR.addr_mismatch__wrong_derivation_path
        if not path_type
        else f"{TR.words__unknown} {path_type.lower()}."
    )
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_warning(
                    title=title,
                    value=path,
                    description=TR.words__continue_anyway,
                    button=TR.buttons__continue,
                )
            ),
            "path_warning",
            br_code=ButtonRequestType.UnknownDerivationPath,
        )
    )


async def confirm_homescreen(
    image: bytes,
) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_homescreen(
                    title=TR.homescreen__title_set,
                    image=image,
                )
            ),
            "set_homesreen",
            ButtonRequestType.ProtectCall,
        )
    )


async def show_address(
    address: str,
    *,
    title: str | None = None,
    address_qr: str | None = None,
    case_sensitive: bool = True,
    path: str | None = None,
    account: str | None = None,
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
    mismatch_title: str | None = None,
    details_title: str | None = None,
    br_type: str = "show_address",
    br_code: ButtonRequestType = ButtonRequestType.Address,
    chunkify: bool = False,
) -> None:
    mismatch_title = mismatch_title or TR.addr_mismatch__mismatch  # def_arg
    send_button_request = True

    if title is None:
        title = TR.address__title_receive_address
        if multisig_index is not None:
            title = f"{title}\n(MULTISIG)"
        details_title = TR.send__title_receiving_to
    elif details_title is None:
        details_title = title

    layout = RustLayout(
        trezorui2.confirm_address(
            title=title,
            data=address,
            description=network or "",
            extra=None,
            chunkify=chunkify,
        )
    )

    while True:
        if send_button_request:
            send_button_request = False
            await button_request(
                br_type,
                br_code,
                pages=layout.page_count(),
            )
        layout.request_complete_repaint()
        result = await ctx_wait(layout)

        # User pressed right button.
        if result is CONFIRMED:
            break

        # User pressed corner button or swiped left, go to address details.
        elif result is INFO:

            def xpub_title(i: int) -> str:
                result = f"MULTISIG XPUB #{i + 1}\n"
                result += (
                    f"({TR.address__title_yours})"
                    if i == multisig_index
                    else f"({TR.address__title_cosigner})"
                )
                return result

            result = await ctx_wait(
                RustLayout(
                    trezorui2.show_address_details(
                        qr_title=title,
                        address=address if address_qr is None else address_qr,
                        case_sensitive=case_sensitive,
                        details_title=details_title,
                        account=account,
                        path=path,
                        xpubs=[(xpub_title(i), xpub) for i, xpub in enumerate(xpubs)],
                    )
                )
            )
            assert result is CANCELLED

        else:
            result = await ctx_wait(
                RustLayout(trezorui2.show_mismatch(title=mismatch_title))
            )
            assert result in (CONFIRMED, CANCELLED)
            # Right button aborts action, left goes back to showing address.
            if result is CONFIRMED:
                raise ActionCancelled


def show_pubkey(
    pubkey: str,
    title: str | None = None,
    *,
    account: str | None = None,
    path: str | None = None,
    mismatch_title: str | None = None,
    br_type: str = "show_pubkey",
) -> Awaitable[None]:
    title = title or TR.address__public_key  # def_arg
    mismatch_title = mismatch_title or TR.addr_mismatch__key_mismatch  # def_arg
    return show_address(
        address=pubkey,
        title=title.upper(),
        account=account,
        path=path,
        br_type=br_type,
        br_code=ButtonRequestType.PublicKey,
        mismatch_title=mismatch_title,
        chunkify=False,
    )


async def show_error_and_raise(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    exc: ExceptionType = ActionCancelled,
) -> NoReturn:
    button = button or TR.buttons__try_again  # def_arg
    await interact(
        RustLayout(
            trezorui2.show_error(
                title=subheader or "",
                description=content,
                button=button.upper(),
                allow_cancel=False,
            )
        ),
        br_type,
        BR_TYPE_OTHER,
    )
    raise exc


async def show_warning(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
    button = button or TR.buttons__continue  # def_arg
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_warning(
                    title=content,
                    description=subheader or "",
                    button=button.upper(),
                )
            ),
            br_type,
            br_code,
        )
    )


async def show_success(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
) -> None:
    button = button or TR.buttons__continue  # def_arg
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_success(
                    title=content,
                    description=subheader or "",
                    button=button.upper(),
                    allow_cancel=False,
                )
            ),
            br_type,
            ButtonRequestType.Success,
        )
    )


async def confirm_output(
    address: str,
    amount: str,
    title: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
    address_label: str | None = None,
    output_index: int | None = None,
    chunkify: bool = False,
) -> None:
    if title is not None:
        # TODO: handle translation
        if title.upper().startswith("CONFIRM "):
            title = title[len("CONFIRM ") :]
        amount_title = title
        recipient_title = title
    elif output_index is not None:
        amount_title = f"{TR.words__amount} #{output_index + 1}"
        recipient_title = f"{TR.words__recipient} #{output_index + 1}"
    else:
        amount_title = TR.send__confirm_sending
        recipient_title = TR.send__title_sending_to

    while True:
        result = await interact(
            RustLayout(
                trezorui2.confirm_value(
                    title=recipient_title.upper(),
                    subtitle=address_label,
                    description=None,
                    value=address,
                    verb=TR.buttons__continue,
                    hold=False,
                    info_button=False,
                    chunkify=chunkify,
                )
            ),
            "confirm_output",
            br_code,
        )
        if result is not CONFIRMED:
            raise ActionCancelled

        result = await interact(
            RustLayout(
                trezorui2.confirm_value(
                    title=amount_title.upper(),
                    subtitle=None,
                    description=None,
                    value=amount,
                    verb=None if hold else TR.buttons__confirm,
                    verb_cancel="^",
                    hold=hold,
                    info_button=False,
                )
            ),
            "confirm_output",
            br_code,
        )
        if result is CONFIRMED:
            return


async def confirm_payment_request(
    recipient_name: str,
    amount: str,
    memos: list[str],
) -> bool:
    result = await interact(
        RustLayout(
            trezorui2.confirm_with_info(
                title=TR.send__title_sending,
                items=[(ui.NORMAL, f"{amount} to\n{recipient_name}")]
                + [(ui.NORMAL, memo) for memo in memos],
                button=TR.buttons__confirm,
                info_button=TR.buttons__details,
            )
        ),
        "confirm_payment_request",
        ButtonRequestType.ConfirmOutput,
    )

    # When user pressed INFO, returning False, which gets processed in higher function
    # to differentiate it from CONFIRMED. Raising otherwise.
    if result is CONFIRMED:
        return True
    elif result is INFO:
        return False
    else:
        raise ActionCancelled


async def should_show_more(
    title: str,
    para: Iterable[tuple[int, str]],
    button_text: str | None = None,
    br_type: str = "should_show_more",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    confirm: str | bytes | None = None,
) -> bool:
    """Return True if the user wants to show more (they click a special button)
    and False when the user wants to continue without showing details.

    Raises ActionCancelled if the user cancels.
    """
    button_text = button_text or TR.buttons__show_all  # def_arg
    if confirm is None or not isinstance(confirm, str):
        confirm = TR.buttons__confirm

    result = await interact(
        RustLayout(
            trezorui2.confirm_with_info(
                title=title.upper(),
                items=para,
                button=confirm.upper(),
                info_button=button_text.upper(),
            )
        ),
        br_type,
        br_code,
    )

    if result is CONFIRMED:
        return False
    elif result is INFO:
        return True
    else:
        assert result is CANCELLED
        raise ActionCancelled


async def _confirm_ask_pagination(
    br_type: str,
    title: str,
    data: bytes | str,
    description: str,
    br_code: ButtonRequestType,
) -> None:
    paginated: ui.Layout | None = None
    # TODO: make should_show_more/confirm_more accept bytes directly
    if isinstance(data, bytes):
        from ubinascii import hexlify

        data = hexlify(data).decode()
    while True:
        if not await should_show_more(
            title,
            para=[(ui.NORMAL, description), (ui.MONO, data)],
            br_type=br_type,
            br_code=br_code,
        ):
            return

        if paginated is None:
            paginated = RustLayout(
                trezorui2.confirm_more(
                    title=title,
                    button=TR.buttons__close,
                    items=[(ui.MONO, data)],
                )
            )
        else:
            paginated.request_complete_repaint()

        result = await interact(paginated, br_type, br_code)
        assert result in (CONFIRMED, CANCELLED)

    assert False


async def confirm_blob(
    br_type: str,
    title: str,
    data: bytes | str,
    description: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    ask_pagination: bool = False,
    chunkify: bool = False,
) -> None:
    verb = verb or TR.buttons__confirm  # def_arg
    title = title.upper()
    layout = RustLayout(
        trezorui2.confirm_blob(
            title=title,
            description=description,
            data=data,
            extra=None,
            hold=hold,
            verb=verb,
            verb_cancel=verb_cancel,
            chunkify=chunkify,
        )
    )

    if ask_pagination and layout.page_count() > 1:
        assert not hold
        await _confirm_ask_pagination(br_type, title, data, description or "", br_code)

    else:
        await raise_if_not_confirmed(
            interact(
                layout,
                br_type,
                br_code,
            )
        )


async def confirm_address(
    title: str,
    address: str,
    description: str | None = None,
    br_type: str = "confirm_address",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    return await confirm_value(
        title,
        address,
        description or "",
        br_type,
        br_code,
        verb=TR.buttons__confirm,
    )


async def confirm_text(
    br_type: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    return await confirm_value(
        title,
        data,
        description or "",
        br_type,
        br_code,
        verb=TR.buttons__confirm,
    )


def confirm_amount(
    title: str,
    amount: str,
    description: str | None = None,
    br_type: str = "confirm_amount",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    description = description or f"{TR.words__amount}:"  # def_arg
    return confirm_value(
        title,
        amount,
        description,
        br_type,
        br_code,
        verb=TR.buttons__confirm,
    )


def confirm_value(
    title: str,
    value: str,
    description: str,
    br_type: str,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    *,
    verb: str | None = None,
    subtitle: str | None = None,
    hold: bool = False,
    value_text_mono: bool = True,
    info_items: Iterable[tuple[str, str]] | None = None,
    info_title: str | None = None,
    chunkify_info: bool = False,
) -> Awaitable[None]:
    """General confirmation dialog, used by many other confirm_* functions."""

    if not verb and not hold:
        raise ValueError("Either verb or hold=True must be set")

    if verb:
        verb = verb.upper()

    info_items = info_items or []
    info_layout = RustLayout(
        trezorui2.show_info_with_cancel(
            title=info_title if info_title else TR.words__title_information,
            items=info_items,
            chunkify=chunkify_info,
        )
    )

    return raise_if_not_confirmed(
        with_info(
            RustLayout(
                trezorui2.confirm_value(
                    title=title.upper(),
                    subtitle=subtitle,
                    description=description,
                    value=value,
                    verb=verb,
                    hold=hold,
                    info_button=bool(info_items),
                    text_mono=value_text_mono,
                )
            ),
            info_layout,
            br_type,
            br_code,
        )
    )


async def confirm_properties(
    br_type: str,
    title: str,
    props: Iterable[PropertyType],
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> None:
    # Monospace flag for values that are bytes.
    items = [(prop[0], prop[1], isinstance(prop[1], bytes)) for prop in props]

    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_properties(
                    title=title.upper(),
                    items=items,
                    hold=hold,
                )
            ),
            br_type,
            br_code,
        )
    )


async def confirm_total(
    total_amount: str,
    fee_amount: str,
    title: str | None = None,
    total_label: str | None = None,
    fee_label: str | None = None,
    account_label: str | None = None,
    fee_rate_amount: str | None = None,
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    title = title or TR.words__title_summary  # def_arg
    total_label = total_label or TR.send__total_amount  # def_arg
    fee_label = fee_label or TR.send__including_fee  # def_arg

    items = [
        (total_label, total_amount),
        (fee_label, fee_amount),
    ]
    info_items = []
    if account_label:
        info_items.append((TR.confirm_total__sending_from_account, account_label))
    if fee_rate_amount:
        info_items.append((TR.confirm_total__fee_rate, fee_rate_amount))

    await confirm_summary(
        items,
        TR.words__title_summary,
        info_items=info_items,
        br_type=br_type,
        br_code=br_code,
    )


async def confirm_summary(
    items: Iterable[tuple[str, str]],
    title: str | None = None,
    info_items: Iterable[tuple[str, str]] | None = None,
    info_title: str | None = None,
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    title = title or TR.words__title_summary  # def_arg

    total_layout = RustLayout(
        trezorui2.confirm_total(
            title=title.upper(),
            items=items,
            info_button=bool(info_items),
        )
    )
    info_items = info_items or []
    info_layout = RustLayout(
        trezorui2.show_info_with_cancel(
            title=info_title.upper() if info_title else TR.words__title_information,
            items=info_items,
        )
    )
    await raise_if_not_confirmed(with_info(total_layout, info_layout, br_type, br_code))


async def confirm_ethereum_tx(
    recipient: str,
    total_amount: str,
    maximum_fee: str,
    items: Iterable[tuple[str, str]],
    br_type: str = "confirm_ethereum_tx",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    chunkify: bool = False,
) -> None:
    total_layout = RustLayout(
        trezorui2.confirm_total(
            title=TR.words__title_summary,
            items=[
                (f"{TR.words__amount}:", total_amount),
                (TR.send__maximum_fee, maximum_fee),
            ],
            info_button=True,
            cancel_arrow=True,
        )
    )
    info_layout = RustLayout(
        trezorui2.show_info_with_cancel(
            title=TR.confirm_total__title_fee,
            items=items,
        )
    )

    while True:
        # Allowing going back and forth between recipient and summary/details
        await confirm_blob(
            br_type,
            TR.words__recipient.upper(),
            recipient,
            verb=TR.buttons__continue,
            chunkify=chunkify,
        )

        try:
            total_layout.request_complete_repaint()
            await raise_if_not_confirmed(
                with_info(total_layout, info_layout, br_type, br_code)
            )
            break
        except ActionCancelled:
            continue


async def confirm_ethereum_staking_tx(
    title: str,
    intro_question: str,
    verb: str,
    total_amount: str,
    maximum_fee: str,
    address: str,
    address_title: str,
    info_items: Iterable[tuple[str, str]],
    chunkify: bool = False,
    br_type: str = "confirm_ethereum_staking_tx",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:

    # intro
    await confirm_value(
        title,
        intro_question,
        "",
        br_type,
        br_code,
        verb=verb,
        value_text_mono=False,
        info_items=(("", address),),
        info_title=address_title,
        chunkify_info=chunkify,
    )

    # confirmation
    if verb == TR.ethereum__staking_claim:
        items = ((TR.send__maximum_fee, maximum_fee),)
    else:
        items = (
            (TR.words__amount + ":", total_amount),
            (TR.send__maximum_fee, maximum_fee),
        )
    await confirm_summary(
        items,  # items
        title=title,
        info_title=TR.confirm_total__title_fee,
        info_items=info_items,
        br_type=br_type,
        br_code=br_code,
    )


async def confirm_solana_tx(
    amount: str,
    fee: str,
    items: Iterable[tuple[str, str]],
    amount_title: str | None = None,
    fee_title: str | None = None,
    br_type: str = "confirm_solana_tx",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
):
    amount_title = (
        amount_title if amount_title is not None else f"{TR.words__amount}:"
    )  # def_arg
    fee_title = fee_title or TR.words__fee  # def_arg
    await confirm_summary(
        ((amount_title, amount), (fee_title, fee)),
        info_items=items,
        br_type=br_type,
        br_code=br_code,
    )


async def confirm_joint_total(spending_amount: str, total_amount: str) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_total(
                    title=TR.send__title_joint_transaction,
                    items=[
                        (TR.send__you_are_contributing, spending_amount),
                        (TR.send__to_the_total_amount, total_amount),
                    ],
                )
            ),
            "confirm_joint_total",
            ButtonRequestType.SignTx,
        )
    )


async def confirm_metadata(
    br_type: str,
    title: str,
    content: str,
    param: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    hold: bool = False,
    verb: str | None = None,
) -> None:
    verb = verb or TR.buttons__continue  # def_arg
    await confirm_action(
        br_type,
        title=title.upper(),
        action="",
        description=content,
        description_param=param,
        verb=verb.upper(),
        hold=hold,
        br_code=br_code,
    )


async def confirm_replacement(title: str, txid: str) -> None:
    await confirm_blob(
        "confirm_replacement",
        title.upper(),
        txid,
        TR.send__transaction_id,
        TR.buttons__continue,
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_modify_output(
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    address_layout = RustLayout(
        trezorui2.confirm_blob(
            title=TR.modify_amount__title,
            data=address,
            verb=TR.buttons__continue,
            verb_cancel=None,
            description=f"{TR.words__address}:",
            extra=None,
        )
    )
    modify_layout = RustLayout(
        trezorui2.confirm_modify_output(
            sign=sign,
            amount_change=amount_change,
            amount_new=amount_new,
        )
    )

    send_button_request = True
    while True:
        if send_button_request:
            await button_request(
                "modify_output",
                ButtonRequestType.ConfirmOutput,
                address_layout.page_count(),
            )
        address_layout.request_complete_repaint()
        await raise_if_not_confirmed(ctx_wait(address_layout))

        if send_button_request:
            send_button_request = False
            await button_request(
                "modify_output",
                ButtonRequestType.ConfirmOutput,
                modify_layout.page_count(),
            )
        modify_layout.request_complete_repaint()
        result = await ctx_wait(modify_layout)

        if result is CONFIRMED:
            break


async def with_info(
    main_layout: RustLayout,
    info_layout: RustLayout,
    br_type: str,
    br_code: ButtonRequestType,
) -> Any:
    await button_request(br_type, br_code, pages=main_layout.page_count())

    while True:
        result = await ctx_wait(main_layout)

        if result is INFO:
            info_layout.request_complete_repaint()
            result = await ctx_wait(info_layout)
            assert result is CANCELLED
            main_layout.request_complete_repaint()
            continue
        else:
            return result


async def confirm_modify_fee(
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None = None,
) -> None:
    fee_layout = RustLayout(
        trezorui2.confirm_modify_fee(
            title=title.upper(),
            sign=sign,
            user_fee_change=user_fee_change,
            total_fee_new=total_fee_new,
            fee_rate_amount=fee_rate_amount,
        )
    )
    items: list[tuple[str, str]] = []
    if fee_rate_amount:
        items.append((TR.bitcoin__new_fee_rate, fee_rate_amount))
    info_layout = RustLayout(
        trezorui2.show_info_with_cancel(
            title=TR.confirm_total__title_fee,
            items=items,
        )
    )
    await raise_if_not_confirmed(
        with_info(fee_layout, info_layout, "modify_fee", ButtonRequestType.SignTx)
    )


async def confirm_coinjoin(max_rounds: int, max_fee_per_vbyte: str) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_coinjoin(
                    max_rounds=str(max_rounds),
                    max_feerate=max_fee_per_vbyte,
                )
            ),
            "coinjoin_final",
            BR_TYPE_OTHER,
        )
    )


# TODO cleanup @ redesign
async def confirm_sign_identity(
    proto: str, identity: str, challenge_visual: str | None
) -> None:
    await confirm_blob(
        "sign_identity",
        f"{TR.words__sign} {proto}",
        identity,
        challenge_visual + "\n" if challenge_visual else "",
        br_code=BR_TYPE_OTHER,
    )


async def confirm_signverify(
    message: str,
    address: str,
    verify: bool,
    path: str | None = None,
    account: str | None = None,
    chunkify: bool = False,
) -> None:
    if verify:
        address_title = TR.sign_message__verify_address
        br_type = "verify_message"
    else:
        address_title = TR.sign_message__confirm_address
        br_type = "sign_message"

    address_layout = RustLayout(
        trezorui2.confirm_address(
            title=address_title,
            data=address,
            description="",
            verb=TR.buttons__continue,
            extra=None,
            chunkify=chunkify,
        )
    )

    items: list[tuple[str, str]] = []
    if account is not None:
        items.append((f"{TR.words__account}:", account))
    if path is not None:
        items.append((TR.address_details__derivation_path, path))
    items.append(
        (
            TR.sign_message__message_size,
            TR.sign_message__bytes_template.format(len(message)),
        )
    )

    info_layout = RustLayout(
        trezorui2.show_info_with_cancel(
            title=TR.words__title_information,
            items=items,
            horizontal=True,
        )
    )

    message_layout = RustLayout(
        trezorui2.confirm_blob(
            title=TR.sign_message__confirm_message,
            description=None,
            data=message,
            extra=None,
            hold=not verify,
            verb=TR.buttons__confirm if verify else None,
        )
    )

    while True:
        result = await with_info(
            address_layout, info_layout, br_type, br_code=BR_TYPE_OTHER
        )
        if result is not CONFIRMED:
            result = await ctx_wait(
                RustLayout(trezorui2.show_mismatch(title=TR.addr_mismatch__mismatch))
            )
            assert result in (CONFIRMED, CANCELLED)
            # Right button aborts action, left goes back to showing address.
            if result is CONFIRMED:
                raise ActionCancelled
            else:
                address_layout.request_complete_repaint()
                continue

        message_layout.request_complete_repaint()
        result = await interact(message_layout, br_type, BR_TYPE_OTHER)
        if result is CONFIRMED:
            break

        address_layout.request_complete_repaint()


async def show_error_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    *,
    button: str = "",
    timeout_ms: int = 0,
) -> None:
    if not button and not timeout_ms:
        raise ValueError("Either button or timeout_ms must be set")

    if subtitle:
        title += f"\n{subtitle}"
    await RustLayout(
        trezorui2.show_error(
            title=title,
            description=description.format(description_param),
            button=button,
            time_ms=timeout_ms,
            allow_cancel=False,
        )
    )


def request_passphrase_on_host() -> None:
    draw_simple(
        trezorui2.show_simple(
            title=None,
            description=TR.passphrase__please_enter,
        )
    )


def show_wait_text(message: str) -> None:
    draw_simple(trezorui2.show_wait_text(message))


async def request_passphrase_on_device(max_len: int) -> str:
    result = await interact(
        RustLayout(
            trezorui2.request_passphrase(
                prompt=TR.passphrase__title_enter, max_len=max_len
            )
        ),
        "passphrase_device",
        ButtonRequestType.PassphraseEntry,
    )
    if result is CANCELLED:
        raise ActionCancelled("Passphrase entry cancelled")

    assert isinstance(result, str)
    return result


async def request_pin_on_device(
    prompt: str,
    attempts_remaining: int | None,
    allow_cancel: bool,
    wrong_pin: bool = False,
) -> str:
    from trezor.wire import PinCancelled

    if attempts_remaining is None:
        subprompt = ""
    elif attempts_remaining == 1:
        subprompt = TR.pin__last_attempt
    else:
        subprompt = f"{attempts_remaining} {TR.pin__tries_left}"

    result = await interact(
        RustLayout(
            trezorui2.request_pin(
                prompt=prompt,
                subprompt=subprompt,
                allow_cancel=allow_cancel,
                wrong_pin=wrong_pin,
            )
        ),
        "pin_device",
        ButtonRequestType.PinEntry,
    )
    if result is CANCELLED:
        raise PinCancelled
    assert isinstance(result, str)
    return result


async def confirm_reenter_pin(
    is_wipe_code: bool = False,
) -> None:
    """Not supported for TT."""
    pass


async def pin_mismatch_popup(
    is_wipe_code: bool = False,
) -> None:
    await button_request("pin_mismatch", code=BR_TYPE_OTHER)
    title = TR.wipe_code__wipe_code_mismatch if is_wipe_code else TR.pin__pin_mismatch
    description = TR.wipe_code__mismatch if is_wipe_code else TR.pin__mismatch
    return await show_error_popup(
        title,
        description,
        button=TR.buttons__try_again,
    )


async def wipe_code_same_as_pin_popup() -> None:
    await button_request("wipe_code_same_as_pin", code=BR_TYPE_OTHER)
    return await show_error_popup(
        TR.wipe_code__invalid,
        TR.wipe_code__diff_from_pin,
        button=TR.buttons__try_again,
    )


async def confirm_set_new_pin(
    br_type: str,
    title: str,
    description: str,
    information: str,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_emphasized(
                    title=title.upper(),
                    items=(
                        (True, description + "\n\n"),
                        information,
                    ),
                    verb=TR.buttons__turn_on,
                )
            ),
            br_type,
            br_code,
        )
    )


async def confirm_firmware_update(description: str, fingerprint: str) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_firmware_update(
                    description=description, fingerprint=fingerprint
                )
            ),
            "firmware_update",
            BR_TYPE_OTHER,
        )
    )
