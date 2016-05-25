from . import msg
from . import layout


message_handlers = {}


def register(message_type, handler):
    message_handlers[message_type] = handler


def unregister(message_type):
    del message_handlers[message_type]


def dispatch():
    mtypes = message_handlers.keys()
    message = yield from msg.read_msg(*mtypes)
    handler = message_handlers[message.message_type]
    layout.change(handler(message))
