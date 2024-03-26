from . import ChannelState
from .channel_context import ChannelContext


def getPacketHandler(
    channel: ChannelContext, packet: bytes
):  # TODO is the packet bytes or BufferType?
    if channel.get_channel_state is ChannelState.TH1:  # TODO is correct
        # return handler_TH_1
        pass


def handler_TH_1(packet):
    pass
