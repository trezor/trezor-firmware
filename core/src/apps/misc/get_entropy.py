from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Entropy, GetEntropy


async def get_entropy(msg: GetEntropy) -> Entropy:
    from trezor import TR
    from trezor.crypto import random
    from trezor.enums import ButtonRequestType
    from trezor.messages import Entropy
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "get_entropy",
        TR.entropy__title_confirm,
        TR.entropy__send,
        TR.words__know_what_your_doing,
        br_code=ButtonRequestType.ProtectCall,
    )

    size = min(msg.size, 1024)
    entropy = random.bytes(size, True)

    return Entropy(entropy=entropy)
