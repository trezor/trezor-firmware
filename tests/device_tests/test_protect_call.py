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

    @pytest.mark.setup_client(pin="1234", passphrase=True)
    def test_expected_responses(self, client):
        with client:
            # Scenario 4 - Received what expected
            client.set_expected_responses(
                [proto.PinMatrixRequest(), proto.PassphraseRequest(), proto.Address()]
            )
            self._some_protected_call(client)

    def test_no_protection(self, client):
        with client:
            assert client.debug.read_pin()[0] is None
            client.set_expected_responses([proto.Address()])
            self._some_protected_call(client)

    @pytest.mark.setup_client(pin="1234")
    def test_pin(self, client):
        with client:
            assert client.debug.read_pin()[0] == "1234"
            client.setup_debuglink(button=True, pin_correct=True)
            client.set_expected_responses([proto.PinMatrixRequest(), proto.Address()])
            self._some_protected_call(client)

    @pytest.mark.setup_client(pin="1234")
    def test_incorrect_pin(self, client):
        client.setup_debuglink(button=True, pin_correct=False)
        with pytest.raises(PinException):
            self._some_protected_call(client)

    @pytest.mark.setup_client(pin="1234")
    def test_cancelled_pin(self, client):
        client.setup_debuglink(button=True, pin_correct=False)  # PIN cancel
        with pytest.raises(PinException):
            self._some_protected_call(client)

    @pytest.mark.setup_client(pin="1234", passphrase=True)
    def test_exponential_backoff_with_reboot(self, client):
        client.setup_debuglink(button=True, pin_correct=False)

        def test_backoff(attempts, start):
            if attempts <= 1:
                expected = 0
            else:
                expected = (2 ** (attempts - 1)) - 1
            got = round(time.time() - start, 2)

            msg = "Pin delay expected to be at least %s seconds, got %s" % (
                expected,
                got,
            )
            print(msg)
            assert got >= expected

        for attempt in range(1, 4):
            start = time.time()
            with pytest.raises(PinException):
                self._some_protected_call(client)
            test_backoff(attempt, start)
