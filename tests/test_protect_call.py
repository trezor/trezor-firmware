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
        
if __name__ == '__main__':
    unittest.main()
