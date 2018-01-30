from trezor import wire, ui, loop

# used to confirm/cancel the dialogs from outside of this module (i.e.
# through debug link)
if __debug__:
    signal = loop.signal()


@ui.layout
async def request_words(ctx, content, code=None, *args, **kwargs):
    from trezor.ui.word_select import WordSelector
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.wire_types import ButtonAck

    ui.display.clear()
    dialog = WordSelector(content, *args, **kwargs)
    dialog.render()

    if code is None:
        code = Other
    await ctx.call(ButtonRequest(code=code), ButtonAck)

    if __debug__:
        waiter = loop.wait(signal, dialog)
    else:
        waiter = dialog
    return await waiter
