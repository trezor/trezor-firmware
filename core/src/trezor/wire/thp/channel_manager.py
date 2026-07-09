from typing import TYPE_CHECKING

from storage import cache_thp
from storage.cache_common import CHANNEL_IFACE, CHANNEL_STATE

from . import ChannelState

if TYPE_CHECKING:
    from trezorio import WireInterface

    from storage.cache_thp import ChannelCache


def create_new_channel(iface: WireInterface) -> ChannelCache:
    """
    Creates a new channel for the interface `iface`.
    """
    channel_cache: ChannelCache = cache_thp.get_new_channel()
    channel_cache.set_int(CHANNEL_IFACE, iface.iface_num())
    channel_cache.set_int(CHANNEL_STATE, ChannelState.TH1)
    return channel_cache
