import unittest
import config

from bitkeylib.client import BitkeyClient
from bitkeylib.debuglink import DebugLink
from bitkeylib import proto

class TestSignTx(unittest.TestCase):

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

'''            
    def test_signtx(self):
        print self.bitkey.sign_tx([], [])
'''