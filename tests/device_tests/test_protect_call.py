# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import time

import pytest

from trezorlib import btc, messages as proto
from trezorlib.exceptions import PinException

# FIXME TODO Add passphrase tests


@pytest.mark.skip_t2
class TestProtectCall:
    def _some_protected_call(self, client):
        # This method perform any call which have protection in the device
        res = btc.get_address(client, "Testnet", [0])
        assert res == "mndoQDWatQhfeQbprzZxD43mZ75Z94D6vz"

    def test_no_protection(self, client):
        with client:
            client.set_expected_responses([proto.Address()])
            self._some_protected_call(client)

    @pytest.mark.setup_client(pin="1234")
    def test_pin(self, client):
        with client:
            client.use_pin_sequence(["1234"])
            client.set_expected_responses([proto.PinMatrixRequest(), proto.Address()])
            self._some_protected_call(client)

    @pytest.mark.setup_client(pin="1234")
    def test_incorrect_pin(self, client):
        with pytest.raises(PinException):
            client.use_pin_sequence(["5678"])
            self._some_protected_call(client)

    @pytest.mark.setup_client(pin="1234", passphrase=True)
    def test_exponential_backoff_with_reboot(self, client):
        def test_backoff(attempts, start):
            if attempts <= 1:
                expected = 0
            else:
                expected = (2 ** (attempts - 1)) - 1
            got = round(time.time() - start, 2)
            assert got >= expected

        for attempt in range(1, 4):
            start = time.time()
            with client, pytest.raises(PinException):
                client.use_pin_sequence(["5678"])
                self._some_protected_call(client)
            test_backoff(attempt, start)
