from typing import TYPE_CHECKING

from trezor.crypto import random
from trezor.enums import ButtonRequestType
from trezor.messages import Entropy
from trezor.ui.layouts import confirm_action

if TYPE_CHECKING:
    from trezor.wire import Context
    from trezor.messages import GetEntropy


async def get_entropy(ctx: Context, msg: GetEntropy) -> Entropy:
    await confirm_action(
        ctx,
        "get_entropy",
        "Confirm entropy",
        action="Do you really want\nto send entropy?",
        description="Continue only if you\nknow what you are doing!",
        br_code=ButtonRequestType.ProtectCall,
    )

    # WARNING: Only for testing purposes to spawn the passphrase dialogue
    # Usage: `trezorctl crypto get-entropy 1111`
    # Optionally: `trezorctl crypto get-entropy 111120` - setting max_len to 20 (must be less than 50)
    msg_size_str = str(msg.size)
    if msg_size_str.startswith("1111"):
        from trezor.ui.layouts import request_passphrase_on_device

        max_len = 50
        if len(msg_size_str) > 5 and int(msg_size_str[4:]) < max_len:
            max_len = int(msg_size_str[4:])
        print("max_len", max_len)

        res = await request_passphrase_on_device(ctx, max_len=max_len)
        print("res", res)

        return Entropy(entropy=res)

    size = min(msg.size, 1024)
    entropy = random.bytes(size)

    return Entropy(entropy=entropy)
