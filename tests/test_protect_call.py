import time
import unittest
import common

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as types
from trezorlib.client import PinException, CallException

# FIXME TODO Add passphrase tests

class TestProtectCall(common.TrezorTest):
    def _some_protected_call(self, button, pin, passphrase):
        # This method perform any call which have protection in the device
        res = self.client.ping('random data',
                                button_protection=button,
                                pin_protection=pin,
                                passphrase_protection=passphrase)
        self.assertEqual(res, 'random data')

    def test_expected_responses(self):
        self.setup_mnemonic_pin_passphrase()

        # This is low-level test of set_expected_responses()
        # feature of debugging client

        # Scenario 1 - Received unexpected message
        self.client.set_expected_responses([])
        self.assertRaises(CallException, self._some_protected_call, True, True, True)

        # Scenario 2 - Received other than expected message
        self.client.set_expected_responses([proto.Success()])
        self.assertRaises(CallException, self._some_protected_call, True, True, True)

        # Scenario 3 - Not received expected message
        self.client.set_expected_responses([proto.ButtonRequest(),
                                            proto.Success(),
                                            proto.Success()])  # This is expected, but not received
        self.assertRaises(Exception, self._some_protected_call, True, False, False)

        # Scenario 4 - Received what expected
        self.client.set_expected_responses([proto.ButtonRequest(),
                                            proto.PinMatrixRequest(),
                                            proto.PassphraseRequest(),
                                            proto.Success(message='random data')])
        self._some_protected_call(True, True, True)

        # Scenario 5 - Failed message by field filter
        self.client.set_expected_responses([proto.ButtonRequest(),
                                            proto.PinMatrixRequest(),
                                            proto.Success(message='wrong data')])
        self.assertRaises(CallException, self._some_protected_call, True, True, True)

    def test_no_protection(self):
        self.setup_mnemonic_nopin_nopassphrase()

        self.assertEqual(self.client.debug.read_pin()[0], '')
        self.client.set_expected_responses([proto.Success()])
        self._some_protected_call(False, True, True)

    def test_pin(self):
        self.setup_mnemonic_pin_passphrase()

        self.assertEqual(self.client.debug.read_pin()[0], self.pin4)
        self.client.setup_debuglink(button=True, pin_correct=True)
        self.client.set_expected_responses([proto.ButtonRequest(),
                                            proto.PinMatrixRequest(),
                                            proto.Success()])
        self._some_protected_call(True, True, False)

    def test_incorrect_pin(self):
        self.setup_mnemonic_pin_passphrase()
        self.client.setup_debuglink(button=True, pin_correct=False)
        self.assertRaises(PinException, self._some_protected_call, False, True, False)

    def test_cancelled_pin(self):
        self.setup_mnemonic_pin_passphrase()
        self.client.setup_debuglink(button=True, pin_correct=False)  # PIN cancel
        self.assertRaises(PinException, self._some_protected_call, False, True, False)

    def test_exponential_backoff_with_reboot(self):
        self.setup_mnemonic_pin_passphrase()

        self.client.setup_debuglink(button=True, pin_correct=False)

        def test_backoff(attempts, start):
            expected = 1.8 ** attempts
            got = time.time() - start

            msg = "Pin delay expected to be at least %s seconds, got %s" % (expected, got)
            print msg
            self.assertLessEqual(expected, got, msg)

        for attempt in range(1, 4):
            start = time.time()
            self.assertRaises(PinException, self._some_protected_call, False, True, False)
            test_backoff(attempt, start)
'''
        # Unplug Trezor now
        self.client.debuglink.stop()
        self.client.close()

        # Give it some time to reboot (it may take some time on RPi)
        boot_delay = 20
        time.sleep(boot_delay)

        # Connect to Trezor again
        start = time.time()
        self.setUp()
        expected = 1.8 ** attempt / 2  # This test isn't accurate, let's expect at least some delay
        took = time.time() - start
        print "Expected reboot time at least %s seconds" % expected
        print "Rebooted in %s seconds" % took
        self.assertLessEqual(expected, time.time() - start, "Bootup took %s seconds, expected %s seconds or more!" % (took, expected))
        '''

if __name__ == '__main__':
    unittest.main()
