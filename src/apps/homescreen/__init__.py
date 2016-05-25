from trezor.dispatcher import register
from trezor.messages.Initialize import Initialize


def dispatch(message):
    from .layout_homescreen import layout_homescreen
    return layout_homescreen(message)


def boot():
    register(Initialize, dispatch)
