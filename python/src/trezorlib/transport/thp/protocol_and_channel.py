from __future__ import annotations

import logging

from ... import messages
from ...mapping import ProtobufMapping
from .. import Transport
from ..thp.channel_data import ChannelData

LOG = logging.getLogger(__name__)


class ProtocolAndChannel:

    def __init__(
        self,
        transport: Transport,
        mapping: ProtobufMapping,
        channel_data: ChannelData | None = None,
    ) -> None:
        self.transport = transport
        self.mapping = mapping
        self.channel_keys = channel_data

    def get_features(self) -> messages.Features:
        raise NotImplementedError()

    def get_channel_data(self) -> ChannelData:
        raise NotImplementedError

    def update_features(self) -> None:
        raise NotImplementedError
