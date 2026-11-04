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


import pytest

from trezorlib import exceptions, messages
from trezorlib.debuglink import DebugSession as Session

from . import testapp_ext


def test_crashed_app_reports_app_error(session: Session, instance_id: int):
    """A crashed app reaches the host as a detail-less `AppError`."""
    with pytest.raises(exceptions.TrezorFailure) as e:
        testapp_ext.crash(session, instance_id)
    assert e.value.code == messages.FailureType.AppError
    # the app's own error text stays in the log
    assert e.value.message == "Application error"
