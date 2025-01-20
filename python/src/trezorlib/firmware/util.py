# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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
from dataclasses import dataclass

from typing_extensions import Protocol


class FirmwareIntegrityError(Exception):
    pass


class InvalidSignatureError(FirmwareIntegrityError):
    pass


class Unsigned(FirmwareIntegrityError):
    pass


class DigestCalculator(Protocol):
    def update(self, __data: bytes) -> None: ...

    def digest(self) -> bytes: ...


Hasher = t.Callable[[bytes], DigestCalculator]


@dataclass
class FirmwareHashParameters:
    hash_function: Hasher
    chunk_size: int
    padding_byte: bytes | None
