from typing import *
from buffer_types import *


# upymod/modtrezorui/modtrezorui-display.h
class Display:
    """
    Provide access to device display.
    """
    WIDTH: int  # display width in pixels
    HEIGHT: int  # display height in pixels

    def __init__(self) -> None:
        """
        Initialize the display.
        """

    def orientation(self, degrees: int | None = None) -> int:
        """
        Sets display orientation to 0, 90, 180 or 270 degrees.
        Everything needs to be redrawn again when this function is used.
        Call without the degrees parameter to just perform the read of the
        value.
        """

    def record_start(
        self, target_directory: AnyBytes, refresh_index: int
    ) -> None:
        """
        Starts screen recording with specified target directory and refresh
        index.
        """

    def record_stop(self) -> None:
        """
        Stops screen recording.
        """

    def record_read(self) -> tuple[list[bytes], bytes]:
        """
        Returns the hashes of distinct screens painted since the previous call
        and the running hash over all screens since the recording started.
        """

    def record_read_screen(
        self, offset: int, length: int
    ) -> tuple[int, int, str, bytes, int, bytes]:
        """
        Reads a chunk of the displayed screen, converted the way the recorded
        hashes are computed. Returns (width, height, mode, hash of the last
        recorded screen, total size, data).
        """
