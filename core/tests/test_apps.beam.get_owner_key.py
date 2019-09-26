from common import *

from trezor.crypto import beam
from trezor.messages.BeamOwnerKey import BeamOwnerKey

from apps.beam.get_owner_key import generate_owner_key
from apps.beam.helpers import (
    bin_to_str,
)


class TestBeamGetOwnerKey(unittest.TestCase):
    mnemonic = "abc abc abc abc abc abc abc abc abc abc abc abc"
    seed = beam.from_mnemonic_beam(mnemonic)

    def test_get_owner_key(self):
        test_suite = (
            ("1234", "YrJfzUs9hCG1JG1dknRxfou6NjRPn+Yh0FYlIHJ3uUq8LF81GUG2zYutSna7BgMDaH+K731lyikWmmtk5k0IyPK/SnmoniIc9irYJ0TWZSGlRC3ctL1Ccuip8fM13S4omMNLmKf0JzIj+jy2\n"),
            ("abcd", "YC0lfYSLKzUxHDdauwFQ0yAisxwPZrvOT3xR3hF4qCAVvoHIm10SmnDwj26CgtUEEtFFDAgNMQX5bgnsdBTYick9eZ14azERxplja/zXzY7R4z/SBnO6q8M10pR33cBnOYkq4lnFg8LtUF7F\n"),
            ("keykeykey", "myoDbg9dafcY/GyknXORNqkXNZdly5MqM1u30Js3PL+wLcjsnYPf5KNxxQY3MgqIBghu5KFwN7A27J/rPol52QBnnntodTga9volL8STzhWZPwSnboapz/MRV2HAL7U/DMEFyldd49HQQ6Fd\n"),
            ("work", "Wyen27GnxY24BV/sohamyOy2Er6m/Uuz2bFb+PJzrD5Av9iwKF0p+wPs7bWmcoZ0N3WGCMhn+FSYBbHDI37ngBbpZFDzx/Jzrrq+J39QgCzcQx/clWI9WigvsCEuvXDCTh1ymWIoalugnDCe\n"),
            ("beam", "2PaixGmhXXW8JvzFPLVVnxWAvx3NpWI8X+4VgL+BA159qfXmwcMUZkYAf8vj9WSpOtuszt00vTRI94cFiCZ0UU513qrxjYbc301PCUpiUR2I1qBoLr+2mFEgFMSJ/gCIx4KsjYcuxNwoagZv\n"),
        )

        for test_params in test_suite:
            passphrase = test_params[0]
            expected_owner_key = test_params[1]
            owner_key  = generate_owner_key(passphrase, self.mnemonic)
            self.assertEqual(str(owner_key, 'utf-8'), expected_owner_key)


if __name__ == '__main__':
    unittest.main()

