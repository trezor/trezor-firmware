from typing import TYPE_CHECKING, Sequence

from trezor import io, log, loop, ui, workflow
from trezor.enums import ButtonRequestType
from trezor.utils import DISABLE_ANIMATION
from trezor.wire import ActionCancelled

import trezorui2

from ..common import button_request, interact

if TYPE_CHECKING:
    from typing import Any, NoReturn, Awaitable, Iterable, TypeVar

    from trezor.wire import GenericContext, Context
    from ..common import PropertyType, ExceptionType, ProgressLayout

    T = TypeVar("T")


BR_TYPE_OTHER = ButtonRequestType.Other  # global_import_cache


if __debug__:
    trezorui2.disable_animation(bool(DISABLE_ANIMATION))


class RustLayoutContent:
    """Providing shortcuts to the data returned by layouts.

    Used only in debug mode.
    """

    # How will some information be identified in the content
    TITLE_TAG = " **TITLE** "
    CONTENT_TAG = " **CONTENT** "
    BTN_TAG = " **BTN** "
    EMPTY_BTN = "---"
    NEXT_BTN = "Next"
    PREV_BTN = "Prev"

    def __init__(self, raw_content: list[str]) -> None:
        self.raw_content = raw_content
        self.str_content = " ".join(raw_content).replace("  ", " ")
        print("str_content", self.str_content)
        print(60 * "-")
        print("active_page:", self.active_page())
        print("page_count:", self.page_count())
        print("flow_page:", self.flow_page())
        print("flow_page_count:", self.flow_page_count())
        print("can_go_next:", self.can_go_next())
        print("get_next_button:", self.get_next_button())
        print(30 * "/")
        print(self.visible_screen())

    def active_page(self) -> int:
        """Current index of the active page. Should always be there."""
        return self.kw_pair_int("active_page") or 0

    def page_count(self) -> int:
        """Overall number of pages in this screen. Should always be there."""
        return self.kw_pair_int("page_count") or 1

    def in_flow(self) -> bool:
        """Whether we are in flow."""
        return self.flow_page() is not None

    def flow_page(self) -> int | None:
        """When in flow, on which page we are. Missing when not in flow."""
        return self.kw_pair_int("flow_page")

    def flow_page_count(self) -> int | None:
        """When in flow, how many unique pages it has. Missing when not in flow."""
        return self.kw_pair_int("flow_page_count")

    def can_go_next(self) -> bool:
        """Checking if there is a next page."""
        return self.get_next_button() is not None

    def get_next_button(self) -> str | None:
        """Position of the next button, if any."""
        return self._get_btn_by_action(self.NEXT_BTN)

    def get_prev_button(self) -> str | None:
        """Position of the previous button, if any."""
        return self._get_btn_by_action(self.PREV_BTN)

    def _get_btn_by_action(self, btn_action: str) -> str | None:
        """Position of button described by some action. None if not found."""
        btn_names = ("left", "middle", "right")
        for index, action in enumerate(self.button_actions()):
            if action == btn_action:
                return btn_names[index]

        return None

    def visible_screen(self) -> str:
        """Getting all the visible screen content - header, content, buttons."""
        title_separator = f"\n{20*'-'}\n"
        btn_separator = f"\n{20*'*'}\n"

        visible = ""
        if self.title():
            visible += self.title()
            visible += title_separator
        visible += self.content()
        visible += btn_separator
        visible += ", ".join(self.buttons())

        return visible

    def title(self) -> str:
        """Getting text that is displayed as a title."""
        # there could be multiple of those - title and subtitle for example
        title_strings = self._get_strings_inside_tag(self.str_content, self.TITLE_TAG)
        return "\n".join(title_strings)

    def content(self) -> str:
        """Getting text that is displayed in the main part of the screen."""
        content_strings = self._get_strings_inside_tag(
            self.str_content, self.CONTENT_TAG
        )
        # there are some unwanted spaces
        strings = [
            s.replace(" \n ", "\n").replace("\n ", "\n").lstrip()
            for s in content_strings
        ]
        return "\n".join(strings)

    def buttons(self) -> tuple[str, str, str]:
        """Getting content and actions for all three buttons."""
        contents = self.buttons_content()
        actions = self.button_actions()
        return tuple(f"{contents[i]} [{actions[i]}]" for i in range(3))

    def buttons_content(self) -> tuple[str, str, str]:
        """Getting visual details for all three buttons. They should always be there."""
        if self.BTN_TAG not in self.str_content:
            return ("None", "None", "None")
        btns = self._get_strings_inside_tag(self.str_content, self.BTN_TAG)
        assert len(btns) == 3
        return btns[0], btns[1], btns[2]

    def button_actions(self) -> tuple[str, str, str]:
        """Getting actions for all three buttons. They should always be there."""
        if "_action" not in self.str_content:
            return ("None", "None", "None")
        action_ids = ("left_action", "middle_action", "right_action")
        assert len(action_ids) == 3
        return tuple(self.kw_pair_compulsory(action) for action in action_ids)

    def kw_pair_int(self, key: str) -> int | None:
        """Getting the value of a key-value pair as an integer. None if missing."""
        val = self.kw_pair(key)
        if val is None:
            return None
        return int(val)

    def kw_pair_compulsory(self, key: str) -> str:
        """Getting value of a key that cannot be missing."""
        val = self.kw_pair(key)
        assert val is not None
        return val

    def kw_pair(self, key: str) -> str | None:
        """Getting the value of a key-value pair. None if missing."""
        # Pairs are sent in this format in the list:
        # [..., "key", "::", "value", ...]
        for key_index, item in enumerate(self.raw_content):
            if item == key:
                if self.raw_content[key_index + 1] == "::":
                    return self.raw_content[key_index + 2]

        return None

    @staticmethod
    def _get_strings_inside_tag(string: str, tag: str) -> list[str]:
        """Getting all strings that are inside two same tags."""
        parts = string.split(tag)
        if len(parts) == 1:
            return []
        else:
            # returning all odd indexes in the list
            return parts[1::2]


