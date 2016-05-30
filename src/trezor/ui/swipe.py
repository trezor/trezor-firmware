import utime

from . import in_area, rotate_coords
from trezor import loop


SWIPE_DISTANCE_THRESHOLD = const(20)  # Min pixels in the primary direction
SWIPE_VELOCITY_THRESHOLD = const(200)  # Min pixels/second
SWIPE_RATIO_THRESHOLD = const(30)  # Max ratio secondary to primary direction in %

SWIPE_UP = const(180)
SWIPE_DOWN = const(0)
SWIPE_LEFT = const(90)
SWIPE_RIGHT = const(270)


class Swipe():

    def __init__(self, area=None, absolute=False):
        self.area = area or (0, 0, 240, 240)
        self.absolute = absolute
        self.start_pos = None
        self.start_time = 0
        self.end_pos = None
        self.end_time = 0

    def send(self, event, pos):

        if not self.absolute:
            pos = rotate_coords(pos)

        if event is loop.TOUCH_START and in_area(pos, self.area):
            self.start_time = utime.time()
            self.start_pos = pos

        elif event is loop.TOUCH_END and self.start_pos is not None:
            self.end_time = utime.time()
            self.end_pos = pos
            td = self.end_time - self.start_time
            pdx = self.end_pos[0] - self.start_pos[0]
            pdy = self.end_pos[1] - self.start_pos[1]
            pdxa = abs(pdx)
            pdya = abs(pdy)
            if pdxa > pdya:
                # Horizontal direction
                velxa = abs(pdx / td)
                ratio = int(pdya / pdxa * 100) if pdxa > 0 else 100
                if (velxa >= SWIPE_VELOCITY_THRESHOLD
                        and pdxa >= SWIPE_DISTANCE_THRESHOLD
                        and ratio <= SWIPE_RATIO_THRESHOLD):
                    return SWIPE_RIGHT if pdx > 0 else SWIPE_LEFT
            else:
                # Vertical direction
                velya = abs(pdy / td)
                ratio = int(pdxa / pdya * 100) if pdya > 0 else 100
                if (velya >= SWIPE_VELOCITY_THRESHOLD
                        and pdya >= SWIPE_DISTANCE_THRESHOLD
                        and ratio <= SWIPE_RATIO_THRESHOLD):
                    return SWIPE_DOWN if pdy > 0 else SWIPE_UP
            # No swipe, reset the state
            self.start_pos = None
            self.start_time = 0
            self.end_pos = None
            self.end_time = 0

    def wait(self):
        while True:
            event, *pos = yield loop.Select(loop.TOUCH)
            result = self.send(event, pos)
            if result is not None:
                return result
