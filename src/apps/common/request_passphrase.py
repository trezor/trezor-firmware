from trezor import ui, wire, res


async def request_passphrase(ctx):
    from trezor.messages.FailureType import ActionCancelled
    from trezor.messages.PassphraseRequest import PassphraseRequest
    from trezor.messages.wire_types import PassphraseAck, Cancel
    from trezor.ui.text import Text
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.ui.entry_select import EntrySelector
    from trezor.ui.keyboard import PassphraseKeyboard

    ui.display.clear()
    text = Text('Enter passphrase', ui.ICON_RESET,
                'Where to enter your', 'passphrase?')
    entry = EntrySelector(text)
    entry_type = await entry

    if entry_type == 1:
        ui.display.clear()
        text = Text('Passphrase entry', ui.ICON_RESET,
                    'Please, type passphrase', 'on connected host.')
        text.render()
        ack = await ctx.call(PassphraseRequest(), PassphraseAck, Cancel)
        if ack.MESSAGE_WIRE_TYPE == Cancel:
            raise wire.FailureError(ActionCancelled, 'Passphrase cancelled')
        return ack.passphrase
    else:
        def onchange():
            c = dialog.cancel
            if keyboard.passphrase:
                c.content = res.load(ui.ICON_CLEAR)
            else:
                c.content = res.load(ui.ICON_LOCK)
            c.taint()
            c.render()

        ui.display.clear()
        keyboard = PassphraseKeyboard('Enter passphrase')
        keyboard.onchange = onchange
        dialog = ConfirmDialog(keyboard)
        dialog.cancel.area = ui.grid(12)
        dialog.confirm.area = ui.grid(14)
        keyboard.onchange()

        while True:
            result = await dialog
            if result == CONFIRMED:
                return keyboard.passphrase
            elif result != CONFIRMED and keyboard.passphrase:
                keyboard.change('')
                continue
            else:
                raise wire.FailureError(ActionCancelled, 'Passphrase cancelled')


async def protect_by_passphrase(ctx):
    from apps.common import storage

    if storage.has_passphrase():
        return await request_passphrase(ctx)
    else:
        return ''
