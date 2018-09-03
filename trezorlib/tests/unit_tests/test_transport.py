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

import mock

from trezorlib.transport import all_transports


def test_all_transports_without_hid():
    # import all transports, assume this doesn't fail
    transports_ref = all_transports()
    # also shouldn't fail when bridge transport is missing
    with mock.patch.dict("sys.modules", {"trezorlib.transport.bridge": None}):
        transports = all_transports()
        # there should now be less transports
        assert len(transports_ref) > len(transports)
