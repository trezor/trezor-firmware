from typing import TYPE_CHECKING

from trezor.messages import HelloWorldResponse
from trezor.ui.layouts import confirm_text

if TYPE_CHECKING:
    from trezor.messages import HelloWorldRequest


async def hello_world(msg: HelloWorldRequest) -> HelloWorldResponse:
    text = _get_text_from_msg(msg)
    if msg.show_display:
        await confirm_text(
            "confirm_hello_world",
            "Hello world",
            text,
            description="Hello world example",
        )
    return HelloWorldResponse(text=text)


def _get_text_from_msg(msg: HelloWorldRequest) -> str:
    return msg.amount * f"Hello {msg.name}!\n"
