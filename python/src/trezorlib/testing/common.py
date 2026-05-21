from typing import TYPE_CHECKING, Generator, Union

from .. import messages
from ..debuglink import LayoutType

if TYPE_CHECKING:

    from ..debuglink import DebugLink


BRGeneratorType = Generator[None, messages.ButtonRequest, None]

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]


def compact_size(n: int) -> bytes:
    if n < 253:
        return n.to_bytes(1, "little")
    elif n < 0x1_0000:
        return bytes([253]) + n.to_bytes(2, "little")
    elif n < 0x1_0000_0000:
        return bytes([254]) + n.to_bytes(4, "little")
    else:
        return bytes([255]) + n.to_bytes(8, "little")


def get_text_possible_pagination(debug: "DebugLink", br: messages.ButtonRequest) -> str:
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
    br = yield
    if br_code is not None:
        assert br.code == br_code
    swipe_till_the_end(debug, br)


def swipe_till_the_end(debug: "DebugLink", br: messages.ButtonRequest) -> None:
    if br.pages is not None:
        for _ in range(br.pages - 1):
            debug.swipe_up()
