from trezor import io, loop, res, ui, workflow
from trezor.crypto import slip39
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


class KeyButton(Button):
    def __init__(
        self,
        area: ui.Area,
        content: ButtonContent,
        keyboard: "Slip39Keyboard",
        index: int,
    ):
        self.keyboard = keyboard
        self.index = index
        super().__init__(area, content)

    def on_click(self) -> None:
        self.keyboard.on_key_click(self)


class InputButton(Button):
    def __init__(self, area: ui.Area, keyboard: "Slip39Keyboard") -> None:
        super().__init__(area, "")
        self.word = ""
        self.pending_button: Optional[Button] = None
        self.pending_index: Optional[int] = None
        self.keyboard = keyboard
        self.disable()

    def edit(
        self,
        text: str,
        word: str,
        pending_button: Optional[Button],
        pending_index: Optional[int],
    ) -> None:
        self.word = word
        self.text = text
        self.pending_button = pending_button
        self.pending_index = pending_index
        self.repaint = True
        if word:  # confirm button
            self.enable()
            self.normal_style = ButtonMonoConfirm.normal
            self.active_style = ButtonMonoConfirm.active
            self.icon = res.load(ui.ICON_CONFIRM)
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

        if not self.keyboard.is_input_final():
            pending_button = self.pending_button
            pending_index = self.pending_index
            to_display = len(self.text) * "*"
            if pending_button and pending_index is not None:
                to_display = to_display[:-1] + pending_button.text[pending_index]
        else:
            to_display = self.word

        display.text(tx, ty, to_display, text_style, fg_color, bg_color)

        if self.pending_button and not self.keyboard.is_input_final():
            width = display.text_width(to_display, text_style)
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


class Slip39Keyboard(ui.Layout):
    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = Prompt(prompt)

        icon_back = res.load(ui.ICON_BACK)
        self.back = Button(ui.grid(0, n_x=3, n_y=4), icon_back, ButtonClear)
        self.back.on_click = self.on_back_click  # type: ignore

        self.input = InputButton(ui.grid(1, n_x=3, n_y=4, cells_x=2), self)
        self.input.on_click = self.on_input_click  # type: ignore

        self.keys = [
            KeyButton(ui.grid(i + 3, n_y=4), k, self, i + 1)
            for i, k in enumerate(
                ("ab", "cd", "ef", "ghij", "klm", "nopq", "rs", "tuv", "wxyz")
            )
        ]
        self.pending_button: Optional[Button] = None
        self.pending_index = 0
        self.button_sequence = ""
        self.mask = slip39.KEYBOARD_FULL_MASK

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
        self.button_sequence = self.button_sequence[:-1]
        self.edit()

    def on_input_click(self) -> None:
        # Input button was clicked. If the content matches the suggested word,
        # let's confirm it, otherwise just auto-complete.
        result = self.input.word
        if self.is_input_final():
            self.button_sequence = ""
            self.edit()
            self.on_confirm(result)

    def on_key_click(self, btn: KeyButton) -> None:
        # Key button was clicked.  If this button is pending, let's cycle the
        # pending character in input.  If not, let's just append the first
        # character.
        if self.pending_button is btn:
            index = (self.pending_index + 1) % len(btn.text)
        else:
            index = 0
            self.button_sequence += str(btn.index)
        self.edit(btn, index)

    def on_timeout(self) -> None:
        # Timeout occurred. Let's redraw to draw asterisks.
        self.edit()

    def on_confirm(self, word: str) -> None:
        # Word was confirmed by the user.
        raise ui.Result(word)

    def edit(self, button: Button = None, index: int = 0) -> None:
        self.pending_button = button
        self.pending_index = index

        # find the completions
        word = ""
        self.mask = slip39.word_completion_mask(self.button_sequence)
        if self.is_input_final():
            word = slip39.button_sequence_to_word(self.button_sequence)

        # modify the input state
        self.input.edit(
            self.button_sequence, word, self.pending_button, self.pending_index
        )

        # enable or disable key buttons
        for btn in self.keys:
            if self.is_input_final():
                btn.disable()
            elif btn is button or self.check_mask(btn.index):
                btn.enable()
            else:
                btn.disable()

        # invalidate the prompt if we display it next frame
        if not self.input.text:
            self.prompt.repaint = True

    def is_input_final(self) -> bool:
        # returns True if mask has exactly one bit set to 1 or is 0
        return not (self.mask & (self.mask - 1))

    def check_mask(self, index: int) -> bool:
        return bool((1 << (index - 1)) & self.mask)

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
