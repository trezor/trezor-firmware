from typing import TYPE_CHECKING

from trezor import io, loop, ui
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

import trezorui2

from ..common import button_request, interact

if TYPE_CHECKING:
    from typing import Any, NoReturn, Awaitable, Iterable, Sequence, TypeVar

    from trezor.wire import GenericContext, Context
    from ..common import PropertyType, ExceptionType

    T = TypeVar("T")


CONFIRMED = trezorui2.CONFIRMED
CANCELLED = trezorui2.CANCELLED
INFO = trezorui2.INFO

BR_TYPE_OTHER = ButtonRequestType.Other  # global_import_cache


if __debug__:
    from trezor.utils import DISABLE_ANIMATION

    trezorui2.disable_animation(bool(DISABLE_ANIMATION))


class RustLayout(ui.Layout):
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
        from trezor.enums import DebugPhysicalButton

        def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
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
            from apps.debug import result_signal
            from storage import debug as debug_storage

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
            self._paint()
            if hold_ms is not None:
                await loop.sleep(hold_ms)
            return self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_LEFT)

        async def _press_right(self, hold_ms: int | None) -> Any:
            """Triggers right button press."""
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_RIGHT)
            self._paint()
            if hold_ms is not None:
                await loop.sleep(hold_ms)
            return self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_RIGHT)

        async def _press_middle(self, hold_ms: int | None) -> Any:
            """Triggers middle button press."""
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_LEFT)
            self._paint()
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_RIGHT)
            self._paint()
            if hold_ms is not None:
                await loop.sleep(hold_ms)
            self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_LEFT)
            self._paint()
            return self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_RIGHT)

        async def _press_button(
            self,
            event_id: int | None,
            btn_to_press: DebugPhysicalButton,
            hold_ms: int | None,
        ) -> Any:
            from trezor.enums import DebugPhysicalButton
            from trezor import workflow
            from apps.debug import notify_layout_change
            from storage import debug as debug_storage

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
            return self.handle_timers(), self.handle_input_and_rendering()

    def _first_paint(self) -> None:
        # Clear the screen of any leftovers.
        ui.display.clear()
        self._paint()

        if __debug__ and self.should_notify_layout_change:
            from apps.debug import notify_layout_change
            from storage import debug as debug_storage

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

    def handle_input_and_rendering(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
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
        """How many paginated pages current screen has."""
        return self.layout.page_count()


def draw_simple(layout: Any) -> None:
    # Simple drawing not supported for layouts that set timers.
    def dummy_set_timer(token: int, deadline: int) -> None:
        raise RuntimeError

    layout.attach_timer_fn(dummy_set_timer)
    ui.display.clear()
    layout.paint()
    ui.refresh()


# Temporary function, so we know where it is used
# Should be gradually replaced by custom designs/layouts
async def _placeholder_confirm(
    ctx: GenericContext,
    br_type: str,
    title: str,
    data: str | None = None,
    description: str | None = None,
    *,
    verb: str = "CONFIRM",
    verb_cancel: str | None = "",
    hold: bool = False,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Any:
    return await confirm_action(
        ctx,
        br_type,
        title.upper(),
        data,
        description,
        verb=verb,
        verb_cancel=verb_cancel,
        hold=hold,
        reverse=True,
        br_code=br_code,
    )


async def get_bool(
    ctx: GenericContext,
    br_type: str,
    title: str,
    data: str | None = None,
    description: str | None = None,
    verb: str = "CONFIRM",
    verb_cancel: str | None = "",
    hold: bool = False,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> bool:
    result = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_action(
                title=title.upper(),
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


async def raise_if_not_confirmed(a: Awaitable[T], exc: Any = ActionCancelled) -> T:
    result = await a
    if result is not CONFIRMED:
        raise exc
    return result


async def confirm_action(
    ctx: GenericContext,
    br_type: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    verb: str = "CONFIRM",
    verb_cancel: str | None = "",
    hold: bool = False,
    hold_danger: bool = False,
    reverse: bool = False,
    exc: ExceptionType = ActionCancelled,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    if verb_cancel is not None:
        verb_cancel = verb_cancel.upper()

    if description is not None and description_param is not None:
        description = description.format(description_param)

    await raise_if_not_confirmed(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_action(
                    title=title.upper(),
                    action=action,
                    description=description,
                    verb=verb.upper(),
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


async def confirm_single(
    ctx: GenericContext,
    br_type: str,
    title: str,
    description: str,
    description_param: str | None = None,
    verb: str | None = None,
) -> None:
    description_param = description_param or ""
    begin, _separator, end = description.partition("{}")
    await confirm_action(
        ctx,
        br_type,
        title,
        description=begin + description_param + end,
        verb=verb or "CONFIRM",
        br_code=ButtonRequestType.ProtectCall,
    )


async def confirm_reset_device(
    ctx: GenericContext,
    title: str,
    recovery: bool = False,
) -> None:
    if recovery:
        button = "RECOVER WALLET"
    else:
        button = "CREATE WALLET"

    await raise_if_not_confirmed(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_reset_device(
                    title=title.upper(),
                    button=button,
                )
            ),
            "recover_device" if recovery else "setup_device",
            ButtonRequestType.ProtectCall
            if recovery
            else ButtonRequestType.ResetDevice,
        )
    )


# TODO cleanup @ redesign
async def confirm_backup(ctx: GenericContext) -> bool:
    if await get_bool(
        ctx,
        "backup_device",
        "SUCCESS",
        description="New wallet has been created.\nIt should be backed up now!",
        verb="BACK UP",
        verb_cancel="SKIP",
        br_code=ButtonRequestType.ResetDevice,
    ):
        return True

    return await get_bool(
        ctx,
        "backup_device",
        "WARNING",
        "Are you sure you want to skip the backup?\n",
        "You can back up your Trezor once, at any time.",
        verb="BACK UP",
        verb_cancel="SKIP",
        br_code=ButtonRequestType.ResetDevice,
    )


async def confirm_path_warning(
    ctx: GenericContext,
    path: str,
    path_type: str | None = None,
) -> None:
    if path_type:
        title = f"Unknown {path_type}"
    else:
        title = "Unknown path"
    return await _placeholder_confirm(
        ctx,
        "path_warning",
        title.upper(),
        description=path,
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


async def confirm_homescreen(
    ctx: GenericContext,
    image: bytes,
) -> None:
    # TODO: show homescreen preview?
    await confirm_action(
        ctx,
        "set_homescreen",
        "Set homescreen",
        description="Do you really want to set new homescreen image?",
        br_code=ButtonRequestType.ProtectCall,
    )


def _show_xpub(xpub: str, title: str, cancel: str | None) -> ui.Layout:
    return RustLayout(
        trezorui2.confirm_blob(
            title=title.upper(),
            data=xpub,
            verb_cancel=cancel,
            description=None,
            extra=None,
        )
    )


async def show_xpub(ctx: GenericContext, xpub: str, title: str) -> None:
    await raise_if_not_confirmed(
        interact(
            ctx,
            _show_xpub(xpub, title, None),
            "show_xpub",
            ButtonRequestType.PublicKey,
        )
    )


async def show_address(
    ctx: GenericContext,
    address: str,
    *,
    address_qr: str | None = None,
    case_sensitive: bool = True,
    path: str | None = None,
    account: str | None = None,
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
) -> None:
    send_button_request = True
    # Will be a marquee in case of multisig
    title = (
        "RECEIVE ADDRESS (MULTISIG)"
        if multisig_index is not None
        else "RECEIVE ADDRESS"
    )
    while True:
        layout = RustLayout(
            trezorui2.confirm_address(
                title=title,
                data=address,
                description="",  # unused on TR
                extra=None,  # unused on TR
            )
        )
        if send_button_request:
            send_button_request = False
            await button_request(
                ctx,
                "show_address",
                ButtonRequestType.Address,
                pages=layout.page_count(),
            )
        result = await ctx.wait(layout)

        # User confirmed with middle button.
        if result is CONFIRMED:
            break

        # User pressed right button, go to address details.
        elif result is INFO:

            def xpub_title(i: int) -> str:
                # Will be marquee (cannot fit one line)
                result = f"MULTISIG XPUB #{i + 1}"
                result += " (YOURS)" if i == multisig_index else " (COSIGNER)"
                return result

            result = await ctx.wait(
                RustLayout(
                    trezorui2.show_address_details(
                        address=address if address_qr is None else address_qr,
                        case_sensitive=case_sensitive,
                        account=account,
                        path=path,
                        xpubs=[(xpub_title(i), xpub) for i, xpub in enumerate(xpubs)],
                    )
                ),
            )
            # Can only go back from the address details.
            assert result is CANCELLED

        # User pressed left cancel button, show mismatch dialogue.
        else:
            result = await ctx.wait(RustLayout(trezorui2.show_mismatch()))
            assert result in (CONFIRMED, CANCELLED)
            # Right button aborts action, left goes back to showing address.
            if result is CONFIRMED:
                raise ActionCancelled


def show_pubkey(
    ctx: Context, pubkey: str, title: str = "Confirm public key"
) -> Awaitable[None]:
    return confirm_blob(
        ctx,
        "show_pubkey",
        title.upper(),
        pubkey,
        br_code=ButtonRequestType.PublicKey,
    )


async def _show_modal(
    ctx: GenericContext,
    br_type: str,
    header: str,
    subheader: str | None,
    content: str,
    button_confirm: str | None,
    button_cancel: str | None,
    br_code: ButtonRequestType,
    exc: ExceptionType = ActionCancelled,
) -> None:
    await confirm_action(
        ctx,
        br_type,
        header.upper(),
        subheader,
        content,
        verb=button_confirm or "",
        verb_cancel=button_cancel,
        exc=exc,
        br_code=br_code,
    )


async def show_error_and_raise(
    ctx: GenericContext,
    br_type: str,
    content: str,
    header: str = "Error",
    subheader: str | None = None,
    button: str = "Close",
    red: bool = False,  # unused on TR
    exc: ExceptionType = ActionCancelled,
) -> NoReturn:
    await _show_modal(
        ctx,
        br_type,
        header,
        subheader,
        content,
        button_confirm=None,
        button_cancel=button,
        br_code=BR_TYPE_OTHER,
        exc=exc,
    )
    raise exc


def show_warning(
    ctx: GenericContext,
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "Try again",
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[None]:
    return _show_modal(
        ctx,
        br_type,
        "",
        subheader or "WARNING",
        content,
        button_confirm=button,
        button_cancel=None,
        br_code=br_code,
    )


def show_success(
    ctx: GenericContext,
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "Continue",
) -> Awaitable[None]:
    title = "Success"

    # In case only subheader is supplied, showing it
    # in regular font, not bold.
    if not content and subheader:
        content = subheader
        subheader = None

    # Special case for Shamir backup - to show everything just on one page
    # in regular font.
    if "Continue with" in content:
        content = f"{subheader}\n{content}"
        subheader = None
        title = ""

    return _show_modal(
        ctx,
        br_type,
        title,
        subheader,
        content,
        button_confirm=button,
        button_cancel=None,
        br_code=ButtonRequestType.Success,
    )


async def confirm_output(
    ctx: GenericContext,
    address: str,
    amount: str,
    title: str = "Confirm sending",
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
    address_label: str | None = None,
    output_index: int | None = None,
) -> None:
    address_title = (
        "RECIPIENT" if output_index is None else f"RECIPIENT #{output_index + 1}"
    )
    amount_title = "AMOUNT" if output_index is None else f"AMOUNT #{output_index + 1}"

    await raise_if_not_confirmed(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_output(
                    address=address,
                    address_label=address_label or "",
                    address_title=address_title,
                    amount_title=amount_title,
                    amount=amount,
                )
            ),
            "confirm_output",
            br_code,
        )
    )


async def tutorial(
    ctx: GenericContext,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    """Showing users how to interact with the device."""
    await interact(
        ctx,
        RustLayout(trezorui2.tutorial()),
        "tutorial",
        br_code,
    )


async def confirm_payment_request(
    ctx: GenericContext,
    recipient_name: str,
    amount: str,
    memos: list[str],
) -> Any:
    memos_str = "\n".join(memos)
    return await _placeholder_confirm(
        ctx,
        "confirm_payment_request",
        "CONFIRM SENDING",
        description=f"{amount} to\n{recipient_name}\n{memos_str}",
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def should_show_more(
    ctx: GenericContext,
    title: str,
    para: Iterable[tuple[int, str]],
    button_text: str = "Show all",
    br_type: str = "should_show_more",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    confirm: str | bytes | None = None,
) -> bool:
    """Return True if the user wants to show more (they click a special button)
    and False when the user wants to continue without showing details.

    Raises ActionCancelled if the user cancels.
    """
    if confirm is None or not isinstance(confirm, str):
        confirm = "CONFIRM"

    result = await interact(
        ctx,
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


async def confirm_blob(
    ctx: GenericContext,
    br_type: str,
    title: str,
    data: bytes | str,
    description: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    ask_pagination: bool = False,
) -> None:
    title = title.upper()
    description = description or ""
    layout = RustLayout(
        trezorui2.confirm_blob(
            title=title,
            description=description,
            data=data,
            extra=None,
            hold=hold,
        )
    )

    await raise_if_not_confirmed(
        interact(
            ctx,
            layout,
            br_type,
            br_code,
        )
    )


async def confirm_address(
    ctx: GenericContext,
    title: str,
    address: str,
    description: str | None = "Address:",
    br_type: str = "confirm_address",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    return confirm_blob(
        ctx,
        br_type,
        title.upper(),
        address,
        description,
        br_code=br_code,
    )


async def confirm_text(
    ctx: GenericContext,
    br_type: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Any:
    return await _placeholder_confirm(
        ctx,
        br_type,
        title,
        data,
        description,
        br_code=br_code,
    )


def confirm_amount(
    ctx: GenericContext,
    title: str,
    amount: str,
    description: str = "Amount:",
    br_type: str = "confirm_amount",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    return confirm_blob(
        ctx,
        br_type,
        title.upper(),
        amount,
        description,
        br_code=br_code,
    )


async def confirm_properties(
    ctx: GenericContext,
    br_type: str,
    title: str,
    props: Iterable[PropertyType],
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> None:
    from ubinascii import hexlify

    def handle_bytes(prop: PropertyType):
        if isinstance(prop[1], bytes):
            return (prop[0], hexlify(prop[1]).decode(), True)
        else:
            # When there is not space in the text, taking it as data
            # to not include hyphens
            is_data = prop[1] and " " not in prop[1]
            return (prop[0], prop[1], is_data)

    await raise_if_not_confirmed(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_properties(
                    title=title.upper(),
                    items=map(handle_bytes, props),  # type: ignore [cannot be assigned to parameter "items"]
                    hold=hold,
                )
            ),
            br_type,
            br_code,
        )
    )


def confirm_value(
    ctx: GenericContext,
    title: str,
    value: str,
    description: str,
    br_type: str,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
    *,
    verb: str | None = None,
    hold: bool = False,
) -> Awaitable[None]:
    """General confirmation dialog, used by many other confirm_* functions."""

    if not verb and not hold:
        raise ValueError("Either verb or hold=True must be set")

    return raise_if_not_confirmed(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_value(  # type: ignore [Argument missing for parameter "subtitle"]
                    title=title.upper(),
                    description=description,
                    value=value,
                    verb=verb or "HOLD TO CONFIRM",
                    hold=hold,
                )
            ),
            br_type,
            br_code,
        )
    )


async def confirm_total(
    ctx: GenericContext,
    total_amount: str,
    fee_amount: str,
    fee_rate_amount: str | None = None,
    title: str = "SENDING",
    total_label: str = "TOTAL AMOUNT",
    fee_label: str = "Including fee:",
    account_label: str | None = None,
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    await raise_if_not_confirmed(
        interact(
            ctx,
            RustLayout(
                # TODO: resolve these differences in TT's and TR's confirm_total
                trezorui2.confirm_total(  # type: ignore [Arguments missing]
                    total_amount=total_amount,  # type: ignore [No parameter named]
                    fee_amount=fee_amount,  # type: ignore [No parameter named]
                    fee_rate_amount=fee_rate_amount,  # type: ignore [No parameter named]
                    account_label=account_label,  # type: ignore [No parameter named]
                    total_label=total_label.upper(),  # type: ignore [No parameter named]
                    fee_label=fee_label,  # type: ignore [No parameter named]
                )
            ),
            br_type,
            br_code,
        )
    )


async def confirm_joint_total(
    ctx: GenericContext, spending_amount: str, total_amount: str
) -> None:

    await raise_if_not_confirmed(
        interact(
            ctx,
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


async def confirm_metadata(
    ctx: GenericContext,
    br_type: str,
    title: str,
    content: str,
    param: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    hold: bool = False,
) -> None:
    await _placeholder_confirm(
        ctx,
        br_type,
        title.upper(),
        description=content.format(param),
        hold=hold,
        br_code=br_code,
    )


async def confirm_replacement(ctx: GenericContext, description: str, txid: str) -> None:
    await confirm_value(
        ctx,
        description.upper(),
        txid,
        "Confirm transaction ID:",
        "confirm_replacement",
        ButtonRequestType.SignTx,
        verb="CONFIRM",
    )


async def confirm_modify_output(
    ctx: GenericContext,
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    await raise_if_not_confirmed(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_modify_output(
                    address=address,
                    sign=sign,
                    amount_change=amount_change,
                    amount_new=amount_new,
                )
            ),
            "modify_output",
            ButtonRequestType.ConfirmOutput,
        )
    )


async def confirm_modify_fee(
    ctx: GenericContext,
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None = None,
) -> None:
    await raise_if_not_confirmed(
        interact(
            ctx,
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


async def confirm_coinjoin(
    ctx: GenericContext, max_rounds: int, max_fee_per_vbyte: str
) -> None:
    await raise_if_not_confirmed(
        interact(
            ctx,
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
    ctx: GenericContext, proto: str, identity: str, challenge_visual: str | None
) -> None:
    text = ""
    if challenge_visual:
        text += f"{challenge_visual}\n\n"
    text += identity

    await _placeholder_confirm(
        ctx,
        "confirm_sign_identity",
        f"Sign {proto}".upper(),
        text,
        br_code=BR_TYPE_OTHER,
    )


async def confirm_signverify(
    ctx: GenericContext, coin: str, message: str, address: str, verify: bool
) -> None:
    if verify:
        header = f"Verify {coin} message"
        br_type = "verify_message"
    else:
        header = f"Sign {coin} message"
        br_type = "sign_message"

    await confirm_blob(
        ctx,
        br_type,
        header.upper(),
        address,
        "Confirm address:",
        br_code=BR_TYPE_OTHER,
    )

    await confirm_value(
        ctx,
        header.upper(),
        message,
        "Confirm message:",
        br_type,
        BR_TYPE_OTHER,
        verb="CONFIRM",
    )


async def show_error_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    *,
    button: str = "",
    timeout_ms: int = 0,
) -> None:
    if button:
        raise NotImplementedError("Button not implemented")
    description = description.format(description_param)
    if subtitle:
        description = f"{subtitle}\n{description}"
    await RustLayout(
        trezorui2.show_info(
            title=title,
            description=description,
            time_ms=timeout_ms,
        )
    )


def request_passphrase_on_host() -> None:
    draw_simple(
        trezorui2.show_info(
            title="HIDDEN WALLET",
            description="Please type your passphrase on the connected host.",
        )
    )


async def request_passphrase_on_device(ctx: GenericContext, max_len: int) -> str:
    await button_request(
        ctx, "passphrase_device", code=ButtonRequestType.PassphraseEntry
    )

    result = await ctx.wait(
        RustLayout(
            trezorui2.request_passphrase(
                prompt="ENTER PASSPHRASE",
                max_len=max_len,
            )
        )
    )
    if result is CANCELLED:
        raise ActionCancelled("Passphrase entry cancelled")

    assert isinstance(result, str)
    return result


async def request_pin_on_device(
    ctx: GenericContext,
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
        subprompt = "Last attempt"
    else:
        subprompt = f"{attempts_remaining} tries left"

    await button_request(ctx, "pin_device", code=ButtonRequestType.PinEntry)

    dialog = RustLayout(
        trezorui2.request_pin(
            prompt=prompt,
            subprompt=subprompt,
            allow_cancel=allow_cancel,
            wrong_pin=wrong_pin,
        )
    )

    result = await ctx.wait(dialog)
    if result is CANCELLED:
        raise wire.PinCancelled
    assert isinstance(result, str)
    return result


async def confirm_reenter_pin(
    ctx: GenericContext,
    is_wipe_code: bool = False,
) -> None:
    br_type = "reenter_wipe_code" if is_wipe_code else "reenter_pin"
    title = "CHECK WIPE CODE" if is_wipe_code else "CHECK PIN"
    return await confirm_action(
        ctx,
        br_type,
        title,
        action="Please re-enter to confirm.",
        verb="BEGIN",
        br_code=BR_TYPE_OTHER,
    )


async def pin_mismatch_popup(
    ctx: GenericContext,
    is_wipe_code: bool = False,
) -> None:
    title = "WIPE CODE MISMATCH" if is_wipe_code else "PIN MISMATCH"
    description = "wipe codes" if is_wipe_code else "PINs"
    return await confirm_action(
        ctx,
        "pin_mismatch",
        title,
        description=f"The {description} you entered do not match.\nPlease try again.",
        verb="TRY AGAIN",
        verb_cancel=None,
        br_code=BR_TYPE_OTHER,
    )


async def wipe_code_same_as_pin_popup(
    ctx: GenericContext,
    is_wipe_code: bool = False,
) -> None:
    return await confirm_action(
        ctx,
        "wipe_code_same_as_pin",
        "INVALID WIPE CODE",
        description="The wipe code must be different from your PIN.\nPlease try again.",
        verb="TRY AGAIN",
        verb_cancel=None,
        br_code=BR_TYPE_OTHER,
    )


async def confirm_set_new_pin(
    ctx: GenericContext,
    br_type: str,
    title: str,
    description: str,
    information: list[str],
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    await confirm_action(
        ctx,
        br_type,
        title,
        description=description,
        verb="ENABLE",
        br_code=br_code,
    )

    # Additional information for the user to know about PIN/WIPE CODE

    if "wipe_code" in br_type:
        verb = "HODL TO BEGIN"  # Easter egg from @Hannsek
    else:
        information.append(
            "Position of individual numbers will change between entries for enhanced security."
        )
        verb = "HOLD TO BEGIN"

    return await confirm_action(
        ctx,
        br_type,
        "",
        description="\n\r".join(information),
        verb=verb,
        hold=True,
        br_code=br_code,
    )


async def mnemonic_word_entering(ctx: GenericContext) -> None:
    await confirm_action(
        ctx,
        "request_word",
        "WORD ENTERING",
        description="You'll only have to select the first 2-3 letters.",
        verb="CONTINUE",
        verb_cancel=None,
        br_code=ButtonRequestType.MnemonicInput,
    )
