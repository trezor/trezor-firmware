from typing import TYPE_CHECKING  # pyright: ignore[reportShadowedImports]

from trezor import utils
from trezor.wire import codec_v1, thp_v1
from trezor.wire.protocol_common import MessageWithId

if TYPE_CHECKING:
    from trezorio import WireInterface  # pyright: ignore[reportMissingImports]


async def read_message(iface: WireInterface, buffer: utils.BufferType) -> MessageWithId:
    if utils.USE_THP:
        return await thp_v1.read_message(iface, buffer)
    return await codec_v1.read_message(iface, buffer)


async def write_message(iface: WireInterface, message: MessageWithId) -> None:
    if utils.USE_THP:
        await thp_v1.write_message_with_sync_control(iface, message)
        return
    await codec_v1.write_message(iface, message.type, message.data)
    return
