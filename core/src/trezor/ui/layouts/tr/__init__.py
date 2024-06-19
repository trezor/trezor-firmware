from typing import TYPE_CHECKING

import trezorui2
from trezor import TR, io, log, loop, ui, utils
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest
from trezor.wire import ActionCancelled, context

from ..common import button_request, interact

if TYPE_CHECKING:
    from typing import Any, Awaitable, Iterable, NoReturn, Sequence, TypeVar

    from ..common import ExceptionType, PropertyType

    T = TypeVar("T")

    LayoutParentType = ui.Layout[T]

else:
    LayoutParentType = [ui.Layout]
    T = 0


CONFIRMED = trezorui2.CONFIRMED
CANCELLED = trezorui2.CANCELLED
INFO = trezorui2.INFO

BR_TYPE_OTHER = ButtonRequestType.Other  # global_import_cache


if __debug__:
    from trezor.utils import DISABLE_ANIMATION

    trezorui2.disable_animation(bool(DISABLE_ANIMATION))


class RustLayout(LayoutParentType[T]):
    # pylint: disable=super-init-not-called
    def __init__(self, layout: trezorui2.LayoutObj[T]):
        self.br_chan = loop.chan()
        self.layout = layout
        self.timer = loop.Timer()
        self.layout.attach_timer_fn(self.set_timer, None)
        self._send_button_request()

    def __del__(self):
        self.layout.__del__()

    def set_timer(self, token: int, deadline: int) -> None:
        self.timer.schedule(deadline, token)

    def request_complete_repaint(self) -> None:
        msg = self.layout.request_complete_repaint()
        assert msg is None

    def _paint(self) -> None:
        import storage.cache as storage_cache

        painted = self.layout.paint()

        if painted:
            ui.refresh()
        if storage_cache.homescreen_shown is not None and painted:
            storage_cache.homescreen_shown = None

    if __debug__:
        from trezor.enums import DebugPhysicalButton

        def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
            if context.CURRENT_CONTEXT:
                return (
                    self.handle_input_and_rendering(),
                    self.handle_timers(),
                    self.handle_swipe_signal(),
                    self.handle_button_signal(),
                    self.handle_result_signal(),
                    self.handle_usb(context.get_context()),
                )
            else:
                return (
                    self.handle_input_and_rendering(),
                    self.handle_timers(),
                    self.handle_swipe_signal(),
                    self.handle_button_signal(),
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
                # Layout change will be notified in _first_paint of the next layout
                debug_storage.new_layout_event_id = event_id
                raise ui.Result(result)

        def read_content_into(self, content_store: list[str]) -> None:
            """Reads all the strings/tokens received from Rust into given list."""

            def callback(*args: Any) -> None:
                for arg in args:
                    content_store.append(str(arg))

            content_store.clear()
            self.layout.trace(callback)

        async def _press_left(self, hold_ms: int | None) -> Any:
            """Triggers left button press."""
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_LEFT)
            self._send_button_request()
            self._paint()
            if hold_ms is not None:
                await loop.sleep(hold_ms)
            r = self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_LEFT)
            self._send_button_request()
            return r

        async def _press_right(self, hold_ms: int | None) -> Any:
            """Triggers right button press."""
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_RIGHT)
            self._send_button_request()
            self._paint()
            if hold_ms is not None:
                await loop.sleep(hold_ms)
            r = self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_RIGHT)
            self._send_button_request()
            return r

        async def _press_middle(self, hold_ms: int | None) -> Any:
            """Triggers middle button press."""
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_LEFT)
            self._send_button_request()
            self._paint()
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_RIGHT)
            self._send_button_request()
            self._paint()
            if hold_ms is not None:
                await loop.sleep(hold_ms)
            self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_LEFT)
            self._send_button_request()
            self._paint()
            r = self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_RIGHT)
            self._send_button_request()
            return r

        async def _press_button(
            self,
            event_id: int | None,
            btn_to_press: DebugPhysicalButton,
            hold_ms: int | None,
        ) -> Any:
            from storage import debug as debug_storage
            from trezor import workflow
            from trezor.enums import DebugPhysicalButton

            from apps.debug import notify_layout_change

            if btn_to_press == DebugPhysicalButton.LEFT_BTN:
                msg = await self._press_left(hold_ms)
            elif btn_to_press == DebugPhysicalButton.MIDDLE_BTN:
                msg = await self._press_middle(hold_ms)
            elif btn_to_press == DebugPhysicalButton.RIGHT_BTN:
                msg = await self._press_right(hold_ms)
            else:
                raise Exception(f"Unknown button: {btn_to_press}")

            if msg is not None:
                # Layout change will be notified in _first_paint of the next layout
                debug_storage.new_layout_event_id = event_id
                raise ui.Result(msg)

            # So that these presses will keep trezor awake
            # (it will not be locked after auto_lock_delay_ms)
            workflow.idle_timer.touch()

            self._paint()
            notify_layout_change(self, event_id)

        async def _swipe(self, event_id: int | None, direction: int) -> None:
            """Triggers swipe in the given direction.

            Only `UP` and `DOWN` directions are supported.
            """
            from trezor.enums import DebugPhysicalButton, DebugSwipeDirection

            if direction == DebugSwipeDirection.UP:
                btn_to_press = DebugPhysicalButton.RIGHT_BTN
            elif direction == DebugSwipeDirection.DOWN:
                btn_to_press = DebugPhysicalButton.LEFT_BTN
            else:
                raise Exception(f"Unsupported direction: {direction}")

            await self._press_button(event_id, btn_to_press, None)

        async def handle_swipe_signal(self) -> None:
            """Enables pagination through the current page/flow page.

            Waits for `swipe_signal` and carries it out.
            """
            from apps.debug import swipe_signal

            while True:
                event_id, direction = await swipe_signal()
                await self._swipe(event_id, direction)

        async def handle_button_signal(self) -> None:
            """Enables clicking arbitrary of the three buttons.

            Waits for `button_signal` and carries it out.
            """
            from apps.debug import button_signal

            while True:
                event_id, btn, hold_ms = await button_signal()
                await self._press_button(event_id, btn, hold_ms)

    else:

        def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
            if context.CURRENT_CONTEXT:
                return (
                    self.handle_input_and_rendering(),
                    self.handle_timers(),
                    self.handle_usb(context.get_context()),
                )
            else:
                return (
                    self.handle_input_and_rendering(),
                    self.handle_timers(),
                )

    def _first_paint(self) -> None:
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

    def handle_input_and_rendering(self) -> loop.Task:
        from trezor import workflow

        button = loop.wait(io.BUTTON)
        self._first_paint()
        while True:
            # Using `yield` instead of `await` to avoid allocations.
            event, button_num = yield button
            workflow.idle_timer.touch()
            msg = None
            if event in (io.BUTTON_PRESSED, io.BUTTON_RELEASED):
                msg = self.layout.button_event(event, button_num)
                self._send_button_request()
            if msg is not None:
                raise ui.Result(msg)
            self._paint()

    def handle_timers(self) -> loop.Task:
        while True:
            # Using `yield` instead of `await` to avoid allocations.
            token = yield self.timer
            msg = self.layout.timer(token)
            self._send_button_request()
            if msg is not None:
                raise ui.Result(msg)
            self._paint()

    def page_count(self) -> int:
        """How many paginated pages current screen has."""
        return self.layout.page_count()

    async def handle_usb(self, ctx: context.Context):
        while True:
            br_code, br_type, page_count = await loop.race(
                ctx.read(()), self.br_chan.take()
            )
            log.debug(__name__, "ButtonRequest.type=%s", br_type)
            await ctx.call(ButtonRequest(code=br_code, pages=page_count), ButtonAck)

    def _send_button_request(self):
        res = self.layout.button_request()
        if res is not None:
            br_code, br_type = res
            self.br_chan.publish((br_code, br_type, self.layout.page_count()))


