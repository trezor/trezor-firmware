from trezor import io, loop, res, ui
from trezor.crypto import slip39
from trezor.ui import display
from trezor.ui.button import Button, ButtonClear, ButtonMono, ButtonMonoConfirm


class KeyButton(Button):
    def __init__(self, area, content, keyboard, index):
        self.keyboard = keyboard
        self.index = index
        super().__init__(area, content)

    def on_click(self):
        self.keyboard.on_key_click(self)


class InputButton(Button):
    def __init__(self, area, keyboard):
        super().__init__(area, "")
        self.word = ""
        self.pending_button = None
        self.pending_index = None
        self.icon = None  # rendered icon
        self.keyboard = keyboard
        self.disable()

    def edit(self, content, word, pending_button, pending_index):
        self.word = word
        self.content = content
        self.pending_button = pending_button
        self.pending_index = pending_index
        self.repaint = True
        if word:
            self.enable()
            self.normal_style = ButtonMonoConfirm.normal
            self.active_style = ButtonMonoConfirm.active
            self.icon = ui.ICON_CONFIRM
        else:  # disabled button
            self.disabled_style = ButtonMono.normal
            self.disable()
            self.icon = None

    def render_content(self, s, ax, ay, aw, ah):
        text_style = s.text_style
        fg_color = s.fg_color
        bg_color = s.bg_color

        tx = ax + 16  # x-offset of the content
        ty = ay + ah // 2 + 8  # y-offset of the content

        if not self.keyboard.is_input_final():
            to_display = len(self.content) * "*"
            if self.pending_button:
                to_display = (
                    to_display[:-1] + self.pending_button.content[self.pending_index]
                )
        else:
            to_display = self.word

        display.text(tx, ty, to_display, text_style, fg_color, bg_color)

        if self.pending_button and not self.keyboard.is_input_final():
            width = display.text_width(to_display, text_style)
            pw = display.text_width(self.content[-1:], text_style)
            px = tx + width - pw
            display.bar(px, ty + 2, pw + 1, 3, fg_color)

        if self.icon:
            ix = ax + aw - 16 * 2
            iy = ty - 16
            display.icon(ix, iy, res.load(self.icon), fg_color, bg_color)


class Prompt(ui.Control):
    def __init__(self, prompt):
        self.prompt = prompt
        self.repaint = True

    def on_render(self):
        if self.repaint:
            display.bar(0, 8, ui.WIDTH, 60, ui.BG)
            display.text(20, 40, self.prompt, ui.BOLD, ui.GREY, ui.BG)
            self.repaint = False


class Slip39Keyboard(ui.Layout):
    def __init__(self, prompt):
        self.prompt = Prompt(prompt)

        icon_back = res.load(ui.ICON_BACK)
        self.back = Button(ui.grid(0, n_x=3, n_y=4), icon_back, ButtonClear)
        self.back.on_click = self.on_back_click

        self.input = InputButton(ui.grid(1, n_x=3, n_y=4, cells_x=2), self)
        self.input.on_click = self.on_input_click

        self.keys = [
            KeyButton(ui.grid(i + 3, n_y=4), k, self, i + 1)
            for i, k in enumerate(
                ("ab", "cd", "ef", "ghij", "klm", "nopq", "rs", "tuv", "wxyz")
            )
        ]
        self.pending_button = None
        self.pending_index = 0
        self.button_sequence = ""
        self.mask = slip39.KEYBOARD_FULL_MASK

    def dispatch(self, event: int, x: int, y: int):
        for btn in self.keys:
            btn.dispatch(event, x, y)
        if self.input.content:
            self.input.dispatch(event, x, y)
            self.back.dispatch(event, x, y)
        else:
            self.prompt.dispatch(event, x, y)

    def on_back_click(self):
        # Backspace was clicked, let's delete the last character of input.
        self.button_sequence = self.button_sequence[:-1]
        self.edit()

    def on_input_click(self):
        # Input button was clicked. If the content matches the suggested word,
        # let's confirm it, otherwise just auto-complete.
        result = self.input.word
        if self.is_input_final():
            self.button_sequence = ""
            self.edit()
            self.on_confirm(result)

    def on_key_click(self, btn: KeyButton):
        # Key button was clicked.  If this button is pending, let's cycle the
        # pending character in input.  If not, let's just append the first
        # character.
        if self.pending_button is btn:
            index = (self.pending_index + 1) % len(btn.content)
        else:
            index = 0
            self.button_sequence += str(btn.index)
        self.edit(btn, index)

    def on_timeout(self):
        # Timeout occurred. Let's redraw to draw asterisks.
        self.edit()

    def on_confirm(self, word):
        # Word was confirmed by the user.
        raise ui.Result(word)

    def edit(self, button: KeyButton = None, index: int = 0):
        self.pending_button = button
        self.pending_index = index

        # find the completions
        word = ""
        self.mask = slip39.compute_mask(self.button_sequence)
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
        if not self.input.content:
            self.prompt.repaint = True

    def is_input_final(self) -> bool:
        # returns True if mask has exactly one bit set to 1 or is 0
        return not (self.mask & (self.mask - 1))

    def check_mask(self, index: int) -> bool:
        return bool((1 << (index - 1)) & self.mask)

    async def handle_input(self):
        touch = loop.wait(io.TOUCH)
        timeout = loop.sleep(1000 * 1000 * 1)
        spawn_touch = loop.spawn(touch)
        spawn_timeout = loop.spawn(touch, timeout)

        while True:
            if self.pending_button is not None:
                spawn = spawn_timeout
            else:
                spawn = spawn_touch
            result = await spawn

            if touch in spawn.finished:
                event, x, y = result
                self.dispatch(event, x, y)
            else:
                self.on_timeout()
