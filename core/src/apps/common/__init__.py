from micropython import const

from trezor import workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest

if False:
    from trezor import wire

HARDENED = const(0x8000_0000)


async def button_request(
    ctx: wire.GenericContext, code: ButtonRequestType = ButtonRequestType.Other
) -> None:
    workflow.close_others()
    await ctx.call(ButtonRequest(code=code), ButtonAck)
