from typing import TYPE_CHECKING

from trezor.messages import SecureInput
from trezor.ui.components.tt.passphrase import PassphraseKeyboard as Keyboard

if TYPE_CHECKING:
    from trezor.wire import Context
    from trezor.messages import GetSecureInput


async def secure_input(ctx: Context, msg: GetSecureInput) -> SecureInput:
    keyboard = Keyboard(msg.prompt, msg.max_length)
    text = await ctx.wait(keyboard)

    return SecureInput(text=text)
