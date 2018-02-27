from trezor import ui
from trezor.crypto import random
from trezor.messages import ButtonRequestType
from trezor.messages.Entropy import Entropy
from trezor.ui.text import Text
from apps.common.confirm import require_confirm


async def get_entropy(ctx, msg):

    await require_confirm(ctx, Text(
        'Confirm entropy', ui.ICON_DEFAULT,
        ui.BOLD, 'Do you really want', 'to send entropy?',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'),
        code=ButtonRequestType.ProtectCall)

    size = min(msg.size, 1024)
    entropy = random.bytes(size)

    return Entropy(entropy=entropy)
