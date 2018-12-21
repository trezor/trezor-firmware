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

color_bg = ui.rgb(0xBB, 0xAD, 0xA0)
color_empty = ui.rgb(0xCC, 0xC0, 0xB3)
color_fg1 = ui.rgb(0x77, 0x6E, 0x65)
color_fg2 = ui.rgb(0xF9, 0xF6, 0xF2)
color_lose_fg = ui.rgb(0xFF, 0xFF, 0xFF)
color_lose_bg = ui.rgb(0xFF, 0x00, 0x00)
color_win_fg = ui.rgb(0xFF, 0xFF, 0xFF)
color_win_bg = ui.rgb(0x00, 0xFF, 0x00)
color = {}
color[2] = ui.rgb(0xEE, 0xE4, 0xDA), color_fg1
color[4] = ui.rgb(0xED, 0xE0, 0xC8), color_fg1
color[8] = ui.rgb(0xF2, 0xB1, 0x79), color_fg2
color[16] = ui.rgb(0xF5, 0x95, 0x63), color_fg2
color[32] = ui.rgb(0xF6, 0x7C, 0x5F), color_fg2
color[64] = ui.rgb(0xF6, 0x5E, 0x3B), color_fg2
color[128] = ui.rgb(0xED, 0xCF, 0x72), color_fg2
color[256] = ui.rgb(0xED, 0xCC, 0x61), color_fg2
color[512] = ui.rgb(0xED, 0xC8, 0x50), color_fg2
color[1024] = ui.rgb(0xED, 0xC5, 0x3F), color_fg2
color[2048] = ui.rgb(0xED, 0xC2, 0x2E), color_fg2


class State:
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

    def contains(self, val):
        return val in [i for l in self.m for i in l]

    def render(self):
        if not self.contains(0):
            d.bar(0, 0, ui.WIDTH, ui.HEIGHT, color_lose_bg)
            d.text_center(120, 128, "YOU LOSE!", ui.BOLD, color_lose_fg, color_lose_bg)
        elif self.contains(2048):
            d.bar(0, 0, ui.WIDTH, ui.HEIGHT, color_win_bg)
            d.text_center(120, 128, "YOU WIN!", ui.BOLD, color_win_fg, color_win_bg)
        else:
            for i in range(4):
                for j in range(4):
                    if not self.m[i][j]:
                        d.bar_radius(
                            8 + i * 58, 8 + j * 58, 50, 50, color_empty, color_bg, 2
                        )
                    else:
                        v = self.m[i][j]
                        cb, cf = color[v]
                        d.bar_radius(8 + i * 58, 8 + j * 58, 50, 50, cb, color_bg, 2)
                        d.text_center(
                            8 + i * 58 + 25, 8 + j * 58 + 33, str(v), ui.BOLD, cf, cb
                        )
        d.backlight(ui.BACKLIGHT_NORMAL)
        d.refresh()

    def update(self, d):
        for _ in range(4):
            self.compact(d)

    def compact(self, d):
        if d == SWIPE_DOWN:
            for i in range(4):
                for j in [2, 1, 0]:
                    if self.m[i][j] == self.m[i][j + 1]:
                        self.m[i][j + 1] = self.m[i][j] * 2
                        self.m[i][j] = 0
                    elif 0 == self.m[i][j + 1]:
                        self.m[i][j + 1] = self.m[i][j]
                        self.m[i][j] = 0
        elif d == SWIPE_UP:
            for i in range(4):
                for j in [1, 2, 3]:
                    if self.m[i][j] == self.m[i][j - 1]:
                        self.m[i][j - 1] = self.m[i][j] * 2
                        self.m[i][j] = 0
                    elif 0 == self.m[i][j - 1]:
                        self.m[i][j - 1] = self.m[i][j]
                        self.m[i][j] = 0
        elif d == SWIPE_LEFT:
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
d.bar(0, 0, ui.WIDTH, ui.HEIGHT, color_bg)

s = State()


async def swipe_move():
    swipe = await Swipe(absolute=True)
    s.update(swipe)
    s.add_new()


async def layout_game():
    while True:
        s.render()
        await swipe_move()


workflow.startdefault(layout_game)
loop.run()
