from trezor import ui, res, loop, io
from trezor.crypto import bip39
from trezor.ui import display
from trezor.ui.button import Button, BTN_CLICKED, ICON
from .swipe import Swipe, SWIPE_LEFT, SWIPE_RIGHT, SWIPE_HORIZONTAL

KEYBOARD = {
    '0': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    '1': ['_', 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz', '*#'],
    '2': ['_', 'ABC', 'DEF', 'GHI', 'JKL', 'MNO', 'PQRS', 'TUV', 'WXYZ', '*#'],
    '3': ['_', '.', '/', '!', '+', '-', '?', ',', ';', '$']
}

def key_buttons():
    keys = ['abc', 'def', 'ghi', 'jkl', 'mno', 'pqr', 'stu', 'vwx', 'yz']
    return [
        Button(ui.grid(i + 3, n_y=4), k, style=ui.BTN_KEY)
        for i, k in enumerate(keys)
    ]

def render_scrollbar(page):
    bbox = const(240)
    size = const(8)
    padding = 12
    page_count = len(KEYBOARD)

    if page_count * padding > bbox:
        padding = bbox // page_count

    x = (bbox // 2) - (page_count // 2) * padding
    y = 44

    for i in range(0, page_count):
        if i != page:
            ui.display.bar_radius(x + i * padding, y, size,
                                  size, ui.DARK_GREY, ui.BG, size // 2)
    ui.display.bar_radius(x + page * padding, y, size,
                          size, ui.FG, ui.BG, size // 2)

def compute_mask(text: str) -> int:
    mask = 0
    for c in text:
        shift = ord(c) - 97  # ord('a') == 97
        if shift < 0:
            continue
        mask |= 1 << shift
    return mask

def digit_area(i):
    if i == 9:  # 0-position
        i = 10  # display it in the middle
    return ui.grid(i + 3)  # skip the first line

def generate_keyboard(index):
    digits = list(range(0, 10))  # 0-9
    return digits

class Input(Button):
    def __init__(self, area: tuple, content: str='', word: str=''):
        super().__init__(area, content)
        self.word = word
        self.icon = None
        self.pending = False

    def edit(self, content: str, word: str, pending: bool):
        self.word = word
        self.content = content
        self.pending = pending
        self.taint()
        if content == word:  # confirm button
            self.enable()
            self.normal_style = ui.BTN_CONFIRM['normal']
            self.active_style = ui.BTN_CONFIRM['active']
            self.icon = ui.ICON_CONFIRM
        elif word:  # auto-complete button
            self.enable()
            self.normal_style = ui.BTN_KEY['normal']
            self.active_style = ui.BTN_KEY['active']
            self.icon = ui.ICON_CLICK
        else:  # disabled button
            self.disable()
            self.icon = None

    def render_content(self, s, ax, ay, aw, ah):
        text_style = s['text-style']
        fg_color = s['fg-color']
        bg_color = s['bg-color']

        p = self.pending  # should we draw the pending marker?
        t = self.content  # input content
        w = self.word[len(t):]  # suggested word
        i = self.icon  # rendered icon

        tx = ax + 24  # x-offset of the content
        ty = ay + ah // 2 + 8  # y-offset of the content

        # input content and the suggested word
        display.text(tx, ty, t, text_style, fg_color, bg_color)
        width = display.text_width(t, text_style)
        display.text(tx + width, ty, w, text_style, ui.GREY, bg_color)

        if p:  # pending marker
            pw = display.text_width(t[-1:], text_style)
            px = tx + width - pw
            display.bar(px, ty + 2, pw + 1, 3, fg_color)

        if i:  # icon
            ix = ax + aw - ICON * 2
            iy = ty - ICON
            display.icon(ix, iy, res.load(i), fg_color, bg_color)

class PassphraseKeyboard(ui.Widget):
    def __init__(self, label):
        self.label = label
        self.passphrase = ''
        self.index = 1
        self.keyboard_type = 1
        self.keys = KEYBOARD[str(self.keyboard_type)]

        self.key_buttons = [Button(digit_area(i), d)
                            for i, d in enumerate(self.keys)]
        self.onchange = None

    def render(self):
        # clear canvas under input line
        display.bar(0, 0, 240, 45, ui.BG)

        # input line with a header
        header = self.passphrase if self.passphrase else self.label
        display.text_center(120, 32, header, ui.BOLD, ui.GREY, ui.BG)
        render_scrollbar(self.keyboard_type)
        # pin matrix buttons
        for btn in self.key_buttons:
            btn.render()

    def touch(self, event, pos):
        for btn in self.key_buttons:
            if btn.touch(event, pos) == BTN_CLICKED:
                self.change(self.passphrase + btn.content)
                break

    def change(self, passphrase):
        self.passphrase = passphrase
        if self.onchange:
            self.onchange()


class MnemonicKeyboard(ui.Widget):
    def __init__(self, prompt: str=''):
        self.prompt = prompt
        self.input = Input(ui.grid(1, n_x=4, n_y=4, cells_x=3), '', '')
        self.back = Button(ui.grid(0, n_x=4, n_y=4),
                           res.load(ui.ICON_BACK),
                           style=ui.BTN_CLEAR)
        self.keys = key_buttons()
        self.pbutton = None  # pending key button
        self.pindex = 0  # index of current pending char in pbutton

    def render(self):
        if self.input.content:
            # content button and backspace
            self.input.render()
            self.back.render()
        else:
            # prompt
            display.bar(0, 8, 240, 60, ui.BG)
            display.text(20, 40, self.prompt, ui.BOLD, ui.GREY, ui.BG)
        # key buttons
        for btn in self.keys:
            btn.render()

    def touch(self, event, pos):
        content = self.input.content
        word = self.input.word

        if self.back.touch(event, pos) == BTN_CLICKED:
            # backspace, delete the last character of input
            self.edit(content[:-1])
            return

        if self.input.touch(event, pos) == BTN_CLICKED:
            # input press, either auto-complete or confirm
            if content == word:
                self.edit('')
                return content
            else:
                self.edit(word)
                return

        for btn in self.keys:
            if btn.touch(event, pos) == BTN_CLICKED:
                # key press, add new char to input or cycle the pending button
                if self.pbutton is btn:
                    index = (self.pindex + 1) % len(btn.content)
                    content = content[:-1] + btn.content[index]
                else:
                    index = 0
                    content += btn.content[0]
                self.edit(content, btn, index)
                return

    def edit(self, content, button=None, index=0):
        word = bip39.find_word(content) or ''
        mask = bip39.complete_word(content)

        self.pbutton = button
        self.pindex = index
        self.input.edit(content, word, button is not None)

        # enable or disable key buttons
        for btn in self.keys:
            if btn is button or compute_mask(btn.content) & mask:
                btn.enable()
            else:
                btn.disable()

    async def __iter__(self):
        timeout = loop.sleep(1000 * 1000 * 1)
        touch = loop.select(io.TOUCH)
        wait_timeout = loop.wait(touch, timeout)
        wait_touch = loop.wait(touch)
        content = None

        self.back.taint()
        self.input.taint()

        while content is None:
            self.render()
            if self.pbutton is not None:
                wait = wait_timeout
            else:
                wait = wait_touch
            result = await wait
            if touch in wait.finished:
                event, *pos = result
                content = self.touch(event, pos)
            else:
                if self.input.word:
                    # just reset the pending state
                    self.edit(self.input.content)
                else:
                    # invalid character, backspace it
                    self.edit(self.input.content[:-1])
        return content
