from typing import TYPE_CHECKING

from storage import cache_thp
from storage.cache_common import CHANNEL_IFACE

from . import ChannelState, interface_manager
from .channel import Channel

if TYPE_CHECKING:
    from trezorio import WireInterface

    from storage.cache_thp import ChannelCache

if __debug__:
    from trezor import log

CHANNELS_LOADED: bool = False


def create_new_channel(iface: WireInterface) -> Channel:
    """
    Creates a new channel for the interface `iface`.
    """
    channel_cache: ChannelCache = cache_thp.get_new_channel()
    channel_cache.set(CHANNEL_IFACE, interface_manager.encode_iface(iface))
    channel = Channel(channel_cache)
    channel.set_channel_state(ChannelState.TH1)
    return channel


def load_cached_channels(
    channels_dict: dict[int, Channel], iface: WireInterface
) -> None:
    """
    Returns all allocated channels from cache.
    """
    global CHANNELS_LOADED

    if CHANNELS_LOADED:
        if __debug__:
            log.debug(
                __name__, "Channels already loaded, process skipped.", iface=iface
            )
        return

    cached_channels = cache_thp.get_all_allocated_channels()
    for channel in cached_channels:
        channel_id = int.from_bytes(channel.channel_id, "big")
        channels_dict[channel_id] = Channel(channel)
    if __debug__:
        log.debug(__name__, "Channels loaded from cache.", iface=iface)
    CHANNELS_LOADED = True
