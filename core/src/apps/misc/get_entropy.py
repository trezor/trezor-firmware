from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import Context
    from trezor.messages import GetEntropy, Entropy


async def get_entropy(ctx: Context, msg: GetEntropy) -> Entropy:
    from trezor.crypto import random
    from trezor.enums import ButtonRequestType
    from trezor.messages import Entropy
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        ctx,
        "get_entropy",
        "Confirm entropy",
        "Do you really want to send entropy?",
        "Continue only if you know what you are doing!",
        br_code=ButtonRequestType.ProtectCall,
    )

    size = min(msg.size, 1024)
    entropy = random.bytes(size)

    return Entropy(entropy=entropy)
