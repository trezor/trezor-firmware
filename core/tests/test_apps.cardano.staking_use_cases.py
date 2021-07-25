from ubinascii import unhexlify

from common import *

from apps.common import HARDENED
from trezor.crypto import bip32
from trezor.enums import CardanoAddressType
from trezor.messages import CardanoAddressParametersType
from trezor.messages import CardanoBlockchainPointerType


if not utils.BITCOIN_ONLY:
    from apps.cardano.helpers import staking_use_cases
    from apps.cardano.seed import Keychain


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoStakingUseCases(unittest.TestCase):
    def test_get(self):
        mnemonic = (
            "test walk nut penalty hip pave soap entry language right filter choice"
        )
        passphrase = ""
        node = bip32.from_mnemonic_cardano(mnemonic, passphrase)
        keychain = Keychain(node)

        expected_staking_use_cases = [
            # address parameters, expected staking use case
            (
                CardanoAddressParametersType(
                    address_type=CardanoAddressType.BASE,
                    address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                    address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                ),
                staking_use_cases.MATCH,
            ),
            (
                CardanoAddressParametersType(
                    address_type=CardanoAddressType.BASE,
                    address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                    address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 2 | HARDENED, 2, 0],
                ),
                staking_use_cases.MISMATCH,
            ),
            (
                CardanoAddressParametersType(
                    address_type=CardanoAddressType.BASE,
                    address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                    staking_key_hash=unhexlify("32c728d3861e164cab28cb8f006448139c8f1740ffb8e7aa9e5232dc"),
                ),
                staking_use_cases.MATCH,
            ),
            (
                CardanoAddressParametersType(
                    address_type=CardanoAddressType.BASE,
                    address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                    staking_key_hash=unhexlify("122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277"),
                ),
                staking_use_cases.MISMATCH,
            ),
            (
                CardanoAddressParametersType(
                    address_type=CardanoAddressType.POINTER,
                    address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                    certificate_pointer=CardanoBlockchainPointerType(
                        block_index=1, tx_index=2, certificate_index=3
                    ),
                ),
                staking_use_cases.POINTER_ADDRESS,
            ),
            (
                CardanoAddressParametersType(
                    address_type=CardanoAddressType.REWARD,
                    address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                ),
                staking_use_cases.MATCH,
            ),
            (
                CardanoAddressParametersType(
                    address_type=CardanoAddressType.ENTERPRISE,
                    address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                ),
                staking_use_cases.NO_STAKING,
            ),
            (
                CardanoAddressParametersType(
                    address_type=CardanoAddressType.BYRON,
                    address_n=[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                ),
                staking_use_cases.NO_STAKING,
            ),
        ]

        for address_parameters, expected_staking_use_case in expected_staking_use_cases:
            actual_staking_use_case = staking_use_cases.get(keychain, address_parameters)
            self.assertEqual(actual_staking_use_case, expected_staking_use_case)


if __name__ == "__main__":
    unittest.main()
