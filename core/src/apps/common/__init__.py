from micropython import const

from trezor import workflow
from trezor.messages import ButtonAck, ButtonRequest, ButtonRequestType

if False:
    from trezor import wire
    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType

HARDENED = const(0x8000_0000)


async def button_request(
    ctx: wire.GenericContext, code: EnumTypeButtonRequestType = ButtonRequestType.Other
) -> None:
    workflow.close_others()
    await ctx.call(ButtonRequest(code=code), ButtonAck)
