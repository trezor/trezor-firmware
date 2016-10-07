
# ../extmod/modtrezorui/modtrezorui-display.h
def clear() -> None
    '''
    Clear display (with black color)
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def refresh() -> None
    '''
    Refresh display (update screen)
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def bar(x: int, y: int, w: int, h: int, color: int) -> None:
    '''
    Renders a bar at position (x,y = upper left corner) with width w and height h of color color.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def bar_radius(x: int, y: int, w: int, h: int, fgcolor: int, bgcolor: int=None, radius: int=None) -> None:
    '''
    Renders a rounded bar at position (x,y = upper left corner) with width w and height h of color fgcolor.
    Background is set to bgcolor and corners are drawn with radius radius.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def blit(x: int, y: int, w: int, h: int, data: bytes) -> None:
    '''
    Renders rectangle at position (x,y = upper left corner) with width w and height h with data.
    The data needs to have the correct format.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def image(x: int, y: int, image: bytes) -> None:
    '''
    Renders an image at position (x,y).
    The image needs to be in TREZOR Optimized Image Format (TOIF) - full-color mode.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def icon(x: int, y: int, icon: bytes, fgcolor: int, bgcolor: int) -> None:
    '''
    Renders an icon at position (x,y), fgcolor is used as foreground color, bgcolor as background.
    The image needs to be in TREZOR Optimized Image Format (TOIF) - gray-scale mode.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def text(x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None:
    '''
    Renders left-aligned text at position (x,y) where x is left position and y is baseline.
    Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def text_center(x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None:
    '''
    Renders text centered at position (x,y) where x is text center and y is baseline.
    Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def text_right(x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None:
    '''
    Renders right-aligned text at position (x,y) where x is right position and y is baseline.
    Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def text_width(text: bytes, font: int) -> int:
    '''
    Returns a width of text in pixels. Font font is used for rendering.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def qrcode(x: int, y: int, data: bytes, scale: int) -> None:
    '''
    Renders data encoded as a QR code at position (x,y).
    Scale determines a zoom factor.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def loader(progress: int, fgcolor: int, bgcolor: int, icon: bytes=None, iconfgcolor: int=None) -> None:
    '''
    Renders a rotating loader graphic.
    Progress determines its position (0-1000), fgcolor is used as foreground color, bgcolor as background.
    When icon and iconfgcolor are provided, an icon is drawn in the middle using the color specified in iconfgcolor.
    Icon needs to be of exaclty 96x96 pixels size.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def orientation(degrees: int=None) -> int:
    '''
    Sets display orientation to 0, 90, 180 or 270 degrees.
    Everything needs to be redrawn again when this function is used.
    Call without the degrees parameter to just perform the read of the value.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def backlight(val: int=None) -> int:
    '''
    Sets backlight intensity to the value specified in val.
    Call without the val parameter to just perform the read of the value.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def raw(reg: int, data: bytes) -> None:
    '''
    Performs a raw command on the display. Read the datasheet to learn more.
    '''

# ../extmod/modtrezorui/modtrezorui-display.h
def save(filename: string) -> None:
    '''
    Saves current display contents to file filename.
    '''
