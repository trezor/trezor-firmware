from trezor import io, loop, res, ui
from trezor.crypto import bip39
from trezor.ui import display
from trezor.ui.button import Button, ButtonClear, ButtonMono, ButtonMonoConfirm


def compute_mask(text: str) -> int:
    mask = 0
    for c in text:
        shift = ord(c) - 97  # ord('a') == 97
        if shift < 0:
            continue
        mask |= 1 << shift
    return mask


class KeyButton(Button):
    def __init__(self, area, content, keyboard):
        self.keyboard = keyboard
        super().__init__(area, content)

    def on_click(self):
        self.keyboard.on_key_click(self)


class InputButton(Button):
    def __init__(self, area, content, word):
        super().__init__(area, content)
        self.word = word
        self.pending = False  # should we draw the pending marker?
        self.icon = None  # rendered icon
        self.disable()

    def edit(self, content, word, pending):
        self.word = word
        self.content = content
        self.pending = pending
        self.repaint = True
        if word:
            if content == word:  # confirm button
                self.enable()
                self.normal_style = ButtonMonoConfirm.normal
                self.active_style = ButtonMonoConfirm.active
                self.icon = ui.ICON_CONFIRM
            else:  # auto-complete button
                self.enable()
                self.normal_style = ButtonMono.normal
                self.active_style = ButtonMono.active
                self.icon = ui.ICON_CLICK
        else:  # disabled button
            self.disabled_style = ButtonMono.disabled
            self.disable()
            self.icon = None

    def render_content(self, s, ax, ay, aw, ah):
        text_style = s.text_style
        fg_color = s.fg_color
        bg_color = s.bg_color

        tx = ax + 24  # x-offset of the content
        ty = ay + ah // 2 + 8  # y-offset of the content

        # entered content
        display.text(tx, ty, self.content, text_style, fg_color, bg_color)
        # word suggestion
        suggested_word = self.word[len(self.content) :]
        width = display.text_width(self.content, text_style)
        display.text(tx + width, ty, suggested_word, text_style, ui.GREY, bg_color)

        if self.pending:
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


class MnemonicKeyboard(ui.Layout):
    def __init__(self, prompt):
        self.prompt = Prompt(prompt)

        icon_back = res.load(ui.ICON_BACK)
        self.back = Button(ui.grid(0, n_x=4, n_y=4), icon_back, ButtonClear)
        self.back.on_click = self.on_back_click

        self.input = InputButton(ui.grid(1, n_x=4, n_y=4, cells_x=3), "", "")
        self.input.on_click = self.on_input_click

        self.keys = [
            KeyButton(ui.grid(i + 3, n_y=4), k, self)
            for i, k in enumerate(
                ("abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz")
            )
        ]
        self.pending_button = None
        self.pending_index = 0

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
        self.edit(self.input.content[:-1])

    def on_input_click(self):
        # Input button was clicked.  If the content matches the suggested word,
        # let's confirm it, otherwise just auto-complete.
        content = self.input.content
        word = self.input.word
        if word and word == content:
            self.edit("")
            self.on_confirm(word)
        else:
            self.edit(word)

    def on_key_click(self, btn: Button):
        # Key button was clicked.  If this button is pending, let's cycle the
        # pending character in input.  If not, let's just append the first
        # character.
        if self.pending_button is btn:
            index = (self.pending_index + 1) % len(btn.content)
            content = self.input.content[:-1] + btn.content[index]
        else:
            index = 0
            content = self.input.content + btn.content[0]
        self.edit(content, btn, index)

    def on_timeout(self):
        # Timeout occurred.  If we can auto-complete current input, let's just
        # reset the pending marker.  If not, input is invalid, let's backspace
        # the last character.
        if self.input.word:
            self.edit(self.input.content)
        else:
            self.edit(self.input.content[:-1])

    def on_confirm(self, word):
        # Word was confirmed by the user.
        raise ui.Result(word)

    def edit(self, content: str, button: KeyButton = None, index: int = 0):
        self.pending_button = button
        self.pending_index = index

        # find the completions
        pending = button is not None
        word = bip39.find_word(content) or ""
        mask = bip39.complete_word(content)

        # modify the input state
        self.input.edit(content, word, pending)

        # enable or disable key buttons
        for btn in self.keys:
            if btn is button or compute_mask(btn.content) & mask:
                btn.enable()
            else:
                btn.disable()

        # invalidate the prompt if we display it next frame
        if not self.input.content:
            self.prompt.repaint = True

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
