"""
The model/common module contains code that is used by both model/tt and model/t1.
"""

from trezor import log
from trezor.messages import ButtonRequestType

from apps.common import button_request

if False:
    from typing import List, Union, Awaitable, Any

    TextContent = Union[str, int]

    from trezor import wire
    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType


async def interact(
    ctx: wire.GenericContext,
    widget: Awaitable,
    brtype: str,
    brcode: EnumTypeButtonRequestType = ButtonRequestType.Other,
) -> Any:
    log.debug(__name__, "ButtonRequest.type={}".format(brtype))
    await button_request(ctx, code=brcode)
    return await ctx.wait(widget)


def break_path_to_lines(path_str: str, per_line: int) -> List[str]:
    lines = []
    while len(path_str) > per_line:
        i = path_str[:per_line].rfind("/")
        lines.append(path_str[:i])
        path_str = path_str[i:]
    lines.append(path_str)

    return lines
