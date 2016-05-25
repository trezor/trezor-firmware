from trezor.dispatcher import register
from trezor.messages.GetPublicKey import GetPublicKey


def dispatch(message):
    if message.message_type is GetPublicKey:
        from .layout_get_public_key import layout_get_public_key
        return layout_get_public_key(message)


def boot():
    register(GetPublicKey, dispatch)
