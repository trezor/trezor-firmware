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

import typing as t
from enum import Enum

import construct


class EnumAdapter(construct.Adapter):
    def __init__(self, subcon: construct.Adapter, enum: type[Enum]) -> None:
        self.enum = enum
        super().__init__(subcon)

    def _encode(self, obj: t.Any, context: t.Any, path: t.Any) -> t.Any:
        if isinstance(obj, self.enum):
            return obj.value
        return obj

    def _decode(self, obj: t.Any, context: t.Any, path: t.Any) -> t.Any:
        try:
            return self.enum(obj)
        except ValueError:
            return obj


class TupleAdapter(construct.Adapter):
    def __init__(self, *subcons: construct.Adapter) -> None:
        super().__init__(construct.Sequence(*subcons))

    def _encode(self, obj: t.Any, context: t.Any, path: t.Any) -> t.Any:
        return obj

    def _decode(self, obj: t.Any, context: t.Any, path: t.Any) -> t.Any:
        return tuple(obj)
