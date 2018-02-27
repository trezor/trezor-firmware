from trezor import ui


async def get_entropy(ctx, msg):
    from trezor.messages.Entropy import Entropy
    from trezor.crypto import random

    l = min(msg.size, 1024)

    await _show_entropy(ctx)

    return Entropy(entropy=random.bytes(l))


async def _show_entropy(ctx):
    from trezor.messages.ButtonRequestType import ProtectCall
    from trezor.ui.text import Text
    from ..common.confirm import require_confirm

    await require_confirm(ctx, Text(
        'Confirm entropy', ui.ICON_DEFAULT,
        ui.BOLD, 'Do you really want', 'to send entropy?',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'),
        code=ProtectCall)