def draw_simple(layout: trezorui2.LayoutObj[Any]) -> None:
    # Simple drawing not supported for layouts that set timers.
    def dummy_set_timer(token: int, deadline: int) -> None:
        raise RuntimeError

    layout.attach_timer_fn(dummy_set_timer, None)
    layout.paint()
    ui.refresh()


# Temporary function, so we know where it is used
# Should be gradually replaced by custom designs/layouts
def _placeholder_confirm(
    br_type: str,
    title: str,
    data: str | None = None,
    description: str | None = None,
    *,
    verb: str | None = None,
    verb_cancel: str | None = "",
    hold: bool = False,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    verb = verb or TR.buttons__confirm  # def_arg
    return confirm_action(
        br_type,
        title,
        data,
        description,
        verb=verb,
        verb_cancel=verb_cancel,
        hold=hold,
        reverse=True,
        br_code=br_code,
    )


async def get_bool(
    br_type: str,
    title: str,
    data: str | None = None,
    description: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = "",
    hold: bool = False,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> bool:
    verb = verb or TR.buttons__confirm  # def_arg
    result = await interact(
        RustLayout(
            trezorui2.confirm_action(
                title=title,
                action=data,
                description=description,
                verb=verb,
                verb_cancel=verb_cancel,
                hold=hold,
            )
        ),
        br_type,
        br_code,
    )

    return result is CONFIRMED


async def raise_if_not_confirmed(
    a: Awaitable[ui.UiResult], exc: Any = ActionCancelled
) -> None:
    result = await a
    if result is not CONFIRMED:
        raise exc


def confirm_action(
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = "",
    hold: bool = False,
    hold_danger: bool = False,
    reverse: bool = False,
    exc: ExceptionType = ActionCancelled,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    prompt_screen: bool = False,
    prompt_title: str | None = None,
) -> Awaitable[None]:
    verb = verb or TR.buttons__confirm  # def_arg
    if description is not None and description_param is not None:
        description = description.format(description_param)

    return raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_action(
                    title=title,
                    action=action,
                    description=description,
                    subtitle=subtitle,
                    verb=verb,
                    verb_cancel=verb_cancel,
                    hold=hold,
                    reverse=reverse,
                )
            ),
            br_type,
            br_code,
        ),
        exc,
    )


