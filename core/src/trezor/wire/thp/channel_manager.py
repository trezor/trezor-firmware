from typing import TYPE_CHECKING

from storage import cache_thp

from . import ChannelState, interface_manager
from .channel import Channel

if TYPE_CHECKING:
    from trezorio import WireInterface


def create_new_channel(iface: WireInterface) -> Channel:
    """
    Creates a new channel for the interface `iface`.
    """
    channel_cache = cache_thp.get_new_channel(interface_manager.encode_iface(iface))
    channel = Channel(channel_cache)
    channel.set_channel_state(ChannelState.TH1)
    return channel


def load_cached_channels() -> dict[int, Channel]:
    """
    Returns all allocated channels from cache.
    """
    channels: dict[int, Channel] = {}
    cached_channels = cache_thp.get_all_allocated_channels()
    for channel in cached_channels:
        channels[int.from_bytes(channel.channel_id, "big")] = Channel(channel)
    return channels
