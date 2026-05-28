from typing import TYPE_CHECKING, Generator, Union

from .. import messages
from ..debuglink import LayoutType

if TYPE_CHECKING:

    from ..debuglink import DebugLink


BRGeneratorType = Generator[None, messages.ButtonRequest, None]

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]


def compact_size(n: int) -> bytes:
    """
    Encode an integer using Bitcoin's compact size format.

    Args:
        n (int): The integer to encode.

    Returns:
        bytes: The encoded integer.

    Raises:
        ValueError: If n is not in the range 0..2^64-1.
    """
    if n < 0 or n > 0xFFFF_FFFF_FFFF_FFFF:
        raise ValueError("compact_size supports integers in range 0..2^64-1")
    if n < 253:
        return n.to_bytes(1, "little")
    elif n < 0x1_0000:
        return bytes([253]) + n.to_bytes(2, "little")
    elif n < 0x1_0000_0000:
        return bytes([254]) + n.to_bytes(4, "little")
    else:
        return bytes([255]) + n.to_bytes(8, "little")


def get_text_possible_pagination(debug: "DebugLink", br: messages.ButtonRequest) -> str:
    """
    Read all text content from the device, handling possible pagination.

    Args:
        debug (DebugLink): The debug link to interact with the device.
        br (ButtonRequest): The button request containing pagination info.

    Returns:
        str: The concatenated text from all pages.
    """
    text = debug.read_layout().text_content()
    if br.pages is not None:
        for _ in range(br.pages - 1):
            if debug.layout_type is LayoutType.Eckhart:
                debug.click(debug.screen_buttons.ok())
            else:
                debug.swipe_up()
            text += " "
            text += debug.read_layout().text_content()
    return text


def swipe_if_necessary(
    debug: "DebugLink", br_code: Union[messages.ButtonRequestType, None] = None
) -> BRGeneratorType:
    """
    Generator that swipes through pages if necessary, based on button request code.

    Args:
        debug (DebugLink): The debug link to interact with the device.
        br_code (ButtonRequestType or None): Expected button request code.

    Yields:
        ButtonRequest: The button request to process.
    """
    br = yield
    if br_code is not None:
        assert br.code == br_code
    swipe_till_the_end(debug, br)


def swipe_till_the_end(debug: "DebugLink", br: messages.ButtonRequest) -> None:
    """
    Swipe through all pages until the end.

    Args:
        debug (DebugLink): The debug link to interact with the device.
        br (ButtonRequest): The button request containing pagination info.
    """
    if br.pages is not None:
        for _ in range(br.pages - 1):
            debug.swipe_up()
