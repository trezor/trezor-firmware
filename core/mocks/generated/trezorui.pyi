from typing import *


# upymod/modtrezorui/modtrezorui-display.h
class Display:
    """
    Provide access to device display.
    """
    WIDTH: int  # display width in pixels
    HEIGHT: int  # display height in pixels
    FONT_MONO: int  # id of monospace font
    FONT_NORMAL: int  # id of normal-width font
    FONT_DEMIBOLD: int  # id of demibold font
    FONT_BOLD_UPPER: int # id of bold-width-uppercased font

    def __init__(self) -> None:
        """
        Initialize the display.
        """

    def refresh(self) -> None:
        """
        Refresh display (update screen).
        """

    def bar(self, x: int, y: int, w: int, h: int, color: int) -> None:
        """
        Renders a bar at position (x,y = upper left corner) with width w and
        height h of color color.
        """

    def orientation(self, degrees: int | None = None) -> int:
        """
        Sets display orientation to 0, 90, 180 or 270 degrees.
        Everything needs to be redrawn again when this function is used.
        Call without the degrees parameter to just perform the read of the
        value.
        """

    def backlight(self, val: int | None = None) -> int:
        """
        Sets backlight intensity to the value specified in val.
        Call without the val parameter to just perform the read of the value.
        """

    def save(self, prefix: str) -> None:
        """
        Saves current display contents to PNG file with given prefix.
        """

    def clear_save(self) -> None:
        """
        Clears buffers in display saving.
        """
