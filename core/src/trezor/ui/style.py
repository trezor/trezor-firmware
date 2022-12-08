from micropython import const

from trezor.ui import rgb

# backlight brightness
BACKLIGHT_NORMAL = const(150)
BACKLIGHT_LOW = const(45)
BACKLIGHT_DIM = const(5)
BACKLIGHT_NONE = const(0)
BACKLIGHT_MAX = const(255)

# color palette
RED = rgb(0xFF, 0x00, 0x00)
BLUE = rgb(0x21, 0x96, 0xF3)
GREEN = rgb(0x00, 0xAE, 0x0B)
YELLOW = rgb(0xFF, 0xEB, 0x3B)
BLACK = rgb(0x00, 0x00, 0x00)
WHITE = rgb(0xFA, 0xFA, 0xFA)

TITLE_GREY = rgb(0x9B, 0x9B, 0x9B)

# common color styles
BG = BLACK
FG = WHITE

# icons
ICON_CONFIG = "trezor/res/header_icons/cog.toif"
ICON_SEND = "trezor/res/header_icons/send.toif"
ICON_CLICK = "trezor/res/click.toif"
ICON_CHECK = "trezor/res/check.toif"
ICON_DEFAULT = ICON_CONFIG
