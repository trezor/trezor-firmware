from typing import TYPE_CHECKING

from trezor.crypto import random
from trezor.enums import ButtonRequestType
from trezor.messages import Entropy
from trezor.ui.layouts import confirm_action

from apps.management import text_r

if TYPE_CHECKING:
    from trezor.wire import Context
    from trezor.messages import GetEntropy


async def get_entropy(ctx: Context, msg: GetEntropy) -> Entropy:
    await confirm_action(
        ctx,
        "get_entropy",
        "Confirm entropy",
        action=text_r("Do you really want\nto send entropy?"),
        description=text_r("Continue only if you\nknow what you are doing!"),
        br_code=ButtonRequestType.ProtectCall,
    )

    size = min(msg.size, 1024)
    entropy = random.bytes(size)

    return Entropy(entropy=entropy)
