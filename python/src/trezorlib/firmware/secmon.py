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

from copy import copy

import construct as c
from construct_classes import Struct, subcon

from ..tools import EnumAdapter, TupleAdapter
from . import util
from .models import Model

__all__ = [
    "SecmonHeader",
    "SecmonImage",
]


class SecmonHeader(Struct):
    header_len: int
    code_length: int
    version: tuple[int, int, int, int]
    hw_model: Model | bytes
    hw_revision: int
    monotonic: int
    hash: bytes

    sigmask: int
    signature: bytes

    # fmt: off
    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "magic" / c.Const(b"TSEC"),
        "header_len" / c.Int32ul,
        "code_length" / c.Int32ul,
        "version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "hw_model" / EnumAdapter(c.Bytes(4), Model),
        "hw_revision" / c.Int8ul,
        "monotonic" / c.Int8ul,
        "_reserved" / c.Padding(2),
        "hash" / c.Bytes(32),

        "_reserved" / c.Padding(391),
        "sigmask" / c.Byte,
        "signature" / c.Bytes(64),

        "_end_offset" / c.Tell,

        "_rebuild_header_len" / c.Pointer(
            c.this._start_offset + 4,
            c.Rebuild(c.Int32ul, c.this._end_offset - c.this._start_offset)
        ),
    )
    # fmt: on


class SecmonImage(Struct):
    """Raw secmon image.

    Consists of secmon header and code block.
    """

    header: SecmonHeader = subcon(SecmonHeader)
    _header_end: int
    _code_offset: int
    code: bytes

    SUBCON = c.Struct(
        "header" / SecmonHeader.SUBCON,
        "code" / c.Bytes(c.this.header.code_length),
        c.Terminated,
    )

    def get_hash_params(self) -> util.FirmwareHashParameters:
        return Model.from_hw_model(self.header.hw_model).hash_params()

    def code_hash(self) -> bytes:
        """Calculate hash of `code`."""

        hash_params = self.get_hash_params()

        hash = hash_params.hash_function(self.code).digest()

        return hash

    def validate_code_hash(self) -> None:
        if self.code_hash() != self.header.hash:
            raise util.FirmwareIntegrityError("Invalid firmware data.")

    def digest(self) -> bytes:
        hash_params = self.get_hash_params()

        header = copy(self.header)
        header.hash = self.code_hash()
        header.signature = b"\x00" * 64
        header.sigmask = 0
        return hash_params.hash_function(header.build()).digest()

    def model(self) -> Model | None:
        if isinstance(self.header.hw_model, Model):
            return self.header.hw_model
        return None
