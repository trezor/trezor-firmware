from trezor.wire import register_type, protobuf_handler
from trezor.messages.wire_types import \
    DebugLinkDecision, DebugLinkGetState, DebugLinkStop, \
    DebugLinkMemoryRead, DebugLinkMemoryWrite, DebugLinkFlashErase
from trezor.debug import memaccess

async def dispatch_DebugLinkDecision(msg, session_id):
    # TODO: apply button decision from msg.yes_no
    pass

async def dispatch_DebugLinkGetState(msg, session_id):
    from trezor.messages.DebugLinkState import DebugLinkState
    f = DebugLinkState()
    # TODO:
    # f.pin = storage.get_pin()
    # f.matrix = pinmatrix_get()
    # f.reset_entropy = reset_get_internal_entropy()
    # f.reset_word = reset_get_word()
    # f.recovery_fake_word = recovery_get_fake_word()
    # f.recovery_word_pos = recovery_get_word_pos()
    # f.mnemonic = storage.get_mnemonic()
    # f.node = storage.get_node()
    # f.passphrase_protection = storage.get_passphrase_protection()
    await write_message(session_id, f)

async def dispatch_DebugLinkStop(msg, session_id):
    pass

async def dispatch_DebugLinkMemoryRead(msg, session_id):
    from trezor.messages.DebugLinkMemory import DebugLinkMemory
    length = max(msg.length, 1024)
    f = DebugLinkMemory()
    f.memory = memaccess(msg.address, length)
    await write_message(session_id, f)

async def dispatch_DebugLinkMemoryWrite(msg, session_id):
    # TODO memcpy((void *)msg.address, msg.memory, len(msg.memory))
    pass

async def dispatch_DebugLinkFlashErase(msg, session_id):
    # TODO: erase(msg.sector)
    pass

def boot():
    register_type(DebugLinkDecision, protobuf_handler, dispatch_DebugLinkDecision)
    register_type(DebugLinkGetState, protobuf_handler, dispatch_DebugLinkGetState)
    register_type(DebugLinkStop, protobuf_handler, dispatch_DebugLinkStop)
    register_type(DebugLinkMemoryRead, protobuf_handler, dispatch_DebugLinkMemoryRead)
    register_type(DebugLinkMemoryWrite, protobuf_handler, dispatch_DebugLinkMemoryWrite)
    register_type(DebugLinkFlashErase, protobuf_handler, dispatch_DebugLinkFlashErase)
