from __future__ import print_function

import unittest
from trezorlib.client import TrezorDebugClient
from trezorlib.tx_api import TXAPIBitcoin
import config

class TrezorTest(unittest.TestCase):
    def setUp(self):
        self.debug_transport = config.DEBUG_TRANSPORT(*config.DEBUG_TRANSPORT_ARGS, **config.DEBUG_TRANSPORT_KWARGS)
        self.transport = config.TRANSPORT(*config.TRANSPORT_ARGS, **config.TRANSPORT_KWARGS)
        self.client = TrezorDebugClient(self.transport)
        self.client.set_debuglink(self.debug_transport)
        self.client.set_tx_api(TXAPIBitcoin())
        # self.client.set_buttonwait(3)

        #                     1      2     3    4      5      6      7     8      9    10    11    12
        self.mnemonic12 = 'alcohol woman abuse must during monitor noble actual mixed trade anger aisle'
        self.mnemonic18 = 'owner little vague addict embark decide pink prosper true fork panda embody mixture exchange choose canoe electric jewel'
        self.mnemonic24 = 'dignity pass list indicate nasty swamp pool script soccer toe leaf photo multiply desk host tomato cradle drill spread actor shine dismiss champion exotic'
        self.mnemonic_all = ' '.join(['all'] * 12)

        self.pin4 = '1234'
        self.pin6 = '789456'
        self.pin8 = '45678978'

        self.client.wipe_device()

        print("Setup finished")
        print("--------------")

    def setup_mnemonic_allallall(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic_all, pin='', passphrase_protection=False, label='test', language='english')

    def setup_mnemonic_nopin_nopassphrase(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic12, pin='', passphrase_protection=False, label='test', language='english')

    def setup_mnemonic_pin_nopassphrase(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic12, pin=self.pin4, passphrase_protection=False, label='test', language='english')

    def setup_mnemonic_pin_passphrase(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic12, pin=self.pin4, passphrase_protection=True, label='test', language='english')

    def tearDown(self):
        self.client.close()
