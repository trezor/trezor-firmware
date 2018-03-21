from apps.common.confirm import *
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text

# todo wording, ui


async def require_confirm_tx(ctx, recipient, value):
    content = Text('Confirm sending', ui.ICON_SEND,
                   ui.BOLD, value,
                   ui.NORMAL, 'to',
                   ui.MONO, recipient,
                   icon_color=ui.GREEN)
    await require_hold_to_confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


async def require_confirm_fee(ctx, value, fee):
    content = Text('Confirm transaction', ui.ICON_SEND,
                   ui.BOLD, value,
                   ui.NORMAL, 'fee:',
                   ui.BOLD, fee,
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_action(ctx, payload, encrypt=False):
    if encrypt:
        content = Text("Send payload encrypted?", ui.ICON_SEND,
                       ui.NORMAL, payload)
    else:
        content = Text("Send payload unencrypted?", ui.ICON_SEND,
                       ui.NORMAL, payload,
                       icon_color=ui.RED)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)
