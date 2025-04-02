from __future__ import annotations

import logging
import typing as t

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

    def read(self, timeout: float | None = None) -> t.Any:
        raise NotImplementedError

    def write(self, msg: t.Any) -> None:
        raise NotImplementedError
