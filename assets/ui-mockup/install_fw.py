#!../../vendor/micropython/unix/micropython
import sys
sys.path.append('../../src')

import utime
from trezor import ui, res
from trezor.ui import button
from bl_common import bl_header

CONFIRM_BUTTON = {
    'bg-color': ui.GREEN,
    'fg-color': ui.LIGHT_GREEN,
    'text-style': ui.BOLD,
    'border-color': ui.GREEN,
}
CONFIRM_BUTTON_ACTIVE = {
    'bg-color': ui.GREEN,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.GREEN,
}
CANCEL_BUTTON = {
    'bg-color': ui.RED,
    'fg-color': ui.LIGHT_RED,
    'text-style': ui.BOLD,
    'border-color': ui.RED,
}
CANCEL_BUTTON_ACTIVE = {
    'bg-color': ui.RED,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
    'border-color': ui.RED,
}

ui.display.clear()
ui.display.backlight(255)

# header
bl_header('Install new firmware')

# content
ui.display.text(10, 53, 'SatoshiLabs v0.1.1', ui.NORMAL, ui.WHITE, ui.BLACK)

def fingerprint():
    ui.display.bar(0, 60, 240, 128, ui.BLACK)
    ui.display.text(10, 76, 'Fingerprint:', ui.BOLD, ui.GREY, ui.BLACK)
    ui.display.bar(10, 82, 220, 102, ui.DARK_GREY)
    s = 105
    ui.display.text(15, s, '5764715dbcf8ed88', ui.MONO, ui.GREY, ui.DARK_GREY)
    ui.display.text(15, s + 1 * 23, 'bc0ae1c2f715277f', ui.MONO, ui.GREY, ui.DARK_GREY)
    ui.display.text(15, s + 2 * 23, '22b67f26c15e1f75', ui.MONO, ui.GREY, ui.DARK_GREY)
    ui.display.text(15, s + 3 * 23, '43b2b44913b5c255', ui.MONO, ui.GREY, ui.DARK_GREY)

def logo():
    ui.display.bar(0, 60, 240, 128, ui.BLACK)
    image = res.load('./res/sl_logo.toif')
    ui.display.image(60, 64, image)

confirm = button.Button((121, 240 - 48, 119, 48), 'Confirm', normal_style=CONFIRM_BUTTON, active_style=CONFIRM_BUTTON_ACTIVE)
confirm.render()
cancel = button.Button((0, 240 - 48, 119, 48), 'Cancel', normal_style=CANCEL_BUTTON, active_style=CANCEL_BUTTON_ACTIVE)
cancel.render()

while True:
    logo()
    ui.display.refresh()
    utime.sleep(2)

    fingerprint()
    ui.display.refresh()
    utime.sleep(2)
