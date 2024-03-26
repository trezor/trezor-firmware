from storage.cache_thp import SessionThpCache
from trezor import log

from . import thp_session as THP


def handle_received_ACK(cache: SessionThpCache, sync_bit: int) -> None:

    if _ack_is_not_expected(cache):
        _conditionally_log_debug(__name__, "Received unexpected ACK message")
        return
    if _ack_has_incorrect_sync_bit(cache, sync_bit):
        _conditionally_log_debug(__name__, "Received ACK message with wrong sync bit")
        return

    # ACK is expected and it has correct sync bit
    _conditionally_log_debug(__name__, "Received ACK message with correct sync bit")
    THP.sync_set_can_send_message(cache, True)


def _ack_is_not_expected(cache: SessionThpCache) -> bool:
    return THP.sync_can_send_message(cache)


def _ack_has_incorrect_sync_bit(cache: SessionThpCache, sync_bit: int) -> bool:
    return THP.sync_get_send_bit(cache) != sync_bit


def _conditionally_log_debug(name, message):
    if __debug__:
        log.debug(name, message)
