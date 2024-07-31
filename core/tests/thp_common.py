from trezor import utils

if utils.USE_THP:
    from mock_wire_interface import MockHID
    from storage import cache_thp
    from trezor.wire import context
    from trezor.wire.thp import interface_manager
    from trezor.wire.thp.channel import Channel
    from trezor.wire.thp.interface_manager import _MOCK_INTERFACE_HID
    from trezor.wire.thp.session_context import SessionContext

    def dummy_decode_iface(cached_iface: bytes):
        return MockHID(0xDEADBEEF)

    def prepare_context() -> None:
        interface_manager.decode_iface = dummy_decode_iface
        channel_cache = cache_thp.get_new_channel(_MOCK_INTERFACE_HID)
        channel = Channel(channel_cache)
        session_cache = cache_thp.get_new_session(channel_cache)
        session_ctx = SessionContext(channel, session_cache)
        context.CURRENT_CONTEXT = session_ctx


if __debug__:
    # Disable log.debug for the test
    def suppres_debug_log() -> None:
        from trezor import log

        log.debug = lambda name, msg, *args: None
