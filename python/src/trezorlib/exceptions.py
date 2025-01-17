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
    """General Trezor exception."""


class TrezorFailure(TrezorException):
    """Failure received over the wire from Trezor.

    Corresponds to a `Failure` protobuf message.
    """

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
    """PIN operation has failed.

    This exception is only raised on Trezor Model One. It indicates to the caller that
    the Trezor rejected the PIN entered via host-side matrix keyboard.
    """


class Cancelled(TrezorException):
    """Action was cancelled.

    Cancellation can be either received from Trezor or caused by the library, typically
    in response to user action."""


class OutdatedFirmwareError(TrezorException):
    """Trezor firmware is too old.

    Raised when interfacing with a Trezor whose firmware version is no longer supported
    by current library version."""


class UnexpectedMessageError(TrezorException):
    """Unexpected message received from Trezor.

    Raised when the library receives a response from Trezor that does not match the
    previous request."""

    def __init__(self, expected: type[MessageType], actual: MessageType) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"Expected {expected.__name__} but Trezor sent {actual}")
