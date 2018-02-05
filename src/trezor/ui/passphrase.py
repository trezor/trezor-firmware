from micropython import const
from trezor import io, loop, ui, res
from trezor.ui import display
from trezor.ui.button import BTN_CLICKED, ICON, Button
from trezor.ui.swipe import SWIPE_HORIZONTAL, SWIPE_LEFT, SWIPE_RIGHT, Swipe


KEYBOARD_KEYS = (
    ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'),
    ('_', 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz', '*#'),
    ('_', 'ABC', 'DEF', 'GHI', 'JKL', 'MNO', 'PQRS', 'TUV', 'WXYZ', '*#'),
    ('_', '.', '/', '!', '+', '-', '?', ',', ';', '$'))


def digit_area(i):
    if i == 9:  # 0-position
        i = 10  # display it in the middle
    return ui.grid(i + 3)  # skip the first line


def key_buttons(keys):
    return [Button(digit_area(i), str(k)) for i, k in enumerate(keys)]


def render_scrollbar(page):
    bbox = const(240)
    size = const(8)
    padding = 12
    page_count = len(KEYBOARD_KEYS)

    if page_count * padding > bbox:
        padding = bbox // page_count

    x = (bbox // 2) - (page_count // 2) * padding
    y = 44

    for i in range(0, page_count):
        if i != page:
            ui.display.bar_radius(
                x + i * padding, y, size, size, ui.DARK_GREY, ui.BG, size // 2)
    ui.display.bar_radius(
        x + page * padding, y, size, size, ui.FG, ui.BG, size // 2)


class Input(Button):
    def __init__(self, area: tuple, content: str=''):
        super().__init__(area, content)
        self.pending = False
        self.disable()

    def edit(self, content: str, pending: bool):
        self.content = content
        self.pending = pending
        self.taint()

    def render_content(self, s, ax, ay, aw, ah):
        text_style = s['text-style']
        fg_color = s['fg-color']
        bg_color = s['bg-color']

        p = self.pending  # should we draw the pending marker?
        t = self.content  # input content

        tx = ax + 24  # x-offset of the content
        ty = ay + ah // 2 + 8  # y-offset of the content

        # input content
        display.text(tx, ty, t, text_style, fg_color, bg_color)

        if p:  # pending marker
            width = display.text_width(t, text_style)
            pw = display.text_width(t[-1:], text_style)
            px = tx + width - pw
            display.bar(px, ty + 2, pw + 1, 3, fg_color)


class PassphraseKeyboard(ui.Widget):
    def __init__(self, prompt, page=1):
        self.prompt = prompt
        self.page = page
        self.input = Input(ui.grid(0, n_x=1, n_y=6), '')
        self.back = Button(ui.grid(12),
                           res.load(ui.ICON_BACK),
                           style=ui.BTN_CLEAR)
        self.keys = key_buttons(KEYBOARD_KEYS[self.page])
        self.pbutton = None  # pending key button
        self.pindex = 0  # index of current pending char in pbutton
        self.onchange = None

    def render(self):
        if self.input.content:
            # content and backspace
            self.input.render()
            self.back.render()
        else:
            # prompt
            display.bar(0, 0, 240, 48, ui.BG)
            display.text_center(ui.SCREEN // 2, 32, self.prompt, ui.BOLD, ui.GREY, ui.BG)

        # key buttons
        for btn in self.keys:
            btn.render()

        render_scrollbar(self.page)

    def touch(self, event, pos):
        content = self.input.content

        if self.back.touch(event, pos) == BTN_CLICKED:
            # backspace, delete the last character of input
            self.edit(content[:-1])
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
        self.pbutton = button
        self.pindex = index
        self.input.edit(content, button is not None)
        if self.onchange:
            self.onchange()

    async def __iter__(self):
        while True:
            swipe = Swipe(directions=SWIPE_HORIZONTAL)
            wait = loop.wait(swipe, self.show_page())
            result = await wait
            if swipe in wait.finished:
                if result == SWIPE_LEFT:
                    self.page = (self.page + 1) % len(KEYBOARD_KEYS)
                else:
                    self.page = (self.page - 1) % len(KEYBOARD_KEYS)
                self.keys = key_buttons(KEYBOARD_KEYS[self.page])
            else:
                return result

    @ui.layout
    async def show_page(self):
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
                self.edit(self.input.content)
        return content
