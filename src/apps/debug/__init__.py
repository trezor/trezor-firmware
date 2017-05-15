from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import \
    DebugLinkDecision, DebugLinkGetState, DebugLinkStop, \
    DebugLinkMemoryRead, DebugLinkMemoryWrite, DebugLinkFlashErase


async def dispatch_DebugLinkDecision(session_id, msg):
    from trezor.ui.confirm import CONFIRMED, CANCELLED
    from apps.common.confirm import signal
    signal.send(CONFIRMED if msg.yes_no else CANCELLED)


async def dispatch_DebugLinkGetState(session_id, msg):
    from trezor.messages.DebugLinkState import DebugLinkState
    from apps.common import storage, request_pin
    from apps.management import reset_device

    if request_pin.matrix:
        matrix = ''.join([str(d) for d in request_pin.matrix.digits])
    else:
        matrix = None

    m = DebugLinkState()
    m.pin = storage.config_get(storage.PIN).decode()
    m.mnemonic = storage.config_get(storage.MNEMONIC).decode()
    m.passphrase_protection = storage.is_protected_by_passphrase()
    m.matrix = matrix
    m.reset_entropy = reset_device.internal_entropy
    m.reset_word = reset_device.current_word

    # TODO: handle other fields:
    # f.recovery_fake_word = recovery_get_fake_word()
    # f.recovery_word_pos = recovery_get_word_pos()
    # f.node = storage.get_node()

    return m


async def dispatch_DebugLinkStop(session_id, msg):
    pass


async def dispatch_DebugLinkMemoryRead(session_id, msg):
    # TODO: return memaccess(msg.address, msg.length)
    pass


async def dispatch_DebugLinkMemoryWrite(session_id, msg):
    # TODO: memcpy((void *)msg.address, msg.memory, len(msg.memory))
    pass


async def dispatch_DebugLinkFlashErase(session_id, msg):
    # TODO: erase(msg.sector)
    pass


def boot():
    register(DebugLinkDecision, protobuf_workflow, dispatch_DebugLinkDecision)
    register(DebugLinkGetState, protobuf_workflow, dispatch_DebugLinkGetState)
    register(DebugLinkStop, protobuf_workflow, dispatch_DebugLinkStop)
    register(DebugLinkMemoryRead, protobuf_workflow, dispatch_DebugLinkMemoryRead)
    register(DebugLinkMemoryWrite, protobuf_workflow, dispatch_DebugLinkMemoryWrite)
    register(DebugLinkFlashErase, protobuf_workflow, dispatch_DebugLinkFlashErase)
