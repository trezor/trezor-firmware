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

from enum import IntEnum

from .. import exceptions


class ThpErrorCode(IntEnum):
    TRANSPORT_BUSY = 1
    UNALLOCATED_CHANNEL = 2
    DECRYPTION_FAILED = 3
    DEVICE_LOCKED = 5

    @classmethod
    def to_exception(cls, code: int) -> ThpError:
        try:
            valid_code = cls(code)
            return ThpError(valid_code)
        except ValueError:
            return ThpError(code)


class ThpError(exceptions.TrezorException):
    def __init__(self, code: ThpErrorCode | int) -> None:
        self.code = code
        if isinstance(code, ThpErrorCode):
            self.name = code.name
        else:
            self.name = "unknown"
        super().__init__(code, self.name)
