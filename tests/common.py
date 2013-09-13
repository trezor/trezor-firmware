import unittest
import config

from trezorlib.client import TrezorClient
from trezorlib.debuglink import DebugLink
from trezorlib import proto

class TrezorTest(unittest.TestCase):
    def setUp(self):
        self.debug_transport = config.DEBUG_TRANSPORT(*config.DEBUG_TRANSPORT_ARGS)
        self.transport = config.TRANSPORT(*config.TRANSPORT_ARGS)
        self.client = TrezorClient(self.transport, DebugLink(self.debug_transport), debug=True)

        self.mnemonic1 = 'panda tree planet type cinnamon digital always essence grocery poor tree slot'
        self.mnemonic2 = 'glory vanish past debate cricket extra receive spring scatter rebound bat expect'
        self.pin1 = '1234'
        self.pin2 = '43211'

        self.client.setup_debuglink(button=True, pin_correct=True)
        
        self.client.load_device(
            seed=self.mnemonic1,
            pin=self.pin1)

        self.client.apply_settings(label='unit testing', coin_shortcut='BTC', language='english')

        print "Setup finished"
        print "--------------"
        
    def tearDown(self):
        self.debug_transport.close()
        self.transport.close()
