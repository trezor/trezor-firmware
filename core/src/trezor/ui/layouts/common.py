from trezor import log, wire, workflow
from trezor.messages import ButtonRequestType, ButtonAck, ButtonRequest

if False:
    from typing import Any, Awaitable

    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType

    LayoutType = Awaitable[Any]


async def interact(
    ctx: wire.GenericContext,
    layout: LayoutType,
    brtype: str,
    brcode: EnumTypeButtonRequestType = ButtonRequestType.Other,
) -> Any:
    log.debug(__name__, "ButtonRequest.type={}".format(brtype))
    workflow.close_others()
    await ctx.call(ButtonRequest(code=brcode), ButtonAck)
    return await ctx.wait(layout)
