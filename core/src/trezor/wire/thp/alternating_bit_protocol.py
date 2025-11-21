from storage.cache_thp import ChannelCache


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
    return is_expected


def _has_ack_correct_sync_bit(cache: ChannelCache, sync_bit: int) -> bool:
    is_correct: bool = get_send_seq_bit(cache) == sync_bit
    return is_correct


def has_msg_correct_seq_bit(cache: ChannelCache, sync_bit: int) -> bool:
    return sync_bit == get_expected_receive_seq_bit(cache)


def is_sending_allowed(cache: ChannelCache) -> bool:
    """
    Checks whether sending a message in the provided channel is allowed.

    Note: Sending a message in a channel before receipt of ACK message for the previously
    sent message (in the channel) is prohibited, as it can lead to desynchronization.
    """
    return bool(cache.sync >> 7)


def get_send_ack_bit(cache: ChannelCache) -> int:
    """
    Returns the sequential number (bit) of the last message successfully received on this channel.
    """
    return 1 - get_expected_receive_seq_bit(cache)


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
    assert seq_bit in (0, 1)

    # set second bit to "seq_bit" value
    cache.sync &= 0xBF
    if seq_bit:
        cache.sync |= 0x40


def _set_send_seq_bit(cache: ChannelCache, seq_bit: int) -> None:
    assert seq_bit in (0, 1)
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


def is_ack_piggybacking_allowed(cache: ChannelCache) -> bool:
    return bool(cache.sync & 0x10)


def allow_ack_piggybacking(cache: ChannelCache) -> None:
    cache.sync |= 0x10
