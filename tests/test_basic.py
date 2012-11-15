import unittest
import config

from bitkeylib.client import BitkeyClient
from bitkeylib import proto

class TestBasic(unittest.TestCase):

    def setUp(self):
        self.debuglink = config.DEBUG_TRANSPORT(*config.DEBUG_TRANSPORT_ARGS)
        self.transport = config.TRANSPORT(*config.TRANSPORT_ARGS)
        self.bitkey = BitkeyClient(self.transport, self.debuglink)
        
    def tearDown(self):
        self.debuglink.close()
        self.transport.close()
                
    def test_basic(self):
        self.assertEqual(self.bitkey.call(proto.Ping(message='ahoj!')), proto.Success(message='ahoj!'))