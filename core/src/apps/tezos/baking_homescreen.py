from trezor import ui, loop, io
from trezor.ui.text import Text

from apps.tezos import helpers


async def baking_homescreen():
    # render homescreen in dimmed mode and fade back in
    await ui.backlight_slide(ui.BACKLIGHT_DIM)
    display_baking_homescreen()
    await ui.backlight_slide(ui.BACKLIGHT_NORMAL)

    # loop forever, never return
    touch = loop.wait(io.TOUCH)
    while True:
        await touch


def display_baking_homescreen():
    ui.display.clear()

    ui.display.bar(0, 0, ui.WIDTH, 30, ui.GREEN)
    ui.display.text_center(
        ui.WIDTH // 2, 22, "TEZOS BAKING", ui.BOLD, ui.WHITE, ui.GREEN
    )
    ui.display.bar(0, 30, ui.WIDTH, ui.HEIGHT - 30, ui.BG)

    op_type = helpers.get_last_type()

    if op_type == "Block":
        level = str(helpers.get_last_block_level())
    elif op_type == "Endorsement":
        level = str(helpers.get_last_endorsement_level())
    else:
        level = "No operation signed yet"

    text = Text("", None)
    text.bold("Last operation signed")
    text.bold("Level:")
    text.normal(level)
    text.bold("Type:")
    text.normal(op_type)
    text.render()
    ui.display.backlight(ui.BACKLIGHT_NORMAL)
