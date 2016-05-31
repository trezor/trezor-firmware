from . import wire
from . import layout


message_handlers = {}


def register(mtype, handler):
    message_handlers[mtype] = handler


def unregister(mtype):
    del message_handlers[mtype]


def dispatch():
    mtype, mbuf = yield from wire.read_wire_msg()
    handler = message_handlers[mtype]
    layout.change(handler(mtype, mbuf))