class RustLayout(ui.Layout):
    # pylint: disable=super-init-not-called
    def __init__(self, layout: Any):
        self.layout = layout
        self.timer = loop.Timer()

    def set_timer(self, token: int, deadline: int) -> None:
        self.timer.schedule(deadline, token)

    def request_complete_repaint(self) -> None:
        msg = self.layout.request_complete_repaint()
        assert msg is None

    def _paint(self) -> None:
        import storage.cache as storage_cache

        painted = self.layout.paint()
        if storage_cache.homescreen_shown is not None and painted:
            storage_cache.homescreen_shown = None

    def _first_paint(self) -> None:
        # Clear the screen of any leftovers.
        ui.backlight_fade(ui.style.BACKLIGHT_DIM)
        ui.display.clear()
        self._paint()

        if __debug__ and self.should_notify_layout_change:
            from apps.debug import notify_layout_change

            # notify about change and do not notify again until next await.
            # (handle_rendering might be called multiple times in a single await,
            # because of the endless loop in __iter__)
            self.should_notify_layout_change = False
            notify_layout_change(self)

        # Turn the brightness on again.
        ui.backlight_fade(self.BACKLIGHT_LEVEL)

    if __debug__:
        from trezor.enums import DebugPhysicalButton

        BTN_MAP = {
            "left": DebugPhysicalButton.LEFT_BTN,
            "middle": DebugPhysicalButton.MIDDLE_BTN,
            "right": DebugPhysicalButton.RIGHT_BTN,
        }

        def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:  # type: ignore [obscured-by-same-name]
            from apps.debug import confirm_signal, input_signal

            return (
                self.handle_input_and_rendering(),
                self.handle_timers(),
                self.handle_swipe(),
                self.handle_button_click(),
                confirm_signal(),
                input_signal(),
            )

        def read_content(self) -> list[str]:
            """Gets the visible content of the screen."""
            self._place_layout()
            return self._content_obj().visible_screen().split("\n")

        def _place_layout(self) -> None:
            """It is necessary to place the layout to get data about its screen content."""
            self.layout.place()

        def _read_content_raw(self) -> list[str]:
            """Reads raw trace content from Rust layout."""
            result: list[str] = []

            def callback(*args: str):
                for arg in args:
                    result.append(str(arg))

            self.layout.trace(callback)
            return result

        def _content_obj(self) -> RustLayoutContent:
            """Gets object with user-friendly methods on Rust layout content."""
            return RustLayoutContent(self._read_content_raw())

        def _press_left(self) -> Any:
            """Triggers left button press."""
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_LEFT)
            return self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_LEFT)

        def _press_right(self) -> Any:
            """Triggers right button press."""
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_RIGHT)
            return self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_RIGHT)

        def _press_middle(self) -> Any:
            """Triggers middle button press."""
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_LEFT)
            self.layout.button_event(io.BUTTON_PRESSED, io.BUTTON_RIGHT)
            self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_LEFT)
            return self.layout.button_event(io.BUTTON_RELEASED, io.BUTTON_RIGHT)

        def _press_button(self, btn_to_press: DebugPhysicalButton) -> Any:
            from trezor.enums import DebugPhysicalButton
            from apps.debug import notify_layout_change

            if btn_to_press == DebugPhysicalButton.LEFT_BTN:
                msg = self._press_left()
            elif btn_to_press == DebugPhysicalButton.MIDDLE_BTN:
                msg = self._press_middle()
            elif btn_to_press == DebugPhysicalButton.RIGHT_BTN:
                msg = self._press_right()
            else:
                raise Exception(f"Unknown button: {btn_to_press}")

            self.layout.paint()
            if msg is not None:
                raise ui.Result(msg)

            ui.refresh()  # so that a screenshot is taken
            notify_layout_change(self)

        def _swipe(self, direction: int) -> None:
            """Triggers swipe in the given direction.

            Only `UP` and `DOWN` directions are supported.
            """
            from trezor.ui import (
                SWIPE_UP,
                SWIPE_DOWN,
            )

            content_obj = self._content_obj()

            if direction == SWIPE_UP:
                btn_to_press = content_obj.get_next_button()
            elif direction == SWIPE_DOWN:
                btn_to_press = content_obj.get_prev_button()
            else:
                raise Exception(f"Unsupported direction: {direction}")

            assert btn_to_press is not None
            self._press_button(self.BTN_MAP[btn_to_press])

        async def handle_swipe(self) -> None:
            """Enables pagination through the current page/flow page.

            Waits for `swipe_signal` and carries it out.
            """
            from apps.debug import swipe_signal
            from trezor.ui import SWIPE_ALL_THE_WAY_UP, SWIPE_UP

            while True:
                direction = await swipe_signal()

                if direction == SWIPE_ALL_THE_WAY_UP:
                    # Going as far as possible
                    while self._content_obj().can_go_next():
                        self._swipe(SWIPE_UP)
                else:
                    self._swipe(direction)

        async def handle_button_click(self) -> None:
            """Enables clicking arbitrary of the three buttons.

            Waits for `model_r_btn_signal` and carries it out.
            """
            from apps.debug import model_r_btn_signal

            while True:
                btn = await model_r_btn_signal()
                self._press_button(btn)

        def page_count(self) -> int:
            """How many paginated pages current screen has."""
            # TODO: leave it debug-only or use always?
            self._place_layout()
            return self._content_obj().page_count()

        def in_unknown_flow(self) -> bool:
            """Whether we are in a longer flow where we cannot (easily)
            beforehand say how much pages it will have.
            """
            self._place_layout()
            return self._content_obj().in_flow()

    else:

        def create_tasks(self) -> tuple[loop.Task, ...]:
            return self.handle_timers(), self.handle_input_and_rendering()

    def _before_render(self) -> None:
        # Clear the screen of any leftovers.
        ui.backlight_fade(ui.style.BACKLIGHT_DIM)
        ui.display.clear()

        if __debug__ and self.should_notify_layout_change:
            from apps.debug import notify_layout_change

            # notify about change and do not notify again until next await.
            # (handle_rendering might be called multiple times in a single await,
            # because of the endless loop in __iter__)
            self.should_notify_layout_change = False
            notify_layout_change(self)

        # Turn the brightness on again.
        ui.backlight_fade(self.BACKLIGHT_LEVEL)

    def handle_input_and_rendering(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        button = loop.wait(io.BUTTON)
        self._before_render()
        ui.display.clear()
        self.layout.attach_timer_fn(self.set_timer)
        self.layout.paint()
        ui.refresh()
        while True:
            if __debug__:
                # Printing debugging info, just temporary
                RustLayoutContent(self._read_content_raw())
            # Using `yield` instead of `await` to avoid allocations.
            event, button_num = yield button
            workflow.idle_timer.touch()
            msg = None
            if event in (io.BUTTON_PRESSED, io.BUTTON_RELEASED):
                msg = self.layout.button_event(event, button_num)
            if msg is not None:
                raise ui.Result(msg)
            self.layout.paint()
            ui.refresh()

    def handle_timers(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        while True:
            # Using `yield` instead of `await` to avoid allocations.
            token = yield self.timer
            msg = self.layout.timer(token)
            if msg is not None:
                raise ui.Result(msg)
            self.layout.paint()
            ui.refresh()


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
    verb_cancel: str | bytes | None = "",
    hold: bool = False,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> Any:
    return await confirm_action(
        ctx=ctx,
        br_type=br_type,
        br_code=br_code,
        title=title.upper(),
        action=data,
        description=description,
        verb=verb,
        verb_cancel=verb_cancel,
        hold=hold,
        reverse=True,
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

    return result is trezorui2.CONFIRMED


async def raise_if_cancelled(a: Awaitable[T], exc: Any = ActionCancelled) -> T:
    result = await a
    if result is trezorui2.CANCELLED:
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
    verb_cancel: str | None = None,
    hold: bool = False,
    hold_danger: bool = False,
    reverse: bool = False,
    exc: ExceptionType = ActionCancelled,
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    if verb_cancel is not None:
        verb_cancel = verb_cancel.upper()

    # TEMPORARY: when the action targets PIN, it gets handled differently
    if br_type == "set_pin":
        assert action is not None
        return await pin_confirm_action(ctx, br_type, action)

    if description is not None and description_param is not None:
        description = description.format(description_param)

    # Making the button text UPPERCASE, so it is better readable
    if isinstance(verb, str):
        verb = verb.upper()
    if isinstance(verb_cancel, str):
        verb_cancel = verb_cancel.upper()

    await raise_if_cancelled(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_action(
                    title=title.upper(),
                    action=action,
                    description=description,
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


async def confirm_reset_device(
    ctx: GenericContext,
    prompt: str,
    recovery: bool = False,
    show_tutorial: bool = True,
) -> None:
    # Showing the tutorial, as this is the entry point of
    # both the creation of new wallet and recovery of existing seed
    # - the first user interactions with Trezor.
    # (it is also special for model R, so not having to clutter the
    # common code)

    if show_tutorial:
        await tutorial(ctx)

    to_show = "By continuing you agree to our terms and conditions.\nMore info at trezor.io/tos."
    if not recovery:
        to_show += "\nUse you backup to recover your wallet."

    return await _placeholder_confirm(
        ctx,
        "recover_device" if recovery else "setup_device",
        "WALLET RECOVERY" if recovery else "WALLET BACKUP",
        description=to_show,
        br_code=ButtonRequestType.ProtectCall
        if recovery
        else ButtonRequestType.ResetDevice,
    )


# TODO cleanup @ redesign
async def confirm_backup(ctx: GenericContext) -> bool:
    if await get_bool(
        ctx,
        "backup_device",
        "SUCCESS",
        "New wallet created successfully!\nYou should back up your new wallet right now.",
        verb="BACK UP",
        verb_cancel="SKIP",
        br_code=ButtonRequestType.ResetDevice,
    ):
        return True

    confirmed = await get_bool(
        ctx,
        "backup_device",
        "WARNING",
        "Are you sure you want to skip the backup?\n",
        "You can back up your Trezor once, at any time.",
        verb="BACK UP",
        verb_cancel="SKIP",
        br_code=ButtonRequestType.ResetDevice,
    )
    return confirmed


async def confirm_path_warning(
    ctx: GenericContext, path: str, path_type: str = "Path"
) -> None:
    return await _placeholder_confirm(
        ctx,
        "path_warning",
        "CONFIRM PATH",
        f"{path_type}\n{path} is unknown.\nAre you sure?",
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


def _show_xpub(xpub: str, title: str, cancel: str | None) -> ui.Layout:
    content = RustLayout(
        trezorui2.confirm_action(
            title=title.upper(),
            action="",
            description=xpub,
            verb="CONFIRM",
            verb_cancel=cancel,
        )
    )
    return content


async def show_xpub(ctx: GenericContext, xpub: str, title: str) -> None:
    await raise_if_cancelled(
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
    case_sensitive: bool = True,
    address_qr: str | None = None,
    title: str | None = None,
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
    address_extra: str | None = None,
    title_qr: str | None = None,
    derivation_path: str | None = None,
    account: str | None = None,
) -> None:
    account = account or "Unknown"
    derivation_path = derivation_path or "Unknown"
    title = title or "Receive address"

    await raise_if_cancelled(
        interact(
            ctx,
            RustLayout(
                trezorui2.show_receive_address(
                    title=title.upper(),
                    address=address,
                    address_qr=address if address_qr is None else address_qr,
                    account=account,
                    derivation_path=derivation_path,
                    case_sensitive=case_sensitive,
                )
            ),
            "show_address",
            ButtonRequestType.Address,
        )
    )

    # TODO: support showing multisig xpubs?
    # TODO: send button requests in the flow above?


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
    red: bool = False,
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
        subheader or "Warning",
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
    return _show_modal(
        ctx,
        br_type,
        "Success",
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
    index: int | None = None,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> None:
    address_title = "RECIPIENT" if index is None else f"RECIPIENT #{index + 1}"
    amount_title = "AMOUNT" if index is None else f"AMOUNT #{index + 1}"
    await raise_if_cancelled(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_output_r(
                    address=address,
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
        f"{amount} to\n{recipient_name}\n{memos_str}",
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
    return await get_bool(
        ctx=ctx,
        title=title.upper(),
        data=button_text,
        br_type=br_type,
        br_code=br_code,
    )


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
    await _placeholder_confirm(
        ctx=ctx,
        br_type=br_type,
        title=title.upper(),
        data=str(data),
        description=description,
        br_code=br_code,
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
        ctx=ctx,
        br_type=br_type,
        title=title.upper(),
        data=address,
        description=description,
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
        ctx=ctx,
        br_type=br_type,
        title=title,
        data=data,
        description=description,
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
    return _placeholder_confirm(
        ctx=ctx,
        br_type=br_type,
        title=title.upper(),
        data=amount,
        description=description,
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
            return (prop[0], prop[1], False)

    await raise_if_cancelled(
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

    return _placeholder_confirm(
        ctx=ctx,
        br_type=br_type,
        title=title.upper(),
        data=value,
        description=description,
        br_code=br_code,
    )


async def confirm_total(
    ctx: GenericContext,
    total_amount: str,
    fee_amount: str,
    fee_rate_amount: str | None = None,
    total_label: str = "Total amount",
    fee_label: str = "Including fee",
    br_type: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    await raise_if_cancelled(
        interact(
            ctx,
            RustLayout(
                trezorui2.confirm_total_r(
                    total_amount=total_amount,
                    fee_amount=fee_amount,
                    fee_rate_amount=fee_rate_amount,
                    total_label=total_label.upper(),
                    fee_label=fee_label.upper(),
                )
            ),
            br_type,
            br_code,
        )
    )


async def confirm_joint_total(
    ctx: GenericContext, spending_amount: str, total_amount: str
) -> None:
    await _placeholder_confirm(
        ctx,
        "confirm_joint_total",
        "JOINT TRANSACTION",
        f"You are contributing:\n{spending_amount}\nto the total amount:\n{total_amount}",
        br_code=ButtonRequestType.SignTx,
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
        content.format(param),
        hold=hold,
        br_code=br_code,
    )


async def confirm_replacement(ctx: GenericContext, description: str, txid: str) -> None:
    await _placeholder_confirm(
        ctx,
        "confirm_replacement",
        description.upper(),
        f"Confirm transaction ID:\n{txid}",
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_modify_output(
    ctx: GenericContext,
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    text = f"Address:\n{address}\n\n"
    if sign < 0:
        text += f"Decrease amount by:\n{amount_change}\n\n"
    else:
        text += f"Increase amount by:\n{amount_change}\n\n"
    text += f"New amount:\n{amount_new}"

    await _placeholder_confirm(
        ctx,
        "modify_output",
        "MODIFY AMOUNT",
        text,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_modify_fee(
    ctx: GenericContext,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None = None,
) -> None:
    text = ""
    if sign == 0:
        text += "Your fee did not change.\n"
    else:
        if sign < 0:
            text += "Decrease your fee by:\n"
        else:
            text += "Increase your fee by:\n"
        text += f"{user_fee_change}\n"
    text += f"Transaction fee:\n{total_fee_new}"
    if fee_rate_amount is not None:
        text += "\n" + fee_rate_amount

    await _placeholder_confirm(
        ctx,
        "modify_fee",
        "MODIFY FEE",
        text,
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_coinjoin(
    ctx: GenericContext, max_rounds: int, max_fee_per_vbyte: str
) -> None:
    await _placeholder_confirm(
        ctx,
        "coinjoin_final",
        "AUTHORIZE COINJOIN",
        f"Maximum rounds: {max_rounds}\n\nMaximum mining fee:\n{max_fee_per_vbyte}",
        br_code=BR_TYPE_OTHER,
    )


def show_coinjoin() -> None:
    log.error(__name__, "show_coinjoin not implemented")


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

    await _placeholder_confirm(
        ctx=ctx,
        br_type=br_type,
        title=header.upper(),
        data=f"Confirm address:\n{address}",
        br_code=BR_TYPE_OTHER,
    )

    await _placeholder_confirm(
        ctx,
        br_type,
        header.upper(),
        f"Confirm message:\n{message}",
        br_code=BR_TYPE_OTHER,
    )


async def show_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    timeout_ms: int = 3000,
) -> None:
    if subtitle:
        title += f"\n{subtitle}"
    await RustLayout(
        trezorui2.show_info(
            title=title,
            description=description.format(description_param),
            time_ms=timeout_ms,
        )
    )


def request_passphrase_on_host() -> None:
    draw_simple(
        trezorui2.show_info(
            title="",
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
                prompt="Enter passphrase",
                max_len=max_len,
            )
        )
    )
    if result is trezorui2.CANCELLED:
        raise ActionCancelled("Passphrase entry cancelled")

    assert isinstance(result, str)
    return result


async def request_pin_on_device(
    ctx: GenericContext,
    prompt: str,
    attempts_remaining: int | None,
    allow_cancel: bool,
) -> str:
    from trezor import wire

    if attempts_remaining is None:
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
        )
    )

    while True:
        result = await ctx.wait(dialog)
        if result is trezorui2.CANCELLED:
            raise wire.PinCancelled
        assert isinstance(result, str)
        return result


async def confirm_reenter_pin(
    ctx: GenericContext,
    br_type: str = "set_pin",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    return await confirm_action(
        ctx,
        br_type,
        "CHECK PIN",
        "Please re-enter to confirm.",
        verb="BEGIN",
        br_code=br_code,
    )


async def pin_mismatch(
    ctx: GenericContext,
    br_type: str = "set_pin",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    return await confirm_action(
        ctx,
        br_type,
        "PIN MISMATCH",
        "The PINs you entered do not match.\nPlease try again.",
        verb="TRY AGAIN",
        verb_cancel=None,
        br_code=br_code,
    )


async def confirm_pin_action(
    ctx: GenericContext,
    br_type: str,
    title: str,
    action: str | None,
    description: str | None = "Do you really want to",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    return await confirm_action(
        ctx,
        br_type,
        title,
        f"{description} {action}",
        br_code=br_code,
    )


async def confirm_set_new_pin(
    ctx: GenericContext,
    br_type: str,
    title: str,
    action: str,
    information: list[str],
    description: str = "Do you want to",
    br_code: ButtonRequestType = BR_TYPE_OTHER,
) -> None:
    await confirm_action(
        ctx,
        br_type,
        title,
        description=f"{description} {action}",
        verb="ENABLE",
        br_code=br_code,
    )

    # TODO: this is a hack to put the next info on new screen in case of wipe code
    # TODO: there should be a possibility to give a list of strings and each of them
    # would be rendered on a new screen
    if len(information) == 1:
        information.append("\n")

    information.append(
        "Position of individual numbers will change between entries for more security."
    )
    return await confirm_action(
        ctx,
        br_type,
        title="",
        description="\n".join(information),
        verb="HOLD TO BEGIN",
        hold=True,
        br_code=br_code,
    )


class RustProgress:
    def __init__(
        self,
        title: str,
        description: str | None = None,
        indeterminate: bool = False,
    ):
        self.layout: Any = trezorui2.show_progress(
            title=title.upper(),
            indeterminate=indeterminate,
            description=description or "",
        )
        ui.backlight_fade(ui.style.BACKLIGHT_DIM)
        ui.display.clear()
        self.layout.attach_timer_fn(self.set_timer)
        self.layout.paint()
        ui.backlight_fade(ui.style.BACKLIGHT_NORMAL)

    def set_timer(self, token: int, deadline: int) -> None:
        raise RuntimeError  # progress layouts should not set timers

    def report(self, value: int, description: str | None = None):
        msg = self.layout.progress_event(value, description or "")
        assert msg is None
        self.layout.paint()
        ui.refresh()


def progress(message: str = "PLEASE WAIT") -> ProgressLayout:
    return RustProgress(message.upper())


def bitcoin_progress(message: str) -> ProgressLayout:
    return RustProgress(message.upper())


def pin_progress(message: str, description: str) -> ProgressLayout:
    return RustProgress(message.upper(), description=description)


def monero_keyimage_sync_progress() -> ProgressLayout:
    return RustProgress("SYNCING")


def monero_live_refresh_progress() -> ProgressLayout:
    return RustProgress("REFRESHING", description="", indeterminate=True)


def monero_transaction_progress_inner() -> ProgressLayout:
    return RustProgress("SIGNING TRANSACTION", description="")
