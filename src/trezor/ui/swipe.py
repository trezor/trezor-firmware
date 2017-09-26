import utime
from micropython import const
from trezor import io, ui
from . import contains, rotate

_SWIPE_DISTANCE_THRESHOLD = const(20)  # Min pixels in the primary direction
_SWIPE_VELOCITY_THRESHOLD = const(200)  # Min pixels per second
_SWIPE_RATIO_THRESHOLD = const(30)  # Max ratio or directions in %

SWIPE_UP = const(0x01)
SWIPE_DOWN = const(0x02)
SWIPE_LEFT = const(0x04)
SWIPE_RIGHT = const(0x08)
SWIPE_VERTICAL = const(SWIPE_UP | SWIPE_DOWN)
SWIPE_HORIZONTAL = const(SWIPE_LEFT | SWIPE_RIGHT)
SWIPE_ALL = const(SWIPE_VERTICAL | SWIPE_HORIZONTAL)


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

    def __init__(self, area=None, absolute=False, directions=SWIPE_ALL):
        self.area = area or (0, 0, ui.SCREEN, ui.SCREEN)
        self.absolute = absolute
        self.directions = directions
        self.start_pos = None
        self.start_time = 0
        self.light = None
        self.light_origin = None
        self.light_target = ui.BACKLIGHT_NONE

    def touch(self, event, pos):

        if not self.absolute:
            pos = rotate(pos)

        temp_time = utime.ticks_ms() / 1000

        if event == io.TOUCH_MOVE and self.start_pos is not None:
            pdx = pos[0] - self.start_pos[0]
            pdy = pos[1] - self.start_pos[1]
            td = temp_time - self.start_time

            pdxa = abs(pdx)
            pdya = abs(pdy)
            if pdxa > pdya and self.directions & SWIPE_HORIZONTAL:
                # Horizontal direction
                if (pdx > 0 and self.directions & SWIPE_RIGHT) or (pdx < 0 and self.directions & SWIPE_LEFT):
                    ui.display.backlight(ui.lerpi(
                        self.light_origin,
                        self.light_target,
                        pdxa / 120 if pdxa < 120 else 1))
            elif pdxa < pdya and self.directions & SWIPE_VERTICAL:
                # Vertical direction
                if (pdy > 0 and self.directions & SWIPE_DOWN) or (pdy < 0 and self.directions & SWIPE_UP):
                    ui.display.backlight(ui.lerpi(
                        self.light_origin,
                        self.light_target,
                        pdya / 120 if pdya < 120 else 1))

        elif event == io.TOUCH_START and contains(self.area, pos):
            self.start_time = temp_time
            self.start_pos = pos
            self.light_origin = ui.BACKLIGHT_NORMAL

        elif event == io.TOUCH_END and self.start_pos is not None:
            td = temp_time - self.start_time
            pdx = pos[0] - self.start_pos[0]
            pdy = pos[1] - self.start_pos[1]
            pdxa = abs(pdx)
            pdya = abs(pdy)
            if pdxa > pdya and self.directions & SWIPE_HORIZONTAL:
                # Horizontal direction
                velxa = abs(pdx / td)
                ratio = int(pdya / pdxa * 100) if pdxa > 0 else 100
                if (velxa >= _SWIPE_VELOCITY_THRESHOLD and
                        pdxa >= _SWIPE_DISTANCE_THRESHOLD and
                        ratio <= _SWIPE_RATIO_THRESHOLD):
                    if pdx > 0 and self.directions & SWIPE_RIGHT:
                        return SWIPE_RIGHT
                    elif pdx < 0 and self.directions & SWIPE_LEFT:
                        return SWIPE_LEFT
            elif pdxa < pdya and self.directions & SWIPE_VERTICAL:
                # Vertical direction
                velya = abs(pdy / td)
                ratio = int(pdxa / pdya * 100) if pdya > 0 else 100
                if (velya >= _SWIPE_VELOCITY_THRESHOLD and
                        pdya >= _SWIPE_DISTANCE_THRESHOLD and
                        ratio <= _SWIPE_RATIO_THRESHOLD):
                    if pdy > 0 and self.directions & SWIPE_DOWN:
                        self.light = None
                        return SWIPE_DOWN
                    elif pdy < 0 and self.directions & SWIPE_UP:
                        self.light = None
                        return SWIPE_UP
            # No swipe, reset the state
            self.start_pos = None
            self.start_time = 0
            ui.display.backlight(self.light_origin)
