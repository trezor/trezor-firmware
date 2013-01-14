import unittest
import common

from bitkeylib import proto
from bitkeylib.client import CallException, PinException, OtpException 

class TestProtectCall(common.BitkeyTest):
    def _some_protected_call(self):
        # This method perform any call which have protection in the device
        entropy_len = 10
        entropy = self.bitkey.get_entropy(entropy_len)
        self.assertEqual(len(entropy), entropy_len)
        
    def test_no_protection(self):
        self.bitkey.load_device(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            otp=False, pin='', spv=False)
        
        self.assertEqual(self.bitkey.features.otp, False)
        self.assertEqual(self.bitkey.features.pin, False)
        self._some_protected_call()

    def test_otp_only(self):
        self.bitkey.load_device(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            otp=True, pin='', spv=False)

        self.assertEqual(self.bitkey.features.otp, True)
        self.assertEqual(self.bitkey.features.pin, False)
        self._some_protected_call()
        
    def test_pin_only(self):
        self.bitkey.load_device(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            otp=False, pin='2345', spv=False)

        self.assertEqual(self.bitkey.features.otp, False)
        self.assertEqual(self.bitkey.features.pin, True)
        self._some_protected_call()
        
    def test_both(self):
        self.bitkey.load_device(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            otp=True, pin='3456', spv=False)
        
        self.assertEqual(self.bitkey.features.otp, True)
        self.assertEqual(self.bitkey.features.pin, True)
        self._some_protected_call()

    def test_incorrect_pin(self):
        self.bitkey.setup_debuglink(button=True, pin_correct=False, otp_correct=True)
        self.assertRaises(PinException, self._some_protected_call)

    def test_incorrect_otp(self):
        self.bitkey.setup_debuglink(button=True, pin_correct=True, otp_correct=False)
        self.assertRaises(OtpException, self._some_protected_call)
        
    def test_incorrect_both(self):
        self.bitkey.setup_debuglink(button=True, pin_correct=False, otp_correct=False)
        self.assertRaises(CallException, self._some_protected_call)
        
if __name__ == '__main__':
    unittest.main()