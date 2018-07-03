from micropython import const

from trezor import io, loop, res, ui
from trezor.ui import display
from trezor.ui.button import BTN_CLICKED, Button
from trezor.ui.swipe import SWIPE_HORIZONTAL, SWIPE_LEFT, Swipe

SPACE = res.load(ui.ICON_SPACE)

KEYBOARD_KEYS = (
    ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"),
    (SPACE, "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz", "*#"),
    (SPACE, "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ", "*#"),
    ("_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ';"~', "$^="),
)


def digit_area(i):
    if i == 9:  # 0-position
        i = 10  # display it in the middle
    return ui.grid(i + 3)  # skip the first line


def key_buttons(keys):
    return [Button(digit_area(i), k) for i, k in enumerate(keys)]


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
                x + i * padding, y, size, size, ui.DARK_GREY, ui.BG, size // 2
            )
    ui.display.bar_radius(x + page * padding, y, size, size, ui.FG, ui.BG, size // 2)


class Input(Button):
    def __init__(self, area: tuple, content: str = ""):
        super().__init__(area, content)
        self.pending = False
        self.disable()

    def edit(self, content: str, pending: bool):
        self.content = content
        self.pending = pending
        self.taint()

    def render_content(self, s, ax, ay, aw, ah):
        text_style = s["text-style"]
        fg_color = s["fg-color"]
        bg_color = s["bg-color"]

        p = self.pending  # should we draw the pending marker?
        t = self.content  # input content

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
            display.bar(tx + width - pw, ty + 2, pw + 1, 3, fg_color)
        else:  # cursor
            display.bar(tx + width + 1, ty - 18, 2, 22, fg_color)


class Prompt:
    def __init__(self, text):
        self.text = text
        self.dirty = True

    def taint(self):
        self.dirty = True

    def render(self):
        if self.dirty:
            display.bar(0, 0, ui.WIDTH, 48, ui.BG)
            display.text_center(ui.WIDTH // 2, 32, self.text, ui.BOLD, ui.GREY, ui.BG)
            self.dirty = False


CANCELLED = const(0)


class PassphraseKeyboard(ui.Widget):
    def __init__(self, prompt, page=1):
        self.prompt = Prompt(prompt)
        self.page = page
        self.input = Input(ui.grid(0, n_x=1, n_y=6), "")
        self.back = Button(ui.grid(12), res.load(ui.ICON_BACK), style=ui.BTN_CLEAR)
        self.done = Button(ui.grid(14), res.load(ui.ICON_CONFIRM), style=ui.BTN_CONFIRM)
        self.keys = key_buttons(KEYBOARD_KEYS[self.page])
        self.pbutton = None  # pending key button
        self.pindex = 0  # index of current pending char in pbutton

    def render(self):
        # passphrase or prompt
        if self.input.content:
            self.input.render()
        else:
            self.prompt.render()
        render_scrollbar(self.page)
        # buttons
        self.back.render()
        self.done.render()
        for btn in self.keys:
            btn.render()

    def touch(self, event, pos):
        content = self.input.content
        if self.back.touch(event, pos) == BTN_CLICKED:
            if content:
                # backspace, delete the last character of input
                self.edit(content[:-1])
                return
            else:
                # cancel
                return CANCELLED
        if self.done.touch(event, pos) == BTN_CLICKED:
            # confirm button, return the content
            return content
        for btn in self.keys:
            if btn.touch(event, pos) == BTN_CLICKED:
                if isinstance(btn.content[0], str):
                    # key press, add new char to input or cycle the pending button
                    if self.pbutton is btn:
                        index = (self.pindex + 1) % len(btn.content)
                        content = content[:-1] + btn.content[index]
                    else:
                        index = 0
                        content += btn.content[0]
                else:
                    index = 0
                    content += " "

                self.edit(content, btn, index)
                return

    def edit(self, content, button=None, index=0):
        if button and len(button.content) == 1:
            # one-letter buttons are never pending
            button = None
            index = 0
        self.pbutton = button
        self.pindex = index
        self.input.edit(content, button is not None)
        if content:
            self.back.enable()
        else:
            self.back.disable()
            self.prompt.taint()

    async def __iter__(self):
        self.edit(self.input.content)  # init button state
        while True:
            change = self.change_page()
            enter = self.enter_text()
            wait = loop.spawn(change, enter)
            result = await wait
            if enter in wait.finished:
                return result

    @ui.layout
    async def enter_text(self):
        timeout = loop.sleep(1000 * 1000 * 1)
        touch = loop.wait(io.TOUCH)
        wait_timeout = loop.spawn(touch, timeout)
        wait_touch = loop.spawn(touch)
        content = None
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
                # disable the pending buttons
                self.edit(self.input.content)
        return content

    async def change_page(self):
        swipe = await Swipe(directions=SWIPE_HORIZONTAL)
        if swipe == SWIPE_LEFT:
            self.page = (self.page + 1) % len(KEYBOARD_KEYS)
        else:
            self.page = (self.page - 1) % len(KEYBOARD_KEYS)
        self.keys = key_buttons(KEYBOARD_KEYS[self.page])
        self.back.taint()
        self.done.taint()
        self.input.taint()
        self.prompt.taint()
