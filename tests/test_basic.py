import unittest
import common

from trezorlib import proto

'''
    TODO:
        * Features reflects all variations of LoadDevice
        * Maxfee settings
        * Client requires OTP
        * Client requires PIN

'''

class TestBasic(common.TrezorTest):           
    def test_features(self):
        features = self.client.call(proto.Initialize())
        
        # Result is the same as reported by BitkeyClient class
        self.assertEqual(features, self.client.features)
         
    def test_ping(self):
        ping = self.client.call(proto.Ping(message='ahoj!'))
        
        # Ping results in Success(message='Ahoj!')
        self.assertEqual(ping, proto.Success(message='ahoj!'))
        
    def test_uuid(self):
        uuid1 = self.client.get_serial_number()
        self.client.init_device()
        uuid2 = self.client.get_serial_number()
        
        # UUID must be longer than 10 characters
        self.assertEqual(len(uuid1), 12)
        
        # Every resulf of UUID must be the same
        self.assertEqual(uuid1, uuid2)

if __name__ == '__main__':
    unittest.main()
