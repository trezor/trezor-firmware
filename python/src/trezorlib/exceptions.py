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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .messages import Failure
    from .protobuf import MessageType


class TrezorException(Exception):
    pass


class TrezorFailure(TrezorException):
    def __init__(self, failure: Failure) -> None:
        self.failure = failure
        self.code = failure.code
        self.message = failure.message
        super().__init__(self.code, self.message, self.failure)

    def __str__(self) -> str:
        from .messages import FailureType

        types = {
            getattr(FailureType, name): name
            for name in dir(FailureType)
            if not name.startswith("_")
        }
        if self.message is not None:
            return f"{types[self.code]}: {self.message}"
        else:
            return types[self.failure.code]


class PinException(TrezorException):
    pass


class Cancelled(TrezorException):
    pass


class OutdatedFirmwareError(TrezorException):
    pass


class UnexpectedMessageError(TrezorException):
    def __init__(self, expected: type[MessageType], actual: MessageType) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"Expected {expected.__name__} but Trezor sent {actual}")
