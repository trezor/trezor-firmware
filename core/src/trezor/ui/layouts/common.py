from trezor import log, wire, workflow
from trezor.messages import ButtonRequestType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest

if False:
    from typing import Any, Awaitable

    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType

    LayoutType = Awaitable[Any]


async def button_request(
    ctx: wire.GenericContext,
    br_type: str,
    code: EnumTypeButtonRequestType = ButtonRequestType.Other,
) -> None:
    log.debug(__name__, "ButtonRequest.type={}".format(br_type))
    workflow.close_others()
    await ctx.call(ButtonRequest(code=code), ButtonAck)


async def interact(
    ctx: wire.GenericContext,
    layout: LayoutType,
    br_type: str,
    br_code: EnumTypeButtonRequestType = ButtonRequestType.Other,
) -> Any:
    await button_request(ctx, br_type, br_code)
    return await ctx.wait(layout)
