from storage.cache_thp import ChannelCache
from trezor import log, utils
from trezor.wire.thp import ThpError


def is_ack_valid(cache: ChannelCache, ack_bit: int) -> bool:
    """
    Checks if:
    - an ACK message is expected
    - the received ACK message acknowledges correct sequence number (bit)
    """
    if not _is_ack_expected(cache):
        return False

    if not _has_ack_correct_sync_bit(cache, ack_bit):
        return False

    return True


def _is_ack_expected(cache: ChannelCache) -> bool:
    is_expected: bool = not is_sending_allowed(cache)
    if __debug__ and utils.ALLOW_DEBUG_MESSAGES and not is_expected:
        log.debug(__name__, "Received unexpected ACK message")
    return is_expected


def _has_ack_correct_sync_bit(cache: ChannelCache, sync_bit: int) -> bool:
    is_correct: bool = get_send_seq_bit(cache) == sync_bit
    if __debug__ and utils.ALLOW_DEBUG_MESSAGES and not is_correct:
        log.debug(__name__, "Received ACK message with wrong ack bit")
    return is_correct


def is_sending_allowed(cache: ChannelCache) -> bool:
    """
    Checks whether sending a message in the provided channel is allowed.

    Note: Sending a message in a channel before receipt of ACK message for the previously
    sent message (in the channel) is prohibited, as it can lead to desynchronization.
    """
    return bool(cache.sync >> 7)


def get_send_seq_bit(cache: ChannelCache) -> int:
    """
    Returns the sequential number (bit) of the next message to be sent
    in the provided channel.
    """
    return (cache.sync & 0x20) >> 5


def get_expected_receive_seq_bit(cache: ChannelCache) -> int:
    """
    Returns the (expected) sequential number (bit) of the next message
    to be received in the provided channel.
    """
    return (cache.sync & 0x40) >> 6


def set_sending_allowed(cache: ChannelCache, sending_allowed: bool) -> None:
    """
    Set the flag whether sending a message in this channel is allowed or not.
    """
    cache.sync &= 0x7F
    if sending_allowed:
        cache.sync |= 0x80


def set_expected_receive_seq_bit(cache: ChannelCache, seq_bit: int) -> None:
    """
    Set the expected sequential number (bit) of the next message to be received
    in the provided channel
    """
    if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
        log.debug(__name__, "Set sync receive expected seq bit to %d", seq_bit)
    if seq_bit not in (0, 1):
        raise ThpError("Unexpected receive sync bit")

    # set second bit to "seq_bit" value
    cache.sync &= 0xBF
    if seq_bit:
        cache.sync |= 0x40


def _set_send_seq_bit(cache: ChannelCache, seq_bit: int) -> None:
    if seq_bit not in (0, 1):
        raise ThpError("Unexpected send seq bit")
    if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
        log.debug(__name__, "setting sync send seq bit to %d", seq_bit)
    # set third bit to "seq_bit" value
    cache.sync &= 0xDF
    if seq_bit:
        cache.sync |= 0x20


def set_send_seq_bit_to_opposite(cache: ChannelCache) -> None:
    """
    Set the sequential bit of the "next message to be send" to the opposite value,
    i.e. 1 -> 0 and 0 -> 1
    """
    _set_send_seq_bit(cache=cache, seq_bit=1 - get_send_seq_bit(cache))
