from trezor import ui

def rgb2color(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)

RED         = rgb2color(0xF4, 0x43, 0x36)
PINK        = rgb2color(0xE9, 0x1E, 0x63)
PURPLE      = rgb2color(0x9C, 0x27, 0xB0)
DEEP_PURPLE = rgb2color(0x67, 0x3A, 0xB7)
INDIGO      = rgb2color(0x3F, 0x51, 0xB5)
BLUE        = rgb2color(0x21, 0x96, 0xF3)
LIGHT_BLUE  = rgb2color(0x03, 0xA9, 0xF4)
CYAN        = rgb2color(0x00, 0xBC, 0xD4)
TEAL        = rgb2color(0x00, 0x96, 0x88)
GREEN       = rgb2color(0x4C, 0xAF, 0x50)
LIGHT_GREEN = rgb2color(0x8B, 0xC3, 0x4A)
LIME        = rgb2color(0xCD, 0xDC, 0x39)
YELLOW      = rgb2color(0xFF, 0xEB, 0x3B)
AMBER       = rgb2color(0xFF, 0xC1, 0x07)
ORANGE      = rgb2color(0xFF, 0x98, 0x00)
DEEP_ORANGE = rgb2color(0xFF, 0x57, 0x22)
BROWN       = rgb2color(0x79, 0x55, 0x48)
GREY        = rgb2color(0x9E, 0x9E, 0x9E)
BLUE_GRAY   = rgb2color(0x60, 0x7D, 0x8B)
BLACK       = rgb2color(0x00, 0x00, 0x00)
WHITE       = rgb2color(0xFF, 0xFF, 0xFF)

MONO   = 0
NORMAL = 1
BOLD   = 2

def show_send(address, amount, currency='BTC'):
   ui.display.bar(0, 0, 240, 40, GREEN)
   ui.display.bar(0, 40, 240, 200, WHITE)
   ui.display.text(10, 28, 'Sending', BOLD, WHITE, GREEN)
   ui.display.text(10, 80, '%f %s' % (amount, currency), BOLD, BLACK, WHITE)
   ui.display.text(10, 110, 'to this address:', NORMAL, BLACK, WHITE)
   ui.display.text(10, 140, address[:18], MONO, BLACK, WHITE)
   ui.display.text(10, 160, address[18:], MONO, BLACK, WHITE)