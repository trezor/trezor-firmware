from typing import *

# extmod/modtrezorui/modtrezorui-display.h
class Display:
    '''
    Provide access to device display.
    '''

    def __init__(self) -> None:
        '''
        Initialize the display.
        '''

    def clear(self) -> None:
        '''
        Clear display with black color.
        '''

    def refresh(self) -> None:
        '''
        Refresh display (update screen).
        '''

    def bar(self, x: int, y: int, w: int, h: int, color: int) -> None:
        '''
        Renders a bar at position (x,y = upper left corner) with width w and height h of color color.
        '''

    def bar_radius(self, x: int, y: int, w: int, h: int, fgcolor: int, bgcolor: int = None, radius: int = None) -> None:
        '''
        Renders a rounded bar at position (x,y = upper left corner) with width w and height h of color fgcolor.
        Background is set to bgcolor and corners are drawn with radius radius.
        '''

    def image(self, x: int, y: int, image: bytes) -> None:
        '''
        Renders an image at position (x,y).
        The image needs to be in TREZOR Optimized Image Format (TOIF) - full-color mode.
        '''

    def avatar(self, x: int, y: int, image: bytes, fgcolor: int, bgcolor: int) -> None:
        '''
        Renders an avatar at position (x,y).
        The image needs to be in TREZOR Optimized Image Format (TOIF) - full-color mode.
        Image needs to be of exactly AVATAR_IMAGE_SIZE x AVATAR_IMAGE_SIZE pixels size.
        '''

    def icon(self, x: int, y: int, icon: bytes, fgcolor: int, bgcolor: int) -> None:
        '''
        Renders an icon at position (x,y), fgcolor is used as foreground color, bgcolor as background.
        The icon needs to be in TREZOR Optimized Image Format (TOIF) - gray-scale mode.
        '''

    def print(self, text: str) -> None:
        '''
        Renders text using 5x8 bitmap font (using special text mode).
        '''

    def text(self, x: int, y: int, text: str, font: int, fgcolor: int, bgcolor: int, minwidth: int=None) -> None:
        '''
        Renders left-aligned text at position (x,y) where x is left position and y is baseline.
        Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
        '''

    def text_center(self, x: int, y: int, text: str, font: int, fgcolor: int, bgcolor: int, minwidth: int=None) -> None:
        '''
        Renders text centered at position (x,y) where x is text center and y is baseline.
        Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
        '''

    def text_right(self, x: int, y: int, text: str, font: int, fgcolor: int, bgcolor: int, minwidth: int=None) -> None:
        '''
        Renders right-aligned text at position (x,y) where x is right position and y is baseline.
        Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
        '''

    def text_width(self, text: str, font: int) -> int:
        '''
        Returns a width of text in pixels. Font font is used for rendering.
        '''

    def qrcode(self, x: int, y: int, data: bytes, scale: int) -> None:
        '''
        Renders data encoded as a QR code centered at position (x,y).
        Scale determines a zoom factor.
        '''

    def loader(self, progress: int, yoffset: int, fgcolor: int, bgcolor: int, icon: bytes = None, iconfgcolor: int = None) -> None:
        '''
        Renders a rotating loader graphic.
        Progress determines its position (0-1000), fgcolor is used as foreground color, bgcolor as background.
        When icon and iconfgcolor are provided, an icon is drawn in the middle using the color specified in iconfgcolor.
        Icon needs to be of exactly LOADER_ICON_SIZE x LOADER_ICON_SIZE pixels size.
        '''

    def orientation(self, degrees: int = None) -> int:
        '''
        Sets display orientation to 0, 90, 180 or 270 degrees.
        Everything needs to be redrawn again when this function is used.
        Call without the degrees parameter to just perform the read of the value.
        '''

    def backlight(self, val: int = None) -> int:
        '''
        Sets backlight intensity to the value specified in val.
        Call without the val parameter to just perform the read of the value.
        '''

    def offset(self, xy: Tuple[int, int] = None) -> Tuple[int, int]:
        '''
        Sets offset (x, y) for all subsequent drawing calls.
        Call without the xy parameter to just perform the read of the value.
        '''

    def save(self, prefix: str) -> None:
        '''
        Saves current display contents to PNG file with given prefix.
        '''