def confirm_single(
    br_type: str,
    title: str,
    description: str,
    description_param: str | None = None,
    verb: str | None = None,
) -> Awaitable[None]:
    description_param = description_param or ""

    # Placeholders are coming from translations in form of {0}
    template_str = "{0}"
    if template_str not in description:
        template_str = "{}"

    begin, _separator, end = description.partition(template_str)
    return confirm_action(
        br_type,
        title,
        description=begin + description_param + end,
        verb=verb or TR.buttons__confirm,
        br_code=ButtonRequestType.ProtectCall,
    )


def confirm_reset_device(
    title: str,
    recovery: bool = False,
) -> Awaitable[None]:
    if recovery:
        button = TR.reset__button_recover
    else:
        button = TR.reset__button_create

    return raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_reset_device(
                    title=title,
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


async def show_wallet_created_success() -> None:
    # not shown on model R
    return None


async def prompt_backup() -> bool:
    br_type = "backup_device"
    br_code = ButtonRequestType.ResetDevice

    result = await interact(
        RustLayout(trezorui2.confirm_backup()),
        br_type,
        br_code,
    )
    if result is CONFIRMED:
        return True

    return await get_bool(
        br_type,
        TR.backup__title_skip,
        description=TR.backup__want_to_skip,
        verb=TR.buttons__back_up,
        verb_cancel=TR.buttons__skip,
        br_code=br_code,
    )


def confirm_path_warning(
    path: str,
    path_type: str | None = None,
) -> Awaitable[None]:
    title = f"{TR.words__unknown} {path_type if path_type else 'path'}"
    return _placeholder_confirm(
        "path_warning",
        title,
        description=path,
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


def confirm_multisig_warning() -> Awaitable[None]:
    return show_warning(
        "warning_multisig",
        TR.send__receiving_to_multisig,
        TR.words__continue_anyway,
    )


def confirm_homescreen(image: bytes) -> Awaitable[None]:
    return raise_if_not_confirmed(
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
    br_type: str = "show_address",
    br_code: ButtonRequestType = ButtonRequestType.Address,
    chunkify: bool = False,
) -> None:
    mismatch_title = mismatch_title or TR.addr_mismatch__mismatch  # def_arg
    send_button_request = True
    if title is None:
        # Will be a marquee in case of multisig
        title = TR.address__title_receive_address
        if multisig_index is not None:
            title = f"{title} (MULTISIG)"
    while True:
        layout = RustLayout(
            trezorui2.confirm_address(
                title=title,
                data=address,
                description="",  # unused on TR
                extra=None,  # unused on TR
                chunkify=chunkify,
            )
        )
        if send_button_request:
            send_button_request = False
            await button_request(
                br_type,
                br_code,
                pages=layout.page_count(),
            )
        layout.request_complete_repaint()
        result = await layout

        # User confirmed with middle button.
        if result is CONFIRMED:
            break

        # User pressed right button, go to address details.
        elif result is INFO:

            def xpub_title(i: int) -> str:
                # Will be marquee (cannot fit one line)
                result = f"MULTISIG XPUB #{i + 1}"
                result += (
                    f" ({TR.address__title_yours})"
                    if i == multisig_index
                    else f" ({TR.address__title_cosigner})"
                )
                return result

            result = await RustLayout(
                trezorui2.show_address_details(
                    qr_title="",  # unused on this model
                    address=address if address_qr is None else address_qr,
                    case_sensitive=case_sensitive,
                    details_title="",  # unused on this model
                    account=account,
                    path=path,
                    xpubs=[(xpub_title(i), xpub) for i, xpub in enumerate(xpubs)],
                )
            )
            # Can only go back from the address details.
            assert result is CANCELLED

        # User pressed left cancel button, show mismatch dialogue.
        else:
            result = await RustLayout(trezorui2.show_mismatch(title=mismatch_title))
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
        title=title,
        account=account,
        path=path,
        br_type=br_type,
        br_code=ButtonRequestType.PublicKey,
        mismatch_title=mismatch_title,
        chunkify=False,
    )


def _show_modal(
    br_type: str,
    header: str,
    subheader: str | None,
    content: str,
    button_confirm: str | None,
    button_cancel: str | None,
    br_code: ButtonRequestType,
    exc: ExceptionType = ActionCancelled,
) -> Awaitable[None]:
    return confirm_action(
        br_type,
        header,
        subheader,
        content,
        verb=button_confirm or "",
        verb_cancel=button_cancel,
        exc=exc,
        br_code=br_code,
    )


async def show_error_and_raise(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    exc: ExceptionType = ActionCancelled,
) -> NoReturn:
    button = button or TR.buttons__try_again  # def_arg
    await show_warning(
        br_type,
        subheader or "",
        content,
        button=button,
        br_code=BR_TYPE_OTHER,
    )
    raise exc


def show_warning(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[None]:
    from trezor import translations

    button = button or TR.buttons__continue  # def_arg

    # Putting there a delimiter line in case of english, so it looks better
    # (we know it will fit one page)
    # TODO: figure out some better and non-intrusive way to do this
    # (check if the content fits one page with the newline, and if not, do not add it)
    if content and subheader and translations.get_language() == "en-US":
        content = content + "\n"

    return interact(
        RustLayout(
            trezorui2.show_warning(  # type: ignore [Argument missing for parameter "title"]
                button=button,
                warning=content,  # type: ignore [No parameter named "warning"]
                description=subheader or "",
            )
        ),
        br_type,
        br_code,
    )


def show_success(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
) -> Awaitable[None]:
    button = button or TR.buttons__continue  # def_arg
    title = TR.words__title_success

    # In case only subheader is supplied, showing it
    # in regular font, not bold.
    if not content and subheader:
        content = subheader
        subheader = None

    # Special case for Shamir backup - to show everything just on one page
    # in regular font.
    if TR.words__continue_with in content:
        content = f"{subheader}\n\n{content}"
        subheader = None
        title = ""

    return _show_modal(
        br_type,
        title,
        subheader,
        content,
        button_confirm=button,
        button_cancel=None,
        br_code=ButtonRequestType.Success,
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
    source_account: str | None = None,  # ignored on safe 3
    source_account_path: str | None = None,  # ignored on safe 3
) -> None:
    title = title or TR.send__confirm_sending  # def_arg
    address_title = TR.words__recipient
    if output_index is not None:
        address_title += f" #{output_index + 1}"
    amount_title = TR.words__amount
    if output_index is not None:
        amount_title += f" #{output_index + 1}"

    while True:
        result = await interact(
            RustLayout(
                trezorui2.confirm_output_address(
                    address=address,
                    address_label=address_label or "",
                    address_title=address_title,
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
                trezorui2.confirm_output_amount(
                    amount_title=amount_title,
                    amount=amount,
                )
            ),
            "confirm_output",
            br_code,
        )
        if result is CONFIRMED:
            return


def tutorial(br_code: ButtonRequestType = BR_TYPE_OTHER) -> Awaitable[None]:
    """Showing users how to interact with the device."""
    return raise_if_not_confirmed(
        interact(
            RustLayout(trezorui2.tutorial()),
            "tutorial",
            br_code,
        )
    )


async def should_show_payment_request_details(
    recipient_name: str,
    amount: str,
    memos: list[str],
) -> bool:
    memos_str = "\n".join(memos)
    await _placeholder_confirm(
        "confirm_payment_request",
        TR.send__title_confirm_sending,
        description=f"{amount} to\n{recipient_name}\n{memos_str}",
        br_code=ButtonRequestType.ConfirmOutput,
    )
    return False


async def should_show_more(
    title: str,
    para: Iterable[tuple[int, str]],
    button_text: str | None = None,
    br_type: str = "should_show_more",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    confirm: str | bytes | None = None,
    verb_cancel: str | None = None,
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
                title=title,
                items=para,
                button=confirm,
                verb_cancel=verb_cancel,  # type: ignore [No parameter named "verb_cancel"]
                info_button=button_text,  # unused on TR
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


def confirm_blob(
    br_type: str,
    title: str,
    data: bytes | str,
    description: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = "",  # icon
    hold: bool = False,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    ask_pagination: bool = False,
    chunkify: bool = False,
    prompt_screen: bool = True,
) -> Awaitable[None]:
    verb = verb or TR.buttons__confirm  # def_arg
    layout = RustLayout(
        trezorui2.confirm_blob(
            title=title,
            description=description,
            data=data,
            extra=None,
            verb=verb,
            verb_cancel=verb_cancel,
            hold=hold,
            chunkify=chunkify,
        )
    )

    if ask_pagination and layout.page_count() > 1:
        assert not hold
        return _confirm_ask_pagination(
            br_type, title, data, description or "", verb_cancel, br_code
        )

    else:
        return raise_if_not_confirmed(
            interact(
                layout,
                br_type,
                br_code,
            )
        )


async def _confirm_ask_pagination(
    br_type: str,
    title: str,
    data: bytes | str,
    description: str,
    verb_cancel: str | None,
    br_code: ButtonRequestType,
) -> None:
    paginated: RustLayout[trezorui2.UiResult] | None = None
    # TODO: make should_show_more/confirm_more accept bytes directly
    if isinstance(data, (bytes, bytearray, memoryview)):
        from ubinascii import hexlify

        data = hexlify(data).decode()
    while True:
        if not await should_show_more(
            title,
            para=[(ui.NORMAL, description), (ui.MONO, data)],
            verb_cancel=verb_cancel,
            br_type=br_type,
            br_code=br_code,
        ):
            return

        if paginated is None:
            paginated = RustLayout(
                trezorui2.confirm_more(
                    title=title,
                    button=TR.buttons__go_back,
                    items=[
                        (ui.BOLD_UPPER, f"Size: {len(data)} bytes"),
                        (ui.MONO, data),
                    ],
                )
            )
        else:
            paginated.request_complete_repaint()

        result = await interact(paginated, br_type, br_code)
        assert result in (CONFIRMED, CANCELLED)

    assert False


def confirm_address(
    title: str,
    address: str,
    description: str | None = None,
    br_type: str = "confirm_address",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    return confirm_blob(
        br_type,
        title,
        address,
        description,
        br_code=br_code,
    )


def confirm_text(
    br_type: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    return _placeholder_confirm(
        br_type,
        title,
        data,
        description,
        br_code=br_code,
    )


def confirm_amount(
    title: str,
    amount: str,
    description: str | None = None,
    br_type: str = "confirm_amount",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    description = description or f"{TR.words__amount}:"  # def_arg
    return confirm_blob(
        br_type,
        title,
        amount,
        description,
        br_code=br_code,
    )


def confirm_properties(
    br_type: str,
    title: str,
    props: Iterable[PropertyType],
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> Awaitable[None]:
    from ubinascii import hexlify

    def handle_bytes(prop: PropertyType):
        key, value = prop
        if isinstance(value, (bytes, bytearray, memoryview)):
            return (key, hexlify(value).decode(), True)
        else:
            # When there is not space in the text, taking it as data
            # to not include hyphens
            is_data = value and " " not in value
            return (key, value, is_data)

    return raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_properties(
                    title=title,
                    items=map(handle_bytes, props),  # type: ignore [cannot be assigned to parameter "items"]
                    hold=hold,
                )
            ),
            br_type,
            br_code,
        )
    )


async def confirm_value(
    title: str,
    value: str,
    description: str,
    br_type: str,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    *,
    verb: str | None = None,
    hold: bool = False,
    info_items: Iterable[tuple[str, str]] | None = None,
    chunkify_info: bool = False,
) -> None:
    """General confirmation dialog, used by many other confirm_* functions."""

    if not verb and not hold:
        raise ValueError("Either verb or hold=True must be set")

    if info_items is None:
        return await raise_if_not_confirmed(
            interact(
                RustLayout(
                    trezorui2.confirm_value(  # type: ignore [Argument missing for parameter "subtitle"]
                        title=title,
                        description=description,
                        value=value,
                        verb=verb or TR.buttons__hold_to_confirm,
                        hold=hold,
                    )
                ),
                br_type,
                br_code,
            )
        )
    else:
        info_items_list = list(info_items)
        if len(info_items_list) > 1:
            raise NotImplementedError("Only one info item is supported")

        send_button_request = True
        while True:
            should_show_more_layout = RustLayout(
                trezorui2.confirm_with_info(
                    title=title,
                    items=((ui.NORMAL, value),),
                    button=verb or TR.buttons__confirm,
                    info_button=TR.buttons__info,
                )
            )

            if send_button_request:
                send_button_request = False
                await button_request(
                    br_type,
                    br_code,
                    should_show_more_layout.page_count(),
                )

            result = await should_show_more_layout

            if result is CONFIRMED:
                return
            elif result is INFO:
                info_title, info_value = info_items_list[0]
                await RustLayout(
                    trezorui2.confirm_blob(
                        title=info_title,
                        data=info_value,
                        description=description,
                        extra=None,
                        verb="",
                        verb_cancel="<",
                        hold=False,
                        chunkify=chunkify_info,
                    )
                )
            else:
                assert result is CANCELLED
                raise ActionCancelled


def confirm_total(
    total_amount: str,
    fee_amount: str,
    fee_rate_amount: str | None = None,
    title: str | None = None,
    total_label: str | None = None,
    fee_label: str | None = None,
    source_account: str | None = None,
    source_account_path: str | None = None,
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> Awaitable[None]:
    total_label = total_label or TR.send__total_amount_colon  # def_arg
    fee_label = fee_label or TR.send__including_fee  # def_arg
    return raise_if_not_confirmed(
        interact(
            RustLayout(
                # TODO: resolve these differences in TT's and TR's confirm_total
                trezorui2.confirm_total(  # type: ignore [Arguments missing]
                    total_amount=total_amount,  # type: ignore [No parameter named]
                    fee_amount=fee_amount,  # type: ignore [No parameter named]
                    fee_rate_amount=fee_rate_amount,  # type: ignore [No parameter named]
                    account_label=source_account,  # type: ignore [No parameter named]
                    total_label=total_label,  # type: ignore [No parameter named]
                    fee_label=fee_label,  # type: ignore [No parameter named]
                )
            ),
            br_type,
            br_code,
        )
    )


if not utils.BITCOIN_ONLY:

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
            info_items=((address_title, address),),
            chunkify_info=chunkify,
        )

        # confirmation
        if verb == TR.ethereum__staking_claim:
            amount_title = verb
            amount_value = ""
        else:
            amount_title = TR.words__amount + ":"
            amount_value = total_amount
        await raise_if_not_confirmed(
            interact(
                RustLayout(
                    trezorui2.altcoin_tx_summary(
                        amount_title=amount_title,
                        amount_value=amount_value,
                        fee_title=TR.send__maximum_fee,
                        fee_value=maximum_fee,
                        items=info_items,
                        cancel_cross=True,
                    )
                ),
                br_type=br_type,
                br_code=br_code,
            )
        )

    def confirm_solana_tx(
        amount: str,
        fee: str,
        items: Iterable[tuple[str, str]],
        amount_title: str | None = None,
        fee_title: str | None = None,
        br_type: str = "confirm_solana_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> Awaitable[None]:
        amount_title = (
            amount_title if amount_title is not None else f"{TR.words__amount}:"
        )  # def_arg
        fee_title = fee_title or TR.words__fee  # def_arg
        return raise_if_not_confirmed(
            interact(
                RustLayout(
                    trezorui2.altcoin_tx_summary(
                        amount_title=amount_title,
                        amount_value=amount,
                        fee_title=fee_title,
                        fee_value=fee,
                        items=items,
                        cancel_cross=True,
                    )
                ),
                br_type=br_type,
                br_code=br_code,
            )
        )

    async def confirm_ethereum_tx(
        recipient: str,
        total_amount: str,
        maximum_fee: str,
        items: Iterable[tuple[str, str]],
        br_type: str = "confirm_ethereum_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
        chunkify: bool = False,
    ) -> None:
        summary_layout = RustLayout(
            trezorui2.altcoin_tx_summary(
                amount_title=f"{TR.words__amount}:",
                amount_value=total_amount,
                fee_title=TR.send__maximum_fee,
                fee_value=maximum_fee,
                items=items,
            )
        )

        while True:
            # Allowing going back and forth between recipient and summary/details
            await confirm_blob(
                br_type,
                TR.words__recipient,
                recipient,
                verb=TR.buttons__continue,
                chunkify=chunkify,
            )

            try:
                summary_layout.request_complete_repaint()
                await raise_if_not_confirmed(
                    interact(
                        summary_layout,
                        br_type,
                        br_code,
                    )
                )
                break
            except ActionCancelled:
                continue


def confirm_joint_total(spending_amount: str, total_amount: str) -> Awaitable[None]:
    return raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_joint_total(
                    spending_amount=spending_amount,
                    total_amount=total_amount,
                )
            ),
            "confirm_joint_total",
            ButtonRequestType.SignTx,
        )
    )


def confirm_metadata(
    br_type: str,
    title: str,
    content: str,
    param: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    hold: bool = False,
) -> Awaitable[None]:
    return _placeholder_confirm(
        br_type,
        title,
        description=content.format(param),
        hold=hold,
        br_code=br_code,
    )


def confirm_replacement(description: str, txid: str) -> Awaitable[None]:
    return confirm_value(
        description,
        txid,
        TR.send__transaction_id,
        "confirm_replacement",
        ButtonRequestType.SignTx,
        verb=TR.buttons__continue,
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
        await raise_if_not_confirmed(address_layout)

        if send_button_request:
            send_button_request = False
            await button_request(
                "modify_output",
                ButtonRequestType.ConfirmOutput,
                modify_layout.page_count(),
            )
        modify_layout.request_complete_repaint()
        result = await modify_layout

        if result is CONFIRMED:
            break


def confirm_modify_fee(
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None = None,
) -> Awaitable[None]:
    return raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_modify_fee(
                    title=title,
                    sign=sign,
                    user_fee_change=user_fee_change,
                    total_fee_new=total_fee_new,
                    fee_rate_amount=fee_rate_amount,
                )
            ),
            "modify_fee",
            ButtonRequestType.SignTx,
        )
    )


def confirm_coinjoin(max_rounds: int, max_fee_per_vbyte: str) -> Awaitable[None]:
    return raise_if_not_confirmed(
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
def confirm_sign_identity(
    proto: str, identity: str, challenge_visual: str | None
) -> Awaitable[None]:
    text = ""
    if challenge_visual:
        text += f"{challenge_visual}\n\n"
    text += identity

    return _placeholder_confirm(
        "confirm_sign_identity",
        f"{TR.words__sign} {proto}",
        text,
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
    br_type = "verify_message" if verify else "sign_message"

    # Allowing to go back from the second screen
    while True:
        await confirm_blob(
            br_type,
            TR.sign_message__confirm_address,
            address,
            verb=TR.buttons__continue,
            br_code=BR_TYPE_OTHER,
        )

        try:
            await confirm_blob(
                br_type,
                TR.sign_message__confirm_message,
                message,
                verb_cancel="^",
                br_code=BR_TYPE_OTHER,
                ask_pagination=True,
            )
        except ActionCancelled:
            continue
        else:
            break


def show_error_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    *,
    button: str = "",
    timeout_ms: int = 0,
) -> Awaitable[None]:
    if button:
        raise NotImplementedError("Button not implemented")
    description = description.format(description_param)
    if subtitle:
        description = f"{subtitle}\n{description}"
    layout = RustLayout(
        trezorui2.show_info(
            title=title,
            description=description,
            time_ms=timeout_ms,
        )
    )
    return layout  # type: ignore [Expression of type "RustLayout[UiResult]" is incompatible with return type "Awaitable[None]"]


def request_passphrase_on_host() -> None:
    draw_simple(trezorui2.show_passphrase())


def show_wait_text(message: str) -> None:
    draw_simple(trezorui2.show_wait_text(message))


async def request_passphrase_on_device(max_len: int) -> str:
    result = await interact(
        RustLayout(
            trezorui2.request_passphrase(
                prompt=TR.passphrase__title_enter,
                max_len=max_len,
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
    from trezor import wire

    # Not showing the prompt in case user did not enter it badly yet
    # (has full 16 attempts left)
    if attempts_remaining is None or attempts_remaining == 16:
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
        raise wire.PinCancelled
    assert isinstance(result, str)
    return result


def confirm_reenter_pin(is_wipe_code: bool = False) -> Awaitable[None]:
    br_type = "reenter_wipe_code" if is_wipe_code else "reenter_pin"
    title = TR.wipe_code__title_check if is_wipe_code else TR.pin__title_check_pin
    description = (
        TR.wipe_code__reenter_to_confirm if is_wipe_code else TR.pin__reenter_to_confirm
    )
    return confirm_action(
        br_type,
        title,
        description=description,
        verb=TR.buttons__continue,
        verb_cancel=None,
        br_code=BR_TYPE_OTHER,
    )


def _confirm_multiple_pages_texts(
    br_type: str,
    title: str,
    items: list[str],
    verb: str,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    return raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.multiple_pages_texts(
                    title=title,
                    verb=verb,
                    items=items,
                )
            ),
            br_type,
            br_code,
        )
    )


def pin_mismatch_popup(is_wipe_code: bool = False) -> Awaitable[None]:
    description = TR.wipe_code__mismatch if is_wipe_code else TR.pin__mismatch
    br_code = "wipe_code_mismatch" if is_wipe_code else "pin_mismatch"
    return show_warning(
        br_code,
        description,
        TR.pin__please_check_again,
        TR.buttons__check_again,
        BR_TYPE_OTHER,
    )


def wipe_code_same_as_pin_popup() -> Awaitable[None]:
    return confirm_action(
        "wipe_code_same_as_pin",
        TR.wipe_code__title_invalid,
        description=TR.wipe_code__diff_from_pin,
        verb=TR.buttons__try_again,
        verb_cancel=None,
        br_code=BR_TYPE_OTHER,
    )


async def confirm_set_new_pin(
    br_type: str,
    title: str,
    description: str,
    information: str,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    await _confirm_multiple_pages_texts(
        br_type,
        title,
        [description, information],
        TR.buttons__turn_on,
        br_code,
    )

    # Not showing extra info for wipe code
    if "wipe_code" in br_type:
        return

    # Additional information for the user to know about PIN
    next_info = [
        TR.pin__should_be_long,
        TR.pin__cursor_will_change,
    ]
    await _confirm_multiple_pages_texts(
        br_type,
        title,
        next_info,
        TR.buttons__continue,
        br_code,
    )


def confirm_firmware_update(description: str, fingerprint: str) -> Awaitable[None]:
    return raise_if_not_confirmed(
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
