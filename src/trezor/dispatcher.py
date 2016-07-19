from . import wire
from . import layout


message_handlers = {}


def register(mtype, handler):
    if mtype in message_handlers:
        raise Exception('Message wire type %s is already registered', mtype)
    message_handlers[mtype] = handler


def unregister(mtype):
    del message_handlers[mtype]


def dispatch():
    _, mtype, mbuf = yield from wire.read_wire_msg()
    handler = message_handlers[mtype]
    layout.change(handler(mtype, mbuf))
