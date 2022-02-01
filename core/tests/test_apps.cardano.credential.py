from common import *

from apps.cardano.helpers.credential import Credential
from apps.common.paths import HARDENED
from trezor.enums import CardanoAddressType
from trezor.messages import CardanoAddressParametersType, CardanoBlockchainPointerType


CERTIFICATE_POINTER = CardanoBlockchainPointerType(
    block_index=24157,
    tx_index=177,
    certificate_index=42,
)


def _create_flags(
    is_reward: bool = False,
    is_no_staking: bool = False,
    is_mismatch: bool = False,
    is_unusual_path: bool = False,
    is_other_warning: bool = False,
) -> tuple[bool, ...]:
    return (is_reward, is_no_staking, is_mismatch, is_unusual_path, is_other_warning)


ADDRESS_PARAMETERS_CASES = [
    # base
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
        ),
        _create_flags(),
        _create_flags(),
    ),
    # base mismatch
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 1 | HARDENED, 2, 0],
        ),
        _create_flags(),
        _create_flags(is_mismatch=True),
    ),
    # base payment unusual
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
        ),
        _create_flags(is_unusual_path=True),
        _create_flags(is_mismatch=True),
    ),
    # base staking unusual
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 2, 0],
        ),
        _create_flags(is_unusual_path=True),
        _create_flags(is_unusual_path=True),
    ),
    # base both unusual and mismatch
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 102 | HARDENED, 2, 0],
        ),
        _create_flags(is_unusual_path=True),
        _create_flags(is_mismatch=True, is_unusual_path=True),
    ),
    # base staking key hash
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            staking_key_hash="1bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
        ),
        _create_flags(),
        _create_flags(is_other_warning=True),
    ),
    # base key script
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE_KEY_SCRIPT,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            staking_script_hash="1bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
        ),
        _create_flags(),
        _create_flags(is_other_warning=True),
    ),
    # base key script unusual
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE_KEY_SCRIPT,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
            staking_script_hash="1bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
        ),
        _create_flags(is_unusual_path=True),
        _create_flags(is_other_warning=True),
    ),
    # base script key
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE_SCRIPT_KEY,
            payment_script_hash="1bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
        ),
        _create_flags(is_other_warning=True),
        _create_flags(),
    ),
    # base script key unusual
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE_SCRIPT_KEY,
            payment_script_hash="1bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 2, 0],
        ),
        _create_flags(is_other_warning=True),
        _create_flags(is_unusual_path=True),
    ),
    # base script script
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BASE_SCRIPT_SCRIPT,
            payment_script_hash="1bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
            staking_script_hash="2bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
        ),
        _create_flags(is_other_warning=True),
        _create_flags(is_other_warning=True),
    ),
    # pointer
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.POINTER,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            certificate_pointer=CERTIFICATE_POINTER,
        ),
        _create_flags(),
        _create_flags(is_other_warning=True),
    ),
    # pointer unusual
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.POINTER,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
            certificate_pointer=CERTIFICATE_POINTER,
        ),
        _create_flags(is_unusual_path=True),
        _create_flags(is_other_warning=True),
    ),
    # pointer script
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.POINTER_SCRIPT,
            payment_script_hash="1bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
            certificate_pointer=CERTIFICATE_POINTER,
        ),
        _create_flags(is_other_warning=True),
        _create_flags(is_other_warning=True),
    ),
    # enterprise
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.ENTERPRISE,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
        ),
        _create_flags(),
        _create_flags(is_no_staking=True),
    ),
    # enterprise unusual
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.ENTERPRISE,
            address_n=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
        ),
        _create_flags(is_unusual_path=True),
        _create_flags(is_no_staking=True),
    ),
    # enterprise script
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.ENTERPRISE_SCRIPT,
            payment_script_hash="1bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
        ),
        _create_flags(is_other_warning=True),
        _create_flags(is_no_staking=True),
    ),
    # reward
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.REWARD,
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
        ),
        _create_flags(is_reward=True),
        _create_flags(),
    ),
    # reward unusual
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.REWARD,
            address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 2, 0],
        ),
        _create_flags(is_reward=True),
        _create_flags(is_unusual_path=True),
    ),
    # reward script
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.REWARD_SCRIPT,
            staking_script_hash="2bc428e4720732ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
        ),
        _create_flags(is_reward=True),
        _create_flags(is_other_warning=True),
    ),
    # byron
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BYRON,
            address_n=[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
        ),
        _create_flags(),
        _create_flags(is_no_staking=True),
    ),
    # byron unusual
    (
        CardanoAddressParametersType(
            address_type=CardanoAddressType.BYRON,
            address_n=[44 | HARDENED, 1815 | HARDENED, 101 | HARDENED, 0, 0],
        ),
        _create_flags(is_unusual_path=True),
        _create_flags(is_no_staking=True),
    ),
]


def _get_flags(credential: Credential) -> tuple[bool, ...]:
    return (
        credential.is_reward,
        credential.is_no_staking,
        credential.is_mismatch,
        credential.is_unusual_path,
        credential.is_other_warning,
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoCredential(unittest.TestCase):
    def test_credential_flags(self):
        for (
            address_parameters,
            expected_payment_flags,
            expected_stake_flags,
        ) in ADDRESS_PARAMETERS_CASES:
            payment_credential = Credential.payment_credential(address_parameters)
            stake_credential = Credential.stake_credential(address_parameters)
            self.assertEqual(_get_flags(payment_credential), expected_payment_flags)
            self.assertEqual(_get_flags(stake_credential), expected_stake_flags)


if __name__ == "__main__":
    unittest.main()
