from trezor.crypto import random
from trezor.messages import ButtonRequestType
from trezor.messages.Entropy import Entropy
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm


async def get_entropy(ctx, msg):
    text = Text("Confirm entropy")
    text.bold("Do you really want", "to send entropy?")
    text.normal("Continue only if you", "know what you are doing!")
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)

    size = min(msg.size, 1024)
    entropy = random.bytes(size)

    return Entropy(entropy=entropy)
