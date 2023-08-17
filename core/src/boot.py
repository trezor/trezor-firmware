# isort:skip_file

import trezorui2

# Showing welcome screen as soon as possible
# (display is also prepared on that occasion).
# Remembering time to control how long we show it.
trezorui2.draw_welcome_screen()

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
                await lockscreen
            await verify_user_pin()
            storage.init_unlocked()
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
