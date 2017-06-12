from trezor import ui, res, loop
from trezor.crypto import bip39
from trezor.ui import display
from trezor.ui.button import Button, BTN_CLICKED, CLEAR_BUTTON, CLEAR_BUTTON_ACTIVE

KEY_BUTTON = {
    'bg-color': ui.BLACKISH,
    'fg-color': ui.WHITE,
    'text-style': ui.MONO,
    'border-color': ui.BLACK,
}
KEY_BUTTON_ACTIVE = {
    'bg-color': ui.GREY,
    'fg-color': ui.BLACK,
    'text-style': ui.MONO,
    'border-color': ui.GREY,
}


def cell_area(i, n_x=3, n_y=3, start_x=0, start_y=40, end_x=240, end_y=240 - 48, spacing=0):
    w = (end_x - start_x) // n_x
    h = (end_y - start_y) // n_y
    x = (i % n_x) * w
    y = (i // n_x) * h
    return (x + start_x, y + start_y, w - spacing, h - spacing)


def key_buttons():
    keys = ['abc', 'def', 'ghi', 'jkl', 'mno', 'pqr', 'stu', 'vwx', 'yz']
    # keys = [' ', 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz']
    return [Button(cell_area(i), k,
                   normal_style=KEY_BUTTON,
                   active_style=KEY_BUTTON_ACTIVE) for i, k in enumerate(keys)]


def compute_mask(text):
    mask = 0
    for c in text:
        shift = ord(c) - 97  # ord('a') == 97
        if shift < 0:
            continue
        mask |= 1 << shift
    return mask


class KeyboardMultiTap:

    def __init__(self, content=''):
        self.content = content
        self.sugg_mask = 0xffffffff
        self.sugg_word = None
        self.pending_button = None
        self.pending_index = 0

        self.key_buttons = key_buttons()
        self.sugg_button = Button((5, 5, 240 - 35, 30), '')
        self.bs_button = Button((240 - 35, 5, 30, 30),
                                res.load('trezor/res/pin_close.toig'),
                                normal_style=CLEAR_BUTTON,
                                active_style=CLEAR_BUTTON_ACTIVE)

    def render(self):

        # clear canvas under input line
        display.bar(0, 0, 205, 40, ui.BLACK)

        # input line
        content_width = display.text_width(self.content, ui.BOLD)
        display.text(20, 30, self.content, ui.BOLD, ui.WHITE, ui.BLACK)

        # pending marker
        if self.pending_button is not None:
            pending_width = display.text_width(self.content[-1:], ui.BOLD)
            pending_x = 20 + content_width - pending_width
            display.bar(pending_x, 33, pending_width + 2, 3, ui.WHITE)

        # auto-suggest
        if self.sugg_word is not None:
            sugg_rest = self.sugg_word[len(self.content):]
            sugg_x = 20 + content_width
            display.text(sugg_x, 30, sugg_rest, ui.BOLD, ui.GREY, ui.BLACK)

        # render backspace button
        if self.content:
            self.bs_button.render()
        else:
            display.bar(240 - 48, 0, 48, 42, ui.BLACK)

        # key buttons
        for btn in self.key_buttons:
            btn.render()

    def touch(self, event, pos):
        if self.bs_button.touch(event, pos) == BTN_CLICKED:
            self.content = self.content[:-1]
            self.pending_button = None
            self.pending_index = 0
            self._update_suggestion()
            self._update_buttons()
            return
        if self.sugg_button.touch(event, pos) == BTN_CLICKED and self.sugg_word is not None:
            self.content = self.sugg_word
            self.pending_button = None
            self.pending_index = 0
            self._update_suggestion()
            self._update_buttons()
            return
        for btn in self.key_buttons:
            if btn.touch(event, pos) == BTN_CLICKED:
                if self.pending_button is btn:
                    self.pending_index = (
                        self.pending_index + 1) % len(btn.content)
                    self.content = self.content[:-1]
                    self.content += btn.content[self.pending_index]
                    self._update_suggestion()
                else:
                    self.content += btn.content[0]
                    self._update_suggestion()
                    self.pending_button = btn
                    self.pending_index = 0
                return

    def _update_suggestion(self):
        if self.content:
            self.sugg_word = bip39.find_word(self.content)
            self.sugg_mask = bip39.complete_word(self.content)
        else:
            self.sugg_word = None
            self.sugg_mask = 0xffffffff

    def _update_buttons(self):
        for btn in self.key_buttons:
            if compute_mask(btn.content) & self.sugg_mask:
                btn.enable()
            else:
                btn.disable()

    def __iter__(self):
        timeout = loop.Sleep(1000 * 1000 * 1)
        touch = loop.Select(loop.TOUCH)
        wait = loop.Wait((touch, timeout))
        while True:
            self.render()
            result = yield wait
            if touch in wait.finished:
                event, *pos = result
                self.touch(event, pos)
            else:
                self.pending_button = None
                self.pending_index = 0
                self._update_suggestion()
                self._update_buttons()


def zoom_buttons(keys, upper=False):
    n_x = len(keys)
    if upper:
        keys = keys + keys.upper()
        n_y = 2
    else:
        n_y = 1
    return [Button(cell_area(i, n_x, n_y), key) for i, key in enumerate(keys)]


class KeyboardZooming:

    def __init__(self, content='', uppercase=True):
        self.content = content
        self.uppercase = uppercase

        self.zoom_buttons = None
        self.key_buttons = key_buttons()
        self.bs_button = Button((240 - 35, 5, 30, 30),
                                res.load('trezor/res/pin_close.toig'),
                                normal_style=CLEAR_BUTTON,
                                active_style=CLEAR_BUTTON_ACTIVE)

    def render(self):
        self.render_input()
        if self.zoom_buttons:
            for btn in self.zoom_buttons:
                btn.render()
        else:
            for btn in self.key_buttons:
                btn.render()

    def render_input(self):
        if self.content:
            display.bar(0, 0, 200, 40, ui.BLACK)
        else:
            display.bar(0, 0, 240, 40, ui.BLACK)
        display.text(20, 30, self.content, ui.BOLD, ui.GREY, ui.BLACK)
        if self.content:
            self.bs_button.render()

    def touch(self, event, pos):
        if self.bs_button.touch(event, pos) == BTN_CLICKED:
            self.content = self.content[:-1]
            self.bs_button.taint()
            return
        if self.zoom_buttons:
            return self.touch_zoom(event, pos)
        else:
            return self.touch_keyboard(event, pos)

    def touch_zoom(self, event, pos):
        for btn in self.zoom_buttons:
            if btn.touch(event, pos) == BTN_CLICKED:
                self.content += btn.content
                self.zoom_buttons = None
                for btn in self.key_buttons:
                    btn.taint()
                self.bs_button.taint()
                break

    def touch_keyboard(self, event, pos):
        for btn in self.key_buttons:
            if btn.touch(event, pos) == BTN_CLICKED:
                self.zoom_buttons = zoom_buttons(btn.content, self.uppercase)
                for btn in self.zoom_buttons:
                    btn.taint()
                self.bs_button.taint()
                break

    def __iter__(self):
        timeout = loop.Sleep(1000 * 1000 * 1)
        touch = loop.Select(loop.TOUCH)
        wait = loop.Wait((touch, timeout))
        while True:
            self.render()
            result = yield wait
            if touch in wait.finished:
                event, *pos = result
                self.touch(event, pos)
            elif self.zoom_buttons:
                self.zoom_buttons = None
                for btn in self.key_buttons:
                    btn.taint()


Keyboard = KeyboardMultiTap
