import unittest
import common

from bitkeylib import proto

'''
    TODO:
        * Features reflects all variations of LoadDevice
        * Maxfee settings
        * Client requires OTP
        * Client requires PIN

'''

class TestBasic(common.BitkeyTest):           
    def test_features(self):
        features = self.bitkey.call(proto.Initialize(session_id=self.bitkey.session_id))
        
        # Result is the same as reported by BitkeyClient class
        self.assertEqual(features, self.bitkey.features)
         
    def test_ping(self):
        ping = self.bitkey.call(proto.Ping(message='ahoj!'))
        
        # Ping results in Success(message='Ahoj!')
        self.assertEqual(ping, proto.Success(message='ahoj!'))
        
    def test_uuid(self):
        uuid1 = self.bitkey.get_uuid()
        uuid2 = self.bitkey.get_uuid()
        
        # UUID must be longer than 10 characters
        self.assertGreater(len(uuid1), 10)
        
        # Every resulf of UUID must be the same
        self.assertEqual(uuid1, uuid2)

if __name__ == '__main__':
    unittest.main()