import unittest
import config

from bitkeylib.client import BitkeyClient
from bitkeylib.debuglink import DebugLink
from bitkeylib import proto

'''
    TODO:
        * Features reflects all variations of LoadDevice
        * Maxfee settings
        * Client requires OTP
        * Client requires PIN

'''

class TestBasic(unittest.TestCase):

    def setUp(self):
        self.debug_transport = config.DEBUG_TRANSPORT(*config.DEBUG_TRANSPORT_ARGS)
        self.transport = config.TRANSPORT(*config.TRANSPORT_ARGS)
        self.bitkey = BitkeyClient(self.transport, DebugLink(self.debug_transport), algo=proto.ELECTRUM)
        
        self.bitkey.setup_debuglink(pin_correct=True, otp_correct=True)
        
        self.bitkey.load_device(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            otp=True, pin='1234', spv=True, button=True)
        
        print "Setup finished"
        print "--------------"
        
    def tearDown(self):
        self.debug_transport.close()
        self.transport.close()
            
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
        self.assertGreater(len(uuid1.UUID), 10)
        
        # Every resulf of UUID must be the same
        self.assertEqual(uuid1, uuid2)
