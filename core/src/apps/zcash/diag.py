# if __debug__:

from trezor.messages import DebugZcashDiagRequest, DebugZcashDiagResponse
#from trezor.crypto import random
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_action, draw_simple_text

from trezor import log

async def diag(ctx: Context, msg: DebugZcashDiagRequest) -> DebugZcashDiagResponse:
    log.debug(__name__, "Zcash Diag. data={}".format(msg.data))

    await confirm_action(
        ctx,
        "test",
        "Confirm test",
        action="msg: {}".format(msg.data),
        description="continue",
        br_code=ButtonRequestType.ProtectCall,
    )

    return DebugZcashDiagResponse(data=b"Hello from the Trezor!") 