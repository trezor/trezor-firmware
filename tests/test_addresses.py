import unittest
import common

import bitkeylib.bitkey_pb2 as proto 

class TestAddresses(common.BitkeyTest):
    def test_electrum_address(self):
        self.bitkey.load_device(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            otp=False, pin='', spv=False)

        self.bitkey.algo = proto.ELECTRUM
        self.assertEqual(self.bitkey.get_address([0, 0]), "1KqYyzL53R8oA1LdYvyv7m6JUryFfGJDpa")
        self.assertEqual(self.bitkey.get_address([2, 0]), "13MzKU6YjjdyiW3dZJDa5VU4AWGczQsdYD")
        self.assertEqual(self.bitkey.get_address([3, 0]), "1FQVPnjrbkPWeA8poUoEnX9U3n9DyhAVtv")
        self.assertEqual(self.bitkey.get_address([9, 0]), "1C9DHmWBpvGcFKXEiWWC3EK3EY5Bj79nze")

    def test_electrum_change_address(self):
        self.bitkey.load_device(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            otp=False, pin='', spv=False)

        self.bitkey.algo = proto.ELECTRUM
        self.assertEqual(self.bitkey.get_address([0, 1]), "17GpAFnkHRjWKePkX4kxHaHy49V8EHTr7i")
        self.assertEqual(self.bitkey.get_address([2, 1]), "1MVgq4XaMX7PmohkYzFEisH1D7uxTiPbFK")
        self.assertEqual(self.bitkey.get_address([3, 1]), "1M5NSqrUmmkZqokpHsJd5xm74YG6kjVcz4")
        self.assertEqual(self.bitkey.get_address([9, 1]), "1BXUkUsc5gGSzYUAEebg5WZWtRGPNW4NQ9")
                
    '''
    def test_bip32_address(self):
        # TODO, FIXME
        self.bitkey.load_device(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
            otp=False, pin='', spv=False)

        self.bitkey.algo = proto.BIP32
        #self.assertEqual(self.bitkey.get_address([0, 0]), "1KqYyzL53R8oA1LdYvyv7m6JUryFfGJDpa")
    '''

if __name__ == '__main__':
    unittest.main()        