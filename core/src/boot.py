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

if utils.USE_OPTIGA:
    from trezor.crypto import optiga

# have to use "==" over "in (list)" so that it can be statically replaced
# with the correct value during the build process
if (  # pylint: disable-next=consider-using-in
    utils.INTERNAL_MODEL == "T2T1"
    or utils.INTERNAL_MODEL == "T2B1"
    or utils.INTERNAL_MODEL == "T3B1"
):
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
    while True:
        try:

            if can_lock_device():
                enforce_welcome_screen_duration()
                if utils.INTERNAL_MODEL == "T2T1":
                    ui.backlight_fade(ui.BacklightLevels.NONE)
                ui.display.orientation(storage.device.get_rotation())
                if utils.USE_HAPTIC:
                    io.haptic.haptic_set_enabled(storage.device.get_haptic_feedback())
                lockscreen = Lockscreen(
                    label=storage.device.get_label(), bootscreen=True
                )
                await lockscreen
                lockscreen.__del__()
                await verify_user_pin()
                storage.init_unlocked()
                allow_all_loader_messages()
                return
            else:
                # Even if PIN is not configured, storage needs to be unlocked, unless it has just been initialized.
                if not config.is_unlocked():
                    await verify_user_pin()
                storage.init_unlocked()
                enforce_welcome_screen_duration()
                rotation = storage.device.get_rotation()
                if utils.USE_HAPTIC:
                    io.haptic.haptic_set_enabled(storage.device.get_haptic_feedback())

                if rotation != ui.display.orientation():
                    # there is a slight delay before next screen is shown,
                    # so we don't fade unless there is a change of orientation
                    if utils.INTERNAL_MODEL == "T2T1":
                        ui.backlight_fade(ui.BacklightLevels.NONE)
                    ui.display.orientation(rotation)
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


# Ignore all automated PIN messages in the boot-phase (turned off in `bootscreen()`), unless Optiga throttling delays are active.
if not utils.USE_OPTIGA or (optiga.get_sec() or 0) < 150:
    ignore_nonpin_loader_messages()

config.init(show_pin_timeout)
translations.init()

if __debug__ and not utils.EMULATOR:
    config.wipe()

loop.schedule(bootscreen())
loop.run()
