from typing import TYPE_CHECKING, Generator, Optional

from .. import messages
from ..debuglink import LayoutType

if TYPE_CHECKING:

    from ..debuglink import DebugLink


BRGeneratorType = Generator[None, messages.ButtonRequest, None]

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]


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
    debug: "DebugLink",
    br_code: Optional[messages.ButtonRequestType] = None,
    br_name: Optional[str] = None,
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
    if br_name is not None:
        assert br.name == br_name
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
