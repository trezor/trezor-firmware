from trezor.loop import Sleep
import utime

class ConstDelay:
    def __init__(self, delay):
        self.delay = delay
        self.last_run = utime.ticks_us()
        
    def wait(self):
        delay = 2 * self.delay - (utime.ticks_us() - self.last_run)
        self.last_run = utime.ticks_us()
        return Sleep(delay)
