import utime
from micropython import const
from trezor import loop, ui
from . import in_area, rotate_coords

_SWIPE_DISTANCE_THRESHOLD = const(20)  # Min pixels in the primary direction
_SWIPE_VELOCITY_THRESHOLD = const(200)  # Min pixels per second
_SWIPE_RATIO_THRESHOLD = const(30)  # Max ratio or directions in %

SWIPE_UP = const(180)
SWIPE_DOWN = const(0)
SWIPE_LEFT = const(90)
SWIPE_RIGHT = const(270)


class Swipe():
    def __init__(self, area=None, absolute=False):
        self.area = area or (0, 0, ui.SCREEN, ui.SCREEN)
        self.absolute = absolute
        self.start_pos = None
        self.start_time = 0
        self.light_origin = None
        self.light_target = ui.BACKLIGHT_NONE

    def send(self, event, pos):

        if not self.absolute:
            pos = rotate_coords(pos)

        temp_time = utime.ticks_ms() / 1000

        # primary now for fading purposes
        if event == loop.TOUCH_MOVE and self.start_pos is not None:
            pdx = pos[0] - self.start_pos[0]
            pdy = pos[1] - self.start_pos[1]
            td = temp_time - self.start_time

            pdxa = abs(pdx)
            pdya = abs(pdy)
            if pdxa < pdya and pdy < 0:
                # check if its vertical scroll up
                velya = abs(pdy / td) if td > 0 else 1
                ratio = int(pdxa / pdya * 100) if pdya > 0 else 100
                if (velya >= _SWIPE_VELOCITY_THRESHOLD
                    and pdya >= _SWIPE_DISTANCE_THRESHOLD
                    and ratio <= _SWIPE_RATIO_THRESHOLD):
                    light = ui.display.backlight()
                    if light > self.light_target:
                        light -= 5
                        ui.display.backlight(light)
                    else:
                        ui.display.backlight(self.light_target)

        elif event == loop.TOUCH_START and in_area(pos, self.area):
            self.start_time = temp_time
            self.start_pos = pos
            self.light_origin = ui.BACKLIGHT_NORMAL
            ui.display.backlight(self.light_origin)

        elif event == loop.TOUCH_END and self.start_pos is not None:
            td = temp_time - self.start_time
            pdx = pos[0] - self.start_pos[0]
            pdy = pos[1] - self.start_pos[1]
            pdxa = abs(pdx)
            pdya = abs(pdy)
            if pdxa > pdya:
                # Horizontal direction
                velxa = abs(pdx / td)
                ratio = int(pdya / pdxa * 100) if pdxa > 0 else 100
                if (velxa >= _SWIPE_VELOCITY_THRESHOLD
                    and pdxa >= _SWIPE_DISTANCE_THRESHOLD
                    and ratio <= _SWIPE_RATIO_THRESHOLD):
                    return SWIPE_RIGHT if pdx > 0 else SWIPE_LEFT
            else:
                # Vertical direction
                velya = abs(pdy / td)
                ratio = int(pdxa / pdya * 100) if pdya > 0 else 100
                if (velya >= _SWIPE_VELOCITY_THRESHOLD
                    and pdya >= _SWIPE_DISTANCE_THRESHOLD
                    and ratio <= _SWIPE_RATIO_THRESHOLD):
                    if pdy < 0:
                        ui.display.backlight(self.light_origin)
                    return SWIPE_DOWN if pdy > 0 else SWIPE_UP
            # No swipe, reset the state
            self.start_pos = None
            self.start_time = 0
            ui.display.backlight(self.light_origin)

    def __iter__(self):
        while True:
            event, *pos = yield loop.Select(loop.TOUCH)
            result = self.send(event, pos)
            if result is not None:
                return result
