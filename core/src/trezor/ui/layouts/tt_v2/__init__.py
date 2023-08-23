from typing import TYPE_CHECKING

import trezorui2
from trezor import io, loop, ui
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
        # Clear the screen of any leftovers.
        ui.backlight_fade(ui.style.BACKLIGHT_NONE)
        ui.display.clear()
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
    ui.display.clear()
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
    begin, _separator, end = description.partition("{}")
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
        button = "RECOVER WALLET"
    else:
        button = "CREATE WALLET"

    await raise_if_not_confirmed(
        interact(
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
async def prompt_backup() -> bool:
    result = await interact(
        RustLayout(
            trezorui2.confirm_action(
                title="SUCCESS",
                action="New wallet created successfully.",
                description="You should back up your new wallet right now.",
                verb="BACK UP",
                verb_cancel="SKIP",
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
                title="WARNING",
                action="Are you sure you want to skip the backup?",
                description="You can back up your Trezor once, at any time.",
                verb="BACK UP",
                verb_cancel="SKIP",
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
    title = "Unknown path" if not path_type else f"Unknown {path_type.lower()}"
    await show_warning(
        "path_warning",
        title,
        path,
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


async def confirm_homescreen(
    image: bytes,
) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_homescreen(
                    title="SET HOMESCREEN",
                    image=image,
                )
            ),
            "set_homesreen",
            ButtonRequestType.ProtectCall,
        )
    )


async def show_xpub(xpub: str, title: str) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_blob(
                    title=title,
                    data=xpub,
                    verb="CONFIRM",
                    verb_cancel=None,
                    extra=None,
                    description=None,
                )
            ),
            "show_xpub",
            ButtonRequestType.PublicKey,
        )
    )


