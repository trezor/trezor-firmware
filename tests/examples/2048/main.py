#
# 2048 Game ported to TREZOR Core by Pavol Rusnak (stick@satoshilabs.com)
#
# inspired by https://github.com/gabrielecirulli/2048
#


from trezor import ui
from trezor import loop
from trezor import workflow
from trezor.crypto import random
from trezor.ui.swipe import Swipe, SWIPE_DOWN, SWIPE_UP, SWIPE_LEFT

color_bg = ui.rgb(0xbb, 0xad, 0xa0)
color_empty = ui.rgb(0xcc, 0xc0, 0xb3)
color_fg1 = ui.rgb(0x77, 0x6e, 0x65)
color_fg2 = ui.rgb(0xf9, 0xf6, 0xf2)
color_lose_fg = ui.rgb(0xff, 0xff, 0xff)
color_lose_bg = ui.rgb(0xff, 0x00, 0x00)
color_win_fg = ui.rgb(0xff, 0xff, 0xff)
color_win_bg = ui.rgb(0x00, 0xff, 0x00)
color = {}
color[2] = ui.rgb(0xee, 0xe4, 0xda), color_fg1
color[4] = ui.rgb(0xed, 0xe0, 0xc8), color_fg1
color[8] = ui.rgb(0xf2, 0xb1, 0x79), color_fg2
color[16] = ui.rgb(0xf5, 0x95, 0x63), color_fg2
color[32] = ui.rgb(0xf6, 0x7c, 0x5f), color_fg2
color[64] = ui.rgb(0xf6, 0x5e, 0x3b), color_fg2
color[128] = ui.rgb(0xed, 0xcf, 0x72), color_fg2
color[256] = ui.rgb(0xed, 0xcc, 0x61), color_fg2
color[512] = ui.rgb(0xed, 0xc8, 0x50), color_fg2
color[1024] = ui.rgb(0xed, 0xc5, 0x3f), color_fg2
color[2048] = ui.rgb(0xed, 0xc2, 0x2e), color_fg2


class State():

    def __init__(self):
        self.m = [[0 for _ in range(4)] for _ in range(4)]
        self.add_new()
        self.add_new()

    def add_new(self):
        while True:
            i, j = random.uniform(4), random.uniform(4)
            if self.m[i][j] == 0:
                self.m[i][j] = 2
                break

    def render(self):
        if 0 not in self.m[0] and 0 not in self.m[1] and 0 not in self.m[2] and 0 not in self.m[3]:
            d.bar(0, 0, 240, 240, color_lose_bg)
            d.text_center(120, 128, "YOU LOSE!", ui.BOLD, color_lose_fg, color_lose_bg)
        elif 2048 in self.m[0] or 2048 in self.m[1] or 2048 in self.m[2] or 2048 in self.m[3]:
            d.bar(0, 0, 240, 240, color_win_bg)
            d.text_center(120, 128, "YOU WIN!", ui.BOLD, color_win_fg, color_win_bg)
        else:
            for i in range(4):
                for j in range(4):
                    if not self.m[i][j]:
                        d.bar_radius(8 + i * 58, 8 + j * 58, 50, 50, color_empty, color_bg, 2)
                    else:
                        v = self.m[i][j]
                        cb, cf = color[v]
                        d.bar_radius(8 + i * 58, 8 + j * 58, 50, 50, cb, color_bg, 2)
                        d.text_center(8 + i * 58 + 25, 8 + j * 58 + 33, str(v), ui.BOLD, cf, cb)
        d.backlight(ui.BACKLIGHT_NORMAL)
        d.refresh()

    def update(self, dir):
        for _ in range(4):
            self.compact(dir)

    def compact(self, dir):
        if dir == SWIPE_DOWN:
            for i in range(4):
                for j in [2, 1, 0]:
                    if self.m[i][j] == self.m[i][j + 1]:
                        self.m[i][j + 1] = self.m[i][j] * 2
                        self.m[i][j] = 0
                    elif 0 == self.m[i][j + 1]:
                        self.m[i][j + 1] = self.m[i][j]
                        self.m[i][j] = 0
        elif dir == SWIPE_UP:
            for i in range(4):
                for j in [1, 2, 3]:
                    if self.m[i][j] == self.m[i][j - 1]:
                        self.m[i][j - 1] = self.m[i][j] * 2
                        self.m[i][j] = 0
                    elif 0 == self.m[i][j - 1]:
                        self.m[i][j - 1] = self.m[i][j]
                        self.m[i][j] = 0
        elif dir == SWIPE_LEFT:
            for j in range(4):
                for i in [1, 2, 3]:
                    if self.m[i][j] == self.m[i - 1][j]:
                        self.m[i - 1][j] = self.m[i][j] * 2
                        self.m[i][j] = 0
                    elif 0 == self.m[i - 1][j]:
                        self.m[i - 1][j] = self.m[i][j]
                        self.m[i][j] = 0
        else:  # SWIPE_RIGHT
            for j in range(4):
                for i in [2, 1, 0]:
                    if self.m[i][j] == self.m[i + 1][j]:
                        self.m[i + 1][j] = self.m[i][j] * 2
                        self.m[i][j] = 0
                    elif 0 == self.m[i + 1][j]:
                        self.m[i + 1][j] = self.m[i][j]
                        self.m[i][j] = 0


d = ui.Display()
d.backlight(ui.BACKLIGHT_NORMAL)
d.bar(0, 0, 240, 240, color_bg)

s = State()


async def swipe_move():
    swipe = await Swipe(absolute=True)
    s.update(swipe)
    s.add_new()


async def layout_game():
    while True:
        s.render()
        await loop.wait(swipe_move())


workflow.startdefault(layout_game)
loop.run()
