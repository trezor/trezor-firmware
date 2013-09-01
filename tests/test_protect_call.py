import unittest
import common

from bitkeylib.client import CallException, PinException 
from bitkeylib import proto

class TestProtectCall(common.BitkeyTest):
    def _some_protected_call(self):
        # This method perform any call which have protection in the device
        entropy_len = 10
        entropy = self.bitkey.get_entropy(entropy_len)
        self.assertEqual(len(entropy), entropy_len)
        
    def test_no_protection(self):
        self.bitkey.load_device(
            seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            pin='')
        
        self.assertEqual(self.bitkey.debuglink.read_pin()[0], '')
        self._some_protected_call()

    def test_pin(self):
        self.bitkey.load_device(
            seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            pin='2345')

        self.assertEqual(self.bitkey.debuglink.read_pin()[0], '2345')
        self._some_protected_call()
        
    def test_incorrect_pin(self):
        self.bitkey.setup_debuglink(button=True, pin_correct=False)
        self.assertRaises(PinException, self._some_protected_call)
        
if __name__ == '__main__':
    unittest.main()