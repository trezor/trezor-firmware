# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import os

from . import conftest

from trezorlib import coins
from trezorlib import tx_api
from trezorlib.client import TrezorClientDebugLink

tests_dir = os.path.dirname(os.path.abspath(__file__))
tx_api.cache_dir = os.path.join(tests_dir, '../txcache')


class TrezorTest:

    def setup_method(self, method):
        wirelink = conftest.get_device()
        debuglink = wirelink.find_debug()
        self.client = TrezorClientDebugLink(wirelink)
        self.client.set_debuglink(debuglink)
        self.client.set_tx_api(coins.tx_api['Bitcoin'])
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
        self.client.transport.session_begin()

    def teardown_method(self, method):
        self.client.transport.session_end()
        self.client.close()

    def setup_mnemonic_allallall(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic_all, pin='', passphrase_protection=False, label='test', language='english')

    def setup_mnemonic_nopin_nopassphrase(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic12, pin='', passphrase_protection=False, label='test', language='english')

    def setup_mnemonic_nopin_passphrase(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic12, pin='', passphrase_protection=True, label='test', language='english')

    def setup_mnemonic_pin_nopassphrase(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic12, pin=self.pin4, passphrase_protection=False, label='test', language='english')

    def setup_mnemonic_pin_passphrase(self):
        self.client.load_device_by_mnemonic(mnemonic=self.mnemonic12, pin=self.pin4, passphrase_protection=True, label='test', language='english')


def generate_entropy(strength, internal_entropy, external_entropy):
    '''
    strength - length of produced seed. One of 128, 192, 256
    random - binary stream of random data from external HRNG
    '''
    import hashlib

    if strength not in (128, 192, 256):
        raise ValueError("Invalid strength")

    if not internal_entropy:
        raise ValueError("Internal entropy is not provided")

    if len(internal_entropy) < 32:
        raise ValueError("Internal entropy too short")

    if not external_entropy:
        raise ValueError("External entropy is not provided")

    if len(external_entropy) < 32:
        raise ValueError("External entropy too short")

    entropy = hashlib.sha256(internal_entropy + external_entropy).digest()
    entropy_stripped = entropy[:strength // 8]

    if len(entropy_stripped) * 8 != strength:
        raise ValueError("Entropy length mismatch")

    return entropy_stripped
