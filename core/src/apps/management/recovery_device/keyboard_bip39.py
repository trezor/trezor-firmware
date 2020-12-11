from trezor import io, loop, res, ui, workflow
from trezor.crypto import bip39
from trezor.ui import display
from trezor.ui.components.tt.button import (
    Button,
    ButtonClear,
    ButtonMono,
    ButtonMonoConfirm,
)

if False:
    from typing import Optional, Tuple
    from trezor.ui.components.tt.button import ButtonContent, ButtonStyleStateType


def compute_mask(text: str) -> int:
    mask = 0
    for c in text:
        shift = ord(c) - 97  # ord('a') == 97
        if shift < 0:
            continue
        mask |= 1 << shift
    return mask


class KeyButton(Button):
    def __init__(
        self, area: ui.Area, content: ButtonContent, keyboard: "Bip39Keyboard"
    ):
        self.keyboard = keyboard
        super().__init__(area, content)

    def on_click(self) -> None:
        self.keyboard.on_key_click(self)


class InputButton(Button):
    def __init__(self, area: ui.Area, text: str, word: str) -> None:
        super().__init__(area, text)
        self.word = word
        self.pending = False
        self.disable()

    def edit(self, text: str, word: str, pending: bool) -> None:
        self.word = word
        self.text = text
        self.pending = pending
        self.repaint = True
        if word:
            if text == word:  # confirm button
                self.enable()
                self.normal_style = ButtonMonoConfirm.normal
                self.active_style = ButtonMonoConfirm.active
                self.icon = res.load(ui.ICON_CONFIRM)
            else:  # auto-complete button
                self.enable()
                self.normal_style = ButtonMono.normal
                self.active_style = ButtonMono.active
                self.icon = res.load(ui.ICON_CLICK)
        else:  # disabled button
            self.disabled_style = ButtonMono.disabled
            self.disable()
            self.icon = b""

    def render_content(
        self, s: ButtonStyleStateType, ax: int, ay: int, aw: int, ah: int
    ) -> None:
        text_style = s.text_style
        fg_color = s.fg_color
        bg_color = s.bg_color

        tx = ax + 16  # x-offset of the content
        ty = ay + ah // 2 + 8  # y-offset of the content

        # entered content
        display.text(tx, ty, self.text, text_style, fg_color, bg_color)
        # word suggestion
        suggested_word = self.word[len(self.text) :]
        width = display.text_width(self.text, text_style)
        display.text(tx + width, ty, suggested_word, text_style, ui.GREY, bg_color)

        if self.pending:
            pw = display.text_width(self.text[-1:], text_style)
            px = tx + width - pw
            display.bar(px, ty + 2, pw + 1, 3, fg_color)

        if self.icon:
            ix = ax + aw - 16 * 2
            iy = ty - 16
            display.icon(ix, iy, self.icon, fg_color, bg_color)


class Prompt(ui.Component):
    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt

    def on_render(self) -> None:
        if self.repaint:
            display.bar(0, 8, ui.WIDTH, 60, ui.BG)
            display.text(20, 40, self.prompt, ui.BOLD, ui.GREY, ui.BG)
            self.repaint = False


class Bip39Keyboard(ui.Layout):
    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = Prompt(prompt)

        icon_back = res.load(ui.ICON_BACK)
        self.back = Button(ui.grid(0, n_x=3, n_y=4), icon_back, ButtonClear)
        self.back.on_click = self.on_back_click  # type: ignore

        self.input = InputButton(ui.grid(1, n_x=3, n_y=4, cells_x=2), "", "")
        self.input.on_click = self.on_input_click  # type: ignore

        self.keys = [
            KeyButton(ui.grid(i + 3, n_y=4), k, self)
            for i, k in enumerate(
                ("abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz")
            )
        ]
        self.pending_button: Optional[Button] = None
        self.pending_index = 0

    def dispatch(self, event: int, x: int, y: int) -> None:
        for btn in self.keys:
            btn.dispatch(event, x, y)
        if self.input.text:
            self.input.dispatch(event, x, y)
            self.back.dispatch(event, x, y)
        else:
            self.prompt.dispatch(event, x, y)

    def on_back_click(self) -> None:
        # Backspace was clicked, let's delete the last character of input.
        self.edit(self.input.text[:-1])

    def on_input_click(self) -> None:
        # Input button was clicked.  If the content matches the suggested word,
        # let's confirm it, otherwise just auto-complete.
        text = self.input.text
        word = self.input.word
        if word and word == text:
            self.edit("")
            self.on_confirm(word)
        else:
            self.edit(word)

    def on_key_click(self, btn: Button) -> None:
        # Key button was clicked.  If this button is pending, let's cycle the
        # pending character in input.  If not, let's just append the first
        # character.
        if self.pending_button is btn:
            index = (self.pending_index + 1) % len(btn.text)
            text = self.input.text[:-1] + btn.text[index]
        else:
            index = 0
            text = self.input.text + btn.text[0]
        self.edit(text, btn, index)

    def on_timeout(self) -> None:
        # Timeout occurred.  If we can auto-complete current input, let's just
        # reset the pending marker.  If not, input is invalid, let's backspace
        # the last character.
        if self.input.word:
            self.edit(self.input.text)
        else:
            self.edit(self.input.text[:-1])

    def on_confirm(self, word: str) -> None:
        # Word was confirmed by the user.
        raise ui.Result(word)

    def edit(self, text: str, button: Button = None, index: int = 0) -> None:
        self.pending_button = button
        self.pending_index = index

        # find the completions
        pending = button is not None
        word = bip39.complete_word(text) or ""
        mask = bip39.word_completion_mask(text)

        # modify the input state
        self.input.edit(text, word, pending)

        # enable or disable key buttons
        for btn in self.keys:
            if btn is button or compute_mask(btn.text) & mask:
                btn.enable()
            else:
                btn.disable()

        # invalidate the prompt if we display it next frame
        if not self.input.text:
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

    if __debug__:

        def create_tasks(self) -> Tuple[loop.Task, ...]:
            from apps.debug import input_signal

            return super().create_tasks() + (input_signal(),)
