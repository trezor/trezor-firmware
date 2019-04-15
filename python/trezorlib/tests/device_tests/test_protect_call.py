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

import time

import pytest

from trezorlib import messages as proto
from trezorlib.exceptions import PinException

from .common import TrezorTest

# FIXME TODO Add passphrase tests


@pytest.mark.skip_t2
class TestProtectCall(TrezorTest):
    def _some_protected_call(self, button, pin, passphrase):
        # This method perform any call which have protection in the device
        res = self.client.ping(
            "random data",
            button_protection=button,
            pin_protection=pin,
            passphrase_protection=passphrase,
        )
        assert res == "random data"

    """
    def test_expected_responses(self):
        self.setup_mnemonic_pin_passphrase()

        # This is low-level test of set_expected_responses()
        # feature of debugging client

        with self.client:
            # Scenario 1 - Received unexpected message
            self.client.set_expected_responses([])
            with pytest.raises(CallException):
                self._some_protected_call(True, True, True)

        with self.client:
            # Scenario 2 - Received other than expected message
            self.client.set_expected_responses([proto.Success()])
            with pytest.raises(CallException):
                self._some_protected_call(True, True, True)

        def scenario3():
            with self.client:
                # Scenario 3 - Not received expected message
                self.client.set_expected_responses([proto.ButtonRequest(),
                                                    proto.Success(),
                                                    proto.Success()])  # This is expected, but not received
                self._some_protected_call(True, False, False)
                with pytest.raises(Exception):
                    scenario3()

        with self.client:
            # Scenario 4 - Received what expected
            self.client.set_expected_responses([proto.ButtonRequest(),
                                                proto.PinMatrixRequest(),
                                                proto.PassphraseRequest(),
                                                proto.Success(message='random data')])
            self._some_protected_call(True, True, True)

        def scenario5():
            with self.client:
                # Scenario 5 - Failed message by field filter
                self.client.set_expected_responses([proto.ButtonRequest(),
                                                    proto.Success(message='wrong data')])
                self._some_protected_call(True, True, True)
        with pytest.raises(CallException):
            scenario5()
    """

    def test_no_protection(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            assert self.client.debug.read_pin()[0] is None
            self.client.set_expected_responses([proto.Success()])
            self._some_protected_call(False, True, True)

    def test_pin(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            assert self.client.debug.read_pin()[0] == self.pin4
            self.client.setup_debuglink(button=True, pin_correct=True)
            self.client.set_expected_responses(
                [proto.ButtonRequest(), proto.PinMatrixRequest(), proto.Success()]
            )
            self._some_protected_call(True, True, False)

    def test_incorrect_pin(self):
        self.setup_mnemonic_pin_passphrase()
        self.client.setup_debuglink(button=True, pin_correct=False)
        with pytest.raises(PinException):
            self._some_protected_call(False, True, False)

    def test_cancelled_pin(self):
        self.setup_mnemonic_pin_passphrase()
        self.client.setup_debuglink(button=True, pin_correct=False)  # PIN cancel
        with pytest.raises(PinException):
            self._some_protected_call(False, True, False)

    def test_exponential_backoff_with_reboot(self):
        self.setup_mnemonic_pin_passphrase()

        self.client.setup_debuglink(button=True, pin_correct=False)

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
                self._some_protected_call(False, True, False)
            test_backoff(attempt, start)
