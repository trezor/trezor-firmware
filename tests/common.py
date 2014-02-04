import unittest
import config

from trezorlib.client import TrezorClient
from trezorlib.debuglink import DebugLink

class TrezorTest(unittest.TestCase):
    def setUp(self):
        self.debug_transport = config.DEBUG_TRANSPORT(*config.DEBUG_TRANSPORT_ARGS, **config.DEBUG_TRANSPORT_KWARGS)
        self.transport = config.TRANSPORT(*config.TRANSPORT_ARGS, **config.TRANSPORT_KWARGS)
        self.client = TrezorClient(self.transport, DebugLink(self.debug_transport), debug=True)
        # self.client = TrezorClient(self.transport, debug=False)

        self.mnemonic1 = 'alcohol woman abuse must during monitor noble actual mixed trade anger aisle'
        self.mnemonic2 = 'owner little vague addict embark decide pink prosper true fork panda embody mixture exchange choose canoe electric jewel'
        self.pin1 = '1234'
        self.pin2 = '43211'

        self.client.setup_debuglink(button=True, pin_correct=True)
        
        self.client.wipe_device()
        self.client.load_device_by_mnemonic(
            mnemonic=self.mnemonic1,
            pin=self.pin1,
            passphrase_protection=False,
            label='test',
            language='english',
        )

        # self.client.apply_settings(label='unit testing', coin_shortcut='BTC', language='english')

        print "Setup finished"
        print "--------------"
        
    def tearDown(self):
        self.debug_transport.close()
        self.transport.close()