async def show_address(
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
    title = (
        "RECEIVE ADDRESS\n(MULTISIG)"
        if multisig_index is not None
        else "RECEIVE ADDRESS"
    )
    while True:
        layout = RustLayout(
            trezorui2.confirm_address(
                title=title,
                data=address,
                description=network or "",
                extra=None,
            )
        )
        if send_button_request:
            send_button_request = False
            await button_request(
                "show_address",
                ButtonRequestType.Address,
                pages=layout.page_count(),
            )
        result = await ctx_wait(layout)

        # User pressed right button.
        if result is CONFIRMED:
            break

        # User pressed corner button or swiped left, go to address details.
        elif result is INFO:

            def xpub_title(i: int) -> str:
                result = f"MULTISIG XPUB #{i + 1}\n"
                result += "(YOURS)" if i == multisig_index else "(COSIGNER)"
                return result

            result = await ctx_wait(
                RustLayout(
                    trezorui2.show_address_details(
                        address=address if address_qr is None else address_qr,
                        case_sensitive=case_sensitive,
                        account=account,
                        path=path,
                        xpubs=[(xpub_title(i), xpub) for i, xpub in enumerate(xpubs)],
                    )
                )
            )
            assert result is CANCELLED

        else:
            result = await ctx_wait(RustLayout(trezorui2.show_mismatch()))
            assert result in (CONFIRMED, CANCELLED)
            # Right button aborts action, left goes back to showing address.
            if result is CONFIRMED:
                raise ActionCancelled


def show_pubkey(pubkey: str, title: str = "Confirm public key") -> Awaitable[None]:
    return confirm_blob(
        "show_pubkey",
        title,
        pubkey,
        br_code=ButtonRequestType.PublicKey,
    )


async def show_error_and_raise(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "TRY AGAIN",
    exc: ExceptionType = ActionCancelled,
) -> NoReturn:
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
    button: str = "CONTINUE",
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
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
    button: str = "CONTINUE",
) -> None:
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
) -> None:
    if title is not None:
        if title.upper().startswith("CONFIRM "):
            title = title[len("CONFIRM ") :]
        amount_title = title.upper()
        recipient_title = title.upper()
    elif output_index is not None:
        amount_title = f"AMOUNT #{output_index + 1}"
        recipient_title = f"RECIPIENT #{output_index + 1}"
    else:
        amount_title = "SENDING AMOUNT"
        recipient_title = "SENDING TO"

    while True:
        result = await interact(
            RustLayout(
                trezorui2.confirm_value(
                    title=recipient_title,
                    subtitle=address_label,
                    description=None,
                    value=address,
                    verb="CONTINUE",
                    hold=False,
                    info_button=False,
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
                    title=amount_title,
                    subtitle=None,
                    description=None,
                    value=amount,
                    verb=None if hold else "CONFIRM",
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
                title="SENDING",
                items=[(ui.NORMAL, f"{amount} to\n{recipient_name}")]
                + [(ui.NORMAL, memo) for memo in memos],
                button="CONFIRM",
                info_button="DETAILS",
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
                    button="CLOSE",
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
    verb: str = "CONFIRM",
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
            verb=verb,
        )
    )

    if ask_pagination and layout.page_count() > 1:
        assert not hold
        await _confirm_ask_pagination(br_type, title, data, description, br_code)

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
    description: str | None = "Address:",
    br_type: str = "confirm_address",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    return await confirm_value(
        title,
        address,
        description or "",
        br_type,
        br_code,
        verb="CONFIRM",
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
        verb="CONFIRM",
    )


def confirm_amount(
    title: str,
    amount: str,
    description: str = "Amount:",
    br_type: str = "confirm_amount",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Awaitable[None]:
    return confirm_value(
        title,
        amount,
        description,
        br_type,
        br_code,
        verb="CONFIRM",
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
    info_button: bool = False,
) -> Awaitable[None]:
    """General confirmation dialog, used by many other confirm_* functions."""

    if not verb and not hold:
        raise ValueError("Either verb or hold=True must be set")

    if verb:
        verb = verb.upper()

    return raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_value(
                    title=title.upper(),
                    subtitle=subtitle,
                    description=description,
                    value=value,
                    verb=verb,
                    hold=hold,
                    info_button=info_button,
                )
            ),
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
    fee_rate_amount: str | None = None,
    title: str = "SUMMARY",
    total_label: str = "Total amount:",
    fee_label: str = "Including fee:",
    account_label: str | None = None,
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    total_layout = RustLayout(
        trezorui2.confirm_total(
            title=title,
            items=[
                (total_label, total_amount),
                (fee_label, fee_amount),
            ],
            info_button=bool(account_label or fee_rate_amount),
        )
    )
    info_layout = RustLayout(
        trezorui2.show_spending_details(
            account=account_label or "",
            fee_rate=fee_rate_amount or "",
        )
    )
    await with_info(total_layout, info_layout, br_type, br_code)


async def confirm_joint_total(spending_amount: str, total_amount: str) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.confirm_total(
                    title="JOINT TRANSACTION",
                    items=[
                        ("You are contributing:", spending_amount),
                        ("To the total amount:", total_amount),
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
    verb: str = "CONTINUE",
) -> None:
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
        title=title.upper(),
        data=txid,
        description="Transaction ID:",
        verb="CONTINUE",
        br_type="confirm_replacement",
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_modify_output(
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    send_button_request = True
    while True:
        if send_button_request:
            await button_request(
                "modify_output",
                ButtonRequestType.ConfirmOutput,
            )
        await raise_if_not_confirmed(
            ctx_wait(
                RustLayout(
                    trezorui2.confirm_blob(
                        title="MODIFY AMOUNT",
                        data=address,
                        verb="CONTINUE",
                        verb_cancel=None,
                        description="Address:",
                        extra=None,
                    )
                )
            )
        )

        if send_button_request:
            send_button_request = False
            await button_request(
                "modify_output",
                ButtonRequestType.ConfirmOutput,
            )
        result = await ctx_wait(
            RustLayout(
                trezorui2.confirm_modify_output(
                    address=address,
                    sign=sign,
                    amount_change=amount_change,
                    amount_new=amount_new,
                )
            ),
        )

        if result is CONFIRMED:
            break


async def with_info(
    main_layout: RustLayout,
    info_layout: RustLayout,
    br_type: str,
    br_code: ButtonRequestType,
) -> None:
    await button_request(br_type, br_code, pages=main_layout.page_count())

    while True:
        result = await ctx_wait(main_layout)

        if result is CONFIRMED:
            return
        elif result is INFO:
            info_layout.request_complete_repaint()
            result = await ctx_wait(info_layout)
            assert result is CANCELLED
            main_layout.request_complete_repaint()
            continue

        raise ActionCancelled


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
    info_layout = RustLayout(
        trezorui2.show_spending_details(
            account=None,
            title="FEE INFORMATION",
            fee_rate=fee_rate_amount,
            fee_rate_title="New fee rate:",
        )
    )
    await with_info(fee_layout, info_layout, "modify_fee", ButtonRequestType.SignTx)


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
        title=f"Sign {proto}",
        data=identity,
        description=challenge_visual + "\n" if challenge_visual else "",
        br_type="sign_identity",
        br_code=BR_TYPE_OTHER,
    )


async def confirm_signverify(
    coin: str, message: str, address: str, verify: bool
) -> None:
    if verify:
        title = f"VERIFY {coin} MESSAGE"
        br_type = "verify_message"
    else:
        title = f"SIGN {coin} MESSAGE"
        br_type = "sign_message"

    await confirm_blob(
        br_type,
        title,
        address,
        "Confirm address:",
        br_code=BR_TYPE_OTHER,
    )

    await confirm_blob(
        br_type,
        title,
        message,
        "Confirm message:",
        br_code=BR_TYPE_OTHER,
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
            description="Please enter your passphrase.",
        )
    )


async def request_passphrase_on_device(max_len: int) -> str:
    result = await interact(
        RustLayout(
            trezorui2.request_passphrase(prompt="Enter passphrase", max_len=max_len)
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
        subprompt = "Last attempt"
    else:
        subprompt = f"{attempts_remaining} tries left"

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
    title = "Wipe code mismatch" if is_wipe_code else "PIN mismatch"
    description = "wipe codes" if is_wipe_code else "PINs"
    return await show_error_popup(
        title,
        f"The {description} you entered do not match.",
        button="TRY AGAIN",
    )


async def wipe_code_same_as_pin_popup() -> None:
    await button_request("wipe_code_same_as_pin", code=BR_TYPE_OTHER)
    return await show_error_popup(
        "Invalid wipe code",
        "The wipe code must be different from your PIN.",
        button="TRY AGAIN",
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
                        "Turn on ",
                        (True, description),
                        " protection?\n\n",
                        information,
                    ),
                    verb="TURN ON",
                )
            ),
            br_type,
            br_code,
        )
    )
