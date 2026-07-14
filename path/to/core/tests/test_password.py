# complete code
import unittest
from trezor import utils
from core.crypto.password import Password

class TestPassword(unittest.TestCase):
    def test_password_verification(self):
        password = Password('test_password')
        self.assertTrue(password.verify('test_password'))

    def test_password_verification_cache(self):
        password = Password('test_password')
        self.assertTrue(password.verify('test_password'))
        self.assertTrue(password.verify('test_password'))  # Should return cached result