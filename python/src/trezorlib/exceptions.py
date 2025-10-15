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

if t.TYPE_CHECKING:
    from .messages import Failure
    from .protobuf import MessageType


OUTDATED_FIRMWARE_ERROR = """
Your Trezor firmware is out of date. Update it with the following command:
  trezorctl firmware update
Or visit https://suite.trezor.io/
""".strip()


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
    in response to user action.
    """

    def __init__(self, message: str = "Action was cancelled") -> None:
        self.message = message
        super().__init__(self.message)


class DeviceLockedError(TrezorException):
    """Device is locked.

    Raised when an action cannot proceed because the device is locked.

    Typically, an action will trigger an unlock prompt on device. In specific
    cases, that is not the appropriate action (e.g., when establishing a THP channel).
    In such cases, this exception will be raised for the caller to handle,
    by, e.g., explicitly triggering the unlock prompt.
    """

    def __init__(self, message: str = "Device is locked") -> None:
        self.message = message
        super().__init__(self.message)


class OutdatedFirmwareError(TrezorException):
    """Trezor firmware is too old.

    Raised when interfacing with a Trezor whose firmware version is no longer supported
    by current library version.
    """

    def __init__(self, message: str = OUTDATED_FIRMWARE_ERROR) -> None:
        self.message = message
        super().__init__(self.message)


class UnexpectedMessageError(TrezorException):
    """Unexpected message received from Trezor.

    Raised when the library receives a response from Trezor that does not match the
    previous request.
    """

    def __init__(self, expected: type[MessageType], actual: MessageType) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"Expected {expected.__name__} but Trezor sent {actual}")


class InvalidSessionError(TrezorException):
    """Session is invalid or expired."""

    def __init__(
        self, session_id: t.Any, *, from_message: MessageType | None = None
    ) -> None:
        self.session_id = session_id
        self.from_message = from_message
        super().__init__(session_id)


class ProtocolError(TrezorException):
    """Response from Trezor could not be understood.

    This could indicate invalid magic bytes or another kind of error in the
    low-level message encoding.
    """


class PassphraseError(TrezorException):
    """Unable to create a passphrase session because passphrase is disabled on device."""


class NotPairedError(TrezorException):
    """Pairing is required before this client can be used."""

    def __init__(self, message: str | None = None) -> None:
        if message is None:
            message = self.__doc__
        super().__init__(message)


class StateMismatchError(TrezorException):
    """Expected state mismatch.

    Raised when the caller invokes a function that does not match the current
    state of a flow.
    """
