from trezor import config
from trezor import loop
from trezor import ui

from apps.common.request_pin import request_pin


async def unlock_layout():
    while True:
        if config.has_pin():
            pin = await request_pin()
        else:
            pin = ''
        if config.unlock(pin):
            return
        else:
            await unlock_failed()


async def unlock_failed():
    pass


config.init()
ui.display.backlight(ui.BACKLIGHT_DIM)
loop.schedule(unlock_layout())
loop.run()
