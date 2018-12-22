#
# 2048 Game
# ported to TREZOR Core by Pavol Rusnak (stick@satoshilabs.com)
#
# inspired by https://github.com/gabrielecirulli/2048
#

from trezor import loop, ui, workflow
from trezor.crypto import random
from trezor.ui.swipe import Swipe, SWIPE_DOWN, SWIPE_UP, SWIPE_LEFT


color_fg1 = ui.rgb(0x77, 0x6E, 0x65)
color_fg2 = ui.rgb(0xF9, 0xF6, 0xF2)
color = {
    "0": (ui.rgb(0xCC, 0xC0, 0xB3), ui.rgb(0xBB, 0xAD, 0xA0)),
    "2": (ui.rgb(0xEE, 0xE4, 0xDA), color_fg1),
    "4": (ui.rgb(0xED, 0xE0, 0xC8), color_fg1),
    "8": (ui.rgb(0xF2, 0xB1, 0x79), color_fg2),
    "16": (ui.rgb(0xF5, 0x95, 0x63), color_fg2),
    "32": (ui.rgb(0xF6, 0x7C, 0x5F), color_fg2),
    "64": (ui.rgb(0xF6, 0x5E, 0x3B), color_fg2),
    "128": (ui.rgb(0xED, 0xCF, 0x72), color_fg2),
    "256": (ui.rgb(0xED, 0xCC, 0x61), color_fg2),
    "512": (ui.rgb(0xED, 0xC8, 0x50), color_fg2),
    "1024": (ui.rgb(0xED, 0xC5, 0x3F), color_fg2),
    "2048": (ui.rgb(0xED, 0xC2, 0x2E), color_fg2),
    "lose": (ui.rgb(0xFF, 0x00, 0x00), ui.rgb(0xFF, 0xFF, 0xFF)),
    "win": (ui.rgb(0x00, 0xFF, 0x00), ui.rgb(0xFF, 0xFF, 0xFF)),
}


class Game:
    def __init__(self):
        self.d = ui.Display()
        self.d.backlight(ui.BACKLIGHT_NORMAL)
        self.d.bar(0, 0, ui.WIDTH, ui.HEIGHT, color["0"][1])
        self.m = [[0 for _ in range(4)] for _ in range(4)]
        self.add()
        self.add()

    def add(self):
        while True:
            i, j = random.uniform(4), random.uniform(4)
            if self.m[i][j] == 0:
                self.m[i][j] = 2
                break

    def contains(self, val):
        return val in [i for l in self.m for i in l]

    def render(self):
        # LOSE endstate
        if not self.contains(0):
            self.d.bar(0, 0, ui.WIDTH, ui.HEIGHT, color["lose"][0])
            self.d.text_center(
                120, 128, "YOU LOSE!", ui.BOLD, color["lose"][1], color["lose"][0]
            )
        # WIN endstate
        elif self.contains(2048):
            self.d.bar(0, 0, ui.WIDTH, ui.HEIGHT, color["win"][0])
            self.d.text_center(
                120, 128, "YOU WIN!", ui.BOLD, color["win"][1], color["win"][0]
            )
        # NORMAL game state
        else:
            for i in range(4):
                for j in range(4):
                    v = self.m[i][j]
                    cb, cf = color[str(v)]
                    self.d.bar_radius(
                        8 + i * 58, 8 + j * 58, 50, 50, cb, color["0"][1], 2
                    )
                    if v:
                        self.d.text_center(
                            8 + i * 58 + 25, 8 + j * 58 + 33, str(v), ui.BOLD, cf, cb
                        )
        self.d.backlight(ui.BACKLIGHT_NORMAL)
        self.d.refresh()

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


async def layout_game():
    game = Game()
    while True:
        game.render()
        swipe = await Swipe(absolute=True)
        game.update(swipe)
        game.add()


workflow.startdefault(layout_game)
loop.run()
