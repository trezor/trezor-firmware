from trezor import log
from trezor import loop
from trezor.utils import unimport
from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import \
    DebugLinkDecision, DebugLinkGetState, DebugLinkStop, \
    DebugLinkMemoryRead, DebugLinkMemoryWrite, DebugLinkFlashErase


@unimport
async def dispatch_DebugLinkDecision(ctx, msg):
    from trezor.ui.confirm import CONFIRMED, CANCELLED
    from apps.common.confirm import signal
    signal.send(CONFIRMED if msg.yes_no else CANCELLED)


@unimport
async def dispatch_DebugLinkGetState(ctx, msg):
    from trezor.messages.DebugLinkState import DebugLinkState
    from apps.common import storage
    from apps.management import reset_device

    m = DebugLinkState()
    m.mnemonic = storage.get_mnemonic()
    m.passphrase_protection = storage.has_passphrase()
    m.reset_entropy = reset_device.internal_entropy
    m.reset_word = reset_device.current_word

    return m


@unimport
async def dispatch_DebugLinkStop(ctx, msg):
    pass


@unimport
async def dispatch_DebugLinkMemoryRead(ctx, msg):
    from trezor.messages.DebugLinkMemory import DebugLinkMemory
    from uctypes import bytes_at
    m = DebugLinkMemory()
    m.memory = bytes_at(msg.address, msg.length)
    return m


@unimport
async def dispatch_DebugLinkMemoryWrite(ctx, msg):
    from uctypes import bytearray_at
    l = len(msg.memory)
    data = bytearray_at(msg.address, l)
    data[0:l] = msg.memory


@unimport
async def dispatch_DebugLinkFlashErase(ctx, msg):
    # TODO: erase(msg.sector)
    pass


async def memory_stats(interval):
    import micropython
    import gc

    sleep = loop.sleep(interval * 1000 * 1000)
    while True:
        micropython.mem_info()
        gc.collect()
        await sleep


def boot():
    register(DebugLinkDecision, protobuf_workflow, dispatch_DebugLinkDecision)
    register(DebugLinkGetState, protobuf_workflow, dispatch_DebugLinkGetState)
    register(DebugLinkStop, protobuf_workflow, dispatch_DebugLinkStop)
    register(DebugLinkMemoryRead, protobuf_workflow, dispatch_DebugLinkMemoryRead)
    register(DebugLinkMemoryWrite, protobuf_workflow, dispatch_DebugLinkMemoryWrite)
    register(DebugLinkFlashErase, protobuf_workflow, dispatch_DebugLinkFlashErase)

    # loop.schedule(memory_stats(10))
