# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import contextlib
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

    def interactive_context(self) -> contextlib.AbstractContextManager:
        return contextlib.nullcontext()
