# isort:skip_file

import utime

# Welcome screen is shown immediately after display init.
# Then it takes about 120ms to get here.
# (display is also prepared on that occasion).
# Remembering time to control how long we show it.
welcome_screen_start_ms = utime.ticks_ms()

import storage
import storage.device
from trezor import config, io, log, loop, ui, utils, wire, translations
from trezor.pin import (
    allow_all_loader_messages,
    ignore_nonpin_loader_messages,
    show_pin_timeout,
)
from trezor.ui.layouts.homescreen import Lockscreen

from apps.common.request_pin import can_lock_device, verify_user_pin

if utils.INTERNAL_MODEL in ("T2T1", "T2B1"):
    _WELCOME_SCREEN_MS = 1000  # how long do we want to show welcome screen (minimum)
else:
    _WELCOME_SCREEN_MS = 0


def enforce_welcome_screen_duration() -> None:
    """Make sure we will show the welcome screen for appropriate amount of time."""
    # Not wasting the time in emulator debug builds (debugging and development)
    if __debug__ and utils.EMULATOR:
        return
    while (
        utime.ticks_diff(utime.ticks_ms(), welcome_screen_start_ms) < _WELCOME_SCREEN_MS
    ):
        utime.sleep_ms(100)


async def bootscreen() -> None:
    """Sequence of actions to be done on boot (after device is connected).

    We are starting with welcome_screen on the screen and want to show it
    for at least _WELCOME_SCREEN_MS before any other screen.

    Any non-PIN loaders are ignored during this function.
    Allowing all of them before returning.
    """
    lockscreen = None
    try:
        # turn on peripherals
        if utils.USE_HAPTIC:
            io.haptic.haptic_set_enabled(storage.device.get_haptic_feedback())

        # if required, change display orientation
        rotation = storage.device.get_rotation()
        if rotation != ui.display.orientation():
            # wait before hiding the welcome screen
            enforce_welcome_screen_duration()
            # hide, rotate
            ui.backlight_fade(ui.BacklightLevels.NONE)
            ui.display.orientation(rotation)

        if can_lock_device():
            lockscreen = Lockscreen(label=storage.device.get_label(), bootscreen=True)
            # we will be showing the lockscreen soon, wait for welcome screen first
            enforce_welcome_screen_duration()
        else:
            lockscreen = None

        while True:
            if lockscreen:
                await lockscreen

            try:
                await verify_user_pin()
            except wire.PinCancelled:
                # verify_user_pin will convert a SdCardUnavailable (in case of sd salt)
                # to PinCancelled exception.
                # Ignore exception, retry loop.
                continue
            else:
                storage.init_unlocked()
                break

    except BaseException as e:
        # halt the device if anything failed
        if __debug__:
            log.exception(__name__, e)
        utils.halt(e.__class__.__name__)

    finally:
        if lockscreen:
            lockscreen.__del__()

    # if nothing was shown so far, wait for welcome screen duration
    enforce_welcome_screen_duration()
    allow_all_loader_messages()


# Ignoring all non-PIN messages in the boot-phase (turned off in `bootscreen()`).
ignore_nonpin_loader_messages()

config.init(show_pin_timeout)
translations.init()

if __debug__ and not utils.EMULATOR:
    config.wipe()

loop.schedule(bootscreen())
loop.run()
