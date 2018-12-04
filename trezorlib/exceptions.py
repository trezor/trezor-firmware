# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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


class TrezorException(Exception):
    pass


class TrezorFailure(TrezorException):
    def __init__(self, failure):
        self.failure = failure
        # TODO: this is backwards compatibility with tests. it should be changed
        super().__init__(self.failure.code, self.failure.message)

    def __str__(self):
        from .messages import FailureType

        types = {
            getattr(FailureType, name): name
            for name in dir(FailureType)
            if not name.startswith("_")
        }
        if self.failure.message is not None:
            return "{}: {}".format(types[self.failure.code], self.failure.message)
        else:
            return types[self.failure.code]


class PinException(TrezorException):
    pass


class Cancelled(TrezorException):
    pass


class OutdatedFirmwareError(TrezorException):
    pass
