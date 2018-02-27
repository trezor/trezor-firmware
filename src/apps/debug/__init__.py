import micropython
import gc
from uctypes import bytes_at, bytearray_at

from trezor import loop
from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import \
    DebugLinkDecision, DebugLinkGetState, DebugLinkStop, \
    DebugLinkMemoryRead, DebugLinkMemoryWrite, DebugLinkFlashErase
from trezor.messages.DebugLinkMemory import DebugLinkMemory
from trezor.messages.DebugLinkState import DebugLinkState
from trezor.ui.confirm import CONFIRMED, CANCELLED

from apps.common.confirm import signal
from apps.common import storage
from apps.management import reset_device


async def dispatch_DebugLinkDecision(ctx, msg):
    signal.send(CONFIRMED if msg.yes_no else CANCELLED)


async def dispatch_DebugLinkGetState(ctx, msg):
    m = DebugLinkState()
    m.mnemonic = storage.get_mnemonic()
    m.passphrase_protection = storage.has_passphrase()
    m.reset_entropy = reset_device.internal_entropy
    m.reset_word = reset_device.current_word
    return m


async def dispatch_DebugLinkStop(ctx, msg):
    pass


async def dispatch_DebugLinkMemoryRead(ctx, msg):
    m = DebugLinkMemory()
    m.memory = bytes_at(msg.address, msg.length)
    return m


async def dispatch_DebugLinkMemoryWrite(ctx, msg):
    l = len(msg.memory)
    data = bytearray_at(msg.address, l)
    data[0:l] = msg.memory


async def dispatch_DebugLinkFlashErase(ctx, msg):
    # TODO: erase(msg.sector)
    pass


async def memory_stats(interval):
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
