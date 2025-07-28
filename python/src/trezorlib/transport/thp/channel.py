from __future__ import annotations

import typing as t

from ... import messages
from ...mapping import ProtobufMapping
from .. import Transport


class Channel:
    _DEFAULT_READ_TIMEOUT: t.ClassVar[float | None] = None

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
