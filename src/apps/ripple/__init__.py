from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import RippleGetAddress
from .get_address import get_address
from .serializer import *


def dispatch_RippleGetAddress(*args, **kwargs):
    from .get_address import get_address
    return get_address(*args, **kwargs)


def boot():
    register(RippleGetAddress, protobuf_workflow, dispatch_RippleGetAddress)
