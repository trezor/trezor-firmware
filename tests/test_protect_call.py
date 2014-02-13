import time
import unittest
import common

from trezorlib import messages_pb2 as proto
from trezorlib import types_pb2 as types
from trezorlib.client import PinException

# FIXME TODO Add passphrase tests

class TestProtectCall(common.TrezorTest):
    def _some_protected_call(self, button, pin, passphrase):
        # This method perform any call which have protection in the device
        res = self.client.ping('random data',
                                button_protection=button,
                                pin_protection=pin,
                                passphrase_protection=passphrase)
        self.assertEqual(res, 'random data')

    def test_no_protection(self):
        self.client.wipe_device()
        self.client.load_device_by_mnemonic(
            mnemonic=self.mnemonic1,
            pin='',
            passphrase_protection=False,
            label='test',
            language='english',
        )
        
        self.assertEqual(self.client.debug.read_pin()[0], '')
        self.client.set_expected_buttonrequests([])
        self._some_protected_call(False, True, True)

    def test_pin(self):
        self.client.wipe_device()
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic1,
                                            pin=self.pin2,
                                            passphrase_protection=True,
                                            label='test',
                                            language='english')

        self.assertEqual(self.client.debug.read_pin()[0], self.pin2)
        self.client.setup_debuglink(button=True, pin_correct=True)
        self.client.set_expected_buttonrequests([types.ButtonRequest_Other])
        self._some_protected_call(True, True, False)

    def test_incorrect_pin(self):
        self.client.setup_debuglink(button=True, pin_correct=False)
        self.assertRaises(PinException, self._some_protected_call, False, True, False)

    def test_cancelled_pin(self):
        self.client.setup_debuglink(button=True, pin_correct=False)  # PIN cancel
        self.assertRaises(PinException, self._some_protected_call, False, True, False)

    def test_exponential_backoff_with_reboot(self):
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
