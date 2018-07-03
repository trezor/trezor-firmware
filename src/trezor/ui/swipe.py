from micropython import const

from trezor import io, ui
from trezor.ui import contains, rotate

SWIPE_UP = const(0x01)
SWIPE_DOWN = const(0x02)
SWIPE_LEFT = const(0x04)
SWIPE_RIGHT = const(0x08)
SWIPE_VERTICAL = const(SWIPE_UP | SWIPE_DOWN)
SWIPE_HORIZONTAL = const(SWIPE_LEFT | SWIPE_RIGHT)
SWIPE_ALL = const(SWIPE_VERTICAL | SWIPE_HORIZONTAL)

_SWIPE_DISTANCE = const(120)


def degrees(swipe: int) -> int:
    if swipe == SWIPE_UP:
        return 180
    elif swipe == SWIPE_DOWN:
        return 0
    elif swipe == SWIPE_LEFT:
        return 90
    elif swipe == SWIPE_RIGHT:
        return 270


class Swipe(ui.Widget):
    def __init__(self, area=None, absolute=False, directions=SWIPE_ALL, treshold=30):
        self.area = area or (0, 0, ui.WIDTH, ui.HEIGHT)
        self.absolute = absolute
        self.directions = directions
        self.treshold = treshold
        self.start_pos = None
        self.light_origin = None
        self.light_target = ui.BACKLIGHT_NONE

    def touch(self, event, pos):

        if not self.absolute:
            pos = rotate(pos)

        if event == io.TOUCH_MOVE and self.start_pos is not None:
            pdx = pos[0] - self.start_pos[0]
            pdy = pos[1] - self.start_pos[1]

            pdxa = abs(pdx)
            pdya = abs(pdy)
            if pdxa > pdya and self.directions & SWIPE_HORIZONTAL:
                # Horizontal direction
                if (pdx > 0 and self.directions & SWIPE_RIGHT) or (
                    pdx < 0 and self.directions & SWIPE_LEFT
                ):
                    ui.display.backlight(
                        ui.lerpi(
                            self.light_origin,
                            self.light_target,
                            pdxa / _SWIPE_DISTANCE if pdxa < _SWIPE_DISTANCE else 1,
                        )
                    )
            elif pdxa < pdya and self.directions & SWIPE_VERTICAL:
                # Vertical direction
                if (pdy > 0 and self.directions & SWIPE_DOWN) or (
                    pdy < 0 and self.directions & SWIPE_UP
                ):
                    ui.display.backlight(
                        ui.lerpi(
                            self.light_origin,
                            self.light_target,
                            pdya / _SWIPE_DISTANCE if pdya < _SWIPE_DISTANCE else 1,
                        )
                    )

        elif event == io.TOUCH_START and contains(self.area, pos):
            self.start_pos = pos
            self.light_origin = ui.BACKLIGHT_NORMAL

        elif event == io.TOUCH_END and self.start_pos is not None:
            pdx = pos[0] - self.start_pos[0]
            pdy = pos[1] - self.start_pos[1]
            pdxa = abs(pdx)
            pdya = abs(pdy)
            if pdxa > pdya and self.directions & SWIPE_HORIZONTAL:
                # Horizontal direction
                ratio = pdxa / _SWIPE_DISTANCE if pdxa < _SWIPE_DISTANCE else 1
                if ratio * 100 >= self.treshold:
                    if pdx > 0 and self.directions & SWIPE_RIGHT:
                        return SWIPE_RIGHT
                    elif pdx < 0 and self.directions & SWIPE_LEFT:
                        return SWIPE_LEFT
            elif pdxa < pdya and self.directions & SWIPE_VERTICAL:
                # Vertical direction
                ratio = pdya / _SWIPE_DISTANCE if pdya < _SWIPE_DISTANCE else 1
                if ratio * 100 >= self.treshold:
                    if pdy > 0 and self.directions & SWIPE_DOWN:
                        return SWIPE_DOWN
                    elif pdy < 0 and self.directions & SWIPE_UP:
                        return SWIPE_UP
            # No swipe, reset the state
            self.start_pos = None
            ui.display.backlight(self.light_origin)
