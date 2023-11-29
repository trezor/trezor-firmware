# isort:skip_file

import utime

# Welcome screen is shown immediately after display init.
# Then it takes about 120ms to get here.
# (display is also prepared on that occasion).
# Remembering time to control how long we show it.
welcome_screen_start_ms = utime.ticks_ms()

import storage
import storage.device
from trezor import config, log, loop, ui, utils, wire
from trezor.pin import (
    allow_all_loader_messages,
    ignore_nonpin_loader_messages,
    show_pin_timeout,
)
from trezor.ui.layouts.homescreen import Lockscreen

from apps.common.request_pin import can_lock_device, verify_user_pin

_WELCOME_SCREEN_MS = 1000  # how long do we want to show welcome screen (minimum)


def enforce_welcome_screen_duration() -> None:
    """Make sure we will show the welcome screen for appropriate amount of time."""
    # Not wasting the time in emulator debug builds (debugging and development)
    if __debug__ and utils.EMULATOR:
        return
    while utime.ticks_ms() - welcome_screen_start_ms < _WELCOME_SCREEN_MS:
        utime.sleep_ms(100)


async def bootscreen() -> None:
    """Sequence of actions to be done on boot (after device is connected).

    We are starting with welcome_screen on the screen and want to show it
    for at least _WELCOME_SCREEN_MS before any other screen.

    Any non-PIN loaders are ignored during this function.
    Allowing all of them before returning.
    """
    lockscreen = Lockscreen(label=storage.device.get_label(), bootscreen=True)
    ui.display.orientation(storage.device.get_rotation())
    while True:
        try:
            if can_lock_device():
                enforce_welcome_screen_duration()
                await lockscreen
            await verify_user_pin()
            storage.init_unlocked()
            enforce_welcome_screen_duration()
            allow_all_loader_messages()
            return
        except wire.PinCancelled:
            # verify_user_pin will convert a SdCardUnavailable (in case of sd salt)
            # to PinCancelled exception.
            # Ignore exception, retry loop.
            pass
        except BaseException as e:
            # other exceptions here are unexpected and should halt the device
            if __debug__:
                log.exception(__name__, e)
            utils.halt(e.__class__.__name__)


# Ignoring all non-PIN messages in the boot-phase (turned off in `bootscreen()`).
ignore_nonpin_loader_messages()

config.init(show_pin_timeout)

if __debug__ and not utils.EMULATOR:
    config.wipe()

loop.schedule(bootscreen())
loop.run()
