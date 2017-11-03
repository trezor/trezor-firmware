from trezor import ui, res, loop, io
from trezor.crypto import bip39
from trezor.ui import display
from trezor.ui.button import Button, BTN_CLICKED


def cell_area(i, n_x=3, n_y=3, start_x=6, start_y=66, end_x=234, end_y=237, spacing=0):
    w = (end_x - start_x) // n_x
    h = (end_y - start_y) // n_y
    x = (i % n_x) * w
    y = (i // n_x) * h
    return (x + start_x, y + start_y, w - spacing, h - spacing)


def key_buttons():
    keys = ['abc', 'def', 'ghi', 'jkl', 'mno', 'pqr', 'stu', 'vwx', 'yz']
    # keys = [' ', 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz']
    return [Button(cell_area(i), k,
                   normal_style=ui.BTN_KEY,
                   active_style=ui.BTN_KEY_ACTIVE,
                   disabled_style=ui.BTN_KEY_DISABLED) for i, k in enumerate(keys)]


def compute_mask(text):
    mask = 0
    for c in text:
        shift = ord(c) - 97  # ord('a') == 97
        if shift < 0:
            continue
        mask |= 1 << shift
    return mask


class KeyboardMultiTap(ui.Widget):

    def __init__(self, content='', prompt=''):
        self.content = content
        self.prompt = prompt
        self.sugg_mask = 0xffffffff
        self.sugg_word = None
        self.pending_button = None
        self.pending_index = 0

        self.key_buttons = key_buttons()
        self.sugg_button = Button((63, 0, 240 - 65, 57), '')
        self.bs_button = Button((6, 5, 57, 60),
                                res.load('trezor/res/left.toig'),
                                normal_style=ui.BTN_CLEAR,
                                active_style=ui.BTN_CLEAR_ACTIVE)

    def render(self):
        if self.content:
            display.bar(62, 8, 168, 54, ui.BG)
            content_width = display.text_width(self.content, ui.BOLD)
            offset_x = 78
            if self.content == self.sugg_word:
                # confirm button + content
                display.bar_radius(67, 8, 164, 54, ui.GREEN, ui.BG, ui.RADIUS)
                type_icon = res.load(ui.ICON_CONFIRM2)
                display.icon(228 - 30, 28, type_icon, ui.WHITE, ui.GREEN)
                display.text(offset_x, 40, self.content, ui.BOLD, ui.WHITE, ui.GREEN)

            elif self.sugg_word is not None:
                # auto-suggest button + content + suggestion
                display.bar_radius(67, 8, 164, 54, ui.BLACKISH, ui.BG, ui.RADIUS)
                display.text(offset_x, 40, self.content, ui.BOLD, ui.FG, ui.BLACKISH)
                sugg_text = self.sugg_word[len(self.content):]
                sugg_x = offset_x + content_width
                type_icon = res.load(ui.ICON_CLICK)
                display.icon(228 - 30, 24, type_icon, ui.GREY, ui.BLACKISH)
                display.text(sugg_x, 40, sugg_text, ui.BOLD, ui.GREY, ui.BLACKISH)

            else:
                # content
                display.bar(63, 8, 168, 54, ui.BG)
                display.text(offset_x, 40, self.content, ui.BOLD, ui.FG, ui.BG)

            # backspace button
            self.bs_button.render()

            # pending marker
            if self.pending_button is not None:
                pending_width = display.text_width(self.content[-1:], ui.BOLD)
                pending_x = offset_x + content_width - pending_width
                display.bar(pending_x, 42, pending_width + 2, 3, ui.FG)

        else:
            # prompt
            display.bar(0, 8, 240, 60, ui.BG)
            display.text(20, 40, self.prompt, ui.BOLD, ui.GREY, ui.BG)

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
        if self.sugg_button.touch(event, pos) == BTN_CLICKED:
            if not self.content or self.sugg_word is None:
                return None
            if self.content == self.sugg_word:
                result = self.content
                self.content = ''
            else:
                result = None
                self.content = self.sugg_word
            self.pending_button = None
            self.pending_index = 0
            self._update_suggestion()
            self._update_buttons()
            return result
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
            if btn is self.pending_button or compute_mask(btn.content) & self.sugg_mask:
                btn.enable()
            else:
                btn.disable()

    async def __iter__(self):
        timeout = loop.sleep(1000 * 1000 * 1)
        touch = loop.select(io.TOUCH)
        wait_timeout = loop.wait(touch, timeout)
        wait_touch = loop.wait(touch)
        content = None

        self.bs_button.taint()

        while content is None:
            self.render()
            if self.pending_button is not None:
                wait = wait_timeout
            else:
                wait = wait_touch
            result = await wait
            if touch in wait.finished:
                event, *pos = result
                content = self.touch(event, pos)
            else:
                self.pending_button = None
                self.pending_index = 0
                if self.sugg_word is None:
                    self.content = self.content[:-1]
            self._update_suggestion()
            self._update_buttons()
        return content


# def zoom_buttons(keys, upper=False):
#     n_x = len(keys)
#     if upper:
#         keys = keys + keys.upper()
#         n_y = 2
#     else:
#         n_y = 1
#     return [Button(cell_area(i, n_x, n_y), key) for i, key in enumerate(keys)]


# class KeyboardZooming(ui.Widget):

#     def __init__(self, content='', uppercase=True):
#         self.content = content
#         self.uppercase = uppercase

#         self.zoom_buttons = None
#         self.key_buttons = key_buttons()
#         self.bs_button = Button((240 - 35, 5, 30, 30),
#                                 res.load('trezor/res/pin_close.toig'),
#                                 normal_style=ui.BTN_CLEAR,
#                                 active_style=ui.BTN_CLEAR_ACTIVE)

#     def render(self):
#         self.render_input()
#         if self.zoom_buttons:
#             for btn in self.zoom_buttons:
#                 btn.render()
#         else:
#             for btn in self.key_buttons:
#                 btn.render()

#     def render_input(self):
#         if self.content:
#             display.bar(0, 0, 200, 40, ui.BG)
#         else:
#             display.bar(0, 0, 240, 40, ui.BG)
#         display.text(20, 30, self.content, ui.BOLD, ui.GREY, ui.BG)
#         if self.content:
#             self.bs_button.render()

#     def touch(self, event, pos):
#         if self.bs_button.touch(event, pos) == BTN_CLICKED:
#             self.content = self.content[:-1]
#             self.bs_button.taint()
#             return
#         if self.zoom_buttons:
#             return self.touch_zoom(event, pos)
#         else:
#             return self.touch_keyboard(event, pos)

#     def touch_zoom(self, event, pos):
#         for btn in self.zoom_buttons:
#             if btn.touch(event, pos) == BTN_CLICKED:
#                 self.content += btn.content
#                 self.zoom_buttons = None
#                 for b in self.key_buttons:
#                     b.taint()
#                 self.bs_button.taint()
#                 break

#     def touch_keyboard(self, event, pos):
#         for btn in self.key_buttons:
#             if btn.touch(event, pos) == BTN_CLICKED:
#                 self.zoom_buttons = zoom_buttons(btn.content, self.uppercase)
#                 for b in self.zoom_buttons:
#                     b.taint()
#                 self.bs_button.taint()
#                 break

#     def __iter__(self):
#         timeout = loop.sleep(1000 * 1000 * 1)
#         touch = loop.select(io.TOUCH)
#         wait = loop.wait(touch, timeout)
#         while True:
#             self.render()
#             result = yield wait
#             if touch in wait.finished:
#                 event, *pos = result
#                 self.touch(event, pos)
#             elif self.zoom_buttons:
#                 self.zoom_buttons = None
#                 for btn in self.key_buttons:
#                     btn.taint()


Keyboard = KeyboardMultiTap
