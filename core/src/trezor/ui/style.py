from micropython import const

from trezor.ui import rgb

# radius for buttons and other elements
RADIUS = const(2)

# backlight brightness
BACKLIGHT_NORMAL = const(150)
BACKLIGHT_LOW = const(45)
BACKLIGHT_DIM = const(5)
BACKLIGHT_NONE = const(2)
BACKLIGHT_MAX = const(255)

# color palette
RED = rgb(0xFF, 0x00, 0x00)
PINK = rgb(0xE9, 0x1E, 0x63)
PURPLE = rgb(0x9C, 0x27, 0xB0)
DEEP_PURPLE = rgb(0x67, 0x3A, 0xB7)
INDIGO = rgb(0x3F, 0x51, 0xB5)
BLUE = rgb(0x21, 0x96, 0xF3)
LIGHT_BLUE = rgb(0x03, 0xA9, 0xF4)
CYAN = rgb(0x00, 0xBC, 0xD4)
TEAL = rgb(0x00, 0x96, 0x88)
GREEN = rgb(0x00, 0xAE, 0x0B)
LIGHT_GREEN = rgb(0x87, 0xCE, 0x26)
LIME = rgb(0xCD, 0xDC, 0x39)
YELLOW = rgb(0xFF, 0xEB, 0x3B)
AMBER = rgb(0xFF, 0xC1, 0x07)
ORANGE = rgb(0xFF, 0x98, 0x00)
DEEP_ORANGE = rgb(0xFF, 0x57, 0x22)
BROWN = rgb(0x79, 0x55, 0x48)
LIGHT_GREY = rgb(0xDA, 0xDD, 0xD8)
GREY = rgb(0x9E, 0x9E, 0x9E)
DARK_GREY = rgb(0x3E, 0x3E, 0x3E)
BLUE_GRAY = rgb(0x60, 0x7D, 0x8B)
BLACK = rgb(0x00, 0x00, 0x00)
WHITE = rgb(0xFA, 0xFA, 0xFA)
BLACKISH = rgb(0x30, 0x30, 0x30)
DARK_BLACK = rgb(0x10, 0x10, 0x10)
DARK_WHITE = rgb(0xE8, 0xE8, 0xE8)

TITLE_GREY = rgb(0x9B, 0x9B, 0x9B)
ORANGE_ICON = rgb(0xF5, 0xA6, 0x23)

# common color styles
BG = BLACK
FG = WHITE

# icons
ICON_RESET = "trezor/res/header_icons/reset.toif"
ICON_WIPE = "trezor/res/header_icons/wipe.toif"
ICON_RECOVERY = "trezor/res/header_icons/recovery.toif"
ICON_NOCOPY = "trezor/res/header_icons/nocopy.toif"
ICON_WRONG = "trezor/res/header_icons/wrong.toif"
ICON_CONFIG = "trezor/res/header_icons/cog.toif"
ICON_RECEIVE = "trezor/res/header_icons/receive.toif"
ICON_SEND = "trezor/res/header_icons/send.toif"

ICON_DEFAULT = ICON_CONFIG

ICON_CANCEL = "trezor/res/cancel.toif"
ICON_CONFIRM = "trezor/res/confirm.toif"
ICON_LOCK = "trezor/res/lock.toif"
ICON_CLICK = "trezor/res/click.toif"
ICON_BACK = "trezor/res/left.toif"
ICON_SWIPE = "trezor/res/swipe.toif"
ICON_SWIPE_LEFT = "trezor/res/swipe_left.toif"
ICON_SWIPE_RIGHT = "trezor/res/swipe_right.toif"
ICON_CHECK = "trezor/res/check.toif"
ICON_SPACE = "trezor/res/space.toif"
