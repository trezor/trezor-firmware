from trezor.wire import register_type, protobuf_handler
from trezor.messages.wire_types import \
    DebugLinkDecision, DebugLinkGetState, DebugLinkStop, \
    DebugLinkMemoryRead, DebugLinkMemoryWrite, DebugLinkFlashErase


async def dispatch_DebugLinkDecision(msg, session_id):
    from trezor.ui.confirm import CONFIRMED, CANCELLED
    from ..common.confirm import signal
    signal.send(CONFIRMED if msg.yes_no else CANCELLED)


async def dispatch_DebugLinkGetState(msg, session_id):
    from trezor.messages.DebugLinkState import DebugLinkState
    from ..common import storage, request_pin

    if request_pin.matrix:
        matrix = ''.join([str(d) for d in request_pin.matrix.digits])
    else:
        matrix = None

    m = DebugLinkState()
    m.pin = storage.get_pin()
    m.mnemonic = storage.get_mnemonic()
    m.passphrase_protection = storage.is_protected_by_passphrase()
    m.matrix = matrix

    # TODO: handle other fields:
    # f.reset_entropy = reset_get_internal_entropy()
    # f.reset_word = reset_get_word()
    # f.recovery_fake_word = recovery_get_fake_word()
    # f.recovery_word_pos = recovery_get_word_pos()
    # f.node = storage.get_node()

    return m


async def dispatch_DebugLinkStop(msg, session_id):
    pass


async def dispatch_DebugLinkMemoryRead(msg, session_id):
    from trezor.messages.DebugLinkMemory import DebugLinkMemory
    from trezor.debug import memaccess

    length = min(msg.length, 1024)
    m = DebugLinkMemory()
    m.memory = memaccess(msg.address, length)

    return m


async def dispatch_DebugLinkMemoryWrite(msg, session_id):
    # TODO: memcpy((void *)msg.address, msg.memory, len(msg.memory))
    pass


async def dispatch_DebugLinkFlashErase(msg, session_id):
    # TODO: erase(msg.sector)
    pass


def boot():
    register_type(
        DebugLinkDecision, protobuf_handler, dispatch_DebugLinkDecision)
    register_type(
        DebugLinkGetState, protobuf_handler, dispatch_DebugLinkGetState)
    register_type(
        DebugLinkStop, protobuf_handler, dispatch_DebugLinkStop)
    register_type(
        DebugLinkMemoryRead, protobuf_handler, dispatch_DebugLinkMemoryRead)
    register_type(
        DebugLinkMemoryWrite, protobuf_handler, dispatch_DebugLinkMemoryWrite)
    register_type(
        DebugLinkFlashErase, protobuf_handler, dispatch_DebugLinkFlashErase)
