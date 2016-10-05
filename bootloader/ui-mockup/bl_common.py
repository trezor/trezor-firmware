from trezor import ui, res

BL_HEADER_FG = ui.BLACK
BL_HEADER_BG = ui.ORANGE

def bl_header(title):
    ui.display.bar(0, 0, 240, 32, BL_HEADER_BG)
    image = res.load('./res/bootloader.toig')
    ui.display.icon(8, 4, image, BL_HEADER_FG, BL_HEADER_BG)
    ui.display.text(8 + 24 + 8, 23, title, ui.BOLD, BL_HEADER_FG, BL_HEADER_BG)
