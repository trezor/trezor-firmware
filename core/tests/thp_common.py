# flake8: noqa: F403,F405
from common import *  # isort:skip

if utils.USE_THP:
    from typing import TYPE_CHECKING

    from mock_wire_interface import MockHID
    from storage import cache_thp
    from trezor.wire import context
    from trezor.wire.thp.channel import Channel
    from trezor.wire.thp.channel_manager import create_new_channel
    from trezor.wire.thp.interface_context import ThpContext
    from trezor.wire.thp.memory_manager import ThpBuffer
    from trezor.wire.thp.session_context import SessionContext

    if TYPE_CHECKING:
        from trezor.wire import WireInterface

    def prepare_context() -> None:
        mock_iface = MockHID()
        channel_cache = create_new_channel(mock_iface)
        session_cache = cache_thp.create_or_replace_session(
            channel_cache, session_id=b"\x01"
        )
        channel = Channel(
            channel_cache, ThpContext(mock_iface), (ThpBuffer(), ThpBuffer())
        )
        context.CURRENT_CONTEXT = SessionContext(channel, session_cache)

    def get_new_channel(iface: WireInterface) -> Channel:
        channel_cache = create_new_channel(iface)
        return Channel(channel_cache, ThpContext(iface), (ThpBuffer(), ThpBuffer()))


if __debug__:
    # Disable log.debug
    def suppress_debug_log() -> None:
        from trezor import log

        log._min_level = 1
