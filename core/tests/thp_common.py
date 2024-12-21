# flake8: noqa: F403,F405
from trezor import utils
from trezor.wire.thp import ChannelState

if utils.USE_THP:
    import unittest
    from typing import TYPE_CHECKING

    from mock_wire_interface import MockHID
    from storage import cache_thp
    from trezor.wire import context
    from trezor.wire.thp import interface_manager
    from trezor.wire.thp.channel import Channel
    from trezor.wire.thp.session_context import SessionContext

    _MOCK_INTERFACE_HID = b"\x00"

    if TYPE_CHECKING:
        from trezor.wire import WireInterface

    def dummy_decode_iface(cached_iface: bytes):
        return MockHID(0xDEADBEEF)

    def get_new_channel(channel_iface: WireInterface | None = None) -> Channel:
        interface_manager.decode_iface = dummy_decode_iface
        channel_cache = cache_thp.get_new_channel(_MOCK_INTERFACE_HID)
        channel = Channel(channel_cache)
        channel.set_channel_state(ChannelState.TH1)
        if channel_iface is not None:
            channel.iface = channel_iface
        return channel

    def prepare_context() -> None:
        channel = get_new_channel()
        session_cache = cache_thp.create_or_replace_session(
            channel.channel_cache, session_id=b"\x01"
        )
        session_ctx = SessionContext(channel, session_cache)
        context.CURRENT_CONTEXT = session_ctx


if __debug__:
    # Disable log.debug
    def suppres_debug_log() -> None:
        from trezor import log

        log.debug = lambda name, msg, *args: None
