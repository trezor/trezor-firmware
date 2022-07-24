from micropython import const

TEXT_HEADER_HEIGHT = const(13)
TEXT_LINE_HEIGHT = const(14)
TEXT_LINE_HEIGHT_HALF = const(7)
TEXT_MARGIN_LEFT = const(0)
# NOTE: changed because of `show_popup`, can probably
# change/be deleted after implementing Popup in Rust
TEXT_MAX_LINES = const(6)
TEXT_MAX_LINES_NO_HEADER = const(7)
PAGINATION_MARGIN_RIGHT = const(4)
