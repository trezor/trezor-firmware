import time
import unittest
import common

from trezorlib.client import CallException, PinException 
from trezorlib import proto

class TestProtectCall(common.TrezorTest):
    def _some_protected_call(self):
        # This method perform any call which have protection in the device
        entropy_len = 10
        entropy = self.client.get_entropy(entropy_len)
        self.assertEqual(len(entropy), entropy_len)

    def test_no_protection(self):
        self.client.load_device(seed=self.mnemonic1, pin='')
        
        self.assertEqual(self.client.debuglink.read_pin()[0], '')
        self._some_protected_call()

    def test_pin(self):
        self.client.load_device(seed=self.mnemonic1, pin=self.pin2)

        self.assertEqual(self.client.debuglink.read_pin()[0], self.pin2)
        self._some_protected_call()
        
    def test_incorrect_pin(self):
        self.client.setup_debuglink(button=True, pin_correct=False)
        self.assertRaises(PinException, self._some_protected_call)

    def test_cancelled_pin(self):
        self.client.setup_debuglink(button=True, pin_correct=-1)  # PIN cancel
        self.assertRaises(PinException, self._some_protected_call)

    def test_exponential_backoff_with_reboot(self):
        self.client.setup_debuglink(button=True, pin_correct=False)
        
        def test_backoff(attempts, start):
            expected = 1.8 ** attempts
            got = time.time() - start

            msg = "Pin delay expected to be at least %s seconds, got %s" % (expected, got)
            print msg
            self.assertLessEqual(expected, got, msg)

        for attempt in range(1, 6):
            start = time.time()
            self.assertRaises(PinException, self._some_protected_call)
            test_backoff(attempt, start)

        # Unplug Trezor now
        self.client.debuglink.stop()
        self.client.close()

        # Give it some time to reboot (it may take some time on RPi)
        boot_delay = 5
        start = time.time()
        time.sleep(boot_delay)

        # Connect to Trezor again
        self.setUp()
        print "Expected reboot time %s seconds" % (1.8 ** attempt)
        print "Rebooted in %s seconds" % (time.time() - start)
        self.assertLessEqual(1.8 ** attempt, time.time() - start, "Bootup took less than expected!")

if __name__ == '__main__':
    unittest.main()
