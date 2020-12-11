from micropython import const

from trezor import io, loop, res, ui, workflow
from trezor.ui import display

from .button import Button, ButtonClear, ButtonConfirm
from .swipe import SWIPE_HORIZONTAL, SWIPE_LEFT, Swipe

if False:
    from typing import Iterable, List, Optional, Tuple
    from .button import ButtonContent, ButtonStyleStateType

SPACE = res.load(ui.ICON_SPACE)

KEYBOARD_KEYS = (
    ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"),
    (SPACE, "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz", "*#"),
    (SPACE, "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ", "*#"),
    ("_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ';"~', "$^="),
)


def digit_area(i: int) -> ui.Area:
    if i == 9:  # 0-position
        i = 10  # display it in the middle
    return ui.grid(i + 3)  # skip the first line


def render_scrollbar(page: int) -> None:
    BBOX = const(240)
    SIZE = const(8)
    pages = len(KEYBOARD_KEYS)

    padding = 12
    if pages * padding > BBOX:
        padding = BBOX // pages

    x = (BBOX // 2) - (pages // 2) * padding
    Y = const(44)

    for i in range(0, pages):
        if i == page:
            fg = ui.FG
        else:
            fg = ui.DARK_GREY
        ui.display.bar_radius(x + i * padding, Y, SIZE, SIZE, fg, ui.BG, SIZE // 2)


class KeyButton(Button):
    def __init__(
        self, area: ui.Area, content: ButtonContent, keyboard: "PassphraseKeyboard"
    ) -> None:
        self.keyboard = keyboard
        super().__init__(area, content)

    def on_click(self) -> None:
        self.keyboard.on_key_click(self)

    def get_text_content(self) -> str:
        if self.text:
            return self.text
        elif self.icon is SPACE:
            return " "
        else:
            raise TypeError


def key_buttons(
    keys: Iterable[ButtonContent], keyboard: "PassphraseKeyboard"
) -> List[KeyButton]:
    return [KeyButton(digit_area(i), k, keyboard) for i, k in enumerate(keys)]


class Input(Button):
    def __init__(self, area: ui.Area, text: str) -> None:
        super().__init__(area, text)
        self.pending = False
        self.disable()

    def edit(self, text: str, pending: bool) -> None:
        self.text = text
        self.pending = pending
        self.repaint = True

    def render_content(
        self, s: ButtonStyleStateType, ax: int, ay: int, aw: int, ah: int
    ) -> None:
        text_style = s.text_style
        fg_color = s.fg_color
        bg_color = s.bg_color

        p = self.pending  # should we draw the pending marker?
        t = self.text  # input content

        tx = ax + 24  # x-offset of the content
        ty = ay + ah // 2 + 8  # y-offset of the content
        maxlen = const(14)  # maximum text length

        # input content
        if len(t) > maxlen:
            t = "<" + t[-maxlen:]  # too long, align to the right
        width = display.text_width(t, text_style)
        display.text(tx, ty, t, text_style, fg_color, bg_color)

        if p:  # pending marker
            pw = display.text_width(t[-1:], text_style)
            px = tx + width - pw
            display.bar(px, ty + 2, pw + 1, 3, fg_color)
        else:  # cursor
            cx = tx + width + 1
            display.bar(cx, ty - 18, 2, 22, fg_color)

    def on_click(self) -> None:
        pass


class Prompt(ui.Component):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text

    def on_render(self) -> None:
        if self.repaint:
            display.bar(0, 0, ui.WIDTH, 48, ui.BG)
            display.text_center(ui.WIDTH // 2, 32, self.text, ui.BOLD, ui.GREY, ui.BG)
            self.repaint = False


CANCELLED = object()


class PassphraseKeyboard(ui.Layout):
    def __init__(self, prompt: str, max_length: int, page: int = 1) -> None:
        super().__init__()
        self.prompt = Prompt(prompt)
        self.max_length = max_length
        self.page = page

        self.input = Input(ui.grid(0, n_x=1, n_y=6), "")

        self.back = Button(ui.grid(12), res.load(ui.ICON_BACK), ButtonClear)
        self.back.on_click = self.on_back_click  # type: ignore
        self.back.disable()

        self.done = Button(ui.grid(14), res.load(ui.ICON_CONFIRM), ButtonConfirm)
        self.done.on_click = self.on_confirm  # type: ignore

        self.keys = key_buttons(KEYBOARD_KEYS[self.page], self)
        self.pending_button: Optional[KeyButton] = None
        self.pending_index = 0

    def dispatch(self, event: int, x: int, y: int) -> None:
        if self.input.text:
            self.input.dispatch(event, x, y)
        else:
            self.prompt.dispatch(event, x, y)
        self.back.dispatch(event, x, y)
        self.done.dispatch(event, x, y)
        for btn in self.keys:
            btn.dispatch(event, x, y)

        if event == ui.RENDER:
            render_scrollbar(self.page)

    def on_back_click(self) -> None:
        # Backspace was clicked.  If we have any content in the input, let's delete
        # the last character.  Otherwise cancel.
        text = self.input.text
        if text:
            self.edit(text[:-1])
        else:
            self.on_cancel()

    def on_key_click(self, button: KeyButton) -> None:
        # Key button was clicked.  If this button is pending, let's cycle the
        # pending character in input.  If not, let's just append the first
        # character.
        button_text = button.get_text_content()
        if self.pending_button is button:
            index = (self.pending_index + 1) % len(button_text)
            prefix = self.input.text[:-1]
        else:
            index = 0
            prefix = self.input.text
        if len(button_text) > 1:
            self.edit(prefix + button_text[index], button, index)
        else:
            self.edit(prefix + button_text[index])

    def on_timeout(self) -> None:
        # Timeout occurred, let's just reset the pending marker.
        self.edit(self.input.text)

    def edit(self, text: str, button: KeyButton = None, index: int = 0) -> None:
        if len(text) > self.max_length:
            return

        self.pending_button = button
        self.pending_index = index

        # modify the input state
        pending = button is not None
        self.input.edit(text, pending)

        if text:
            self.back.enable()
        else:
            self.back.disable()
            self.prompt.repaint = True

    async def handle_input(self) -> None:
        touch = loop.wait(io.TOUCH)
        timeout = loop.sleep(1000)
        race_touch = loop.race(touch)
        race_timeout = loop.race(touch, timeout)

        while True:
            if self.pending_button is not None:
                race = race_timeout
            else:
                race = race_touch
            result = await race

            if touch in race.finished:
                event, x, y = result
                workflow.idle_timer.touch()
                self.dispatch(event, x, y)
            else:
                self.on_timeout()

    async def handle_paging(self) -> None:
        swipe = await Swipe(SWIPE_HORIZONTAL)
        if swipe == SWIPE_LEFT:
            self.page = (self.page + 1) % len(KEYBOARD_KEYS)
        else:
            self.page = (self.page - 1) % len(KEYBOARD_KEYS)
        self.keys = key_buttons(KEYBOARD_KEYS[self.page], self)
        self.back.repaint = True
        self.done.repaint = True
        self.input.repaint = True
        self.prompt.repaint = True

    def on_cancel(self) -> None:
        raise ui.Result(CANCELLED)

    def on_confirm(self) -> None:
        raise ui.Result(self.input.text)

    def create_tasks(self) -> Tuple[loop.Task, ...]:
        tasks: Tuple[loop.Task, ...] = (
            self.handle_input(),
            self.handle_rendering(),
            self.handle_paging(),
        )

        if __debug__:
            from apps.debug import input_signal

            return tasks + (input_signal(),)
        else:
            return tasks
