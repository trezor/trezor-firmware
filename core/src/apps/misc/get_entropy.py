from trezor.crypto import random
from trezor.messages import ButtonRequestType, Entropy
from trezor.ui.layouts import confirm_action

if False:
    from trezor.wire import Context
    from trezor.messages.GetEntropy import GetEntropy


async def get_entropy(ctx: Context, msg: GetEntropy) -> Entropy:
    await confirm_action(
        ctx,
        "get_entropy",
        "Confirm entropy",
        action="Do you really want\nto send entropy?",
        description="Continue only if you\nknow what you are doing!",
        br_code=ButtonRequestType.ProtectCall,
    )

    size = min(msg.size, 1024)
    entropy = random.bytes(size)

    return Entropy(entropy=entropy)
