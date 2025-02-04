from __future__ import annotations

import logging

from ... import messages
from ...mapping import ProtobufMapping
from .. import Transport

LOG = logging.getLogger(__name__)


class Channel:

    def __init__(
        self,
        transport: Transport,
        mapping: ProtobufMapping,
    ) -> None:
        self.transport = transport
        self.mapping = mapping

    def get_features(self) -> messages.Features:
        raise NotImplementedError()

    def update_features(self) -> None:
        raise NotImplementedError
