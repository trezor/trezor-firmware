from micropython import const

from trezor.ui import BOLD, MONO, NORMAL, rgb

# radius for buttons and other elements
RADIUS = const(2)

# backlight brightness
BACKLIGHT_NORMAL = const(150)
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

TITLE_GREY = rgb(0x9B, 0x9B, 0x9B)
ORANGE_ICON = rgb(0xF5, 0xA6, 0x23)

# common color styles
BG = BLACK
FG = WHITE

# icons
ICON_RESET = "trezor/res/header_icons/reset.toig"
ICON_WIPE = "trezor/res/header_icons/wipe.toig"
ICON_RECOVERY = "trezor/res/header_icons/recovery.toig"
ICON_NOCOPY = "trezor/res/header_icons/nocopy.toig"
ICON_WRONG = "trezor/res/header_icons/wrong.toig"
ICON_CONFIG = "trezor/res/header_icons/cog.toig"
ICON_RECEIVE = "trezor/res/header_icons/receive.toig"
ICON_SEND = "trezor/res/header_icons/send.toig"

ICON_DEFAULT = ICON_CONFIG

ICON_CANCEL = "trezor/res/cancel.toig"
ICON_CONFIRM = "trezor/res/confirm.toig"
ICON_LOCK = "trezor/res/lock.toig"
ICON_CLICK = "trezor/res/click.toig"
ICON_BACK = "trezor/res/left.toig"
ICON_SWIPE = "trezor/res/swipe.toig"
ICON_CHECK = "trezor/res/check.toig"
ICON_SPACE = "trezor/res/space.toig"

# buttons
BTN_DEFAULT = {
    "normal": {
        "bg-color": BG,
        "fg-color": FG,
        "text-style": NORMAL,
        "border-color": BG,
        "radius": RADIUS,
    },
    "active": {
        "bg-color": FG,
        "fg-color": BG,
        "text-style": BOLD,
        "border-color": FG,
        "radius": RADIUS,
    },
    "disabled": {
        "bg-color": BG,
        "fg-color": GREY,
        "text-style": NORMAL,
        "border-color": BG,
        "radius": RADIUS,
    },
}

BTN_CANCEL = {
    "normal": {
        "bg-color": RED,
        "fg-color": FG,
        "text-style": BOLD,
        "border-color": BG,
        "radius": RADIUS,
    },
    "active": {
        "bg-color": FG,
        "fg-color": RED,
        "text-style": BOLD,
        "border-color": FG,
        "radius": RADIUS,
    },
    "disabled": {
        "bg-color": BG,
        "fg-color": GREY,
        "text-style": NORMAL,
        "border-color": BG,
        "radius": RADIUS,
    },
}

BTN_CONFIRM = {
    "normal": {
        "bg-color": GREEN,
        "fg-color": FG,
        "text-style": BOLD,
        "border-color": BG,
        "radius": RADIUS,
    },
    "active": {
        "bg-color": FG,
        "fg-color": GREEN,
        "text-style": BOLD,
        "border-color": FG,
        "radius": RADIUS,
    },
    "disabled": {
        "bg-color": BG,
        "fg-color": GREY,
        "text-style": NORMAL,
        "border-color": BG,
        "radius": RADIUS,
    },
}

BTN_CLEAR = {
    "normal": {
        "bg-color": ORANGE,
        "fg-color": FG,
        "text-style": NORMAL,
        "border-color": BG,
        "radius": RADIUS,
    },
    "active": {
        "bg-color": BG,
        "fg-color": GREY,
        "text-style": NORMAL,
        "border-color": BG,
        "radius": RADIUS,
    },
    "disabled": {
        "bg-color": BG,
        "fg-color": GREY,
        "text-style": MONO,
        "border-color": BG,
        "radius": RADIUS,
    },
}

BTN_KEY = {
    "normal": {
        "bg-color": BLACKISH,
        "fg-color": FG,
        "text-style": MONO,
        "border-color": BG,
        "radius": RADIUS,
    },
    "active": {
        "bg-color": FG,
        "fg-color": BLACKISH,
        "text-style": MONO,
        "border-color": FG,
        "radius": RADIUS,
    },
    "disabled": {
        "bg-color": BG,
        "fg-color": GREY,
        "text-style": MONO,
        "border-color": BG,
        "radius": RADIUS,
    },
}

BTN_KEY_CONFIRM = {
    "normal": {
        "bg-color": GREEN,
        "fg-color": FG,
        "text-style": MONO,
        "border-color": BG,
        "radius": RADIUS,
    },
    "active": {
        "bg-color": FG,
        "fg-color": GREEN,
        "text-style": MONO,
        "border-color": FG,
        "radius": RADIUS,
    },
    "disabled": {
        "bg-color": BG,
        "fg-color": GREY,
        "text-style": MONO,
        "border-color": BG,
        "radius": RADIUS,
    },
}

# loader
LDR_DEFAULT = {
    "normal": {"bg-color": BG, "fg-color": GREEN, "icon": None, "icon-fg-color": None},
    "active": {
        "bg-color": BG,
        "fg-color": GREEN,
        "icon": ICON_CHECK,
        "icon-fg-color": WHITE,
    },
}

LDR_DANGER = {
    "normal": {"bg-color": BG, "fg-color": RED, "icon": None, "icon-fg-color": None},
    "active": {
        "bg-color": BG,
        "fg-color": RED,
        "icon": ICON_CHECK,
        "icon-fg-color": WHITE,
    },
}
